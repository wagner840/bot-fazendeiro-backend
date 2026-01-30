"""
Testes para a funcionalidade de comissão por modo de pagamento (entrega vs producao).
Verifica que:
- Modo 'entrega': vendedor ganha comissão independente de quem produziu
- Modo 'producao': só ganha comissão se produziu os itens
"""

import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestDatabaseFunctions:
    """Testes para as novas funções de banco de dados."""

    @pytest.mark.asyncio
    async def test_get_estoque_global_detalhado(self):
        """Testa se get_estoque_global_detalhado retorna dados com preço."""
        with patch('database.supabase') as mock_supabase, \
             patch('database.get_produtos_empresa', new_callable=AsyncMock) as mock_get_produtos:

            # Mock produtos
            mock_get_produtos.return_value = {
                'prod1': {
                    'produtos_referencia': {'nome': 'Produto 1'},
                    'preco_pagamento_funcionario': 10.0
                },
                'prod2': {
                    'produtos_referencia': {'nome': 'Produto 2'},
                    'preco_pagamento_funcionario': 20.0
                }
            }

            # Mock estoque - 2 funcionários com mesmo produto
            mock_response = MagicMock()
            mock_response.data = [
                {'id': 1, 'funcionario_id': 101, 'produto_codigo': 'prod1', 'quantidade': 50},
                {'id': 2, 'funcionario_id': 102, 'produto_codigo': 'prod1', 'quantidade': 30},
                {'id': 3, 'funcionario_id': 101, 'produto_codigo': 'prod2', 'quantidade': 20},
            ]
            mock_supabase.table.return_value.select.return_value.eq.return_value.gt.return_value.execute.return_value = mock_response

            from database import get_estoque_global_detalhado
            result = await get_estoque_global_detalhado(empresa_id=1)

            # Verifica estrutura
            assert 'prod1' in result
            assert 'prod2' in result

            # Verifica quantidade total
            assert result['prod1']['quantidade'] == 80  # 50 + 30
            assert result['prod2']['quantidade'] == 20

            # Verifica preço funcionário
            assert result['prod1']['preco_funcionario'] == 10.0
            assert result['prod2']['preco_funcionario'] == 20.0

            # Verifica registros individuais
            assert len(result['prod1']['registros']) == 2
            assert len(result['prod2']['registros']) == 1

    @pytest.mark.asyncio
    async def test_remover_do_estoque_global_success(self):
        """Testa remoção do estoque global com sucesso."""
        with patch('database.supabase') as mock_supabase, \
             patch('database.get_produtos_empresa', new_callable=AsyncMock) as mock_get_produtos:

            mock_get_produtos.return_value = {
                'prod1': {
                    'produtos_referencia': {'nome': 'Produto 1'},
                    'preco_pagamento_funcionario': 15.0
                }
            }

            # Mock estoque disponível
            mock_response = MagicMock()
            mock_response.data = [
                {'id': 1, 'funcionario_id': 101, 'quantidade': 30},
                {'id': 2, 'funcionario_id': 102, 'quantidade': 20},
            ]
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gt.return_value.order.return_value.execute.return_value = mock_response

            from database import remover_do_estoque_global
            result = await remover_do_estoque_global(empresa_id=1, codigo='prod1', quantidade=25)

            # Verifica resultado
            assert result is not None
            assert result['removido'] == 25
            assert result['preco_funcionario'] == 15.0
            assert result['nome'] == 'Produto 1'

            # Verifica que chamou update/delete no supabase
            assert mock_supabase.table.called

    @pytest.mark.asyncio
    async def test_remover_do_estoque_global_insufficient(self):
        """Testa erro quando não há estoque suficiente."""
        with patch('database.supabase') as mock_supabase, \
             patch('database.get_produtos_empresa', new_callable=AsyncMock) as mock_get_produtos:

            mock_get_produtos.return_value = {
                'prod1': {
                    'produtos_referencia': {'nome': 'Produto 1'},
                    'preco_pagamento_funcionario': 15.0
                }
            }

            # Mock estoque insuficiente
            mock_response = MagicMock()
            mock_response.data = [
                {'id': 1, 'funcionario_id': 101, 'quantidade': 10},
            ]
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gt.return_value.order.return_value.execute.return_value = mock_response

            from database import remover_do_estoque_global
            result = await remover_do_estoque_global(empresa_id=1, codigo='prod1', quantidade=50)

            # Deve retornar erro
            assert result is not None
            assert 'erro' in result
            assert 'insuficiente' in result['erro'].lower()


