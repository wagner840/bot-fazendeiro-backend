"""
Bot Multi-Empresa Downtown - Sistema de Gerenciamento Econômico para Roleplay (RDR2)
Desenvolvido para Discord com integração Supabase
Suporta múltiplos tipos de empresas do Downtown
Versão 2.0 - Sistema de Canais Privados por Funcionário
"""

import os
import re
import asyncio
from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Dict, Any

import discord
from discord.ext import commands
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

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

PRODUTO_REGEX = re.compile(r'([a-zA-Z_]+)(\d+)')

empresas_cache: Dict[str, Dict] = {}
funcionarios_cache: Dict[str, Dict] = {}  # channel_id -> funcionario


# ============================================
# FUNÇÕES DE EMPRESA
# ============================================

async def get_tipos_empresa() -> List[Dict]:
    try:
        response = supabase.table('tipos_empresa').select('*').eq('ativo', True).order('nome').execute()
        return response.data
    except Exception as e:
        print(f"Erro tipos_empresa: {e}")
        return []


async def get_empresa_by_guild(guild_id: str) -> Optional[Dict]:
    if guild_id in empresas_cache:
        return empresas_cache[guild_id]
    try:
        response = supabase.table('empresas').select('*, tipos_empresa(*)').eq('guild_id', guild_id).eq('ativo', True).execute()
        if response.data:
            empresas_cache[guild_id] = response.data[0]
            return response.data[0]
        return None
    except Exception as e:
        print(f"Erro get_empresa: {e}")
        return None


async def criar_empresa(guild_id: str, nome: str, tipo_empresa_id: int, proprietario_id: str) -> Optional[Dict]:
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
        print(f"Erro criar_empresa: {e}")
        return None


async def get_produtos_referencia(tipo_empresa_id: int) -> List[Dict]:
    try:
        response = supabase.table('produtos_referencia').select('*').eq('tipo_empresa_id', tipo_empresa_id).eq('ativo', True).order('categoria').order('nome').execute()
        return response.data
    except Exception as e:
        print(f"Erro produtos_referencia: {e}")
        return []


async def get_produtos_empresa(empresa_id: int) -> Dict[str, Dict]:
    try:
        response = supabase.table('produtos_empresa').select('*, produtos_referencia(*)').eq('empresa_id', empresa_id).eq('ativo', True).execute()
        return {p['produtos_referencia']['codigo']: p for p in response.data}
    except Exception as e:
        print(f"Erro produtos_empresa: {e}")
        return {}


async def configurar_produto_empresa(empresa_id: int, produto_ref_id: int, preco_venda: float, preco_funcionario: float) -> bool:
    try:
        existing = supabase.table('produtos_empresa').select('id').eq('empresa_id', empresa_id).eq('produto_referencia_id', produto_ref_id).execute()
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
        print(f"Erro configurar_produto: {e}")
        return False


# ============================================
# FUNÇÕES DE FUNCIONÁRIO
# ============================================

async def get_funcionario_by_channel(channel_id: str) -> Optional[Dict]:
    if channel_id in funcionarios_cache:
        return funcionarios_cache[channel_id]
    try:
        response = supabase.table('funcionarios').select('*, empresas(*, tipos_empresa(*))').eq('channel_id', channel_id).eq('ativo', True).execute()
        if response.data:
            funcionarios_cache[channel_id] = response.data[0]
            return response.data[0]
        return None
    except Exception as e:
        print(f"Erro get_funcionario_by_channel: {e}")
        return None


async def get_funcionario_by_discord_id(discord_id: str, empresa_id: int = None) -> Optional[Dict]:
    try:
        query = supabase.table('funcionarios').select('*').eq('discord_id', discord_id)
        if empresa_id:
            query = query.eq('empresa_id', empresa_id)
        response = query.execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Erro get_funcionario: {e}")
        return None


async def criar_funcionario(discord_id: str, nome: str, empresa_id: int, channel_id: str) -> Optional[Dict]:
    try:
        response = supabase.table('funcionarios').insert({
            'discord_id': discord_id,
            'nome': nome,
            'empresa_id': empresa_id,
            'channel_id': channel_id
        }).execute()
        if response.data:
            funcionarios_cache[channel_id] = response.data[0]
            return response.data[0]
        return None
    except Exception as e:
        print(f"Erro criar_funcionario: {e}")
        return None


# ============================================
# FUNÇÕES DE ESTOQUE
# ============================================

async def adicionar_ao_estoque(funcionario_id: int, empresa_id: int, codigo: str, quantidade: int) -> Optional[Dict]:
    try:
        produtos = await get_produtos_empresa(empresa_id)
        if codigo.lower() not in produtos:
            return {'erro': f'Produto `{codigo}` não configurado'}
        
        produto = produtos[codigo.lower()]
        
        estoque = supabase.table('estoque_produtos').select('*').eq('funcionario_id', funcionario_id).eq('produto_codigo', codigo.lower()).eq('empresa_id', empresa_id).execute()
        
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
        print(f"Erro adicionar_estoque: {e}")
        return None


