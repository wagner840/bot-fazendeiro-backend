
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock database and dependencies
sys.modules['config'] = MagicMock()
sys.modules['database'] = MagicMock()
sys.modules['aiohttp'] = MagicMock()

from cogs.assinatura import Assinatura

@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.is_owner = AsyncMock(return_value=False)
    # get_guild is synchronous
    mock_guild = MagicMock()
    mock_guild.name = "Test Guild"
    bot.get_guild.return_value = mock_guild
    bot.wait_for = AsyncMock()
    return bot

@pytest.fixture
def mock_ctx(mock_bot):
    ctx = AsyncMock()
    ctx.bot = mock_bot
    ctx.guild.id = 12345
    ctx.guild.name = "Test Guild"
    ctx.author.id = 999
    return ctx

@pytest.fixture
def cog(mock_bot):
    return Assinatura(mock_bot)

@pytest.fixture
def mock_env():
    with patch('cogs.assinatura.verificar_assinatura_servidor', new_callable=AsyncMock) as mock_verificar, \
         patch('cogs.assinatura.get_planos_disponiveis', new_callable=AsyncMock) as mock_get_planos, \
         patch('cogs.assinatura.adicionar_tester', new_callable=AsyncMock) as mock_add_tester, \
         patch('cogs.assinatura.listar_testers', new_callable=AsyncMock) as mock_list_testers, \
         patch('cogs.assinatura.simular_pagamento', new_callable=AsyncMock) as mock_sim_pay, \
         patch('cogs.assinatura.SUPERADMIN_IDS', ['999']):  # Mock our user as superadmin
        
        mock_verificar.return_value = {
            'ativa': True,
            'status': 'active',
            'plano_nome': 'Pro',
            'dias_restantes': 30,
            'data_expiracao': '2025-12-31'
        }
        
        mock_get_planos.return_value = [
            {'nome': 'Mensal', 'preco': 20.0, 'duracao_dias': 30, 'descricao': 'Desc'}
        ]
        
        yield {
            'verificar': mock_verificar,
            'get_planos': mock_get_planos,
            'add_tester': mock_add_tester,
            'list_testers': mock_list_testers,
            'sim_pay': mock_sim_pay
        }

@pytest.mark.asyncio
async def test_ver_assinatura_ativa(cog, mock_ctx, mock_env):
    await cog.ver_assinatura.callback(cog, mock_ctx)
    args, kwargs = mock_ctx.send.call_args
    embed = kwargs.get('embed') or args[0]
    assert embed is not None
    assert "Assinatura Ativa" in embed.title
    assert "Pro" in str(embed.to_dict())

@pytest.mark.asyncio
async def test_listar_planos(cog, mock_ctx, mock_env):
    await cog.listar_planos.callback(cog, mock_ctx)
    args, kwargs = mock_ctx.send.call_args
    embed = kwargs.get('embed') or args[0]
    assert embed is not None
    assert "Planos Disponíveis" in embed.title
    assert "Mensal" in str(embed.to_dict())

@pytest.mark.asyncio
async def test_superadmin_add_tester(cog, mock_ctx, mock_env):
    mock_env['add_tester'].return_value = True
    await cog.add_tester.callback(cog, mock_ctx, guild_id="111")
    assert mock_env['add_tester'].called
    assert mock_ctx.send.called
    assert "adicionado como tester" in mock_ctx.send.call_args[0][0]

@pytest.mark.asyncio
async def test_validar_pagamento_pendente(cog, mock_ctx):
    # Need to mock local imports inside validarpagamento
    with patch('database.buscar_pagamento_pendente_usuario', new_callable=AsyncMock) as mock_buscar, \
         patch('aiohttp.ClientSession') as MockSession, \
         patch('config.ASAAS_API_KEY', "key"), \
         patch('database.ativar_assinatura_servidor', new_callable=AsyncMock) as mock_ativar, \
         patch('config.supabase') as mock_supabase:
         
        # Mock payment found
        mock_buscar.return_value = {
            'pix_id': 'pix_123',
            'valor': 20.0,
            'plano_id': 1,
            'status': 'pendente',
            'guild_id': str(mock_ctx.guild.id)
        }
        
        # Mock Asaas API response
        session_mock = MagicMock()
        MockSession.return_value = session_mock
        session_mock.__aenter__.return_value = session_mock
        
        response_ctx = MagicMock()
        session_mock.get.return_value = response_ctx
        
        response = AsyncMock()
        response.status = 200
        response.json.return_value = {'status': 'RECEIVED'}
        response_ctx.__aenter__.return_value = response
        
        mock_ativar.return_value = True
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute = MagicMock()

        await cog.validar_pagamento.callback(cog, mock_ctx)
        
        assert mock_ctx.send.call_count >= 2
        last_call = mock_ctx.send.call_args[0][0]
        success_phrases = ["Assinatura ativa", "Parabéns", "Pagamento confirmado"]
        assert any(phrase in last_call for phrase in success_phrases)
        assert mock_ativar.called
