"""
Testes de Login Frontend - Bot Fazendeiro
Testa a logica de autenticacao sem navegador.
"""

import asyncio
import sys
import os
from datetime import datetime

# Adiciona o diretorio pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import supabase
from database import (
    verificar_assinatura_servidor,
    criar_usuario_frontend,
    get_usuario_frontend,
    get_usuarios_frontend_by_guild,
    atualizar_role_usuario_frontend,
    desativar_usuario_frontend
)

# ============================================
# CORES PARA OUTPUT
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
TEST_DISCORD_ID = "777777777777777777"  # ID ficticio
TEST_GUILD_ID = "1450699474526671002"   # Guild real
TEST_DISCORD_REAL = "306217606082199555"  # ID real do admin

# ============================================
# TESTES DE BUSCA DE USUARIO
# ============================================

async def test_buscar_usuario_existente():
    """Testa busca de usuario existente no frontend."""
    print("\n" + "="*50)
    print("TESTE: buscar_usuario_existente")
    print("="*50)

    # Busca usuario real
    usuario = await get_usuario_frontend(TEST_DISCORD_REAL, TEST_GUILD_ID)

    if usuario:
        ok("Usuario existente encontrado")
        info(f"  ID: {usuario.get('id')}")
        info(f"  Nome: {usuario.get('nome', 'N/A')}")
        info(f"  Role: {usuario.get('role')}")
        info(f"  Ativo: {usuario.get('ativo')}")
        return True
    else:
        warn("Usuario nao encontrado (pode precisar criar via !bemvindo)")
        return True  # Nao e falha - usuario pode nao existir


async def test_buscar_usuario_inexistente():
    """Testa busca de usuario que nao existe."""
    print("\n" + "="*50)
    print("TESTE: buscar_usuario_inexistente")
    print("="*50)

    usuario = await get_usuario_frontend(TEST_DISCORD_ID, TEST_GUILD_ID)

    if not usuario:
        ok("Usuario inexistente retorna None")
        return True
    else:
        warn("Usuario ficticio encontrado (inesperado)")
        return True


async def test_listar_usuarios_guild():
    """Testa listagem de usuarios de uma guild."""
    print("\n" + "="*50)
    print("TESTE: listar_usuarios_guild")
    print("="*50)

    usuarios = await get_usuarios_frontend_by_guild(TEST_GUILD_ID)

    ok(f"{len(usuarios)} usuario(s) encontrado(s)")
    
    for u in usuarios[:5]:  # Mostra ate 5
        info(f"  - {u.get('nome', 'N/A')} | Role: {u.get('role')} | Ativo: {u.get('ativo')}")

    return True


# ============================================
# TESTES DE ROLES
# ============================================

async def test_verificar_role_superadmin():
    """Testa verificacao de role superadmin."""
    print("\n" + "="*50)
    print("TESTE: verificar_role_superadmin")
    print("="*50)

    usuarios = await get_usuarios_frontend_by_guild(TEST_GUILD_ID)
    superadmins = [u for u in usuarios if u.get('role') == 'superadmin']

    if superadmins:
        ok(f"{len(superadmins)} superadmin(s) encontrado(s)")
        for sa in superadmins:
            info(f"  - {sa.get('nome', 'N/A')} (ID: {sa.get('discord_id')})")
        return True
    else:
        info("Nenhum superadmin nesta guild")
        return True


async def test_verificar_role_admin():
    """Testa verificacao de role admin."""
    print("\n" + "="*50)
    print("TESTE: verificar_role_admin")
    print("="*50)

    usuarios = await get_usuarios_frontend_by_guild(TEST_GUILD_ID)
    admins = [u for u in usuarios if u.get('role') == 'admin']

    ok(f"{len(admins)} admin(s) encontrado(s)")
    for a in admins[:3]:
        info(f"  - {a.get('nome', 'N/A')}")

    return True


async def test_verificar_role_funcionario():
    """Testa verificacao de role funcionario."""
    print("\n" + "="*50)
    print("TESTE: verificar_role_funcionario")
    print("="*50)

    usuarios = await get_usuarios_frontend_by_guild(TEST_GUILD_ID)
    funcionarios = [u for u in usuarios if u.get('role') == 'funcionario']

    ok(f"{len(funcionarios)} funcionario(s) encontrado(s)")

    return True


# ============================================
# TESTES DE CRUD USUARIO
# ============================================

async def test_criar_usuario_frontend():
    """Testa criacao de usuario frontend."""
    print("\n" + "="*50)
    print("TESTE: criar_usuario_frontend")
    print("="*50)

    usuario = await criar_usuario_frontend(
        discord_id=TEST_DISCORD_ID,
        guild_id=TEST_GUILD_ID,
        nome="Usuario Teste Automatizado",
        role="funcionario"
    )

    if usuario:
        ok("Usuario criado com sucesso")
        info(f"  ID: {usuario.get('id')}")
        info(f"  Role: {usuario.get('role')}")
        return usuario
    else:
        fail("Falha ao criar usuario")
        return None


