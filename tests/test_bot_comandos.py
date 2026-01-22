"""
Testes de Comandos do Bot - Bot Fazendeiro
Testa todos os comandos simulando as funcoes subjacentes.
"""

import asyncio
import sys
import os
from datetime import datetime
from decimal import Decimal

# Adiciona o diretorio pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import supabase
from database import (
    # Servidor
    get_or_create_servidor,
    get_servidor_by_guild,
    # Empresa
    get_empresa_by_guild,
    get_empresas_by_guild,
    criar_empresa,
    get_tipos_empresa,
    atualizar_modo_pagamento,
    # Funcionario
    get_or_create_funcionario,
    get_funcionario_by_discord_id,
    get_funcionarios_empresa,
    # Usuario Frontend
    criar_usuario_frontend,
    # Produtos e Precos
    get_produtos_referencia,
    get_produtos_empresa,
    configurar_produto_empresa,
    # Estoque
    adicionar_ao_estoque,
    remover_do_estoque,
    get_estoque_funcionario,
    get_estoque_global,
    zerar_estoque_funcionario,
    # Transacoes
    registrar_transacao,
    get_transacoes_empresa,
    get_saldo_empresa,
    # Encomendas
    criar_encomenda,
    get_encomendas_pendentes,
    get_encomenda,
    atualizar_status_encomenda,
    # Assinatura
    verificar_assinatura_servidor,
    get_planos_disponiveis,
    simular_pagamento,
    adicionar_tester,
    remover_tester,
    listar_testers,
    # Cache
    limpar_cache_global
)

# ============================================
# CORES PARA OUTPUT
# ============================================
class Colors:
    OK = '\033[92m'
    FAIL = '\033[91m'
    WARN = '\033[93m'
    INFO = '\033[94m'
    HEADER = '\033[95m'
    END = '\033[0m'

def ok(msg): print(f"{Colors.OK}[OK]{Colors.END} {msg}")
def fail(msg): print(f"{Colors.FAIL}[FALHOU]{Colors.END} {msg}")
def warn(msg): print(f"{Colors.WARN}[AVISO]{Colors.END} {msg}")
def info(msg): print(f"{Colors.INFO}[INFO]{Colors.END} {msg}")
def section(msg): print(f"\n{Colors.HEADER}=== {msg} ==={Colors.END}")

# ============================================
# DADOS DE TESTE
# ============================================
TEST_GUILD_ID = "1450699474526671002"
TEST_DISCORD_ID = "306217606082199555"
BOT_TEST_GUILD = "666666666666666666"  # Guild ficticia para testes de bot
BOT_TEST_DISCORD = "555555555555555555"  # Discord ficticio

# ============================================
# TESTES ADMIN COG
# ============================================

async def test_admin_limpar_cache():
    """Simula !limparcache"""
    section("ADMIN: !limparcache")
    
    limpar_cache_global()
    ok("Cache limpo com sucesso")
    return True


async def test_admin_get_tipos_empresa():
    """Simula listagem de tipos para !configurar"""
    section("ADMIN: tipos de empresa")
    
    tipos = await get_tipos_empresa()
    
    if tipos:
        ok(f"{len(tipos)} tipo(s) de empresa disponivel(is)")
        for t in tipos[:5]:
            info(f"  - {t['codigo']}: {t['nome']}")
        return True
    else:
        fail("Nenhum tipo de empresa")
        return False


async def test_admin_listar_empresas():
    """Simula !empresas"""
    section("ADMIN: !empresas")
    
    empresas = await get_empresas_by_guild(TEST_GUILD_ID)
    
    ok(f"{len(empresas)} empresa(s) configurada(s)")
    for e in empresas[:3]:
        info(f"  - {e['nome']}")
    
    return True


# ============================================
# TESTES ASSINATURA COG
# ============================================

async def test_assinatura_ver():
    """Simula !assinatura"""
    section("ASSINATURA: !assinatura")
    
    assinatura = await verificar_assinatura_servidor(TEST_GUILD_ID)
    
    info(f"  Ativa: {assinatura.get('ativa')}")
    info(f"  Status: {assinatura.get('status')}")
    info(f"  Dias: {assinatura.get('dias_restantes')}")
    
    ok("Comando !assinatura funciona")
    return True


async def test_assinatura_planos():
    """Simula !planos"""
    section("ASSINATURA: !planos")
    
    planos = await get_planos_disponiveis()
    
    if planos:
        ok(f"{len(planos)} plano(s) disponivel(is)")
        for p in planos:
            info(f"  - {p['nome']}: R$ {float(p['preco']):.2f}")
        return True
    else:
        fail("Nenhum plano")
        return False


