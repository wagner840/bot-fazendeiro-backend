"""
UI components for company (empresa) creation and management.
"""

import discord
from database import (
    get_tipos_empresa,
    criar_empresa,
    atualizar_base_servidor
)
from ui_utils import create_success_embed, create_error_embed, create_info_embed, handle_interaction_error


class NovaEmpresaModal(discord.ui.Modal, title="Criar Nova Empresa"):
    def __init__(self, tipo_id: int, tipo_nome: str, guild_id: str, servidor_id: int, proprietario_id: str):
        super().__init__()
        self.tipo_id = tipo_id
        self.tipo_nome = tipo_nome
        self.guild_id = guild_id
        self.servidor_id = servidor_id
        self.proprietario_id = proprietario_id

        self.nome = discord.ui.TextInput(
            label="Nome da Empresa",
            placeholder=f"Ex: {tipo_nome} do {proprietario_id}",
            min_length=3,
            max_length=50,
            required=True
        )
        self.add_item(self.nome)

    async def on_submit(self, interaction: discord.Interaction):
        nome_empresa = self.nome.value.strip()
        guild = interaction.guild

        try:
            # 1. Criar Categoria da Empresa
            categoria_nome = f"🏭 {nome_empresa.upper()}"
            categoria = await guild.create_category(categoria_nome)

            # 2. Criar Canal Principal
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            canal_principal = await guild.create_text_channel(
                name="💼-chat-principal",
                category=categoria,
                overwrites=overwrites,
                topic=f"Canal principal da empresa {nome_empresa}"
            )

            # 3. Salvar no Banco
            empresa = await criar_empresa(
                self.guild_id,
                nome_empresa,
                self.tipo_id,
                self.proprietario_id,
                servidor_id=self.servidor_id,
                categoria_id=str(categoria.id),
                canal_principal_id=str(canal_principal.id)
            )

            if not empresa:
                await interaction.response.send_message(embed=create_error_embed("Erro", "Erro ao criar empresa no banco."), ephemeral=True)
                return

            embed = create_success_embed("Empresa Criada com Sucesso!")
            embed.description = f"A empresa **{nome_empresa}** foi configurada.\n\n" \
                                f"📂 Categoria: {categoria.mention}\n" \
                                f"💬 Canal: {canal_principal.mention}\n\n" \
                                f"Use o canal principal para gerenciar sua empresa!"

            await interaction.response.send_message(embed=embed, ephemeral=False)

            # Mensagem de boas vindas no novo canal
            welcome = discord.Embed(
                title=f"🏢 Bem-vindo à {nome_empresa}",
                description="Este é o canal principal da sua nova empresa.\n\n"
                            "**Próximos Passos:**\n"
                            "1. Use `!bemvindo @usuario` para adicionar funcionários.\n"
                            "2. Use `!configurarprecos` para definir os valores.\n"
                            "3. Dica: Use `!configmin`, `!configmedio` ou `!configmax` para configurar preços automaticamente!\n"
                            "4. Comece a produzir com `/produzir`!",
                color=discord.Color.blue()
            )
            await canal_principal.send(embed=welcome)

        except Exception as e:
            await handle_interaction_error(interaction, e)


class NovaEmpresaSelect(discord.ui.Select):
    def __init__(self, tipos: list, guild_id: str, servidor_id: int, proprietario_id: str):
        options = []
        for t in tipos[:25]:  # Limit 25
            label = f"{t['nome']}"
            if t.get('icone'):
                label = f"{t['icone']} {label}"
            options.append(discord.SelectOption(label=label, value=str(t['id']), description=f"Tipo: {t['nome']}"))

        super().__init__(placeholder="Selecione o tipo de empresa...", min_values=1, max_values=1, options=options)
        self.tipos = {str(t['id']): t for t in tipos}
        self.guild_id = guild_id
        self.servidor_id = servidor_id
        self.proprietario_id = proprietario_id

    async def callback(self, interaction: discord.Interaction):
        tipo_id = int(self.values[0])
        tipo = self.tipos[str(tipo_id)]

        modal = NovaEmpresaModal(
            tipo_id=tipo_id,
            tipo_nome=tipo['nome'],
            guild_id=self.guild_id,
            servidor_id=self.servidor_id,
            proprietario_id=self.proprietario_id
        )
        await interaction.response.send_modal(modal)


class NovaEmpresaView(discord.ui.View):
    def __init__(self, tipos: list, guild_id: str, servidor_id: int, proprietario_id: str):
        super().__init__(timeout=180)
        self.add_item(NovaEmpresaSelect(tipos, guild_id, servidor_id, proprietario_id))


class BaseSelectView(discord.ui.View):
    def __init__(self, bases: list, guild_id: str, servidor_id: int, proprietario_id: str):
        super().__init__(timeout=180)
        self.bases = bases
        self.guild_id = guild_id
        self.servidor_id = servidor_id
        self.proprietario_id = proprietario_id

        # Dynamic Buttons for each base
        for base in bases:
            btn = discord.ui.Button(label=base['nome'], custom_id=f"base_{base['id']}", style=discord.ButtonStyle.primary)
            btn.callback = self.create_callback(base)
            self.add_item(btn)

    def create_callback(self, base):
        async def callback(interaction: discord.Interaction):
            if str(interaction.user.id) != self.proprietario_id:
                await interaction.response.send_message("❌ Apenas quem iniciou o comando pode selecionar.", ephemeral=True)
                return

            await interaction.response.defer()

            # Update Server Base
            updated = await atualizar_base_servidor(self.guild_id, base['id'])
            if not updated:
                await interaction.followup.send("❌ Erro ao atualizar base do servidor.")
                return

            # Proceed to Company Type Selection
            tipos = await get_tipos_empresa(self.guild_id)
            if not tipos:
                await interaction.followup.send(embed=create_error_embed("Erro", f"Nenhum tipo de empresa configurado para a base {base['nome']}."))
                return

            # Use NovaEmpresaView
            view = NovaEmpresaView(tipos, self.guild_id, self.servidor_id, self.proprietario_id)
            embed = create_info_embed(f"🏢 Configuração Inicial ({base['nome']})", "Selecione o tipo da sua primeira empresa.")

            await interaction.edit_original_response(embed=embed, view=view)

        return callback
