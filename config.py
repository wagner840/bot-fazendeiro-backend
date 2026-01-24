"""
Bot Multi-Empresa Downtown - Configurações
Carrega variáveis de ambiente e inicializa conexões.
"""

import os
import re
from dotenv import load_dotenv
from supabase import create_client, Client

# Carrega variáveis de ambiente
load_dotenv()

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

# Regex para parsing de produtos (ex: pa2, va10, gp5)
PRODUTO_REGEX = re.compile(r'([a-zA-Z_]+)(\d+)')

# Caches globais
empresas_cache = {}
servidores_cache = {}
