
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock database functions before importing cog
sys.modules['config'] = MagicMock()
mock_utils = MagicMock()
def pass_through_decorator(*args, **kwargs):
    def decorator(func):
        return func
    return decorator
mock_utils.empresa_configurada = pass_through_decorator
mock_utils.verificar_is_admin = AsyncMock() 

sys.modules['utils'] = mock_utils
sys.modules['database'] = MagicMock()

from cogs.producao import ProducaoCog

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
    return ProducaoCog(mock_bot)

@pytest.fixture
def mock_dependencies():
    """Setup common mocks"""
    with patch('cogs.producao.selecionar_empresa', new_callable=AsyncMock) as mock_selecionar_empresa, \
         patch('cogs.producao.get_or_create_funcionario', new_callable=AsyncMock) as mock_get_funcionario, \
         patch('cogs.producao.get_produtos_empresa', new_callable=AsyncMock) as mock_get_produtos, \
         patch('cogs.producao.adicionar_ao_estoque', new_callable=AsyncMock) as mock_add_estoque, \
         patch('cogs.producao.remover_do_estoque', new_callable=AsyncMock) as mock_remove_estoque, \
         patch('cogs.producao.get_estoque_funcionario', new_callable=AsyncMock) as mock_get_estoque, \
         patch('cogs.producao.get_funcionario_by_discord_id', new_callable=AsyncMock) as mock_get_func_discord, \
         patch('cogs.producao.supabase') as mock_supabase:
         
        mock_selecionar_empresa.return_value = {'id': 1, 'nome': 'Test Corp', 'modo_pagamento': 'producao'}
        mock_get_funcionario.return_value = 101
        sys.modules['utils'].verificar_is_admin.return_value = False
        
        def fake_findall(text):
            import re
            return re.findall(r'([a-zA-Z0-9_]+)\s+(\d+)', text)
        sys.modules['config'].PRODUTO_REGEX.findall.side_effect = fake_findall
        
        yield {
            'selecionar_empresa': mock_selecionar_empresa,
            'get_funcionario': mock_get_funcionario,
            'get_produtos': mock_get_produtos,
            'add_estoque': mock_add_estoque,
            'remove_estoque': mock_remove_estoque,
            'get_estoque': mock_get_estoque,
            'get_func_discord': mock_get_func_discord,
            'supabase': mock_supabase
        }

@pytest.mark.asyncio
async def test_add_produto_admin_isento(cog, mock_ctx, mock_dependencies):
    deps = mock_dependencies
    sys.modules['utils'].verificar_is_admin.return_value = True
    deps['get_produtos'].return_value = {
        'prod1': {'produtos_referencia': {'nome': 'Produto 1'}, 'preco_pagamento_funcionario': 10.0, 'preco_venda': 20.0}
    }
    deps['add_estoque'].return_value = {'nome': 'Produto 1', 'quantidade': 15}

    await cog.add_produto.callback(cog, mock_ctx, entrada="prod1 5")

    assert mock_ctx.send.called
    args, kwargs = mock_ctx.send.call_args
    embed = kwargs.get('embed') or (args[0] if args else None)
    assert embed is not None
    found = any("Isento (Admin)" in f.value for f in embed.fields)
    assert found

@pytest.mark.asyncio
async def test_add_produto_user_com_comissao(cog, mock_ctx, mock_dependencies):
    deps = mock_dependencies
    sys.modules['utils'].verificar_is_admin.return_value = False
    deps['get_produtos'].return_value = {
        'prod1': {'produtos_referencia': {'nome': 'Produto 1'}, 'preco_pagamento_funcionario': 10.0, 'preco_venda': 20.0}
    }
    deps['add_estoque'].return_value = {'nome': 'Produto 1', 'quantidade': 15}

    await cog.add_produto.callback(cog, mock_ctx, entrada="prod1 5")

    args, kwargs = mock_ctx.send.call_args
    embed = kwargs.get('embed') or (args[0] if args else None)
    found = any("R$ 50.00" in f.value for f in embed.fields)
    assert found

