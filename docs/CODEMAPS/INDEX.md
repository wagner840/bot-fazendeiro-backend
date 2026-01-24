# Bot Fazendeiro Project Architecture

**Last Updated:** 2026-01-24

Welcome to the architectural documentation for **Bot Fazendeiro**. This directory contains detailed maps of the codebase structure, dependencies, and data flow.

## System Overview

The system is composed of three main parts:
1.  **Discord Bot (Python):** Handles user interactions within Discord servers, economy logic, and production management.
2.  **Web Dashboard (React):** Provides a visual interface for users to manage their farm, view finances, and configure settings.
3.  **API (FastAPI):** Serves as the communication bridge between the Frontend, the Database, and external services (Payments).

## Codemaps

| Area | Description | Link |
|------|-------------|------|
| **Backend** | Python Discord Bot & FastAPI structure, Modules (Cogs) | [Backend Codemap](./backend.md) |
| **Frontend** | React/Vite Dashboard structure, Pages, Components | [Frontend Codemap](./frontend.md) |
| **Integrations** | External services (Supabase, Asaas, Discord) | [Integrations Codemap](./integrations.md) |

## Quick Links

- [Project README](../../README.md)
- [API Documentation](../../api.py) (Self-documented in code)
