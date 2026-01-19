"""
Bot Multi-Empresa Downtown - Sistema de Gerenciamento Econômico para Roleplay (RDR2)
Desenvolvido para Discord com integração Supabase
Suporta múltiplos tipos de empresas do Downtown
"""

import os
import re
import asyncio
from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Dict, Any

import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from supabase import create_client, Client

# Carrega variáveis de ambiente
load_dotenv()

# Configurações
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not all([DISCORD_TOKEN, SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("Variáveis de ambiente faltando.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Regex para parsing de produtos (ex: pa2, va10, gp5)
PRODUTO_REGEX = re.compile(r'([a-zA-Z_]+)(\d+)')

# Cache de empresas por guild
empresas_cache: Dict[str, Dict] = {}


# ============================================
# FUNÇÕES DE EMPRESA
# ============================================

async def get_tipos_empresa() -> List[Dict]:
    """Obtém todos os tipos de empresa disponíveis."""
    try:
        response = supabase.table('tipos_empresa').select('*').eq('ativo', True).order('nome').execute()
        return response.data
    except Exception as e:
        print(f"Erro ao buscar tipos de empresa: {e}")
        return []


async def get_empresa_by_guild(guild_id: str) -> Optional[Dict]:
    """Obtém a empresa configurada para um servidor Discord."""
    if guild_id in empresas_cache:
        return empresas_cache[guild_id]
    
    try:
        response = supabase.table('empresas').select(
            '*, tipos_empresa(*)'
        ).eq('guild_id', guild_id).eq('ativo', True).execute()
        
        if response.data:
            empresas_cache[guild_id] = response.data[0]
            return response.data[0]
        return None
    except Exception as e:
        print(f"Erro ao buscar empresa: {e}")
        return None


async def criar_empresa(guild_id: str, nome: str, tipo_empresa_id: int, proprietario_id: str) -> Optional[Dict]:
    """Cria uma nova empresa para o servidor."""
    try:
        response = supabase.table('empresas').insert({
            'guild_id': guild_id,
            'nome': nome,
            'tipo_empresa_id': tipo_empresa_id,
            'proprietario_discord_id': proprietario_id
        }).execute()
        
        if response.data:
            empresas_cache[guild_id] = response.data[0]
            return response.data[0]
        return None
    except Exception as e:
        print(f"Erro ao criar empresa: {e}")
        return None


async def get_produtos_referencia(tipo_empresa_id: int) -> List[Dict]:
    """Obtém produtos de referência para um tipo de empresa."""
    try:
        response = supabase.table('produtos_referencia').select('*').eq(
            'tipo_empresa_id', tipo_empresa_id
        ).eq('ativo', True).order('categoria', desc=False).order('nome').execute()
        return response.data
    except Exception as e:
        print(f"Erro ao buscar produtos: {e}")
        return []


async def get_produtos_empresa(empresa_id: int) -> Dict[str, Dict]:
    """Obtém produtos configurados para a empresa."""
    try:
        response = supabase.table('produtos_empresa').select(
            '*, produtos_referencia(*)'
        ).eq('empresa_id', empresa_id).eq('ativo', True).execute()
        
        return {p['produtos_referencia']['codigo']: p for p in response.data}
    except Exception as e:
        print(f"Erro ao buscar produtos da empresa: {e}")
        return {}


async def configurar_produto_empresa(empresa_id: int, produto_ref_id: int, preco_venda: float, preco_funcionario: float) -> bool:
    """Configura um produto para a empresa."""
    try:
        existing = supabase.table('produtos_empresa').select('id').eq(
            'empresa_id', empresa_id
        ).eq('produto_referencia_id', produto_ref_id).execute()
        
        if existing.data:
            supabase.table('produtos_empresa').update({
                'preco_venda': preco_venda,
                'preco_pagamento_funcionario': preco_funcionario,
                'ativo': True
            }).eq('id', existing.data[0]['id']).execute()
        else:
            supabase.table('produtos_empresa').insert({
                'empresa_id': empresa_id,
                'produto_referencia_id': produto_ref_id,
                'preco_venda': preco_venda,
                'preco_pagamento_funcionario': preco_funcionario
            }).execute()
        return True
    except Exception as e:
        print(f"Erro ao configurar produto: {e}")
        return False


# ============================================
# FUNÇÕES DE FUNCIONÁRIO
# ============================================

async def get_or_create_funcionario(discord_id: str, nome: str, empresa_id: int = None) -> Optional[int]:
    """Obtém ou cria um funcionário."""
    try:
        response = supabase.table('funcionarios').select('id, empresa_id').eq('discord_id', discord_id).execute()
        
        if response.data:
            func_id = response.data[0]['id']
            if empresa_id and response.data[0].get('empresa_id') != empresa_id:
                supabase.table('funcionarios').update({'empresa_id': empresa_id}).eq('id', func_id).execute()
            return func_id
        
        response = supabase.table('funcionarios').insert({
            'discord_id': discord_id,
            'nome': nome,
            'empresa_id': empresa_id
        }).execute()
        
        return response.data[0]['id'] if response.data else None
    except Exception as e:
        print(f"Erro ao obter/criar funcionário: {e}")
        return None


async def get_funcionario_by_discord_id(discord_id: str) -> Optional[Dict]:
    """Obtém dados do funcionário."""
    try:
        response = supabase.table('funcionarios').select('*').eq('discord_id', discord_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Erro ao buscar funcionário: {e}")
        return None


# ============================================
# FUNÇÕES DE ESTOQUE
# ============================================

async def adicionar_ao_estoque(funcionario_id: int, empresa_id: int, codigo: str, quantidade: int) -> Optional[Dict]:
    """Adiciona produtos ao estoque do funcionário."""
    try:
        produtos = await get_produtos_empresa(empresa_id)
        if codigo.lower() not in produtos:
            return None
        
        produto = produtos[codigo.lower()]
        
        estoque = supabase.table('estoque_produtos').select('*').eq(
            'funcionario_id', funcionario_id
        ).eq('produto_codigo', codigo.lower()).eq('empresa_id', empresa_id).execute()
        
        if estoque.data:
            nova_qtd = estoque.data[0]['quantidade'] + quantidade
            supabase.table('estoque_produtos').update({
                'quantidade': nova_qtd,
                'data_atualizacao': datetime.utcnow().isoformat()
            }).eq('id', estoque.data[0]['id']).execute()
            return {'quantidade': nova_qtd, 'nome': produto['produtos_referencia']['nome']}
        else:
            supabase.table('estoque_produtos').insert({
                'funcionario_id': funcionario_id,
                'empresa_id': empresa_id,
                'produto_codigo': codigo.lower(),
                'quantidade': quantidade
            }).execute()
            return {'quantidade': quantidade, 'nome': produto['produtos_referencia']['nome']}
    except Exception as e:
        print(f"Erro ao adicionar estoque: {e}")
        return None


async def remover_do_estoque(funcionario_id: int, empresa_id: int, codigo: str, quantidade: int) -> Optional[Dict]:
    """Remove produtos do estoque."""
    try:
        produtos = await get_produtos_empresa(empresa_id)
        if codigo.lower() not in produtos:
            return {'erro': 'Produto não encontrado'}
        
        produto = produtos[codigo.lower()]
        
        estoque = supabase.table('estoque_produtos').select('*').eq(
            'funcionario_id', funcionario_id
        ).eq('produto_codigo', codigo.lower()).eq('empresa_id', empresa_id).execute()
        
        if not estoque.data:
            return {'erro': 'Produto não encontrado no estoque'}
        
        atual = estoque.data[0]['quantidade']
        nome = produto['produtos_referencia']['nome']
        
        if quantidade > atual:
            return {'erro': f'Quantidade insuficiente. Você tem {atual} {nome}'}
        
        nova_qtd = atual - quantidade
        
        if nova_qtd == 0:
            supabase.table('estoque_produtos').delete().eq('id', estoque.data[0]['id']).execute()
        else:
            supabase.table('estoque_produtos').update({
                'quantidade': nova_qtd,
                'data_atualizacao': datetime.utcnow().isoformat()
            }).eq('id', estoque.data[0]['id']).execute()
        
        return {'quantidade': nova_qtd, 'nome': nome, 'removido': quantidade}
    except Exception as e:
        print(f"Erro ao remover estoque: {e}")
        return None


async def get_estoque_funcionario(funcionario_id: int, empresa_id: int) -> List[Dict]:
    """Obtém estoque do funcionário."""
    try:
        produtos = await get_produtos_empresa(empresa_id)
        
        response = supabase.table('estoque_produtos').select('*').eq(
            'funcionario_id', funcionario_id
        ).eq('empresa_id', empresa_id).gt('quantidade', 0).execute()
        
        result = []
        for item in response.data:
            codigo = item['produto_codigo']
            if codigo in produtos:
                prod = produtos[codigo]
                result.append({
                    **item,
                    'nome': prod['produtos_referencia']['nome'],
                    'preco_venda': prod['preco_venda'],
                    'preco_funcionario': prod['preco_pagamento_funcionario']
                })
        return result
    except Exception as e:
        print(f"Erro ao buscar estoque: {e}")
        return []


async def get_estoque_global(empresa_id: int) -> List[Dict]:
    """Obtém estoque global da empresa."""
    try:
        produtos = await get_produtos_empresa(empresa_id)
        
        response = supabase.table('estoque_produtos').select('*').eq(
            'empresa_id', empresa_id
        ).gt('quantidade', 0).execute()
        
        totais = {}
        for item in response.data:
            codigo = item['produto_codigo']
            if codigo not in totais:
                nome = produtos.get(codigo, {}).get('produtos_referencia', {}).get('nome', codigo)
                totais[codigo] = {'codigo': codigo, 'nome': nome, 'quantidade': 0}
            totais[codigo]['quantidade'] += item['quantidade']
        
        return list(totais.values())
    except Exception as e:
        print(f"Erro ao buscar estoque global: {e}")
        return []


# ============================================
# EVENTOS DO BOT
# ============================================

@bot.event
async def on_ready():
    """Bot está pronto."""
    print('============================================')
    print('  Bot Multi-Empresa Downtown conectado!')
    print(f'  Usuario: {bot.user.name}')
    print(f'  Servidores: {len(bot.guilds)}')
    print('============================================')
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Downtown | !help"
        )
    )


@bot.event
async def on_guild_join(guild):
    """Quando bot entra em novo servidor."""
    canal = guild.system_channel or guild.text_channels[0]
    
    embed = discord.Embed(
        title="🏢 Bot Multi-Empresa Downtown",
        description="Olá! Sou um bot de gerenciamento econômico para roleplay.\n\n"
                    "**Para começar**, um administrador deve configurar o tipo de empresa:\n"
                    "`!configurar`",
        color=discord.Color.blue()
    )
    await canal.send(embed=embed)


@bot.event
async def on_command_error(ctx, error):
    """Tratamento de erros."""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Argumento faltando: `{error.param.name}`")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Você não tem permissão.")
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        print(f"Erro: {error}")
        await ctx.send("❌ Ocorreu um erro.")


# ============================================
# DECORATOR - VERIFICAR EMPRESA CONFIGURADA
# ============================================

def empresa_configurada():
    """Decorator que verifica se a empresa está configurada."""
    async def predicate(ctx):
        empresa = await get_empresa_by_guild(str(ctx.guild.id))
        if not empresa:
            await ctx.send("❌ Empresa não configurada. Use `!configurar` primeiro.")
            return False
        ctx.empresa = empresa
        return True
    return commands.check(predicate)


# ============================================
# COMANDOS - CONFIGURAÇÃO
# ============================================

@bot.command(name='configurar', aliases=['setup'])
@commands.has_permissions(administrator=True)
async def configurar_empresa(ctx):
    """Configura a empresa para este servidor."""
    # Verifica se já existe
    empresa = await get_empresa_by_guild(str(ctx.guild.id))
    if empresa:
        await ctx.send(f"✅ Já existe uma empresa configurada: **{empresa['nome']}** ({empresa['tipos_empresa']['nome']})")
        return
    
    # Lista tipos disponíveis
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
        msg = await bot.wait_for('message', timeout=60.0, check=check)
        
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
        
        # Pede nome da empresa
        await ctx.send(f"✅ Tipo selecionado: **{tipo_escolhido['nome']}**\n\nAgora digite o **nome da sua empresa**:")
        
        msg = await bot.wait_for('message', timeout=60.0, check=check)
        nome_empresa = msg.content.strip()
        
        if len(nome_empresa) < 3:
            await ctx.send("❌ Nome muito curto.")
            return
        
        # Cria empresa
        empresa = await criar_empresa(
            str(ctx.guild.id),
            nome_empresa,
            tipo_escolhido['id'],
            str(ctx.author.id)
        )
        
        if not empresa:
            await ctx.send("❌ Erro ao criar empresa.")
            return
        
        # Busca empresa com dados do tipo
        empresa = await get_empresa_by_guild(str(ctx.guild.id))
        
        embed = discord.Embed(
            title="✅ Empresa Criada!",
            description=f"**{nome_empresa}**",
            color=discord.Color.green()
        )
        embed.add_field(name="Tipo", value=f"{tipo_escolhido['icone']} {tipo_escolhido['nome']}")
        embed.add_field(name="Proprietário", value=ctx.author.mention)
        embed.add_field(
            name="Próximo Passo",
            value="Use `!configurarprecos` para definir os preços dos produtos.",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except asyncio.TimeoutError:
        await ctx.send("❌ Tempo esgotado.")


@bot.command(name='configurarprecos', aliases=['precos', 'setprecos'])
@commands.has_permissions(administrator=True)
@empresa_configurada()
async def configurar_precos(ctx):
    """Configura os preços dos produtos."""
    empresa = ctx.empresa
    
    # Busca produtos de referência
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
        value="Use `!configurarauto` para configurar todos os produtos com preço médio automaticamente.",
        inline=False
    )
    
    await ctx.send(embed=embed)
    
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    
    try:
        msg = await bot.wait_for('message', timeout=60.0, check=check)
        
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
        
        # Mostra produtos da categoria
        embed = discord.Embed(
            title=f"📦 {cat_escolhida}",
            description="Para configurar, digite: `codigo preco_venda preco_funcionario`\nExemplo: `ensopado_carne 1.40 0.35`\n\nDigite `pronto` quando terminar.",
            color=discord.Color.blue()
        )
        
        for p in produtos_cat[:25]:  # Limite do embed
            embed.add_field(
                name=f"`{p['codigo']}`",
                value=f"{p['nome']}\nRef: ${p['preco_minimo']:.2f} - ${p['preco_maximo']:.2f}",
                inline=True
            )
        
        await ctx.send(embed=embed)
        
        configurados = 0
        
        while True:
            msg = await bot.wait_for('message', timeout=120.0, check=check)
            
            if msg.content.lower() == 'pronto':
                break
            
            parts = msg.content.split()
            if len(parts) != 3:
                await ctx.send("❌ Formato: `codigo preco_venda preco_funcionario`")
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


@bot.command(name='configurarauto', aliases=['autoconfig'])
@commands.has_permissions(administrator=True)
@empresa_configurada()
async def configurar_auto(ctx):
    """Configura todos os produtos automaticamente com preço médio."""
    empresa = ctx.empresa
    produtos_ref = await get_produtos_referencia(empresa['tipo_empresa_id'])
    
    if not produtos_ref:
        await ctx.send("❌ Nenhum produto disponível.")
        return
    
    await ctx.send(f"⏳ Configurando {len(produtos_ref)} produtos automaticamente...")
    
    configurados = 0
    for p in produtos_ref:
        preco_venda = (float(p['preco_minimo']) + float(p['preco_maximo'])) / 2
        preco_func = preco_venda * 0.25  # 25% do preço de venda para funcionário
        
        if await configurar_produto_empresa(empresa['id'], p['id'], preco_venda, preco_func):
            configurados += 1
    
    await ctx.send(f"✅ {configurados}/{len(produtos_ref)} produtos configurados com preço médio!")


# ============================================
# COMANDOS - GESTÃO DE SERVIDOR
# ============================================

@bot.command(name='bemvindo')
@commands.has_permissions(manage_channels=True)
@empresa_configurada()
async def bemvindo(ctx, membro: discord.Member):
    """Cria canal privado para funcionário."""
    empresa = ctx.empresa
    guild = ctx.guild
    
    nome_canal = f"func-{membro.display_name.lower().replace(' ', '-')}"
    
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        membro: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    
    canal = await guild.create_text_channel(name=nome_canal, overwrites=overwrites)
    
    func_id = await get_or_create_funcionario(str(membro.id), membro.display_name, empresa['id'])
    
    embed = discord.Embed(
        title=f"🏢 Bem-vindo à {empresa['nome']}!",
        description=f"Olá {membro.mention}! Este é seu canal privado.",
        color=discord.Color.green()
    )
    embed.add_field(
        name="📋 Comandos",
        value="`!add [codigo][qtd]` - Adicionar produtos\n`!estoque` - Ver seu estoque\n`!produtos` - Ver produtos disponíveis",
        inline=False
    )
    
    await canal.send(embed=embed)
    await ctx.send(f"✅ Canal {canal.mention} criado para {membro.mention}!")


# ============================================
# COMANDOS - SISTEMA DE PRODUÇÃO
# ============================================

@bot.command(name='add', aliases=['1'])
@empresa_configurada()
async def add_produto(ctx, *, entrada: str):
    """Adiciona produtos ao estoque. Uso: !add codigo10 codigo25"""
    empresa = ctx.empresa
    
    func_id = await get_or_create_funcionario(str(ctx.author.id), ctx.author.display_name, empresa['id'])
    if not func_id:
        await ctx.send("❌ Erro ao identificar funcionário.")
        return
    
    matches = PRODUTO_REGEX.findall(entrada)
    
    if not matches:
        await ctx.send("❌ Formato: `!add codigo10 codigo25`")
        return
    
    produtos = await get_produtos_empresa(empresa['id'])
    resultados = []
    erros = []
    
    for codigo, qtd_str in matches:
        codigo_lower = codigo.lower()
        quantidade = int(qtd_str)
        
        if quantidade <= 0:
            erros.append(f"Quantidade inválida: {codigo}")
            continue
        
        if codigo_lower not in produtos:
            erros.append(f"Produto `{codigo}` não configurado")
            continue
        
        resultado = await adicionar_ao_estoque(func_id, empresa['id'], codigo_lower, quantidade)
        
        if resultado:
            resultados.append({
                'codigo': codigo_lower.upper(),
                'nome': resultado['nome'],
                'adicionado': quantidade,
                'total': resultado['quantidade']
            })
        else:
            erros.append(f"Erro ao adicionar {codigo}")
    
    if resultados:
        embed = discord.Embed(title="✅ Produtos Adicionados!", color=discord.Color.green())
        for r in resultados:
            embed.add_field(
                name=f"{r['nome']}",
                value=f"+{r['adicionado']} → Total: **{r['total']}**",
                inline=True
            )
        embed.set_footer(text=f"Funcionário: {ctx.author.display_name}")
        await ctx.send(embed=embed)
    
    if erros:
        await ctx.send("⚠️ Avisos:\n" + "\n".join(f"• {e}" for e in erros))


@bot.command(name='estoque', aliases=['2', 'veranimais', 'meuestoque'])
@empresa_configurada()
async def ver_estoque(ctx, membro: discord.Member = None):
    """Mostra estoque do funcionário."""
    empresa = ctx.empresa
    target = membro or ctx.author
    
    func = await get_funcionario_by_discord_id(str(target.id))
    if not func:
        await ctx.send(f"❌ {target.display_name} não está cadastrado.")
        return
    
    estoque = await get_estoque_funcionario(func['id'], empresa['id'])
    
    embed = discord.Embed(
        title=f"📦 Estoque de {target.display_name}",
        color=discord.Color.blue()
    )
    
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
                value=f"Qtd: **{qtd}**\nValor: R$ {valor_total:.2f}",
                inline=True
            )
        
        embed.add_field(name="💰 Total a Receber", value=f"**R$ {total_valor:.2f}**", inline=False)
    
    embed.set_footer(text=f"Saldo: R$ {func['saldo']:.2f}")
    await ctx.send(embed=embed)


