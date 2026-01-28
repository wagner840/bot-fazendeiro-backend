# 🤖 Bot Fazendeiro Downtown - AGENTS.md

> Este arquivo contém informações essenciais para agentes de IA trabalharem neste projeto.
> Leia atentamente antes de fazer qualquer modificação.

---

## 📋 Visão Geral do Projeto

**Bot Fazendeiro Downtown** é um bot Discord para gerenciamento econômico de empresas em servidores de roleplay (RDR2/RedM). O sistema opera em modelo SaaS (Software as a Service) com assinatura via PIX.

### Funcionalidades Principais
- Múltiplos tipos de empresa (Jornal, Fazenda, Restaurante, etc.)
- Gestão de estoque de funcionários
- Sistema de encomendas
- Configuração de preços (mínimo/médio/máximo)
- Comissão configurável para funcionários
- Painel web frontend React
- Sistema de assinatura com pagamento via PIX (Asaas)

---

## 🏗️ Arquitetura

### Stack Tecnológico

| Camada | Tecnologia |
|--------|------------|
| **Bot Discord** | Python 3.10+, discord.py 2.3+ |
| **API/Webhooks** | FastAPI, uvicorn |
| **Banco de Dados** | Supabase (PostgreSQL) |
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS |
| **Pagamentos** | Asaas (PIX) |
| **Testes** | pytest, unittest.mock |

### Arquitetura Multi-Tenant

```
Servidor Discord (guild_id)
    |
    +-- Servidor (tenant)
    |       |
    |       +-- Empresa 1 (tipo: Fazenda)
    |       |       +-- Produtos da empresa
    |       |       +-- Funcionários
    |       |       +-- Encomendas
    |       |
    |       +-- Empresa 2 (tipo: Padaria)
    |               +-- ...
    |
    +-- Usuários Frontend (acesso ao painel web)
```

---

## 📁 Estrutura de Diretórios

```
├── main.py              # Ponto de entrada do bot Discord
├── api.py               # API FastAPI (webhooks, endpoints)
├── config.py            # Configurações e variáveis de ambiente
├── database.py          # Funções de banco de dados
├── utils.py             # Utilitários e decorators
├── ui_utils.py          # Componentes de UI padronizados
├── logging_config.py    # Configuração de logging
├── requirements.txt     # Dependências Python
├── .env                 # Variáveis de ambiente (não commitar!)
├── .env.example         # Template de variáveis de ambiente
│
├── cogs/                # Módulos do bot (Cogs)
│   ├── admin.py         # Comandos administrativos
│   ├── producao.py      # Comandos de produção/estoque
│   ├── financeiro.py    # Comandos financeiros
│   ├── precos.py        # Configuração de preços
│   └── assinatura.py    # Gestão de assinatura
│
├── frontend/            # Aplicação React
│   ├── src/
│   │   ├── pages/       # Páginas (Dashboard, Produtos, etc.)
│   │   ├── components/  # Componentes React
│   │   ├── lib/         # Utilitários e cliente Supabase
│   │   └── types.ts     # Tipos TypeScript
│   └── package.json
│
├── tests/               # Testes automatizados
│   ├── conftest.py      # Fixtures pytest
│   ├── test_*.py        # Testes por módulo
│   └── run_all_tests.py # Runner de testes
│
├── docs/                # Documentação
│   ├── DOCUMENTACAO_BOT.md  # Documentação técnica completa
│   ├── CODEMAPS/            # Mapas arquiteturais
│   └── plans/               # Planos de desenvolvimento
│
├── supabase/
│   └── migrations/      # Migrações do banco de dados
│
├── data/                # Dados de referência
└── logs/                # Logs do bot
```

---

## 🚀 Comandos de Build e Execução

### Bot (Python)

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar o bot
python main.py

# Executar a API (em terminal separado)
uvicorn api:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Instalar dependências
npm install

# Desenvolvimento
npm run dev

# Build para produção
npm run build

# Preview da build
npm run preview

# Testes
npm test
npm run test:coverage
```

### Testes Python

```bash
# Executar todos os testes
pytest

