"""
Database functions for assinatura (subscription) and payment management.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict
from config import supabase
from logging_config import logger


async def verificar_assinatura_servidor(guild_id: str) -> dict:
    """Verifica se servidor tem assinatura ativa."""
    try:
        response = await supabase.rpc('verificar_assinatura', {'p_guild_id': guild_id}).execute()

        if response.data and len(response.data) > 0:
            return response.data[0]

        return {
            'ativa': False,
            'status': None,
            'dias_restantes': 0,
            'data_expiracao': None,
            'plano_nome': None,
            'tipo': None
        }
    except Exception as e:
        logger.error(f"Erro ao verificar assinatura: {e}")
        return {'ativa': False, 'status': 'erro', 'dias_restantes': 0, 'tipo': None}


async def get_assinatura_servidor(guild_id: str) -> Optional[Dict]:
    """Obtém dados completos da assinatura do servidor."""
    try:
        response = await supabase.table('assinaturas').select(
            '*, planos(*)'
        ).eq('guild_id', guild_id).execute()

        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar assinatura: {e}")
        return None


async def get_planos_disponiveis() -> List[Dict]:
    """Obtém todos os planos disponíveis."""
    try:
        response = await supabase.table('planos').select('*').eq('ativo', True).order('preco').execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Erro ao buscar planos: {e}")
        return []


async def criar_pagamento_pix(guild_id: str, plano_id: int, valor: float) -> Optional[Dict]:
    """Cria um registro de pagamento PIX pendente."""
    try:
        response = await supabase.table('pagamentos_pix').insert({
            'guild_id': guild_id,
            'plano_id': plano_id,
            'valor': valor,
            'status': 'pendente',
            'pix_expiracao': (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
        }).execute()

        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Erro ao criar pagamento PIX: {e}")
        return None


async def buscar_pagamento_pendente_usuario(discord_id: str) -> Optional[Dict]:
    """Busca pagamento mais recente do usuário (pendente ou pago)."""
    try:
        response = await supabase.table('pagamentos_pix').select('*').eq(
            'discord_id', discord_id
        ).in_('status', ['pendente', 'pago']).order('created_at', desc=True).limit(1).execute()

        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Erro ao buscar pagamento usuário: {e}")
        return None


async def atualizar_pagamento_guild(pix_id: str, guild_id: str) -> bool:
    """Atualiza a guild_id de um pagamento."""
    try:
        await supabase.table('pagamentos_pix').update({
            'guild_id': guild_id
        }).eq('pix_id', pix_id).execute()
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar guild do pagamento: {e}")
        return False


async def ativar_assinatura_servidor(guild_id: str, plano_id: int, pagador_discord_id: str = None) -> bool:
    """Ativa assinatura do servidor após pagamento confirmado."""
    try:
        response = await supabase.rpc('ativar_assinatura', {
            'p_guild_id': guild_id,
            'p_plano_id': plano_id,
            'p_pagador_discord_id': pagador_discord_id
        }).execute()

        return response.data == True
    except Exception as e:
        logger.error(f"Erro ao ativar assinatura: {e}")
        return False
