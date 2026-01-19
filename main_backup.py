"""
Bot Fazendeiro - Sistema de Gerenciamento Econômico para Roleplay (RDR2)
Desenvolvido para Discord com integração Supabase
"""

import os
import re
import json
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

# Validação das variáveis de ambiente
if not all([DISCORD_TOKEN, SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError(
        "Variáveis de ambiente faltando. Configure DISCORD_TOKEN, SUPABASE_URL e SUPABASE_KEY no arquivo .env"
    )

# Cliente Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configuração do Bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Regex para parsing de animais (ex: pa2, va10, gp5)
ANIMAL_REGEX = re.compile(r'([a-zA-Z]+)(\d+)')


# ============================================
# FUNÇÕES AUXILIARES DO BANCO DE DADOS
# ============================================

async def get_or_create_funcionario(discord_id: str, nome: str) -> Optional[int]:
    """Obtém ou cria um funcionário no banco de dados."""
    try:
        # Tenta encontrar funcionário existente
        response = supabase.table('funcionarios').select('id').eq('discord_id', discord_id).execute()

        if response.data:
            return response.data[0]['id']

        # Cria novo funcionário
        response = supabase.table('funcionarios').insert({
            'discord_id': discord_id,
            'nome': nome
        }).execute()

        return response.data[0]['id'] if response.data else None
    except Exception as e:
        print(f"Erro ao obter/criar funcionário: {e}")
        return None


async def get_funcionario_by_discord_id(discord_id: str) -> Optional[Dict]:
    """Obtém dados completos do funcionário pelo Discord ID."""
    try:
        response = supabase.table('funcionarios').select('*').eq('discord_id', discord_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Erro ao buscar funcionário: {e}")
        return None


async def get_precos_config() -> Dict[str, Dict]:
    """Obtém a tabela de preços como dicionário."""
    try:
        response = supabase.table('precos_config').select('*').eq('ativo', True).execute()
        return {item['sigla']: item for item in response.data}
    except Exception as e:
        print(f"Erro ao buscar preços: {e}")
        return {}


async def adicionar_ao_estoque(funcionario_id: int, sigla: str, quantidade: int) -> Optional[Dict]:
    """Adiciona animais ao estoque do funcionário."""
    try:
        sigla_lower = sigla.lower()

        # Verifica se a sigla existe
        preco = supabase.table('precos_config').select('nome_real').eq('sigla', sigla_lower).execute()
        if not preco.data:
            return None

        # Verifica estoque existente
        estoque = supabase.table('estoque_animais').select('*').eq(
            'funcionario_id', funcionario_id
        ).eq('sigla_animal', sigla_lower).execute()

        if estoque.data:
            # Atualiza quantidade existente
            nova_qtd = estoque.data[0]['quantidade'] + quantidade
            supabase.table('estoque_animais').update({
                'quantidade': nova_qtd,
                'data_atualizacao': datetime.utcnow().isoformat()
            }).eq('id', estoque.data[0]['id']).execute()

            return {'quantidade': nova_qtd, 'nome': preco.data[0]['nome_real']}
        else:
            # Insere novo registro
            supabase.table('estoque_animais').insert({
                'funcionario_id': funcionario_id,
                'sigla_animal': sigla_lower,
                'quantidade': quantidade
            }).execute()

            return {'quantidade': quantidade, 'nome': preco.data[0]['nome_real']}
    except Exception as e:
        print(f"Erro ao adicionar ao estoque: {e}")
        return None


async def remover_do_estoque(funcionario_id: int, sigla: str, quantidade: int) -> Optional[Dict]:
    """Remove animais do estoque do funcionário."""
    try:
        sigla_lower = sigla.lower()

        estoque = supabase.table('estoque_animais').select(
            '*, precos_config!inner(nome_real)'
        ).eq('funcionario_id', funcionario_id).eq('sigla_animal', sigla_lower).execute()

        if not estoque.data:
            return {'erro': 'Animal não encontrado no estoque'}

        atual = estoque.data[0]['quantidade']
        nome = estoque.data[0]['precos_config']['nome_real']

        if quantidade > atual:
            return {'erro': f'Quantidade insuficiente. Você tem {atual} {nome}(s)'}

        nova_qtd = atual - quantidade

        if nova_qtd == 0:
            supabase.table('estoque_animais').delete().eq('id', estoque.data[0]['id']).execute()
        else:
            supabase.table('estoque_animais').update({
                'quantidade': nova_qtd,
                'data_atualizacao': datetime.utcnow().isoformat()
            }).eq('id', estoque.data[0]['id']).execute()

        return {'quantidade': nova_qtd, 'nome': nome, 'removido': quantidade}
    except Exception as e:
        print(f"Erro ao remover do estoque: {e}")
        return None


async def get_estoque_funcionario(funcionario_id: int) -> List[Dict]:
    """Obtém o estoque completo de um funcionário."""
    try:
        response = supabase.table('estoque_animais').select(
            '*, precos_config!inner(nome_real, valor_pagamento_funcionario)'
        ).eq('funcionario_id', funcionario_id).gt('quantidade', 0).execute()

        return response.data
    except Exception as e:
        print(f"Erro ao buscar estoque: {e}")
        return []


async def get_estoque_global() -> List[Dict]:
    """Obtém o estoque global de todos os funcionários."""
    try:
        response = supabase.rpc('', {}).execute()

        # Query manual para agregação
        response = supabase.table('estoque_animais').select(
            'sigla_animal, quantidade, precos_config!inner(nome_real)'
        ).gt('quantidade', 0).execute()

        # Agrupa por animal
        totais = {}
        for item in response.data:
            sigla = item['sigla_animal']
            if sigla not in totais:
                totais[sigla] = {
                    'sigla': sigla,
                    'nome': item['precos_config']['nome_real'],
                    'quantidade': 0
                }
            totais[sigla]['quantidade'] += item['quantidade']

        return list(totais.values())
    except Exception as e:
        print(f"Erro ao buscar estoque global: {e}")
        return []


# ============================================
# EVENTOS DO BOT
# ============================================

@bot.event
async def on_ready():
    """Evento disparado quando o bot está pronto."""
    print('============================================')
    print('  Bot Fazendeiro conectado com sucesso!')
    print(f'  Usuario: {bot.user.name}')
    print(f'  ID: {bot.user.id}')
    print('============================================')

    # Define status do bot
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="a Fazenda | !help"
        )
    )


@bot.event
async def on_command_error(ctx, error):
    """Tratamento global de erros."""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Argumento faltando: `{error.param.name}`")
    elif isinstance(error, commands.MissingRole):
        await ctx.send("❌ Você não tem permissão para usar este comando.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Você não tem as permissões necessárias.")
    elif isinstance(error, commands.CommandNotFound):
        pass  # Ignora comandos não encontrados
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Argumento inválido: {error}")
    else:
        print(f"Erro não tratado: {error}")
        await ctx.send("❌ Ocorreu um erro ao executar o comando.")


# ============================================
# COMANDOS - GESTÃO DE SERVIDOR
# ============================================

@bot.command(name='bemvindo')
@commands.has_permissions(manage_channels=True)
async def bemvindo(ctx, membro: discord.Member):
    """
    Cria um canal privado para o novo funcionário.
    Uso: !bemvindo @pessoa
    """
    try:
        guild = ctx.guild

        # Nome do canal baseado no nome do membro
        nome_canal = f"fiscal-{membro.display_name.lower().replace(' ', '-')}"

        # Configuração de permissões
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            membro: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                attach_files=True,
                embed_links=True
            ),
            guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_messages=True
            )
        }

        # Adiciona permissão para admins
        for role in guild.roles:
            if role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True
                )

        # Cria o canal
        canal = await guild.create_text_channel(
            name=nome_canal,
            overwrites=overwrites,
            topic=f"Canal privado do funcionário {membro.display_name}"
        )

        # Cadastra funcionário no banco
        func_id = await get_or_create_funcionario(str(membro.id), membro.display_name)

        # Embed de boas-vindas
        embed = discord.Embed(
            title="🌾 Bem-vindo à Fazenda!",
            description=f"Olá {membro.mention}!\n\nEste é seu canal privado para registro de produção.",
            color=discord.Color.green()
        )
        embed.add_field(
            name="📋 Comandos Principais",
            value="""
`!add [sigla][qtd]` - Adicionar animais (ex: !add pa5)
`!veranimais` ou `!2` - Ver seu estoque
`!deletaranimal [sigla][qtd]` - Remover animais
`!encomendas` ou `!5` - Ver encomendas pendentes
            """,
            inline=False
        )
        embed.add_field(
            name="🐄 Siglas de Animais",
            value="""
`pa/pm/pp` - Porco (Adulto/Médio/Pequeno)
`va/vm/vp` - Vaca (Adulto/Médio/Pequeno)
`ga/gm/gp` - Galinha (Adulto/Médio/Pequeno)
`ca/cm/cp` - Cavalo (Adulto/Médio/Pequeno)
            """,
            inline=False
        )
        embed.set_footer(text=f"ID do Funcionário: {func_id}")

        await canal.send(embed=embed)

        # Confirmação no canal original
        await ctx.send(f"✅ Canal {canal.mention} criado para {membro.mention}!")

    except discord.Forbidden:
        await ctx.send("❌ Não tenho permissão para criar canais.")
    except Exception as e:
        await ctx.send(f"❌ Erro ao criar canal: {e}")


