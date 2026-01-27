
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock database and dependencies
# sys.modules hacks removed
# sys.modules['config'] = MagicMock()
# sys.modules['database'] = MagicMock()
from config import empresas_cache, servidores_cache

# We need to ensure AdminCog imports verify these mocks or we mock where it imports
# cogs/admin.py imports from config and database.

from cogs.admin import AdminCog

@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.wait_for = AsyncMock()
    return bot

@pytest.fixture
def mock_ctx(mock_bot):
    ctx = AsyncMock()
    ctx.bot = mock_bot
    ctx.guild.id = 12345
    ctx.guild.name = "Test Guild"
    ctx.author.id = 999
    ctx.author.display_name = "Admin User"
    return ctx

@pytest.fixture
def cog(mock_bot):
    return AdminCog(mock_bot)

@pytest.fixture
def mock_env():
    with patch('cogs.admin.get_servidor_by_guild', new_callable=AsyncMock) as mock_get_server, \
         patch('cogs.admin.get_empresas_by_guild', new_callable=AsyncMock) as mock_get_empresas, \
         patch('cogs.admin.selecionar_empresa', new_callable=AsyncMock) as mock_selecionar, \
         patch('cogs.admin.supabase') as mock_supabase:
        
        mock_get_server.return_value = {'id': 1, 'nome': 'Server 1'}
        mock_get_empresas.return_value = [{'id': 1, 'nome': 'Empresa 1', 'modo_pagamento': 'producao', 'ativo': True}]
        mock_selecionar.return_value = {'id': 1, 'nome': 'Empresa 1', 'modo_pagamento': 'producao'}
        
        yield {
            'get_server': mock_get_server,
            'get_empresas': mock_get_empresas,
            'selecionar': mock_selecionar,
            'supabase': mock_supabase
        }

@pytest.mark.asyncio
async def test_limpar_cache(cog, mock_ctx, mock_env):
    # Populate cache
    servidores_cache['12345'] = 'data'
    empresas_cache['12345'] = 'data'
    
    await cog.limpar_cache.callback(cog, mock_ctx)
    
    assert '12345' not in servidores_cache
    assert '12345' not in empresas_cache
    assert mock_ctx.send.called
    
    args, kwargs = mock_ctx.send.call_args
    embed = kwargs.get('embed') or args[0]
    assert "Cache Limpo" in embed.title

@pytest.mark.asyncio
async def test_listar_usuarios(cog, mock_ctx, mock_env):
    deps = mock_env
    # Mock supabase response
    mock_select = MagicMock()
    mock_select.data = [
        {'nome': 'Admin', 'role': 'admin', 'discord_id': '1'},
        {'nome': 'Func', 'role': 'funcionario', 'discord_id': '2'}
    ]
    deps['supabase'].table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_select
    
    await cog.listar_usuarios.callback(cog, mock_ctx)
    
    assert mock_ctx.send.called
    args, kwargs = mock_ctx.send.call_args
    embed = kwargs.get('embed') or (args[0] if args else None)
    assert embed is not None
    assert "Usuários" in embed.title
    assert "Admin" in str(embed.to_dict())
    assert "Func" in str(embed.to_dict())

@pytest.mark.asyncio
async def test_promover_usuario(cog, mock_ctx, mock_env):
    deps = mock_env
    member = MagicMock()
    member.id = 2
    member.display_name = "UserToPromote"
    member.mention = "@UserToPromote"
    
    # Mock existing user
    mock_select = MagicMock()
    mock_select.data = [{'id': 55, 'role': 'funcionario'}]
    deps['supabase'].table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_select
    
    # Patch database functions
    with patch('database.get_usuario_frontend', new_callable=AsyncMock) as mock_get_u, \
         patch('database.atualizar_role_usuario_frontend', new_callable=AsyncMock) as mock_upd:
         
        mock_get_u.return_value = {'id': 55, 'role': 'funcionario'}
        mock_upd.return_value = True

        await cog.promover_admin.callback(cog, mock_ctx, membro=member)
        
        # Verify call to the mock
        mock_upd.assert_called_with(55, 'admin')

@pytest.mark.asyncio
async def test_modo_pagamento_interactive(cog, mock_ctx, mock_env, mock_bot):
    deps = mock_env
    
    # Mock interaction
    msg = AsyncMock()
    msg.content = "2" # Entrega
    msg.author = mock_ctx.author
    msg.channel = mock_ctx.channel
    mock_bot.wait_for.return_value = msg
    
    # Mock database update
    with patch('database.atualizar_modo_pagamento', new_callable=AsyncMock) as mock_update:
        mock_update.return_value = True
        
        await cog.definir_modo_pagamento.callback(cog, mock_ctx)
        
        mock_update.assert_called_with(1, 'entrega')
        assert mock_ctx.send.called
        # Check success message
        args, kwargs = mock_ctx.send.call_args
        last_msg = args[0] if args else kwargs.get('embed', '') # actually it sends text string at end
        # await ctx.send(f"✅ ...") -> args[0]
        # But wait, it sends embed first then success msg?
        # send called multiple times.
        # call_args matches LAST call.
        # last call is await ctx.send(f"✅ ...") which is args[0].
        # So args[0] should work here.
        assert "ENTREGA" in str(last_msg).upper()

@pytest.mark.asyncio
async def test_remover_acesso_proprio(cog, mock_ctx, mock_env):
    # Try to remove self
    member = MagicMock()
    member.id = 999 
    
    await cog.remover_acesso.callback(cog, mock_ctx, membro=member)
    
    assert mock_ctx.send.called
    args, kwargs = mock_ctx.send.call_args
    text = args[0] if args else kwargs.get('embed', '')
    assert "não pode remover seu próprio acesso" in str(text)
