"""
Bot Multi-Empresa Downtown - Cog de Produção
Comandos para gerenciamento de estoque, produtos e encomendas.
"""

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
    get_estoque_global
)
from utils import empresa_configurada, selecionar_empresa


class ProducaoCog(commands.Cog, name="Produção"):
    """Comandos de gerenciamento de produção, estoque e encomendas."""

    def __init__(self, bot):
        self.bot = bot

    # ============================================
    # ESTOQUE - ADICIONAR
    # ============================================

    @commands.command(name='add', aliases=['1', 'produzir', 'fabricar'])
    @empresa_configurada()
    async def add_produto(self, ctx, *, entrada: str = None):
        """Adiciona produtos ao seu estoque (fabricação). Uso: !add rotulo 10 ou !add rotulo10"""
        empresa = await selecionar_empresa(ctx)
        if not empresa: return
        
        func_id = await get_or_create_funcionario(str(ctx.author.id), ctx.author.display_name, empresa['id'])
        if not func_id:
            await ctx.send("❌ Erro ao identificar funcionário.")
            return

        # Verifica se é Admin (isento de comissão)
        from config import supabase
        eh_admin = False
        try:
            # Verifica na tabela de usuarios_frontend se tem role admin/superadmin nessa guild
            resp = supabase.table('usuarios_frontend').select('role').eq('discord_id', str(ctx.author.id)).eq('guild_id', str(ctx.guild.id)).execute()
            if resp.data:
                role = resp.data[0]['role']
                if role in ['admin', 'superadmin']:
                    eh_admin = True
        except:
            pass

        produtos = await get_produtos_empresa(empresa['id'])
        if not produtos:
            await ctx.send("❌ Nenhum produto configurado.")
            return

        modo_pagamento = empresa.get('modo_pagamento', 'producao')
        
        # Ajuda interativa
        if not entrada:
            embed = discord.Embed(title="🏭 Adicionar Produção", description="Adicione produtos fabricados.", color=discord.Color.blue())
            
            if eh_admin:
                embed.add_field(name="🛡️ Admin", value="Você é **Admin**, não recebe comissão (Isento).", inline=False)
            elif modo_pagamento == 'producao':
                embed.add_field(name="💰 Pagamento", value="✅ **Acumulativo** (pago via !pagarestoque)", inline=False)
            else:
                embed.add_field(name="💰 Pagamento", value="📦 **Comissão** (pago ao entregar + !pagarestoque)", inline=False)

            prods_sample = list(produtos.items())[:6]
            prods_text = "\n".join([f"`{c}` - {p['produtos_referencia']['nome']}" for c, p in prods_sample])
            if len(produtos) > 6: prods_text += f"\n*+{len(produtos)-6} mais... use `!produtos`*"
            
            embed.add_field(name="📦 Disponíveis", value=prods_text, inline=False)
            embed.set_footer(text="Ex: !add rotulo 100")
            await ctx.send(embed=embed)
            return
        
        # Parse entrada
        import re
        entrada_limpa = entrada.strip()
        partes = entrada_limpa.split()
        itens_para_add = []
        
        if len(partes) == 2 and partes[1].isdigit():
            itens_para_add.append((partes[0].lower(), int(partes[1])))
        else:
            matches = PRODUTO_REGEX.findall(entrada)
            if matches:
                 for c, q in matches: itens_para_add.append((c.lower(), int(q)))
            else:
                codigo = entrada_limpa.lower()
                if codigo in produtos:
                    embed = discord.Embed(title="❓ Quantidade?", description=f"Produto: **{produtos[codigo]['produtos_referencia']['nome']}**", color=discord.Color.blue())
                    await ctx.send(embed=embed)
                    try:
                        msg = await self.bot.wait_for('message', timeout=30.0, check=lambda m: m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit())
                        itens_para_add.append((codigo, int(msg.content)))
                    except:
                        return
                else:
                    await ctx.send(f"❌ Não entendi `{entrada}`.")
                    return

        # Processa
        resultados = []
        erros = []
        total_comissao = Decimal('0')
        func = await get_funcionario_by_discord_id(str(ctx.author.id))
        
        for codigo, quantidade in itens_para_add:
            if quantidade <= 0: continue
            if codigo not in produtos:
                erros.append(f"`{codigo}` não encontrado.")
                continue
                
            resultado = await adicionar_ao_estoque(func_id, empresa['id'], codigo, quantidade)
            if resultado:
                # Se for admin, comissão é ZERO
                if eh_admin:
                    comissao = Decimal('0')
                else:
                    preco_func = Decimal(str(produtos[codigo]['preco_pagamento_funcionario']))
                    comissao = preco_func * quantidade
                
                total_comissao += comissao
                resultados.append({
                    'nome': resultado['nome'],
                    'adicionado': quantidade,
                    'total': resultado['quantidade'],
                    'comissao': float(comissao)
                })
            else:
                erros.append(codigo)

        pago_agora = False
        # Pagamento modificado para ser sempre manual (acumulado)
        # O valor fica no estoque e é pago via !pagarestoque ou quando entregue (comissao_pendente)

        if resultados:
            embed = discord.Embed(title="✅ Produção Registrada!", color=discord.Color.green())
            if eh_admin:
                embed.description = "🛡️ **Modo Admin:** Produção registrada sem custos."
            
            for r in resultados:
                txt_comissao = "Isento (Admin)" if eh_admin else f"💰 Acumulado: R$ {r['comissao']:.2f}"
                embed.add_field(name=f"🏭 {r['nome']}", value=f"+{r['adicionado']} (Total: {r['total']})\n{txt_comissao}", inline=True)
            
            if pago_agora:
                embed.add_field(name="💵 Pagamento", value=f"**R$ {total_comissao:.2f}** creditados.", inline=False)
            
            await ctx.send(embed=embed)
        
        if erros:
            await ctx.send(f"⚠️ Erro ao adicionar: {', '.join(erros)}")

    # ============================================
    # ESTOQUE - VER
    # ============================================

    # ============================================
    # ESTOQUE - VER
    # ============================================

    @commands.command(name='estoque', aliases=['2', 'veranimais', 'meuestoque'])
    @empresa_configurada()
    async def ver_estoque(self, ctx, membro: discord.Member = None):
        """Mostra estoque do funcionário."""
        empresa = await selecionar_empresa(ctx)
        if not empresa: return
        target = membro or ctx.author
        
        func = await get_funcionario_by_discord_id(str(target.id))
        if not func:
            await ctx.send(f"❌ {target.display_name} não está cadastrado.")
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
            for item in estoque:
                qtd = item['quantidade']
                valor_unit = Decimal(str(item['preco_funcionario']))
                valor_total = valor_unit * qtd
                total_valor += valor_total
                
                embed.add_field(
                    name=f"{item['nome']}",
                    value=f"Qtd: **{qtd}**\nValor Ref: R$ {valor_total:.2f}",
                    inline=True
                )
            
            if modo_pagamento == 'producao':
                 embed.add_field(name="💰 Valor Acumulado", value=f"**R$ {total_valor:.2f}** (Aguardando !pagarestoque)", inline=False)
            else:
                 # modo == 'entrega' (ou qualquer outro fallback, trata como entrega/potencial)
                 embed.add_field(name="💰 Valor Potencial", value=f"**R$ {total_valor:.2f}** (Recebe ao entregar)", inline=False)
        
        await ctx.send(embed=embed)

    # ... (deletar e estoqueglobal nao mudam, apenas manter placeholder se necessario, mas como replace é chunk, ok)

    # ============================================
    # ENCOMENDAS - ENTREGAR
    # ============================================

    # (Função entregar_encomenda removida pois estava duplicada. A versão correta está mais abaixo)

    # ============================================
    # ESTOQUE - DELETAR
    # ============================================

    @commands.command(name='deletar', aliases=['3', 'remover'])
    @empresa_configurada()
    async def deletar_produto(self, ctx, *, entrada: str):
        """Remove produtos do estoque. Uso: !deletar codigo5"""
        empresa = await selecionar_empresa(ctx)
        if not empresa:
            return
        
        func = await get_funcionario_by_discord_id(str(ctx.author.id))
        if not func:
            await ctx.send("❌ Você não está cadastrado.")
            return
        
        matches = PRODUTO_REGEX.findall(entrada)
        
        if not matches:
            await ctx.send("❌ Formato: `!deletar codigo5`")
            return
        
        resultados = []
        erros = []
        
        for codigo, qtd_str in matches:
            quantidade = int(qtd_str)
            
            resultado = await remover_do_estoque(func['id'], empresa['id'], codigo, quantidade)
            
            if resultado:
                if 'erro' in resultado:
                    erros.append(resultado['erro'])
                else:
                    resultados.append({
                        'nome': resultado['nome'],
                        'removido': resultado['removido'],
                        'restante': resultado['quantidade']
                    })
            else:
                erros.append(f"Erro ao remover {codigo}")
        
        if resultados:
            embed = discord.Embed(title="🗑️ Produtos Removidos", color=discord.Color.orange())
            for r in resultados:
                embed.add_field(name=r['nome'], value=f"-{r['removido']} → Restante: **{r['restante']}**", inline=True)
            await ctx.send(embed=embed)
        
        if erros:
            await ctx.send("⚠️ Erros:\n" + "\n".join(f"• {e}" for e in erros))

    # ============================================
    # ESTOQUE GLOBAL
    # ============================================

    @commands.command(name='estoqueglobal', aliases=['verestoque', 'producao'])
    @empresa_configurada()
    async def ver_estoque_global(self, ctx):
        """Mostra estoque global da empresa."""
        empresa = await selecionar_empresa(ctx)
        if not empresa:
            return
        estoque = await get_estoque_global(empresa['id'])
        
        embed = discord.Embed(
            title=f"🏢 Estoque Global - {empresa['nome']}",
            color=discord.Color.gold()
        )
        
        if not estoque:
            embed.description = "📭 Nenhum produto em estoque."
        else:
            for item in estoque[:25]:
                embed.add_field(
                    name=item['nome'],
                    value=f"**{item['quantidade']}** unidades",
                    inline=True
                )
        
        embed.set_footer(text=f"Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        await ctx.send(embed=embed)

    # ============================================
    # VER PRODUTOS
    # ============================================

    @commands.command(name='produtos', aliases=['catalogo', 'tabela', 'codigos'])
    @empresa_configurada()
    async def ver_produtos(self, ctx):
        """Lista todos os produtos configurados com seus códigos."""
        empresa = await selecionar_empresa(ctx)
        if not empresa:
            return
        produtos = await get_produtos_empresa(empresa['id'])
        
        if not produtos:
            embed = discord.Embed(
                title="❌ Nenhum Produto Configurado",
                description="A empresa ainda não tem produtos configurados.",
                color=discord.Color.red()
            )
            embed.add_field(
                name="🔧 Como configurar?",
                value="Um **administrador** deve usar um dos comandos:\n"
                      "• `!configmedio` - Configura preços médios\n"
                      "• `!configmin` - Configura preços mínimos\n"
                      "• `!configmax` - Configura preços máximos",
                inline=False
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title=f"📦 Catálogo de Produtos - {empresa['nome']}",
            description=f"**{len(produtos)}** produtos disponíveis\n"
                        f"Use o **código** para adicionar ao estoque ou encomendas",
            color=discord.Color.blue()
        )
        
        categorias = {}
        for codigo, p in produtos.items():
            cat = p['produtos_referencia'].get('categoria', 'Outros')
            if cat not in categorias:
                categorias[cat] = []
            categorias[cat].append((codigo, p))
        
        for cat, prods in list(categorias.items())[:6]:
            linhas = []
            for codigo, p in prods[:6]:
                nome = p['produtos_referencia']['nome'][:18]
                preco = p['preco_venda']
                linhas.append(f"`{codigo}` {nome} R${preco:.2f}")
            
            if len(prods) > 6:
                linhas.append(f"*+{len(prods) - 6} mais...*")
            
            embed.add_field(name=f"� {cat} ({len(prods)})", value="\n".join(linhas), inline=True)
        
        embed.add_field(
            name="💡 Exemplos de Uso",
            value="• `!add rotulo10` - Adiciona 10 ao estoque\n"
                  "• `!novaencomenda` - Criar encomenda interativa\n"
                  "• `!verprecos` - Ver tabela de preços",
            inline=False
        )
        
        embed.set_footer(text="Dica: Os códigos são case-insensitive (maiúsculo ou minúsculo)")
        await ctx.send(embed=embed)

    # ============================================
    # ENCOMENDAS - NOVA (MENU INTERATIVO)
    # ============================================

    @commands.command(name='novaencomenda', aliases=['4', 'addencomenda', 'encomenda'])
    @empresa_configurada()
    async def nova_encomenda(self, ctx, *, entrada: str = None):
        """Cria uma nova encomenda. Uso: !novaencomenda ou !novaencomenda "Cliente" produto10"""
        empresa = await selecionar_empresa(ctx)
        if not empresa:
            return
        
        # Verifica se funcionário está cadastrado
        func = await get_funcionario_by_discord_id(str(ctx.author.id))
        if not func:
            embed = discord.Embed(
                title="❌ Você não está cadastrado",
                description="Para usar os comandos de produção e encomendas, você precisa ser cadastrado como funcionário.",
                color=discord.Color.red()
            )
            embed.add_field(
                name="📋 Como se cadastrar?",
                value="Peça a um **administrador** da empresa para usar:\n"
                      "`!bemvindo @você`\n\n"
                      "Isso criará seu canal privado e liberará seu acesso.",
                inline=False
            )
            embed.set_footer(text="Apenas administradores podem cadastrar funcionários")
            await ctx.send(embed=embed)
            return
        
        produtos = await get_produtos_empresa(empresa['id'])
        if not produtos:
            await ctx.send("❌ Nenhum produto configurado. Peça a um admin para usar `!configmedio`.")
            return
        
        # Se passou argumentos, usa o modo rápido
        if entrada:
            # Tenta extrair comprador e itens
            import re
            match_comprador = re.match(r'^["\'](.+?)["\'](.*)$', entrada.strip())
            if match_comprador:
                comprador = match_comprador.group(1)
                itens_str = match_comprador.group(2).strip()
            else:
                # Primeira palavra é o comprador
                parts = entrada.split(maxsplit=1)
                comprador = parts[0]
                itens_str = parts[1] if len(parts) > 1 else ""
            
            if itens_str:
                matches = PRODUTO_REGEX.findall(itens_str)
                if matches:
                    await self._criar_encomenda_rapida(ctx, empresa, func, comprador, matches, produtos)
                    return
        
        # Modo interativo
        await self._criar_encomenda_interativa(ctx, empresa, func, produtos)

    async def _criar_encomenda_interativa(self, ctx, empresa, func, produtos):
        """Menu interativo para criar encomenda."""
        
        # ===== PASSO 1: Nome do cliente =====
        embed = discord.Embed(
            title="📦 Nova Encomenda",
            description="**Passo 1/3:** Digite o **nome do cliente**:",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Digite 'cancelar' para sair")
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            if msg.content.lower() == 'cancelar':
                await ctx.send("❌ Encomenda cancelada.")
                return
            comprador = msg.content.strip()
        except:
            await ctx.send("❌ Tempo esgotado.")
            return
        
        # ===== PASSO 2: Adicionar produtos =====
        itens = []
        valor_total = Decimal('0')
        
        while True:
            # Mostra menu de categorias
            categorias = {}
            for codigo, p in produtos.items():
                cat = p['produtos_referencia'].get('categoria', 'Outros')
                if cat not in categorias:
                    categorias[cat] = []
                categorias[cat].append((codigo, p))
            
            embed = discord.Embed(
                title=f"📦 Encomenda para: {comprador}",
                description="**Passo 2/3:** Adicione produtos ao carrinho",
                color=discord.Color.gold()
            )
            
            # Mostra itens já adicionados
            if itens:
                itens_text = "\n".join([f"• **{i['nome']}** x{i['quantidade']} = R${i['valor']:.2f}" for i in itens])
                embed.add_field(name="🛒 Carrinho", value=itens_text, inline=False)
                embed.add_field(name="💰 Subtotal", value=f"**R$ {valor_total:.2f}**", inline=False)
            
            # Mostra produtos disponíveis com formato melhorado
            for cat, prods in list(categorias.items())[:4]:
                # Formata cada produto com nome e código
                prods_lines = []
                for codigo, p in prods[:5]:
                    nome = p['produtos_referencia']['nome'][:20]
                    preco = p['preco_venda']
                    prods_lines.append(f"`{codigo}` {nome} • R${preco:.2f}")
                
                if len(prods) > 5:
                    prods_lines.append(f"*+{len(prods)-5} mais...*")
                
                embed.add_field(
                    name=f"📁 {cat} ({len(prods)})",
                    value="\n".join(prods_lines),
                    inline=True
                )
            
            embed.add_field(
                name="💡 Como adicionar?",
                value="Digite o **código** e a **quantidade**\n"
                      "Exemplo: `camera_fotografica 5`\n"
                      "Ou apenas o código para 1 unidade: `rotulo`",
                inline=False
            )
            
            embed.set_footer(text="✅ pronto = confirmar | ❌ cancelar = sair | 🧹 limpar = esvaziar carrinho")
            await ctx.send(embed=embed)
            
            try:
                msg = await self.bot.wait_for('message', timeout=120.0, check=check)
                texto = msg.content.strip().lower()
                
                if texto == 'cancelar':
                    await ctx.send("❌ Encomenda cancelada.")
                    return
                
                if texto == 'limpar':
                    itens = []
                    valor_total = Decimal('0')
                    await ctx.send("🧹 Carrinho limpo!")
                    continue
                
                if texto == 'pronto':
                    if not itens:
                        await ctx.send("⚠️ Adicione pelo menos um produto antes de finalizar!")
                        continue
                    break
                
                # Tenta parsear entrada como "codigo quantidade"
                parts = texto.split()
                if len(parts) >= 1:
                    codigo = parts[0].lower()
                    quantidade = int(parts[1]) if len(parts) > 1 else 1
                    
                    if codigo not in produtos:
                        await ctx.send(f"❌ Código `{codigo}` não encontrado.\n💡 **Dica:** Use `!produtos` para ver todos os códigos disponíveis.")
                        continue
                    
                    if quantidade <= 0:
                        await ctx.send("❌ Quantidade deve ser maior que zero.")
                        continue
                    
                    prod = produtos[codigo]
                    valor = Decimal(str(prod['preco_venda'])) * quantidade
                    
                    # Verifica se já existe no carrinho
                    existente = next((i for i in itens if i['codigo'] == codigo), None)
                    if existente:
                        existente['quantidade'] += quantidade
                        existente['valor'] = Decimal(str(prod['preco_venda'])) * existente['quantidade']
                        valor_total = sum(Decimal(str(i['valor'])) for i in itens)
                        await ctx.send(f"✅ Adicionado mais **{quantidade}x {prod['produtos_referencia']['nome']}** (total: {existente['quantidade']})")
                    else:
                        itens.append({
                            'codigo': codigo,
                            'nome': prod['produtos_referencia']['nome'],
                            'quantidade': quantidade,
                            'valor_unitario': float(prod['preco_venda']),
                            'valor': float(valor)
                        })
                        valor_total += valor
                        await ctx.send(f"✅ **{quantidade}x {prod['produtos_referencia']['nome']}** adicionado!")
                else:
                    await ctx.send("❌ Formato: `codigo quantidade` (ex: `pa 10`)")
                    
            except ValueError:
                await ctx.send("❌ Quantidade inválida. Use números.")
            except:
                await ctx.send("❌ Tempo esgotado.")
                return
        
        # ===== PASSO 3: Confirmação =====
        embed = discord.Embed(
            title="📋 Confirmar Encomenda",
            description=f"**Cliente:** {comprador}",
            color=discord.Color.green()
        )
        
        for item in itens:
            embed.add_field(
                name=f"{item['nome']}",
                value=f"Qtd: **{item['quantidade']}**\nValor: R$ {item['valor']:.2f}",
                inline=True
            )
        
        embed.add_field(name="━━━━━━━━━━━━━━━━", value="​", inline=False)
        embed.add_field(name="💰 TOTAL", value=f"**R$ {valor_total:.2f}**", inline=False)
        embed.set_footer(text="Digite 'sim' para confirmar ou 'não' para cancelar")
        
        await ctx.send(embed=embed)
        
        try:
            msg = await self.bot.wait_for('message', timeout=30.0, check=check)
            if msg.content.lower() not in ['sim', 's', 'yes', 'y']:
                await ctx.send("❌ Encomenda cancelada.")
                return
        except:
            await ctx.send("❌ Tempo esgotado.")
            return
        
        # ===== Criar encomenda no banco =====
        itens_json = [{
            'codigo': i['codigo'],
            'nome': i['nome'],
            'quantidade': i['quantidade'],
            'quantidade_entregue': 0,
            'valor_unitario': i['valor_unitario']
        } for i in itens]
        
        response = supabase.table('encomendas').insert({
            'comprador': comprador,
            'itens_json': itens_json,
            'valor_total': float(valor_total),
            'status': 'pendente',
            'funcionario_responsavel_id': func['id'],
            'empresa_id': empresa['id']
        }).execute()
        
        encomenda_id = response.data[0]['id']
        
        # Embed de sucesso
        embed = discord.Embed(
            title="✅ Encomenda Criada com Sucesso!",
            description=f"**ID:** `#{encomenda_id}`\n**Cliente:** {comprador}",
            color=discord.Color.green()
        )
        
        itens_resumo = "\n".join([f"• {i['quantidade']}x {i['nome']}" for i in itens])
        embed.add_field(name="📦 Itens", value=itens_resumo, inline=False)
        embed.add_field(name="💰 Total", value=f"**R$ {valor_total:.2f}**", inline=True)
        embed.add_field(name="📋 Status", value="🟡 Pendente", inline=True)
        embed.add_field(
            name="💡 Próximos passos",
            value=f"• `!encomendas` - Ver todas pendentes\n• `!entregar {encomenda_id}` - Entregar esta encomenda",
            inline=False
        )
        embed.set_footer(text=f"Criada por {ctx.author.display_name}")
        
        await ctx.send(embed=embed)

    async def _criar_encomenda_rapida(self, ctx, empresa, func, comprador, matches, produtos):
        """Cria encomenda no modo rápido (com argumentos)."""
        itens_json = []
        valor_total = Decimal('0')
        
        for codigo, qtd_str in matches:
            codigo_lower = codigo.lower()
            quantidade = int(qtd_str)
            
            if codigo_lower not in produtos:
                await ctx.send(f"❌ Produto `{codigo}` não configurado.")
                return
            
            prod = produtos[codigo_lower]
            valor = Decimal(str(prod['preco_venda'])) * quantidade
            valor_total += valor
            
            itens_json.append({
                'codigo': codigo_lower,
                'nome': prod['produtos_referencia']['nome'],
                'quantidade': quantidade,
                'quantidade_entregue': 0,
                'valor_unitario': float(prod['preco_venda'])
            })
        
        response = supabase.table('encomendas').insert({
            'comprador': comprador,
            'itens_json': itens_json,
            'valor_total': float(valor_total),
            'status': 'pendente',
            'funcionario_responsavel_id': func['id'],
            'empresa_id': empresa['id']
        }).execute()
        
        encomenda_id = response.data[0]['id']
        
        embed = discord.Embed(
            title="✅ Encomenda Criada!",
            description=f"**ID:** `#{encomenda_id}`\n**Cliente:** {comprador}",
            color=discord.Color.green()
        )
        
        for item in itens_json:
            embed.add_field(name=item['nome'], value=f"Qtd: **{item['quantidade']}**", inline=True)
        
        embed.add_field(name="💰 Total", value=f"**R$ {valor_total:.2f}**", inline=False)
        embed.set_footer(text=f"Use !entregar {encomenda_id} para entregar")
        await ctx.send(embed=embed)

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
            embed.set_footer(text="💡 Use !novaencomenda para criar | !entregar [ID] para entregar")
        
        await ctx.send(embed=embed)

    # ============================================
    # ENCOMENDAS - ENTREGAR
    # ============================================

    @commands.command(name='entregar', aliases=['entregarencomenda'])
    @empresa_configurada()
    async def entregar_encomenda(self, ctx, encomenda_id: int):
        """Entrega encomenda completa."""
        empresa = await selecionar_empresa(ctx)
        if not empresa:
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