class TestEntregarModoEntrega:
    """Testes para o modo de pagamento 'entrega'."""

    @pytest.fixture
    def mock_bot(self):
        return AsyncMock()

    @pytest.fixture
    def mock_ctx(self):
        ctx = AsyncMock()
        ctx.author.id = 123456789
        ctx.author.display_name = "VendedorTeste"
        ctx.guild.id = 987654321
        ctx.channel = MagicMock()
        return ctx

    @pytest.fixture
    def cog(self, mock_bot):
        from cogs.producao import ProducaoCog
        return ProducaoCog(mock_bot)

    @pytest.mark.asyncio
    async def test_entregar_modo_entrega_ganha_comissao(self, cog, mock_ctx):
        """
        Testa que no modo 'entrega', o vendedor ganha comissão
        mesmo vendendo produtos que não produziu.
        """
        with patch('cogs.producao.selecionar_empresa', new_callable=AsyncMock) as mock_empresa, \
             patch('cogs.producao.get_funcionario_by_discord_id', new_callable=AsyncMock) as mock_get_func, \
             patch('cogs.producao.get_estoque_global_detalhado', new_callable=AsyncMock) as mock_estoque_global, \
             patch('cogs.producao.remover_do_estoque_global', new_callable=AsyncMock) as mock_remover_global, \
             patch('cogs.producao.supabase') as mock_supabase:

            # Empresa em modo ENTREGA
            mock_empresa.return_value = {
                'id': 1,
                'nome': 'Empresa Teste',
                'modo_pagamento': 'entrega'  # MODO ENTREGA
            }

            # Funcionário que vai entregar (não produziu nada)
            mock_get_func.return_value = {'id': 201, 'nome': 'Vendedor'}

            # Estoque GLOBAL tem os produtos (produzidos por outro funcionário)
            mock_estoque_global.return_value = {
                'prod1': {
                    'codigo': 'prod1',
                    'nome': 'Produto 1',
                    'quantidade': 100,
                    'preco_funcionario': 10.0,
                    'registros': [{'id': 1, 'funcionario_id': 999, 'quantidade': 100}]  # Outro funcionário produziu
                }
            }

            # Mock da encomenda
            mock_select = MagicMock()
            mock_select.data = [{
                'id': 500,
                'status': 'pendente',
                'itens_json': [{'codigo': 'prod1', 'quantidade': 20, 'quantidade_entregue': 0, 'nome': 'Produto 1'}],
                'valor_total': 400.0,
                'comprador': 'Cliente X'
            }]
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_select

            # Executa entrega
            await cog.entregar_encomenda.callback(cog, mock_ctx, encomenda_id=500)

            # Verifica que usou estoque global
            mock_estoque_global.assert_called_once()

            # Verifica que removeu do estoque global
            mock_remover_global.assert_called_with(1, 'prod1', 20)

            # Verifica que registrou transação de comissão
            insert_calls = [call for call in mock_supabase.table.return_value.insert.call_args_list]
            assert len(insert_calls) > 0

            # Verifica embed de sucesso
            assert mock_ctx.send.called
            embed_call = mock_ctx.send.call_args
            embed = embed_call.kwargs.get('embed') or embed_call.args[0]

            # Deve mostrar comissão
            embed_dict = embed.to_dict()
            assert any('Comissão' in str(f.get('name', '')) or 'Comissão' in str(f.get('value', ''))
                      for f in embed_dict.get('fields', []))

    @pytest.mark.asyncio
    async def test_entregar_modo_entrega_estoque_insuficiente(self, cog, mock_ctx):
        """
        Testa que no modo 'entrega', se não há estoque global suficiente,
        a entrega é bloqueada (não permite entregar sem estoque).
        """
        with patch('cogs.producao.selecionar_empresa', new_callable=AsyncMock) as mock_empresa, \
             patch('cogs.producao.get_funcionario_by_discord_id', new_callable=AsyncMock) as mock_get_func, \
             patch('cogs.producao.get_estoque_global_detalhado', new_callable=AsyncMock) as mock_estoque_global, \
             patch('cogs.producao.supabase') as mock_supabase:

            # Empresa em modo ENTREGA
            mock_empresa.return_value = {
                'id': 1,
                'nome': 'Empresa Teste',
                'modo_pagamento': 'entrega'
            }

            mock_get_func.return_value = {'id': 201, 'nome': 'Vendedor'}

            # Estoque GLOBAL insuficiente
            mock_estoque_global.return_value = {
                'prod1': {
                    'codigo': 'prod1',
                    'nome': 'Produto 1',
                    'quantidade': 5,  # Só tem 5
                    'preco_funcionario': 10.0,
                    'registros': []
                }
            }

            # Encomenda precisa de 20
            mock_select = MagicMock()
            mock_select.data = [{
                'id': 501,
                'status': 'pendente',
                'itens_json': [{'codigo': 'prod1', 'quantidade': 20, 'quantidade_entregue': 0, 'nome': 'Produto 1'}],
                'valor_total': 400.0,
                'comprador': 'Cliente Y'
            }]
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_select

            await cog.entregar_encomenda.callback(cog, mock_ctx, encomenda_id=501)

            # Verifica que mostrou erro de estoque insuficiente
            assert mock_ctx.send.called
            embed_call = mock_ctx.send.call_args
            embed = embed_call.kwargs.get('embed') or embed_call.args[0]

            # Deve ser embed de erro (vermelho)
            assert embed.color.value == 0xe74c3c  # discord.Color.red()


