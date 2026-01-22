"""
Testes das funcoes do banco de dados
Simula as operacoes que o bot faz
"""

import asyncio
import sys
import os
from decimal import Decimal
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import supabase
from database import (
    get_servidor_by_guild,
    get_empresas_by_guild,
    get_produtos_empresa,
    get_funcionario_by_discord_id,
    get_estoque_funcionario,
    get_produtos_referencia
)

# ============================================
# CORES
# ============================================
class Colors:
    OK = '\033[92m'
    FAIL = '\033[91m'
    WARN = '\033[93m'
    INFO = '\033[94m'
    END = '\033[0m'

def ok(msg): print(f"{Colors.OK}[OK]{Colors.END} {msg}")
def fail(msg): print(f"{Colors.FAIL}[FALHOU]{Colors.END} {msg}")
def warn(msg): print(f"{Colors.WARN}[AVISO]{Colors.END} {msg}")
def info(msg): print(f"{Colors.INFO}[INFO]{Colors.END} {msg}")

# ============================================
# DADOS DE TESTE
# ============================================
TEST_GUILD_ID = "1450699474526671002"  # ID do servidor de teste
TEST_DISCORD_ID = "306217606082199555"  # ID do usuario de teste

# ============================================
# TESTES
# ============================================

async def test_get_servidor():
    """Testa funcao get_servidor_by_guild"""
    print("\n" + "="*50)
    print("TESTE: get_servidor_by_guild")
    print("="*50)

    servidor = await get_servidor_by_guild(TEST_GUILD_ID)

    if servidor:
        ok(f"Servidor encontrado: {servidor['nome']}")
        info(f"  ID: {servidor['id']}")
        info(f"  Guild: {servidor['guild_id']}")
        return True
    else:
        fail("Servidor nao encontrado")
        return False


async def test_get_empresas():
    """Testa funcao get_empresas_by_guild"""
    print("\n" + "="*50)
    print("TESTE: get_empresas_by_guild")
    print("="*50)

    empresas = await get_empresas_by_guild(TEST_GUILD_ID)

    if empresas:
        ok(f"{len(empresas)} empresa(s) encontrada(s)")
        for emp in empresas:
            info(f"  - {emp['nome']} (ID: {emp['id']})")
        return empresas[0]
    else:
        fail("Nenhuma empresa encontrada")
        return None


async def test_get_produtos_empresa(empresa_id):
    """Testa funcao get_produtos_empresa"""
    print("\n" + "="*50)
    print("TESTE: get_produtos_empresa")
    print("="*50)

    produtos = await get_produtos_empresa(empresa_id)

    if produtos:
        ok(f"{len(produtos)} produto(s) encontrado(s)")
        for codigo, p in list(produtos.items())[:3]:
            nome = p['produtos_referencia']['nome']
            venda = float(p['preco_venda'])
            func = float(p['preco_pagamento_funcionario'])
            info(f"  - {codigo}: {nome} (Venda: R${venda:.2f}, Func: R${func:.2f})")
        return True
    else:
        fail("Nenhum produto encontrado")
        return False


async def test_get_funcionario():
    """Testa funcao get_funcionario_by_discord_id"""
    print("\n" + "="*50)
    print("TESTE: get_funcionario_by_discord_id")
    print("="*50)

    func = await get_funcionario_by_discord_id(TEST_DISCORD_ID)

    if func:
        ok(f"Funcionario encontrado: {func['nome']}")
        info(f"  ID: {func['id']}")
        info(f"  Saldo: R$ {float(func['saldo']):.2f}")
        return func
    else:
        fail("Funcionario nao encontrado")
        return None


async def test_get_estoque(func_id, empresa_id):
    """Testa funcao get_estoque_funcionario"""
    print("\n" + "="*50)
    print("TESTE: get_estoque_funcionario")
    print("="*50)

    estoque = await get_estoque_funcionario(func_id, empresa_id)

    if estoque:
        ok(f"{len(estoque)} item(ns) no estoque")
        for item in estoque[:3]:
            info(f"  - {item['produto_codigo']}: {item['quantidade']}x")
    else:
        info("Estoque vazio (normal se foi pago)")

    return True


