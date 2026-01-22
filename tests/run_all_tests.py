"""
Runner de Testes - Bot Fazendeiro
Executa TODOS os testes em sequência e gera relatório completo.
"""

import asyncio
import subprocess
import sys
import os
from datetime import datetime

# ============================================
# CORES PARA OUTPUT
# ============================================
class Colors:
    OK = '\033[92m'
    FAIL = '\033[91m'
    WARN = '\033[93m'
    INFO = '\033[94m'
    HEADER = '\033[95m'
    BOLD = '\033[1m'
    END = '\033[0m'

def banner(msg):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}")
    print(f"   {msg}")
    print(f"{'='*60}{Colors.END}\n")

def section(msg):
    print(f"\n{Colors.BOLD}{msg}{Colors.END}")
    print("-" * 40)

def ok(msg): print(f"{Colors.OK}[OK]{Colors.END} {msg}")
def fail(msg): print(f"{Colors.FAIL}[FALHOU]{Colors.END} {msg}")
def info(msg): print(f"{Colors.INFO}[i]{Colors.END} {msg}")

# ============================================
# CONFIGURAÇÃO DE TESTES
# ============================================

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(TESTS_DIR)

# Lista de testes na ordem de execução
TESTS = [
    {
        "name": "Estrutura do Banco",
        "file": "test_database.py",
        "description": "Verifica tabelas, tipos, produtos e integridade FK",
        "critical": True
    },
    {
        "name": "Funções Database",
        "file": "test_funcoes.py",
        "description": "Testa CRUD de servidor, empresa, funcionário, estoque",
        "critical": True
    },
    {
        "name": "Assinatura e Pagamento",
        "file": "test_assinatura_completo.py",
        "description": "Testa planos, assinaturas, testers e simulação de pagamento",
        "critical": True
    },
    {
        "name": "Integração E2E",
        "file": "test_integracao_e2e.py",
        "description": "Fluxos completos: pagamento->liberacao, testers, expiracao",
        "critical": True
    },
    {
        "name": "API Asaas",
        "file": "test_asaas.py",
        "description": "Conexão com sandbox Asaas (requer internet)",
        "critical": False  # Não crítico pois depende de conexão externa
    }
]

# ============================================
# FUNÇÕES DE EXECUÇÃO
# ============================================

def run_test(test_file: str) -> tuple:
    """
    Executa um arquivo de teste e retorna (success, output).
    """
    file_path = os.path.join(TESTS_DIR, test_file)
    
    if not os.path.exists(file_path):
        return False, f"Arquivo não encontrado: {test_file}"
    
    try:
        result = subprocess.run(
            [sys.executable, file_path],
            capture_output=True,
            text=True,
            timeout=120,  # 2 minutos de timeout
            cwd=PROJECT_DIR
        )
        
        output = result.stdout + result.stderr
        success = result.returncode == 0
        
        return success, output
        
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT: Teste excedeu 2 minutos"
    except Exception as e:
        return False, f"Erro ao executar: {str(e)}"


def run_all_tests():
    """Executa todos os testes e gera relatório."""
    
    start_time = datetime.now()
    
    banner("BATERIA DE TESTES COMPLETA - BOT FAZENDEIRO")
    print(f"  Início: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Diretório: {PROJECT_DIR}")
    
    results = []
    
    for test in TESTS:
        section(f">>> {test['name']}")
        info(test['description'])
        print()
        
        success, output = run_test(test['file'])
        
        # Mostra output resumido
        lines = output.strip().split('\n')
        
        # Mostra as últimas linhas relevantes (resumo)
        for line in lines[-20:]:  # Últimas 20 linhas
            if line.strip():
                print(f"  {line}")
        
        results.append({
            "name": test['name'],
            "file": test['file'],
            "success": success,
            "critical": test['critical']
        })
        
        if success:
            ok(f"{test['name']} concluído com sucesso!")
        else:
            fail(f"{test['name']} falhou!")
            if test['critical']:
                print(f"  {Colors.WARN}[!] Este é um teste crítico{Colors.END}")

    # ============================================
    # RELATÓRIO FINAL
    # ============================================
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    banner("RELATÓRIO FINAL")
    
    passou = sum(1 for r in results if r['success'])
    falhou = sum(1 for r in results if not r['success'])
    criticos_falhando = sum(1 for r in results if not r['success'] and r['critical'])
    
    print(f"  {'Teste':<30} {'Status':<10} {'Crítico'}")
    print("  " + "-"*50)
    
    for r in results:
        status = f"{Colors.OK}PASSOU{Colors.END}" if r['success'] else f"{Colors.FAIL}FALHOU{Colors.END}"
        critico = "Sim" if r['critical'] else "Não"
        print(f"  {r['name']:<30} {status:<20} {critico}")
    
    print("\n" + "  " + "="*50)
    print(f"  Total de testes: {len(results)}")
    print(f"  {Colors.OK}Passou: {passou}{Colors.END}")
    print(f"  {Colors.FAIL}Falhou: {falhou}{Colors.END}")
    print(f"  Tempo total: {duration:.1f}s")
    print("  " + "="*50)
    
    if falhou == 0:
        print(f"\n  {Colors.OK}{Colors.BOLD}>>> TODOS OS TESTES PASSARAM! <<<{Colors.END}")
    elif criticos_falhando > 0:
        print(f"\n  {Colors.FAIL}{Colors.BOLD}>>> {criticos_falhando} TESTE(S) CRÍTICO(S) FALHANDO!{Colors.END}")
    else:
        print(f"\n  {Colors.WARN}{Colors.BOLD}[!] Alguns testes nao-criticos falharam{Colors.END}")
    
    print(f"\n  Fim: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Retorna código de saída
    return 0 if criticos_falhando == 0 else 1


# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)
