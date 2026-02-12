"""
UI components for order (encomenda) management.
"""

from decimal import Decimal
import discord
from database import criar_encomenda
from ui_utils import create_success_embed, create_error_embed, create_info_embed, handle_interaction_error


class OrderQtyModal(discord.ui.Modal, title="Quantidade do Item"):
    def __init__(self, builder_view, produto_codigo, produto_nome, preco):
        super().__init__()
        self.builder_view = builder_view
        self.produto_codigo = produto_codigo
        self.produto_nome = produto_nome
        self.preco = preco

        self.qty = discord.ui.TextInput(
            label=f"Qtd de {produto_nome}",
            placeholder="Ex: 50",
            min_length=1, max_length=5, required=True
        )
        self.add_item(self.qty)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            qtd = int(self.qty.value)
            if qtd <= 0:
                raise ValueError
        except:
            await interaction.response.send_message(embed=create_error_embed("Erro", "Quantidade inválida."), ephemeral=True)
            return

        await self.builder_view.add_to_cart(interaction, self.produto_codigo, self.produto_nome, qtd, self.preco)


class ProductSelectOrder(discord.ui.Select):
    def __init__(self, builder_view, produtos):
        options = []
        for codigo, p in list(produtos.items())[:25]:
            nome = p['produtos_referencia']['nome']
            preco = p['preco_venda']
            options.append(discord.SelectOption(
                label=f"{nome}",
                value=codigo,
                description=f"R$ {preco:.2f}",
                emoji="📦"
            ))
        super().__init__(placeholder="Selecione um produto para adicionar...", options=options)
        self.builder_view = builder_view
        self.produtos = produtos

    async def callback(self, interaction: discord.Interaction):
        codigo = self.values[0]
        prod = self.produtos[codigo]
        await interaction.response.send_modal(
            OrderQtyModal(
                self.builder_view, codigo,
                prod['produtos_referencia']['nome'],
                float(prod['preco_venda'])
            )
        )


class OrderBuilderView(discord.ui.View):
    def __init__(self, ctx, produtos, empresa_id, func_id, comprador_nome):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.produtos = produtos
        self.empresa_id = empresa_id
        self.func_id = func_id
        self.comprador_nome = comprador_nome
        self.cart = []

        self.add_item(ProductSelectOrder(self, produtos))

    async def update_message(self, interaction: discord.Interaction):
        total = sum(i['valor'] for i in self.cart)

        embed = discord.Embed(
            title=f"📦 Nova Encomenda: {self.comprador_nome}",
            description="Adicione itens usando o menu abaixo.",
            color=discord.Color.blue()
        )

        cart_text = ""
        if not self.cart:
            cart_text = "🛒 Carrinho vazio."
        else:
            for idx, item in enumerate(self.cart):
                cart_text += f"{idx+1}. **{item['nome']}** x{item['qtd']} (R$ {item['valor']:.2f})\n"

        embed.add_field(name="Itens", value=cart_text, inline=False)
        embed.add_field(name="💰 Total", value=f"**R$ {total:.2f}**", inline=False)

        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.label == "Finalizar Encomenda":
                item.disabled = len(self.cart) == 0
                break

        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    async def add_to_cart(self, interaction: discord.Interaction, codigo, nome, qtd, preco_unit):
        valor = Decimal(str(qtd)) * Decimal(str(preco_unit))
        existing = next((i for i in self.cart if i['codigo'] == codigo), None)
        if existing:
            existing['qtd'] += qtd
            existing['valor'] += valor
        else:
            self.cart.append({
                'codigo': codigo,
                'nome': nome,
                'qtd': qtd,
                'preco_unit': preco_unit,
                'valor': valor
            })
        await self.update_message(interaction)

    @discord.ui.button(label="Finalizar Encomenda", style=discord.ButtonStyle.green, emoji="✅", disabled=True, row=1)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.cart:
            return
        itens_db = [{
            'codigo': i['codigo'],
            'nome': i['nome'],
            'quantidade': i['qtd'],
            'quantidade_entregue': 0,
            'valor_unitario': i['preco_unit'],
            'valor': float(i['valor'])
        } for i in self.cart]
        try:
            encomenda = await criar_encomenda(
                empresa_id=self.empresa_id,
                comprador=self.comprador_nome,
                itens=itens_db
            )
            if not encomenda:
                raise Exception("Erro ao criar encomenda via DB.")

            embed = create_success_embed(f"Encomenda #{encomenda['id']} Criada!", f"Cliente: {self.comprador_nome}")
            embed.add_field(name="Total", value=f"R$ {encomenda['valor_total']:.2f}")
            embed.set_footer(text="Use !entregar para finalizar a entrega.")
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
        except Exception as e:
            await handle_interaction_error(interaction, e)

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.red, emoji="❌", row=1)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_error_embed("Cancelado", "Encomenda cancelada."), view=None)
        self.stop()


class ClientNameModal(discord.ui.Modal, title="Nome do Cliente"):
    def __init__(self, ctx, produtos, empresa_id, func_id):
        super().__init__()
        self.ctx = ctx
        self.produtos = produtos
        self.empresa_id = empresa_id
        self.func_id = func_id

        self.nome = discord.ui.TextInput(
            label="Nome do Comprador",
            placeholder="Ex: Delegacia, Hospital...",
            min_length=3,
            required=True
        )
        self.add_item(self.nome)

    async def on_submit(self, interaction: discord.Interaction):
        view = OrderBuilderView(self.ctx, self.produtos, self.empresa_id, self.func_id, self.nome.value)
        embed = create_info_embed(f"📦 Nova Encomenda: {self.nome.value}", "Selecione os produtos abaixo para montar o pedido.")
        embed.add_field(name="Carrinho", value="Vazio", inline=False)
        await interaction.response.send_message(embed=embed, view=view)
