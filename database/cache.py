"""
Database cache management functions.
"""

from config import empresas_cache, servidores_cache


def limpar_cache_global():
    """Limpa todos os caches."""
    empresas_cache.clear()
    servidores_cache.clear()


def limpar_cache_empresa(guild_id: str):
    """Limpa cache de uma empresa específica."""
    if guild_id in empresas_cache:
        del empresas_cache[guild_id]


def limpar_cache_servidor(guild_id: str):
    """Limpa cache de um servidor específico."""
    if guild_id in servidores_cache:
        del servidores_cache[guild_id]