async def test_get_produtos_referencia(tipo_empresa_id):
    """Testa funcao get_produtos_referencia"""
    print("\n" + "="*50)
    print("TESTE: get_produtos_referencia")
    print("="*50)

    produtos = await get_produtos_referencia(tipo_empresa_id)

    if produtos:
        ok(f"{len(produtos)} produto(s) de referencia")
        for p in produtos[:3]:
            info(f"  - {p['codigo']}: {p['nome']} (R${float(p['preco_minimo']):.2f} - R${float(p['preco_maximo']):.2f})")
        return True
    else:
        fail("Nenhum produto de referencia encontrado")
        return False


async def test_operacoes_estoque(func_id, empresa_id, produto_codigo):
    """Testa operacoes de adicionar e remover do estoque"""
    print("\n" + "="*50)
    print("TESTE: Operacoes de Estoque")
    print("="*50)

    # Adicionar ao estoque
    info("Adicionando 10 itens ao estoque...")

    # Verifica se ja existe
    existing = supabase.table('estoque_produtos').select('*').eq(
        'funcionario_id', func_id
    ).eq('empresa_id', empresa_id).eq('produto_codigo', produto_codigo).execute()

    if existing.data:
        # Atualiza quantidade
        nova_qtd = existing.data[0]['quantidade'] + 10
        supabase.table('estoque_produtos').update({
            'quantidade': nova_qtd
        }).eq('id', existing.data[0]['id']).execute()
        ok(f"Estoque atualizado: {nova_qtd} itens")
    else:
        # Insere novo
        supabase.table('estoque_produtos').insert({
            'funcionario_id': func_id,
            'empresa_id': empresa_id,
            'produto_codigo': produto_codigo,
            'quantidade': 10
        }).execute()
        ok("10 itens adicionados ao estoque")

    # Verifica
    estoque = supabase.table('estoque_produtos').select('*').eq(
        'funcionario_id', func_id
    ).eq('empresa_id', empresa_id).eq('produto_codigo', produto_codigo).execute()

    if estoque.data:
        ok(f"Estoque atual: {estoque.data[0]['quantidade']} {produto_codigo}")

    # Remove do estoque
    info("Removendo 5 itens...")
    nova_qtd = estoque.data[0]['quantidade'] - 5
    supabase.table('estoque_produtos').update({
        'quantidade': nova_qtd
    }).eq('id', estoque.data[0]['id']).execute()
    ok(f"Estoque apos remocao: {nova_qtd} itens")

    return True


async def test_criar_encomenda(empresa_id, func_id):
    """Testa criacao de encomenda"""
    print("\n" + "="*50)
    print("TESTE: Criar Encomenda")
    print("="*50)

    itens_json = [{
        'codigo': 'rotulo',
        'nome': 'Rotulo (Teste)',
        'quantidade': 5,
        'quantidade_entregue': 0,
        'valor_unitario': 0.55
    }]

    response = supabase.table('encomendas').insert({
        'comprador': 'Cliente Teste',
        'itens_json': itens_json,
        'valor_total': 2.75,
        'status': 'pendente',
        'funcionario_responsavel_id': func_id,
        'empresa_id': empresa_id
    }).execute()

    if response.data:
        ok(f"Encomenda criada: #{response.data[0]['id']}")
        return response.data[0]['id']
    else:
        fail("Falha ao criar encomenda")
        return None


async def test_entregar_encomenda(encomenda_id):
    """Testa entrega de encomenda"""
    print("\n" + "="*50)
    print("TESTE: Entregar Encomenda")
    print("="*50)

    response = supabase.table('encomendas').update({
        'status': 'entregue',
        'data_entrega': datetime.utcnow().isoformat()
    }).eq('id', encomenda_id).execute()

    if response.data:
        ok(f"Encomenda #{encomenda_id} entregue")
        return True
    else:
        fail("Falha ao entregar encomenda")
        return False


async def test_registrar_pagamento(func_id, valor):
    """Testa registro de pagamento"""
    print("\n" + "="*50)
    print("TESTE: Registrar Pagamento")
    print("="*50)

    response = supabase.table('historico_pagamentos').insert({
        'funcionario_id': func_id,
        'tipo': 'producao',
        'valor': float(valor),
        'descricao': 'Pagamento de teste automatizado'
    }).execute()

    if response.data:
        ok(f"Pagamento registrado: R$ {valor:.2f}")
        return True
    else:
        fail("Falha ao registrar pagamento")
        return False


