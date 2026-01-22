# Bot Multi-Empresa Downtown - Documentacao Tecnica

## Visao Geral

Bot Discord para gerenciamento economico de empresas em servidores de roleplay (RDR2/FiveM). Permite multiplas empresas por servidor Discord, controle de estoque, encomendas, pagamentos de funcionarios e integracao com frontend web.

---

## Stack Tecnologica

- **Bot**: Python 3.x + discord.py
- **Banco de Dados**: Supabase (PostgreSQL)
- **Frontend**: React + TypeScript + Vite
- **Autenticacao**: Discord OAuth2

---

## Arquitetura Multi-Tenant

```
Servidor Discord (guild_id)
    |
    +-- Servidor (tenant)
    |       |
    |       +-- Empresa 1 (tipo: Fazenda)
    |       |       +-- Produtos da empresa
    |       |       +-- Funcionarios
    |       |       +-- Encomendas
    |       |
    |       +-- Empresa 2 (tipo: Padaria)
    |               +-- ...
    |
    +-- Usuarios Frontend (acesso ao painel web)
```

---

## Estrutura do Banco de Dados

### Tabelas Principais

#### `servidores` (Tenant)
```sql
- id: INT (PK)
- guild_id: TEXT (UNIQUE) -- ID do servidor Discord
- nome: TEXT
- proprietario_discord_id: TEXT
- plano: TEXT (basico/pro/enterprise)
- assinatura_ativa: BOOLEAN
- ativo: BOOLEAN
```

#### `empresas`
```sql
- id: INT (PK)
- guild_id: TEXT -- ID do servidor Discord
- nome: TEXT
- tipo_empresa_id: INT (FK -> tipos_empresa)
- proprietario_discord_id: TEXT
- servidor_id: INT (FK -> servidores)
- ativo: BOOLEAN
```

#### `tipos_empresa`
```sql
- id: INT (PK)
- codigo: TEXT (UNIQUE) -- ex: "fazenda", "padaria", "atelie"
- nome: TEXT
- descricao: TEXT
- cor_hex: TEXT
- icone: TEXT (emoji)
- ativo: BOOLEAN
```

#### `produtos_referencia` (Catalogo Downtown)
```sql
- id: INT (PK)
- tipo_empresa_id: INT (FK)
- codigo: TEXT -- ex: "pa" (pao), "ensopado_carne"
- nome: TEXT
- categoria: TEXT
- preco_minimo: DECIMAL
- preco_maximo: DECIMAL
- unidade: TEXT
- ativo: BOOLEAN
```

#### `produtos_empresa` (Produtos vinculados a empresa)
```sql
- id: INT (PK)
- empresa_id: INT (FK)
- produto_referencia_id: INT (FK)
- preco_venda: DECIMAL
- preco_pagamento_funcionario: DECIMAL
- estoque_atual: INT
- ativo: BOOLEAN
```

#### `funcionarios`
```sql
- id: INT (PK)
- discord_id: TEXT (UNIQUE)
- nome: TEXT
- saldo: DECIMAL
- empresa_id: INT (FK) -- empresa principal
- ativo: BOOLEAN
```

#### `funcionario_empresa` (N:N)
```sql
- id: INT (PK)
- funcionario_id: INT (FK)
- empresa_id: INT (FK)
- cargo: TEXT
- ativo: BOOLEAN
```

#### `estoque_produtos`
```sql
- id: INT (PK)
- funcionario_id: INT (FK)
- empresa_id: INT (FK)
- produto_codigo: TEXT
- quantidade: INT
```

#### `encomendas`
```sql
- id: INT (PK)
- empresa_id: INT (FK)
- comprador: TEXT
- itens_json: JSONB -- [{codigo, nome, quantidade, quantidade_entregue, valor_unitario}]
- valor_total: DECIMAL
- status: TEXT (pendente/em_andamento/entregue/cancelada)
- funcionario_responsavel_id: INT (FK)
```

#### `usuarios_frontend`
```sql
- id: INT (PK)
- discord_id: TEXT
- guild_id: TEXT
- nome: TEXT
- role: TEXT (superadmin/admin/funcionario)
- ativo: BOOLEAN
```

---

## Fluxo de Configuracao

### 1. Primeiro Uso (Admin do Discord)

