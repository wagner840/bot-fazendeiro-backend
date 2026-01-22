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
├── .env              # Configurações (não commitar)
├── requirements.txt  # Dependências Python
├── docs/             # Documentação
│   ├── DOCUMENTACAO_BOT.md
│   ├── TUTORIAL_BOT.md
│   └── schema.sql
├── data/             # Dados de referência
└── frontend/         # Frontend React
```

## 🔧 Comandos Principais

| Comando | Descrição |
|---------|-----------|
| `!configurar` | Configura empresa do servidor |
| `!configmedio` | Preços médios + mostra tabela |
| `!comissao 30` | Define comissão funcionários 30% |
| `!verprecos` | Ver preços configurados |
| `!help` | Lista todos os comandos |

## 📖 Documentação

Ver [docs/DOCUMENTACAO_BOT.md](docs/DOCUMENTACAO_BOT.md)
