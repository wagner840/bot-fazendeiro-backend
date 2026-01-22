"""
Testes automatizados para o Bot Fazendeiro
Verifica integridade do banco de dados e funcionalidades principais
"""

import asyncio
import sys
import os
from decimal import Decimal
from datetime import datetime

# Adiciona o diretorio pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import supabase

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
# TESTES DE ESTRUTURA DO BANCO
# ============================================

def test_tabelas_existem():
    """Verifica se todas as tabelas necessarias existem"""
    print("\n" + "="*50)
    print("TESTE: Verificar existencia das tabelas")
    print("="*50)

    tabelas_necessarias = [
        'servidores',
        'empresas',
        'tipos_empresa',
        'funcionarios',
        'funcionario_empresa',
        'produtos_referencia',
        'produtos_empresa',
        'estoque_produtos',
        'encomendas',
        'transacoes',
        'historico_pagamentos',
        'usuarios_frontend'
    ]

    todas_ok = True
    for tabela in tabelas_necessarias:
        try:
            response = supabase.table(tabela).select('*').limit(1).execute()
            ok(f"Tabela '{tabela}' existe")
        except Exception as e:
            fail(f"Tabela '{tabela}' NAO existe ou erro: {e}")
            todas_ok = False

    return todas_ok


def test_tipos_empresa():
    """Verifica se tipos de empresa estao populados"""
    print("\n" + "="*50)
    print("TESTE: Tipos de empresa")
    print("="*50)

    response = supabase.table('tipos_empresa').select('*').eq('ativo', True).execute()

    if not response.data:
        fail("Nenhum tipo de empresa cadastrado")
        return False

    ok(f"{len(response.data)} tipos de empresa cadastrados")

    # Verifica tipos essenciais
    tipos_essenciais = ['fazenda', 'padaria', 'jornal', 'atelie']
    tipos_cadastrados = [t['codigo'] for t in response.data]

    for tipo in tipos_essenciais:
        if tipo in tipos_cadastrados:
            ok(f"Tipo '{tipo}' encontrado")
        else:
            warn(f"Tipo '{tipo}' nao encontrado")

    return True


def test_produtos_referencia():
    """Verifica se produtos de referencia estao populados"""
    print("\n" + "="*50)
    print("TESTE: Produtos de referencia (Catalogo Downtown)")
    print("="*50)

    response = supabase.table('produtos_referencia').select('*, tipos_empresa(nome)').eq('ativo', True).execute()

    if not response.data:
        fail("Nenhum produto de referencia cadastrado")
        return False

    ok(f"{len(response.data)} produtos de referencia cadastrados")

    # Agrupa por tipo
    tipos = {}
    for p in response.data:
        tipo_id = p['tipo_empresa_id']
        if tipo_id not in tipos:
            tipos[tipo_id] = 0
        tipos[tipo_id] += 1

    info(f"Distribuidos em {len(tipos)} tipos de empresa")

    # Verifica se precos estao corretos
    produtos_sem_preco = [p for p in response.data if not p['preco_minimo'] or not p['preco_maximo']]
    if produtos_sem_preco:
        warn(f"{len(produtos_sem_preco)} produtos sem preco definido")
    else:
        ok("Todos os produtos tem preco minimo e maximo")

    return True


def test_servidor_empresa():
    """Verifica se servidor e empresa estao configurados"""
    print("\n" + "="*50)
    print("TESTE: Servidor e Empresa")
    print("="*50)

    # Verifica servidores
    servidores = supabase.table('servidores').select('*').eq('ativo', True).execute()
    if not servidores.data:
        warn("Nenhum servidor configurado")
        return False

    ok(f"{len(servidores.data)} servidor(es) configurado(s)")

    # Verifica empresas
    empresas = supabase.table('empresas').select('*, tipos_empresa(nome)').eq('ativo', True).execute()
    if not empresas.data:
        warn("Nenhuma empresa configurada")
        return False

    ok(f"{len(empresas.data)} empresa(s) configurada(s)")

    for emp in empresas.data:
        tipo_nome = emp.get('tipos_empresa', {}).get('nome', 'Desconhecido') if emp.get('tipos_empresa') else 'N/A'
        info(f"  - {emp['nome']} (Tipo: {tipo_nome})")

    return True


