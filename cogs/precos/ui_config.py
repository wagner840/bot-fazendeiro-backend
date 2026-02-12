"""
UI components for price configuration.
"""

import discord
from database import configurar_produto_empresa
from logging_config import logger


class ConfigPrecoModal(discord.ui.Modal, title="Editar Preco"):
    def __init__(self, produto: dict, empresa_id: int):
        super().__init__()
        self.produto = produto
        self.empresa_id = empresa_id

        self.preco_venda = discord.ui.TextInput(
            label=f"Preco Venda ({produto['nome']})",
            placeholder=f"Min: {produto['preco_minimo']} | Max: {produto['preco_maximo']}",
            default=str(produto.get('preco_venda', '')),
            required=True
        )
        self.add_item(self.preco_venda)

        self.preco_func = discord.ui.TextInput(
            label="Pagamento Funcionario (%)",
            placeholder="Ex: 25 para 25%",
            default=str(produto.get('preco_pagamento_funcionario', '')),
            required=True
        )
        self.add_item(self.preco_func)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            pv = float(self.preco_venda.value.replace(',', '.'))
            # pf now represents percentage
            porcentagem = float(self.preco_func.value.replace(',', '.').replace('%', ''))

            # Calculate actual value based on percentage
            pf = round(pv * (porcentagem / 100), 2)

            await configurar_produto_empresa(self.empresa_id, self.produto['id'], pv, pf)

            # Feedback
            embed = discord.Embed(
                title=f"OK {self.produto['nome']} Atualizado!",
                color=discord.Color.green()
            )
            embed.add_field(name="Venda", value=f"R$ {pv:.2f}", inline=True)
            embed.add_field(name="Pagamento", value=f"R$ {pf:.2f}", inline=True)

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Valores invalidos! Use numeros (ex: 1.50)", ephemeral=True)
        except Exception as e:
            logger.error(f"Erro modal preco: {e}")
            await interaction.response.send_message("Erro ao salvar.", ephemeral=True)


class ProductSelect(discord.ui.Select):
    def __init__(self, produtos, empresa_id):
        self.produtos_map = {str(p['id']): p for p in produtos}
        self.empresa_id = empresa_id

        options = []
        for p in produtos[:25]:
            label = f"{p['nome']} (${p['preco_minimo']} - ${p['preco_maximo']})"
            options.append(discord.SelectOption(label=label[:100], value=str(p['id'])))

        super().__init__(placeholder="Selecione um produto para editar...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        prod_id = self.values[0]
        produto = self.produtos_map[prod_id]

        # Open Modal
        await interaction.response.send_modal(ConfigPrecoModal(produto, self.empresa_id))


class CategorySelect(discord.ui.Select):
    def __init__(self, categorias, full_products, empresa_id):
        self.full_products = full_products
        self.empresa_id = empresa_id
        self.categorias = categorias

        options = []
        for cat in list(categorias.keys())[:25]:
            count = len(categorias[cat])
            options.append(discord.SelectOption(label=f"{cat} ({count})", value=cat))

        super().__init__(placeholder="Filtrar por Categoria...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        cat = self.values[0]
        prods = self.categorias[cat]

        # Update View with Product Select
        view = self.view  # Get parent view
        view.clear_items()

        # Re-add Category Select (so user can switch back)
        view.add_item(self)

        # Add Product Select for this category
        view.add_item(ProductSelect(prods, self.empresa_id))

        await interaction.response.edit_message(content=f"Categoria: **{cat}**. Selecione o produto:", view=view)


class PriceConfigurationView(discord.ui.View):
    def __init__(self, ctx, categorias, all_products, empresa_id):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.add_item(CategorySelect(categorias, all_products, empresa_id))

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.ctx.author.id
