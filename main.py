"""
Bot Multi-Empresa Downtown - Sistema de Gerenciamento Econômico para Roleplay (RDR2)
Desenvolvido para Discord com integração Supabase
Versão modularizada com Cogs
"""

import asyncio
import discord
from discord.ext import commands

from config import DISCORD_TOKEN, supabase
from database import get_empresas_by_guild, get_produtos_empresa
from utils import selecionar_empresa


# ============================================
# CONFIGURAÇÃO DO BOT
# ============================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)


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
# COMANDO DE AJUDA
# ============================================

@bot.command(name='help', aliases=['ajuda', 'comandos'])
async def ajuda(ctx):
    """Mostra todos os comandos."""
    guild_id = str(ctx.guild.id)
    empresas = await get_empresas_by_guild(guild_id)
    
    nome_empresa = "Não configurada"
    if empresas:
        if len(empresas) == 1:
            nome_empresa = empresas[0]['nome']
        else:
            nome_empresa = f"{len(empresas)} empresas configuradas"

    embed = discord.Embed(
        title="🏢 Bot Multi-Empresa Downtown",
        description=f"**Empresa(s):** {nome_empresa}\nVersão: 2.1 (Pagamentos & Admins)",
        color=discord.Color.green()
    )

    if not empresas:
        embed.add_field(
            name="⚙️ Configuração",
            value="`!configurar` - Configurar primeira empresa (Admin)",
            inline=False
        )
    else:
        embed.add_field(
            name="⚙️ Configuração Geral (Admin)",
            value="`!configurar` - Ver empresa\n`!novaempresa` - Adicionar empresa\n`!modopagamento` - Configurar Pagamento (Prod/Entrega/Estoque)\n`!limparcache` - Recarregar bot",
            inline=False
        )

        embed.add_field(
            name="💲 Config. de Preços (Admin)",
            value="`!configmin` - Preços MÍNIMOS\n`!configmedio` - Preços MÉDIOS\n`!configmax` - Preços MÁXIMOS\n`!configurarprecos` - Manual",
            inline=False
        )

        embed.add_field(
            name="👥 Gestão de Usuários (Admin)",
            value="`!bemvindo @pessoa` - Criar canal privado (Admin=admin-nome)\n`!usuarios` - Listar usuários frontend\n`!promover @pessoa` - Promover Admin\n`!removeracesso` - Remover acesso",
            inline=False
        )

        embed.add_field(
            name="📦 Produção (Funcionários)",
            value="`!add rotulo 100` ou `!add rotulo100` - Fabricar\n`!estoque` - Ver saldo e itens\n`!deletar codigo` - Jogar fora\n`!produtos` - Ver catálogo com códigos",
            inline=False
        )

        embed.add_field(
            name="📦 Encomendas",
            value='`!novaencomenda` - Criar venda\n`!encomendas` - Ver pendentes\n`!entregar [ID]` - Entregar e receber',
            inline=False
        )

        embed.add_field(
            name="💰 Financeiro (Admin)",
            value="`!pagar @pessoa [valor]` - Pagamento extra\n`!pagarestoque @pessoa` - Pagar e zerar estoque\n`!caixa` - Relatório financeiro",
            inline=False
        )

    embed.add_field(
        name="🌐 Painel Web",
        value="Gerencie tudo pelo painel web usando seu Discord!",
        inline=False
    )

    await ctx.send(embed=embed)


@bot.command(name='empresa', aliases=['info'])
async def info_empresa(ctx):
    """Mostra informações da empresa."""
    ctx.empresas_lista = await get_empresas_by_guild(str(ctx.guild.id))
    if not ctx.empresas_lista:
        await ctx.send("❌ Nenhuma empresa configurada.")
        return
        
    if len(ctx.empresas_lista) == 1:
        ctx.empresa = ctx.empresas_lista[0]
    else:
        ctx.empresa = await selecionar_empresa(ctx)
        
    empresa = ctx.empresa
    if not empresa:
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


# ============================================
# CARREGAMENTO DAS COGS
# ============================================

async def load_cogs():
    """Carrega todas as Cogs."""
    cogs = [
        'cogs.admin',
        'cogs.precos',
        'cogs.producao',
        'cogs.financeiro'
    ]
    
    for cog in cogs:
        try:
            await bot.load_extension(cog)
            print(f"  [OK] Cog carregada: {cog}")
        except Exception as e:
            print(f"  [ERRO] Erro ao carregar {cog}: {e}")


# ============================================
# INICIALIZAÇÃO
# ============================================

async def main():
    """Função principal."""
    print("Iniciando Bot Multi-Empresa Downtown...")
    print("Carregando Cogs...")
    await load_cogs()
    await bot.start(DISCORD_TOKEN)


if __name__ == '__main__':
    asyncio.run(main())