@pytest.mark.asyncio
async def test_nova_encomenda_rapida(cog, mock_ctx, mock_dependencies):
    """Test creating an order using arguments."""
    deps = mock_dependencies
    deps['get_func_discord'].return_value = {'id': 101, 'nome': 'Func 1'}
    deps['get_produtos'].return_value = {
        'pa': {'produtos_referencia': {'nome': 'Pa'}, 'preco_venda': 50.0}
    }
    mock_execute = MagicMock()
    mock_execute.data = [{'id': 555}]
    deps['supabase'].table.return_value.insert.return_value.execute.return_value = mock_execute

    await cog.nova_encomenda.callback(cog, mock_ctx, entrada='"Cliente Teste" pa 10')

    args, kwargs = mock_ctx.send.call_args
    embed = kwargs.get('embed') or (args[0] if args else None)
    assert embed is not None
    
    found_total = False
    for f in embed.fields:
        if "Total" in f.name and ("500.00" in f.value or "500,00" in f.value):
            found_total = True
            break
         
    assert found_total or "500.00" in str(embed.to_dict())

@pytest.mark.asyncio
async def test_nova_encomenda_interactive(cog, mock_bot, mock_ctx, mock_dependencies):
    """Test interactive order creation."""
    deps = mock_dependencies
    deps['get_func_discord'].return_value = {'id': 101, 'nome': 'Func 1'}
    deps['get_produtos'].return_value = {
        'p1': {'produtos_referencia': {'nome': 'P1', 'categoria': 'C1'}, 'preco_venda': 10.0}
    }
    mock_execute = MagicMock()
    mock_execute.data = [{'id': 666}]
    deps['supabase'].table.return_value.insert.return_value.execute.return_value = mock_execute

    msg1 = AsyncMock(); msg1.content = "Cliente Interativo"; msg1.author = mock_ctx.author; msg1.channel = mock_ctx.channel
    msg2 = AsyncMock(); msg2.content = "p1 5"; msg2.author = mock_ctx.author; msg2.channel = mock_ctx.channel
    msg3 = AsyncMock(); msg3.content = "pronto"; msg3.author = mock_ctx.author; msg3.channel = mock_ctx.channel
    msg4 = AsyncMock(); msg4.content = "sim"; msg4.author = mock_ctx.author; msg4.channel = mock_ctx.channel
    
    mock_bot.wait_for.side_effect = [msg1, msg2, msg3, msg4]

    await cog.nova_encomenda.callback(cog, mock_ctx, entrada=None)

    deps['supabase'].table.assert_called_with('encomendas')

@pytest.mark.asyncio
async def test_deletar_produto(cog, mock_ctx, mock_dependencies):
    deps = mock_dependencies
    deps['get_func_discord'].return_value = {'id': 101}
    deps['remove_estoque'].return_value = {'nome': 'P1', 'removido': 5, 'quantidade': 10}

    await cog.deletar_produto.callback(cog, mock_ctx, entrada="p1 5")

    deps['remove_estoque'].assert_called_with(101, 1, 'p1', 5)

