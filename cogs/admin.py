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
    get_or_create_funcionario
)
from utils import empresa_configurada, selecionar_empresa


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

    @commands.command(name='configurar', aliases=['setup'])
    @commands.has_permissions(administrator=True)
    async def configurar_empresa(self, ctx):
        """Configura a empresa para este servidor."""
        guild_id = str(ctx.guild.id)
        proprietario_id = str(ctx.author.id)

        servidor = await get_or_create_servidor(guild_id, ctx.guild.name, proprietario_id)
        if not servidor:
            await ctx.send("❌ Erro ao registrar servidor.")
            return

        await criar_usuario_frontend(
            discord_id=proprietario_id,
            guild_id=guild_id,
            nome=ctx.author.display_name,
            role='admin'
        )

        empresa = await get_empresa_by_guild(guild_id)
        if empresa:
            await ctx.send(f"✅ Já existe uma empresa configurada: **{empresa['nome']}** ({empresa['tipos_empresa']['nome']})\n\n💡 Use `!novaempresa` para adicionar mais empresas ao servidor.")
            return

        tipos = await get_tipos_empresa()

        embed = discord.Embed(
            title="🏢 Configuração de Empresa",
            description="Escolha o tipo de empresa digitando o **número**:",
            color=discord.Color.blue()
        )

        tipos_text = ""
        for i, tipo in enumerate(tipos, 1):
            tipos_text += f"`{i}.` {tipo['icone']} **{tipo['nome']}**\n"

        embed.add_field(name="Tipos Disponíveis", value=tipos_text, inline=False)
        embed.set_footer(text="Digite o número ou 'cancelar'")

        await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)

            if msg.content.lower() == 'cancelar':
                await ctx.send("❌ Configuração cancelada.")
                return

            try:
                escolha = int(msg.content) - 1
                if escolha < 0 or escolha >= len(tipos):
                    await ctx.send("❌ Número inválido.")
                    return
            except ValueError:
                await ctx.send("❌ Digite apenas o número.")
                return

            tipo_escolhido = tipos[escolha]

            await ctx.send(f"✅ Tipo selecionado: **{tipo_escolhido['nome']}**\n\nAgora digite o **nome da sua empresa**:")

            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            nome_empresa = msg.content.strip()

            if len(nome_empresa) < 3:
                await ctx.send("❌ Nome muito curto.")
                return

            try:
                empresa = await criar_empresa(
                    guild_id,
                    nome_empresa,
                    tipo_escolhido['id'],
                    proprietario_id,
                    servidor_id=servidor['id']
                )
            except Exception as e:
                await ctx.send(f"❌ Erro ao criar empresa: {e}")
                return

            if guild_id in empresas_cache:
                del empresas_cache[guild_id]
            empresa = await get_empresa_by_guild(guild_id)

            embed = discord.Embed(
                title="✅ Empresa Criada!",
                description=f"**{nome_empresa}**",
                color=discord.Color.green()
            )
            embed.add_field(name="Tipo", value=f"{tipo_escolhido['icone']} {tipo_escolhido['nome']}")
            embed.add_field(name="Proprietário", value=ctx.author.mention)
            embed.add_field(
                name="🌐 Acesso Frontend",
                value=f"Você foi registrado como **Admin** do frontend.\nUse Discord OAuth para fazer login no painel.",
                inline=False
            )
            embed.add_field(
                name="Próximo Passo",
                value="Use `!configurarprecos` para definir os preços dos produtos.",
                inline=False
            )

            await ctx.send(embed=embed)

        except asyncio.TimeoutError:
            await ctx.send("❌ Tempo esgotado.")

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
    # NOVA EMPRESA
    # ============================================

    @commands.command(name='novaempresa')
    @commands.has_permissions(administrator=True)
    async def nova_empresa(self, ctx):
        """Adiciona uma nova empresa ao servidor (multi-empresa)."""
        guild_id = str(ctx.guild.id)
        proprietario_id = str(ctx.author.id)

        servidor = await get_servidor_by_guild(guild_id)
        if not servidor:
            await ctx.send("❌ Use `!configurar` primeiro para configurar o servidor.")
            return

        tipos = await get_tipos_empresa()

        embed = discord.Embed(
            title="🏢 Nova Empresa",
            description="Escolha o tipo de empresa digitando o **número**:",
            color=discord.Color.blue()
        )

        tipos_text = ""
        for i, tipo in enumerate(tipos, 1):
            tipos_text += f"`{i}.` {tipo['icone']} **{tipo['nome']}**\n"

        embed.add_field(name="Tipos Disponíveis", value=tipos_text, inline=False)
        embed.set_footer(text="Digite o número ou 'cancelar'")

        await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)

            if msg.content.lower() == 'cancelar':
                await ctx.send("❌ Cancelado.")
                return

            try:
                escolha = int(msg.content) - 1
                if escolha < 0 or escolha >= len(tipos):
                    await ctx.send("❌ Número inválido.")
                    return
            except ValueError:
                await ctx.send("❌ Digite apenas o número.")
                return

            tipo_escolhido = tipos[escolha]

            await ctx.send(f"✅ Tipo: **{tipo_escolhido['nome']}**\n\nDigite o **nome da empresa**:")

            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            nome_empresa = msg.content.strip()

            if len(nome_empresa) < 3:
                await ctx.send("❌ Nome muito curto.")
                return

            empresa = await criar_empresa(
                guild_id,
                nome_empresa,
                tipo_escolhido['id'],
                proprietario_id,
                servidor_id=servidor['id']
            )

            if not empresa:
                await ctx.send("❌ Erro ao criar empresa.")
                return

            embed = discord.Embed(
                title="✅ Nova Empresa Adicionada!",
                description=f"**{nome_empresa}**",
                color=discord.Color.green()
            )
            embed.add_field(name="Tipo", value=f"{tipo_escolhido['icone']} {tipo_escolhido['nome']}")
            embed.add_field(name="ID", value=f"`{empresa['id']}`")

            await ctx.send(embed=embed)

        except asyncio.TimeoutError:
            await ctx.send("❌ Tempo esgotado.")

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
            print(f"Erro ao listar usuários: {e}")
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

            response = supabase.table('usuarios_frontend').update({
                'ativo': False
            }).eq('discord_id', discord_id).eq('guild_id', guild_id).execute()

            if response.data:
                await ctx.send(f"✅ Acesso de {membro.mention} ao frontend removido.")
            else:
                await ctx.send(f"⚠️ {membro.display_name} não tinha acesso ao frontend.")
        except Exception as e:
            print(f"Erro ao remover acesso: {e}")
            await ctx.send("❌ Erro ao remover acesso.")

    @commands.command(name='promover')
    @commands.has_permissions(administrator=True)
    async def promover_admin(self, ctx, membro: discord.Member):
        """Promove usuário para admin do frontend."""
        guild_id = str(ctx.guild.id)
        discord_id = str(membro.id)

        try:
            existing = supabase.table('usuarios_frontend').select('*').eq(
                'discord_id', discord_id
            ).eq('guild_id', guild_id).execute()

            if not existing.data:
                await criar_usuario_frontend(discord_id, guild_id, membro.display_name, 'admin')
                await ctx.send(f"✅ {membro.mention} agora é **Admin** do frontend!")
            else:
                supabase.table('usuarios_frontend').update({
                    'role': 'admin',
                    'ativo': True
                }).eq('id', existing.data[0]['id']).execute()
                await ctx.send(f"✅ {membro.mention} promovido para **Admin**!")
        except Exception as e:
            print(f"Erro ao promover: {e}")
            await ctx.send("❌ Erro ao promover usuário.")

    @commands.command(name='bemvindo')
    @commands.has_permissions(manage_channels=True)
    @empresa_configurada()
    async def bemvindo(self, ctx, membro: discord.Member):
        """Cria canal privado para funcionário e dá acesso ao frontend."""
        empresa = await selecionar_empresa(ctx)
        if not empresa: return
        
        guild = ctx.guild
        guild_id = str(guild.id)

        # Verifica Admin
        eh_admin = False
        try:
             resp = supabase.table('usuarios_frontend').select('role').eq('discord_id', str(membro.id)).eq('guild_id', guild_id).execute()
             if resp.data and resp.data[0]['role'] in ['admin', 'superadmin']:
                 eh_admin = True
        except: pass

        prefixo = "admin" if eh_admin else "func"
        nome_canal = f"{prefixo}-{membro.display_name.lower().replace(' ', '-')}"

        # Lógica de Categorias
        nome_categoria = "👔 ADMINISTRAÇÃO" if eh_admin else "🏭 PRODUÇÃO"
        categoria = discord.utils.get(guild.categories, name=nome_categoria)
        
        if not categoria:
            try:
                categoria = await guild.create_category(nome_categoria)
            except Exception as e:
                await ctx.send(f"⚠️ Não consegui criar a categoria '{nome_categoria}': {e}")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            membro: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        try:
             # Tenta encontrar canal existente ou criar novo dentro da categoria
             existing_channel = discord.utils.get(guild.text_channels, name=nome_canal)
             if existing_channel:
                 canal = existing_channel
                 if categoria and canal.category != categoria:
                     await canal.edit(category=categoria)
                 await ctx.send(f"⚠️ O canal {canal.mention} já existia e foi configurado.")
             else:
                 canal = await guild.create_text_channel(name=nome_canal, overwrites=overwrites, category=categoria)
        except Exception as e:
             await ctx.send(f"❌ Erro ao criar canal: {e}")
             return

        func_id = await get_or_create_funcionario(str(membro.id), membro.display_name, empresa['id'])

        usuario_frontend = None
        if not eh_admin: 
             usuario_frontend = await criar_usuario_frontend(str(membro.id), guild_id, membro.display_name, 'funcionario')
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

        await canal.send(embed=embed)
        await ctx.send(f"✅ Canal {canal.mention} configurado na categoria **{nome_categoria}**!")

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
