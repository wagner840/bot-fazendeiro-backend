# 🏢 Bot Fazendeiro Downtown

Bot Discord para gerenciamento econômico de empresas em servidores de roleplay (RDR2/RedM).

## 🚀 Funcionalidades

- Múltiplos tipos de empresa (Jornal, Fazenda, Restaurante, etc.)
- Gestão de estoque de funcionários
- Sistema de encomendas
- Configuração de preços (mínimo/médio/máximo)
- Comissão configurável para funcionários
- Integração com frontend React

## 📋 Requisitos

- Python 3.10+
- Discord Bot Token
- Supabase Account

## ⚙️ Instalação

1. Clone o repositório
2. Copie `.env.example` para `.env` e preencha:
   ```
   DISCORD_TOKEN=seu_token
   SUPABASE_URL=sua_url
   SUPABASE_KEY=sua_key
   ```
3. Instale dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Execute:
   ```bash
   python main.py
   ```

## 📁 Estrutura

```
├── main.py           # Bot principal
├── api.py            # API & Webhooks
├── .env              # Configurações (não commitar)
├── docs/             # Documentação & Codemaps
│   ├── CODEMAPS/     # <--- Mapas Arquiteturais
│   ├── DOCUMENTACAO_BOT.md
│   └── ...
├── cogs/             # Módulos do Bot
├── frontend/         # Frontend React
└── data/             # Dados de referência
```

## 🔧 Comandos Principais

| Comando | Descrição |
|---------|-----------|
| `!configurar` | Configura empresa do servidor |
| `!configmedio` | Preços médios + mostra tabela |
| `!comissao 30` | Define comissão funcionários 30% |
| `!verprecos` | Ver preços configurados |
| `!help` | Lista todos os comandos |

## 🏗️ Arquitetura

Veja os mapas arquiteturais detalhados em [docs/CODEMAPS/INDEX.md](docs/CODEMAPS/INDEX.md).

- [Backend Codemap](docs/CODEMAPS/backend.md)
- [Frontend Codemap](docs/CODEMAPS/frontend.md)
- [Integrations Codemap](docs/CODEMAPS/integrations.md)

## 📖 Documentação

Ver [docs/DOCUMENTACAO_BOT.md](docs/DOCUMENTACAO_BOT.md)
