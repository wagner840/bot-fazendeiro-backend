"""Testes do Admin Cog."""
from . import section, ok, fail, info, warn, TEST_GUILD_ID
from database import get_tipos_empresa, get_empresas_by_guild, limpar_cache_global


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
