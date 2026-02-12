"""
Precos cog module - Commands for price and commission configuration.
"""

import discord
from discord.ext import commands
from config import supabase
from database import (
    get_produtos_referencia,
    get_produtos_empresa,
    configurar_produto_empresa
)
from utils import empresa_configurada, selecionar_empresa

from .ui_config import PriceConfigurationView
from .ui_comissao import CommissionView, aplicar_comissao
from .auto_config import configurar_precos_com_feedback


class PrecosCog(commands.Cog, name="Precos"):
    """Comandos de configuracao de precos e comissoes."""

    def __init__(self, bot):
        self.bot = bot

    # ============================================
    # CONFIGURAR PRECOS MANUALMENTE
    # ============================================

    @commands.command(name='configurarprecos', aliases=['setprecos', 'editarprecos'])
    @commands.has_permissions(administrator=True)
    @empresa_configurada()
    async def configurar_precos(self, ctx):
        """Configura os precos dos produtos (Menu Interativo)."""
        empresa = await selecionar_empresa(ctx)
        if not empresa:
            return

        produtos_ref = await get_produtos_referencia(empresa['tipo_empresa_id'], guild_id=str(ctx.guild.id))
        if not produtos_ref:
            await ctx.send("Nenhum produto disponivel.")
            return

        # Prepare Data
        categorias = {}
        for p in produtos_ref:
            cat = p.get('categoria') or 'Outros'
            if cat not in categorias:
                categorias[cat] = []
            categorias[cat].append(p)

        view = PriceConfigurationView(ctx, categorias, produtos_ref, empresa['id'])

        embed = discord.Embed(
            title=f"Editor de Precos - {empresa['nome']}",
            description="Selecione uma **Categoria** abaixo para ver os produtos.\nDepois, clique no produto para editar o preco.",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed, view=view)

    # ============================================
    # CONFIGURACAO AUTOMATICA DE PRECOS
    # ============================================

    @commands.command(name='configmin', aliases=['configminimo', 'precosmin'])
    @commands.has_permissions(administrator=True)
    @empresa_configurada()
    async def configurar_minimo(self, ctx):
        """Configura todos os produtos com preco MINIMO (25% funcionario)."""
        empresa = await selecionar_empresa(ctx)
        if not empresa:
            return
        await configurar_precos_com_feedback(ctx, empresa, 'minimo')

    @commands.command(name='configmedio', aliases=['configurarauto', 'autoconfig', 'precosmed'])
    @commands.has_permissions(administrator=True)
    @empresa_configurada()
    async def configurar_medio(self, ctx):
        """Configura todos os produtos com preco MEDIO (25% funcionario)."""
        empresa = await selecionar_empresa(ctx)
        if not empresa:
            return
        await configurar_precos_com_feedback(ctx, empresa, 'medio')

    @commands.command(name='configmax', aliases=['configmaximo', 'precosmax'])
    @commands.has_permissions(administrator=True)
    @empresa_configurada()
    async def configurar_maximo(self, ctx):
        """Configura todos os produtos com preco MAXIMO (25% funcionario)."""
        empresa = await selecionar_empresa(ctx)
        if not empresa:
            return
        await configurar_precos_com_feedback(ctx, empresa, 'maximo')

    # ============================================
    # VER PRECOS
    # ============================================

    @commands.command(name='verprecos', aliases=['precos', 'listaprecos', 'tabelaprecos', 'meusprecos'])
    @empresa_configurada()
    async def ver_precos(self, ctx, *, categoria: str = None):
        """Ver precos dos produtos. Uso: !precos [categoria]"""
        empresa = await selecionar_empresa(ctx)
        if not empresa:
            return

        produtos = await get_produtos_empresa(empresa['id'])

        if not produtos:
            await ctx.send("Nenhum produto configurado. Use `!configmedio` para configurar.")
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
                await ctx.send(f"Categoria `{categoria}` nao encontrada.")
                return

            categorias = {cat_encontrada: categorias[cat_encontrada]}

        # Mostra todos os produtos por categoria
        embed = discord.Embed(
            title=f"Tabela de Precos",
            description=f"**{empresa['nome']}**\n`Venda` | `Funcionario`",
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
                linhas.append(f"`{codigo}` {nome}\n${venda:.2f} | ${func:.2f}")

            # Divide em chunks se necessario (limite de 1024 chars por field)
            texto = "\n".join(linhas)

            if len(texto) <= 1024:
                if field_count >= 25:
                    embed = discord.Embed(color=discord.Color.gold())
                    embeds.append(embed)
                    field_count = 0
                embed.add_field(name=f"{cat} ({len(prods)})", value=texto, inline=False)
                field_count += 1
            else:
                # Divide em multiplos fields
                chunk = []
                chunk_len = 0
                for linha in linhas:
                    if chunk_len + len(linha) + 1 > 1000:
                        if field_count >= 25:
                            embed = discord.Embed(color=discord.Color.gold())
                            embeds.append(embed)
                            field_count = 0
                        embed.add_field(name=f"{cat}", value="\n".join(chunk), inline=False)
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
                    embed.add_field(name=f"{cat} (cont.)", value="\n".join(chunk), inline=False)
                    field_count += 1

        embeds[-1].set_footer(text=f"Total: {len(produtos)} produtos | !configurarprecos para editar")

        for e in embeds:
            await ctx.send(embed=e)

    # ============================================
    # CONFIGURAR COMISSAO
    # ============================================

    @commands.command(name='comissao', aliases=['porcentagem', 'setcomissao', 'definircomissao'])
    @commands.has_permissions(administrator=True)
    @empresa_configurada()
    async def configurar_comissao(self, ctx, porcentagem: float = None):
        """Define a porcentagem de comissao (Menu Interativo)."""
        empresa = await selecionar_empresa(ctx)
        if not empresa:
            return

        produtos = await get_produtos_empresa(empresa['id'])
        if not produtos:
            await ctx.send("Nenhum produto configurado.")
            return

        if porcentagem:
            # Modo direto: aplica comissao imediatamente
            msg = await ctx.send("Aplicando...")
            for codigo, p in produtos.items():
                pv = float(p['preco_venda'])
                nf = round(pv * (porcentagem / 100), 2)
                await supabase.table('produtos_empresa').update({'preco_pagamento_funcionario': nf}).eq('id', p['id']).execute()
            await msg.edit(content=f"OK Comissao de {porcentagem}% aplicada!")
            return

        # UI Mode
        embed = discord.Embed(
            title="Configurar Comissao",
            description=f"Empresa: **{empresa['nome']}**\nEscolha a nova porcentagem para todos os funcionarios.",
            color=discord.Color.blue()
        )
        view = CommissionView(ctx, empresa['id'], produtos, aplicar_comissao)
        await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(PrecosCog(bot))
