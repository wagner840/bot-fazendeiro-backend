"""Testes do Assinatura Cog."""
from . import section, ok, fail, info, warn, TEST_GUILD_ID
from database import (
    verificar_assinatura_servidor,
    get_planos_disponiveis,
    listar_testers,
)


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
