"""
Bot Fazendeiro API — Application setup & middleware.
Endpoints live in api/routes/.
"""
import os
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from logging_config import logger

load_dotenv()

from config import FRONTEND_URL, init_supabase

# ─── App & Rate Limiter ─────────────────────────────────────────────────────

app = FastAPI()

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ─── Startup ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    await init_supabase()
    logger.info("Supabase async client initialized (API).")


# ─── CORS ────────────────────────────────────────────────────────────────────

is_production = FRONTEND_URL != "http://localhost:3000"
origins = [FRONTEND_URL]
if is_production:
    origins.extend([
        "http://fazendabot.einsof7.com",
        "https://fazendabot.einsof7.com",
    ])
else:
    origins.extend([
        "http://localhost:3000",
        "http://localhost:5173",
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "asaas-access-token"],
)


# ─── Security Headers ───────────────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

app.add_middleware(SecurityHeadersMiddleware)


# ─── Routes ──────────────────────────────────────────────────────────────────

from api_pkg.routes.payment import router as payment_router
app.include_router(payment_router)


@app.get("/")
async def root():
    return {"status": "online", "service": "Bot Fazendeiro API (Production)"}
