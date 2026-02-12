"""Testes do Precos Cog."""
from . import section, ok, fail, info, warn, TEST_GUILD_ID
from database import (
    get_empresas_by_guild,
    get_produtos_empresa,
    get_tipos_empresa,
    get_produtos_referencia,
)


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
