"""
Bot Multi-Empresa Downtown - Sistema de Gerenciamento Econômico para Roleplay (RDR2)
Desenvolvido para Discord com integração Supabase
Versão modularizada com Cogs
"""

import asyncio
import discord
from discord.ext import commands

from config import DISCORD_TOKEN, supabase
from database import get_empresas_by_guild, get_produtos_empresa, verificar_assinatura_servidor
from utils import selecionar_empresa
from logging_config import logger


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
    logger.info('============================================')
    logger.info('  Bot Multi-Empresa Downtown conectado!')
    logger.info(f'  Usuario: {bot.user.name}')
    logger.info(f'  Servidores: {len(bot.guilds)}')
    logger.info('============================================')
    
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


# ============================================
# VERIFICAÇÃO GLOBAL DE ASSINATURA
# ============================================

# Comandos liberados mesmo sem assinatura ativa
COMANDOS_LIVRES = {
    'help', 'ajuda', 'comandos',
    'assinatura', 'status', 'plano',
    'assinarpix', 'renovar', 'assinar', 'planos',
    'addtester', 'removetester', 'testers', 'simularpagamento', 'simpay', 'testpay',
    'validarpagamento'
}

# URL do frontend para checkout
CHECKOUT_URL = "http://localhost:3000/checkout"


def criar_embed_bloqueio():
    """Cria embed de bloqueio por falta de assinatura."""
    embed = discord.Embed(
        title="⚠️ Assinatura Necessária",
        description="Este servidor não possui uma assinatura ativa do Bot Fazendeiro.\n\n"
                    "Para continuar usando o bot, é necessário renovar a assinatura.",
        color=discord.Color.red()
    )
    embed.add_field(
        name="🔗 Link para Pagamento",
        value=f"[Clique aqui para assinar]({CHECKOUT_URL})",
        inline=False
    )
    embed.add_field(
        name="💳 Pagamento via PIX",
        value="Pagamentos são confirmados instantaneamente!",
        inline=False
    )
    embed.set_footer(text="Bot Fazendeiro | Sistema de Gestão Empresarial")
    return embed


@bot.check
async def verificar_assinatura_global(ctx):
    """Check global que verifica assinatura antes de cada comando."""
    # Comandos livres não precisam de verificação
    if ctx.command and ctx.command.name in COMANDOS_LIVRES:
        return True
    
    # Também libera aliases dos comandos
    if ctx.invoked_with and ctx.invoked_with.lower() in COMANDOS_LIVRES:
        return True
    
    # Se não tiver guild (DM), bloqueia
    if not ctx.guild:
        await ctx.send("❌ Este bot só funciona em servidores!")
        return False
    
    # Verifica assinatura do servidor
    assinatura = await verificar_assinatura_servidor(str(ctx.guild.id))
    
    if not assinatura.get('ativa'):
        embed = criar_embed_bloqueio()
        await ctx.send(embed=embed)
        return False
    
    return True


@bot.event
async def on_command_error(ctx, error):
    """Tratamento de erros."""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Argumento faltando: `{error.param.name}`")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Você não tem permissão.")
    elif isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.CheckFailure):
        # Já foi tratado pelo check (assinatura inativa)
        pass
    else:
        logger.error(f"Erro no comando: {error}")
        await ctx.send("❌ Ocorreu um erro.")


# ============================================
# COMANDO DE AJUDA
# ============================================

@bot.command(name='help', aliases=['ajuda', 'comandos'])
async def ajuda(ctx):
    """Mostra todos os comandos disponíveis categorizados."""
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
        description=f"**Empresa(s):** {nome_empresa}\nVersão: 2.5 (Produção & Encomendas)",
        color=discord.Color.blue()
    )

    # 1. GERAL
    embed.add_field(
        name="ℹ️ Geral",
        value="`!empresa` - Ver informações da empresa\n"
              "`!assinatura` - Ver status da assinatura\n"
              "`!planos` - Ver planos disponíveis\n"
              "`!assinarpix` - Gerar link de pagamento",
        inline=False
    )

    # 2. PRODUÇÃO
    embed.add_field(
        name="🏭 Produção & Encomendas",
        value="`!add [produto] [qtd]` - Adicionar ao estoque (Fabricar)\n"
              "`!estoque` - Ver seu estoque e saldo\n"
              "`!produtos` - Ver catálogo de códigos e produtos\n"
              "`!novaencomenda` - Criar nova encomenda (Menu ou Rápido)\n"
              "`!encomendas` - Ver encomendas pendentes\n"
              "`!entregar [ID]` - Entregar encomenda para cliente\n"
              "`!deletar [codigo]` - Jogar fora/remover do estoque\n"
              "`!verprecos` - Ver tabela de preços completa",
        inline=False
    )

    # 3. ADMINISTRAÇÃO
    embed.add_field(
        name="🛡️ Administração (Requer permissão)",
        value="`!configurar` - Configuração inicial da empresa\n"
              "`!novaempresa` - Adicionar outra empresa no servidor\n"
              "`!modopagamento` - Definir Produção (Acumulativo) ou Entrega (Comissão)\n"
              "`!configmin` / `!configmedio` / `!configmax` - Configurar preços auto\n"
              "`!configurarprecos` - Configurar preços manualmente\n"
              "`!comissao [%]` - Definir porcentagem de comissão (ex: 30%)\n"
              "`!usuarios` - Listar equipe cadastrada\n"
              "`!bemvindo @pessoa` - Criar cadastro e canal privado\n"
              "`!promover @pessoa` - Promover funcionário a Admin\n"
              "`!removeracesso @pessoa` - Remover acesso ao painel\n"
              "`!limpar [qtd]` - Limpar mensagens do chat",
        inline=False
    )

    # 4. FINANCEIRO
    embed.add_field(
        name="💰 Financeiro (Admin)",
        value="`!caixa` - Relatório financeiro geral (Saldos + Estoques)\n"
              "`!pagar @pessoa [valor]` - Pagamento avulso/bônus\n"
              "`!pagarestoque @pessoa` - Pagar comissão acumulada e zerar estoque",
        inline=False
    )

    embed.add_field(
        name="🌐 Painel Web",
        value="Gerencie tudo pelo painel web: [Clique Aqui](http://localhost:3000)",
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
        'cogs.financeiro',
        'cogs.assinatura'
    ]
    
    for cog in cogs:
        try:
            await bot.load_extension(cog)
            logger.info(f"  [OK] Cog carregada: {cog}")
        except Exception as e:
            logger.error(f"  [ERRO] Erro ao carregar {cog}: {e}")


# ============================================
# INICIALIZAÇÃO
# ============================================

async def main():
    """Função principal."""
    logger.info("Iniciando Bot Multi-Empresa Downtown...")
    logger.info("Carregando Cogs...")
    await load_cogs()
    
    # Run Bot Only (API must be run separately via uvicorn)
    await bot.start(DISCORD_TOKEN)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Handle manual stop gracefully
        pass

