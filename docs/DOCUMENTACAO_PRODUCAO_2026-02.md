# Documentacao de Producao - Bot Fazendeiro (2026-02)

## 1. Objetivo

Consolidar estado real de producao para frontend + backend, incluindo:
- arquitetura atual
- fluxos criticos de auth/pagamento/webhook
- modelo de autorizacao tenant-aware
- checklist de deploy
- operacao e resposta a incidentes
- riscos e mitigacoes
- criterios de rollback

## 2. Arquitetura real

### Backend
- `main.py`: bot Discord e check global de assinatura.
- `api.py`: app FastAPI, CORS, rate-limit, security headers, request-id.
- `api_pkg/routes/payment.py`: create/status/verify/webhook PIX.
- `api_pkg/auth.py`: validacao JWT Supabase e autorizacao de tenant.
- `database/*`: funcoes de dominio.

### Frontend
- `frontend/src/context/auth/*`: sessao e perfil de acesso.
- `frontend/src/components/ProtectedRoute.tsx`: auth/role guard.
- `frontend/src/components/SubscriptionGate.tsx`: bloqueio por assinatura.
- `frontend/src/pages/Checkout/*`: compra PIX via API autenticada.

### Banco (Supabase)
- Tabelas principais: `usuarios_frontend`, `pagamentos_pix`, `assinaturas`, `planos`, `empresas`.
- Nova tabela de idempotencia: `webhook_events`.

## 3. Fluxos criticos

### 3.1 Login e autorizacao
1. Frontend realiza OAuth Discord via Supabase Auth.
2. Sessao retorna access token.
3. API valida token em `auth/v1/user`.
4. API extrai `discord_id` e valida acesso por `usuarios_frontend`.

### 3.2 Criacao de PIX
1. Frontend chama `POST /api/pix/create` com bearer token.
2. API valida tenant (`guild_id`) para usuario autenticado.
3. API cria customer/cobranca PIX no Asaas.
4. API salva `pagamentos_pix` como pendente.

### 3.3 Webhook Asaas
1. Asaas envia webhook para `/api/pix/webhook`.
2. API valida `asaas-access-token`.
3. API cria registro unico em `webhook_events` por hash do payload.
4. Evento duplicado e ignorado.
5. Evento valido atualiza `pagamentos_pix` e ativa `assinaturas`.

### 3.4 Verificacao/Status de pagamento
- `GET /api/pix/status/{payment_id}`:
  - exige JWT
  - exige acesso ao tenant ou ownership do pagamento
- `POST /api/pix/verify/{payment_id}`:
  - exige JWT
  - valida acesso tenant-aware
  - consulta Asaas para reconciliacao

## 4. Modelo tenant-aware

Regras:
1. Usuario sem vinculo ativo em `usuarios_frontend` nao opera tenant.
2. `guild_id` do payload e validado no backend.
3. Superadmin pode operar cross-tenant.
4. Pagamentos `pending_activation` exigem ownership por `discord_id`.

## 5. Checklist de deploy (Coolify)

## 5.1 Pre-deploy
1. Validar env vars backend/frontend.
2. Aplicar migrations do Supabase.
3. Rodar `pytest -q` no backend.
4. Rodar `npm test && npm run build` no frontend.

## 5.2 Deploy
1. Subir API FastAPI.
2. Subir bot Discord.
3. Subir frontend (Nginx).

## 5.3 Pos-deploy (smoke)
1. Login Discord no frontend.
2. Gerar PIX no checkout.
3. Confirmar status por endpoint de API.
4. Confirmar webhook e ativacao de assinatura.
5. Validar acesso liberado no bot e no dashboard.

## 6. Observabilidade e operacao

Minimo obrigatorio:
1. Correlacao por `X-Request-ID`.
2. Logs de pagamento com `guild_id`, `discord_id`, `payment_id`.
3. Monitorar erros 4xx/5xx em rotas PIX.
4. Monitorar backlog de webhook (`webhook_events` com `status=failed`).
5. Coletar metricas em `GET /metrics`:
   - `api_requests_total`
   - `api_request_duration_seconds_(sum|count)`
   - `asaas_http_requests_total`
   - `asaas_http_request_duration_seconds_(sum|count)`
   - `pix_webhook_processed_total`, `pix_webhook_failed_total`

## 6.1 CI/CD
1. Backend workflow: `.github/workflows/backend-ci-cd.yml`
   - testes Python
   - deploy API e Bot por webhook Coolify
2. Frontend workflow: `frontend/.github/workflows/frontend-ci-cd.yml`
   - testes + build
   - deploy frontend por webhook Coolify

## 7. Runbook de incidentes

### 7.1 PIX criado, assinatura nao ativou
1. Conferir `pagamentos_pix.status`.
2. Conferir `webhook_events` por `payment_id`.
3. Rodar `POST /api/pix/verify/{payment_id}` para reconciliar.
4. Verificar `assinaturas` no `guild_id`.

### 7.2 Usuario sem acesso no frontend
1. Confirmar sessao Supabase.
2. Confirmar `usuarios_frontend` (`discord_id`, `guild_id`, `ativo`).
3. Confirmar role necessaria para rota.

### 7.3 Bot bloqueado apos pagamento
1. Validar assinatura ativa no banco.
2. Executar `!limparcache`.
3. Revalidar comando bloqueado.

## 8. Matriz de riscos e mitigacao

1. Spoof de `guild_id` no checkout.
   - Mitigacao: JWT obrigatorio + validacao tenant no backend.
2. Reprocessamento de webhook.
   - Mitigacao: `webhook_events` com hash unico.
3. Vazamento de acesso cross-tenant.
   - Mitigacao: autorizacao por `usuarios_frontend` e ownership.
4. Regressao de testes async.
   - Mitigacao: `pytest-asyncio` + `pytest.ini` (`asyncio_mode=auto`).

## 9. Criterios de rollback

Rollback imediato se:
1. taxa de erro 5xx PIX > 10% por 10 min.
2. falha sistemica de webhook com `failed` crescente.
3. usuarios autenticados sem acesso generalizado por tenant.

Procedimento:
1. Reverter deploy backend para versao anterior estavel.
2. Reverter frontend para build anterior.
3. Manter migration de auditoria/idempotencia (nao destrutiva).
4. Reprocessar pagamentos pendentes manualmente por verify endpoint.

## 10. Estado de prontidao atual

- Frontend build/test: OK
- Backend testes: OK (E2E reais desativados por padrao, habilitar com `RUN_E2E_TESTS=1`)
- Supabase migration idempotencia: aplicada
- Proxima etapa operacional: deploy coordenado no Coolify + smoke E2E real
