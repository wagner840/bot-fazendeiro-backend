"""
Bot Fazendeiro API — Application setup & middleware.
Endpoints live in api/routes/.
"""
import os
import uuid
import time
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from logging_config import logger

load_dotenv()

from config import FRONTEND_URL, init_supabase
from api_pkg.rate_limit import limiter
from api_pkg.observability import inc_counter, observe_histogram, render_metrics

# ─── App & Rate Limiter ─────────────────────────────────────────────────────

app = FastAPI()

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
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Request-ID"] = request_id
        return response

app.add_middleware(SecurityHeadersMiddleware)


class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        route_path = request.url.path
        labels = {
            "method": request.method,
            "path": route_path,
            "status": str(response.status_code),
        }
        inc_counter("api_requests_total", labels=labels)
        observe_histogram("api_request_duration_seconds", duration, labels=labels)
        logger.info(
            "request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
            getattr(request.state, "request_id", "n/a"),
            request.method,
            route_path,
            response.status_code,
            duration * 1000,
        )
        return response


app.add_middleware(RequestObservabilityMiddleware)


# ─── Routes ──────────────────────────────────────────────────────────────────

from api_pkg.routes.payment import router as payment_router
app.include_router(payment_router)


@app.get("/")
async def root():
    return {"status": "online", "service": "Bot Fazendeiro API (Production)"}


@app.get("/metrics")
async def metrics():
    return Response(content=render_metrics(), media_type="text/plain; version=0.0.4")
