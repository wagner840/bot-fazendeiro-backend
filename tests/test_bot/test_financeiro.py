"""Testes do Financeiro Cog."""
from . import section, ok, fail, info, warn, TEST_GUILD_ID, TEST_DISCORD_ID
from database import (
    get_empresas_by_guild,
    get_funcionario_by_discord_id,
    registrar_transacao,
    get_transacoes_empresa,
    get_saldo_empresa,
)


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