async def remover_do_estoque(funcionario_id: int, empresa_id: int, codigo: str, quantidade: int) -> Optional[Dict]:
    try:
        produtos = await get_produtos_empresa(empresa_id)
        if codigo.lower() not in produtos:
            return {'erro': 'Produto não encontrado'}
        
        produto = produtos[codigo.lower()]
        
        estoque = supabase.table('estoque_produtos').select('*').eq('funcionario_id', funcionario_id).eq('produto_codigo', codigo.lower()).eq('empresa_id', empresa_id).execute()
        
        if not estoque.data:
            return {'erro': 'Você não tem este produto no estoque'}
        
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
        print(f"Erro remover_estoque: {e}")
        return None


async def get_estoque_funcionario(funcionario_id: int, empresa_id: int) -> List[Dict]:
    try:
        produtos = await get_produtos_empresa(empresa_id)
        response = supabase.table('estoque_produtos').select('*').eq('funcionario_id', funcionario_id).eq('empresa_id', empresa_id).gt('quantidade', 0).execute()
        
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
        print(f"Erro get_estoque: {e}")
        return []


async def get_estoque_global(empresa_id: int) -> List[Dict]:
    try:
        produtos = await get_produtos_empresa(empresa_id)
        response = supabase.table('estoque_produtos').select('*').eq('empresa_id', empresa_id).gt('quantidade', 0).execute()
        
        totais = {}
        for item in response.data:
            codigo = item['produto_codigo']
            if codigo not in totais:
                nome = produtos.get(codigo, {}).get('produtos_referencia', {}).get('nome', codigo)
                totais[codigo] = {'codigo': codigo, 'nome': nome, 'quantidade': 0}
            totais[codigo]['quantidade'] += item['quantidade']
        
        return list(totais.values())
    except Exception as e:
        print(f"Erro estoque_global: {e}")
        return []


# ============================================
# EVENTOS DO BOT
# ============================================

@bot.event
async def on_ready():
    print('============================================')
    print('  Bot Multi-Empresa Downtown v2.0')
    print(f'  Usuario: {bot.user.name}')
    print(f'  Servidores: {len(bot.guilds)}')
    print('============================================')
    
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Downtown | !help"))


@bot.event
async def on_guild_join(guild):
    canal = guild.system_channel or guild.text_channels[0]
    embed = discord.Embed(
        title="🏢 Bot Multi-Empresa Downtown",
        description="Olá! Sou um bot de gerenciamento econômico.\n\n**Para começar:** `!configurar`",
        color=discord.Color.blue()
    )
    await canal.send(embed=embed)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Argumento faltando: `{error.param.name}`")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Você não tem permissão.")
    elif isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.CheckFailure):
        pass
    else:
        print(f"Erro: {error}")


# ============================================
# DECORATORS
# ============================================

def empresa_configurada():
    async def predicate(ctx):
        empresa = await get_empresa_by_guild(str(ctx.guild.id))
        if not empresa:
            await ctx.send("❌ Empresa não configurada. Use `!configurar` primeiro.")
            return False
        ctx.empresa = empresa
        return True
    return commands.check(predicate)


def canal_funcionario():
    """Verifica se o comando está sendo usado no canal do funcionário."""
    async def predicate(ctx):
        func = await get_funcionario_by_channel(str(ctx.channel.id))
        if not func:
            await ctx.send("❌ Use este comando no seu canal privado de funcionário.")
            return False
        ctx.funcionario = func
        ctx.empresa = func['empresas']
        return True
    return commands.check(predicate)


# ============================================
# COMANDOS - CONFIGURAÇÃO (ADMIN)
# ============================================

@bot.command(name='configurar', aliases=['setup'])
@commands.has_permissions(administrator=True)
async def configurar_empresa(ctx):
    """Configura a empresa para este servidor."""
    empresa = await get_empresa_by_guild(str(ctx.guild.id))
    if empresa:
        await ctx.send(f"✅ Empresa já configurada: **{empresa['nome']}** ({empresa['tipos_empresa']['nome']})")
        return
    
    tipos = await get_tipos_empresa()
    
    embed = discord.Embed(title="🏢 Configuração de Empresa", description="Escolha o tipo digitando o **número**:", color=discord.Color.blue())
    
    tipos_text = ""
    for i, tipo in enumerate(tipos, 1):
        tipos_text += f"`{i}.` {tipo['icone']} **{tipo['nome']}**\n"
    
    embed.add_field(name="Tipos Disponíveis", value=tipos_text, inline=False)
    await ctx.send(embed=embed)
    
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    
    try:
        msg = await bot.wait_for('message', timeout=60.0, check=check)
        
        if msg.content.lower() == 'cancelar':
            await ctx.send("❌ Cancelado.")
            return
        
        escolha = int(msg.content) - 1
        if escolha < 0 or escolha >= len(tipos):
            await ctx.send("❌ Número inválido.")
            return
        
        tipo_escolhido = tipos[escolha]
        
        await ctx.send(f"✅ Tipo: **{tipo_escolhido['nome']}**\n\nDigite o **nome da sua empresa**:")
        
        msg = await bot.wait_for('message', timeout=60.0, check=check)
        nome_empresa = msg.content.strip()
        
        if len(nome_empresa) < 3:
            await ctx.send("❌ Nome muito curto.")
            return
        
        empresa = await criar_empresa(str(ctx.guild.id), nome_empresa, tipo_escolhido['id'], str(ctx.author.id))
        
        if not empresa:
            await ctx.send("❌ Erro ao criar empresa.")
            return
        
        # Limpa cache para recarregar com tipos_empresa
        empresas_cache.pop(str(ctx.guild.id), None)
        empresa = await get_empresa_by_guild(str(ctx.guild.id))
        
        embed = discord.Embed(title="✅ Empresa Criada!", description=f"**{nome_empresa}**", color=discord.Color.green())
        embed.add_field(name="Tipo", value=f"{tipo_escolhido['icone']} {tipo_escolhido['nome']}")
        embed.add_field(name="Próximo Passo", value="Use `!configurarauto` para configurar os produtos.", inline=False)
        
        await ctx.send(embed=embed)
        
    except asyncio.TimeoutError:
        await ctx.send("❌ Tempo esgotado.")
    except ValueError:
        await ctx.send("❌ Digite apenas o número.")


