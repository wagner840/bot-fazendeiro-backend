
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock database and utils
# sys.modules hacks removed
# sys.modules['config'] = MagicMock()
# sys.modules['utils'] = MagicMock()
# sys.modules['database'] = MagicMock()
mock_utils = MagicMock()
def pass_through_decorator(*args, **kwargs):
    def decorator(func):
        return func
    return decorator
mock_utils.empresa_configurada = pass_through_decorator

from cogs.precos import PrecosCog

@pytest.fixture
def mock_bot():
    return AsyncMock()

@pytest.fixture
def mock_ctx():
    ctx = AsyncMock()
    ctx.author.id = 123456789
    ctx.author.display_name = "TestUser"
    ctx.guild.id = 987654321
    ctx.channel = "Channel"
    return ctx

@pytest.fixture
def cog(mock_bot):
    return PrecosCog(mock_bot)

@pytest.fixture
def mock_dependencies():
    with patch('cogs.precos.selecionar_empresa', new_callable=AsyncMock) as mock_selecionar_empresa, \
         patch('cogs.precos.get_produtos_referencia', new_callable=AsyncMock) as mock_get_ref, \
         patch('cogs.precos.get_produtos_empresa', new_callable=AsyncMock) as mock_get_empresa, \
         patch('cogs.precos.configurar_produto_empresa', new_callable=AsyncMock) as mock_config_prod, \
         patch('cogs.precos.supabase') as mock_supabase:
        
        mock_selecionar_empresa.return_value = {
            'id': 1, 'nome': 'Test Corp', 'tipo_empresa_id': 1
        }
        
        # Sample Reference Products
        mock_get_ref.return_value = [
            {'id': 10, 'codigo': 'p1', 'nome': 'Prod 1', 'categoria': 'Cat1', 'preco_minimo': 10.0, 'preco_maximo': 20.0},
            {'id': 11, 'codigo': 'p2', 'nome': 'Prod 2', 'categoria': 'Cat1', 'preco_minimo': 5.0,  'preco_maximo': 15.0}
        ]
        
        # Sample Configured Products
        mock_get_empresa.return_value = {
            'p1': {
                'id': 100,
                'preco_venda': 15.0,
                'preco_pagamento_funcionario': 3.75,
                'produtos_referencia': {'nome': 'Prod 1', 'categoria': 'Cat1'}
            }
        }
        
        mock_config_prod.return_value = True

        yield {
            'selecionar_empresa': mock_selecionar_empresa,
            'get_ref': mock_get_ref,
            'get_empresa': mock_get_empresa,
            'config_prod': mock_config_prod,
            'supabase': mock_supabase
        }

@pytest.mark.asyncio
async def test_ver_precos(cog, mock_ctx, mock_dependencies):
    await cog.ver_precos.callback(cog, mock_ctx)
    args, kwargs = mock_ctx.send.call_args
    embed = kwargs.get('embed') or args[0]
    assert embed is not None
    assert "Test Corp" in embed.description
    assert "Prod 1" in str(embed.to_dict())

@pytest.mark.asyncio
async def test_configurar_minimo(cog, mock_ctx, mock_dependencies):
    deps = mock_dependencies
    await cog.configurar_minimo.callback(cog, mock_ctx)
    
    # Should configure p1 and p2 to min prices (10.0 and 5.0)
    assert deps['config_prod'].call_count == 2
    # Verify call args for first product (id 10, min 10.0)
    # config_prod(empresa_id, prod_id, pv, pf)
    # Check if any call matches
    calls = deps['config_prod'].call_args_list
    # call(1, 10, 10.0, 2.5) -> p1
    found = False
    for c in calls:
        if c.args[1] == 10 and c.args[2] == 10.0:
            found = True
            break
    assert found
    assert mock_ctx.send.called # Success embed

@pytest.mark.asyncio
async def test_configurar_medio(cog, mock_ctx, mock_dependencies):
    deps = mock_dependencies
    await cog.configurar_medio.callback(cog, mock_ctx)
    # (10+20)/2 = 15.0
    calls = deps['config_prod'].call_args_list
    found = False
    for c in calls:
        if c.args[1] == 10 and c.args[2] == 15.0:
            found = True
            break
    assert found

@pytest.mark.asyncio
async def test_configurar_maximo(cog, mock_ctx, mock_dependencies):
    deps = mock_dependencies
    await cog.configurar_maximo.callback(cog, mock_ctx)
    # Max 20.0
    calls = deps['config_prod'].call_args_list
    found = False
    for c in calls:
        if c.args[1] == 10 and c.args[2] == 20.0:
            found = True
            break
    assert found

@pytest.mark.asyncio
async def test_configurar_comissao(cog, mock_ctx, mock_dependencies):
    deps = mock_dependencies
    
    # Test setting commission to 50%
    await cog.configurar_comissao.callback(cog, mock_ctx, porcentagem=50.0)
    
    deps['supabase'].table.assert_called_with('produtos_empresa')
    # Update should be called for existing products
    # Current product p1 price 15.0. New func price = 15.0 * 0.5 = 7.5
    # We can check if update was called
    # deps['supabase'].table().update().eq().execute()
    assert deps['supabase'].table.return_value.update.called
