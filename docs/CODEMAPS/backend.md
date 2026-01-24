# Backend Architecture

**Last Updated:** 2026-01-24
**Runtime:** Python 3.10+
**Frameworks:** discord.py, FastAPI
**Entry Points:** `main.py` (Bot), `api.py` (API)

## Directory Structure

```
w:\Bot Fazendeiro\
├── main.py              # Discord Bot Entrypoint
├── api.py               # FastAPI/Webhooks Entrypoint
├── config.py            # Configuration & Env Vars
├── database.py          # Supabase Connection Helper
├── utils.py             # Shared Utilities
├── logging_config.py    # Centralized Logger
└── cogs/                # Bot Modules (Extensions)
    ├── admin.py         # Admin commands
    ├── assinatura.py    # Subscription/Plan Logic
    ├── financeiro.py    # Economy & Transactions
    ├── precos.py        # Market Prices & Logic
    └── producao.py      # Farming/Production Logic
```

## Key Modules (Cogs)

| Cog | Purpose | Key Commands.Events | Dependencies |
|-----|---------|---------------------|--------------|
| **Producao** | Core gameplay: planting, harvesting, inventory | `/plantar`, `/colher`, `/estoque` | `database.py` |
| **Financeiro**| Economy: sales, profit tracking, taxes | `/vender`, `/saldo`, `/extrato` | `database.py` |
| **Precos** | Market dynamic pricing system | Task: `atualizar_precos` | `database.py` |
| **Assinatura**| Guild subscription enforcement | Check: `verificar_assinatura` | `api.py` (indirectly) |
| **Admin** | System administration | `/restart`, `/logs` | `main.py` |

## Data Flow

1.  **Discord Flow:** User -> Discord Command -> `main.py` -> `cogs/*.py` -> `database.py` -> Supabase.
2.  **API Flow:** Web Request -> `api.py` -> `database.py` -> Supabase.
3.  **Webhook Flow:** Asaas (Payment) -> `api.py` (`/api/pix/webhook`) -> Supabase (Updates Status).

## Core Dependencies

- `discord.py`: Bot interaction framework.
- `fastapi`: API server for dashboard & webhooks.
- `supabase`: Database client (PostgreSQL).
- `aiohttp`: Async HTTP requests (used for Asaas API).