@bot.command(name='deletar', aliases=['3', 'remover'])
@empresa_configurada()
async def deletar_produto(ctx, *, entrada: str):
    """Remove produtos do estoque. Uso: !deletar codigo5"""
    empresa = ctx.empresa
    
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


@bot.command(name='estoqueglobal', aliases=['verestoque', 'producao'])
@empresa_configurada()
async def ver_estoque_global(ctx):
    """Mostra estoque global da empresa."""
    empresa = ctx.empresa
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


@bot.command(name='produtos', aliases=['catalogo', 'tabela'])
@empresa_configurada()
async def ver_produtos(ctx):
    """Lista todos os produtos configurados."""
    empresa = ctx.empresa
    produtos = await get_produtos_empresa(empresa['id'])
    
    if not produtos:
        await ctx.send("❌ Nenhum produto configurado. Use `!configurarauto`.")
        return
    
    embed = discord.Embed(
        title=f"📦 Produtos - {empresa['nome']}",
        color=discord.Color.blue()
    )
    
    # Agrupa por categoria
    categorias = {}
    for codigo, p in produtos.items():
        cat = p['produtos_referencia'].get('categoria', 'Outros')
        if cat not in categorias:
            categorias[cat] = []
        categorias[cat].append((codigo, p))
    
    for cat, prods in list(categorias.items())[:5]:  # Limita categorias no embed
        valor = "\n".join(
            f"`{c}` {p['produtos_referencia']['nome']}: R${p['preco_venda']:.2f}"
            for c, p in prods[:5]
        )
        embed.add_field(name=f"📋 {cat}", value=valor, inline=False)
    
    embed.set_footer(text=f"Total: {len(produtos)} produtos configurados")
    await ctx.send(embed=embed)


