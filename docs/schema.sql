-- ============================================
-- SCHEMA MULTI-EMPRESA DOWNTOWN
-- Bot de Gerenciamento Econômico para RDR2 RP
-- ============================================

-- Tabela de tipos de empresa (categorias)
CREATE TABLE IF NOT EXISTS tipos_empresa (
    id SERIAL PRIMARY KEY,
    codigo TEXT UNIQUE NOT NULL,
    nome TEXT NOT NULL,
    descricao TEXT,
    cor_hex TEXT DEFAULT '#10b981',
    icone TEXT DEFAULT '🏢',
    ativo BOOLEAN DEFAULT TRUE,
    base_redm_id INTEGER REFERENCES bases_redm(id)
);

-- Tabela de empresas (uma por servidor Discord)
CREATE TABLE IF NOT EXISTS empresas (
    id SERIAL PRIMARY KEY,
    guild_id TEXT UNIQUE NOT NULL,
    nome TEXT NOT NULL,
    ativo BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (tipo_empresa_id) REFERENCES tipos_empresa(id)
);

CREATE INDEX IF NOT EXISTS idx_empresas_guild ON empresas(guild_id);

-- Tabela de produtos de referência (preços oficiais Downtown)
CREATE TABLE IF NOT EXISTS produtos_referencia (
    id SERIAL PRIMARY KEY,
    tipo_empresa_id INTEGER NOT NULL REFERENCES tipos_empresa(id),
    codigo TEXT NOT NULL,
    nome TEXT NOT NULL,
    categoria TEXT,
    preco_minimo DECIMAL(12,2) NOT NULL,
    preco_maximo DECIMAL(12,2) NOT NULL,
    unidade TEXT DEFAULT 'un',
    ativo BOOLEAN DEFAULT TRUE,
    UNIQUE(tipo_empresa_id, codigo)
);

CREATE INDEX IF NOT EXISTS idx_produtos_ref_tipo ON produtos_referencia(tipo_empresa_id);

-- Tabela de produtos da empresa (preços personalizados)
CREATE TABLE IF NOT EXISTS produtos_empresa (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    produto_referencia_id INTEGER NOT NULL REFERENCES produtos_referencia(id),
    preco_venda DECIMAL(12,2) NOT NULL,
    preco_pagamento_funcionario DECIMAL(12,2) NOT NULL,
    estoque_atual INTEGER DEFAULT 0,
    ativo BOOLEAN DEFAULT TRUE,
    UNIQUE(empresa_id, produto_referencia_id)
);

CREATE INDEX IF NOT EXISTS idx_produtos_empresa ON produtos_empresa(empresa_id);

-- Tabela de funcionários
CREATE TABLE IF NOT EXISTS funcionarios (
    id SERIAL PRIMARY KEY,
    discord_id TEXT UNIQUE NOT NULL,
    nome TEXT NOT NULL,
    saldo DECIMAL(12,2) DEFAULT 0.00,
    data_cadastro TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ativo BOOLEAN DEFAULT TRUE,
    empresa_id INTEGER REFERENCES empresas(id)
);

CREATE INDEX IF NOT EXISTS idx_funcionarios_discord ON funcionarios(discord_id);
CREATE INDEX IF NOT EXISTS idx_funcionarios_empresa ON funcionarios(empresa_id);

