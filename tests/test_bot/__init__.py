"""
Testes de Comandos do Bot - Bot Fazendeiro
Modulo de testes organizados por cog.
"""
import sys
import os

# Adiciona o diretorio pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


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


def ok(msg):
    print(f"{Colors.OK}[OK]{Colors.END} {msg}")


def fail(msg):
    print(f"{Colors.FAIL}[FALHOU]{Colors.END} {msg}")


def warn(msg):
    print(f"{Colors.WARN}[AVISO]{Colors.END} {msg}")


def info(msg):
    print(f"{Colors.INFO}[INFO]{Colors.END} {msg}")


def section(msg):
    print(f"\n{Colors.HEADER}=== {msg} ==={Colors.END}")


# ============================================
# DADOS DE TESTE
# ============================================
TEST_GUILD_ID = "1450699474526671002"
TEST_DISCORD_ID = "306217606082199555"
BOT_TEST_GUILD = "666666666666666666"  # Guild ficticia para testes de bot
BOT_TEST_DISCORD = "555555555555555555"  # Discord ficticio
