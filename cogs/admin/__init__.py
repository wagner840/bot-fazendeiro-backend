"""
Admin cog module - Administrative commands for company and user management.
"""

import asyncio
import discord
from discord.ext import commands
from config import supabase, empresas_cache, servidores_cache
from database import (
    get_or_create_servidor,
    get_servidor_by_guild,
    get_empresa_by_guild,
    get_empresas_by_guild,
    get_tipos_empresa,
    criar_usuario_frontend,
    get_bases_redm
)
from utils import empresa_configurada, selecionar_empresa
from ui_utils import create_success_embed, create_error_embed, create_info_embed
from logging_config import logger

from .ui_empresa import NovaEmpresaView, BaseSelectView
from .ui_bemvindo import BemVindoView, processar_bemvindo


class AdminCog(commands.Cog, name="Administração"):
    """Comandos administrativos para configuração e gestão."""

    def __init__(self, bot):
        self.bot = bot

    # ============================================
    # LIMPAR CACHE
    # ============================================

    @commands.command(name='limparcache', aliases=['clearcache', 'recarregar'])
    @commands.has_permissions(administrator=True)
    async def limpar_cache(self, ctx):
        """Limpa o cache local do servidor forçando recarregamento do banco."""
        guild_id = str(ctx.guild.id)

        servidores_cache.pop(guild_id, None)
        empresas_cache.pop(guild_id, None)

        servidor = await get_servidor_by_guild(guild_id)
        empresas = await get_empresas_by_guild(guild_id)

        embed = discord.Embed(
            title="🧹 Cache Limpo e Recarregado!",
            color=discord.Color.green()
        )
        embed.add_field(name="Guild ID", value=f"`{guild_id}`", inline=False)
        embed.add_field(name="Servidor", value=f"{'✅ ' + servidor['nome'] if servidor else '❌ Não encontrado'}", inline=True)
        embed.add_field(name="Empresas", value=f"{'✅ ' + str(len(empresas)) + ' encontrada(s)' if empresas else '❌ Nenhuma'}", inline=True)

        if empresas:
            nomes = ", ".join([e['nome'] for e in empresas])
            embed.add_field(name="Lista", value=nomes, inline=False)

        await ctx.send(embed=embed)

    # ============================================
    # CONFIGURAR EMPRESA
    # ============================================

    @commands.hybrid_command(name='configurar', aliases=['setup'], description="Configura a primeira empresa do servidor.")
    @commands.has_permissions(administrator=True)
    async def configurar_empresa(self, ctx):
        """Configura a empresa para este servidor (UI)."""
        guild_id = str(ctx.guild.id)
        proprietario_id = str(ctx.author.id)

        servidor = await get_or_create_servidor(guild_id, ctx.guild.name, proprietario_id)
        if not servidor:
            await ctx.send(embed=create_error_embed("Erro", "Erro ao registrar servidor."), ephemeral=True)
            return

        # Create Frontend User
        await criar_usuario_frontend(
            discord_id=proprietario_id,
            guild_id=guild_id,
            nome=ctx.author.display_name,
            role='admin'
        )

        empresa = await get_empresa_by_guild(guild_id)
        if empresa:
            await ctx.send(embed=create_info_embed("Já Configurado", f"Empresa já existe: **{empresa['nome']}**\nUse `/novaempresa` para adicionar mais."), ephemeral=True)
            return

        # Check if we need to select base
        if servidor.get('base_redm_id'):
            tipos = await get_tipos_empresa(guild_id)
            if not tipos:
                await ctx.send(embed=create_error_embed("Erro", "Nenhum tipo de empresa configurado para esta base."))
                return

            view = NovaEmpresaView(tipos, guild_id, servidor['id'], proprietario_id)
            embed = create_info_embed("🏢 Configuração de Empresa", "Selecione o tipo da sua empresa.")
            await ctx.send(embed=embed, view=view)
            return

        bases = await get_bases_redm()
        if not bases:
            await ctx.send("❌ Erro critico: Nenhuma base REDM encontrada no sistema.")
            return

        # Create View for Base Selection
        view = BaseSelectView(bases, guild_id, servidor['id'], proprietario_id)
        embed = create_info_embed("🌍 Selecione o Servidor REDM",
                                  "Este bot suporta múltiplas economias.\n"
                                  "Qual servidor/base vocês jogam?")

        await ctx.send(embed=embed, view=view)

    # ============================================
    # MODO PAGAMENTO
    # ============================================

    @commands.command(name='modopagamento', aliases=['setpagamento', 'metodopagamento'])
    @commands.has_permissions(administrator=True)
    @empresa_configurada()
    async def definir_modo_pagamento(self, ctx):
        """Define como os funcionários recebem pagamento (produção, entrega ou estoque)."""
        empresa = await selecionar_empresa(ctx)
        if not empresa:
            return

        embed = discord.Embed(
            title="💰 Configurar Modo de Pagamento",
            description=f"Modo atual: **{empresa.get('modo_pagamento', 'producao').upper()}**\n\n"
                        "Escolha o novo modo digitando o número:",
            color=discord.Color.gold()
        )

        embed.add_field(
            name="1️⃣ Produção (Acumulativo)",
            value="O valor é gerado na fabricação (`!add`) e fica **acumulado** no estoque.\n"
                  "Chefe paga tudo via `!pagarestoque`.",
            inline=False
        )
        embed.add_field(
            name="2️⃣ Entrega (Comissão)",
            value="Funcionário ganha comissão ao **entregar** (`!entregar`).\n"
                  "Valor acumula como 'Comissão Pendente'.\n"
                  "Chefe paga tudo via `!pagarestoque`.",
            inline=False
        )

        embed.set_footer(text="Digite 1 ou 2")

        await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', timeout=30.0, check=check)
            escolha = msg.content.strip()

            novomodo = None
            if escolha == '1':
                novomodo = 'producao'
            elif escolha == '2':
                novomodo = 'entrega'
            else:
                await ctx.send("❌ Opção inválida.")
                return

            from database import atualizar_modo_pagamento
            sucesso = await atualizar_modo_pagamento(empresa['id'], novomodo)

            if sucesso:
                # Limpa cache para atualizar
                if str(ctx.guild.id) in empresas_cache:
                    del empresas_cache[str(ctx.guild.id)]

                await ctx.send(f"✅ Modo de pagamento alterado para **{novomodo.upper()}**!")
            else:
                await ctx.send("❌ Erro ao atualizar modo.")

        except asyncio.TimeoutError:
            await ctx.send("❌ Tempo esgotado.")

    # ============================================
    # LISTAR EMPRESAS
    # ============================================

    @commands.command(name='empresas', aliases=['listaempresas'])
    async def listar_empresas(self, ctx):
        """Lista as empresas configuradas neste servidor."""
        guild_id = str(ctx.guild.id)

        empresas = await get_empresas_by_guild(guild_id)

        if not empresas:
            await ctx.send("❌ Nenhuma empresa configurada neste servidor.\nUse `!configurar` ou `!novaempresa` para começar.")
            return

        embed = discord.Embed(
            title=f"🏢 Empresas de {ctx.guild.name}",
            color=discord.Color.blue()
        )

        for emp in empresas:
            tipo = emp.get('tipos_empresa') or {}
            tipo_nome = tipo.get('nome', 'Desconhecido')
            tipo_icone = tipo.get('icone', '🏢')
            status = "✅ Ativa" if emp.get('ativo') else "❌ Inativa"
            modo = emp.get('modo_pagamento', 'producao').upper()

            embed.add_field(
                name=f"{tipo_icone} {emp['nome']}",
                value=f"**Tipo:** {tipo_nome}\n**ID:** `{emp['id']}`\n**Status:** {status}\n**Pagamento:** {modo}",
                inline=False
            )

        await ctx.send(embed=embed)

    # ============================================
    # NOVA EMPRESA
    # ============================================

    @commands.hybrid_command(name='novaempresa', description="Cria uma nova empresa no servidor.")
    @commands.has_permissions(administrator=True)
    async def nova_empresa(self, ctx):
        """Adiciona uma nova empresa ao servidor (UI Interativa)."""
        guild_id = str(ctx.guild.id)
        proprietario_id = str(ctx.author.id)

        servidor = await get_servidor_by_guild(guild_id)
        if not servidor:
            await ctx.send(embed=create_error_embed("Erro", "Use `!configurar` primeiro."), ephemeral=True)
            return

        tipos = await get_tipos_empresa(guild_id)
        if not tipos:
            await ctx.send(embed=create_error_embed("Erro", "Nenhum tipo de empresa configurado no sistema."), ephemeral=True)
            return

        view = NovaEmpresaView(tipos, guild_id, servidor['id'], proprietario_id)
        embed = create_info_embed("🏢 Nova Empresa", "Selecione o tipo de empresa abaixo para continuar.")

        await ctx.send(embed=embed, view=view)

    # ============================================
    # GESTÃO DE USUÁRIOS
    # ============================================

    @commands.command(name='usuarios', aliases=['useraccess', 'acessos'])
    @commands.has_permissions(administrator=True)
    async def listar_usuarios(self, ctx):
        """Lista usuários com acesso ao frontend."""
        guild_id = str(ctx.guild.id)

        try:
            response = await supabase.table('usuarios_frontend').select('*').eq(
                'guild_id', guild_id
            ).eq('ativo', True).execute()

            embed = discord.Embed(
                title="👥 Usuários com Acesso ao Frontend",
                color=discord.Color.blue()
            )

            if not response.data:
                embed.description = "Nenhum usuário cadastrado."
            else:
                admins = [u for u in response.data if u['role'] == 'admin']
                funcs = [u for u in response.data if u['role'] == 'funcionario']

                if admins:
                    admin_text = "\n".join(f"• {u['nome']} (`{u['discord_id']}`)" for u in admins)
                    embed.add_field(name="👑 Administradores", value=admin_text, inline=False)

                if funcs:
                    func_text = "\n".join(f"• {u['nome']}" for u in funcs[:15])
                    if len(funcs) > 15:
                        func_text += f"\n... e mais {len(funcs) - 15}"
                    embed.add_field(name="👷 Funcionários", value=func_text, inline=False)

                embed.set_footer(text=f"Total: {len(response.data)} usuários")

            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Erro ao listar usuários: {e}")
            await ctx.send("❌ Erro ao listar usuários.")

    @commands.command(name='removeracesso')
    @commands.has_permissions(administrator=True)
    async def remover_acesso(self, ctx, membro: discord.Member):
        """Remove acesso ao frontend de um usuário."""
        guild_id = str(ctx.guild.id)
        discord_id = str(membro.id)

        try:
            if discord_id == str(ctx.author.id):
                await ctx.send("❌ Você não pode remover seu próprio acesso.")
                return

            from database import get_usuario_frontend, desativar_usuario_frontend

            user_db = await get_usuario_frontend(discord_id, guild_id)
            if not user_db:
                await ctx.send(f"⚠️ {membro.display_name} não tinha acesso ao frontend.")
                return

            if await desativar_usuario_frontend(user_db['id']):
                await ctx.send(f"✅ Acesso de {membro.mention} ao frontend removido.")
            else:
                await ctx.send("❌ Erro ao desativar usuário no banco.")

        except Exception as e:
            logger.error(f"Erro ao remover acesso: {e}")
            await ctx.send("❌ Erro ao remover acesso.")

    @commands.command(name='promover')
    @commands.has_permissions(administrator=True)
    async def promover_admin(self, ctx, membro: discord.Member):
        """Promove usuário para admin do frontend."""
        guild_id = str(ctx.guild.id)
        discord_id = str(membro.id)

        try:
            from database import get_usuario_frontend, criar_usuario_frontend, atualizar_role_usuario_frontend

            user_db = await get_usuario_frontend(discord_id, guild_id)

            if not user_db:
                await criar_usuario_frontend(discord_id, guild_id, membro.display_name, 'admin')
                await ctx.send(f"✅ {membro.mention} agora é **Admin** do frontend!")
            else:
                # Verifica se já é admin antes de promover
                if user_db.get('role') == 'admin':
                    await ctx.send(f"⚠️ {membro.mention} já é **Admin** do frontend!")
                    return

                if await atualizar_role_usuario_frontend(user_db['id'], 'admin'):
                    await ctx.send(f"✅ {membro.mention} promovido para **Admin**!")
                else:
                    await ctx.send("❌ Erro ao atualizar permissão.")

        except Exception as e:
            logger.error(f"Erro ao promover: {e}")
            await ctx.send("❌ Erro ao promover usuário.")

    # ============================================
    # BEM-VINDO
    # ============================================

    @commands.hybrid_command(name='bemvindo', description="Cria canal e cadastro para funcionário.")
    @commands.has_permissions(manage_channels=True)
    @empresa_configurada()
    async def bemvindo(self, ctx, membro: discord.Member = None):
        """Cria canal privado e cadastro (UI ou Argumento)."""
        if not membro:
            view = BemVindoView(self, ctx)
            await ctx.send(embed=create_info_embed("👋 Cadastro de Funcionário", "Selecione o usuário abaixo."), view=view, ephemeral=True)
            return

        await processar_bemvindo(ctx, membro)

    # ============================================
    # LIMPAR MENSAGENS
    # ============================================

    @commands.command(name='limpar')
    @commands.has_permissions(manage_messages=True)
    async def limpar(self, ctx, quantidade: int = 10):
        """Limpa mensagens do canal."""
        if quantidade < 1 or quantidade > 100:
            await ctx.send("❌ Quantidade: 1-100")
            return

        deleted = await ctx.channel.purge(limit=quantidade + 1)
        msg = await ctx.send(f"🧹 {len(deleted) - 1} mensagens apagadas!")
        await asyncio.sleep(3)
        await msg.delete()


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
