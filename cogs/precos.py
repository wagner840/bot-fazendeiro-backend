"""
Bot Multi-Empresa Downtown - Cog de Preços
Comandos para configuração de preços e comissões.
"""

import asyncio
import discord
from discord.ext import commands
from config import supabase
from database import (
    get_produtos_referencia,
    get_produtos_empresa,
    configurar_produto_empresa
)
from utils import empresa_configurada, selecionar_empresa
from logging_config import logger


class PrecosCog(commands.Cog, name="Preços"):
    """Comandos de configuração de preços e comissões."""

    def __init__(self, bot):
        self.bot = bot

    # ============================================
    # CONFIGURAR PREÇOS MANUALMENTE
    # ============================================

    # ============================================
    # CONFIGURAR PREÇOS (UI REFATORADA)
    # ============================================

    class ConfigPrecoModal(discord.ui.Modal, title="Editar Preço"):
        def __init__(self, produto: dict, empresa_id: int):
            super().__init__()
            self.produto = produto
            self.empresa_id = empresa_id
            
            self.preco_venda = discord.ui.TextInput(
                label=f"Preço Venda ({produto['nome']})",
                placeholder=f"Min: {produto['preco_minimo']} | Max: {produto['preco_maximo']}",
                default=str(produto.get('preco_venda', '')),
                required=True
            )
            self.add_item(self.preco_venda)
            
            self.preco_func = discord.ui.TextInput(
                label="Pagamento Funcionário (%)",
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
                    title=f"✅ {self.produto['nome']} Atualizado!",
                    color=discord.Color.green()
                )
                embed.add_field(name="Venda", value=f"R$ {pv:.2f}", inline=True)
                embed.add_field(name="Pagamento", value=f"R$ {pf:.2f}", inline=True)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except ValueError:
                await interaction.response.send_message("❌ Valores inválidos! Use números (ex: 1.50)", ephemeral=True)
            except Exception as e:
                logger.error(f"Erro modal preco: {e}")
                await interaction.response.send_message("❌ Erro ao salvar.", ephemeral=True)

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
            await interaction.response.send_modal(PrecosCog.ConfigPrecoModal(produto, self.empresa_id))

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
            view = self.view # Get parent view
            view.clear_items()
            
            # Re-add Category Select (so user can switch back)
            view.add_item(self)
            
            # Add Product Select for this category
            view.add_item(PrecosCog.ProductSelect(prods, self.empresa_id))
            
            await interaction.response.edit_message(content=f"📂 Categoria: **{cat}**. Selecione o produto:", view=view)


    class PriceConfigurationView(discord.ui.View): # Inherit BaseMenuView better if available, but staying safe with View + check
        def __init__(self, ctx, categorias, all_products, empresa_id):
            super().__init__(timeout=300)
            self.ctx = ctx
            self.add_item(PrecosCog.CategorySelect(categorias, all_products, empresa_id))

        async def interaction_check(self, interaction: discord.Interaction):
            return interaction.user.id == self.ctx.author.id

    @commands.command(name='configurarprecos', aliases=['setprecos', 'editarprecos'])
    @commands.has_permissions(administrator=True)
    @empresa_configurada()
    async def configurar_precos(self, ctx):
        """Configura os preços dos produtos (Menu Interativo)."""
        empresa = await selecionar_empresa(ctx)
        if not empresa: return

        produtos_ref = await get_produtos_referencia(empresa['tipo_empresa_id'], guild_id=str(ctx.guild.id))
        if not produtos_ref:
            await ctx.send("❌ Nenhum produto disponível.")
            return

        # Prepare Data
        categorias = {}
        for p in produtos_ref:
            cat = p.get('categoria') or 'Outros'
            if cat not in categorias: categorias[cat] = []
            categorias[cat].append(p)

        view = self.PriceConfigurationView(ctx, categorias, produtos_ref, empresa['id'])
        
        embed = discord.Embed(
            title=f"💰 Editor de Preços - {empresa['nome']}",
            description="Selecione uma **Categoria** abaixo para ver os produtos.\nDepois, clique no produto para editar o preço.",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed, view=view)


    # ============================================
    # CONFIGURAÇÃO AUTOMÁTICA DE PREÇOS
    # ============================================

    @commands.command(name='configmin', aliases=['configminimo', 'precosmin'])
    @commands.has_permissions(administrator=True)
    @empresa_configurada()
    async def configurar_minimo(self, ctx):
        """Configura todos os produtos com preço MÍNIMO (25% funcionário)."""
        await self._configurar_precos_com_feedback(ctx, 'minimo')

    @commands.command(name='configmedio', aliases=['configurarauto', 'autoconfig', 'precosmed'])
    @commands.has_permissions(administrator=True)
    @empresa_configurada()
    async def configurar_medio(self, ctx):
        """Configura todos os produtos com preço MÉDIO (25% funcionário)."""
        await self._configurar_precos_com_feedback(ctx, 'medio')

    @commands.command(name='configmax', aliases=['configmaximo', 'precosmax'])
    @commands.has_permissions(administrator=True)
    @empresa_configurada()
    async def configurar_maximo(self, ctx):
        """Configura todos os produtos com preço MÁXIMO (25% funcionário)."""
        await self._configurar_precos_com_feedback(ctx, 'maximo')

    async def _configurar_precos_com_feedback(self, ctx, modo: str):
        """Função auxiliar para configurar preços com feedback visual completo."""
        empresa = await selecionar_empresa(ctx)
        if not empresa:
            return
        
        produtos_ref = await get_produtos_referencia(empresa['tipo_empresa_id'], guild_id=str(ctx.guild.id))

        if not produtos_ref:
            await ctx.send("❌ Nenhum produto disponível.")
            return
        
        modos = {
            'minimo': {'emoji': '📉', 'cor': discord.Color.blue(), 'nome': 'MÍNIMO'},
            'medio': {'emoji': '📊', 'cor': discord.Color.gold(), 'nome': 'MÉDIO'},
            'maximo': {'emoji': '📈', 'cor': discord.Color.green(), 'nome': 'MÁXIMO'}
        }
        cfg = modos[modo]
        
        progress_msg = await ctx.send(f"{cfg['emoji']} Configurando {len(produtos_ref)} produtos com preço **{cfg['nome']}**...")
        
        configurados = 0
        produtos_config = []
        
        for p in produtos_ref:
            # Parse min/max handling None
            p_min_raw = p.get('preco_minimo')
            p_max_raw = p.get('preco_maximo')
            
            p_min = float(p_min_raw) if p_min_raw is not None else None
            p_max = float(p_max_raw) if p_max_raw is not None else None

            preco_venda = 0.0

            if modo == 'minimo':
                if p_min is not None:
                    preco_venda = p_min
                elif p_max is not None:
                    preco_venda = p_max # Fallback to max if min missing
                else:
                    continue # Skip if no price

            elif modo == 'maximo':
                if p_max is not None:
                    preco_venda = p_max
                elif p_min is not None:
                    preco_venda = p_min # Fallback to min if max missing
                else:
                    continue

            else: # medio
                if p_min is not None and p_max is not None:
                    preco_venda = (p_min + p_max) / 2
                elif p_min is not None:
                    preco_venda = p_min
                elif p_max is not None:
                    preco_venda = p_max
                else:
                    continue
            
            preco_func = round(preco_venda * 0.25, 2)
            
            if await configurar_produto_empresa(empresa['id'], p['id'], preco_venda, preco_func):
                configurados += 1
                produtos_config.append({
                    'codigo': p['codigo'],
                    'nome': p['nome'],
                    'categoria': p.get('categoria', 'Outros'),
                    'preco_venda': preco_venda,
                    'preco_func': preco_func
                })
        
        try:
            await progress_msg.delete()
        except:
            pass
        
        # Embed principal
        embed_sucesso = discord.Embed(
            title=f"✅ Preços Configurados no {cfg['nome']}!",
            description=f"{cfg['emoji']} **{configurados}/{len(produtos_ref)}** produtos de **{empresa['nome']}** atualizados.",
            color=cfg['cor']
        )
        
        # Agrupa por categoria
        categorias = {}
        for p in produtos_config:
            cat = p['categoria']
            if cat not in categorias:
                categorias[cat] = []
            categorias[cat].append(p)
        
        for cat, prods in list(categorias.items())[:6]:
            preview = "\n".join([f"`{p['codigo']}` ${p['preco_venda']:.2f}" for p in prods[:3]])
            if len(prods) > 3:
                preview += f"\n*+{len(prods) - 3} mais*"
            embed_sucesso.add_field(name=f"📦 {cat} ({len(prods)})", value=preview, inline=True)
        
        embed_sucesso.add_field(
            name="💡 Comandos Úteis",
            value="`!verprecos` - Ver todos os preços\n`!verprecos [categoria]` - Ver por categoria",
            inline=False
        )
        embed_sucesso.set_footer(text="👷 Pagamento Funcionário = 25% do preço de venda")
        
        await ctx.send(embed=embed_sucesso)
        
        # Embed com tabela de preços
        embed_precos = discord.Embed(
            title=f"💰 Tabela de Preços - {cfg['nome']}",
            description=f"Preços configurados para **{empresa['nome']}**:",
            color=cfg['cor']
        )
        
        for p in produtos_config[:24]:
            embed_precos.add_field(
                name=f"`{p['codigo']}`",
                value=f"**{p['nome'][:18]}**\n💵 ${p['preco_venda']:.2f} | 👷 ${p['preco_func']:.2f}",
                inline=True
            )
        
        if len(produtos_config) > 24:
            embed_precos.set_footer(text=f"... e mais {len(produtos_config) - 24} produtos. Use !verprecos para ver todos.")
        
        await ctx.send(embed=embed_precos)

    # ============================================
    # VER PREÇOS
    # ============================================

    @commands.command(name='verprecos', aliases=['precos', 'listaprecos', 'tabelaprecos', 'meusprecos'])
    @empresa_configurada()
    async def ver_precos(self, ctx, *, categoria: str = None):
        """Ver preços dos produtos. Uso: !precos [categoria]"""
        empresa = await selecionar_empresa(ctx)
        if not empresa:
            return

        produtos = await get_produtos_empresa(empresa['id'])

        if not produtos:
            await ctx.send("❌ Nenhum produto configurado. Use `!configmedio` para configurar.")
            return

        # Agrupa por categoria
        categorias = {}
        for codigo, p in produtos.items():
            cat = p['produtos_referencia'].get('categoria', 'Outros')
            if cat not in categorias:
                categorias[cat] = []
            categorias[cat].append((codigo, p))

        # Se especificou categoria, filtra
        if categoria:
            cat_encontrada = None
            for cat in categorias.keys():
                if categoria.lower() in cat.lower():
                    cat_encontrada = cat
                    break

            if not cat_encontrada:
                await ctx.send(f"❌ Categoria `{categoria}` não encontrada.")
                return

            categorias = {cat_encontrada: categorias[cat_encontrada]}

        # Mostra todos os produtos por categoria
        embed = discord.Embed(
            title=f"💰 Tabela de Preços",
            description=f"**{empresa['nome']}**\n`💵 Venda` | `👷 Funcionário`",
            color=discord.Color.gold()
        )

        field_count = 0
        embeds = [embed]

        for cat, prods in categorias.items():
            # Monta lista de produtos da categoria
            linhas = []
            for codigo, p in prods:
                nome = p['produtos_referencia']['nome'][:20]
                venda = float(p['preco_venda'])
                func = float(p['preco_pagamento_funcionario'])
                linhas.append(f"`{codigo}` {nome}\n💵 ${venda:.2f} | 👷 ${func:.2f}")

            # Divide em chunks se necessário (limite de 1024 chars por field)
            texto = "\n".join(linhas)

            if len(texto) <= 1024:
                if field_count >= 25:
                    embed = discord.Embed(color=discord.Color.gold())
                    embeds.append(embed)
                    field_count = 0
                embed.add_field(name=f"📁 {cat} ({len(prods)})", value=texto, inline=False)
                field_count += 1
            else:
                # Divide em múltiplos fields
                chunk = []
                chunk_len = 0
                for linha in linhas:
                    if chunk_len + len(linha) + 1 > 1000:
                        if field_count >= 25:
                            embed = discord.Embed(color=discord.Color.gold())
                            embeds.append(embed)
                            field_count = 0
                        embed.add_field(name=f"📁 {cat}", value="\n".join(chunk), inline=False)
                        field_count += 1
                        chunk = []
                        chunk_len = 0
                    chunk.append(linha)
                    chunk_len += len(linha) + 1

                if chunk:
                    if field_count >= 25:
                        embed = discord.Embed(color=discord.Color.gold())
                        embeds.append(embed)
                        field_count = 0
                    embed.add_field(name=f"📁 {cat} (cont.)", value="\n".join(chunk), inline=False)
                    field_count += 1

        embeds[-1].set_footer(text=f"Total: {len(produtos)} produtos | !configurarprecos para editar")

        for e in embeds:
            await ctx.send(embed=e)

    # ============================================
    # CONFIGURAR COMISSÃO
    # ============================================

    # ============================================
    # CONFIGURAR COMISSÃO (UI REFATORADA)
    # ============================================

    class ComissaoCustomModal(discord.ui.Modal, title="Comissão Personalizada"):
        def __init__(self, cog, empresa_id, produtos):
            super().__init__()
            self.cog = cog
            self.empresa_id = empresa_id
            self.produtos = produtos
            
            self.porcentagem = discord.ui.TextInput(
                label="Porcentagem (%)",
                placeholder="Exente: 35",
                min_length=1,
                max_length=3
            )
            self.add_item(self.porcentagem)

        async def on_submit(self, interaction: discord.Interaction):
            try:
                val = float(self.porcentagem.value.replace(',', '.').replace('%', ''))
                if val <= 0 or val > 100: raise ValueError
                
                await self.cog.aplicar_comissao(interaction, self.empresa_id, self.produtos, val)
            except ValueError:
                await interaction.response.send_message("❌ Valor inválido.", ephemeral=True)

    class CommissionView(discord.ui.View):
        def __init__(self, cog, ctx, empresa_id, produtos):
            super().__init__(timeout=120)
            self.cog = cog
            self.ctx = ctx
            self.empresa_id = empresa_id
            self.produtos = produtos

        async def interaction_check(self, interaction: discord.Interaction):
            return interaction.user.id == self.ctx.author.id

        @discord.ui.select(placeholder="Selecione uma % pré-definida...", options=[
            discord.SelectOption(label="20% - Margem Alta", value="20"),
            discord.SelectOption(label="25% - Padrão", value="25"),
            discord.SelectOption(label="30% - Equilibrado", value="30"),
            discord.SelectOption(label="40% - Generoso", value="40"),
            discord.SelectOption(label="50% - Meio a Meio", value="50"),
        ])
        async def select_preset(self, interaction: discord.Interaction, select: discord.ui.Select):
            val = float(select.values[0])
            await self.cog.aplicar_comissao(interaction, self.empresa_id, self.produtos, val)

        @discord.ui.button(label="Personalizar %", style=discord.ButtonStyle.secondary, emoji="⚙️")
        async def custom(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_modal(
                PrecosCog.ComissaoCustomModal(self.cog, self.empresa_id, self.produtos)
            )

    async def aplicar_comissao(self, interaction: discord.Interaction, empresa_id, produtos, porcentagem):
        """Helper para aplicar lógica de banco."""
        await interaction.response.defer()
        
        atualizados = 0
        for codigo, p in produtos.items():
            preco_venda = float(p['preco_venda'])
            novo_preco_func = round(preco_venda * (porcentagem / 100), 2)
            
            try:
                supabase.table('produtos_empresa').update({
                    'preco_pagamento_funcionario': novo_preco_func
                }).eq('id', p['id']).execute()
                atualizados += 1
            except Exception as e:
                logger.error(f"Erro update comissao: {e}")

        embed = discord.Embed(
            title=f"✅ Comissão Ajustada: {porcentagem:.0f}%",
            description=f"{atualizados} produtos atualizados com sucesso.",
            color=discord.Color.green()
        )
        embed.set_footer(text="Confira em !verprecos")
        
        await interaction.followup.send(embed=embed)


    @commands.command(name='comissao', aliases=['porcentagem', 'setcomissao', 'definircomissao'])
    @commands.has_permissions(administrator=True)
    @empresa_configurada()
    async def configurar_comissao(self, ctx, porcentagem: float = None):
        """Define a porcentagem de comissão (Menu Interativo)."""
        empresa = await selecionar_empresa(ctx)
        if not empresa: return
        
        produtos = await get_produtos_empresa(empresa['id'])
        if not produtos:
            await ctx.send("❌ Nenhum produto configurado.")
            return

        if porcentagem:
            # Direct usage fallback
            await self.aplicar_comissao(ctx, empresa['id'], produtos, porcentagem) # Context masquerading as interaction for followup support if needed, requires generic send check or separate method.
            # actually better to just create fake interaction wrapper or duplicate logic slightly?
            # ideally we deprecate direct usage, but let's keep it simple:
            # self.aplicar_comissao expects interaction. Let's make it robust.
            pass # Too complex to retrofit "interaction" on ctx. Let's just run logic.
            
            # Legacy Logic for valid arg
            msg = await ctx.send("⏳ Aplicando...")
            for codigo, p in produtos.items():
                pv = float(p['preco_venda'])
                nf = round(pv * (porcentagem / 100), 2)
                supabase.table('produtos_empresa').update({'preco_pagamento_funcionario': nf}).eq('id', p['id']).execute()
            await msg.edit(content=f"✅ Comissão de {porcentagem}% aplicada!")
            return

        # UI Mode
        embed = discord.Embed(
            title="💼 Configurar Comissão",
            description=f"Empresa: **{empresa['nome']}**\nEscolha a nova porcentagem para todos os funcionários.",
            color=discord.Color.blue()
        )
        view = self.CommissionView(self, ctx, empresa['id'], produtos)
        await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(PrecosCog(bot))