@bot.command(name='configurarauto', aliases=['autoconfig'])
@commands.has_permissions(administrator=True)
@empresa_configurada()
async def configurar_auto(ctx):
    """Configura todos os produtos automaticamente com preço médio."""
    empresa = ctx.empresa
    produtos_ref = await get_produtos_referencia(empresa['tipo_empresa_id'])
    
    if not produtos_ref:
        await ctx.send("❌ Nenhum produto disponível para este tipo.")
        return
    
    await ctx.send(f"⏳ Configurando {len(produtos_ref)} produtos...")
    
    configurados = 0
    for p in produtos_ref:
        preco_venda = (float(p['preco_minimo']) + float(p['preco_maximo'])) / 2
        preco_func = preco_venda * 0.25
        
        if await configurar_produto_empresa(empresa['id'], p['id'], preco_venda, preco_func):
            configurados += 1
    
    await ctx.send(f"✅ {configurados}/{len(produtos_ref)} produtos configurados!")


@bot.command(name='configurarprecos', aliases=['configprecos'])
@commands.has_permissions(administrator=True)
@empresa_configurada()
async def configurar_precos_manual(ctx):
    """Configurar preços por categoria manualmente."""
    empresa = ctx.empresa
    produtos_ref = await get_produtos_referencia(empresa['tipo_empresa_id'])
    
    if not produtos_ref:
        await ctx.send("❌ Nenhum produto disponível.")
        return
    
    # Agrupa por categoria
    categorias = {}
    for p in produtos_ref:
        cat = p.get('categoria', 'Outros')
        if cat not in categorias:
            categorias[cat] = []
        categorias[cat].append(p)
    
    embed = discord.Embed(
        title="⚙️ Configurar Preços por Categoria",
        description="Digite o número da categoria para configurar:",
        color=discord.Color.blue()
    )
    
    cat_list = list(categorias.keys())
    for i, cat in enumerate(cat_list, 1):
        quantidade = len(categorias[cat])
        embed.add_field(name=f"`{i}.` {cat}", value=f"{quantidade} produtos", inline=True)
    
    embed.add_field(name="Opções", value="`0` - Sair | `todos` - Configurar todas", inline=False)
    await ctx.send(embed=embed)
    
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    
    try:
        msg = await bot.wait_for('message', timeout=60.0, check=check)
        
        if msg.content == '0':
            await ctx.send("❌ Cancelado.")
            return
        
        if msg.content.lower() == 'todos':
            # Configura todas as categorias com preço médio
            total = 0
            for cat_produtos in categorias.values():
                for p in cat_produtos:
                    preco_venda = (float(p['preco_minimo']) + float(p['preco_maximo'])) / 2
                    preco_func = preco_venda * 0.25
                    if await configurar_produto_empresa(empresa['id'], p['id'], preco_venda, preco_func):
                        total += 1
            await ctx.send(f"✅ {total} produtos configurados com preço médio!")
            return
        
        idx = int(msg.content) - 1
        if idx < 0 or idx >= len(cat_list):
            await ctx.send("❌ Número inválido.")
            return
        
        cat_escolhida = cat_list[idx]
        produtos_cat = categorias[cat_escolhida]
        
        # Mostra produtos da categoria
        embed = discord.Embed(
            title=f"📦 {cat_escolhida}",
            description="Escolha como configurar: `medio` (preço médio) ou `minimo` ou `maximo`",
            color=discord.Color.green()
        )
        
        for p in produtos_cat[:15]:
            embed.add_field(
                name=f"`{p['codigo']}`",
                value=f"{p['nome']}\nMin: ${p['preco_minimo']:.2f} | Max: ${p['preco_maximo']:.2f}",
                inline=True
            )
        
        if len(produtos_cat) > 15:
            embed.set_footer(text=f"... e mais {len(produtos_cat) - 15} produtos")
        
        await ctx.send(embed=embed)
        
        msg = await bot.wait_for('message', timeout=60.0, check=check)
        modo = msg.content.lower()
        
        configurados = 0
        for p in produtos_cat:
            if modo == 'minimo':
                preco_venda = float(p['preco_minimo'])
            elif modo == 'maximo':
                preco_venda = float(p['preco_maximo'])
            else:  # medio
                preco_venda = (float(p['preco_minimo']) + float(p['preco_maximo'])) / 2
            
            preco_func = preco_venda * 0.25
            if await configurar_produto_empresa(empresa['id'], p['id'], preco_venda, preco_func):
                configurados += 1
        
        await ctx.send(f"✅ {configurados} produtos de **{cat_escolhida}** configurados!")
        
    except asyncio.TimeoutError:
        await ctx.send("❌ Tempo esgotado.")
    except ValueError:
        await ctx.send("❌ Digite apenas o número.")


