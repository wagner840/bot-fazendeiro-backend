from datetime import datetime
from decimal import Decimal
import discord
from discord.ext import commands
from config import supabase, PRODUTO_REGEX
from database import (
    get_or_create_funcionario,
    get_funcionario_by_discord_id,
    get_produtos_empresa,
    adicionar_ao_estoque,
    remover_do_estoque,
    get_estoque_funcionario,
    get_estoque_global,
    criar_encomenda
)
from utils import empresa_configurada, selecionar_empresa
from ui_utils import create_success_embed, create_error_embed, create_info_embed, handle_interaction_error
from logging_config import logger

# ============================================
# UI COMPONENTS - PRODUÇÃO
# ============================================

class ProducaoModal(discord.ui.Modal, title="Registrar Produção"):
    def __init__(self, produto_codigo: str, produto_nome: str, produto_preco: float, empresa_id: int, func_id: int, eh_admin: bool):
        super().__init__()
        self.produto_codigo = produto_codigo
        self.produto_nome = produto_nome
        self.produto_preco = produto_preco
        self.empresa_id = empresa_id
        self.func_id = func_id
        self.eh_admin = eh_admin

        self.quantidade = discord.ui.TextInput(
            label=f"Quantidade de {produto_nome}",
            placeholder="Ex: 100",
            min_length=1,
            max_length=5,
            required=True
        )
        self.add_item(self.quantidade)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            qty = int(self.quantidade.value)
            if qty <= 0:
                raise ValueError("Quantidade deve ser maior que zero.")
        except ValueError:
            await interaction.response.send_message(
                embed=create_error_embed("Erro", "Quantidade inválida. Digite apenas números inteiros positivos."),
                ephemeral=True
            )
            return

        resultado = await adicionar_ao_estoque(self.func_id, self.empresa_id, self.produto_codigo, qty)
        
        if resultado:
            if self.eh_admin:
                txt_comissao = "Isento (Admin)"
            else:
                comissao = Decimal(str(self.produto_preco)) * qty
                txt_comissao = f"💰 Acumulado: R$ {comissao:.2f}"
            
            embed = create_success_embed("Produção Registrada!")
            embed.add_field(name=f"🏭 {self.produto_nome}", value=f"+{qty} (Total: {resultado['quantidade']})\n{txt_comissao}", inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=create_error_embed("Erro", "Falha ao adicionar ao estoque."), ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await handle_interaction_error(interaction, error)

class ProducaoSelect(discord.ui.Select):
    def __init__(self, produtos: dict, empresa_id: int, func_id: int, eh_admin: bool):
        options = []
        for codigo, p in list(produtos.items())[:25]:
            nome = p['produtos_referencia']['nome']
            preco = p['preco_pagamento_funcionario']
            label = f"{nome[:20]} (R$ {preco})"
            options.append(discord.SelectOption(label=label, value=codigo, description=f"Cód: {codigo}"))

        super().__init__(placeholder="Selecione um produto para produzir...", min_values=1, max_values=1, options=options)
        self.produtos = produtos
        self.empresa_id = empresa_id
        self.func_id = func_id
        self.eh_admin = eh_admin

    async def callback(self, interaction: discord.Interaction):
        codigo = self.values[0]
        prod = self.produtos[codigo]
        
        modal = ProducaoModal(
            produto_codigo=codigo,
            produto_nome=prod['produtos_referencia']['nome'],
            produto_preco=prod['preco_pagamento_funcionario'],
            empresa_id=self.empresa_id,
            func_id=self.func_id,
            eh_admin=self.eh_admin
        )
        await interaction.response.send_modal(modal)

class ProducaoView(discord.ui.View):
    def __init__(self, produtos: dict, empresa_id: int, func_id: int, eh_admin: bool):
        super().__init__(timeout=180)
        self.add_item(ProducaoSelect(produtos, empresa_id, func_id, eh_admin))

# ============================================
# UI COMPONENTS - ESTOQUE & DELETE
# ============================================

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
                # Busca quantidade atual para remover tudo
                from database import get_estoque_funcionario
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

# ============================================
# UI COMPONENTS - ENCOMENDAS
# ============================================

class OrderQtyModal(discord.ui.Modal, title="Quantidade do Item"):
    def __init__(self, builder_view, produto_codigo, produto_nome, preco):
        super().__init__()
        self.builder_view = builder_view
        self.produto_codigo = produto_codigo
        self.produto_nome = produto_nome
        self.preco = preco

        self.qty = discord.ui.TextInput(
            label=f"Qtd de {produto_nome}",
            placeholder="Ex: 50",
            min_length=1, max_length=5, required=True
        )
        self.add_item(self.qty)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            qtd = int(self.qty.value)
            if qtd <= 0: raise ValueError
        except:
            await interaction.response.send_message(embed=create_error_embed("Erro", "Quantidade inválida."), ephemeral=True)
            return

        await self.builder_view.add_to_cart(interaction, self.produto_codigo, self.produto_nome, qtd, self.preco)

class ProductSelectOrder(discord.ui.Select):
    def __init__(self, builder_view, produtos):
        options = []
        for codigo, p in list(produtos.items())[:25]:
            nome = p['produtos_referencia']['nome']
            preco = p['preco_venda']
            options.append(discord.SelectOption(
                label=f"{nome}", 
                value=codigo, 
                description=f"R$ {preco:.2f}",
                emoji="📦"
            ))
        super().__init__(placeholder="Selecione um produto para adicionar...", options=options)
        self.builder_view = builder_view
        self.produtos = produtos

    async def callback(self, interaction: discord.Interaction):
        codigo = self.values[0]
        prod = self.produtos[codigo]
        await interaction.response.send_modal(
            OrderQtyModal(
                self.builder_view, codigo, 
                prod['produtos_referencia']['nome'], 
                float(prod['preco_venda'])
            )
        )

class OrderBuilderView(discord.ui.View):
    def __init__(self, ctx, produtos, empresa_id, func_id, comprador_nome):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.produtos = produtos
        self.empresa_id = empresa_id
        self.func_id = func_id
        self.comprador_nome = comprador_nome
        self.cart = []

        self.add_item(ProductSelectOrder(self, produtos))

    async def update_message(self, interaction: discord.Interaction):
        total = sum(i['valor'] for i in self.cart)
        
        embed = discord.Embed(
            title=f"📦 Nova Encomenda: {self.comprador_nome}",
            description="Adicione itens usando o menu abaixo.",
            color=discord.Color.blue()
        )
        
        cart_text = ""
        if not self.cart:
            cart_text = "🛒 Carrinho vazio."
        else:
            for idx, item in enumerate(self.cart):
                cart_text += f"{idx+1}. **{item['nome']}** x{item['qtd']} (R$ {item['valor']:.2f})\n"
        
        embed.add_field(name="Itens", value=cart_text, inline=False)
        embed.add_field(name="💰 Total", value=f"**R$ {total:.2f}**", inline=False)
        
        # Find Confirm Button and Enable/Disable
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.label == "Finalizar Encomenda":
                item.disabled = len(self.cart) == 0
                break
        
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    async def add_to_cart(self, interaction: discord.Interaction, codigo, nome, qtd, preco_unit):
        valor = Decimal(str(qtd)) * Decimal(str(preco_unit))
        existing = next((i for i in self.cart if i['codigo'] == codigo), None)
        if existing:
            existing['qtd'] += qtd
            existing['valor'] += valor
        else:
            self.cart.append({
                'codigo': codigo,
                'nome': nome,
                'qtd': qtd,
                'preco_unit': preco_unit,
                'valor': valor
            })
        await self.update_message(interaction)

    @discord.ui.button(label="Finalizar Encomenda", style=discord.ButtonStyle.green, emoji="✅", disabled=True, row=1)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.cart: return
        itens_db = [{
            'codigo': i['codigo'],
            'nome': i['nome'],
            'quantidade': i['qtd'],
            'quantidade_entregue': 0,
            'valor_unitario': i['preco_unit'],
            'valor': float(i['valor'])
        } for i in self.cart]
        try:
            encomenda = await criar_encomenda(
                empresa_id=self.empresa_id,
                comprador=self.comprador_nome,
                itens=itens_db
            )
            if not encomenda: raise Exception("Erro ao criar encomenda via DB.")
            
            embed = create_success_embed(f"Encomenda #{encomenda['id']} Criada!", f"Cliente: {self.comprador_nome}")
            embed.add_field(name="Total", value=f"R$ {encomenda['valor_total']:.2f}")
            embed.set_footer(text="Use !entregar para finalizar a entrega.")
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
        except Exception as e:
            await handle_interaction_error(interaction, e)

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.red, emoji="❌", row=1)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_error_embed("Cancelado", "Encomenda cancelada."), view=None)
        self.stop()

