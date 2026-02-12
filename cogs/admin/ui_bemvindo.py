"""
UI components for employee welcome/registration (bemvindo).
"""

import discord
from config import supabase
from database import (
    get_or_create_funcionario,
    criar_usuario_frontend,
    atualizar_canal_funcionario
)
from utils import selecionar_empresa
from logging_config import logger


class BemVindoUserSelect(discord.ui.Select):
    def __init__(self, cog, ctx):
        super().__init__(
            placeholder="Selecione o funcionário...",
            min_values=1,
            max_values=1,
            select_type=discord.ComponentType.user_select
        )
        self.cog = cog
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        # Get member object
        member = self.values[0]
        if isinstance(member, discord.User):  # Fallback if cache miss
            guild = interaction.guild
            member = guild.get_member(member.id) or member

        await interaction.response.defer()
        # Call original logic
        await processar_bemvindo(self.ctx, member, interaction)


class BemVindoView(discord.ui.View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=120)
        self.add_item(BemVindoUserSelect(cog, ctx))


async def processar_bemvindo(ctx, membro: discord.Member, interaction: discord.Interaction = None):
    """Central logic for employee welcome/registration."""
    empresa = await selecionar_empresa(ctx)
    if not empresa:
        return

    guild = ctx.guild
    guild_id = str(guild.id)

    # 0. Check Admin Status (Always needed)
    eh_admin = False
    try:
        resp = await supabase.table('usuarios_frontend').select('role').eq('discord_id', str(membro.id)).eq('guild_id', guild_id).execute()
        if resp.data and resp.data[0]['role'] in ['admin', 'superadmin']:
            eh_admin = True
    except:
        pass

    # 1. Determinar Categoria Alvo (da empresa ou genérica)
    categoria_id = empresa.get('categoria_id')
    categoria = None
    nome_categoria = "N/A"  # Initialize default

    if categoria_id:
        categoria = discord.utils.get(guild.categories, id=int(categoria_id))
        if categoria:
            nome_categoria = categoria.name

    if not categoria:
        # Fallback para lógica antiga de nomes se o ID não bater ou não existir
        nome_categoria = "👔 ADMINISTRAÇÃO" if eh_admin else "🏭 PRODUÇÃO"
        categoria = discord.utils.get(guild.categories, name=nome_categoria)

        if not categoria:
            try:
                categoria = await guild.create_category(nome_categoria)
            except Exception as e:
                msg = f"⚠️ Não consegui criar a categoria '{nome_categoria}': {e}"
                if interaction:
                    await interaction.followup.send(msg)
                else:
                    await ctx.send(msg)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        membro: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    nome_canal = f"func-{membro.display_name.lower().replace(' ', '-')}"

    created_channel = None
    try:
        # Tenta encontrar canal existente ou criar novo dentro da categoria
        existing_channel = discord.utils.get(guild.text_channels, name=nome_canal)
        if existing_channel:
            created_channel = existing_channel
            if categoria and created_channel.category != categoria:
                await created_channel.edit(category=categoria)

            msg = f"⚠️ O canal {created_channel.mention} já existia e foi configurado."
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
        else:
            created_channel = await guild.create_text_channel(name=nome_canal, overwrites=overwrites, category=categoria)
    except Exception as e:
        msg = f"❌ Erro ao criar canal: {e}"
        if interaction:
            await interaction.followup.send(msg)
        else:
            await ctx.send(msg)
        return

    try:
        func_id = await get_or_create_funcionario(str(membro.id), membro.display_name, empresa['id'])
        if not func_id:
            raise Exception("Falha ao criar/obter registro de funcionário no banco.")

        # Update Channel ID
        await atualizar_canal_funcionario(func_id, str(created_channel.id))

        usuario_frontend = None
        if not eh_admin:
            usuario_frontend = await criar_usuario_frontend(str(membro.id), guild_id, membro.display_name, 'funcionario')
            if not usuario_frontend:
                raise Exception("Falha ao criar usuário frontend (verifique logs/permissões).")
        else:
            usuario_frontend = True

        embed = discord.Embed(
            title=f"🏢 Bem-vindo à {empresa['nome']}!",
            description=f"Olá {membro.mention}! Este é seu canal privado.",
            color=discord.Color.green()
        )

        if eh_admin:
            embed.description += "\n🛡️ **Canal Administrativo**\nUse este canal para gerenciar a empresa."
            embed.add_field(name="⚙️ Comandos Admin", value="`!configurar`, `!modopagamento`, `!pagar`...", inline=False)

        embed.add_field(
            name="📋 Comandos do Bot",
            value="`!add` - Adicionar produtos\n`!estoque` - Ver seu estoque\n`!produtos` - Ver catálogo",
            inline=False
        )

        embed.add_field(
            name="🌐 Painel Web",
            value="Você tem acesso ao **Painel Fazendeiro**!\nFaça login com sua conta Discord.",
            inline=False
        )

        await created_channel.send(embed=embed)

        success_msg = f"✅ Canal {created_channel.mention} configurado na categoria **{nome_categoria}**!"
        if interaction:
            await interaction.followup.send(success_msg)
        else:
            await ctx.send(success_msg)

    except Exception as e:
        err_msg = f"❌ Erro ao configurar usuário: {e}"
        logger.error(f"Erro em bemvindo: {e}", exc_info=True)
        if interaction:
            await interaction.followup.send(err_msg)
        else:
            await ctx.send(err_msg)