```
!configurar
    |
    +-> Cria registro em `servidores` (tenant)
    +-> Lista tipos de empresa disponiveis
    +-> Usuario escolhe tipo (ex: Jornal)
    +-> Usuario digita nome (ex: Editora Blue Dream)
    +-> Cria registro em `empresas`
    +-> Cria usuario em `usuarios_frontend` (role=admin)
```

### 2. Configurar Precos dos Produtos

```
!configmin   -> Todos produtos com preco MINIMO (25% funcionario)
!configmedio -> Todos produtos com preco MEDIO (25% funcionario)
!configmax   -> Todos produtos com preco MAXIMO (25% funcionario)

!configurarprecos -> Configuracao manual produto a produto
```

**Logica de configuracao automatica:**
```python
preco_venda = preco_minimo  # ou medio ou maximo
preco_funcionario = preco_venda * 0.25
```

Isso cria registros em `produtos_empresa` vinculando `produtos_referencia` a `empresa`.

---

## Comandos do Bot

### Configuracao (Admin)

| Comando | Descricao |
|---------|-----------|
| `!configurar` | Configura primeira empresa do servidor |
| `!novaempresa` | Adiciona outra empresa ao servidor |
| `!limparcache` | Limpa cache e recarrega dados do banco |
| `!configmin` | Configura todos precos no MINIMO + mostra preços |
| `!configmedio` | Configura todos precos no MEDIO + mostra preços |
| `!configmax` | Configura todos precos no MAXIMO + mostra preços |
| `!configurarprecos` | Configuracao manual de precos |
| `!verprecos` | Ver todos os preços da empresa por categoria |
| `!verprecos [cat]` | Ver preços de uma categoria específica |

### Gestao de Usuarios (Admin)

| Comando | Descricao |
|---------|-----------|
| `!bemvindo @pessoa` | Cria canal privado + acesso frontend |
| `!usuarios` | Lista usuarios com acesso ao frontend |
| `!promover @pessoa` | Promove para Admin |
| `!removeracesso @pessoa` | Remove acesso frontend |

### Producao (Funcionarios)

| Comando | Alias | Descricao |
|---------|-------|-----------|
| `!add [codigo][qtd]` | `!1` | Adiciona produtos ao estoque |
| `!estoque` | `!2` | Ver estoque pessoal |
| `!deletar [codigo][qtd]` | `!3` | Remove produtos do estoque |
| `!estoqueglobal` | - | Ver estoque total da empresa |
| `!produtos` | - | Ver catalogo de produtos |

**Formato de adicao:**
```
!add pa10 bo5 ce20
     ^^ ^^
     |  quantidade
     codigo do produto
```

### Encomendas

| Comando | Alias | Descricao |
|---------|-------|-----------|
| `!novaencomenda "Cliente" itens` | `!4` | Cria encomenda |
| `!encomendas` | `!5` | Lista encomendas pendentes |
| `!entregar [ID]` | - | Marca encomenda como entregue |

**Formato de encomenda:**
```
!novaencomenda "Joao Silva" pa10 bo5
```

### Financeiro (Admin)

| Comando | Descricao |
|---------|-----------|
| `!pagar @pessoa [valor]` | Registra pagamento manual |
| `!pagarestoque @pessoa` | Paga e zera estoque do funcionario |
| `!caixa` | Relatorio financeiro |

---

## Fluxo de Trabalho Tipico

### Funcionario Produz e Vende

```
1. Funcionario produz itens no jogo
2. Usa !add pa10 (adiciona 10 paes ao estoque)
3. Vende para cliente no jogo
4. Admin usa !pagarestoque @funcionario
5. Sistema calcula: quantidade * preco_pagamento_funcionario
6. Adiciona ao saldo do funcionario
7. Zera estoque
```

### Encomenda

```
1. Cliente faz pedido
2. Admin/Func usa !novaencomenda "Cliente" pa10 bo5
3. Sistema cria encomenda com status "pendente"
4. Funcionario produz os itens
5. Funcionario usa !add pa10 bo5
6. Quando pronto: !entregar [ID]
7. Sistema deduz do estoque e marca como entregue
```

---

## Cache do Bot

O bot mantem cache em memoria para:
- `servidores_cache`: Dict[guild_id -> servidor]
- `empresas_cache`: Dict[guild_id -> empresa]