@bot.command(name='limpar')
@commands.has_permissions(manage_messages=True)
async def limpar(ctx, quantidade: int = 10):
    """
    Limpa mensagens do canal.
    Uso: !limpar [quantidade]
    """
    if quantidade < 1 or quantidade > 100:
        await ctx.send("❌ A quantidade deve estar entre 1 e 100.")
        return

    try:
        deleted = await ctx.channel.purge(limit=quantidade + 1)  # +1 para incluir o comando
        msg = await ctx.send(f"🧹 {len(deleted) - 1} mensagens apagadas!")
        await asyncio.sleep(3)
        await msg.delete()
    except discord.Forbidden:
        await ctx.send("❌ Não tenho permissão para apagar mensagens.")
    except Exception as e:
        await ctx.send(f"❌ Erro ao limpar mensagens: {e}")


# ============================================
# COMANDOS - SISTEMA DE PRODUÇÃO
# ============================================

@bot.command(name='add', aliases=['animal', '1'])
async def add_animal(ctx, *, entrada: str):
    """
    Adiciona animais ao estoque usando Regex.
    Uso: !add pa2 va5 gp10
    """
    try:
        # Obtém ou cria funcionário
        func_id = await get_or_create_funcionario(str(ctx.author.id), ctx.author.display_name)
        if not func_id:
            await ctx.send("❌ Erro ao identificar funcionário.")
            return

        # Parse com Regex - encontra todos os padrões [letras][números]
        matches = ANIMAL_REGEX.findall(entrada)

        if not matches:
            await ctx.send(
                "❌ Formato inválido. Use: `!add [sigla][quantidade]`\n"
                "Exemplos: `!add pa2`, `!add va5 gp10`, `!add pa2va3gp5`"
            )
            return

        # Carrega tabela de preços para validação
        precos = await get_precos_config()

        resultados = []
        erros = []

        for sigla, qtd_str in matches:
            sigla_lower = sigla.lower()
            quantidade = int(qtd_str)

            if quantidade <= 0:
                erros.append(f"Quantidade inválida para {sigla}")
                continue

            if sigla_lower not in precos:
                erros.append(f"Sigla `{sigla}` não reconhecida")
                continue

            # Adiciona ao estoque
            resultado = await adicionar_ao_estoque(func_id, sigla_lower, quantidade)

            if resultado:
                resultados.append({
                    'sigla': sigla_lower.upper(),
                    'nome': resultado['nome'],
                    'adicionado': quantidade,
                    'total': resultado['quantidade']
                })
            else:
                erros.append(f"Erro ao adicionar {sigla}")

        # Cria embed de resposta
        if resultados:
            embed = discord.Embed(
                title="✅ Animais Adicionados!",
                color=discord.Color.green()
            )

            for r in resultados:
                embed.add_field(
                    name=f"{r['nome']} ({r['sigla']})",
                    value=f"+{r['adicionado']} → Total: **{r['total']}**",
                    inline=True
                )

            embed.set_footer(text=f"Funcionário: {ctx.author.display_name}")
            await ctx.send(embed=embed)

        if erros:
            await ctx.send("⚠️ Avisos:\n" + "\n".join(f"• {e}" for e in erros))

    except Exception as e:
        await ctx.send(f"❌ Erro ao adicionar animais: {e}")