class TestEntregarModoProducao:
    """Testes para o modo de pagamento 'producao' (lógica original)."""

    @pytest.fixture
    def mock_bot(self):
        return AsyncMock()

    @pytest.fixture
    def mock_ctx(self):
        ctx = AsyncMock()
        ctx.author.id = 123456789
        ctx.author.display_name = "ProdutorTeste"
        ctx.guild.id = 987654321
        ctx.channel = MagicMock()
        return ctx

    @pytest.fixture
    def cog(self, mock_bot):
        from cogs.producao import ProducaoCog
        return ProducaoCog(mock_bot)

    @pytest.mark.asyncio
    async def test_entregar_modo_producao_com_estoque_pessoal(self, cog, mock_ctx):
        """
        Testa que no modo 'producao', funcionário com estoque pessoal
        ganha comissão normalmente.
        """
        with patch('cogs.producao.selecionar_empresa', new_callable=AsyncMock) as mock_empresa, \
             patch('cogs.producao.get_funcionario_by_discord_id', new_callable=AsyncMock) as mock_get_func, \
             patch('cogs.producao.get_estoque_funcionario', new_callable=AsyncMock) as mock_estoque_func, \
             patch('cogs.producao.remover_do_estoque', new_callable=AsyncMock) as mock_remover, \
             patch('cogs.producao.supabase') as mock_supabase:

            # Empresa em modo PRODUCAO
            mock_empresa.return_value = {
                'id': 1,
                'nome': 'Empresa Teste',
                'modo_pagamento': 'producao'  # MODO PRODUCAO
            }

            mock_get_func.return_value = {'id': 201, 'nome': 'Produtor'}

            # Funcionário TEM o produto no estoque pessoal
            mock_estoque_func.return_value = [
                {'produto_codigo': 'prod1', 'quantidade': 50, 'preco_funcionario': 10.0}
            ]

            mock_select = MagicMock()
            mock_select.data = [{
                'id': 600,
                'status': 'pendente',
                'itens_json': [{'codigo': 'prod1', 'quantidade': 20, 'quantidade_entregue': 0, 'nome': 'Produto 1'}],
                'valor_total': 400.0,
                'comprador': 'Cliente Z'
            }]
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_select

            await cog.entregar_encomenda.callback(cog, mock_ctx, encomenda_id=600)

            # Verifica que usou estoque pessoal (não global)
            mock_estoque_func.assert_called_once()

            # Verifica que removeu do estoque pessoal
            mock_remover.assert_called_with(201, 1, 'prod1', 20)

            # Verifica sucesso
            assert mock_ctx.send.called

    @pytest.mark.asyncio
    async def test_entregar_modo_producao_sem_estoque_pessoal(self, cog, mock_bot, mock_ctx):
        """
        Testa que no modo 'producao', funcionário SEM estoque pessoal
        NÃO ganha comissão (lógica original).
        """
        with patch('cogs.producao.selecionar_empresa', new_callable=AsyncMock) as mock_empresa, \
             patch('cogs.producao.get_funcionario_by_discord_id', new_callable=AsyncMock) as mock_get_func, \
             patch('cogs.producao.get_estoque_funcionario', new_callable=AsyncMock) as mock_estoque_func, \
             patch('cogs.producao.supabase') as mock_supabase:

            # Empresa em modo PRODUCAO
            mock_empresa.return_value = {
                'id': 1,
                'nome': 'Empresa Teste',
                'modo_pagamento': 'producao'
            }

            mock_get_func.return_value = {'id': 201, 'nome': 'Vendedor Sem Estoque'}

            # Funcionário NÃO tem o produto (estoque vazio)
            mock_estoque_func.return_value = []

            mock_select = MagicMock()
            mock_select.data = [{
                'id': 601,
                'status': 'pendente',
                'itens_json': [{'codigo': 'prod1', 'quantidade': 20, 'quantidade_entregue': 0, 'nome': 'Produto 1'}],
                'valor_total': 400.0,
                'comprador': 'Cliente W'
            }]
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_select

            # Mock confirmação do usuário
            msg = AsyncMock()
            msg.content = "sim"
            msg.author = mock_ctx.author
            msg.channel = mock_ctx.channel
            mock_bot.wait_for.return_value = msg

            await cog.entregar_encomenda.callback(cog, mock_ctx, encomenda_id=601)

            # Deve ter mostrado aviso de estoque insuficiente
            calls = mock_ctx.send.call_args_list
            warning_shown = False
            for call in calls:
                embed = call.kwargs.get('embed') or (call.args[0] if call.args else None)
                if embed and hasattr(embed, 'title'):
                    if 'Insuficiente' in str(embed.title):
                        warning_shown = True
                        break

            assert warning_shown, "Deveria mostrar aviso de estoque insuficiente"


