"""
UI components for inventory/delete operations.
"""

import discord
from database import remover_do_estoque, get_estoque_funcionario
from ui_utils import create_success_embed


class DeleteConfirmModal(discord.ui.Modal, title="Confirmar Exclusão"):
    def __init__(self, codigo, func_id, empresa_id):
        super().__init__()
        self.codigo = codigo
        self.func_id = func_id
        self.empresa_id = empresa_id

        self.qtd = discord.ui.TextInput(label="Quantidade a descartar", placeholder="Digite o número ou 'tudo'", required=True)
        self.add_item(self.qtd)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            qtd_str = self.qtd.value.lower().strip()

            if qtd_str == 'tudo':
                estoque = await get_estoque_funcionario(self.func_id, self.empresa_id)
                item = next((e for e in estoque if e['produto_codigo'] == self.codigo), None)
                if not item:
                    await interaction.response.send_message("❌ Item não encontrado no estoque.", ephemeral=True)
                    return
                quantidade = item['quantidade']
            else:
                quantidade = int(qtd_str)
                if quantidade <= 0:
                    raise ValueError

            res = await remover_do_estoque(self.func_id, self.empresa_id, self.codigo, quantidade)
            if res and 'removido' in res:
                embed = create_success_embed("Item Removido", f"-{res['removido']} {res['nome']}\nRestante: {res['quantidade']}")
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message("❌ Erro ao remover ou estoque insuficiente.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Quantidade inválida.", ephemeral=True)


class DeleteSelect(discord.ui.Select):
    def __init__(self, estoque, func_id, empresa_id):
        self.func_id = func_id
        self.empresa_id = empresa_id
        options = []
        for item in estoque[:25]:
            label = f"{item['nome']} ({item['quantidade']}x)"
            options.append(discord.SelectOption(label=label, value=item['produto_codigo'], description="Clique para excluir"))

        super().__init__(placeholder="Selecione o item para JOGAR FORA...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        codigo = self.values[0]
        await interaction.response.send_modal(DeleteConfirmModal(codigo, self.func_id, self.empresa_id))


class InventoryView(discord.ui.View):
    def __init__(self, ctx, estoque, func_id, empresa_id):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.estoque = estoque
        self.func_id = func_id
        self.empresa_id = empresa_id

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user == self.ctx.author

    @discord.ui.button(label="🗑️ Jogar Fora (Deletar)", style=discord.ButtonStyle.danger, row=1)
    async def delete_mode(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.estoque:
            await interaction.response.send_message("❌ Estoque vazio.", ephemeral=True)
            return

        view = discord.ui.View(timeout=60)
        view.add_item(DeleteSelect(self.estoque, self.func_id, self.empresa_id))
        await interaction.response.send_message("Selecione o item para excluir:", view=view, ephemeral=True)
