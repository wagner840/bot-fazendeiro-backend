"""
Production cog module - Commands for production, inventory and orders.
"""

from datetime import datetime
from decimal import Decimal
import discord
from discord.ext import commands
from config import supabase
from database import (
    get_or_create_funcionario,
    get_funcionario_by_discord_id,
    get_produtos_empresa,
    get_estoque_funcionario,
    get_estoque_global,
    get_estoque_global_detalhado,
    adicionar_ao_estoque,
    remover_do_estoque,
    remover_do_estoque_global,
)
from utils import empresa_configurada, selecionar_empresa
from ui_utils import create_success_embed, create_error_embed, create_info_embed
from logging_config import logger

from .ui_producao import ProducaoView
from .ui_estoque import InventoryView
from .ui_encomenda import ClientNameModal
from .entrega import entregar_modo_entrega, entregar_modo_producao


class ProducaoCog(commands.Cog, name="Produção"):
    """Comandos de gerenciamento de produção, estoque e encomendas."""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name='produzir', aliases=['add', 'fabricar'], description="Abre o menu de produção (Fabricação)")
    @empresa_configurada()
    async def produzir(self, ctx):
        """Abre o painel de produção interativo."""
        if ctx.interaction:
            await ctx.interaction.response.defer(ephemeral=True)

        empresa = await selecionar_empresa(ctx)
        if not empresa:
            return

        func_id = await get_or_create_funcionario(str(ctx.author.id), ctx.author.display_name, empresa['id'])
        if not func_id:
            await ctx.send(embed=create_error_embed("Erro", "Erro ao identificar funcionário."), ephemeral=True)
            return

        from utils import verificar_is_admin
        eh_admin = await verificar_is_admin(ctx, empresa)

        produtos = await get_produtos_empresa(empresa['id'])
        if not produtos:
            await ctx.send(embed=create_error_embed("Sem Produtos", "Nenhum produto configurado na empresa."), ephemeral=True)
            return

        view = ProducaoView(produtos, empresa['id'], func_id, eh_admin)
        embed = create_info_embed("🏭 Painel de Produção", "Selecione o produto abaixo para registrar sua produção.")
        await ctx.send(embed=embed, view=view, ephemeral=True)

    @commands.hybrid_command(name='estoque', aliases=['2', 'veranimais', 'meuestoque'], description="Mostra seu estoque pessoal.")
    @empresa_configurada()
    async def ver_estoque(self, ctx, membro: discord.Member = None):
        """Mostra estoque do funcionário (Menu Interativo)."""
        empresa = await selecionar_empresa(ctx)
        if not empresa:
            return
        target = membro or ctx.author

        func = await get_funcionario_by_discord_id(str(target.id))
        if not func:
            await ctx.send(embed=create_error_embed("Erro", f"{target.display_name} não cadastrado."), ephemeral=True)
            return

        estoque = await get_estoque_funcionario(func['id'], empresa['id'])
        modo_pagamento = empresa.get('modo_pagamento', 'producao')

        embed = discord.Embed(
            title=f"📦 Estoque de {target.display_name}",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Modo: {modo_pagamento.upper()} | Saldo: R$ {func['saldo']:.2f}")

        if not estoque:
            embed.description = "📭 Estoque vazio."
        else:
            total_valor = Decimal('0')
            description = ""
            for item in estoque:
                qtd = item['quantidade']
                valor_unit = Decimal(str(item['preco_funcionario']))
                valor_total = valor_unit * qtd
                total_valor += valor_total
                description += f"**{item['nome']}**: {qtd}x (Ref: R$ {valor_total:.2f})\n"

            embed.description = description

            if modo_pagamento == 'producao':
                embed.add_field(name="💰 A Receber (Acumulado)", value=f"R$ {total_valor:.2f}", inline=False)
            else:
                embed.add_field(name="💰 Valor Potencial", value=f"R$ {total_valor:.2f}", inline=False)

        view = None
        if target == ctx.author and estoque:
            view = InventoryView(ctx, estoque, func['id'], empresa['id'])

        await ctx.send(embed=embed, view=view)

    @commands.command(name='deletar', aliases=['3', 'remover'])
    @empresa_configurada()
    async def deletar_produto(self, ctx):
        """Atalho para abrir o menu de deleção via estoque."""
        await self.ver_estoque(ctx)

    @commands.command(name='estoqueglobal', aliases=['verestoque', 'producao'])
    @empresa_configurada()
    async def ver_estoque_global(self, ctx):
        """Mostra estoque global da empresa."""
        empresa = await selecionar_empresa(ctx)
        if not empresa:
            return

        estoque = await get_estoque_global(empresa['id'])
        embed = discord.Embed(title=f"🏢 Estoque Global - {empresa['nome']}", color=discord.Color.gold())

        if not estoque:
            embed.description = "📭 Nenhum produto em estoque."
        else:
            for item in estoque[:25]:
                embed.add_field(name=item['nome'], value=f"**{item['quantidade']}** unidades", inline=True)

        embed.set_footer(text=f"Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        await ctx.send(embed=embed)

    @commands.command(name='produtos', aliases=['catalogo', 'tabela', 'codigos'])
    @empresa_configurada()
    async def ver_produtos(self, ctx):
        """Lista todos os produtos configurados com seus códigos."""
        empresa = await selecionar_empresa(ctx)
        if not empresa:
            return
        produtos = await get_produtos_empresa(empresa['id'])

        if not produtos:
            await ctx.send(embed=create_error_embed("❌ Nenhum Produto", "A empresa ainda não tem produtos configurados."))
            return

        embed = discord.Embed(
            title=f"📦 Catálogo - {empresa['nome']}",
            description=f"**{len(produtos)}** produtos disponíveis",
            color=discord.Color.blue()
        )

        categorias = {}
        for codigo, p in produtos.items():
            cat = p['produtos_referencia'].get('categoria', 'Outros')
            if cat not in categorias:
                categorias[cat] = []
            categorias[cat].append((codigo, p))

        for cat, prods in list(categorias.items())[:6]:
            linhas = [f"`{c}` {p['produtos_referencia']['nome'][:18]} R${p['preco_venda']:.2f}" for c, p in prods[:6]]
            embed.add_field(name=f"📦 {cat}", value="\n".join(linhas) or "Vazio", inline=True)

        await ctx.send(embed=embed)

    @commands.hybrid_command(name='encomenda', aliases=['novaencomenda', 'pedido'], description="Cria uma nova encomenda interativa.")
    @empresa_configurada()
    async def nova_encomenda(self, ctx):
        """Inicia o assistente de criação de encomendas."""
        empresa = await selecionar_empresa(ctx)
        if not empresa:
            return

        func_id = await get_or_create_funcionario(str(ctx.author.id), ctx.author.display_name, empresa['id'])
        if not func_id:
            await ctx.send(embed=create_error_embed("Acesso Negado", "Você precisa ser funcionário."), ephemeral=True)
            return

        produtos = await get_produtos_empresa(empresa['id'])
        if not produtos:
            await ctx.send(embed=create_error_embed("Sem Produtos", "Empresa sem produtos configurados."), ephemeral=True)
            return

        if ctx.interaction:
            await ctx.interaction.response.send_modal(ClientNameModal(ctx, produtos, empresa['id'], func_id))
        else:
            view = discord.ui.View()
            btn = discord.ui.Button(label="📝 Criar Encomenda", style=discord.ButtonStyle.primary)

            async def btn_callback(interaction: discord.Interaction):
                if interaction.user.id != ctx.author.id:
                    await interaction.response.send_message("Apenas quem chamou o comando pode usar.", ephemeral=True)
                    return
                await interaction.response.send_modal(ClientNameModal(ctx, produtos, empresa['id'], func_id))

            btn.callback = btn_callback
            view.add_item(btn)
            await ctx.send("Clique abaixo para preencher os dados da encomenda:", view=view)

    @commands.command(name='encomendas', aliases=['5', 'pendentes'])
    @empresa_configurada()
    async def ver_encomendas(self, ctx):
        """Lista encomendas pendentes com visual melhorado."""
        empresa = await selecionar_empresa(ctx)
        if not empresa:
            return

        response = await supabase.table('encomendas').select(
            '*, funcionarios(nome)'
        ).eq('empresa_id', empresa['id']).in_(
            'status', ['pendente', 'em_andamento']
        ).order('data_criacao').execute()

        encomendas = response.data

        if not encomendas:
            embed = discord.Embed(
                title="📋 Encomendas",
                description="✅ Nenhuma encomenda pendente!\n\n"
                            "Use `!novaencomenda` para criar uma nova.",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/190/190411.png")
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title=f"📋 Encomendas Pendentes - {empresa['nome']}",
            description=f"Total: **{len(encomendas)}** encomenda(s)",
            color=discord.Color.blue()
        )

        for enc in encomendas[:10]:
            itens_str = " · ".join([f"{i['quantidade']}x `{i['codigo']}`" for i in enc['itens_json']])
            resp = enc.get('funcionarios', {})
            responsavel = resp.get('nome', 'N/A') if resp else 'N/A'

            status_info = {
                'pendente': ('🟡', 'Pendente'),
                'em_andamento': ('🔵', 'Em andamento')
            }
            emoji, status_text = status_info.get(enc['status'], ('⚪', enc['status']))

            embed.add_field(
                name=f"{emoji} #{enc['id']} | {enc['comprador']}",
                value=f"**Itens:** {itens_str}\n"
                      f"**Valor:** R$ {enc['valor_total']:.2f}\n"
                      f"**Resp:** {responsavel}\n"
                      f"*Para entregar: `!entregar {enc['id']}`*",
                inline=False
            )

        if len(encomendas) > 10:
            embed.set_footer(text=f"Mostrando 10 de {len(encomendas)} encomendas")
        else:
            embed.set_footer(text="💡 Use !entregar [ID] (Ex: !entregar 9) para finalizar!")

        await ctx.send(embed=embed)

    @commands.command(name='entregar', aliases=['entregarencomenda'])
    @empresa_configurada()
    async def entregar_encomenda(self, ctx, encomenda_id: int = None):
        """Entrega encomenda completa."""
        empresa = await selecionar_empresa(ctx)
        if not empresa:
            return

        if encomenda_id is None:
            embed = discord.Embed(
                title="❓ Como Entregar Encomendas",
                description="Você precisa informar o **ID da Encomenda** que deseja entregar.",
                color=discord.Color.gold()
            )
            embed.add_field(
                name="1️⃣ Ver IDs",
                value="Use o comando `!encomendas` para ver a lista de pedidos pendentes e seus IDs (Ex: #1, #2).",
                inline=False
            )
            embed.add_field(
                name="2️⃣ Entregar",
                value="Digite `!entregar [ID]`.\nExemplo: `!entregar 9`",
                inline=False
            )
            await ctx.send(embed=embed)
            return

        func = await get_funcionario_by_discord_id(str(ctx.author.id))
        if not func:
            embed = discord.Embed(
                title="❌ Você não está cadastrado",
                description="Para entregar encomendas, você precisa ser cadastrado.",
                color=discord.Color.red()
            )
            embed.add_field(
                name="📋 Como se cadastrar?",
                value="Peça a um **administrador** para usar:\n`!bemvindo @você`",
                inline=False
            )
            await ctx.send(embed=embed)
            return

        response = await supabase.table('encomendas').select('*').eq('id', encomenda_id).eq('empresa_id', empresa['id']).execute()

        if not response.data:
            await ctx.send(f"❌ Encomenda #{encomenda_id} não encontrada.\n💡 Use `!encomendas` para ver as pendentes.")
            return

        encomenda = response.data[0]

        if encomenda['status'] == 'entregue':
            await ctx.send("❌ Esta encomenda já foi entregue.")
            return

        modo_pagamento = empresa.get('modo_pagamento', 'producao')

        if modo_pagamento == 'entrega':
            await entregar_modo_entrega(ctx, empresa, encomenda, func, encomenda_id, self.bot)
        else:
            await entregar_modo_producao(ctx, empresa, encomenda, func, encomenda_id, self.bot)


async def setup(bot):
    await bot.add_cog(ProducaoCog(bot))
