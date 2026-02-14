# Bot Fazendeiro Downtown

SaaS multi-tenant para servidores Discord de RP (RDR2/RedM), com:
- Bot Discord (operações de empresa e economia)
- API FastAPI (PIX/Asaas, webhook, verificação)
- Frontend React (painel de gestão)
- Supabase/PostgreSQL (dados, RLS, RPC)

## Arquitetura

- Backend repo: `W:/Bot Fazendeiro`
- Frontend repo (git separado): `W:/Bot Fazendeiro/frontend`
- Banco: Supabase
- Pagamentos: Asaas PIX

Fluxo principal:
1. Usuário autentica via Discord no frontend (Supabase Auth).
2. Frontend chama API PIX com bearer token.
3. API valida JWT + autorização por tenant (`usuarios_frontend`).
4. Webhook Asaas confirma pagamento.
5. API ativa assinatura no banco.
6. Bot libera comandos via verificação de assinatura.

## Variáveis de ambiente (backend)

`.env`:

```env
DISCORD_TOKEN=
SUPABASE_URL=
SUPABASE_KEY=
SUPABASE_SERVICE_ROLE_KEY=

ASAAS_API_KEY=
ASAAS_API_URL=https://www.asaas.com/api/v3
ASAAS_WEBHOOK_TOKEN=

FRONTEND_URL=http://localhost:3000
SUPERADMIN_IDS=123,456
```

## Variáveis de ambiente (frontend)

`frontend/.env`:

```env
VITE_SUPABASE_URL=
VITE_SUPABASE_KEY=
VITE_API_URL=http://localhost:8000
```

## Execução local

Backend:

```bash
pip install -r requirements.txt
python main.py
uvicorn api:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Testes e validações

Backend:

```bash
pytest -q
```

Notas:
- Testes E2E reais de Supabase ficam desabilitados por padrão.
- Para habilitar: `RUN_E2E_TESTS=1 pytest -q`.

Frontend:

```bash
cd frontend
npm test
npm run build
```

## Ordem de deploy (Coolify)

1. Aplicar migrations Supabase (`supabase/migrations`).
2. Deploy API FastAPI (`api.py`).
3. Deploy Bot Discord (`main.py`).
4. Deploy Frontend (`frontend/Dockerfile` + `frontend/nginx.conf`).
5. Rodar smoke test pós-deploy.

## Healthchecks

- API: `GET /`
- API metrics: `GET /metrics`
- Frontend: `GET /health` (nginx)

## CI/CD

- Backend pipeline: `.github/workflows/backend-ci-cd.yml`
  - roda testes (`pytest -q`)
  - dispara deploy API/Bot no Coolify via webhooks:
    - `COOLIFY_API_DEPLOY_HOOK`
    - `COOLIFY_BOT_DEPLOY_HOOK`
- Frontend pipeline (repo frontend): `frontend/.github/workflows/frontend-ci-cd.yml`
  - roda `npm test` + `npm run build`
  - dispara deploy no Coolify com:
    - `COOLIFY_FRONTEND_DEPLOY_HOOK`

## Troubleshooting

- `401 Unauthorized` em `/api/pix/create`:
  - conferir bearer token e sessão Supabase no frontend.
- `403 User has no access to this guild`:
  - validar `usuarios_frontend` (`discord_id`, `guild_id`, `ativo=true`).
- Webhook duplicado:
  - verificar tabela `webhook_events` (idempotência).
- Bot bloqueado mesmo após pagamento:
  - validar `assinaturas` e executar `!limparcache`.

## Documentação de produção

Guia completo: `docs/DOCUMENTACAO_PRODUCAO_2026-02.md`.