@bot.command(name='verprecos', aliases=['precos', 'listaprecos'])
@empresa_configurada()
async def ver_precos(ctx, *, categoria: str = None):
    """Ver preços dos produtos. Uso: !verprecos [categoria]"""
    empresa = ctx.empresa
    produtos = await get_produtos_empresa(empresa['id'])
    
    if not produtos:
        await ctx.send("❌ Nenhum produto configurado. Admin use `!configurarauto`.")
        return
    
    # Agrupa por categoria
    categorias = {}
    for codigo, p in produtos.items():
        cat = p['produtos_referencia'].get('categoria', 'Outros')
        if cat not in categorias:
            categorias[cat] = []
        categorias[cat].append((codigo, p))
    
    if categoria:
        # Busca categoria específica
        cat_encontrada = None
        for cat in categorias.keys():
            if categoria.lower() in cat.lower():
                cat_encontrada = cat
                break
        
        if not cat_encontrada:
            await ctx.send(f"❌ Categoria `{categoria}` não encontrada.")
            return
        
        embed = discord.Embed(title=f"💰 Preços - {cat_encontrada}", color=discord.Color.gold())
        
        for codigo, p in categorias[cat_encontrada][:25]:
            nome = p['produtos_referencia']['nome']
            venda = p['preco_venda']
            func = p['preco_pagamento_funcionario']
            embed.add_field(
                name=f"`{codigo}`",
                value=f"**{nome}**\n💵 ${venda:.2f} | 👷 ${func:.2f}",
                inline=True
            )
        
        await ctx.send(embed=embed)
    else:
        # Lista categorias disponíveis
        embed = discord.Embed(
            title="📦 Categorias de Produtos",
            description="Use `!verprecos [categoria]` para ver detalhes",
            color=discord.Color.blue()
        )
        
        for cat, prods in categorias.items():
            embed.add_field(name=cat, value=f"{len(prods)} produtos", inline=True)
        
        embed.set_footer(text=f"Total: {len(produtos)} produtos configurados")
        await ctx.send(embed=embed)


@bot.command(name='alterarpreco', aliases=['editarpreco', 'mudarpreco'])
@commands.has_permissions(administrator=True)
@empresa_configurada()
async def alterar_preco(ctx, codigo: str, preco_venda: float, preco_funcionario: float = None):
    """Alterar preço de um produto. Uso: !alterarpreco codigo 0.50 0.12"""
    empresa = ctx.empresa
    produtos = await get_produtos_empresa(empresa['id'])
    
    codigo_lower = codigo.lower()
    if codigo_lower not in produtos:
        await ctx.send(f"❌ Produto `{codigo}` não encontrado.")
        return
    
    produto = produtos[codigo_lower]
    
    if preco_funcionario is None:
        preco_funcionario = preco_venda * 0.25
    
    # Atualiza no banco
    try:
        supabase.table('produtos_empresa').update({
            'preco_venda': preco_venda,
            'preco_pagamento_funcionario': preco_funcionario
        }).eq('id', produto['id']).execute()
        
        embed = discord.Embed(title="✅ Preço Atualizado!", color=discord.Color.green())
        embed.add_field(name="Produto", value=f"`{codigo}` - {produto['produtos_referencia']['nome']}")
        embed.add_field(name="Preço Venda", value=f"${preco_venda:.2f}")
        embed.add_field(name="Pagamento Funcionário", value=f"${preco_funcionario:.2f}")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Erro ao atualizar: {e}")


@bot.command(name='infoproduto', aliases=['produto', 'verproduto'])
@empresa_configurada()
async def info_produto(ctx, codigo: str):
    """Ver informações detalhadas de um produto. Uso: !infoproduto codigo"""
    empresa = ctx.empresa
    produtos = await get_produtos_empresa(empresa['id'])
    
    codigo_lower = codigo.lower()
    if codigo_lower not in produtos:
        await ctx.send(f"❌ Produto `{codigo}` não encontrado.")
        return
    
    p = produtos[codigo_lower]
    ref = p['produtos_referencia']
    
    embed = discord.Embed(
        title=f"📦 {ref['nome']}",
        description=f"Código: `{ref['codigo']}`",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="📁 Categoria", value=ref.get('categoria', 'Outros'))
    embed.add_field(name="📏 Unidade", value=ref.get('unidade', 'un'))
    embed.add_field(name="━" * 10, value="**Preços Referência (Downtown)**", inline=False)
    embed.add_field(name="💵 Mínimo", value=f"${ref['preco_minimo']:.2f}")
    embed.add_field(name="💵 Máximo", value=f"${ref['preco_maximo']:.2f}")
    embed.add_field(name="━" * 10, value="**Preços Configurados**", inline=False)
    embed.add_field(name="💰 Venda", value=f"${p['preco_venda']:.2f}")
    embed.add_field(name="👷 Funcionário", value=f"${p['preco_pagamento_funcionario']:.2f}")
    embed.set_footer(text=f"Use: !add {codigo}[quantidade]")
    
    await ctx.send(embed=embed)


