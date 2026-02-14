-- Webhook idempotency and audit table for payment providers.

create table if not exists public.webhook_events (
  id bigserial primary key,
  provider text not null,
  event_hash text not null,
  event_type text not null,
  payment_id text null,
  payload jsonb not null default '{}'::jsonb,
  status text not null default 'processing' check (status in ('processing', 'processed', 'failed')),
  error_message text null,
  received_at timestamptz not null default now(),
  processed_at timestamptz null
);

create unique index if not exists webhook_events_provider_event_hash_uq
  on public.webhook_events (provider, event_hash);

create index if not exists webhook_events_payment_status_idx
  on public.webhook_events (payment_id, status);

create unique index if not exists pagamentos_pix_pix_id_uq
  on public.pagamentos_pix (pix_id);

alter table public.webhook_events enable row level security;