# Executar com verbose
pytest -v

# Executar teste específico
pytest tests/test_admin_cog.py -v

# Executar via script
python tests/run_all_tests.py
```

---

## 📝 Convenções de Código

### Estilo Python
- **Linter**: Sem linter configurado, mas siga PEP 8
- **Docstrings**: Use docstrings em português para funções públicas
- **Tipagem**: Use type hints quando apropriado
- **Async**: Todo código de I/O deve ser async/await
- **Imports**: Agrupe imports: stdlib → third-party → local

### Estrutura de Cogs
```python
class NomeCog(commands.Cog, name="Nome Amigável"):
    """Descrição do cog."""
    
    def __init__(self, bot):
        self.bot = bot
    
    # Comandos aqui...

async def setup(bot):
    await bot.add_cog(NomeCog(bot))
```

### UI Components
Use as factories de `ui_utils.py`:
```python
from ui_utils import create_success_embed, create_error_embed, create_info_embed

# Criar embeds padronizados
embed = create_success_embed("Título", "Descrição")
embed = create_error_embed("Erro", "Mensagem de erro")
embed = create_info_embed("Info", "Informação")
```

### Cores Padronizadas (ui_utils.py)
- `COLOR_SUCCESS = 0x2ecc71` (Verde)
- `COLOR_WARNING = 0xf1c40f` (Amarelo)
- `COLOR_ERROR = 0xe74c3c` (Vermelho)
- `COLOR_INFO = 0x3498db` (Azul)
- `COLOR_NEUTRAL = 0x95a5a6` (Cinza)

---

## 🧪 Estratégia de Testes

### Testes Unitários (Python)
- Localização: `tests/`
- Framework: pytest
- Mocking: unittest.mock para Supabase
- Fixtures: `conftest.py` contém mocks de Supabase

### Estrutura de Testes
```python
# Exemplo de teste com mock
async def test_funcao(mock_config):
    # mock_config é uma fixture que mocka o Supabase
    resultado = await funcao_testada()
    assert resultado == esperado
```

### Testes Frontend
- Framework: Vitest + React Testing Library
- Localização: `frontend/src/test/`

---

## 🔐 Variáveis de Ambiente

### Bot (.env)
```env
# Discord (obrigatório)
DISCORD_TOKEN=seu_token_aqui

# Supabase (obrigatório)
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua_anon_key
SUPABASE_SERVICE_ROLE_KEY=sua_service_role_key

