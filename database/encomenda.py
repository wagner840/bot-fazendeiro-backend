"""
Database functions for encomenda (order) management.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict
from config import supabase
from logging_config import logger


async def criar_encomenda(empresa_id: int, comprador: str, itens: List[Dict]) -> Optional[Dict]:
    """Cria uma nova encomenda."""
    try:
        valor_total = sum(item.get('valor', 0) for item in itens)

        response = await supabase.table('encomendas').insert({
            'empresa_id': empresa_id,
            'comprador': comprador,
            'itens_json': itens,
            'valor_total': valor_total,
            'status': 'pendente'
        }).execute()

        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Erro ao criar encomenda: {e}")
        return None


async def get_encomendas_pendentes(empresa_id: int) -> List[Dict]:
    """Obtém encomendas pendentes da empresa."""
    try:
        response = await supabase.table('encomendas').select('*').eq(
            'empresa_id', empresa_id
        ).eq('status', 'pendente').order('data_criacao').execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Erro ao buscar encomendas: {e}")
        return []


async def get_encomenda(encomenda_id: int) -> Optional[Dict]:
    """Obtém uma encomenda por ID."""
    try:
        response = await supabase.table('encomendas').select('*').eq('id', encomenda_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Erro ao buscar encomenda: {e}")
        return None


async def atualizar_status_encomenda(encomenda_id: int, status: str, entregador_id: int = None) -> bool:
    """Atualiza o status de uma encomenda."""
    try:
        data = {'status': status}
        if entregador_id:
            data['funcionario_responsavel_id'] = entregador_id
        if status == 'entregue':
            data['data_entrega'] = datetime.now(timezone.utc).isoformat()

        await supabase.table('encomendas').update(data).eq('id', encomenda_id).execute()
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar encomenda: {e}")
        return False