@bot.command(name='veranimais', aliases=['2', 'estoque', 'meuestoque'])
async def ver_animais(ctx, membro: discord.Member = None):
    """
    Mostra o estoque de animais do funcionário.
    Uso: !veranimais ou !2
    """
    try:
        # Se não especificou membro, usa o autor
        target = membro or ctx.author

        func = await get_funcionario_by_discord_id(str(target.id))
        if not func:
            await ctx.send(f"❌ {target.display_name} não está cadastrado como funcionário.")
            return

        estoque = await get_estoque_funcionario(func['id'])

        embed = discord.Embed(
            title=f"🐄 Estoque de {target.display_name}",
            color=discord.Color.blue()
        )

        if not estoque:
            embed.description = "📭 Estoque vazio."
        else:
            total_valor = Decimal('0')

            for item in estoque:
                nome = item['precos_config']['nome_real']
                qtd = item['quantidade']
                sigla = item['sigla_animal'].upper()
                valor_unit = Decimal(str(item['precos_config']['valor_pagamento_funcionario']))
                valor_total = valor_unit * qtd
                total_valor += valor_total

                embed.add_field(
                    name=f"{nome} ({sigla})",
                    value=f"Qtd: **{qtd}**\nValor: R$ {valor_total:.2f}",
                    inline=True
                )

            embed.add_field(
                name="💰 Total a Receber",
                value=f"**R$ {total_valor:.2f}**",
                inline=False
            )

        embed.set_footer(text=f"Saldo acumulado: R$ {func['saldo']:.2f}")
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Erro ao buscar estoque: {e}")


