import os
import aiohttp
from fastapi import FastAPI, HTTPException, Request, Header
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
from supabase import create_client, Client
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import datetime

# Custom Logging
from logging_config import logger

# Load env vars
load_dotenv()

# Configuration
# Configuration
ASAAS_API_KEY = os.getenv('ASAAS_API_KEY')
ASAAS_WEBHOOK_TOKEN = os.getenv('ASAAS_WEBHOOK_TOKEN')  # Ensure this is set in .env
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

if ASAAS_API_KEY:
    logger.info(f"ASAAS_API_KEY loaded. Length: {len(ASAAS_API_KEY)}")
else:
    logger.critical("ASAAS_API_KEY NOT loaded. Production mode requires API Key.")

# Default to Production URL
ASAAS_API_URL = "https://api.asaas.com/v3"
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') 

# Initialize clients
app = FastAPI()

# CORS Middleware
origins = [
    FRONTEND_URL,
    "http://localhost:3000",
    "https://bot-fazendeiro-dashboard.vercel.app", # Example production URL
    "http://fazendabot.einsof7.com",
    "https://fazendabot.einsof7.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Models
class PixChargeRequest(BaseModel):
    guild_id: str
    plano_id: int
    pagador_discord_id: str
    cpf_cnpj: str # Added CPF/CNPJ
    email: Optional[str] = None # Optional email

class WebhookEvent(BaseModel):
    event: str
    payment: dict

@app.get("/")
async def root():
    return {"status": "online", "service": "Bot Fazendeiro API (Production)"}

@app.post("/api/pix/create")
async def create_pix_charge(req: PixChargeRequest):
    """Creates a customer and a PIX charge in Asaas."""
    logger.info(f"Received PIX charge request: {req.dict()}")

    if not ASAAS_API_KEY:
        logger.error("Asaas API Key missing during charge creation.")
        raise HTTPException(status_code=500, detail="Asaas API Key not configured")

    # Production URL
    current_asaas_url = os.getenv('ASAAS_API_URL', "https://api.asaas.com/v3")

    headers = {
        "access_token": ASAAS_API_KEY,
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        # 1. Fetch Plan Details
        try:
            plan_resp = supabase.table('planos').select('*').eq('id', req.plano_id).single().execute()
            if not plan_resp.data:
                logger.warning(f"Plan not found: {req.plano_id}")
                raise HTTPException(status_code=404, detail="Plano not found")
            plano = plan_resp.data
        except Exception as e:
            logger.error(f"Error fetching plan: {e}")
            raise HTTPException(status_code=500, detail="Database error fetching plan")

        # 2. Create/Get Customer in Asaas
        # Use provided email or fallback to a dummy one
        customer_email = req.email or f"user_{req.pagador_discord_id}@fazendeiro.bot"
        
        customer_data = {
            "name": f"User {req.pagador_discord_id}",
            "email": customer_email, 
            "cpfCnpj": req.cpf_cnpj, # Critical for PIX
            "externalReference": req.pagador_discord_id
        }

        async with session.post(f"{current_asaas_url}/customers", headers=headers, json=customer_data) as resp:
            if resp.status != 200:
                text = await resp.text()
                logger.warning(f"Asaas Customer Creation Error: {text}")
                
                if "customer_email_unique" in text:
                     # Fallback: search by email
                     async with session.get(f"{current_asaas_url}/customers?email={customer_data['email']}", headers=headers) as search_resp:
                         search_data = await search_resp.json()
                         if search_data.get('data') and len(search_data['data']) > 0:
                             customer_id = search_data['data'][0]['id']
                             logger.info(f"Found existing customer: {customer_id}")
                             
                             # UPDATE customer with new CPF/CNPJ
                             update_data = {"cpfCnpj": req.cpf_cnpj}
                             async with session.put(f"{current_asaas_url}/customers/{customer_id}", headers=headers, json=update_data) as update_resp:
                                 if update_resp.status == 200:
                                     logger.info(f"Updated customer {customer_id} with CPF.")
                                 else:
                                     logger.warning(f"Failed to update customer CPF: {await update_resp.text()}")

                         else: 
                             logger.error("Customer creation failed and search returned empty.")
                             raise HTTPException(status_code=400, detail=f"Customer creation failed: {text}")
                else: 
                     # Try to parse error
                     try:
                        customer_json = await resp.json()
                        if 'id' in customer_json:
                             customer_id = customer_json.get('id')
                        else:
                             raise Exception("No ID in response")
                     except:
                         logger.error(f"Critical error creating customer. Response: {text}")
                         raise HTTPException(status_code=500, detail=f"Error creating payment customer: {text}")
            else:
                customer_json = await resp.json()
                customer_id = customer_json['id']
                logger.info(f"Created new customer: {customer_id}")

        # 3. Create Payment
        due_date = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        
        charge_data = {
            "customer": customer_id,
            "billingType": "PIX",
            "value": float(plano['preco']), # Ensure float
            "dueDate": due_date,
            "description": f"Assinatura Bot Fazendeiro - {plano['nome']}",
            "externalReference": f"{req.guild_id}_{req.plano_id}_{int(datetime.datetime.now().timestamp())}"
        }

        async with session.post(f"{current_asaas_url}/payments", headers=headers, json=charge_data) as resp:
            if resp.status != 200:
                text = await resp.text()
                logger.error(f"Asaas Payment Error: {text}")
                raise HTTPException(status_code=500, detail=f"Error creating charge: {text}")
            charge = await resp.json()
            logger.info(f"Created charge: {charge['id']}")

        # 4. Get QR Code (Robust Retry)
        qr_data = None
        for attempt in range(3):
            async with session.get(f"{current_asaas_url}/payments/{charge['id']}/pixQrCode", headers=headers) as resp:
                if resp.status == 200:
                    qr_data = await resp.json()
                    break
                elif resp.status == 404:
                    logger.warning(f"QR Code not ready yet (Attempt {attempt+1}/3). Retrying in 1s...")
                    await asyncio.sleep(1)
                else:
                    text = await resp.text()
                    logger.error(f"Error retrieving QR Code: {text}")
                    raise HTTPException(status_code=500, detail=f"Error retrieving QR Code: {text}")
        
        if not qr_data:
             logger.error("Timeout retrieving QR Code from Asaas after retries.")
             raise HTTPException(status_code=504, detail="Timeout retrieving QR Code from Asaas")

        # 5. Save to Database
        try:
            supabase.table('pagamentos_pix').insert({
                'pix_id': charge['id'],
                'guild_id': req.guild_id,
                'plano_id': req.plano_id,
                'discord_id': req.pagador_discord_id,
                'status': 'pendente',
                'pix_qrcode': qr_data['encodedImage'],
                'pix_copia_cola': qr_data['payload'],
                'valor': float(plano['preco']),
                'link_pagamento': charge.get('invoiceUrl')
            }).execute()
        except Exception as e:
            logger.error(f"DB Error saving payment: {e}")
            # Do not fail request if DB fails, as Payment IS created. User can retry or check web.
            # But better to warn.
            pass 

        return {
            "payment_id": charge['id'],
            "qrcode": f"data:image/png;base64,{qr_data['encodedImage']}",
            "copia_cola": qr_data['payload'],
            "expiracao": due_date 
        }

@app.post("/api/pix/webhook")
async def handle_webhook(request: Request, asaas_access_token: Optional[str] = Header(None)):
    """Handles Asaas Webhooks."""
    
    # 1. Security Verification
    if not ASAAS_WEBHOOK_TOKEN:
        logger.critical("SECURITY ALERT: ASAAS_WEBHOOK_TOKEN not configured! Rejecting webhook.")
        raise HTTPException(status_code=500, detail="Server misconfiguration: Webhook Token missing")

    if asaas_access_token != ASAAS_WEBHOOK_TOKEN:
        logger.warning(f"Unauthorized Webhook attempt. Token: {asaas_access_token}")
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        data = await request.json()
        logger.info(f"Webhook received: {data}")
        
        event = data.get('event')
        payment = data.get('payment')
        
        if not payment:
            return {"status": "ignored", "reason": "no_payment_data"}

        payment_id = payment.get('id')
        
        if event in ['PAYMENT_RECEIVED', 'PAYMENT_CONFIRMED']:
            await process_payment_confirmation(payment_id)
            return {"status": "success", "action": "subscription_activated"}

        return {"status": "received", "event": event}

    except Exception as e:
        logger.error(f"Webhook Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pix/verify/{payment_id}")
async def verify_payment_endpoint(payment_id: str):
    """
    Active Payment Verification Endpoint.
    Checks status in Asaas and updates DB if Paid.
    """
    logger.info(f"Manual verification requested for: {payment_id}")
    
    # 1. Check local status first
    try:
        local_record = supabase.table('pagamentos_pix').select('*').eq('pix_id', payment_id).single().execute()
        if not local_record.data:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        if local_record.data['status'] == 'pago':
             return {"status": "pago", "message": "Payment already confirmed"}
    except Exception as e:
        logger.error(f"DB Error: {e}")
        raise HTTPException(status_code=500, detail="Database Error")

    # 2. Check Asaas API
    if not ASAAS_API_KEY:
        # Dev/Localhost Fallback: If no API key, we trust the polling if status is 'pago' (which we checked above)
        # OR we simulate success if requested for dev
        logger.warning("No Asaas API Key, cannot verify remotely.")
        return {"status": "pending", "message": "Cannot verify remotely without API Key"}

    current_asaas_url = os.getenv('ASAAS_API_URL', "https://api.asaas.com/v3")
    headers = {"access_token": ASAAS_API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{current_asaas_url}/payments/{payment_id}", headers=headers) as resp:
            if resp.status == 200:
                payment_data = await resp.json()
                status = payment_data.get('status')
                
                if status in ['RECEIVED', 'CONFIRMED']:
                    # Active Confirmation!
                    await process_payment_confirmation(payment_id)
                    return {"status": "pago", "message": "Payment confirmed and subscription activated"}
                else:
                    return {"status": status.lower(), "message": f"Payment status is {status}"}
            else:
                raise HTTPException(status_code=resp.status, detail="Error communicating with payment provider")


async def process_payment_confirmation(payment_id: str):
    """Core logic to activate subscription from a confirmed payment."""
    logger.info(f"Processing confirmation for: {payment_id}")
    
    # Update Payment Status
    supabase.table('pagamentos_pix').update({'status': 'pago'}).eq('pix_id', payment_id).execute()
    
    # Get payment details
    pay_record = supabase.table('pagamentos_pix').select('*').eq('pix_id', payment_id).single().execute()
    
    if pay_record.data:
        guild_id = pay_record.data['guild_id']
        plano_id = pay_record.data['plano_id']
        
        # Guard clause for pending activation
        if guild_id == 'pending_activation':
            logger.warning(f"Payment {payment_id} is paid but has no guild linked yet.")
            return

        # Fetch plan duration
        plano = supabase.table('planos').select('*').eq('id', plano_id).single().execute()
        days = plano.data['duracao_dias']
        
        # Calculate expiration (Idempotency check could go here)
        expiration = (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()
        
        # Update/Create Subscription
        existing = supabase.table('assinaturas').select('*').eq('guild_id', guild_id).execute()
        
        subscription_data = {
            'plano_id': plano_id,
            'data_inicio': datetime.datetime.now().isoformat(),
            'data_expiracao': expiration,
            'status': 'ativa',
            'pagamento_status': 'pago'
        }

        if existing.data:
            supabase.table('assinaturas').update(subscription_data).eq('guild_id', guild_id).execute()
            logger.info(f"Subscription updated for guild {guild_id}")
        else:
            subscription_data['guild_id'] = guild_id
            supabase.table('assinaturas').insert(subscription_data).execute()
            logger.info(f"Subscription created for guild {guild_id}")