def test_produtos_empresa():
    """Verifica se produtos estao vinculados a empresa"""
    print("\n" + "="*50)
    print("TESTE: Produtos da Empresa")
    print("="*50)

    empresas = supabase.table('empresas').select('id, nome').eq('ativo', True).execute()

    if not empresas.data:
        warn("Nenhuma empresa para testar")
        return False

    todas_ok = True
    for emp in empresas.data:
        produtos = supabase.table('produtos_empresa').select('*, produtos_referencia(nome, codigo)').eq('empresa_id', emp['id']).eq('ativo', True).execute()

        if not produtos.data:
            warn(f"Empresa '{emp['nome']}' sem produtos configurados")
            todas_ok = False
        else:
            ok(f"Empresa '{emp['nome']}': {len(produtos.data)} produtos")

            # Verifica se precos estao definidos
            sem_preco = [p for p in produtos.data if not p['preco_venda'] or p['preco_venda'] <= 0]
            if sem_preco:
                warn(f"  {len(sem_preco)} produtos sem preco de venda")

    return todas_ok


def test_funcionarios():
    """Verifica funcionarios cadastrados"""
    print("\n" + "="*50)
    print("TESTE: Funcionarios")
    print("="*50)

    funcionarios = supabase.table('funcionarios').select('*, empresas(nome)').eq('ativo', True).execute()

    if not funcionarios.data:
        warn("Nenhum funcionario cadastrado")
        return False

    ok(f"{len(funcionarios.data)} funcionario(s) cadastrado(s)")

    for func in funcionarios.data:
        emp_nome = func.get('empresas', {}).get('nome', 'N/A') if func.get('empresas') else 'N/A'
        saldo = float(func.get('saldo', 0))
        info(f"  - {func['nome']} | Empresa: {emp_nome} | Saldo: R$ {saldo:.2f}")

    return True


def test_usuarios_frontend():
    """Verifica usuarios com acesso ao frontend"""
    print("\n" + "="*50)
    print("TESTE: Usuarios Frontend")
    print("="*50)

    usuarios = supabase.table('usuarios_frontend').select('*').eq('ativo', True).execute()

    if not usuarios.data:
        warn("Nenhum usuario com acesso ao frontend")
        return False

    ok(f"{len(usuarios.data)} usuario(s) com acesso ao frontend")

    admins = [u for u in usuarios.data if u['role'] == 'admin']
    funcionarios = [u for u in usuarios.data if u['role'] == 'funcionario']
    superadmins = [u for u in usuarios.data if u['role'] == 'superadmin']

    info(f"  - Superadmins: {len(superadmins)}")
    info(f"  - Admins: {len(admins)}")
    info(f"  - Funcionarios: {len(funcionarios)}")

    return True


def test_estoque():
    """Verifica estado do estoque"""
    print("\n" + "="*50)
    print("TESTE: Estoque de Produtos")
    print("="*50)

    estoque = supabase.table('estoque_produtos').select('*, funcionarios(nome), empresas(nome)').execute()

    if not estoque.data:
        info("Estoque vazio (normal se tudo foi pago)")
        return True

    ok(f"{len(estoque.data)} item(ns) no estoque")

    total_valor = 0
    for item in estoque.data:
        func_nome = item.get('funcionarios', {}).get('nome', 'N/A') if item.get('funcionarios') else 'N/A'
        info(f"  - {item['produto_codigo']}: {item['quantidade']}x | Func: {func_nome}")

    return True


def test_encomendas():
    """Verifica encomendas"""
    print("\n" + "="*50)
    print("TESTE: Encomendas")
    print("="*50)

    encomendas = supabase.table('encomendas').select('*, empresas(nome)').execute()

    if not encomendas.data:
        info("Nenhuma encomenda registrada")
        return True

    ok(f"{len(encomendas.data)} encomenda(s) registrada(s)")

    por_status = {}
    for enc in encomendas.data:
        status = enc['status']
        if status not in por_status:
            por_status[status] = 0
        por_status[status] += 1

    for status, count in por_status.items():
        info(f"  - {status}: {count}")

    return True


