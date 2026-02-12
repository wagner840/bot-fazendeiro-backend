"""
UI components for production module.
"""

from decimal import Decimal
import discord
from database import adicionar_ao_estoque
from ui_utils import create_success_embed, create_error_embed, handle_interaction_error


class ProducaoModal(discord.ui.Modal, title="Registrar Produção"):
    def __init__(self, produto_codigo: str, produto_nome: str, produto_preco: float, empresa_id: int, func_id: int, eh_admin: bool):
        super().__init__()
        self.produto_codigo = produto_codigo
        self.produto_nome = produto_nome
        self.produto_preco = produto_preco
        self.empresa_id = empresa_id
        self.func_id = func_id
        self.eh_admin = eh_admin

        self.quantidade = discord.ui.TextInput(
            label=f"Quantidade de {produto_nome}",
            placeholder="Ex: 100",
            min_length=1,
            max_length=5,
            required=True
        )
        self.add_item(self.quantidade)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            qty = int(self.quantidade.value)
            if qty <= 0:
                raise ValueError("Quantidade deve ser maior que zero.")
        except ValueError:
            await interaction.response.send_message(
                embed=create_error_embed("Erro", "Quantidade inválida. Digite apenas números inteiros positivos."),
                ephemeral=True
            )
            return

        resultado = await adicionar_ao_estoque(self.func_id, self.empresa_id, self.produto_codigo, qty)

        if resultado:
            if self.eh_admin:
                txt_comissao = "Isento (Admin)"
            else:
                comissao = Decimal(str(self.produto_preco)) * qty
                txt_comissao = f"💰 Acumulado: R$ {comissao:.2f}"

            embed = create_success_embed("Produção Registrada!")
            embed.add_field(name=f"🏭 {self.produto_nome}", value=f"+{qty} (Total: {resultado['quantidade']})\n{txt_comissao}", inline=False)

            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=create_error_embed("Erro", "Falha ao adicionar ao estoque."), ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await handle_interaction_error(interaction, error)


class ProducaoSelect(discord.ui.Select):
    def __init__(self, produtos: dict, empresa_id: int, func_id: int, eh_admin: bool):
        options = []
        for codigo, p in list(produtos.items())[:25]:
            nome = p['produtos_referencia']['nome']
            preco = p['preco_pagamento_funcionario']
            label = f"{nome[:20]} (R$ {preco})"
            options.append(discord.SelectOption(label=label, value=codigo, description=f"Cód: {codigo}"))

        super().__init__(placeholder="Selecione um produto para produzir...", min_values=1, max_values=1, options=options)
        self.produtos = produtos
        self.empresa_id = empresa_id
        self.func_id = func_id
        self.eh_admin = eh_admin

    async def callback(self, interaction: discord.Interaction):
        codigo = self.values[0]
        prod = self.produtos[codigo]

        modal = ProducaoModal(
            produto_codigo=codigo,
            produto_nome=prod['produtos_referencia']['nome'],
            produto_preco=prod['preco_pagamento_funcionario'],
            empresa_id=self.empresa_id,
            func_id=self.func_id,
            eh_admin=self.eh_admin
        )
        await interaction.response.send_modal(modal)


class ProducaoView(discord.ui.View):
    def __init__(self, produtos: dict, empresa_id: int, func_id: int, eh_admin: bool):
        super().__init__(timeout=180)
        self.add_item(ProducaoSelect(produtos, empresa_id, func_id, eh_admin))