@bot.command(name='deletaranimal', aliases=['3', 'remover', 'deletar'])
async def deletar_animal(ctx, *, entrada: str):
    """
    Remove animais do estoque.
    Uso: !deletaranimal pa2 va5
    """
    try:
        func = await get_funcionario_by_discord_id(str(ctx.author.id))
        if not func:
            await ctx.send("❌ Você não está cadastrado como funcionário.")
            return

        # Parse com Regex
        matches = ANIMAL_REGEX.findall(entrada)

        if not matches:
            await ctx.send(
                "❌ Formato inválido. Use: `!deletaranimal [sigla][quantidade]`\n"
                "Exemplo: `!deletaranimal pa2`"
            )
            return

        resultados = []
        erros = []

        for sigla, qtd_str in matches:
            quantidade = int(qtd_str)

            if quantidade <= 0:
                erros.append(f"Quantidade inválida para {sigla}")
                continue

            resultado = await remover_do_estoque(func['id'], sigla, quantidade)

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
                erros.append(f"Erro ao remover {sigla}")

        if resultados:
            embed = discord.Embed(
                title="🗑️ Animais Removidos",
                color=discord.Color.orange()
            )

            for r in resultados:
                embed.add_field(
                    name=r['nome'],
                    value=f"-{r['removido']} → Restante: **{r['restante']}**",
                    inline=True
                )

            await ctx.send(embed=embed)

        if erros:
            await ctx.send("⚠️ Erros:\n" + "\n".join(f"• {e}" for e in erros))

    except Exception as e:
        await ctx.send(f"❌ Erro ao remover animais: {e}")