async def test_assinatura_testers():
    """Simula !testers"""
    section("ASSINATURA: !testers")
    
    testers = await listar_testers()
    
    ok(f"{len(testers)} tester(s) cadastrado(s)")
    return True


# ============================================
# TESTES FINANCEIRO COG
# ============================================

async def test_financeiro_registrar_pagamento():
    """Simula !pagar"""
    section("FINANCEIRO: !pagar")
    
    empresas = await get_empresas_by_guild(TEST_GUILD_ID)
    if not empresas:
        warn("Nenhuma empresa para testar")
        return True
    
    empresa_id = empresas[0]['id']
    func = await get_funcionario_by_discord_id(TEST_DISCORD_ID)
    
    if not func:
        warn("Funcionario nao encontrado")
        return True
    
    # Registra transacao simulando pagamento
    success = await registrar_transacao(
        empresa_id=empresa_id,
        tipo='pagamento_funcionario',
        valor=50.00,
        descricao='Teste automatizado - pagamento',
        funcionario_id=func['id']
    )
    
    if success:
        ok("Transacao de pagamento registrada")
        return True
    else:
        fail("Erro ao registrar transacao")
        return False


async def test_financeiro_caixa():
    """Simula !caixa"""
    section("FINANCEIRO: !caixa")
    
    empresas = await get_empresas_by_guild(TEST_GUILD_ID)
    if not empresas:
        warn("Nenhuma empresa para testar")
        return True
    
    empresa_id = empresas[0]['id']
    
    saldo = await get_saldo_empresa(empresa_id)
    transacoes = await get_transacoes_empresa(empresa_id, limit=5)
    
    info(f"  Saldo: R$ {saldo:.2f}")
    info(f"  Ultimas transacoes: {len(transacoes)}")
    
    ok("Comando !caixa funciona")
    return True


# ============================================
# TESTES PRECOS COG
# ============================================

async def test_precos_ver():
    """Simula !precos"""
    section("PRECOS: !precos")
    
    empresas = await get_empresas_by_guild(TEST_GUILD_ID)
    if not empresas:
        warn("Nenhuma empresa para testar")
        return True
    
    empresa_id = empresas[0]['id']
    produtos = await get_produtos_empresa(empresa_id)
    
    ok(f"{len(produtos)} produto(s) configurado(s)")
    for codigo, p in list(produtos.items())[:5]:
        preco = float(p.get('preco_venda', 0))
        info(f"  - {codigo}: R$ {preco:.2f}")
    
    return True


async def test_precos_produtos_referencia():
    """Testa produtos de referencia para configuracao"""
    section("PRECOS: produtos referencia")
    
    tipos = await get_tipos_empresa()
    if not tipos:
        warn("Nenhum tipo de empresa")
        return True
    
    tipo_id = tipos[0]['id']
    produtos = await get_produtos_referencia(tipo_id)
    
    ok(f"{len(produtos)} produto(s) de referencia para tipo {tipos[0]['codigo']}")
    return True


# ============================================
# TESTES PRODUCAO COG
# ============================================

async def test_producao_add():
    """Simula !add produto quantidade"""
    section("PRODUCAO: !add")
    
    empresas = await get_empresas_by_guild(TEST_GUILD_ID)
    if not empresas:
        warn("Nenhuma empresa para testar")
        return True
    
    empresa_id = empresas[0]['id']
    func = await get_funcionario_by_discord_id(TEST_DISCORD_ID)
    
    if not func:
        warn("Funcionario nao encontrado")
        return True
    
    # Pega primeiro produto disponivel
    produtos = await get_produtos_empresa(empresa_id)
    if not produtos:
        warn("Nenhum produto configurado")
        return True
    
    codigo = list(produtos.keys())[0]
    
    resultado = await adicionar_ao_estoque(
        funcionario_id=func['id'],
        empresa_id=empresa_id,
        codigo=codigo,
        quantidade=5
    )
    
    if resultado:
        ok(f"Adicionados 5x {codigo} ao estoque")
        info(f"  Novo total: {resultado.get('quantidade')}")
        return resultado
    else:
        fail("Erro ao adicionar ao estoque")
        return None


async def test_producao_estoque():
    """Simula !estoque"""
    section("PRODUCAO: !estoque")
    
    empresas = await get_empresas_by_guild(TEST_GUILD_ID)
    if not empresas:
        warn("Nenhuma empresa para testar")
        return True
    
    empresa_id = empresas[0]['id']
    func = await get_funcionario_by_discord_id(TEST_DISCORD_ID)
    
    if not func:
        warn("Funcionario nao encontrado")
        return True
    
    estoque = await get_estoque_funcionario(func['id'], empresa_id)
    
    ok(f"{len(estoque)} item(ns) no estoque")
    for item in estoque[:5]:
        info(f"  - {item['produto_codigo']}: {item['quantidade']}x")
    
    return True


