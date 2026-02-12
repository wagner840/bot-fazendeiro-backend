"""
UI components for commission configuration.
"""

import discord
from config import supabase
from logging_config import logger


class ComissaoCustomModal(discord.ui.Modal, title="Comissao Personalizada"):
    def __init__(self, empresa_id, produtos, apply_commission_func):
        super().__init__()
        self.empresa_id = empresa_id
        self.produtos = produtos
        self.apply_commission_func = apply_commission_func

        self.porcentagem = discord.ui.TextInput(
            label="Porcentagem (%)",
            placeholder="Exemplo: 35",
            min_length=1,
            max_length=3
        )
        self.add_item(self.porcentagem)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            val = float(self.porcentagem.value.replace(',', '.').replace('%', ''))
            if val <= 0 or val > 100:
                raise ValueError

            await self.apply_commission_func(interaction, self.empresa_id, self.produtos, val)
        except ValueError:
            await interaction.response.send_message("Valor invalido.", ephemeral=True)


class CommissionView(discord.ui.View):
    def __init__(self, ctx, empresa_id, produtos, apply_commission_func):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.empresa_id = empresa_id
        self.produtos = produtos
        self.apply_commission_func = apply_commission_func

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.ctx.author.id

    @discord.ui.select(placeholder="Selecione uma % pre-definida...", options=[
        discord.SelectOption(label="20% - Margem Alta", value="20"),
        discord.SelectOption(label="25% - Padrao", value="25"),
        discord.SelectOption(label="30% - Equilibrado", value="30"),
        discord.SelectOption(label="40% - Generoso", value="40"),
        discord.SelectOption(label="50% - Meio a Meio", value="50"),
    ])
    async def select_preset(self, interaction: discord.Interaction, select: discord.ui.Select):
        val = float(select.values[0])
        await self.apply_commission_func(interaction, self.empresa_id, self.produtos, val)

    @discord.ui.button(label="Personalizar %", style=discord.ButtonStyle.secondary, emoji="*")
    async def custom(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            ComissaoCustomModal(self.empresa_id, self.produtos, self.apply_commission_func)
        )


async def aplicar_comissao(interaction: discord.Interaction, empresa_id, produtos, porcentagem):
    """Helper to apply commission logic to database."""
    await interaction.response.defer()

    atualizados = 0
    for codigo, p in produtos.items():
        preco_venda = float(p['preco_venda'])
        novo_preco_func = round(preco_venda * (porcentagem / 100), 2)

        try:
            await supabase.table('produtos_empresa').update({
                'preco_pagamento_funcionario': novo_preco_func
            }).eq('id', p['id']).execute()
            atualizados += 1
        except Exception as e:
            logger.error(f"Erro update comissao: {e}")

    embed = discord.Embed(
        title=f"OK Comissao Ajustada: {porcentagem:.0f}%",
        description=f"{atualizados} produtos atualizados com sucesso.",
        color=discord.Color.green()
    )
    embed.set_footer(text="Confira em !verprecos")

    await interaction.followup.send(embed=embed)