def test_transacoes():
    """Verifica transacoes financeiras"""
    print("\n" + "="*50)
    print("TESTE: Transacoes Financeiras")
    print("="*50)

    transacoes = supabase.table('transacoes').select('*').execute()

    if not transacoes.data:
        info("Nenhuma transacao registrada")
        return True

    ok(f"{len(transacoes.data)} transacao(oes) registrada(s)")

    por_tipo = {}
    for t in transacoes.data:
        tipo = t['tipo']
        if tipo not in por_tipo:
            por_tipo[tipo] = {'count': 0, 'valor': 0}
        por_tipo[tipo]['count'] += 1
        por_tipo[tipo]['valor'] += float(t['valor'])

    for tipo, dados in por_tipo.items():
        info(f"  - {tipo}: {dados['count']}x | Total: R$ {dados['valor']:.2f}")

    return True


def test_historico_pagamentos():
    """Verifica historico de pagamentos"""
    print("\n" + "="*50)
    print("TESTE: Historico de Pagamentos")
    print("="*50)

    historico = supabase.table('historico_pagamentos').select('*, funcionarios(nome)').execute()

    if not historico.data:
        info("Nenhum pagamento registrado")
        return True

    ok(f"{len(historico.data)} pagamento(s) registrado(s)")

    total = sum(float(h['valor']) for h in historico.data)
    info(f"  Total pago: R$ {total:.2f}")

    return True


# ============================================
# TESTES DE INTEGRIDADE
# ============================================

def test_integridade_fk():
    """Verifica integridade das foreign keys"""
    print("\n" + "="*50)
    print("TESTE: Integridade de Foreign Keys")
    print("="*50)

    problemas = 0

    # Empresas -> Servidores
    empresas = supabase.table('empresas').select('id, nome, servidor_id').execute()
    for emp in empresas.data:
        if emp['servidor_id']:
            servidor = supabase.table('servidores').select('id').eq('id', emp['servidor_id']).execute()
            if not servidor.data:
                fail(f"Empresa '{emp['nome']}' referencia servidor inexistente")
                problemas += 1

    # Funcionarios -> Empresas
    funcionarios = supabase.table('funcionarios').select('id, nome, empresa_id').execute()
    for func in funcionarios.data:
        if func['empresa_id']:
            empresa = supabase.table('empresas').select('id').eq('id', func['empresa_id']).execute()
            if not empresa.data:
                fail(f"Funcionario '{func['nome']}' referencia empresa inexistente")
                problemas += 1

    # Produtos_empresa -> Empresas
    produtos = supabase.table('produtos_empresa').select('id, empresa_id').execute()
    for prod in produtos.data:
        empresa = supabase.table('empresas').select('id').eq('id', prod['empresa_id']).execute()
        if not empresa.data:
            fail(f"Produto {prod['id']} referencia empresa inexistente")
            problemas += 1

    if problemas == 0:
        ok("Todas as foreign keys estao integras")
        return True
    else:
        fail(f"{problemas} problema(s) de integridade encontrado(s)")
        return False


# ============================================
# EXECUTAR TODOS OS TESTES
# ============================================

def run_all_tests():
    """Executa todos os testes"""
    print("\n" + "="*60)
    print("   BATERIA DE TESTES - BOT FAZENDEIRO")
    print("   " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)

    testes = [
        ("Tabelas Existem", test_tabelas_existem),
        ("Tipos de Empresa", test_tipos_empresa),
        ("Produtos Referencia", test_produtos_referencia),
        ("Servidor e Empresa", test_servidor_empresa),
        ("Produtos da Empresa", test_produtos_empresa),
        ("Funcionarios", test_funcionarios),
        ("Usuarios Frontend", test_usuarios_frontend),
        ("Estoque", test_estoque),
        ("Encomendas", test_encomendas),
        ("Transacoes", test_transacoes),
        ("Historico Pagamentos", test_historico_pagamentos),
        ("Integridade FK", test_integridade_fk),
    ]

    resultados = []
    for nome, func in testes:
        try:
            resultado = func()
            resultados.append((nome, resultado))
        except Exception as e:
            fail(f"Erro ao executar teste '{nome}': {e}")
            resultados.append((nome, False))

    # Resumo
    print("\n" + "="*60)
    print("   RESUMO DOS TESTES")
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
    success = run_all_tests()
    sys.exit(0 if success else 1)