class TestModoPagamentoSwitch:
    """Testes para verificar que a troca de modo funciona."""

    @pytest.fixture
    def mock_bot(self):
        return AsyncMock()

    @pytest.fixture
    def mock_ctx(self):
        ctx = AsyncMock()
        ctx.author.id = 123456789
        ctx.author.display_name = "TestUser"
        ctx.guild.id = 987654321
        ctx.channel = MagicMock()
        return ctx

    @pytest.fixture
    def cog(self, mock_bot):
        from cogs.producao import ProducaoCog
        return ProducaoCog(mock_bot)

    @pytest.mark.asyncio
    async def test_modo_pagamento_detectado_corretamente(self, cog, mock_ctx):
        """Verifica que o modo de pagamento é lido corretamente da empresa."""
        with patch('cogs.producao.selecionar_empresa', new_callable=AsyncMock) as mock_empresa, \
             patch('cogs.producao.get_funcionario_by_discord_id', new_callable=AsyncMock) as mock_get_func, \
             patch('cogs.producao.get_estoque_global_detalhado', new_callable=AsyncMock) as mock_global, \
             patch('cogs.producao.get_estoque_funcionario', new_callable=AsyncMock) as mock_pessoal, \
             patch('cogs.producao.supabase') as mock_supabase:

            mock_get_func.return_value = {'id': 201, 'nome': 'Test'}
            mock_global.return_value = {}
            mock_pessoal.return_value = []

            mock_select = MagicMock()
            mock_select.data = [{
                'id': 700, 'status': 'pendente',
                'itens_json': [{'codigo': 'x', 'quantidade': 1, 'quantidade_entregue': 0, 'nome': 'X'}],
                'valor_total': 10.0, 'comprador': 'C'
            }]
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_select

            # Teste modo ENTREGA
            mock_empresa.return_value = {'id': 1, 'nome': 'E', 'modo_pagamento': 'entrega'}
            await cog.entregar_encomenda.callback(cog, mock_ctx, encomenda_id=700)
            mock_global.assert_called()  # Deve usar estoque global

            mock_global.reset_mock()
            mock_pessoal.reset_mock()

            # Teste modo PRODUCAO
            mock_empresa.return_value = {'id': 1, 'nome': 'E', 'modo_pagamento': 'producao'}
            await cog.entregar_encomenda.callback(cog, mock_ctx, encomenda_id=700)
            mock_pessoal.assert_called()  # Deve usar estoque pessoal
