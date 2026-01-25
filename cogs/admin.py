"""
Bot Multi-Empresa Downtown - Cog de Administração
Comandos administrativos para configuração de empresas e usuários.
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
    criar_empresa,
    criar_usuario_frontend,
    get_or_create_funcionario,
    get_bases_redm,
    atualizar_base_servidor
)
from utils import empresa_configurada, selecionar_empresa
from ui_utils import create_success_embed, create_error_embed, create_info_embed, handle_interaction_error, BaseMenuView
from logging_config import logger


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

    # ============================================
    # CONFIGURAR EMPRESA (UI)
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

        # 0. Check if we need to select base
        # Logic: Show Base Select first.
        bases = await get_bases_redm()
        if not bases:
             await ctx.send("❌ Erro critico: Nenhuma base REDM encontrada no sistema.")
             return

        # Create View for Base Selection
        view = self.BaseSelectView(bases, guild_id, servidor['id'], proprietario_id, self)
        embed = create_info_embed("🌍 Selecione o Servidor REDM", 
                                "Este bot suporta múltiplas economias.\n"
                                "Qual servidor/base vocês jogam?")
        
        await ctx.send(embed=embed, view=view)


    # ============================================
    # BASE SELECT UI
    # ============================================
    
    class BaseSelectView(discord.ui.View):
        def __init__(self, bases: list, guild_id: str, servidor_id: int, proprietario_id: str, cog):
            super().__init__(timeout=180)
            self.bases = bases
            self.guild_id = guild_id
            self.servidor_id = servidor_id
            self.proprietario_id = proprietario_id
            self.cog = cog

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

                # Reuse NovaEmpresaView logic
                view = self.cog.NovaEmpresaView(tipos, self.guild_id, self.servidor_id, self.proprietario_id)
                embed = create_info_embed(f"🏢 Configuração Inicial ({base['nome']})", "Selecione o tipo da sua primeira empresa.")
                
                await interaction.edit_original_response(embed=embed, view=view)
            
            return callback

    # ============================================
    # LISTAR EMPRESAS
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
    # NOVA EMPRESA (UI MODAL)
    # ============================================

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

    class NovaEmpresaView(discord.ui.View):
        def __init__(self, tipos: list, guild_id: str, servidor_id: int, proprietario_id: str):
            super().__init__(timeout=180)
            self.add_item(AdminCog.NovaEmpresaSelect(tipos, guild_id, servidor_id, proprietario_id))

    class NovaEmpresaSelect(discord.ui.Select):
        def __init__(self, tipos: list, guild_id: str, servidor_id: int, proprietario_id: str):
            options = []
            for t in tipos[:25]: # Limit 25
                label = f"{t['nome']}"
                if t.get('icone'): label = f"{t['icone']} {label}"
                options.append(discord.SelectOption(label=label, value=str(t['id']), description=f"Tipo: {t['nome']}"))

            super().__init__(placeholder="Selecione o tipo de empresa...", min_values=1, max_values=1, options=options)
            self.tipos = {str(t['id']): t for t in tipos}
            self.guild_id = guild_id
            self.servidor_id = servidor_id
            self.proprietario_id = proprietario_id

        async def callback(self, interaction: discord.Interaction):
            tipo_id = int(self.values[0])
            tipo = self.tipos[str(tipo_id)]
            
            modal = AdminCog.NovaEmpresaModal(
                tipo_id=tipo_id,
                tipo_nome=tipo['nome'],
                guild_id=self.guild_id,
                servidor_id=self.servidor_id,
                proprietario_id=self.proprietario_id
            )
            await interaction.response.send_modal(modal)

    # View replaced by PaymentModeView section


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

        view = self.NovaEmpresaView(tipos, guild_id, servidor['id'], proprietario_id)
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
            response = supabase.table('usuarios_frontend').select('*').eq(
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
            
            # Need to get user DB ID first or use valid function
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
                if await atualizar_role_usuario_frontend(user_db['id'], 'admin'):
                    await ctx.send(f"✅ {membro.mention} promovido para **Admin**!")
                else:
                    await ctx.send("❌ Erro ao atualizar permissão.")
                    
        except Exception as e:
            logger.error(f"Erro ao promover: {e}")
            await ctx.send("❌ Erro ao promover usuário.")

    # ============================================
    # BEM-VINDO (UI USER SELECT)
    # ============================================

    class BemVindoUserSelect(discord.ui.Select):
        def __init__(self, cog, ctx):
            super().__init__(placeholder="Selecione o funcionário...", min_values=1, max_values=1, select_type=discord.ComponentType.user_select)
            self.cog = cog
            self.ctx = ctx

        async def callback(self, interaction: discord.Interaction):
            # Get member object
            member = self.values[0]
            if isinstance(member, discord.User): # Fallback if cache miss
                guild = interaction.guild
                member = guild.get_member(member.id) or member
            
            await interaction.response.defer()
            # Call original logic
            await self.cog.processar_bemvindo(self.ctx, member, interaction)

    # View replaced by PaymentModeView section


    @commands.hybrid_command(name='bemvindo', description="Cria canal e cadastro para funcionário.")
    @commands.has_permissions(manage_channels=True)
    @empresa_configurada()
    async def bemvindo(self, ctx, membro: discord.Member = None):
        """Cria canal privado e cadastro (UI ou Argumento)."""
        if not membro:
            view = self.BemVindoView(self, ctx)
            await ctx.send(embed=create_info_embed("👋 Cadastro de Funcionário", "Selecione o usuário abaixo."), view=view, ephemeral=True)
            return
        
        await self.processar_bemvindo(ctx, membro)

    async def processar_bemvindo(self, ctx, membro: discord.Member, interaction: discord.Interaction = None):
        """Lógica central do bem-vindo (separada para reuso)."""
        empresa = await selecionar_empresa(ctx)
        if not empresa: return
        
        guild = ctx.guild
        guild_id = str(guild.id)

        # 0. Check Admin Status (Always needed)
        eh_admin = False
        try:
             resp = supabase.table('usuarios_frontend').select('role').eq('discord_id', str(membro.id)).eq('guild_id', guild_id).execute()
             if resp.data and resp.data[0]['role'] in ['admin', 'superadmin']:
                 eh_admin = True
        except: pass

        # 1. Determinar Categoria Alvo (da empresa ou genérica)
        categoria_id = empresa.get('categoria_id')
        categoria = None
        nome_categoria = "N/A" # Initialize default

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
                    if interaction: await interaction.followup.send(msg)
                    else: await ctx.send(msg)

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
                 if interaction: await interaction.followup.send(msg)
                 else: await ctx.send(msg)
             else:
                 created_channel = await guild.create_text_channel(name=nome_canal, overwrites=overwrites, category=categoria)
        except Exception as e:
             msg = f"❌ Erro ao criar canal: {e}"
             if interaction: await interaction.followup.send(msg)
             else: await ctx.send(msg)
             return


        try:
            from database import atualizar_canal_funcionario # Import new function

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
            if interaction: await interaction.followup.send(success_msg)
            else: await ctx.send(success_msg)

        except Exception as e:
            err_msg = f"❌ Erro ao configurar usuário: {e}"
            logger.error(f"Erro em bemvindo: {e}", exc_info=True)
            if interaction: await interaction.followup.send(err_msg)
            else: await ctx.send(err_msg)

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