**Importante:** Apos alteracoes diretas no banco, usar `!limparcache` para forcar recarregamento.

---

## Integracao Frontend

### Autenticacao
1. Usuario faz login com Discord OAuth2
2. Frontend obtem `discord_id` do usuario
3. Consulta `usuarios_frontend` para verificar acesso
4. Se `role = admin` ou `funcionario` e `ativo = true`, permite acesso

### Fluxo de Dados
```
Frontend -> Supabase Client -> Banco PostgreSQL
                |
                +-- RLS (Row Level Security) controla acesso por guild_id
```

### Endpoints Principais (via Supabase)
- `empresas` - Dados da empresa
- `produtos_empresa` - Produtos com precos
- `funcionarios` - Lista de funcionarios
- `encomendas` - Encomendas
- `historico_pagamentos` - Historico financeiro

---

## Variaveis de Ambiente

### Bot (.env)
```
DISCORD_TOKEN=xxx
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=xxx (anon key)
SUPABASE_SERVICE_ROLE_KEY=xxx (ignora RLS)
```

### Frontend (.env)
```
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_KEY=xxx (anon key)
```

---

## Problemas Comuns e Solucoes

### Bot diz "Empresa nao configurada"
- Verificar se `empresas` tem registro com o `guild_id` correto
- Usar `!limparcache` para limpar cache

### Frontend "Acesso Negado"
- Verificar se `usuarios_frontend` tem registro com `discord_id` e `guild_id` corretos
- Verificar se `ativo = true`

### Produtos nao aparecem
- Verificar se `produtos_empresa` tem registros para a `empresa_id`
- Usar `!configmin` ou similar para popular

### Erro silencioso ao criar usuario
- Verificar se tabela `usuarios_frontend` tem todas as colunas que o bot tenta inserir (especialmente `nome`)

---

## Tipos de Empresa Disponiveis

| Codigo | Nome | Produtos |
|--------|------|----------|
| alimentos | Restaurante/Alimentos | 50 |
| fazenda | Fazenda | 51 |
| bebidas | Bar/Bebidas | 45 |
| acougue | Acougue | 34 |
| agroindustria | Agroindustria | 32 |
| padaria | Padaria | 23 |
| armaria | Armaria | 17 |
| municao | Loja de Municoes | 17 |
| cartorio | Cartorio | 17 |
| ferraria | Ferraria | 16 |
| medico | Clinica Medica | 15 |
| artesanato | Artesanato | 15 |
| madeireira | Madeireira | 14 |
| estabulo | Estabulo | 11 |
| mineradora | Mineradora | 11 |
| nativos | Comercio Nativo | 9 |
| grafica | Grafica de Manuais | 9 |
| tabacaria | Tabacaria | 7 |
| bercario | Bercario | 7 |
| jornal | Jornal | 8 |
| atelie | Atelie | 6 |
| mercearia | Mercearia | 6 |
| passaros | Loja de Passaros | 6 |
| tatuagem | Estudio de Tatuagem | 4 |
| cavalaria | Cavalaria | 2 |

---

## Arquivos Principais

```
W:\Bot Fazendeiro\
├── main_multi.py          # Bot Discord principal
├── .env                   # Variaveis de ambiente
├── schema.sql             # Schema do banco (referencia)
├── DOCUMENTACAO_BOT.md    # Este arquivo
├── frontend\
│   ├── src\
│   │   ├── App.tsx
│   │   ├── pages\
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Produtos.tsx
│   │   │   ├── Funcionarios.tsx
│   │   │   └── ...
│   │   └── lib\
│   │       ├── supabase.ts    # Client Supabase
│   │       └── types.ts       # TypeScript types
│   └── ...
└── Tabela de Precos Downtown.txt  # Referencia de precos
```

---

## Resumo para IA

1. **Objetivo**: Gerenciar economia de empresas em RP
2. **Multi-tenant**: Cada servidor Discord = 1 tenant, pode ter N empresas
3. **Produtos**: Catalogo de referencia (Downtown) -> vinculados por empresa com precos personalizados
4. **Funcionarios**: Tem estoque individual, recebem pagamento por producao
5. **Frontend**: React com Supabase, acesso controlado por `usuarios_frontend`
6. **Cache**: Bot tem cache em memoria, usar `!limparcache` apos mudancas diretas no banco