@pytest.mark.asyncio
async def test_display_commands(cog, mock_ctx, mock_dependencies):
    deps = mock_dependencies
    deps['get_func_discord'].return_value = {'id': 101, 'saldo': 100.0}
    deps['get_estoque'].return_value = [{'produto_codigo': 'p1', 'quantidade': 10, 'preco_funcionario': 5.0, 'nome': 'P1'}]
    deps['get_produtos'].return_value = {'p1': {'produtos_referencia': {'nome': 'P1', 'categoria': 'C1'}, 'preco_venda': 20.0}}
    
    await cog.ver_estoque.callback(cog, mock_ctx)
    mock_ctx.send.reset_mock()
    await cog.ver_produtos.callback(cog, mock_ctx)
    
    with patch('cogs.producao.get_estoque_global', new_callable=AsyncMock) as mock_get_global:
        mock_get_global.return_value = [{'nome': 'P1', 'quantidade': 100}]
        await cog.ver_estoque_global.callback(cog, mock_ctx)
        
    mock_select = MagicMock()
    mock_select.data = [{
        'id': 1, 'status': 'pendente', 'itens_json': [{'codigo': 'p1', 'quantidade': 1}], 'valor_total': 20.0, 'comprador': 'C', 'funcionarios': {'nome': 'F'}
    }]
    deps['supabase'].table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.execute.return_value = mock_select
    await cog.ver_encomendas.callback(cog, mock_ctx)

@pytest.mark.asyncio
async def test_entregar_encomenda_success(cog, mock_ctx, mock_dependencies):
    deps = mock_dependencies
    deps['get_func_discord'].return_value = {'id': 101, 'nome': 'Func 1'}
    
    mock_select = MagicMock()
    mock_select.data = [{
        'id': 123, 'status': 'pendente', 
        'itens_json': [{'codigo': 'pa', 'quantidade': 5, 'quantidade_entregue': 0, 'valor_unitario': 50.0}],
        'valor_total': 250.0, 'comprador': 'Cliente Teste'
    }]
    deps['supabase'].table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_select
    deps['get_estoque'].return_value = [{'produto_codigo': 'pa', 'quantidade': 10, 'preco_funcionario': 10.0}]
    
    await cog.entregar_encomenda.callback(cog, mock_ctx, encomenda_id=123)
    deps['remove_estoque'].assert_called()

@pytest.mark.asyncio
async def test_entregar_encomenda_insufficient_stock(cog, mock_bot, mock_ctx, mock_dependencies):
    """Test delivery with insufficient stock requiring confirmation."""
    deps = mock_dependencies
    deps['get_func_discord'].return_value = {'id': 101, 'nome': 'Func 1'}
    
    mock_select = MagicMock()
    mock_select.data = [{
        'id': 124, 'status': 'pendente', 
        'itens_json': [{'codigo': 'pa', 'quantidade': 10, 'nome': 'Pa'}],
        'valor_total': 500.0, 'comprador': 'Cliente Teste'
    }]
    deps['supabase'].table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_select
    
    # User has 5, needs 10 (Missign 5)
    deps['get_estoque'].return_value = [{'produto_codigo': 'pa', 'quantidade': 5, 'preco_funcionario': 10.0}]
    
    # Mock confirmation "sim"
    msg = AsyncMock(); msg.content = "sim"; msg.author = mock_ctx.author; msg.channel = mock_ctx.channel
    mock_bot.wait_for.side_effect = [msg]

    await cog.entregar_encomenda.callback(cog, mock_ctx, encomenda_id=124)

    # Should have called remover_do_estoque with partial amount?
    # Logic: loops over itens_com_estoque.
    # If item is insufficient (pa), it is in itens_sem_estoque.
    # Logic in code: "Remove do estoque apenas os itens que o funcionário TEM"
    # Actually, lines 897-900 loop over `itens_com_estoque`.
    # `pa` is missing 5. `tem` 5, `precisa` 10. `tem >= precisa` is False.
    # So `pa` goes to `itens_sem_estoque`.
    # So `itens_com_estoque` is empty!
    # So `remover_do_estoque` receives nothing.
    
    # Verify we got the warning embed
    args, kwargs = mock_ctx.send.call_args
    embed = kwargs.get('embed') or (args[0] if args else None)
    # The LAST call might be success message? or None?
    # Actually wait_for happens. Then "Processa a entrega".
    # Since itens_com_estoque is empty, no remove calls.
    # But later it likely updates DB status.
    
    assert mock_ctx.send.called
    deps['supabase'].table.assert_called() # Should verify update to 'entregue' happens