# ============================================
# COMANDOS - SISTEMA DE ENCOMENDAS
# ============================================

@bot.command(name='novaencomenda', aliases=['4', 'addencomenda'])
@empresa_configurada()
async def nova_encomenda(ctx, comprador: str, *, itens: str):
    """Cria encomenda. Uso: !novaencomenda "Cliente" produto10 produto5"""
    empresa = ctx.empresa
    
    func = await get_funcionario_by_discord_id(str(ctx.author.id))
    if not func:
        await ctx.send("❌ Você não está cadastrado.")
        return
    
    matches = PRODUTO_REGEX.findall(itens)
    if not matches:
        await ctx.send("❌ Formato: `!novaencomenda \"Cliente\" produto10 produto5`")
        return
    
    produtos = await get_produtos_empresa(empresa['id'])
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
        title="📦 Encomenda Criada!",
        description=f"**ID:** #{encomenda_id}\n**Cliente:** {comprador}",
        color=discord.Color.green()
    )
    
    for item in itens_json:
        embed.add_field(name=item['nome'], value=f"Qtd: {item['quantidade']}", inline=True)
    
    embed.add_field(name="💰 Total", value=f"R$ {valor_total:.2f}", inline=False)
    await ctx.send(embed=embed)


@bot.command(name='encomendas', aliases=['5', 'pendentes'])
@empresa_configurada()
async def ver_encomendas(ctx):
    """Lista encomendas pendentes."""
    empresa = ctx.empresa
    
    response = supabase.table('encomendas').select(
        '*, funcionarios(nome)'
    ).eq('empresa_id', empresa['id']).in_(
        'status', ['pendente', 'em_andamento']
    ).order('data_criacao').execute()
    
    encomendas = response.data
    
    embed = discord.Embed(title="📋 Encomendas Pendentes", color=discord.Color.blue())
    
    if not encomendas:
        embed.description = "✅ Nenhuma encomenda pendente!"
    else:
        for enc in encomendas[:10]:
            itens_str = ", ".join(f"{i['quantidade']}x {i['codigo']}" for i in enc['itens_json'])
            resp = enc.get('funcionarios', {})
            responsavel = resp.get('nome', 'N/A') if resp else 'N/A'
            status_emoji = "🟡" if enc['status'] == 'pendente' else "🔵"
            
            embed.add_field(
                name=f"{status_emoji} #{enc['id']} - {enc['comprador']}",
                value=f"**Itens:** {itens_str}\n**Valor:** R$ {enc['valor_total']:.2f}\n**Resp:** {responsavel}",
                inline=False
            )
    
    embed.set_footer(text=f"Total: {len(encomendas)} pendentes")
    await ctx.send(embed=embed)


