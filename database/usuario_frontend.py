"""
Database functions for frontend user management.
"""

from typing import Optional, List, Dict
from config import supabase
from logging_config import logger


async def criar_usuario_frontend(
    discord_id: str,
    guild_id: str,
    nome: str,
    role: str = 'funcionario'
) -> Optional[Dict]:
    """Cria ou atualiza usuário com acesso ao frontend."""
    try:
        existing = await supabase.table('usuarios_frontend').select('*').eq(
            'discord_id', discord_id
        ).eq('guild_id', guild_id).execute()

        if existing.data:
            response = await supabase.table('usuarios_frontend').update({
                'nome': nome,
                'ativo': True
            }).eq('id', existing.data[0]['id']).execute()
            return response.data[0] if response.data else existing.data[0]

        response = await supabase.table('usuarios_frontend').insert({
            'discord_id': discord_id,
            'guild_id': guild_id,
            'nome': nome,
            'role': role,
            'ativo': True
        }).execute()

        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Erro ao criar usuário frontend: {e}")
        return None


async def get_usuario_frontend(discord_id: str, guild_id: str) -> Optional[Dict]:
    """Obtém usuário frontend por discord_id e guild_id."""
    try:
        response = await supabase.table('usuarios_frontend').select('*').eq(
            'discord_id', discord_id
        ).eq('guild_id', guild_id).eq('ativo', True).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Erro ao buscar usuário frontend: {e}")
        return None


async def get_usuarios_frontend_by_guild(guild_id: str) -> List[Dict]:
    """Obtém todos os usuários frontend de um servidor."""
    try:
        response = await supabase.table('usuarios_frontend').select('*').eq(
            'guild_id', guild_id
        ).eq('ativo', True).execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Erro ao buscar usuários frontend: {e}")
        return []


async def atualizar_role_usuario_frontend(usuario_id: int, role: str) -> bool:
    """Atualiza a role de um usuário frontend."""
    try:
        await supabase.table('usuarios_frontend').update({'role': role}).eq('id', usuario_id).execute()
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar role: {e}")
        return False


async def desativar_usuario_frontend(usuario_id: int) -> bool:
    """Desativa um usuário frontend."""
    try:
        await supabase.table('usuarios_frontend').update({'ativo': False}).eq('id', usuario_id).execute()
        return True
    except Exception as e:
        logger.error(f"Erro ao desativar usuário: {e}")
        return False
