# Integrations & External Services

**Last Updated:** 2026-01-24

This document maps the external services that Bot Fazendeiro relies on to function.

## 1. Database (Supabase)

The core persistence layer. A hosted PostgreSQL database.

### Key Tables
- `users`: Registered users (linked to Discord IDs).
- `guilds`: Discord servers configuration.
- `assinaturas`: Subscription status for guilds.
- `pagamentos_pix`: Logs of PIX generated transactions.
- `producao`: Active farming slots/items.
- `estoque`: Inventory items per user/guild.
- `transacoes_financeiras`: Economy ledger.

## 2. Payments (Asaas)

Used for processing BRAZILIAN PIX payments for subscriptions.

- **Environment:** Sandbox (Test) & Production.
- **Integration Type:** REST API + Webhooks.
- **Key Flows:**
    - **Creation:** Backend requests new PIX charge from Asaas.
    - **Display:** Frontend displays QR Code returned by Asaas.
    - **Confirmation:** Asaas sends `PAYMENT_RECEIVED` webhook to `/api/pix/webhook`.

## 3. Discord API (via discord.py)

The primary user interface for game commands.

- **Interactions:** Slash Commands (`/`).
- **Permissions:** Admin checks, User ID verification.
- **Notifications:** Embeds DM'd to users or sent to channels.
