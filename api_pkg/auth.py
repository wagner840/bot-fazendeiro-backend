"""Authentication and tenant authorization helpers for API routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import aiohttp
from fastapi import Header, HTTPException

from config import KEY_TO_USE, SUPABASE_KEY, SUPABASE_URL, supabase


@dataclass
class AuthContext:
    user_id: str
    discord_id: str
    email: Optional[str]
    raw_user: dict[str, Any]
    is_superadmin: bool = False


def _extract_discord_id(user_data: dict[str, Any]) -> Optional[str]:
    metadata = user_data.get("user_metadata") or {}
    discord_id = metadata.get("provider_id")
    if discord_id:
        return str(discord_id)

    identities = user_data.get("identities") or []
    for identity in identities:
        if identity.get("provider") == "discord" and identity.get("id"):
            return str(identity["id"])
    return None


async def _fetch_user_from_token(access_token: str) -> dict[str, Any]:
    api_key = SUPABASE_KEY or KEY_TO_USE
    if not SUPABASE_URL or not api_key:
        raise HTTPException(status_code=500, detail="Supabase Auth not configured")

    url = f"{SUPABASE_URL}/auth/v1/user"
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {access_token}",
    }

    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                raise HTTPException(status_code=401, detail="Invalid or expired token")
            return await response.json()


async def _check_superadmin(discord_id: str) -> bool:
    response = await (
        supabase.table("usuarios_frontend")
        .select("id")
        .eq("discord_id", discord_id)
        .eq("role", "superadmin")
        .eq("ativo", True)
        .limit(1)
        .execute()
    )
    return bool(response.data)


async def require_auth_context(authorization: Optional[str] = Header(None)) -> AuthContext:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization bearer token is required")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Authorization bearer token is required")

    user_data = await _fetch_user_from_token(token)
    discord_id = _extract_discord_id(user_data)
    if not discord_id:
        raise HTTPException(status_code=403, detail="Discord identity not found in session")

    is_superadmin = await _check_superadmin(discord_id)
    return AuthContext(
        user_id=str(user_data.get("id", "")),
        discord_id=discord_id,
        email=user_data.get("email"),
        raw_user=user_data,
        is_superadmin=is_superadmin,
    )


async def get_guild_access(discord_id: str, guild_id: str) -> Optional[dict[str, Any]]:
    response = await (
        supabase.table("usuarios_frontend")
        .select("id, role, guild_id, ativo")
        .eq("discord_id", discord_id)
        .eq("guild_id", guild_id)
        .eq("ativo", True)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None
