"""
Bot Multi-Empresa Downtown - Database Module
Re-exports all database functions for backward compatibility.
"""

# Re-export supabase for test patching compatibility
from config import supabase

from database.servidor import (
    get_or_create_servidor,
    get_servidor_by_guild,
)

from database.usuario_frontend import (
    criar_usuario_frontend,
    get_usuario_frontend,
    get_usuarios_frontend_by_guild,
    atualizar_role_usuario_frontend,
    desativar_usuario_frontend,
)

from database.empresa import (
    get_tipos_empresa,
    get_bases_redm,
    atualizar_base_servidor,
    get_empresa_by_guild,
    get_empresas_by_guild,
    criar_empresa,
    atualizar_modo_pagamento,
    get_produtos_referencia,
)

from database.produto import (
    get_produtos_empresa,
    criar_produto_referencia_custom,
    configurar_produto_empresa,
)

from database.funcionario import (
    get_or_create_funcionario,
    vincular_funcionario_empresa,
    get_funcionario_by_discord_id,
    get_funcionarios_empresa,
    atualizar_canal_funcionario,
)

from database.estoque import (
    adicionar_ao_estoque,
    remover_do_estoque,
    get_estoque_funcionario,
    get_estoque_global,
    get_estoque_global_detalhado,
    remover_do_estoque_global,
    zerar_estoque_funcionario,
)

from database.transacao import (
    registrar_transacao,
    get_transacoes_empresa,
    get_saldo_empresa,
)

from database.encomenda import (
    criar_encomenda,
    get_encomendas_pendentes,
    get_encomenda,
    atualizar_status_encomenda,
)

from database.assinatura import (
    verificar_assinatura_servidor,
    get_assinatura_servidor,
    get_planos_disponiveis,
    criar_pagamento_pix,
    buscar_pagamento_pendente_usuario,
    atualizar_pagamento_guild,
    ativar_assinatura_servidor,
)

from database.tester import (
    adicionar_tester,
    remover_tester,
    verificar_tester,
    listar_testers,
    simular_pagamento,
)

from database.cache import (
    limpar_cache_global,
    limpar_cache_empresa,
    limpar_cache_servidor,
)

__all__ = [
    # Servidor
    'get_or_create_servidor',
    'get_servidor_by_guild',
    # Usuario Frontend
    'criar_usuario_frontend',
    'get_usuario_frontend',
    'get_usuarios_frontend_by_guild',
    'atualizar_role_usuario_frontend',
    'desativar_usuario_frontend',
    # Empresa
    'get_tipos_empresa',
    'get_bases_redm',
    'atualizar_base_servidor',
    'get_empresa_by_guild',
    'get_empresas_by_guild',
    'criar_empresa',
    'atualizar_modo_pagamento',
    'get_produtos_referencia',
    # Produto
    'get_produtos_empresa',
    'criar_produto_referencia_custom',
    'configurar_produto_empresa',
    # Funcionario
    'get_or_create_funcionario',
    'vincular_funcionario_empresa',
    'get_funcionario_by_discord_id',
    'get_funcionarios_empresa',
    'atualizar_canal_funcionario',
    # Estoque
    'adicionar_ao_estoque',
    'remover_do_estoque',
    'get_estoque_funcionario',
    'get_estoque_global',
    'get_estoque_global_detalhado',
    'remover_do_estoque_global',
    'zerar_estoque_funcionario',
    # Transacao
    'registrar_transacao',
    'get_transacoes_empresa',
    'get_saldo_empresa',
    # Encomenda
    'criar_encomenda',
    'get_encomendas_pendentes',
    'get_encomenda',
    'atualizar_status_encomenda',
    # Assinatura
    'verificar_assinatura_servidor',
    'get_assinatura_servidor',
    'get_planos_disponiveis',
    'criar_pagamento_pix',
    'buscar_pagamento_pendente_usuario',
    'atualizar_pagamento_guild',
    'ativar_assinatura_servidor',
    # Tester
    'adicionar_tester',
    'remover_tester',
    'verificar_tester',
    'listar_testers',
    'simular_pagamento',
    # Cache
    'limpar_cache_global',
    'limpar_cache_empresa',
    'limpar_cache_servidor',
]