@bot.command(name='buscarproduto', aliases=['buscar', 'pesquisar'])
@empresa_configurada()
async def buscar_produto(ctx, *, termo: str):
    """Buscar produtos por nome ou código. Uso: !buscar milho"""
    empresa = ctx.empresa
    produtos = await get_produtos_empresa(empresa['id'])
    
    if not produtos:
        await ctx.send("❌ Nenhum produto configurado.")
        return
    
    termo_lower = termo.lower()
    encontrados = []
    
    for codigo, p in produtos.items():
        nome = p['produtos_referencia']['nome'].lower()
        if termo_lower in codigo or termo_lower in nome:
            encontrados.append((codigo, p))
    
    if not encontrados:
        await ctx.send(f"❌ Nenhum produto encontrado com `{termo}`.")
        return
    
    embed = discord.Embed(
        title=f"🔍 Resultados para '{termo}'",
        description=f"{len(encontrados)} produtos encontrados",
        color=discord.Color.blue()
    )
    
    for codigo, p in encontrados[:20]:
        nome = p['produtos_referencia']['nome']
        venda = p['preco_venda']
        embed.add_field(
            name=f"`{codigo}`",
            value=f"{nome}\n${venda:.2f}",
            inline=True
        )
    
    if len(encontrados) > 20:
        embed.set_footer(text=f"... e mais {len(encontrados) - 20} resultados")
    
    await ctx.send(embed=embed)


# ============================================
# COMANDOS - FUNCIONÁRIOS (ADMIN)
# ============================================

@bot.command(name='bemvindo')
@commands.has_permissions(manage_channels=True)
@empresa_configurada()
async def bemvindo(ctx, membro: discord.Member):
    """Cria canal privado para funcionário."""
    empresa = ctx.empresa
    guild = ctx.guild
    
    # Verifica se já existe
    func_existente = await get_funcionario_by_discord_id(str(membro.id), empresa['id'])
    if func_existente and func_existente.get('channel_id'):
        canal_existente = guild.get_channel(int(func_existente['channel_id']))
        if canal_existente:
            await ctx.send(f"❌ {membro.mention} já tem o canal {canal_existente.mention}")
            return
    
    # Busca ou cria categoria
    categoria = discord.utils.get(guild.categories, name="Funcionários")
    if not categoria:
        categoria = await guild.create_category("Funcionários")
    
    # Cria canal privado
    nome_canal = f"func-{membro.display_name.lower().replace(' ', '-')[:20]}"
    
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        membro: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    
    canal = await guild.create_text_channel(name=nome_canal, category=categoria, overwrites=overwrites)
    
    # Cadastra funcionário
    func = await criar_funcionario(str(membro.id), membro.display_name, empresa['id'], str(canal.id))
    
    if not func:
        await canal.delete()
        await ctx.send("❌ Erro ao cadastrar funcionário.")
        return
    
    # Mensagem de boas vindas no canal
    embed = discord.Embed(
        title=f"🏢 Bem-vindo à {empresa['nome']}!",
        description=f"Olá {membro.mention}!\n\nEste é seu canal privado de trabalho.",
        color=discord.Color.green()
    )
    embed.add_field(
        name="📦 Produção",
        value="`!add [codigo][qtd]` - Adicionar produtos\n`!estoque` - Ver seu estoque\n`!deletar [codigo][qtd]` - Remover",
        inline=False
    )
    embed.add_field(
        name="📋 Encomendas",
        value='`!novaencomenda "Cliente" [itens]` - Nova\n`!encomendas` - Ver pendentes\n`!entregar [ID]` - Entregar',
        inline=False
    )
    embed.add_field(
        name="💰 Financeiro",
        value="`!meusaldo` - Ver saldo\n`!produtos` - Ver catálogo",
        inline=False
    )
    embed.set_footer(text=f"ID do Funcionário: {func['id']}")
    
    await canal.send(embed=embed)
    await ctx.send(f"✅ Canal {canal.mention} criado para {membro.mention}!")


# ============================================
# COMANDOS - PRODUÇÃO (NO CANAL DO FUNCIONÁRIO)
# ============================================

@bot.command(name='add', aliases=['1', 'adicionar'])
@canal_funcionario()
async def add_produto(ctx, *, entrada: str):
    """Adiciona produtos ao estoque."""
    func = ctx.funcionario
    empresa = ctx.empresa
    
    matches = PRODUTO_REGEX.findall(entrada)
    
    if not matches:
        await ctx.send("❌ Formato: `!add codigo10 codigo25`\nUse `!produtos` para ver códigos.")
        return
    
    resultados = []
    erros = []
    
    for codigo, qtd_str in matches:
        resultado = await adicionar_ao_estoque(func['id'], empresa['id'], codigo.lower(), int(qtd_str))
        
        if resultado:
            if 'erro' in resultado:
                erros.append(resultado['erro'])
            else:
                resultados.append({
                    'nome': resultado['nome'],
                    'adicionado': int(qtd_str),
                    'total': resultado['quantidade']
                })
        else:
            erros.append(f"Erro ao adicionar {codigo}")
    
    if resultados:
        embed = discord.Embed(title="✅ Produtos Adicionados!", color=discord.Color.green())
        for r in resultados:
            embed.add_field(name=r['nome'], value=f"+{r['adicionado']} → Total: **{r['total']}**", inline=True)
        await ctx.send(embed=embed)
    
    if erros:
        await ctx.send("⚠️ " + "\n".join(erros))