-- Tabela de estoque por funcionário
CREATE TABLE IF NOT EXISTS estoque_produtos (
    id SERIAL PRIMARY KEY,
    funcionario_id INTEGER NOT NULL REFERENCES funcionarios(id),
    empresa_id INTEGER REFERENCES empresas(id),
    produto_codigo TEXT NOT NULL,
    quantidade INTEGER NOT NULL DEFAULT 0,
    data_atualizacao TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_estoque_funcionario ON estoque_produtos(funcionario_id);
CREATE INDEX IF NOT EXISTS idx_estoque_empresa ON estoque_produtos(empresa_id);

-- Tabela de encomendas
CREATE TABLE IF NOT EXISTS encomendas (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas(id),
    comprador TEXT NOT NULL,
    itens_json JSONB NOT NULL,
    valor_total DECIMAL(12,2) NOT NULL,
    status TEXT DEFAULT 'pendente',
    funcionario_responsavel_id INTEGER REFERENCES funcionarios(id),
    data_criacao TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    data_entrega TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_encomendas_empresa ON encomendas(empresa_id);
CREATE INDEX IF NOT EXISTS idx_encomendas_status ON encomendas(status);

-- Tabela de histórico de pagamentos
CREATE TABLE IF NOT EXISTS historico_pagamentos (
    id SERIAL PRIMARY KEY,
    funcionario_id INTEGER NOT NULL REFERENCES funcionarios(id),
    tipo TEXT NOT NULL,
    valor DECIMAL(12,2) NOT NULL,
    descricao TEXT,
    data_pagamento TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pagamentos_funcionario ON historico_pagamentos(funcionario_id);

-- ============================================
-- TABELAS INFRAESTRUTURA / SAAS
-- ============================================

-- Tabela de Bases RedM (Servidores suportados/conectados)
CREATE TABLE IF NOT EXISTS bases_redm (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    ativo BOOLEAN DEFAULT TRUE
);

-- Tabela de Planos de Assinatura
CREATE TABLE IF NOT EXISTS planos (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    descricao TEXT,
    preco DECIMAL(10,2) NOT NULL,
    duracao_dias INTEGER DEFAULT 30,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de Servidores Discord (Clientes)
CREATE TABLE IF NOT EXISTS servidores (
    id SERIAL PRIMARY KEY,
    guild_id TEXT UNIQUE NOT NULL,
    nome TEXT NOT NULL,
    plano_atual TEXT DEFAULT 'gratuito',
    assinatura_ativa BOOLEAN DEFAULT TRUE,
    data_criacao TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ativo BOOLEAN DEFAULT TRUE,
    base_redm_id INTEGER DEFAULT 1 REFERENCES bases_redm(id)
);

CREATE INDEX IF NOT EXISTS idx_servidores_base_redm ON servidores(base_redm_id);

-- Tabela de Usuários do Dashboard Frontend
CREATE TABLE IF NOT EXISTS usuarios_frontend (
    id SERIAL PRIMARY KEY,
    discord_id TEXT NOT NULL,
    guild_id TEXT,
    role TEXT DEFAULT 'funcionario',
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    criado_por TEXT,
    nome TEXT
);

-- Tabela de Assinaturas
CREATE TABLE IF NOT EXISTS assinaturas (
    id SERIAL PRIMARY KEY,
    servidor_id INTEGER REFERENCES servidores(id),
    guild_id TEXT NOT NULL,
    plano_id INTEGER REFERENCES planos(id),
    status TEXT DEFAULT 'pendente',
    data_inicio TIMESTAMP WITH TIME ZONE,
    data_expiracao TIMESTAMP WITH TIME ZONE,
    pagador_discord_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assinaturas_servidor ON assinaturas(servidor_id);
CREATE INDEX IF NOT EXISTS idx_assinaturas_plano ON assinaturas(plano_id);

-- Tabela de Pagamentos PIX
CREATE TABLE IF NOT EXISTS pagamentos_pix (
    id SERIAL PRIMARY KEY,
    transaction_id TEXT UNIQUE NOT NULL,
    valor DECIMAL(10,2) NOT NULL,
    status TEXT DEFAULT 'pending',
    qr_code TEXT,
    qr_code_base64 TEXT,
    assinatura_id INTEGER REFERENCES assinaturas(id),
    plano_id INTEGER REFERENCES planos(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expiration_date TIMESTAMP WITH TIME ZONE,
    external_reference TEXT
);

CREATE INDEX IF NOT EXISTS idx_pagamentos_pix_assinatura ON pagamentos_pix(assinatura_id);
CREATE INDEX IF NOT EXISTS idx_pagamentos_pix_plano ON pagamentos_pix(plano_id);

-- Indexes adicionais de performance (identificados no review)
CREATE INDEX IF NOT EXISTS idx_empresas_tipo_empresa ON empresas(tipo_empresa_id);
CREATE INDEX IF NOT EXISTS idx_estoque_produtos_empresa ON estoque_produtos(empresa_id);
CREATE INDEX IF NOT EXISTS idx_tipos_empresa_base_redm ON tipos_empresa(base_redm_id);

-- ============================================
-- TIPOS DE EMPRESA DOWNTOWN
-- ============================================

INSERT INTO tipos_empresa (codigo, nome, descricao, icone, cor_hex) VALUES
    ('alimentos', 'Restaurante/Alimentos', 'Estabelecimentos que vendem comidas', '🍖', '#ef4444'),
    ('bebidas', 'Bar/Bebidas', 'Estabelecimentos que vendem bebidas', '🍺', '#f59e0b'),
    ('padaria', 'Padaria', 'Padarias e confeitarias', '🥐', '#eab308'),
    ('fazenda', 'Fazenda', 'Fazendas e produção rural', '🌾', '#22c55e'),
    ('acougue', 'Açougue', 'Açougues e carnes', '🥩', '#dc2626'),
    ('grafica', 'Gráfica de Manuais', 'Gráficas e impressões', '📚', '#6366f1'),
    ('estabulo', 'Estábulo', 'Estábulos e cuidados equinos', '🐴', '#a855f7'),
    ('artesanato', 'Artesanato', 'Produtos artesanais', '🧵', '#ec4899'),
    ('jornal', 'Jornal', 'Jornais e impressões', '📰', '#64748b'),
    ('atelie', 'Ateliê', 'Roupas e acessórios', '👔', '#14b8a6'),
    ('cavalaria', 'Cavalaria', 'Serviços de cavalaria', '🛡️', '#78716c'),
    ('tabacaria', 'Tabacaria', 'Produtos de tabaco', '🚬', '#854d0e'),
    ('tatuagem', 'Estúdio de Tatuagem', 'Tatuagens e body art', '💉', '#7c3aed'),
    ('ferraria', 'Ferraria', 'Ferramentas e metais', '⚒️', '#71717a'),
    ('madeireira', 'Madeireira', 'Madeiras e derivados', '🪵', '#92400e'),
    ('mineradora', 'Mineradora', 'Minérios e mineração', '⛏️', '#1e40af'),
    ('medico', 'Clínica Médica', 'Serviços médicos', '🏥', '#059669'),
    ('mercearia', 'Mercearia', 'Produtos diversos', '🛒', '#0891b2'),
    ('bercario', 'Berçário', 'Venda de animais', '🐄', '#16a34a'),
    ('agroindustria', 'Agroindústria', 'Rações e insumos agrícolas', '🌱', '#65a30d'),
    ('cartorio', 'Cartório', 'Serviços cartoriais', '📋', '#475569'),
    ('armaria', 'Armaria', 'Armas e equipamentos', '🔫', '#1f2937'),
    ('municao', 'Loja de Munições', 'Munições especiais', '💥', '#b91c1c'),
    ('passaros', 'Loja de Pássaros', 'Venda de aves', '🦅', '#0ea5e9'),
    ('nativos', 'Comércio Nativo', 'Produtos nativos', '🏹', '#d97706')
ON CONFLICT (codigo) DO NOTHING;
