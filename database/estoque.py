"""
Database functions for estoque (inventory) management.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict
from config import supabase
from logging_config import logger
from database.produto import get_produtos_empresa


async def adicionar_ao_estoque(funcionario_id: int, empresa_id: int, codigo: str, quantidade: int) -> Optional[Dict]:
    """Adiciona produtos ao estoque do funcionário usando upsert atômico."""
    try:
        produtos = await get_produtos_empresa(empresa_id)
        if codigo.lower() not in produtos:
            return None

        produto = produtos[codigo.lower()]
        codigo_limpo = codigo.lower()

        response = await supabase.rpc('upsert_estoque', {
            'p_funcionario_id': funcionario_id,
            'p_empresa_id': empresa_id,
            'p_produto_codigo': codigo_limpo,
            'p_quantidade': quantidade
        }).execute()
        final_qtd = response.data if response.data is not None else quantidade

        return {'quantidade': final_qtd, 'nome': produto['produtos_referencia']['nome']}
    except Exception as e:
        logger.error(f"Erro ao adicionar estoque: {e}")
        return None


async def remover_do_estoque(funcionario_id: int, empresa_id: int, codigo: str, quantidade: int) -> Optional[Dict]:
    """Remove produtos do estoque."""
    try:
        produtos = await get_produtos_empresa(empresa_id)
        if codigo.lower() not in produtos:
            return {'erro': 'Produto não encontrado'}

        produto = produtos[codigo.lower()]

        estoque = await supabase.table('estoque_produtos').select('*').eq(
            'funcionario_id', funcionario_id
        ).eq('produto_codigo', codigo.lower()).eq('empresa_id', empresa_id).execute()

        if not estoque.data:
            return {'erro': 'Produto não encontrado no estoque'}

        atual = estoque.data[0]['quantidade']
        nome = produto['produtos_referencia']['nome']

        if quantidade > atual:
            return {'erro': f'Quantidade insuficiente. Você tem {atual} {nome}'}

        nova_qtd = atual - quantidade

        if nova_qtd == 0:
            await supabase.table('estoque_produtos').delete().eq('id', estoque.data[0]['id']).execute()
        else:
            await supabase.table('estoque_produtos').update({
                'quantidade': nova_qtd,
                'data_atualizacao': datetime.now(timezone.utc).isoformat()
            }).eq('id', estoque.data[0]['id']).execute()

        return {'quantidade': nova_qtd, 'nome': nome, 'removido': quantidade}
    except Exception as e:
        logger.error(f"Erro ao remover estoque: {e}")
        return None


async def get_estoque_funcionario(funcionario_id: int, empresa_id: int) -> List[Dict]:
    """Obtém estoque do funcionário."""
    try:
        produtos = await get_produtos_empresa(empresa_id)

        response = await supabase.table('estoque_produtos').select('*').eq(
            'funcionario_id', funcionario_id
        ).eq('empresa_id', empresa_id).gt('quantidade', 0).execute()

        result = []
        for item in response.data:
            codigo = item['produto_codigo']
            if codigo in produtos:
                prod = produtos[codigo]
                result.append({
                    **item,
                    'nome': prod['produtos_referencia']['nome'],
                    'preco_venda': prod['preco_venda'],
                    'preco_funcionario': prod['preco_pagamento_funcionario']
                })
        return result
    except Exception as e:
        logger.error(f"Erro ao buscar estoque: {e}")
        return []


async def get_estoque_global(empresa_id: int) -> List[Dict]:
    """Obtém estoque global da empresa."""
    try:
        produtos = await get_produtos_empresa(empresa_id)

        response = await supabase.table('estoque_produtos').select('*').eq(
            'empresa_id', empresa_id
        ).gt('quantidade', 0).execute()

        totais = {}
        for item in response.data:
            codigo = item['produto_codigo']
            if codigo not in totais:
                nome = produtos.get(codigo, {}).get('produtos_referencia', {}).get('nome', codigo)
                totais[codigo] = {'codigo': codigo, 'nome': nome, 'quantidade': 0}
            totais[codigo]['quantidade'] += item['quantidade']

        return list(totais.values())
    except Exception as e:
        logger.error(f"Erro ao buscar estoque global: {e}")
        return []


async def get_estoque_global_detalhado(empresa_id: int) -> Dict:
    """
    Obtém estoque global detalhado da empresa com informações de preço.
    Retorna dict com código como chave e informações completas.
    """
    try:
        produtos = await get_produtos_empresa(empresa_id)

        response = await supabase.table('estoque_produtos').select('*').eq(
            'empresa_id', empresa_id
        ).gt('quantidade', 0).execute()

        totais = {}
        for item in response.data:
            codigo = item['produto_codigo']
            if codigo not in totais:
                prod_info = produtos.get(codigo, {})
                nome = prod_info.get('produtos_referencia', {}).get('nome', codigo)
                preco_func = prod_info.get('preco_pagamento_funcionario', 0)
                totais[codigo] = {
                    'codigo': codigo,
                    'nome': nome,
                    'quantidade': 0,
                    'preco_funcionario': preco_func,
                    'registros': []
                }
            totais[codigo]['quantidade'] += item['quantidade']
            totais[codigo]['registros'].append({
                'id': item['id'],
                'funcionario_id': item['funcionario_id'],
                'quantidade': item['quantidade']
            })

        return totais
    except Exception as e:
        logger.error(f"Erro ao buscar estoque global detalhado: {e}")
        return {}


async def remover_do_estoque_global(empresa_id: int, codigo: str, quantidade: int) -> Optional[Dict]:
    """
    Remove quantidade do estoque global (de qualquer funcionário que tenha).
    Usado no modo de pagamento 'entrega' onde o vendedor não precisa ter produzido.
    Remove dos funcionários na ordem em que têm estoque (FIFO por ID).
    Retorna informações do item removido incluindo preço para cálculo de comissão.
    """
    try:
        produtos = await get_produtos_empresa(empresa_id)

        if codigo.lower() not in produtos:
            return {'erro': 'Produto não encontrado'}

        produto = produtos[codigo.lower()]
        nome = produto['produtos_referencia']['nome']
        preco_funcionario = produto['preco_pagamento_funcionario']

        response = await supabase.table('estoque_produtos').select('*').eq(
            'empresa_id', empresa_id
        ).eq('produto_codigo', codigo.lower()).gt('quantidade', 0).order('id').execute()

        if not response.data:
            return {'erro': f'Produto {nome} não encontrado no estoque global'}

        total_disponivel = sum(item['quantidade'] for item in response.data)

        if quantidade > total_disponivel:
            return {'erro': f'Quantidade insuficiente no estoque global. Disponível: {total_disponivel} {nome}'}

        quantidade_restante = quantidade
        for item in response.data:
            if quantidade_restante <= 0:
                break

            disponivel_neste = item['quantidade']
            a_remover = min(quantidade_restante, disponivel_neste)
            nova_qtd = disponivel_neste - a_remover

            if nova_qtd == 0:
                await supabase.table('estoque_produtos').delete().eq('id', item['id']).execute()
            else:
                await supabase.table('estoque_produtos').update({
                    'quantidade': nova_qtd,
                    'data_atualizacao': datetime.now(timezone.utc).isoformat()
                }).eq('id', item['id']).execute()

            quantidade_restante -= a_remover

        return {
            'quantidade': total_disponivel - quantidade,
            'nome': nome,
            'removido': quantidade,
            'preco_funcionario': preco_funcionario
        }
    except Exception as e:
        logger.error(f"Erro ao remover do estoque global: {e}")
        return None


async def zerar_estoque_funcionario(funcionario_id: int, empresa_id: int) -> bool:
    """Zera todo o estoque de um funcionário."""
    try:
        await supabase.table('estoque_produtos').delete().eq(
            'funcionario_id', funcionario_id
        ).eq('empresa_id', empresa_id).execute()
        return True
    except Exception as e:
        logger.error(f"Erro ao zerar estoque: {e}")
        return False