@bot.command(name='estoque', aliases=['2', 'meuestoque'])
@canal_funcionario()
async def ver_estoque(ctx):
    """Mostra seu estoque."""
    func = ctx.funcionario
    empresa = ctx.empresa
    
    estoque = await get_estoque_funcionario(func['id'], empresa['id'])
    
    embed = discord.Embed(title=f"📦 Seu Estoque", color=discord.Color.blue())
    
    if not estoque:
        embed.description = "📭 Estoque vazio."
    else:
        total_valor = Decimal('0')
        
        for item in estoque:
            qtd = item['quantidade']
            valor_unit = Decimal(str(item['preco_funcionario']))
            valor_total = valor_unit * qtd
            total_valor += valor_total
            
            embed.add_field(name=item['nome'], value=f"Qtd: **{qtd}**\nValor: R$ {valor_total:.2f}", inline=True)
        
        embed.add_field(name="💰 Total a Receber", value=f"**R$ {total_valor:.2f}**", inline=False)
    
    embed.set_footer(text=f"Saldo acumulado: R$ {func['saldo']:.2f}")
    await ctx.send(embed=embed)


@bot.command(name='deletar', aliases=['3', 'remover'])
@canal_funcionario()
async def deletar_produto(ctx, *, entrada: str):
    """Remove produtos do estoque."""
    func = ctx.funcionario
    empresa = ctx.empresa
    
    matches = PRODUTO_REGEX.findall(entrada)
    
    if not matches:
        await ctx.send("❌ Formato: `!deletar codigo5`")
        return
    
    resultados = []
    erros = []
    
    for codigo, qtd_str in matches:
        resultado = await remover_do_estoque(func['id'], empresa['id'], codigo.lower(), int(qtd_str))
        
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
        await ctx.send("⚠️ " + "\n".join(erros))


@bot.command(name='meusaldo', aliases=['saldo'])
@canal_funcionario()
async def meu_saldo(ctx):
    """Mostra seu saldo acumulado."""
    func = ctx.funcionario
    
    embed = discord.Embed(title="💰 Seu Saldo", color=discord.Color.gold())
    embed.add_field(name="Saldo Acumulado", value=f"**R$ {func['saldo']:.2f}**")
    embed.set_footer(text="Use !estoque para ver valor pendente")
    
    await ctx.send(embed=embed)


# ============================================
# COMANDOS - ENCOMENDAS
# ============================================

@bot.command(name='novaencomenda', aliases=['4', 'addencomenda'])
@canal_funcionario()
async def nova_encomenda(ctx, comprador: str, *, itens: str):
    """Cria encomenda. Uso: !novaencomenda "Cliente" produto10 produto5"""
    func = ctx.funcionario
    empresa = ctx.empresa
    
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
    embed.set_footer(text=f"Criada por: {ctx.author.display_name}")
    await ctx.send(embed=embed)


@bot.command(name='encomendas', aliases=['5', 'pendentes'])
@canal_funcionario()
async def ver_encomendas(ctx):
    """Lista encomendas pendentes da empresa."""
    empresa = ctx.empresa
    
    response = supabase.table('encomendas').select('*, funcionarios(nome)').eq('empresa_id', empresa['id']).in_('status', ['pendente', 'em_andamento']).order('data_criacao').execute()
    
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
                value=f"**Itens:** {itens_str}\n**Valor:** R$ {enc['valor_total']:.2f}\n**Por:** {responsavel}",
                inline=False
            )
    
    embed.set_footer(text=f"Total: {len(encomendas)} pendentes")
    await ctx.send(embed=embed)


@bot.command(name='entregar', aliases=['entregarencomenda'])
@canal_funcionario()
async def entregar_encomenda(ctx, encomenda_id: int):
    """Entrega encomenda usando seu estoque."""
    func = ctx.funcionario
    empresa = ctx.empresa
    
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
        'data_entrega': datetime.utcnow().isoformat(),
        'funcionario_responsavel_id': func['id']
    }).eq('id', encomenda_id).execute()
    
    embed = discord.Embed(
        title="✅ Encomenda Entregue!",
        description=f"#{encomenda_id} para **{encomenda['comprador']}**",
        color=discord.Color.green()
    )
    embed.add_field(name="💰 Valor", value=f"R$ {encomenda['valor_total']:.2f}")
    embed.set_footer(text=f"Entregue por: {ctx.author.display_name}")
    await ctx.send(embed=embed)


# ============================================
# COMANDOS - FINANCEIRO (ADMIN)
# ============================================

