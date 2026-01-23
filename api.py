import os
import aiohttp
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
from supabase import create_client, Client

# Load env vars
load_dotenv()

# Configuration
ASAAS_API_KEY = os.getenv('ASAAS_API_KEY') or os.getenv('ASAAS_SANDBOX_API_KEY')
if ASAAS_API_KEY:
    print(f"DEBUG: ASAAS_API_KEY loaded. Length: {len(ASAAS_API_KEY)}. First 5 chars: {ASAAS_API_KEY[:5]}")
else:
    print("DEBUG: ASAAS_API_KEY NOT loaded.")

ASAAS_API_URL = "https://sandbox.asaas.com/api/v3"
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

from fastapi.middleware.cors import CORSMiddleware

# Initialize clients
app = FastAPI()

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for now to ensure it works, then restrict
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

class WebhookEvent(BaseModel):
    event: str
    payment: dict

@app.get("/")
async def root():
    return {"status": "online", "service": "Bot Fazendeiro API"}

@app.post("/api/pix/create")
async def create_pix_charge(req: PixChargeRequest):
    """Creates a customer and a PIX charge in Asaas."""
    if not ASAAS_API_KEY:
        raise HTTPException(status_code=500, detail="Asaas API Key not configured")

    headers = {
        "access_token": ASAAS_API_KEY,
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        # 1. Fetch Plan Details
        try:
            plan_resp = supabase.table('planos').select('*').eq('id', req.plano_id).single().execute()
            if not plan_resp.data:
                raise HTTPException(status_code=404, detail="Plano not found")
            plano = plan_resp.data
        except Exception as e:
            print(f"Error fetching plan: {e}")
            raise HTTPException(status_code=500, detail="Database error fetching plan")

        # 2. Create/Get Customer in Asaas
        # Ideally we search first, but for now we'll create or use existing if we store asaas_id later.
        # For simplicity in this flow, we'll create a new customer or use a generic one if not provided.
        # In a real app, you should check `empresas` table for an existing `asaas_customer_id`.
        
        # Helper: Get user email/name from discord (optional, sticking to basics)
        customer_data = {
            "name": f"User {req.pagador_discord_id}",
            "email": "email@example.com", 
            "externalReference": req.pagador_discord_id
        }

        # Check if company exists to link
        empresa_resp = supabase.table('empresas').select('*').eq('guild_id', req.guild_id).execute()
        
        async with session.post(f"{ASAAS_API_URL}/customers", headers=headers, json=customer_data) as resp:
            if resp.status != 200:
                text = await resp.text()
                print(f"Asaas Customer Error: {text}")
                # If email already exists, Asaas might return 400. We should handle search.
                # For this MVP, we proceed. If it fails, check logs.
                if "customer_email_unique" in text:
                     # Fallback: search by email
                     async with session.get(f"{ASAAS_API_URL}/customers?email={customer_data['email']}", headers=headers) as search_resp:
                         search_data = await search_resp.json()
                         if search_data['data']:
                             customer_id = search_data['data'][0]['id']
                         else: 
                             raise HTTPException(status_code=400, detail="Customer creation failed")
                else: 
                     customer_json = await resp.json()
                     customer_id = customer_json.get('id')
            else:
                customer_json = await resp.json()
                customer_id = customer_json['id']

        # 3. Create Payment
        import datetime
        due_date = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        
        charge_data = {
            "customer": customer_id,
            "billingType": "PIX",
            "value": plano['preco'],
            "dueDate": due_date,
            "description": f"Assinatura Bot Fazendeiro - {plano['nome']}",
            "externalReference": f"{req.guild_id}_{req.plano_id}_{int(datetime.datetime.now().timestamp())}"
        }

        async with session.post(f"{ASAAS_API_URL}/payments", headers=headers, json=charge_data) as resp:
            if resp.status != 200:
                text = await resp.text()
                print(f"Asaas Payment Error: {text}") # Debug print
                raise HTTPException(status_code=500, detail=f"Error creating charge: {text}")
            charge = await resp.json()

        # 4. Get QR Code
        async with session.get(f"{ASAAS_API_URL}/payments/{charge['id']}/pixQrCode", headers=headers) as resp:
            if resp.status != 200:
                 raise HTTPException(status_code=500, detail="Error retrieving QR Code")
            qr_data = await resp.json()

        # 5. Save to Database
        try:
            supabase.table('pagamentos_pix').insert({
                'payment_id': charge['id'], # Asaas ID
                'guild_id': req.guild_id,
                'plano_id': req.plano_id,
                'discord_id': req.pagador_discord_id,
                'status': 'pendente',
                'qr_code': qr_data['encodedImage'],
                'copia_cola': qr_data['payload'],
                'valor': plano['preco'],
                'link_pagamento': charge.get('invoiceUrl')
            }).execute()
        except Exception as e:
            print(f"DB Error: {e}")
            raise HTTPException(status_code=500, detail="Error saving payment to database")

        return {
            "payment_id": charge['id'],
            "qrcode": f"data:image/png;base64,{qr_data['encodedImage']}",
            "copia_cola": qr_data['payload'],
            "expiracao": due_date 
        }

@app.post("/api/pix/webhook")
async def handle_webhook(request: Request):
    """Handles Asaas Webhooks."""
    # Verify signature if needed (Asaas sends access-token in header usually)
    # token = request.headers.get('asaas-access-token')
    # if token != WEBHOOK_TOKEN: return ...

    try:
        data = await request.json()
        event = data.get('event')
        payment = data.get('payment')
        
        if not payment:
            return {"status": "ignored", "reason": "no_payment_data"}

        payment_id = payment.get('id')
        
        if event == 'PAYMENT_RECEIVED' or event == 'PAYMENT_CONFIRMED':
            # Update Payment Status
            supabase.table('pagamentos_pix').update({'status': 'pago'}).eq('payment_id', payment_id).execute()
            
            # Get payment details to activate subscription
            pay_record = supabase.table('pagamentos_pix').select('*').eq('payment_id', payment_id).single().execute()
            
            if pay_record.data:
                guild_id = pay_record.data['guild_id']
                plano_id = pay_record.data['plano_id']
                
                # Fetch plan duration
                plano = supabase.table('planos').select('*').eq('id', plano_id).single().execute()
                days = plano.data['duracao_dias']
                
                # Update/Create Subscription
                # Using RPC or direct insert/update logic to set expiration
                # Ideally, call a procedure. For now, we calculate expiration.
                import datetime
                expiration = (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()
                
                # Check if exists
                existing = supabase.table('assinaturas').select('*').eq('guild_id', guild_id).execute()
                
                if existing.data:
                    # Update
                    current_exp = existing.data[0]['data_expiracao']
                    # logic to extend if already active? For now, we just set new expiration from TODAY or extend?
                    # Simple rule: set to now + days
                    supabase.table('assinaturas').update({
                        'plano_id': plano_id,
                        'data_inicio': datetime.datetime.now().isoformat(),
                        'data_expiracao': expiration,
                        'status': 'ativa',
                        'pagamento_status': 'pago'
                    }).eq('guild_id', guild_id).execute()
                else:
                    # Create
                    supabase.table('assinaturas').insert({
                        'guild_id': guild_id,
                        'plano_id': plano_id,
                        'data_inicio': datetime.datetime.now().isoformat(),
                        'data_expiracao': expiration,
                        'status': 'ativa',
                        'pagamento_status': 'pago'
                    }).execute()
                
                return {"status": "success", "action": "subscription_activated"}

        return {"status": "received", "event": event}

    except Exception as e:
        print(f"Webhook Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
