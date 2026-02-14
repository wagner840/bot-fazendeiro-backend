"""
Payment routes for Bot Fazendeiro API.
Handles PIX creation, webhook processing, and payment verification/status.
"""

from __future__ import annotations

import asyncio
import datetime
import hashlib
import hmac
import json
import random
import time
from typing import Optional

import aiohttp
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from api_pkg.auth import AuthContext, get_guild_access, require_auth_context
from api_pkg.observability import inc_counter, observe_histogram
from api_pkg.rate_limit import limiter
from config import ASAAS_API_KEY, ASAAS_API_URL, ASAAS_WEBHOOK_TOKEN, supabase
from logging_config import logger

router = APIRouter(prefix="/api/pix", tags=["payments"])


class PixChargeRequest(BaseModel):
    guild_id: str
    plano_id: int
    cpf_cnpj: str = Field(min_length=11, max_length=18)
    email: Optional[str] = None


def _normalize_cpf_cnpj(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


async def _request_asaas(
    method: str,
    url: str,
    headers: dict,
    *,
    json_data: Optional[dict] = None,
    retries: int = 3,
) -> tuple[int, dict | str]:
    timeout = aiohttp.ClientTimeout(total=20, connect=5, sock_connect=5, sock_read=15)
    delay = 0.5
    for attempt in range(retries):
        start = time.perf_counter()
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(method, url, headers=headers, json=json_data) as response:
                    elapsed = time.perf_counter() - start
                    text = await response.text()
                    payload: dict | str
                    try:
                        payload = json.loads(text) if text else {}
                    except json.JSONDecodeError:
                        payload = text

                    inc_counter(
                        "asaas_http_requests_total",
                        labels={"method": method, "status": str(response.status), "endpoint": url.split("/")[-1]},
                    )
                    observe_histogram(
                        "asaas_http_request_duration_seconds",
                        elapsed,
                        labels={"method": method, "status": str(response.status)},
                    )
                    if response.status in {429, 500, 502, 503, 504} and attempt < retries - 1:
                        await asyncio.sleep(delay + random.uniform(0.05, delay * 0.2))
                        delay *= 2
                        continue
                    return response.status, payload
        except aiohttp.ClientError:
            inc_counter("asaas_http_errors_total", labels={"method": method})
            if attempt >= retries - 1:
                raise
            await asyncio.sleep(delay + random.uniform(0.05, delay * 0.2))
            delay *= 2
    return 500, {"error": "unexpected_retry_exhausted"}


async def _authorize_guild_access(auth: AuthContext, guild_id: str, *, require_admin: bool = False) -> dict:
    if auth.is_superadmin:
        return {"role": "superadmin", "guild_id": guild_id}

    access = await get_guild_access(auth.discord_id, guild_id)
    if not access:
        raise HTTPException(status_code=403, detail="User has no access to this guild")

    if require_admin and access.get("role") not in {"admin", "superadmin"}:
        raise HTTPException(status_code=403, detail="Admin role required for this action")
    return access


async def _authorize_payment_access(auth: AuthContext, payment: dict, *, require_admin: bool = False) -> dict:
    guild_id = payment.get("guild_id")
    payment_discord_id = payment.get("discord_id")

    if auth.is_superadmin:
        return {"role": "superadmin"}

    if guild_id == "pending_activation":
        if payment_discord_id and payment_discord_id != auth.discord_id:
            raise HTTPException(status_code=403, detail="Payment does not belong to authenticated user")
        return {"role": "owner"}

    access = await _authorize_guild_access(auth, guild_id, require_admin=False)
    if require_admin and access.get("role") not in {"admin", "superadmin"}:
        raise HTTPException(status_code=403, detail="Admin role required")

    if payment_discord_id and payment_discord_id != auth.discord_id and access.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Payment does not belong to authenticated user")
    return access


async def _register_webhook_event(
    *,
    event_hash: str,
    event_type: str,
    payment_id: Optional[str],
    payload: dict,
) -> bool:
    response = await (
        supabase.table("webhook_events")
        .insert(
            {
                "provider": "asaas",
                "event_hash": event_hash,
                "event_type": event_type,
                "payment_id": payment_id,
                "payload": payload,
                "status": "processing",
            }
        )
        .execute()
    )
    return bool(response.data)


async def _mark_webhook_event(event_hash: str, status: str, error_message: Optional[str] = None) -> None:
    update_data = {
        "status": status,
        "processed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    if error_message:
        update_data["error_message"] = error_message[:1000]
    await supabase.table("webhook_events").update(update_data).eq("event_hash", event_hash).execute()


async def process_payment_confirmation(payment_id: str) -> bool:
    logger.info("Processing confirmation for payment_id=%s", payment_id)

    pay_record = (
        await supabase.table("pagamentos_pix").select("*").eq("pix_id", payment_id).single().execute()
    )
    if not pay_record.data:
        logger.warning("Payment %s not found in database", payment_id)
        inc_counter("payment_confirmation_not_found_total")
        return False

    if pay_record.data.get("status") == "pago":
        logger.info("Payment %s already processed", payment_id)
        inc_counter("payment_confirmation_already_processed_total")
        return False

    await supabase.table("pagamentos_pix").update({"status": "pago"}).eq("pix_id", payment_id).execute()

    guild_id = pay_record.data["guild_id"]
    plano_id = pay_record.data["plano_id"]
    if guild_id == "pending_activation":
        logger.warning("Payment %s paid but no guild linked yet", payment_id)
        inc_counter("payment_confirmation_pending_activation_total")
        return True

    plano = await supabase.table("planos").select("*").eq("id", plano_id).single().execute()
    days = int(plano.data["duracao_dias"])
    now = datetime.datetime.now(datetime.timezone.utc)
    expiration = (now + datetime.timedelta(days=days)).isoformat()

    existing = await supabase.table("assinaturas").select("id").eq("guild_id", guild_id).execute()
    subscription_data = {
        "plano_id": plano_id,
        "data_inicio": now.isoformat(),
        "data_expiracao": expiration,
        "status": "ativa",
        "pagador_discord_id": pay_record.data.get("discord_id"),
    }
    if existing.data:
        await supabase.table("assinaturas").update(subscription_data).eq("guild_id", guild_id).execute()
    else:
        subscription_data["guild_id"] = guild_id
        await supabase.table("assinaturas").insert(subscription_data).execute()
    inc_counter("payment_confirmation_success_total")
    return True


@router.post("/create")
@limiter.limit("5/minute")
async def create_pix_charge(
    request: Request,
    req: PixChargeRequest,
    auth: AuthContext = Depends(require_auth_context),
):
    request_id = getattr(request.state, "request_id", "n/a")
    if not ASAAS_API_KEY:
        raise HTTPException(status_code=500, detail="Asaas API Key not configured")

    normalized_doc = _normalize_cpf_cnpj(req.cpf_cnpj)
    if len(normalized_doc) not in {11, 14}:
        raise HTTPException(status_code=422, detail="cpf_cnpj must be valid digits")

    if req.guild_id != "pending_activation":
        await _authorize_guild_access(auth, req.guild_id)

    plan_resp = await supabase.table("planos").select("*").eq("id", req.plano_id).single().execute()
    if not plan_resp.data:
        raise HTTPException(status_code=404, detail="Plano not found")
    plano = plan_resp.data

    headers = {
        "access_token": ASAAS_API_KEY,
        "Content-Type": "application/json",
    }
    customer_email = req.email or auth.email or f"user_{auth.discord_id}@fazendeiro.bot"
    customer_data = {
        "name": f"Discord {auth.discord_id}",
        "email": customer_email,
        "cpfCnpj": normalized_doc,
        "externalReference": auth.discord_id,
    }

    status, customer_payload = await _request_asaas(
        "POST", f"{ASAAS_API_URL}/customers", headers, json_data=customer_data
    )
    if status != 200:
        # Attempt by e-mail fallback.
        status_search, search_payload = await _request_asaas(
            "GET", f"{ASAAS_API_URL}/customers?email={customer_email}", headers
        )
        if status_search == 200 and isinstance(search_payload, dict) and search_payload.get("data"):
            customer_id = search_payload["data"][0]["id"]
            await _request_asaas(
                "PUT",
                f"{ASAAS_API_URL}/customers/{customer_id}",
                headers,
                json_data={"cpfCnpj": normalized_doc},
            )
        else:
            raise HTTPException(status_code=400, detail="Error creating payment customer")
    else:
        if not isinstance(customer_payload, dict) or "id" not in customer_payload:
            raise HTTPException(status_code=502, detail="Invalid customer response from Asaas")
        customer_id = customer_payload["id"]

    due_date = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    charge_data = {
        "customer": customer_id,
        "billingType": "PIX",
        "value": float(plano["preco"]),
        "dueDate": due_date,
        "description": f"Assinatura Bot Fazendeiro - {plano['nome']}",
        "externalReference": f"{req.guild_id}_{req.plano_id}_{int(datetime.datetime.now().timestamp())}",
    }
    status_charge, charge_payload = await _request_asaas(
        "POST", f"{ASAAS_API_URL}/payments", headers, json_data=charge_data
    )
    if status_charge != 200 or not isinstance(charge_payload, dict):
        raise HTTPException(status_code=502, detail="Error creating charge with Asaas")
    payment_id = charge_payload.get("id")
    if not payment_id:
        raise HTTPException(status_code=502, detail="Invalid payment response from Asaas")

    qr_data = None
    for attempt in range(3):
        status_qr, qr_payload = await _request_asaas(
            "GET", f"{ASAAS_API_URL}/payments/{payment_id}/pixQrCode", headers
        )
        if status_qr == 200 and isinstance(qr_payload, dict):
            qr_data = qr_payload
            break
        if status_qr == 404 and attempt < 2:
            await asyncio.sleep(1.0 * (attempt + 1))
            continue
        raise HTTPException(status_code=504, detail="Timeout retrieving QR Code from Asaas")

    await (
        supabase.table("pagamentos_pix")
        .insert(
            {
                "pix_id": payment_id,
                "guild_id": req.guild_id,
                "plano_id": req.plano_id,
                "discord_id": auth.discord_id,
                "status": "pendente",
                "pix_qrcode": qr_data["encodedImage"],
                "pix_copia_cola": qr_data["payload"],
                "valor": float(plano["preco"]),
                "link_pagamento": charge_payload.get("invoiceUrl"),
                "pix_expiracao": due_date,
            }
        )
        .execute()
    )

    logger.info(
        "PIX created request_id=%s guild=%s plano=%s payment_id=%s discord_id=%s",
        request_id,
        req.guild_id,
        req.plano_id,
        payment_id,
        auth.discord_id,
    )
    inc_counter("pix_create_success_total")
    return {
        "payment_id": payment_id,
        "qrcode": f"data:image/png;base64,{qr_data['encodedImage']}",
        "copia_cola": qr_data["payload"],
        "expiracao": due_date,
    }


@router.post("/webhook")
@limiter.limit("30/minute")
async def handle_webhook(
    request: Request,
    asaas_access_token: Optional[str] = Header(None),
):
    request_id = getattr(request.state, "request_id", "n/a")
    if not ASAAS_WEBHOOK_TOKEN:
        raise HTTPException(status_code=500, detail="Server misconfiguration: Webhook Token missing")

    if not hmac.compare_digest((asaas_access_token or "").encode(), ASAAS_WEBHOOK_TOKEN.encode()):
        inc_counter("pix_webhook_unauthorized_total")
        raise HTTPException(status_code=401, detail="Unauthorized")

    body = await request.body()
    event_hash = hashlib.sha256(body).hexdigest()
    data = json.loads(body.decode("utf-8")) if body else {}
    event = data.get("event", "unknown")
    payment = data.get("payment") or {}
    payment_id = payment.get("id")

    try:
        was_inserted = await _register_webhook_event(
            event_hash=event_hash,
            event_type=event,
            payment_id=payment_id,
            payload=data,
        )
    except Exception:
        # Duplicate event hash.
        logger.info(
            "Duplicate webhook ignored request_id=%s event_hash=%s payment_id=%s",
            request_id,
            event_hash,
            payment_id,
        )
        return {"status": "duplicate", "payment_id": payment_id}

    if not was_inserted:
        return {"status": "duplicate", "payment_id": payment_id}

    try:
        if payment_id and event in {"PAYMENT_RECEIVED", "PAYMENT_CONFIRMED"}:
            await process_payment_confirmation(payment_id)
        await _mark_webhook_event(event_hash, "processed")
        inc_counter("pix_webhook_processed_total", labels={"event": event})
        return {"status": "success", "event": event, "payment_id": payment_id}
    except Exception as exc:
        await _mark_webhook_event(event_hash, "failed", str(exc))
        logger.exception("Webhook error request_id=%s payment_id=%s", request_id, payment_id)
        inc_counter("pix_webhook_failed_total")
        raise HTTPException(status_code=500, detail="Webhook processing error")


@router.get("/status/{payment_id}")
@limiter.limit("30/minute")
async def get_payment_status(
    request: Request,
    payment_id: str,
    auth: AuthContext = Depends(require_auth_context),
):
    request_id = getattr(request.state, "request_id", "n/a")
    local_record = (
        await supabase.table("pagamentos_pix").select("*").eq("pix_id", payment_id).single().execute()
    )
    if not local_record.data:
        raise HTTPException(status_code=404, detail="Payment not found")
    await _authorize_payment_access(auth, local_record.data, require_admin=False)
    return {
        "request_id": request_id,
        "payment_id": payment_id,
        "status": local_record.data.get("status"),
        "guild_id": local_record.data.get("guild_id"),
        "plano_id": local_record.data.get("plano_id"),
        "valor": local_record.data.get("valor"),
        "updated_at": local_record.data.get("updated_at"),
    }


@router.post("/verify/{payment_id}")
@limiter.limit("10/minute")
async def verify_payment_endpoint(
    request: Request,
    payment_id: str,
    auth: AuthContext = Depends(require_auth_context),
):
    request_id = getattr(request.state, "request_id", "n/a")
    local_record = (
        await supabase.table("pagamentos_pix").select("*").eq("pix_id", payment_id).single().execute()
    )
    if not local_record.data:
        raise HTTPException(status_code=404, detail="Payment not found")

    await _authorize_payment_access(auth, local_record.data, require_admin=False)
    if local_record.data.get("status") == "pago":
        return {"status": "pago", "message": "Payment already confirmed", "request_id": request_id}

    if not ASAAS_API_KEY:
        return {"status": "pending", "message": "Cannot verify remotely without API key", "request_id": request_id}

    headers = {"access_token": ASAAS_API_KEY}
    status_code, payment_payload = await _request_asaas(
        "GET", f"{ASAAS_API_URL}/payments/{payment_id}", headers
    )
    if status_code != 200 or not isinstance(payment_payload, dict):
        raise HTTPException(status_code=502, detail="Error communicating with payment provider")

    provider_status = payment_payload.get("status")
    if provider_status in {"RECEIVED", "CONFIRMED"}:
        await process_payment_confirmation(payment_id)
        inc_counter("pix_verify_confirmed_total")
        return {"status": "pago", "message": "Payment confirmed and subscription activated", "request_id": request_id}
    return {
        "status": str(provider_status).lower(),
        "message": f"Payment status is {provider_status}",
        "request_id": request_id,
    }