async def test_transacao(empresa_id, func_id, valor):
    """Testa registro de transacao"""
    print("\n" + "="*50)
    print("TESTE: Registrar Transacao")
    print("="*50)

    response = supabase.table('transacoes').insert({
        'empresa_id': empresa_id,
        'funcionario_id': func_id,
        'tipo': 'comissao_pendente',
        'valor': float(valor),
        'descricao': 'Comissao de teste',
        'status': 'pendente'
    }).execute()

    if response.data:
        ok(f"Transacao registrada: R$ {valor:.2f}")
        return response.data[0]['id']
    else:
        fail("Falha ao registrar transacao")
        return None


async def cleanup_testes(encomenda_id=None, transacao_id=None):
    """Limpa dados de teste"""
    print("\n" + "="*50)
    print("LIMPEZA: Removendo dados de teste")
    print("="*50)

    # Remove encomenda de teste
    if encomenda_id:
        supabase.table('encomendas').delete().eq('id', encomenda_id).execute()
        info(f"Encomenda #{encomenda_id} removida")

    # Remove transacao de teste
    if transacao_id:
        supabase.table('transacoes').delete().eq('id', transacao_id).execute()
        info(f"Transacao #{transacao_id} removida")

    # Limpa estoque de teste
    supabase.table('estoque_produtos').delete().eq('produto_codigo', 'rotulo').execute()
    info("Estoque de teste limpo")

    ok("Limpeza concluida")


async def run_all_tests():
    """Executa todos os testes"""
    print("\n" + "="*60)
    print("   TESTES DE FUNCOES - BOT FAZENDEIRO")
    print("   " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)

    resultados = []
    encomenda_id = None
    transacao_id = None

    try:
        # Testes basicos
        r = await test_get_servidor()
        resultados.append(("get_servidor_by_guild", r))

        empresa = await test_get_empresas()
        resultados.append(("get_empresas_by_guild", empresa is not None))

        if empresa:
            r = await test_get_produtos_empresa(empresa['id'])
            resultados.append(("get_produtos_empresa", r))

            r = await test_get_produtos_referencia(empresa['tipo_empresa_id'])
            resultados.append(("get_produtos_referencia", r))

        func = await test_get_funcionario()
        resultados.append(("get_funcionario_by_discord_id", func is not None))

        if func and empresa:
            r = await test_get_estoque(func['id'], empresa['id'])
            resultados.append(("get_estoque_funcionario", r))

            # Testes de operacoes
            r = await test_operacoes_estoque(func['id'], empresa['id'], 'rotulo')
            resultados.append(("operacoes_estoque", r))

            encomenda_id = await test_criar_encomenda(empresa['id'], func['id'])
            resultados.append(("criar_encomenda", encomenda_id is not None))

            if encomenda_id:
                r = await test_entregar_encomenda(encomenda_id)
                resultados.append(("entregar_encomenda", r))

            r = await test_registrar_pagamento(func['id'], Decimal('10.00'))
            resultados.append(("registrar_pagamento", r))

            transacao_id = await test_transacao(empresa['id'], func['id'], Decimal('5.00'))
            resultados.append(("registrar_transacao", transacao_id is not None))

    finally:
        # Limpa dados de teste
        await cleanup_testes(encomenda_id, transacao_id)

    # Resumo
    print("\n" + "="*60)
    print("   RESUMO DOS TESTES DE FUNCOES")
    print("="*60)

    passou = sum(1 for _, r in resultados if r)
    falhou = sum(1 for _, r in resultados if not r)

    for nome, resultado in resultados:
        status = f"{Colors.OK}PASSOU{Colors.END}" if resultado else f"{Colors.FAIL}FALHOU{Colors.END}"
        print(f"  {nome}: {status}")

    print("\n" + "-"*60)
    print(f"  Total: {len(resultados)} | Passou: {passou} | Falhou: {falhou}")
    print("="*60 + "\n")

    return falhou == 0


if __name__ == '__main__':
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
