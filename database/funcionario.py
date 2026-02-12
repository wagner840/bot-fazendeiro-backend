"""
Database functions for funcionario (employee) management.
"""

from typing import Optional, List, Dict
from config import supabase
from logging_config import logger


async def vincular_funcionario_empresa(funcionario_id: int, empresa_id: int) -> bool:
    """Vincula funcionário a uma empresa na tabela N:N."""
    try:
        existing = await supabase.table('funcionario_empresa').select('id').eq(
            'funcionario_id', funcionario_id
        ).eq('empresa_id', empresa_id).execute()

        if existing.data:
            await supabase.table('funcionario_empresa').update({
                'ativo': True
            }).eq('id', existing.data[0]['id']).execute()
            return True

        await supabase.table('funcionario_empresa').insert({
            'funcionario_id': funcionario_id,
            'empresa_id': empresa_id,
            'ativo': True
        }).execute()

        return True
    except Exception as e:
        logger.error(f"Erro ao vincular funcionário-empresa: {e}")
        return False


async def get_or_create_funcionario(discord_id: str, nome: str, empresa_id: int = None) -> Optional[int]:
    """Obtém ou cria um funcionário."""
    try:
        response = await supabase.table('funcionarios').select('id, empresa_id').eq('discord_id', discord_id).execute()

        if response.data:
            func_id = response.data[0]['id']
            if empresa_id and response.data[0].get('empresa_id') != empresa_id:
                await supabase.table('funcionarios').update({'empresa_id': empresa_id}).eq('id', func_id).execute()
            if empresa_id:
                await vincular_funcionario_empresa(func_id, empresa_id)
            return func_id

        response = await supabase.table('funcionarios').insert({
            'discord_id': discord_id,
            'nome': nome,
            'empresa_id': empresa_id
        }).execute()

        func_id = response.data[0]['id'] if response.data else None

        if func_id and empresa_id:
            await vincular_funcionario_empresa(func_id, empresa_id)

        return func_id
    except Exception as e:
        logger.error(f"Erro ao obter/criar funcionário: {e}")
        return None


async def get_funcionario_by_discord_id(discord_id: str) -> Optional[Dict]:
    """Obtém dados do funcionário."""
    try:
        response = await supabase.table('funcionarios').select('*').eq('discord_id', discord_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Erro ao buscar funcionário: {e}")
        return None


async def get_funcionarios_empresa(empresa_id: int) -> List[Dict]:
    """Obtém todos os funcionários vinculados a uma empresa."""
    try:
        response = await supabase.table('funcionario_empresa').select(
            '*, funcionarios(*)'
        ).eq('empresa_id', empresa_id).eq('ativo', True).execute()

        return [item['funcionarios'] for item in response.data if item.get('funcionarios')]
    except Exception as e:
        logger.error(f"Erro ao buscar funcionários da empresa: {e}")
        return []


async def atualizar_canal_funcionario(funcionario_id: int, channel_id: str) -> bool:
    """Atualiza o channel_id do funcionário."""
    try:
        await supabase.table('funcionarios').update({
            'channel_id': channel_id
        }).eq('id', funcionario_id).execute()
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar channel_id: {e}")
        return False
