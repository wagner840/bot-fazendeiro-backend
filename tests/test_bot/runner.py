"""Test runner para todos os testes de comandos do bot."""
import asyncio
import sys
from datetime import datetime

from . import Colors

# Import all test modules
from .test_admin import (
    test_admin_limpar_cache,
    test_admin_get_tipos_empresa,
    test_admin_listar_empresas,
)
from .test_assinatura import (
    test_assinatura_ver,
    test_assinatura_planos,
    test_assinatura_testers,
)
from .test_financeiro import (
    test_financeiro_registrar_pagamento,
    test_financeiro_caixa,
)
from .test_precos import (
    test_precos_ver,
    test_precos_produtos_referencia,
)
from .test_producao import (
    test_producao_add,
    test_producao_estoque,
    test_producao_deletar,
    test_producao_estoque_global,
    test_producao_produtos,
    test_producao_encomendas,
)


async def run_all_tests():
    """Executa todos os testes de comandos do bot."""
    print("\n" + "=" * 60)
    print("   TESTES DE COMANDOS DO BOT - BOT FAZENDEIRO")
    print("   " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

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
        print(f"{Colors.FAIL}[FALHOU]{Colors.END} Erro nos testes: {e}")
        import traceback
        traceback.print_exc()

    # Resumo
    print("\n" + "=" * 60)
    print("   RESUMO DOS TESTES DE COMANDOS")
    print("=" * 60)

    passou = sum(1 for _, r in resultados if r)
    falhou = sum(1 for _, r in resultados if not r)

    for nome, resultado in resultados:
        status = (
            f"{Colors.OK}PASSOU{Colors.END}"
            if resultado
            else f"{Colors.FAIL}FALHOU{Colors.END}"
        )
        print(f"  {nome}: {status}")

    print("\n" + "-" * 60)
    print(f"  Total: {len(resultados)} | Passou: {passou} | Falhou: {falhou}")
    print("=" * 60 + "\n")

    return falhou == 0


def main():
    """Entry point for test runner."""
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