@bot.command(name='pagar', aliases=['pagarestoque'])
@commands.has_permissions(manage_messages=True)
@empresa_configurada()
async def pagar_funcionario(ctx, membro: discord.Member):
    """Paga e zera estoque do funcionário."""
    empresa = ctx.empresa
    
    func = await get_funcionario_by_discord_id(str(membro.id), empresa['id'])
    if not func:
        await ctx.send(f"❌ {membro.display_name} não cadastrado nesta empresa.")
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
    
    for item in estoque[:10]:
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
        'descricao': f'Pagamento - {len(estoque)} tipos de produtos'
    }).execute()
    
    supabase.table('funcionarios').update({
        'saldo': float(Decimal(str(func['saldo'])) + total)
    }).eq('id', func['id']).execute()
    
    supabase.table('estoque_produtos').delete().eq('funcionario_id', func['id']).eq('empresa_id', empresa['id']).execute()
    
    # Limpa cache
    funcionarios_cache.pop(func.get('channel_id', ''), None)
    
    await ctx.send(f"✅ {membro.mention} recebeu **R$ {total:.2f}**! Estoque zerado.")


@bot.command(name='caixa', aliases=['financeiro'])
@commands.has_permissions(manage_messages=True)
@empresa_configurada()
async def verificar_caixa(ctx):
    """Relatório financeiro da empresa."""
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
# COMANDOS - CONSULTA
# ============================================

@bot.command(name='produtos', aliases=['catalogo', 'listaprodutos'])
@empresa_configurada()
async def ver_produtos(ctx, *, categoria: str = None):
    """Lista produtos configurados. Uso: !produtos [categoria]"""
    empresa = ctx.empresa
    produtos = await get_produtos_empresa(empresa['id'])
    
    if not produtos:
        await ctx.send("❌ Nenhum produto configurado. Admin: use `!configurarauto`.")
        return
    
    # Agrupa por categoria
    categorias = {}
    for codigo, p in produtos.items():
        cat = p['produtos_referencia'].get('categoria', 'Outros')
        if cat not in categorias:
            categorias[cat] = []
        categorias[cat].append((codigo, p))
    
    if categoria:
        # Busca categoria específica
        cat_encontrada = None
        for cat in categorias.keys():
            if categoria.lower() in cat.lower():
                cat_encontrada = cat
                break
        
        if not cat_encontrada:
            cats_list = "\n".join(f"• `{c}`" for c in categorias.keys())
            await ctx.send(f"❌ Categoria `{categoria}` não encontrada.\n\n**Categorias disponíveis:**\n{cats_list}")
            return
        
        # Mostra produtos da categoria com detalhes
        prods = categorias[cat_encontrada]
        
        embed = discord.Embed(
            title=f"📦 {cat_encontrada}",
            description=f"**{len(prods)} produtos** • Use `!add codigo[qtd]` para adicionar",
            color=discord.Color.blue()
        )
        
        for codigo, p in prods[:25]:
            ref = p['produtos_referencia']
            embed.add_field(
                name=f"`{codigo}`",
                value=f"**{ref['nome']}**\n💵 ${p['preco_venda']:.2f} | 👷 ${p['preco_pagamento_funcionario']:.2f}",
                inline=True
            )
        
        if len(prods) > 25:
            embed.set_footer(text=f"Mostrando 25 de {len(prods)} • Use !buscar [termo]")
        
        await ctx.send(embed=embed)
    else:
        # Lista todas as categorias
        embed = discord.Embed(
            title=f"📦 Catálogo - {empresa['nome']}",
            description="Escolha uma categoria: `!produtos [categoria]`",
            color=discord.Color.blue()
        )
        
        for cat, prods in sorted(categorias.items()):
            codigos = ", ".join(f"`{c}`" for c, _ in prods[:5])
            if len(prods) > 5:
                codigos += f" +{len(prods)-5}"
            embed.add_field(name=f"📁 {cat} ({len(prods)})", value=codigos, inline=False)
        
        embed.set_footer(text=f"Total: {len(produtos)} produtos | !buscar [termo] | !infoproduto [codigo]")
        await ctx.send(embed=embed)


@bot.command(name='estoqueglobal', aliases=['producao', 'estoquetotal'])
@empresa_configurada()
async def ver_estoque_global(ctx):
    """Mostra estoque total da empresa."""
    empresa = ctx.empresa
    estoque = await get_estoque_global(empresa['id'])
    
    embed = discord.Embed(title=f"🏢 Estoque Global - {empresa['nome']}", color=discord.Color.gold())
    
    if not estoque:
        embed.description = "📭 Nenhum produto em estoque."
    else:
        total_itens = 0
        for item in estoque[:25]:
            embed.add_field(name=item['nome'], value=f"**{item['quantidade']}** un", inline=True)
            total_itens += item['quantidade']
        
        embed.set_footer(text=f"Total: {total_itens} itens | {len(estoque)} tipos | {datetime.now().strftime('%H:%M')}")
    
    await ctx.send(embed=embed)


