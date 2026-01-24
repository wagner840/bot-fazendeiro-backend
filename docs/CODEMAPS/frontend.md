# Frontend Architecture

**Last Updated:** 2026-01-24
**Framework:** React 19 + Vite
**Language:** TypeScript
**Styling:** Tailwind CSS + Radix UI
**Entry Point:** `src/main.tsx`

## Directory Structure

```
frontend/src/
├── main.tsx             # App Entrypoint
├── App.tsx              # Main Router & Layout
├── index.css            # Tailwind & Global Styles
├── components/          # Reusable UI Components
├── context/             # React Context (Auth, Theme)
├── hooks/               # Custom Hooks
├── lib/                 # Utilities (api, utils)
└── pages/               # Route Components
    ├── Dashboard.tsx    # Main User Hub
    ├── Financeiro.tsx   # Economy Views
    ├── Produtos.tsx     # Inventory Mgmt
    ├── Encomendas.tsx   # Order System
    ├── Funcionarios.tsx # Staff Mgmt
    └── ...
```

## Key Pages

| Page | Purpose | Route | Key Components |
|------|---------|-------|----------------|
| **Dashboard** | Overview of farm stats | `/dashboard` | `StatCard`, `RecentActivity` |
| **Login** | Auth with Discord/Email | `/login` | `AuthForm` |
| **Checkout** | Subscription purchase | `/checkout` | `PlanSelector`, `PixQRCode` |
| **Producao** | Manage active crops/animals | `/producao` | `GridSystem` |
| **Admin** | Superadmin controls | `/superadmin` | `UserList`, `ServerList` |

## Data Flow

User Interaction -> React Component -> `lib/api.ts` -> FastAPI (`api.py`) -> Supabase

## External Libraries

- **React Router:** Client-side routing.
- **TanStack Query (suspected):** Data fetching (if installed).
- **Lucide React:** Icons.
- **Recharts:** Charts for Financeiro page.
- **Framer Motion:** Animations.