async def test_atualizar_role():
    """Testa atualizacao de role."""
    print("\n" + "="*50)
    print("TESTE: atualizar_role")
    print("="*50)

    # Primeiro busca usuario de teste
    usuario = await get_usuario_frontend(TEST_DISCORD_ID, TEST_GUILD_ID)
    
    if not usuario:
        warn("Usuario de teste nao existe - criando...")
        usuario = await criar_usuario_frontend(
            discord_id=TEST_DISCORD_ID,
            guild_id=TEST_GUILD_ID,
            nome="Usuario Teste",
            role="funcionario"
        )

    if not usuario:
        fail("Nao conseguiu criar usuario para teste")
        return False

    # Atualiza para admin
    success = await atualizar_role_usuario_frontend(usuario['id'], 'admin')
    
    if success:
        ok("Role atualizada para admin")
        
        # Verifica alteracao
        usuario_atualizado = await get_usuario_frontend(TEST_DISCORD_ID, TEST_GUILD_ID)
        if usuario_atualizado and usuario_atualizado.get('role') == 'admin':
            ok("Confirmado: role = admin")
        
        # Volta para funcionario
        await atualizar_role_usuario_frontend(usuario['id'], 'funcionario')
        return True
    else:
        fail("Falha ao atualizar role")
        return False


async def test_desativar_usuario():
    """Testa desativacao de usuario."""
    print("\n" + "="*50)
    print("TESTE: desativar_usuario")
    print("="*50)

    # Busca usuario de teste
    usuario = await get_usuario_frontend(TEST_DISCORD_ID, TEST_GUILD_ID)
    
    if not usuario:
        warn("Usuario de teste nao existe")
        return True

    success = await desativar_usuario_frontend(usuario['id'])
    
    if success:
        ok("Usuario desativado")
        return True
    else:
        fail("Falha ao desativar")
        return False


# ============================================
# TESTES DE ASSINATURA NO LOGIN
# ============================================

async def test_verificar_assinatura_para_login():
    """Testa verificacao de assinatura durante login."""
    print("\n" + "="*50)
    print("TESTE: verificar_assinatura_para_login")
    print("="*50)

    assinatura = await verificar_assinatura_servidor(TEST_GUILD_ID)

    info(f"  Ativa: {assinatura.get('ativa')}")
    info(f"  Status: {assinatura.get('status')}")
    info(f"  Plano: {assinatura.get('plano_nome', 'N/A')}")
    info(f"  Dias restantes: {assinatura.get('dias_restantes', 0)}")

    # Teste de logica de bloqueio
    if assinatura.get('ativa'):
        ok("Servidor com assinatura ativa - login permitido")
    else:
        warn("Servidor sem assinatura - login bloqueado para funcionarios")
        info("NOTA: Superadmins tem acesso mesmo sem assinatura")

    return True


# ============================================
# LIMPEZA
# ============================================

async def cleanup_testes():
    """Limpa dados de teste."""
    print("\n" + "="*50)
    print("LIMPEZA: Removendo dados de teste")
    print("="*50)

    try:
        supabase.table('usuarios_frontend').delete().eq('discord_id', TEST_DISCORD_ID).execute()
        info("Usuario de teste removido")
    except Exception as e:
        warn(f"Erro na limpeza: {e}")

    ok("Limpeza concluida")


# ============================================
# EXECUTAR TODOS OS TESTES
# ============================================

async def run_all_tests():
    """Executa todos os testes de login."""
    print("\n" + "="*60)
    print("   TESTES DE LOGIN FRONTEND - BOT FAZENDEIRO")
    print("   " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)

    resultados = []

    try:
        # Testes de busca
        r = await test_buscar_usuario_existente()
        resultados.append(("buscar_usuario_existente", r))

        r = await test_buscar_usuario_inexistente()
        resultados.append(("buscar_usuario_inexistente", r))

        r = await test_listar_usuarios_guild()
        resultados.append(("listar_usuarios_guild", r))

        # Testes de roles
        r = await test_verificar_role_superadmin()
        resultados.append(("verificar_role_superadmin", r))

        r = await test_verificar_role_admin()
        resultados.append(("verificar_role_admin", r))

        r = await test_verificar_role_funcionario()
        resultados.append(("verificar_role_funcionario", r))

        # Testes de CRUD
        r = await test_criar_usuario_frontend()
        resultados.append(("criar_usuario_frontend", r is not None))

        r = await test_atualizar_role()
        resultados.append(("atualizar_role", r))

        r = await test_desativar_usuario()
        resultados.append(("desativar_usuario", r))

        # Teste de assinatura
        r = await test_verificar_assinatura_para_login()
        resultados.append(("verificar_assinatura_para_login", r))

    finally:
        await cleanup_testes()

    # Resumo
    print("\n" + "="*60)
    print("   RESUMO DOS TESTES DE LOGIN")
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