class ClientNameModal(discord.ui.Modal, title="Nome do Cliente"):
    def __init__(self, ctx, produtos, empresa_id, func_id):
        super().__init__()
        self.ctx = ctx
        self.produtos = produtos
        self.empresa_id = empresa_id
        self.func_id = func_id

        self.nome = discord.ui.TextInput(
            label="Nome do Comprador",
            placeholder="Ex: Delegacia, Hospital...",
            min_length=3,
            required=True
        )
        self.add_item(self.nome)

    async def on_submit(self, interaction: discord.Interaction):
        view = OrderBuilderView(self.ctx, self.produtos, self.empresa_id, self.func_id, self.nome.value)
        embed = create_info_embed(f"📦 Nova Encomenda: {self.nome.value}", "Selecione os produtos abaixo para montar o pedido.")
        embed.add_field(name="Carrinho", value="Vazio", inline=False)
        await interaction.response.send_message(embed=embed, view=view)

# ============================================
# COG PRINCIPAL
# ============================================

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
        if not empresa: return

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
        if not empresa: return
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
        if not empresa: return
        
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
        if not empresa: return
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
            if cat not in categorias: categorias[cat] = []
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
        if not empresa: return
        
        func_id = await get_or_create_funcionario(str(ctx.author.id), ctx.author.display_name, empresa['id'])
        if not func_id:
            await ctx.send(embed=create_error_embed("Acesso Negado", "Você precisa ser funcionário."), ephemeral=True)
            return
            
        produtos = await get_produtos_empresa(empresa['id'])
        if not produtos:
            await ctx.send(embed=create_error_embed("Sem Produtos", "Empresa sem produtos configurados."), ephemeral=True)
            return

        # Fix for hybrid command: Check if interaction exists
        if ctx.interaction:
            await ctx.interaction.response.send_modal(ClientNameModal(ctx, produtos, empresa['id'], func_id))
        else:
            # Fallback for text command: Send a button to open the modal
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

    # ============================================
    # ENCOMENDAS - VER (VISUAL MELHORADO)
    # ============================================

    @commands.command(name='encomendas', aliases=['5', 'pendentes'])
    @empresa_configurada()
    async def ver_encomendas(self, ctx):
        """Lista encomendas pendentes com visual melhorado."""
        empresa = await selecionar_empresa(ctx)
        if not empresa:
            return
        
        response = supabase.table('encomendas').select(
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
            # Formata itens
            itens_str = " · ".join([f"{i['quantidade']}x `{i['codigo']}`" for i in enc['itens_json']])
            
            # Responsável
            resp = enc.get('funcionarios', {})
            responsavel = resp.get('nome', 'N/A') if resp else 'N/A'
            
            # Status visual
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

    # ============================================
    # ENCOMENDAS - ENTREGAR
    # ============================================

    @commands.command(name='entregar', aliases=['entregarencomenda'])
    @empresa_configurada()
    async def entregar_encomenda(self, ctx, encomenda_id: int = None):
        """Entrega encomenda completa."""
        empresa = await selecionar_empresa(ctx)
        if not empresa:
            return

        # Improved Error Handling/Tutorial for missing ID
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
        
        response = supabase.table('encomendas').select('*').eq('id', encomenda_id).eq('empresa_id', empresa['id']).execute()
        
        if not response.data:
            await ctx.send(f"❌ Encomenda #{encomenda_id} não encontrada.\n💡 Use `!encomendas` para ver as pendentes.")
            return
        
        encomenda = response.data[0]
        
        if encomenda['status'] == 'entregue':
            await ctx.send("❌ Esta encomenda já foi entregue.")
            return
        
        # Verifica estoque do funcionário
        estoque = await get_estoque_funcionario(func['id'], empresa['id'])
        estoque_dict = {e['produto_codigo']: e['quantidade'] for e in estoque}
        
        # Calcula o que falta
        itens_com_estoque = []
        itens_sem_estoque = []
        valor_comissao = Decimal('0')
        
        for item in encomenda['itens_json']:
            precisa = item['quantidade'] - item.get('quantidade_entregue', 0)
            tem = estoque_dict.get(item['codigo'], 0)
            
            if tem >= precisa:
                # Tem estoque suficiente - ganha comissão
                itens_com_estoque.append({
                    'item': item,
                    'precisa': precisa,
                    'tem': tem
                })
                # Busca preço do funcionário para comissão
                preco_func = next(
                    (e['preco_funcionario'] for e in estoque if e['produto_codigo'] == item['codigo']),
                    0
                )
                valor_comissao += Decimal(str(preco_func)) * precisa
            else:
                # Não tem estoque suficiente
                itens_sem_estoque.append({
                    'item': item,
                    'precisa': precisa,
                    'tem': tem,
                    'falta': precisa - tem
                })
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        # Se tem itens sem estoque, pergunta se quer entregar mesmo assim
        if itens_sem_estoque:
            embed = discord.Embed(
                title="⚠️ Estoque Insuficiente",
                description=f"Você não tem todos os itens no seu estoque pessoal.",
                color=discord.Color.orange()
            )
            
            # Mostra o que falta
            faltando_text = "\n".join([
                f"• **{i['item']['nome']}**: precisa {i['precisa']}, tem {i['tem']} (falta {i['falta']})"
                for i in itens_sem_estoque
            ])
            embed.add_field(name="📦 Itens Faltando", value=faltando_text, inline=False)
            
            # Mostra o que tem
            if itens_com_estoque:
                tem_text = "\n".join([
                    f"• **{i['item']['nome']}**: {i['precisa']}x ✅"
                    for i in itens_com_estoque
                ])
                embed.add_field(name="✅ Itens que Você Tem", value=tem_text, inline=False)
            
            embed.add_field(
                name="❓ Entregar mesmo assim?",
                value="Se você entregar **SEM** ter fabricado os produtos:\n"
                      "• A venda será registrada normalmente\n"
                      "• ❌ Você **NÃO receberá comissão** pelos itens que não fabricou\n\n"
                      "Digite **sim** para entregar ou **não** para cancelar",
                inline=False
            )
            
            if itens_com_estoque:
                embed.set_footer(text=f"💰 Comissão garantida (itens que você tem): R$ {valor_comissao:.2f}")
            else:
                embed.set_footer(text="💰 Sem comissão (você não fabricou nenhum item)")
            
            await ctx.send(embed=embed)
            
            try:
                msg = await self.bot.wait_for('message', timeout=30.0, check=check)
                if msg.content.lower() not in ['sim', 's', 'yes', 'y']:
                    await ctx.send("❌ Entrega cancelada.\n💡 Use `!add codigo10` para adicionar produtos ao seu estoque primeiro.")
                    return
            except:
                await ctx.send("❌ Tempo esgotado. Entrega cancelada.")
                return
        
        # Processa a entrega
        # 1. Remove do estoque apenas os itens que o funcionário TEM
        for item_info in itens_com_estoque:
            item = item_info['item']
            precisa = item_info['precisa']
            await remover_do_estoque(func['id'], empresa['id'], item['codigo'], precisa)
        
        # 2. Atualiza status da encomenda
        supabase.table('encomendas').update({
            'status': 'entregue',
            'data_entrega': datetime.utcnow().isoformat()
        }).eq('id', encomenda_id).execute()
        
        # 3. Se teve comissão, adiciona como PENDÊNCIA (para ser pago no !pagarestoque)
        if valor_comissao > 0:
            # Registra transação de comissão pendente
            supabase.table('transacoes').insert({
                'empresa_id': empresa['id'],
                'tipo': 'comissao_pendente',
                'valor': float(valor_comissao),
                'descricao': f'Comissão Encomenda #{encomenda_id}',
                'funcionario_id': func['id']
            }).execute()
        
        # Monta embed de sucesso
        embed = discord.Embed(
            title="✅ Encomenda Entregue!",
            description=f"**ID:** #{encomenda_id}\n**Cliente:** {encomenda['comprador']}",
            color=discord.Color.green()
        )
        
        embed.add_field(name="📦 Valor da Venda", value=f"R$ {encomenda['valor_total']:.2f}", inline=True)
        
        if valor_comissao > 0:
            embed.add_field(name="💰 Comissão Acumulada", value=f"R$ {valor_comissao:.2f}", inline=True)
            embed.set_footer(text=f"Comissão registrada! Use !pagarestoque para receber.")
        else:
            embed.add_field(name="💰 Sua Comissão", value="R$ 0.00", inline=True)
            embed.set_footer(text="Sem comissão pois você não fabricou os itens.")
        
        if itens_sem_estoque:
            sem_comissao = "\n".join([f"• {i['item']['nome']} ({i['precisa']}x)" for i in itens_sem_estoque])
            embed.add_field(
                name="⚠️ Entregue SEM Comissão",
                value=sem_comissao,
                inline=False
            )
        
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ProducaoCog(bot))