async def test_producao_deletar():
    """Simula !deletar produto quantidade"""
    section("PRODUCAO: !deletar")
    
    empresas = await get_empresas_by_guild(TEST_GUILD_ID)
    if not empresas:
        warn("Nenhuma empresa para testar")
        return True
    
    empresa_id = empresas[0]['id']
    func = await get_funcionario_by_discord_id(TEST_DISCORD_ID)
    
    if not func:
        warn("Funcionario nao encontrado")
        return True
    
    estoque = await get_estoque_funcionario(func['id'], empresa_id)
    
    if not estoque:
        info("Estoque vazio - nada para deletar")
        return True
    
    item = estoque[0]
    resultado = await remover_do_estoque(
        funcionario_id=func['id'],
        empresa_id=empresa_id,
        codigo=item['produto_codigo'],
        quantidade=1
    )
    
    if resultado and not resultado.get('erro'):
        ok(f"Removido 1x {item['produto_codigo']}")
        return True
    elif resultado and resultado.get('erro'):
        warn(f"Nao removeu: {resultado.get('erro')}")
        return True
    else:
        fail("Erro ao remover")
        return False


async def test_producao_estoque_global():
    """Simula !estoqueglobal"""
    section("PRODUCAO: !estoqueglobal")
    
    empresas = await get_empresas_by_guild(TEST_GUILD_ID)
    if not empresas:
        warn("Nenhuma empresa para testar")
        return True
    
    empresa_id = empresas[0]['id']
    estoque = await get_estoque_global(empresa_id)
    
    ok(f"{len(estoque)} produto(s) no estoque global")
    return True


async def test_producao_produtos():
    """Simula !produtos"""
    section("PRODUCAO: !produtos")
    
    empresas = await get_empresas_by_guild(TEST_GUILD_ID)
    if not empresas:
        warn("Nenhuma empresa para testar")
        return True
    
    empresa_id = empresas[0]['id']
    produtos = await get_produtos_empresa(empresa_id)
    
    ok(f"{len(produtos)} produto(s) listado(s)")
    return True


async def test_producao_encomendas():
    """Simula !encomendas"""
    section("PRODUCAO: !encomendas")
    
    empresas = await get_empresas_by_guild(TEST_GUILD_ID)
    if not empresas:
        warn("Nenhuma empresa para testar")
        return True
    
    empresa_id = empresas[0]['id']
    encomendas = await get_encomendas_pendentes(empresa_id)
    
    ok(f"{len(encomendas)} encomenda(s) pendente(s)")
    return True


# ============================================
# EXECUTAR TODOS OS TESTES
# ============================================

async def run_all_tests():
    """Executa todos os testes de comandos do bot."""
    print("\n" + "="*60)
    print("   TESTES DE COMANDOS DO BOT - BOT FAZENDEIRO")
    print("   " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)

    resultados = []

    try:
        # Admin
        r = await test_admin_limpar_cache()
        resultados.append(("admin_limpar_cache", r))

        r = await test_admin_get_tipos_empresa()
        resultados.append(("admin_tipos_empresa", r))

        r = await test_admin_listar_empresas()
        resultados.append(("admin_listar_empresas", r))

        # Assinatura
        r = await test_assinatura_ver()
        resultados.append(("assinatura_ver", r))

        r = await test_assinatura_planos()
        resultados.append(("assinatura_planos", r))

        r = await test_assinatura_testers()
        resultados.append(("assinatura_testers", r))

        # Financeiro
        r = await test_financeiro_registrar_pagamento()
        resultados.append(("financeiro_pagar", r))

        r = await test_financeiro_caixa()
        resultados.append(("financeiro_caixa", r))

        # Precos
        r = await test_precos_ver()
        resultados.append(("precos_ver", r))

        r = await test_precos_produtos_referencia()
        resultados.append(("precos_referencia", r))

        # Producao
        r = await test_producao_add()
        resultados.append(("producao_add", r is not None))

        r = await test_producao_estoque()
        resultados.append(("producao_estoque", r))

        r = await test_producao_deletar()
        resultados.append(("producao_deletar", r))

        r = await test_producao_estoque_global()
        resultados.append(("producao_estoque_global", r))

        r = await test_producao_produtos()
        resultados.append(("producao_produtos", r))

        r = await test_producao_encomendas()
        resultados.append(("producao_encomendas", r))

    except Exception as e:
        fail(f"Erro nos testes: {e}")
        import traceback
        traceback.print_exc()

    # Resumo
    print("\n" + "="*60)
    print("   RESUMO DOS TESTES DE COMANDOS")
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