@bot.command(name='verestoque', aliases=['estoqueglobal', 'producao'])
async def ver_estoque_global(ctx):
    """
    Mostra o estoque global da fazenda.
    Uso: !verestoque
    """
    try:
        estoque = await get_estoque_global()

        embed = discord.Embed(
            title="🏠 Estoque Global da Fazenda",
            color=discord.Color.gold()
        )

        if not estoque:
            embed.description = "📭 Nenhum animal em estoque."
        else:
            # Organiza por categoria (primeira letra)
            categorias = {}
            for item in estoque:
                cat = item['nome'].split()[0]  # Primeira palavra (Porco, Vaca, etc)
                if cat not in categorias:
                    categorias[cat] = []
                categorias[cat].append(item)

            for cat, itens in categorias.items():
                valor = "\n".join(
                    f"`{i['sigla'].upper()}` {i['nome']}: **{i['quantidade']}**"
                    for i in itens
                )
                embed.add_field(name=f"🐄 {cat}", value=valor, inline=True)

        embed.set_footer(text=f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Erro ao buscar estoque global: {e}")


# ============================================
# COMANDOS - SISTEMA DE ENCOMENDAS
# ============================================

@bot.command(name='adicionarencomenda', aliases=['novaencomenda'])
@commands.has_permissions(manage_messages=True)
async def adicionar_encomenda(ctx, comprador: str, *, itens: str):
    """
    Cria uma nova encomenda (Admin).
    Uso: !adicionarencomenda "Nome Comprador" pa5 va3 gp10
    """
    try:
        # Parse dos itens com Regex
        matches = ANIMAL_REGEX.findall(itens)

        if not matches:
            await ctx.send(
                "❌ Formato inválido. Use: `!adicionarencomenda \"Comprador\" pa5 va3`"
            )
            return

        precos = await get_precos_config()
        itens_json = []
        valor_total = Decimal('0')

        for sigla, qtd_str in matches:
            sigla_lower = sigla.lower()
            quantidade = int(qtd_str)

            if sigla_lower not in precos:
                await ctx.send(f"❌ Sigla `{sigla}` não reconhecida.")
                return

            preco_info = precos[sigla_lower]
            valor = Decimal(str(preco_info['valor_venda'])) * quantidade
            valor_total += valor

            itens_json.append({
                'sigla': sigla_lower,
                'nome': preco_info['nome_real'],
                'quantidade': quantidade,
                'quantidade_entregue': 0,
                'valor_unitario': float(preco_info['valor_venda'])
            })

        # Insere no banco
        response = supabase.table('encomendas').insert({
            'comprador': comprador,
            'itens_json': itens_json,
            'valor_total': float(valor_total),
            'status': 'pendente'
        }).execute()

        encomenda_id = response.data[0]['id']

        embed = discord.Embed(
            title="📦 Nova Encomenda Criada!",
            description=f"**ID:** #{encomenda_id}\n**Comprador:** {comprador}",
            color=discord.Color.green()
        )

        for item in itens_json:
            embed.add_field(
                name=f"{item['nome']} ({item['sigla'].upper()})",
                value=f"Quantidade: {item['quantidade']}",
                inline=True
            )

        embed.add_field(
            name="💰 Valor Total",
            value=f"**R$ {valor_total:.2f}**",
            inline=False
        )

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Erro ao criar encomenda: {e}")


@bot.command(name='addencomenda', aliases=['4'])
async def add_encomenda_funcionario(ctx, comprador: str, *, itens: str):
    """
    Funcionário cria encomenda.
    Uso: !addencomenda "Nome" pa5 va3
    """
    # Mesma lógica do admin, mas vincula ao funcionário
    try:
        func = await get_funcionario_by_discord_id(str(ctx.author.id))
        if not func:
            await ctx.send("❌ Você não está cadastrado como funcionário.")
            return

        matches = ANIMAL_REGEX.findall(itens)

        if not matches:
            await ctx.send("❌ Formato inválido. Use: `!addencomenda \"Comprador\" pa5 va3`")
            return

        precos = await get_precos_config()
        itens_json = []
        valor_total = Decimal('0')

        for sigla, qtd_str in matches:
            sigla_lower = sigla.lower()
            quantidade = int(qtd_str)

            if sigla_lower not in precos:
                await ctx.send(f"❌ Sigla `{sigla}` não reconhecida.")
                return

            preco_info = precos[sigla_lower]
            valor = Decimal(str(preco_info['valor_venda'])) * quantidade
            valor_total += valor

            itens_json.append({
                'sigla': sigla_lower,
                'nome': preco_info['nome_real'],
                'quantidade': quantidade,
                'quantidade_entregue': 0,
                'valor_unitario': float(preco_info['valor_venda'])
            })

        response = supabase.table('encomendas').insert({
            'comprador': comprador,
            'itens_json': itens_json,
            'valor_total': float(valor_total),
            'status': 'pendente',
            'funcionario_responsavel_id': func['id']
        }).execute()

        encomenda_id = response.data[0]['id']

        embed = discord.Embed(
            title="📦 Encomenda Registrada!",
            description=f"**ID:** #{encomenda_id}\n**Comprador:** {comprador}",
            color=discord.Color.green()
        )

        for item in itens_json:
            embed.add_field(
                name=item['nome'],
                value=f"Quantidade: {item['quantidade']}",
                inline=True
            )

        embed.add_field(name="💰 Total", value=f"R$ {valor_total:.2f}", inline=False)
        embed.set_footer(text=f"Responsável: {ctx.author.display_name}")

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Erro ao criar encomenda: {e}")


@bot.command(name='verencomendas', aliases=['5', 'encomendas', 'pendentes'])
async def ver_encomendas(ctx):
    """
    Lista encomendas pendentes.
    Uso: !verencomendas ou !5
    """
    try:
        response = supabase.table('encomendas').select(
            '*, funcionarios(nome)'
        ).in_('status', ['pendente', 'em_andamento']).order('data_criacao').execute()

        encomendas = response.data

        embed = discord.Embed(
            title="📋 Encomendas Pendentes",
            color=discord.Color.blue()
        )

        if not encomendas:
            embed.description = "✅ Nenhuma encomenda pendente!"
        else:
            for enc in encomendas[:10]:  # Limita a 10 para não estourar o embed
                itens_str = ", ".join(
                    f"{i['quantidade']}x {i['sigla'].upper()}"
                    for i in enc['itens_json']
                )

                responsavel = enc['funcionarios']['nome'] if enc.get('funcionarios') else "Não atribuído"
                status_emoji = "🟡" if enc['status'] == 'pendente' else "🔵"

                embed.add_field(
                    name=f"{status_emoji} #{enc['id']} - {enc['comprador']}",
                    value=f"**Itens:** {itens_str}\n**Valor:** R$ {enc['valor_total']:.2f}\n**Resp:** {responsavel}",
                    inline=False
                )

        embed.set_footer(text=f"Total: {len(encomendas)} encomendas pendentes")
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Erro ao buscar encomendas: {e}")


@bot.command(name='entregarencomenda', aliases=['entregar'])
async def entregar_encomenda(ctx, encomenda_id: int):
    """
    Entrega uma encomenda completa.
    Uso: !entregarencomenda [ID]
    """
    try:
        func = await get_funcionario_by_discord_id(str(ctx.author.id))
        if not func:
            await ctx.send("❌ Você não está cadastrado.")
            return

        # Busca a encomenda
        response = supabase.table('encomendas').select('*').eq('id', encomenda_id).execute()

        if not response.data:
            await ctx.send(f"❌ Encomenda #{encomenda_id} não encontrada.")
            return

        encomenda = response.data[0]

        if encomenda['status'] == 'entregue':
            await ctx.send("❌ Esta encomenda já foi entregue.")
            return

        # Verifica estoque do funcionário
        estoque = await get_estoque_funcionario(func['id'])
        estoque_dict = {e['sigla_animal']: e['quantidade'] for e in estoque}

        faltando = []
        for item in encomenda['itens_json']:
            precisa = item['quantidade'] - item.get('quantidade_entregue', 0)
            tem = estoque_dict.get(item['sigla'], 0)

            if tem < precisa:
                faltando.append(f"{item['nome']}: precisa {precisa}, tem {tem}")

        if faltando:
            embed = discord.Embed(
                title="❌ Estoque Insuficiente",
                description="\n".join(faltando),
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        # Deduz do estoque e marca como entregue
        for item in encomenda['itens_json']:
            precisa = item['quantidade'] - item.get('quantidade_entregue', 0)
            await remover_do_estoque(func['id'], item['sigla'], precisa)

        # Atualiza status da encomenda
        supabase.table('encomendas').update({
            'status': 'entregue',
            'data_entrega': datetime.utcnow().isoformat(),
            'funcionario_responsavel_id': func['id']
        }).eq('id', encomenda_id).execute()

        embed = discord.Embed(
            title="✅ Encomenda Entregue!",
            description=f"Encomenda #{encomenda_id} para **{encomenda['comprador']}** foi entregue com sucesso!",
            color=discord.Color.green()
        )
        embed.add_field(name="💰 Valor", value=f"R$ {encomenda['valor_total']:.2f}")
        embed.set_footer(text=f"Entregue por: {ctx.author.display_name}")

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Erro ao entregar encomenda: {e}")


@bot.command(name='entregarencomendaparcial', aliases=['99', 'parcial'])
async def entregar_parcial(ctx, encomenda_id: int, *, entrada: str):
    """
    Entrega parcial de uma encomenda.
    Uso: !entregarencomendaparcial [ID] pa2 va1
    """
    try:
        func = await get_funcionario_by_discord_id(str(ctx.author.id))
        if not func:
            await ctx.send("❌ Você não está cadastrado.")
            return

        # Busca encomenda
        response = supabase.table('encomendas').select('*').eq('id', encomenda_id).execute()

        if not response.data:
            await ctx.send(f"❌ Encomenda #{encomenda_id} não encontrada.")
            return

        encomenda = response.data[0]

        if encomenda['status'] == 'entregue':
            await ctx.send("❌ Esta encomenda já foi entregue.")
            return

        # Parse da entrada
        matches = ANIMAL_REGEX.findall(entrada)
        if not matches:
            await ctx.send("❌ Formato inválido. Use: `!entregarencomendaparcial [ID] pa2 va1`")
            return

        itens_encomenda = {i['sigla']: i for i in encomenda['itens_json']}
        estoque = await get_estoque_funcionario(func['id'])
        estoque_dict = {e['sigla_animal']: e['quantidade'] for e in estoque}

        entregas = []
        erros = []

        for sigla, qtd_str in matches:
            sigla_lower = sigla.lower()
            quantidade = int(qtd_str)

            if sigla_lower not in itens_encomenda:
                erros.append(f"{sigla.upper()} não está na encomenda")
                continue

            item = itens_encomenda[sigla_lower]
            restante = item['quantidade'] - item.get('quantidade_entregue', 0)

            if quantidade > restante:
                erros.append(f"{sigla.upper()}: máximo restante é {restante}")
                continue

            if estoque_dict.get(sigla_lower, 0) < quantidade:
                erros.append(f"{sigla.upper()}: estoque insuficiente")
                continue

            entregas.append({'sigla': sigla_lower, 'quantidade': quantidade, 'nome': item['nome']})

        if not entregas:
            await ctx.send("❌ Nenhum item válido para entrega.\n" + "\n".join(erros))
            return

        # Processa entregas
        itens_atualizados = encomenda['itens_json'].copy()

        for entrega in entregas:
            # Remove do estoque
            await remover_do_estoque(func['id'], entrega['sigla'], entrega['quantidade'])

            # Atualiza quantidade entregue na encomenda
            for item in itens_atualizados:
                if item['sigla'] == entrega['sigla']:
                    item['quantidade_entregue'] = item.get('quantidade_entregue', 0) + entrega['quantidade']

        # Verifica se a encomenda foi completamente entregue
        completa = all(
            i['quantidade'] == i.get('quantidade_entregue', 0)
            for i in itens_atualizados
        )

        novo_status = 'entregue' if completa else 'em_andamento'

        supabase.table('encomendas').update({
            'itens_json': itens_atualizados,
            'status': novo_status,
            'data_entrega': datetime.utcnow().isoformat() if completa else None
        }).eq('id', encomenda_id).execute()

        embed = discord.Embed(
            title="📦 Entrega Parcial Registrada!",
            description=f"Encomenda #{encomenda_id}",
            color=discord.Color.blue() if not completa else discord.Color.green()
        )

        for e in entregas:
            embed.add_field(name=e['nome'], value=f"Entregue: {e['quantidade']}", inline=True)

        if completa:
            embed.add_field(name="🎉 Status", value="**ENCOMENDA COMPLETA!**", inline=False)
        else:
            restantes = [
                f"{i['sigla'].upper()}: {i['quantidade'] - i.get('quantidade_entregue', 0)}"
                for i in itens_atualizados
                if i['quantidade'] > i.get('quantidade_entregue', 0)
            ]
            embed.add_field(name="📋 Ainda Pendente", value="\n".join(restantes), inline=False)

        if erros:
            embed.add_field(name="⚠️ Avisos", value="\n".join(erros), inline=False)

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Erro ao processar entrega parcial: {e}")


# ============================================
# COMANDOS - FINANCEIRO
# ============================================

@bot.command(name='pagarplanta', aliases=['pp'])
@commands.has_permissions(manage_messages=True)
async def pagar_planta(ctx, membro: discord.Member, valor: float, *, descricao: str = "Pagamento de plantas"):
    """
    Registra pagamento manual (plantas, etc).
    Uso: !pagarplanta @pessoa [valor] [descrição]
    """
    try:
        func = await get_funcionario_by_discord_id(str(membro.id))
        if not func:
            await ctx.send(f"❌ {membro.display_name} não está cadastrado.")
            return

        if valor <= 0:
            await ctx.send("❌ O valor deve ser positivo.")
            return

        # Registra pagamento
        supabase.table('historico_pagamentos').insert({
            'funcionario_id': func['id'],
            'tipo': 'planta',
            'valor': valor,
            'descricao': descricao
        }).execute()

        # Atualiza saldo
        supabase.table('funcionarios').update({
            'saldo': func['saldo'] + Decimal(str(valor))
        }).eq('id', func['id']).execute()

        embed = discord.Embed(
            title="💵 Pagamento Registrado!",
            color=discord.Color.green()
        )
        embed.add_field(name="Funcionário", value=membro.mention, inline=True)
        embed.add_field(name="Valor", value=f"R$ {valor:.2f}", inline=True)
        embed.add_field(name="Descrição", value=descricao, inline=False)
        embed.set_footer(text=f"Registrado por: {ctx.author.display_name}")

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Erro ao registrar pagamento: {e}")


@bot.command(name='pagaranimais', aliases=['pa'])
@commands.has_permissions(manage_messages=True)
async def pagar_animais(ctx, membro: discord.Member):
    """
    Calcula e processa pagamento de animais do funcionário.
    Uso: !pagaranimais @pessoa
    """
    try:
        func = await get_funcionario_by_discord_id(str(membro.id))
        if not func:
            await ctx.send(f"❌ {membro.display_name} não está cadastrado.")
            return

        # Busca estoque com preços
        estoque = await get_estoque_funcionario(func['id'])

        if not estoque:
            await ctx.send(f"❌ {membro.display_name} não tem animais no estoque.")
            return

        # Calcula valores
        total = Decimal('0')
        detalhes = []

        for item in estoque:
            qtd = item['quantidade']
            valor_unit = Decimal(str(item['precos_config']['valor_pagamento_funcionario']))
            valor_total = qtd * valor_unit
            total += valor_total

            detalhes.append({
                'nome': item['precos_config']['nome_real'],
                'sigla': item['sigla_animal'].upper(),
                'quantidade': qtd,
                'valor_unit': valor_unit,
                'valor_total': valor_total
            })

        # Mostra preview e pede confirmação
        embed = discord.Embed(
            title=f"💰 Pagamento de Animais - {membro.display_name}",
            description="Confirme o pagamento respondendo com `sim`",
            color=discord.Color.gold()
        )

        for d in detalhes:
            embed.add_field(
                name=f"{d['nome']} ({d['sigla']})",
                value=f"{d['quantidade']}x R$ {d['valor_unit']:.2f} = **R$ {d['valor_total']:.2f}**",
                inline=False
            )

        embed.add_field(
            name="💵 TOTAL A PAGAR",
            value=f"**R$ {total:.2f}**",
            inline=False
        )

        await ctx.send(embed=embed)

        # Aguarda confirmação
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == 'sim'

        try:
            await bot.wait_for('message', timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("❌ Tempo esgotado. Pagamento cancelado.")
            return

        # Processa pagamento
        # Registra no histórico
        supabase.table('historico_pagamentos').insert({
            'funcionario_id': func['id'],
            'tipo': 'animal',
            'valor': float(total),
            'descricao': f"Pagamento automático - {len(detalhes)} tipos de animais"
        }).execute()

        # Atualiza saldo
        supabase.table('funcionarios').update({
            'saldo': float(Decimal(str(func['saldo'])) + total)
        }).eq('id', func['id']).execute()

        # Zera estoque
        supabase.table('estoque_animais').delete().eq('funcionario_id', func['id']).execute()

        embed = discord.Embed(
            title="✅ Pagamento Processado!",
            description=f"{membro.mention} recebeu **R$ {total:.2f}**",
            color=discord.Color.green()
        )
        embed.set_footer(text="Estoque zerado automaticamente")

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Erro ao processar pagamento: {e}")


@bot.command(name='verificarcaixa', aliases=['caixa', 'financeiro'])
@commands.has_permissions(manage_messages=True)
async def verificar_caixa(ctx):
    """
    Relatório financeiro global da fazenda.
    Uso: !verificarcaixa
    """
    try:
        # Busca todos os funcionários com saldo e estoque
        funcionarios = supabase.table('funcionarios').select('*').eq('ativo', True).execute()

        total_saldos = Decimal('0')
        total_estoque = Decimal('0')

        embed = discord.Embed(
            title="📊 Relatório Financeiro da Fazenda",
            color=discord.Color.gold()
        )

        detalhes = []

        for func in funcionarios.data:
            saldo = Decimal(str(func['saldo']))
            total_saldos += saldo

            # Calcula valor do estoque
            estoque = await get_estoque_funcionario(func['id'])
            valor_estoque = Decimal('0')

            for item in estoque:
                qtd = item['quantidade']
                valor = Decimal(str(item['precos_config']['valor_pagamento_funcionario']))
                valor_estoque += qtd * valor

            total_estoque += valor_estoque

            if saldo > 0 or valor_estoque > 0:
                detalhes.append({
                    'nome': func['nome'],
                    'saldo': saldo,
                    'estoque': valor_estoque
                })

        # Mostra top funcionários
        for d in sorted(detalhes, key=lambda x: x['saldo'] + x['estoque'], reverse=True)[:10]:
            embed.add_field(
                name=d['nome'],
                value=f"Saldo: R$ {d['saldo']:.2f}\nEstoque: R$ {d['estoque']:.2f}",
                inline=True
            )

        embed.add_field(
            name="💰 Total Saldos (já pagos)",
            value=f"**R$ {total_saldos:.2f}**",
            inline=False
        )

        embed.add_field(
            name="📦 Total em Estoque (a pagar)",
            value=f"**R$ {total_estoque:.2f}**",
            inline=False
        )

        embed.add_field(
            name="📈 DÍVIDA TOTAL DA FAZENDA",
            value=f"**R$ {total_saldos + total_estoque:.2f}**",
            inline=False
        )

        embed.set_footer(text=f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Erro ao gerar relatório: {e}")


# ============================================
# COMANDO DE AJUDA PERSONALIZADO
# ============================================

@bot.command(name='help', aliases=['ajuda', 'comandos'])
async def ajuda(ctx):
    """Mostra todos os comandos disponíveis."""
    embed = discord.Embed(
        title="🌾 Bot Fazendeiro - Comandos",
        description="Sistema de gerenciamento da fazenda",
        color=discord.Color.green()
    )

    embed.add_field(
        name="📋 Gestão de Servidor",
        value="""
`!bemvindo @pessoa` - Cria canal privado
`!limpar [qtd]` - Apaga mensagens
        """,
        inline=False
    )

    embed.add_field(
        name="🐄 Sistema de Produção",
        value="""
`!add [sigla][qtd]` ou `!1` - Adiciona animais (ex: !add pa2 va5)
`!veranimais` ou `!2` - Ver seu estoque
`!deletaranimal [sigla][qtd]` ou `!3` - Remove animais
`!verestoque` - Estoque global da fazenda
        """,
        inline=False
    )

    embed.add_field(
        name="📦 Sistema de Encomendas",
        value="""
`!adicionarencomenda "Comprador" [itens]` - Criar encomenda (Admin)
`!addencomenda "Comprador" [itens]` ou `!4` - Criar encomenda
`!verencomendas` ou `!5` - Ver pendentes
`!entregarencomenda [ID]` - Entregar completa
`!entregarencomendaparcial [ID] [itens]` ou `!99` - Entrega parcial
        """,
        inline=False
    )

    embed.add_field(
        name="💰 Sistema Financeiro",
        value="""
`!pagarplanta @pessoa [valor]` ou `!pp` - Pagamento manual
`!pagaranimais @pessoa` ou `!pa` - Pagar animais do estoque
`!verificarcaixa` - Relatório financeiro global
        """,
        inline=False
    )

    embed.add_field(
        name="🐄 Siglas de Animais",
        value="""
**Porcos:** `pp` `pm` `pa` (Pequeno/Médio/Adulto)
**Vacas:** `vp` `vm` `va`
**Galinhas:** `gp` `gm` `ga`
**Cavalos:** `cp` `cm` `ca`
**Ovelhas:** `op` `om` `oa`
**Bois:** `bp` `bm` `ba`
**Cabras:** `cbp` `cbm` `cba`
**Coelhos:** `clp` `clm` `cla`
**Patos:** `ptp` `ptm` `pta`
**Perus:** `prp` `prm` `pra`
        """,
        inline=False
    )

    await ctx.send(embed=embed)


@bot.command(name='precos', aliases=['tabela', 'valores'])
async def ver_precos(ctx):
    """Mostra a tabela de preços dos animais."""
    try:
        precos = await get_precos_config()

        embed = discord.Embed(
            title="💵 Tabela de Preços",
            color=discord.Color.gold()
        )

        # Agrupa por tipo de animal
        categorias = {}
        for sigla, info in precos.items():
            nome_base = info['nome_real'].split()[0]  # Primeira palavra
            if nome_base not in categorias:
                categorias[nome_base] = []
            categorias[nome_base].append({
                'sigla': sigla.upper(),
                'nome': info['nome_real'],
                'venda': info['valor_venda'],
                'pagamento': info['valor_pagamento_funcionario']
            })

        for cat, itens in sorted(categorias.items()):
            valor = "\n".join(
                f"`{i['sigla']}` {i['nome']}\n  └ Venda: R$ {i['venda']:.2f} | Pago: R$ {i['pagamento']:.2f}"
                for i in sorted(itens, key=lambda x: x['pagamento'])
            )
            embed.add_field(name=f"🐄 {cat}", value=valor, inline=False)

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Erro ao buscar preços: {e}")


# ============================================
# INICIALIZAÇÃO DO BOT
# ============================================

if __name__ == '__main__':
    print("Iniciando Bot Fazendeiro...")
    bot.run(DISCORD_TOKEN)
