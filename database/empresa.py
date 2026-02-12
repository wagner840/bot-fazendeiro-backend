"""
Database functions for empresa (company) management.
"""

from typing import Optional, List, Dict
from config import supabase, empresas_cache, servidores_cache
from logging_config import logger
from database.servidor import get_servidor_by_guild, get_or_create_servidor


async def get_tipos_empresa(guild_id: str = None) -> List[Dict]:
    """Obtém todos os tipos de empresa disponíveis para a base do servidor."""
    try:
        base_id = 1  # Default Downtown
        if guild_id:
            servidor = await get_servidor_by_guild(guild_id)
            if servidor:
                base_id = servidor.get('base_redm_id', 1)

        response = await supabase.table('tipos_empresa').select('*').eq('ativo', True).eq('base_redm_id', base_id).order('nome').execute()
        return response.data
    except Exception as e:
        logger.error(f"Erro ao buscar tipos de empresa: {e}")
        return []


async def get_bases_redm() -> List[Dict]:
    """Obtém todas as bases REDM disponíveis (Downtown, Valiria, etc)."""
    try:
        response = await supabase.table('bases_redm').select('*').eq('ativo', True).order('id').execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Erro ao buscar bases REDM: {e}")
        return []


async def atualizar_base_servidor(guild_id: str, base_id: int) -> bool:
    """Atualiza a base REDM de um servidor."""
    try:
        servidor = await get_or_create_servidor(guild_id, f"Guild {guild_id}", "0")
        if not servidor:
            return False

        await supabase.table('servidores').update({
            'base_redm_id': base_id
        }).eq('guild_id', guild_id).execute()

        if guild_id in servidores_cache:
            del servidores_cache[guild_id]

        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar base do servidor: {e}")
        return False


async def get_empresa_by_guild(guild_id: str) -> Optional[Dict]:
    """Obtém a empresa configurada para um servidor Discord."""
    if guild_id in empresas_cache:
        return empresas_cache[guild_id]

    try:
        response = await supabase.table('empresas').select(
            '*, tipos_empresa(*)'
        ).eq('guild_id', guild_id).eq('ativo', True).execute()

        if response.data:
            empresas_cache[guild_id] = response.data[0]
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar empresa: {e}")
        return None


async def get_empresas_by_guild(guild_id: str) -> List[Dict]:
    """Obtém todas as empresas configuradas para um servidor Discord."""
    try:
        response = await supabase.table('empresas').select(
            '*, tipos_empresa(*)'
        ).eq('guild_id', guild_id).eq('ativo', True).order('id').execute()

        return response.data or []
    except Exception as e:
        logger.error(f"Erro ao buscar empresas: {e}")
        return []


async def criar_empresa(
    guild_id: str,
    nome: str,
    tipo_empresa_id: int,
    proprietario_id: str,
    servidor_id: int = None,
    modo_pagamento: str = 'producao',
    categoria_id: str = None,
    canal_principal_id: str = None
) -> Optional[Dict]:
    """Cria uma nova empresa para o servidor."""
    try:
        data = {
            'guild_id': guild_id,
            'nome': nome,
            'tipo_empresa_id': tipo_empresa_id,
            'proprietario_discord_id': proprietario_id,
            'modo_pagamento': modo_pagamento,
            'categoria_id': categoria_id,
            'canal_principal_id': canal_principal_id
        }

        if servidor_id:
            data['servidor_id'] = servidor_id

        response = await supabase.table('empresas').insert(data).execute()

        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Erro ao criar empresa: {e}")
        raise e


async def atualizar_modo_pagamento(empresa_id: int, modo: str) -> bool:
    """Atualiza o modo de pagamento da empresa."""
    try:
        if modo not in ['producao', 'entrega', 'estoque']:
            return False

        await supabase.table('empresas').update({
            'modo_pagamento': modo
        }).eq('id', empresa_id).execute()

        # Invalidar cache para que a próxima leitura busque o valor atualizado
        keys_to_remove = [k for k, v in empresas_cache.items() if isinstance(v, dict) and v.get('id') == empresa_id]
        for k in keys_to_remove:
            del empresas_cache[k]

        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar modo pagamento: {e}")
        return False


async def get_produtos_referencia(tipo_empresa_id: int, guild_id: str = None) -> List[Dict]:
    """Obtém produtos de referência (Globais + Específicos do Servidor)."""
    try:
        query = supabase.table('produtos_referencia').select('*').eq(
            'tipo_empresa_id', tipo_empresa_id
        ).eq('ativo', True)

        if guild_id:
            query = query.or_(f"guild_id.is.null,guild_id.eq.{guild_id}")
        else:
            query = query.is_('guild_id', 'null')

        response = await query.order('categoria', desc=False).order('nome').execute()
        return response.data
    except Exception as e:
        logger.error(f"Erro ao buscar produtos: {e}")
        return []
