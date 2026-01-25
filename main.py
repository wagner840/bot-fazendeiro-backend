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
from ui_utils import create_error_embed
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
    
    # Sync Slash Commands
    try:
        synced = await bot.tree.sync()
        logger.info(f"  [SYNC] {len(synced)} slash commands sincronizados.")
    except Exception as e:
        logger.error(f"  [ERRO] Falha ao sincronizar commands: {e}")
    
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
    embed = create_error_embed("Assinatura Necessária", "Este servidor não possui uma assinatura ativa.")
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
        await ctx.send(embed=create_error_embed("Erro", f"Argumento faltando: `{error.param.name}`"))
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=create_error_embed("Permissão Negada", "Você não tem permissão para usar este comando."))
    elif isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.CheckFailure):
        # Já foi tratado pelo check (assinatura inativa)
        pass
    else:
        logger.error(f"Erro no comando: {error}")
        await ctx.send(embed=create_error_embed("Erro Inesperado", "Ocorreu um erro ao processar o comando."))


# ============================================
# COMANDO DE AJUDA
# ============================================


# ============================================
# INTERACTIVE HELP SYSTEM
# ============================================

from ui_utils import BaseMenuView, EMOJI_INFO, EMOJI_SUCCESS

class HelpSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Visão Geral", value="geral", emoji="ℹ️", description="Comandos básicos"),
            discord.SelectOption(label="Produção & Encomendas", value="producao", emoji="🏭", description="Fábrica, Estoque e Vendas"),
            discord.SelectOption(label="Financeiro", value="financeiro", emoji="💰", description="Pagamentos e Caixa"),
            discord.SelectOption(label="Administração", value="admin", emoji="🛡️", description="Empresas e Equipe"),
            discord.SelectOption(label="Preços & Comissão", value="precos", emoji="💲", description="Configuração de Valores"),
            discord.SelectOption(label="Assinatura", value="assinatura", emoji="🔐", description="Planos e Status")
        ]
        super().__init__(placeholder="Escolha uma categoria...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        embed = discord.Embed(color=discord.Color.blue())
        
        if val == "geral":
            embed.title = "ℹ️ Visão Geral"
            embed.description = (
                "**Comandos Básicos:**\n"
                "`!empresa` - Ver dados da empresa ativa\n"
                "`!help` - Abrir este menu\n"
                "\n**Para onde ir?**\n"
                "Use o menu abaixo para explorar funcionalidades específicas."
            )
        elif val == "producao":
            embed.title = "🏭 Produção & Encomendas"
            embed.description = (
                "**Menu Principal:** `/produzir`\n"
                "*Gerencie toda a fabricação aqui.*\n\n"
                "**Vendas:** `/encomenda`\n"
                "*Crie pedidos para clientes.*\n\n"
                "**Outros:**\n"
                "`!estoque` - Seu inventário pessoal\n"
                "`!produtos` - Catálogo de referência\n"
                "`!entregar [id]` - Finalizar entrega\n"
                "`!deletar [cod]` - Descartar item"
            )
        elif val == "financeiro":
            embed.title = "💰 Financeiro"
            embed.description = (
                "**Pagamentos:** `/pagar`\n"
                "*Wizard seguro para pagar funcionários.*\n\n"
                "**Fluxo de Caixa:**\n"
                "`!caixa` - Ver entradas e saídas\n"
                "`!pagarestoque` - Pagar acumulado de produção"
            )
        elif val == "admin":
            embed.title = "🛡️ Administração"
            embed.description = (
                "**Configuração:**\n"
                "`/novaempresa` - Criar nova empresa\n"
                "`!configurar` - Setup inicial\n"
                "`!modopagamento` - Mudar modo (Produção/Entrega)\n\n"
                "**Equipe:**\n"
                "`!usuarios` - Ver lista\n"
                "`!bemvindo` - Adicionar funcionário\n"
                "`!promover` - Dar cargo de Admin"
            )
        elif val == "precos":
            embed.title = "💲 Preços & Comissão"
            embed.description = (
                "**Preços:** `!configurarprecos`\n"
                "*Define valor de venda e pagamento.*\n\n"
                "**Comissão:** `!comissao`\n"
                "*Define % global de repasse.*\n\n"
                "**Tabelas:**\n"
                "`!verprecos` - Ver tabela atual"
            )
        elif val == "assinatura":
            embed.title = "🔐 Assinatura SaaS"
            embed.description = (
                "**Status:** `!assinatura`\n"
                "**Assinar:** `!assinarpix` ou `!planos`\n"
                "*Mantenha seu servidor ativo para continuar usando o bot.*"
            )

        await interaction.response.edit_message(embed=embed)

class HelpMenuView(BaseMenuView):
    def __init__(self, user_id):
        super().__init__(user_id=user_id)
        self.add_item(HelpSelect())
        self.add_item(discord.ui.Button(label="Painel Web", url="http://localhost:3000", row=1))

@bot.command(name='help', aliases=['ajuda', 'comandos'])
async def ajuda(ctx):
    """Abre o menu interativo de ajuda."""
    embed = discord.Embed(
        title="🏢 Central de Ajuda Downtown",
        description="Selecione uma categoria abaixo para ver os comandos.",
        color=discord.Color.blue()
    )
    view = HelpMenuView(user_id=ctx.author.id)
    await ctx.send(embed=embed, view=view)


@bot.command(name='sync')
@commands.has_permissions(administrator=True)
async def sync(ctx):
    """Sincroniza os slash commands manualmente."""
    msg = await ctx.send(f"{EMOJI_LOADING} Sincronizando comandos...")
    try:
        synced = await bot.tree.sync()
        await msg.edit(content=f"{EMOJI_SUCCESS} {len(synced)} comandos sincronizados!")
    except Exception as e:
        await msg.edit(content=f"❌ Erro ao sincronizar: {e}")



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

