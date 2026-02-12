"""
Database functions for servidor (tenant) management.
"""

from typing import Optional, Dict
from config import supabase, servidores_cache
from logging_config import logger


async def get_or_create_servidor(guild_id: str, nome: str, proprietario_id: str) -> Optional[Dict]:
    """Obtém ou cria um registro de servidor (tenant)."""
    if guild_id in servidores_cache:
        return servidores_cache[guild_id]

    try:
        response = await supabase.table('servidores').select('*').eq('guild_id', guild_id).execute()

        if response.data:
            servidores_cache[guild_id] = response.data[0]
            return response.data[0]

        response = await supabase.table('servidores').insert({
            'guild_id': guild_id,
            'nome': nome,
            'proprietario_discord_id': proprietario_id,
            'ativo': True
        }).execute()

        if response.data:
            servidores_cache[guild_id] = response.data[0]
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Erro ao obter/criar servidor: {e}")
        return None


async def get_servidor_by_guild(guild_id: str) -> Optional[Dict]:
    """Obtém servidor por guild_id."""
    if guild_id in servidores_cache:
        return servidores_cache[guild_id]

    try:
        response = await supabase.table('servidores').select('*').eq('guild_id', guild_id).execute()
        if response.data:
            servidores_cache[guild_id] = response.data[0]
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar servidor: {e}")
        return None