@bot.command(name='entregar', aliases=['entregarencomenda'])
@empresa_configurada()
async def entregar_encomenda(ctx, encomenda_id: int):
    """Entrega encomenda completa."""
    empresa = ctx.empresa
    
    func = await get_funcionario_by_discord_id(str(ctx.author.id))
    if not func:
        await ctx.send("❌ Você não está cadastrado.")
        return
    
    response = supabase.table('encomendas').select('*').eq('id', encomenda_id).eq('empresa_id', empresa['id']).execute()
    
    if not response.data:
        await ctx.send(f"❌ Encomenda #{encomenda_id} não encontrada.")
        return
    
    encomenda = response.data[0]
    
    if encomenda['status'] == 'entregue':
        await ctx.send("❌ Encomenda já entregue.")
        return
    
    # Verifica estoque
    estoque = await get_estoque_funcionario(func['id'], empresa['id'])
    estoque_dict = {e['produto_codigo']: e['quantidade'] for e in estoque}
    
    faltando = []
    for item in encomenda['itens_json']:
        precisa = item['quantidade'] - item.get('quantidade_entregue', 0)
        tem = estoque_dict.get(item['codigo'], 0)
        if tem < precisa:
            faltando.append(f"{item['nome']}: precisa {precisa}, tem {tem}")
    
    if faltando:
        embed = discord.Embed(title="❌ Estoque Insuficiente", description="\n".join(faltando), color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    # Deduz e marca entregue
    for item in encomenda['itens_json']:
        precisa = item['quantidade'] - item.get('quantidade_entregue', 0)
        await remover_do_estoque(func['id'], empresa['id'], item['codigo'], precisa)
    
    supabase.table('encomendas').update({
        'status': 'entregue',
        'data_entrega': datetime.utcnow().isoformat()
    }).eq('id', encomenda_id).execute()
    
    embed = discord.Embed(
        title="✅ Encomenda Entregue!",
        description=f"#{encomenda_id} para **{encomenda['comprador']}**",
        color=discord.Color.green()
    )
    embed.add_field(name="💰 Valor", value=f"R$ {encomenda['valor_total']:.2f}")
    await ctx.send(embed=embed)


# ============================================
# COMANDOS - FINANCEIRO
# ============================================

@bot.command(name='pagar', aliases=['pagamento'])
@commands.has_permissions(manage_messages=True)
@empresa_configurada()
async def pagar_funcionario(ctx, membro: discord.Member, valor: float, *, descricao: str = "Pagamento"):
    """Registra pagamento. Uso: !pagar @pessoa 100 Descrição"""
    empresa = ctx.empresa
    
    func = await get_funcionario_by_discord_id(str(membro.id))
    if not func:
        await ctx.send(f"❌ {membro.display_name} não cadastrado.")
        return
    
    if valor <= 0:
        await ctx.send("❌ Valor deve ser positivo.")
        return
    
    supabase.table('historico_pagamentos').insert({
        'funcionario_id': func['id'],
        'tipo': 'manual',
        'valor': valor,
        'descricao': descricao
    }).execute()
    
    supabase.table('funcionarios').update({
        'saldo': float(Decimal(str(func['saldo'])) + Decimal(str(valor)))
    }).eq('id', func['id']).execute()
    
    embed = discord.Embed(title="💵 Pagamento Registrado!", color=discord.Color.green())
    embed.add_field(name="Funcionário", value=membro.mention)
    embed.add_field(name="Valor", value=f"R$ {valor:.2f}")
    embed.add_field(name="Descrição", value=descricao, inline=False)
    await ctx.send(embed=embed)


@bot.command(name='pagarestoque', aliases=['pe'])
@commands.has_permissions(manage_messages=True)
@empresa_configurada()
async def pagar_estoque(ctx, membro: discord.Member):
    """Paga e zera estoque do funcionário."""
    empresa = ctx.empresa
    
    func = await get_funcionario_by_discord_id(str(membro.id))
    if not func:
        await ctx.send(f"❌ {membro.display_name} não cadastrado.")
        return
    
    estoque = await get_estoque_funcionario(func['id'], empresa['id'])
    
    if not estoque:
        await ctx.send(f"❌ {membro.display_name} não tem estoque.")
        return
    
    total = Decimal('0')
    for item in estoque:
        total += Decimal(str(item['preco_funcionario'])) * item['quantidade']
    
    embed = discord.Embed(
        title=f"💰 Pagamento - {membro.display_name}",
        description="Confirme com `sim`",
        color=discord.Color.gold()
    )
    
    for item in estoque:
        v = Decimal(str(item['preco_funcionario'])) * item['quantidade']
        embed.add_field(name=item['nome'], value=f"{item['quantidade']}x = R$ {v:.2f}", inline=True)
    
    embed.add_field(name="💵 TOTAL", value=f"**R$ {total:.2f}**", inline=False)
    await ctx.send(embed=embed)
    
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == 'sim'
    
    try:
        await bot.wait_for('message', timeout=30.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send("❌ Cancelado.")
        return
    
    supabase.table('historico_pagamentos').insert({
        'funcionario_id': func['id'],
        'tipo': 'estoque',
        'valor': float(total),
        'descricao': f'Pagamento automático - {len(estoque)} tipos de produtos'
    }).execute()
    
    supabase.table('funcionarios').update({
        'saldo': float(Decimal(str(func['saldo'])) + total)
    }).eq('id', func['id']).execute()
    
    supabase.table('estoque_produtos').delete().eq('funcionario_id', func['id']).eq('empresa_id', empresa['id']).execute()
    
    await ctx.send(f"✅ {membro.mention} recebeu **R$ {total:.2f}**! Estoque zerado.")


@bot.command(name='caixa', aliases=['financeiro'])
@commands.has_permissions(manage_messages=True)
@empresa_configurada()
async def verificar_caixa(ctx):
    """Relatório financeiro."""
    empresa = ctx.empresa
    
    funcionarios = supabase.table('funcionarios').select('*').eq('empresa_id', empresa['id']).eq('ativo', True).execute()
    
    total_saldos = Decimal('0')
    total_estoque = Decimal('0')
    detalhes = []
    
    for func in funcionarios.data:
        saldo = Decimal(str(func['saldo']))
        total_saldos += saldo
        
        estoque = await get_estoque_funcionario(func['id'], empresa['id'])
        valor_estoque = sum(Decimal(str(i['preco_funcionario'])) * i['quantidade'] for i in estoque)
        total_estoque += valor_estoque
        
        if saldo > 0 or valor_estoque > 0:
            detalhes.append({'nome': func['nome'], 'saldo': saldo, 'estoque': valor_estoque})
    
    embed = discord.Embed(title=f"📊 Financeiro - {empresa['nome']}", color=discord.Color.gold())
    
    for d in sorted(detalhes, key=lambda x: x['saldo'] + x['estoque'], reverse=True)[:10]:
        embed.add_field(name=d['nome'], value=f"Saldo: R$ {d['saldo']:.2f}\nEstoque: R$ {d['estoque']:.2f}", inline=True)
    
    embed.add_field(name="💰 Total Saldos", value=f"**R$ {total_saldos:.2f}**", inline=False)
    embed.add_field(name="📦 Total Estoque", value=f"**R$ {total_estoque:.2f}**", inline=False)
    embed.add_field(name="📈 TOTAL", value=f"**R$ {total_saldos + total_estoque:.2f}**", inline=False)
    
    await ctx.send(embed=embed)


# ============================================
# COMANDO DE AJUDA
# ============================================

@bot.command(name='help', aliases=['ajuda', 'comandos'])
async def ajuda(ctx):
    """Mostra todos os comandos."""
    empresa = await get_empresa_by_guild(str(ctx.guild.id))
    
    embed = discord.Embed(
        title="🏢 Bot Multi-Empresa Downtown",
        description=f"**Empresa:** {empresa['nome'] if empresa else 'Não configurada'}",
        color=discord.Color.green()
    )
    
    if not empresa:
        embed.add_field(
            name="⚙️ Configuração",
            value="`!configurar` - Configurar empresa (Admin)",
            inline=False
        )
    else:
        embed.add_field(
            name="⚙️ Configuração (Admin)",
            value="`!configurar` - Ver empresa\n`!configurarauto` - Config. produtos automático\n`!configurarprecos` - Config. preços manual",
            inline=False
        )
        
        embed.add_field(
            name="📋 Gestão",
            value="`!bemvindo @pessoa` - Criar canal funcionário",
            inline=False
        )
        
        embed.add_field(
            name="📦 Produção",
            value="`!add [codigo][qtd]` ou `!1` - Adicionar\n`!estoque` ou `!2` - Ver estoque\n`!deletar [codigo][qtd]` ou `!3` - Remover\n`!estoqueglobal` - Estoque total\n`!produtos` - Ver catálogo",
            inline=False
        )
        
        embed.add_field(
            name="📦 Encomendas",
            value='`!novaencomenda "Cliente" [itens]` ou `!4`\n`!encomendas` ou `!5` - Ver pendentes\n`!entregar [ID]` - Entregar',
            inline=False
        )
        
        embed.add_field(
            name="💰 Financeiro (Admin)",
            value="`!pagar @pessoa [valor]` - Pagamento\n`!pagarestoque @pessoa` - Pagar estoque\n`!caixa` - Relatório",
            inline=False
        )
    
    await ctx.send(embed=embed)


@bot.command(name='empresa', aliases=['info'])
async def info_empresa(ctx):
    """Mostra informações da empresa."""
    empresa = await get_empresa_by_guild(str(ctx.guild.id))
    
    if not empresa:
        await ctx.send("❌ Empresa não configurada. Use `!configurar`.")
        return
    
    produtos = await get_produtos_empresa(empresa['id'])
    funcionarios = supabase.table('funcionarios').select('id').eq('empresa_id', empresa['id']).execute()
    
    embed = discord.Embed(
        title=f"{empresa['tipos_empresa']['icone']} {empresa['nome']}",
        description=f"**Tipo:** {empresa['tipos_empresa']['nome']}",
        color=discord.Color.from_str(empresa['tipos_empresa'].get('cor_hex', '#10b981'))
    )
    
    embed.add_field(name="📦 Produtos", value=f"{len(produtos)} configurados")
    embed.add_field(name="👷 Funcionários", value=f"{len(funcionarios.data)} cadastrados")
    embed.add_field(name="📅 Criada em", value=empresa['data_criacao'][:10])
    
    await ctx.send(embed=embed)


@bot.command(name='limpar')
@commands.has_permissions(manage_messages=True)
async def limpar(ctx, quantidade: int = 10):
    """Limpa mensagens do canal."""
    if quantidade < 1 or quantidade > 100:
        await ctx.send("❌ Quantidade: 1-100")
        return
    
    deleted = await ctx.channel.purge(limit=quantidade + 1)
    msg = await ctx.send(f"🧹 {len(deleted) - 1} mensagens apagadas!")
    await asyncio.sleep(3)
    await msg.delete()


# ============================================
# INICIALIZAÇÃO
# ============================================

if __name__ == '__main__':
    print("Iniciando Bot Multi-Empresa Downtown...")
    bot.run(DISCORD_TOKEN)
