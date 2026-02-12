"""
Database functions for tester management.
"""

from typing import List, Dict
from config import supabase
from logging_config import logger


async def adicionar_tester(guild_id: str, nome: str = None, adicionado_por: str = None, motivo: str = None) -> bool:
    """Adiciona um servidor como tester (acesso gratuito)."""
    try:
        response = await supabase.table('testers').upsert({
            'guild_id': guild_id,
            'nome': nome,
            'adicionado_por': adicionado_por,
            'motivo': motivo,
            'ativo': True
        }).execute()
        return bool(response.data)
    except Exception as e:
        logger.error(f"Erro ao adicionar tester: {e}")
        return False


async def remover_tester(guild_id: str) -> bool:
    """Remove um servidor da lista de testers."""
    try:
        await supabase.table('testers').update({
            'ativo': False
        }).eq('guild_id', guild_id).execute()
        return True
    except Exception as e:
        logger.error(f"Erro ao remover tester: {e}")
        return False


async def verificar_tester(guild_id: str) -> bool:
    """Verifica se um servidor é tester."""
    try:
        response = await supabase.rpc('verificar_tester', {'p_guild_id': guild_id}).execute()
        return response.data == True
    except Exception as e:
        logger.error(f"Erro ao verificar tester: {e}")
        return False


async def listar_testers() -> List[Dict]:
    """Lista todos os testers ativos."""
    try:
        response = await supabase.table('testers').select('*').eq('ativo', True).execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Erro ao listar testers: {e}")
        return []


async def simular_pagamento(guild_id: str) -> bool:
    """Simula um pagamento para testes (ativa assinatura do pagamento pendente mais recente)."""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://rgopdilceawaqrgaoaca.supabase.co/functions/v1/simulate-payment',
                json={'guild_id': guild_id},
                headers={'Content-Type': 'application/json'}
            ) as response:
                return response.status == 200
    except Exception as e:
        logger.error(f"Erro ao simular pagamento: {e}")
        return False