@bot.command(name='funcionarios', aliases=['listafuncionarios', 'equipe'])
@commands.has_permissions(manage_messages=True)
@empresa_configurada()
async def ver_funcionarios(ctx):
    """Lista funcionários cadastrados."""
    empresa = ctx.empresa
    
    response = supabase.table('funcionarios').select('*').eq('empresa_id', empresa['id']).eq('ativo', True).execute()
    
    embed = discord.Embed(title=f"👷 Funcionários - {empresa['nome']}", color=discord.Color.blue())
    
    if not response.data:
        embed.description = "Nenhum funcionário cadastrado.\nUse `!bemvindo @pessoa` para adicionar."
    else:
        for func in response.data[:20]:
            canal = f"<#{func['channel_id']}>" if func.get('channel_id') else "Sem canal"
            saldo = func.get('saldo', 0)
            embed.add_field(
                name=f"👤 {func['nome']}",
                value=f"💰 ${saldo:.2f}\n{canal}",
                inline=True
            )
    
    embed.set_footer(text=f"Total: {len(response.data)} funcionários")
    await ctx.send(embed=embed)


@bot.command(name='help', aliases=['ajuda', 'comandos', 'h'])
async def ajuda(ctx):
    """Mostra todos os comandos disponíveis."""
    empresa = await get_empresa_by_guild(str(ctx.guild.id))
    
    embed = discord.Embed(
        title="🏢 Bot Multi-Empresa Downtown v2.0",
        description=f"**Empresa:** {empresa['nome'] if empresa else 'Não configurada'}\n**Tipo:** {empresa['tipos_empresa']['nome'] if empresa else 'N/A'}",
        color=discord.Color.green()
    )
    
    if not empresa:
        embed.add_field(
            name="⚙️ Começar",
            value="`!configurar` - Configurar empresa (Admin)",
            inline=False
        )
    else:
        # Admin - Configuração
        embed.add_field(
            name="⚙️ Configuração (Admin)",
            value=(
                "`!configurar` - Ver/criar empresa\n"
                "`!configurarauto` - Config produtos automático\n"
                "`!configurarprecos` - Config manual por categoria\n"
                "`!bemvindo @pessoa` - Criar canal funcionário\n"
                "`!funcionarios` - Listar equipe"
            ),
            inline=False
        )
        
        # Produtos
        embed.add_field(
            name="📦 Produtos & Preços",
            value=(
                "`!produtos [categoria]` - Catálogo completo\n"
                "`!buscar [termo]` - Pesquisar produto\n"
                "`!infoproduto [codigo]` - Info detalhada\n"
                "`!verprecos [categoria]` - Ver preços\n"
                "`!alterarpreco [cod] [valor]` - Mudar (Admin)"
            ),
            inline=False
        )
        
        # Produção
        embed.add_field(
            name="🌾 Produção (no seu canal)",
            value=(
                "`!add codigo[qtd]` - Adicionar ao estoque\n"
                "`!estoque` ou `!2` - Ver seu estoque\n"
                "`!deletar codigo[qtd]` - Remover\n"
                "`!meusaldo` - Ver saldo acumulado"
            ),
            inline=False
        )
        
        # Encomendas
        embed.add_field(
            name="📋 Encomendas",
            value=(
                '`!novaencomenda "Cliente" itens` - Nova\n'
                "`!encomendas` ou `!5` - Ver pendentes\n"
                "`!entregar [ID]` - Entregar encomenda"
            ),
            inline=False
        )
        
        # Financeiro
        embed.add_field(
            name="💰 Financeiro",
            value=(
                "`!pagar @pessoa` - Pagar estoque (Admin)\n"
                "`!caixa` - Relatório financeiro (Admin)\n"
                "`!estoqueglobal` - Estoque total empresa"
            ),
            inline=False
        )
        
        # Utilidades
        embed.add_field(
            name="🔧 Utilidades",
            value=(
                "`!empresa` - Info da empresa\n"
                "`!limpar [qtd]` - Limpar mensagens\n"
                "`!help` - Este menu"
            ),
            inline=False
        )
    
    embed.set_footer(text="Códigos de produto: !produtos | Dicas: !buscar [termo]")
    await ctx.send(embed=embed)


@bot.command(name='empresa', aliases=['info'])
@empresa_configurada()
async def info_empresa(ctx):
    """Mostra informações da empresa."""
    empresa = ctx.empresa
    
    produtos = await get_produtos_empresa(empresa['id'])
    funcionarios = supabase.table('funcionarios').select('id').eq('empresa_id', empresa['id']).execute()
    
    embed = discord.Embed(
        title=f"{empresa['tipos_empresa']['icone']} {empresa['nome']}",
        description=f"**Tipo:** {empresa['tipos_empresa']['nome']}",
        color=discord.Color.green()
    )
    
    embed.add_field(name="📦 Produtos", value=f"{len(produtos)} configurados")
    embed.add_field(name="👷 Funcionários", value=f"{len(funcionarios.data)} cadastrados")
    
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


@bot.command(name='resetarcache', aliases=['clearcache'])
@commands.has_permissions(administrator=True)
async def resetar_cache(ctx):
    """Limpa cache interno do bot (Admin)."""
    empresas_cache.clear()
    funcionarios_cache.clear()
    await ctx.send("✅ Cache limpo! As informações serão recarregadas do banco.")


# ============================================
# INICIALIZAÇÃO
# ============================================

if __name__ == '__main__':
    print("Iniciando Bot Multi-Empresa Downtown v2.0...")
    bot.run(DISCORD_TOKEN)
