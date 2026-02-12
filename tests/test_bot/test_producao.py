"""Testes do Producao Cog."""
from . import section, ok, fail, info, warn, TEST_GUILD_ID, TEST_DISCORD_ID
from database import (
    get_empresas_by_guild,
    get_funcionario_by_discord_id,
    get_produtos_empresa,
    adicionar_ao_estoque,
    remover_do_estoque,
    get_estoque_funcionario,
    get_estoque_global,
    get_encomendas_pendentes,
)


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