# Asaas (para pagamentos)
ASAAS_API_KEY=sua_chave
ASAAS_WEBHOOK_TOKEN=token_webhook
```

### Frontend (.env)
```env
VITE_SUPABASE_URL=https://seu-projeto.supabase.co
VITE_SUPABASE_KEY=sua_anon_key
```

**⚠️ NUNCA commite arquivos .env com valores reais!**

---

## 🗄️ Estrutura do Banco de Dados

### Tabelas Principais

| Tabela | Descrição |
|--------|-----------|
| `servidores` | Tenants (servidores Discord) |
| `empresas` | Empresas vinculadas a servidores |
| `tipos_empresa` | Tipos de empresa (Fazenda, Jornal, etc.) |
| `produtos_referencia` | Catálogo global de produtos |
| `produtos_empresa` | Produtos com preços por empresa |
| `funcionarios` | Funcionários cadastrados |
| `funcionario_empresa` | Relação N:N funcionário-empresa |
| `estoque_produtos` | Estoque por funcionário |
| `encomendas` | Pedidos/encomendas |
| `transacoes` | Movimentações financeiras |
| `assinaturas` | Assinaturas dos servidores |
| `planos` | Planos de assinatura disponíveis |
| `pagamentos_pix` | Registro de pagamentos PIX |
| `usuarios_frontend` | Acesso ao painel web |

---

## 🎯 Principais Comandos do Bot

### Administração
| Comando | Descrição |
|---------|-----------|
| `!configurar` | Configura primeira empresa do servidor |
| `!novaempresa` | Cria nova empresa |
| `!limparcache` | Limpa cache do servidor |
| `!modopagamento` | Define modo (produção/entrega/estoque) |
| `!bemvindo @user` | Cadastra funcionário |

### Preços
| Comando | Descrição |
|---------|-----------|
| `!configmin` | Preços no mínimo (25% funcionário) |
| `!configmedio` | Preços na média (25% funcionário) |
| `!configmax` | Preços no máximo (25% funcionário) |
| `!configurarprecos` | Configuração manual |
| `!verprecos` | Lista preços configurados |
| `!comissao %` | Define % de comissão |

### Produção
| Comando | Descrição |
|---------|-----------|
| `!produzir` / `!add` | Registra produção |
| `!estoque` | Ver estoque pessoal |
| `!estoqueglobal` | Ver estoque da empresa |
| `!produtos` | Ver catálogo |
| `!encomenda` | Cria encomenda |
| `!entregar [id]` | Entrega encomenda |

### Financeiro
| Comando | Descrição |
|---------|-----------|
| `!pagar @user [valor]` | Pagamento manual |
| `!pagarestoque @user` | Paga e zera estoque |
| `!caixa` | Relatório financeiro |

### Assinatura
| Comando | Descrição |
|---------|-----------|
| `!assinatura` | Status da assinatura |
| `!assinarpix` | Link para pagamento |
| `!planos` | Lista planos disponíveis |
| `!validarpagamento` | Valida pagamento manual |

---

## 💡 Padrões Importantes

### Cache
O bot mantém cache em memória:
- `empresas_cache`: Dict[guild_id -> empresa]
- `servidores_cache`: Dict[guild_id -> servidor]

**Após alterações diretas no banco, use `!limparcache` para recarregar.**

### Verificação de Assinatura
Comandos são bloqueados se o servidor não tiver assinatura ativa, exceto:
- `help`, `ajuda`, `comandos`
- `assinatura`, `status`, `plano`
- `assinarpix`, `renovar`, `assinar`, `planos`
- Comandos de admin de testers (`addtester`, etc.)

### Modos de Pagamento
- **produção**: Valor acumula ao produzir (`!add`)
- **entrega**: Comissão ao entregar encomenda
- **estoque**: Pagamento baseado no estoque

---

## 🔒 Segurança

### Considerações de Segurança
1. **Nunca exponha** `DISCORD_TOKEN` ou `SUPABASE_SERVICE_ROLE_KEY`
2. Webhooks do Asaas verificam `ASAAS_WEBHOOK_TOKEN`
3. RLS (Row Level Security) no Supabase controla acesso
4. Service Role Key ignora RLS - use com cuidado
5. Superadmin IDs são hardcoded em `cogs/assinatura.py`

### IDs de Superadmin
```python
# Configurado via variável de ambiente SUPERADMIN_IDS no .env
```

---

## 📚 Documentação Adicional

- `docs/DOCUMENTACAO_BOT.md` - Documentação técnica completa
- `docs/CODEMAPS/INDEX.md` - Mapas arquiteturais
- `docs/TUTORIAL_BOT.md` - Tutorial para usuários
- `README.md` - Visão geral do projeto

---

## 🐛 Problemas Comuns

### "Empresa não configurada"
- Verifique se `empresas` tem registro com `guild_id` correto
- Use `!limparcache` para limpar cache

### "Acesso Negado" no Frontend
- Verifique `usuarios_frontend` com `discord_id` e `guild_id` corretos
- Verifique se `ativo = true`

### Produtos não aparecem
- Verifique se `produtos_empresa` tem registros para a `empresa_id`
- Use `!configmin` para popular automaticamente

---

## 📝 Notas para IA

1. **Idioma**: Todo o projeto usa **Português (BR)** para interface com usuário
2. **Logs**: Use o logger centralizado de `logging_config.py`
3. **Database**: Use funções de `database.py`, não acesse Supabase diretamente
4. **UI**: Use componentes padronizados de `ui_utils.py`
5. **Erros**: Sempre retorne embeds de erro amigáveis para o usuário
6. **Async**: Todo I/O deve ser async - nunca use sync para DB ou Discord API

---

*Última atualização: 2026-01-27*
