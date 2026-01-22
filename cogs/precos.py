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


class PrecosCog(commands.Cog, name="Preços"):
    """Comandos de configuração de preços e comissões."""

    def __init__(self, bot):
        self.bot = bot

    # ============================================
    # CONFIGURAR PREÇOS MANUALMENTE
    # ============================================

    @commands.command(name='configurarprecos', aliases=['setprecos', 'editarprecos'])
    @commands.has_permissions(administrator=True)
    @empresa_configurada()
    async def configurar_precos(self, ctx):
        """Configura os preços dos produtos."""
        empresa = await selecionar_empresa(ctx)
        if not empresa:
            return
        
        produtos_ref = await get_produtos_referencia(empresa['tipo_empresa_id'])
        
        if not produtos_ref:
            await ctx.send("❌ Nenhum produto disponível para este tipo de empresa.")
            return
        
        # Agrupa por categoria
        categorias = {}
        for p in produtos_ref:
            cat = p['categoria'] or 'Outros'
            if cat not in categorias:
                categorias[cat] = []
            categorias[cat].append(p)
        
        embed = discord.Embed(
            title=f"💰 Configurar Preços - {empresa['nome']}",
            description="Escolha uma **categoria** para configurar (digite o número):",
            color=discord.Color.gold()
        )
        
        cats_list = list(categorias.keys())
        cats_text = ""
        for i, cat in enumerate(cats_list, 1):
            cats_text += f"`{i}.` {cat} ({len(categorias[cat])} produtos)\n"
        
        embed.add_field(name="Categorias", value=cats_text, inline=False)
        embed.add_field(
            name="💡 Dica",
            value="Ou use: `!configmin` (mínimo) | `!configmedio` (médio) | `!configmax` (máximo)",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            
            try:
                escolha = int(msg.content) - 1
                if escolha < 0 or escolha >= len(cats_list):
                    await ctx.send("❌ Número inválido.")
                    return
            except ValueError:
                await ctx.send("❌ Digite apenas o número.")
                return
            
            cat_escolhida = cats_list[escolha]
            produtos_cat = categorias[cat_escolhida]
            
            embed = discord.Embed(
                title=f"📦 {cat_escolhida}",
                description="Para configurar, digite: `codigo preco_venda preco_funcionario`\nExemplo: `ensopado_carne 1.40 0.35`\n\nDigite `pronto` quando terminar.",
                color=discord.Color.blue()
            )
            
            for p in produtos_cat[:25]:
                embed.add_field(
                    name=f"`{p['codigo']}`",
                    value=f"{p['nome']}\nRef: ${p['preco_minimo']:.2f} - ${p['preco_maximo']:.2f}",
                    inline=True
                )
            
            await ctx.send(embed=embed)
            
            configurados = 0

            while True:
                msg = await self.bot.wait_for('message', timeout=120.0, check=check)

                if msg.content.startswith('!'):
                    await ctx.send("⚠️ Configuração cancelada (outro comando detectado).")
                    return

                if msg.content.lower() in ['pronto', 'sair', 'cancelar']:
                    break

                parts = msg.content.split()
                if len(parts) != 3:
                    await ctx.send("❌ Formato: `codigo preco_venda preco_funcionario` (ou digite `pronto` para sair)")
                    continue

                codigo, pv, pf = parts
                produto = next((p for p in produtos_cat if p['codigo'] == codigo.lower()), None)

                if not produto:
                    await ctx.send(f"❌ Produto `{codigo}` não encontrado.")
                    continue

                try:
                    preco_venda = float(pv)
                    preco_func = float(pf)
                except ValueError:
                    await ctx.send("❌ Preços inválidos.")
                    continue

                if await configurar_produto_empresa(empresa['id'], produto['id'], preco_venda, preco_func):
                    await ctx.send(f"✅ `{produto['nome']}`: Venda ${preco_venda:.2f} | Funcionário ${preco_func:.2f}")
                    configurados += 1
                else:
                    await ctx.send(f"❌ Erro ao configurar {codigo}")

            await ctx.send(f"✅ {configurados} produtos configurados!")
            
        except asyncio.TimeoutError:
            await ctx.send("❌ Tempo esgotado.")

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
        
        produtos_ref = await get_produtos_referencia(empresa['tipo_empresa_id'])
        
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
            if modo == 'minimo':
                preco_venda = float(p['preco_minimo'])
            elif modo == 'maximo':
                preco_venda = float(p['preco_maximo'])
            else:
                preco_venda = (float(p['preco_minimo']) + float(p['preco_maximo'])) / 2
            
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

    @commands.command(name='comissao', aliases=['porcentagem', 'setcomissao', 'definircomissao'])
    @commands.has_permissions(administrator=True)
    @empresa_configurada()
    async def configurar_comissao(self, ctx, porcentagem: float = None):
        """Define a porcentagem de comissão dos funcionários. Uso: !comissao 30"""
        empresa = await selecionar_empresa(ctx)
        if not empresa:
            return
        
        if porcentagem is None:
            embed = discord.Embed(
                title="💼 Configurar Comissão dos Funcionários",
                description="Defina a porcentagem que os funcionários recebem por produto vendido.\n\n"
                            "**Exemplos:**\n"
                            "• `!comissao 25` → Funcionário recebe 25% do preço\n"
                            "• `!comissao 30` → Funcionário recebe 30% do preço\n"
                            "• `!comissao 50` → Funcionário recebe 50% do preço\n\n"
                            "**Opções Rápidas:** Digite o número abaixo ou use o comando completo.",
                color=discord.Color.blue()
            )
            embed.add_field(name="1️⃣ 20%", value="Margem alta", inline=True)
            embed.add_field(name="2️⃣ 25%", value="Padrão", inline=True)
            embed.add_field(name="3️⃣ 30%", value="Equilibrado", inline=True)
            embed.add_field(name="4️⃣ 40%", value="Funcionário bem pago", inline=True)
            embed.add_field(name="5️⃣ 50%", value="Divisão igual", inline=True)
            embed.add_field(name="❌ 0", value="Cancelar", inline=True)
            embed.set_footer(text="Digite o número da opção ou a porcentagem desejada (ex: 35)")
            
            await ctx.send(embed=embed)
            
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel
            
            try:
                msg = await self.bot.wait_for('message', timeout=60.0, check=check)
                
                if msg.content == '0':
                    await ctx.send("❌ Cancelado.")
                    return
                
                opcoes = {'1': 20, '2': 25, '3': 30, '4': 40, '5': 50}
                if msg.content in opcoes:
                    porcentagem = opcoes[msg.content]
                else:
                    try:
                        porcentagem = float(msg.content.replace('%', '').replace(',', '.'))
                    except ValueError:
                        await ctx.send("❌ Digite um número válido.")
                        return
            except asyncio.TimeoutError:
                await ctx.send("❌ Tempo esgotado.")
                return
        
        if porcentagem < 1 or porcentagem > 100:
            await ctx.send("❌ A porcentagem deve estar entre 1% e 100%.")
            return
        
        produtos = await get_produtos_empresa(empresa['id'])
        
        if not produtos:
            await ctx.send("❌ Nenhum produto configurado. Use `!configmedio` primeiro.")
            return
        
        progress_msg = await ctx.send(f"⏳ Aplicando comissão de **{porcentagem:.0f}%** em {len(produtos)} produtos...")
        
        atualizados = 0
        produtos_atualizados = []
        
        for codigo, p in produtos.items():
            preco_venda = float(p['preco_venda'])
            novo_preco_func = round(preco_venda * (porcentagem / 100), 2)
            
            try:
                supabase.table('produtos_empresa').update({
                    'preco_pagamento_funcionario': novo_preco_func
                }).eq('id', p['id']).execute()
                
                atualizados += 1
                produtos_atualizados.append({
                    'codigo': codigo,
                    'nome': p['produtos_referencia']['nome'],
                    'preco_venda': preco_venda,
                    'preco_func': novo_preco_func
                })
            except Exception as e:
                print(f"Erro ao atualizar {codigo}: {e}")
        
        try:
            await progress_msg.delete()
        except:
            pass
        
        embed_sucesso = discord.Embed(
            title=f"✅ Comissão Atualizada para {porcentagem:.0f}%!",
            description=f"**{atualizados}/{len(produtos)}** produtos de **{empresa['nome']}** atualizados.",
            color=discord.Color.green()
        )
        
        exemplo_venda = 10.00
        exemplo_func = exemplo_venda * (porcentagem / 100)
        exemplo_lucro = exemplo_venda - exemplo_func
        
        embed_sucesso.add_field(
            name="📊 Como Funciona",
            value=f"**Exemplo:** Produto vendido a $10.00\n"
                  f"• 👷 Funcionário recebe: **${exemplo_func:.2f}** ({porcentagem:.0f}%)\n"
                  f"• 🏢 Empresa fica com: **${exemplo_lucro:.2f}** ({100-porcentagem:.0f}%)",
            inline=False
        )
        
        embed_sucesso.add_field(
            name="💡 Comandos Úteis",
            value="`!verprecos` - Ver todos os preços atualizados\n"
                  "`!comissao [%]` - Alterar porcentagem novamente",
            inline=False
        )
        embed_sucesso.set_footer(text=f"Comissão anterior: 25% → Nova: {porcentagem:.0f}%")
        
        await ctx.send(embed=embed_sucesso)
        
        embed_precos = discord.Embed(
            title=f"💰 Novos Valores de Pagamento ({porcentagem:.0f}%)",
            description=f"Preços atualizados para **{empresa['nome']}**:",
            color=discord.Color.gold()
        )
        
        for p in produtos_atualizados[:24]:
            embed_precos.add_field(
                name=f"`{p['codigo']}`",
                value=f"**{p['nome'][:18]}**\n💵 ${p['preco_venda']:.2f} → 👷 ${p['preco_func']:.2f}",
                inline=True
            )
        
        if len(produtos_atualizados) > 24:
            embed_precos.set_footer(text=f"... e mais {len(produtos_atualizados) - 24} produtos")
        
        await ctx.send(embed=embed_precos)


async def setup(bot):
    await bot.add_cog(PrecosCog(bot))
