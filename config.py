"""
Bot Multi-Empresa Downtown - Configurações
Carrega variáveis de ambiente e inicializa conexões.
"""

import os
import re
from cachetools import TTLCache
from dotenv import load_dotenv
from supabase import create_client, Client

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

# Cliente Supabase
supabase: Client = create_client(SUPABASE_URL, KEY_TO_USE)

# Configurações do Asaas
ASAAS_API_KEY = os.getenv('ASAAS_API_KEY')
# Prioriza URL de produção se não for especificada
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
