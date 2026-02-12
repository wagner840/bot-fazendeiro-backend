"""
Database functions for transacao (transaction) management.
"""

from typing import List, Dict
from config import supabase
from logging_config import logger


async def registrar_transacao(
    empresa_id: int,
    tipo: str,
    valor: float,
    descricao: str,
    funcionario_id: int = None
) -> bool:
    """Registra uma transação financeira."""
    try:
        await supabase.table('transacoes').insert({
            'empresa_id': empresa_id,
            'tipo': tipo,
            'valor': valor,
            'descricao': descricao,
            'funcionario_id': funcionario_id
        }).execute()
        return True
    except Exception as e:
        logger.error(f"Erro ao registrar transação: {e}")
        return False


async def get_transacoes_empresa(empresa_id: int, limit: int = 50) -> List[Dict]:
    """Obtém transações recentes da empresa."""
    try:
        response = await supabase.table('transacoes').select(
            '*, funcionarios(nome)'
        ).eq('empresa_id', empresa_id).order(
            'data_criacao', desc=True
        ).limit(limit).execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Erro ao buscar transações: {e}")
        return []


async def get_saldo_empresa(empresa_id: int) -> float:
    """Calcula o saldo atual da empresa usando RPC otimizado."""
    try:
        response = await supabase.rpc('calcular_saldo_empresa', {'p_empresa_id': empresa_id}).execute()
        if response.data is not None:
            return float(response.data)
        return 0.0
    except Exception as e:
        logger.warning(f"RPC calcular_saldo_empresa falhou, usando fallback: {e}")
        try:
            response = await supabase.table('transacoes').select('tipo, valor').eq('empresa_id', empresa_id).execute()
            saldo = 0.0
            for t in response.data or []:
                if t['tipo'] == 'entrada':
                    saldo += float(t['valor'])
                else:
                    saldo -= float(t['valor'])
            return saldo
        except Exception as e2:
            logger.error(f"Erro ao calcular saldo (fallback): {e2}")
            return 0.0
