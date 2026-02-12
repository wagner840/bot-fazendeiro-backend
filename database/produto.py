"""
Database functions for product management.
"""

from typing import Optional, Dict
from config import supabase
from logging_config import logger


async def get_produtos_empresa(empresa_id: int) -> Dict[str, Dict]:
    """Obtém produtos configurados para a empresa."""
    try:
        response = await supabase.table('produtos_empresa').select(
            '*, produtos_referencia(*)'
        ).eq('empresa_id', empresa_id).eq('ativo', True).execute()

        return {p['produtos_referencia']['codigo']: p for p in response.data}
    except Exception as e:
        logger.error(f"Erro ao buscar produtos da empresa: {e}")
        return {}


async def criar_produto_referencia_custom(
    tipo_empresa_id: int,
    nome: str,
    codigo: str,
    categoria: str,
    guild_id: str,
    consumivel: bool = True
) -> Optional[Dict]:
    """Cria um produto de referência customizado para o servidor."""
    try:
        data = {
            'tipo_empresa_id': tipo_empresa_id,
            'nome': nome,
            'codigo': codigo.lower(),
            'categoria': categoria,
            'guild_id': guild_id,
            'consumivel': consumivel,
            'ativo': True
        }

        response = await supabase.table('produtos_referencia').insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Erro ao criar produto custom: {e}")
        return None


async def configurar_produto_empresa(empresa_id: int, produto_ref_id: int, preco_venda: float, preco_funcionario: float) -> bool:
    """Configura um produto para a empresa."""
    try:
        existing = await supabase.table('produtos_empresa').select('id').eq(
            'empresa_id', empresa_id
        ).eq('produto_referencia_id', produto_ref_id).execute()

        if existing.data:
            await supabase.table('produtos_empresa').update({
                'preco_venda': preco_venda,
                'preco_pagamento_funcionario': preco_funcionario,
                'ativo': True
            }).eq('id', existing.data[0]['id']).execute()
        else:
            await supabase.table('produtos_empresa').insert({
                'empresa_id': empresa_id,
                'produto_referencia_id': produto_ref_id,
                'preco_venda': preco_venda,
                'preco_pagamento_funcionario': preco_funcionario
            }).execute()
        return True
    except Exception as e:
        logger.error(f"Erro ao configurar produto: {e}")
        return False
