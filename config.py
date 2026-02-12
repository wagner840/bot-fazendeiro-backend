"""
Bot Multi-Empresa - Configurações
Carrega variáveis de ambiente e inicializa conexões.
"""

import os
import re
from cachetools import TTLCache
from dotenv import load_dotenv
from supabase import create_async_client, AsyncClient

# Carrega variáveis de ambiente
load_dotenv()

# Regex para produtos (ex: pa2 va10)
PRODUTO_REGEX = re.compile(r'([a-zA-Z]+)(\d+)')

# Configurações do Discord
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Configurações do Asaas
ASAAS_API_KEY = os.getenv('ASAAS_API_KEY')

# Configurações do Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

# Usa Service Role Key se disponível (ignora RLS), senão usa Key normal
KEY_TO_USE = SUPABASE_SERVICE_ROLE_KEY if SUPABASE_SERVICE_ROLE_KEY else SUPABASE_KEY

# Validação
if not all([DISCORD_TOKEN, SUPABASE_URL, KEY_TO_USE]):
    raise ValueError("Variáveis de ambiente faltando (DISCORD_TOKEN, SUPABASE_URL, SUPABASE_KEY).")


class _SupabaseProxy:
    """Proxy que delega para o AsyncClient real após init.

    Necessário porque 20+ arquivos fazem `from config import supabase`.
    Com Python, `from X import Y` copia a referência no momento do import.
    O proxy garante que todas as cópias apontam para o mesmo client real.
    """
    _client: AsyncClient | None = None

    def __getattr__(self, name):
        if self._client is None:
            raise AttributeError(
                f"Supabase not initialized. Call init_supabase() first. "
                f"(Attempted to access '{name}')"
            )
        return getattr(self._client, name)


supabase = _SupabaseProxy()


async def init_supabase():
    """Inicializa o client async. Chamar uma vez no startup."""
    supabase._client = await create_async_client(SUPABASE_URL, KEY_TO_USE)


# Configurações do Asaas
ASAAS_API_URL = os.getenv('ASAAS_API_URL', "https://www.asaas.com/api/v3")
ASAAS_WEBHOOK_TOKEN = os.getenv('ASAAS_WEBHOOK_TOKEN')

# Configurações do Frontend
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')
CHECKOUT_URL = f"{FRONTEND_URL}/checkout"

# Configurações de Superadmin
SUPERADMIN_IDS = [id.strip() for id in os.getenv('SUPERADMIN_IDS', '').split(',') if id.strip()]

# Caches globais com TTL (5 minutos)
empresas_cache = TTLCache(maxsize=1000, ttl=300)
servidores_cache = TTLCache(maxsize=1000, ttl=300)
