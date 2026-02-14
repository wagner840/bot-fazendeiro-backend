"""
Bot Fazendeiro - Sistema de Gerenciamento Econômico Multi-Servidor para Roleplay (RDR2)
Desenvolvido para Discord com integração Supabase
Versão modularizada com Cogs
"""

import asyncio
import discord
from discord.ext import commands

from config import DISCORD_TOKEN, CHECKOUT_URL, supabase, init_supabase
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
    logger.info('  Bot Fazendeiro conectado!')
    logger.info(f'  Usuario: {bot.user.name}')
    logger.info(f'  Servidores: {len(bot.guilds)}')
    logger.info('============================================')

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Bot Fazendeiro | !help"
        )
    )


class SetupWizardView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="⚙️ Iniciar Configuração", style=discord.ButtonStyle.green, custom_id="setup_start")
    async def start_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Envia uma mensagem instruindo o usuário a usar o comando ou trigga manualmente
        # Como o bot usa hybrid commands, podemos sugerir o uso do slash command /configurar
        await interaction.response.send_message(
            "🚀 Excelente! Por favor, use o comando `/configurar` para começarmos a criar sua primeira empresa.",
            ephemeral=True
        )

@bot.event
async def on_guild_join(guild):
    """Quando bot entra em novo servidor."""
    canal = guild.system_channel or guild.text_channels[0]

    embed = discord.Embed(
        title="🏢 Bem-vindo ao Bot Fazendeiro!",
        description=(
            "Obrigado por me adicionar! Sou o sistema definitivo de gestão para o seu servidor.\n\n"
            "**Como funciona a Isolação Multi-Empresa?**\n"
            "• Cada empresa terá sua própria categoria e canais exclusivos.\n"
            "• Funcionários terão canais privados organizados por empresa.\n"
            "• Comandos em canais de empresa detectam qual empresa você está operando.\n\n"
            "**Pronto para começar?**\n"
            "Clique no botão abaixo para configurar sua primeira empresa."
        ),
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)
    embed.set_footer(text="Bot Fazendeiro | Advanced Management Solutions")

    view = SetupWizardView()
    await canal.send(embed=embed, view=view)


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

def criar_embed_bloqueio(assinatura: dict = None):
    """Cria embed de bloqueio por falta de assinatura."""
    is_trial_expired = assinatura and assinatura.get('tipo') == 'trial'

    if is_trial_expired:
        embed = create_error_embed(
            "Período de Teste Expirado",
            "Seu período de teste gratuito de 3 dias acabou. Assine agora para continuar usando o Bot Fazendeiro!"
        )
    else:
        embed = create_error_embed(
            "Assinatura Necessária",
            "Este servidor não possui uma assinatura ativa."
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
        embed = criar_embed_bloqueio(assinatura)
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

from ui_utils import BaseMenuView, EMOJI_INFO, EMOJI_SUCCESS, EMOJI_LOADING

class HelpSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Visão Geral", value="geral", emoji="ℹ️", description="Comandos básicos e navegação"),
            discord.SelectOption(label="Produção", value="producao", emoji="🏭", description="Fabricar, estoque e catálogo"),
            discord.SelectOption(label="Encomendas", value="encomendas", emoji="📦", description="Pedidos e entregas"),
            discord.SelectOption(label="Financeiro", value="financeiro", emoji="💰", description="Pagamentos e relatórios"),
            discord.SelectOption(label="Preços", value="precos", emoji="💲", description="Tabela de preços e comissões"),
            discord.SelectOption(label="Administração", value="admin", emoji="🛡️", description="Empresas, equipe e config"),
            discord.SelectOption(label="Assinatura", value="assinatura", emoji="🔐", description="Planos e pagamento")
        ]
        super().__init__(placeholder="Escolha uma categoria...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        embed = discord.Embed(color=discord.Color.blue())

        if val == "geral":
            embed.title = "ℹ️ Visão Geral"
            embed.description = (
                "**Informações:**\n"
                "`!help` - Abre este menu de ajuda\n"
                "`!empresa` - Mostra dados da empresa ativa\n"
                "`!empresas` - Lista todas as empresas do servidor\n"
                "\n**Navegação:**\n"
                "Use o menu abaixo para explorar cada categoria.\n"
                "Comandos com `/` também funcionam com `!`"
            )

        elif val == "producao":
            embed.title = "🏭 Produção & Estoque"
            embed.description = (
                "**Fabricação:**\n"
                "`/produzir` - Registrar produção de itens\n"
                "\n**Estoque:**\n"
                "`/estoque` - Ver seu inventário pessoal\n"
                "`!estoque @user` - Ver estoque de outro funcionário\n"
                "`!estoqueglobal` - Ver estoque total da empresa\n"
                "`!deletar` - Remover itens do seu estoque\n"
                "\n**Catálogo:**\n"
                "`!produtos` - Lista todos os produtos com códigos"
            )

        elif val == "encomendas":
            embed.title = "📦 Encomendas & Entregas"
            embed.description = (
                "**Criar Pedido:**\n"
                "`/encomenda` - Abre wizard para nova encomenda\n"
                "\n**Gerenciar:**\n"
                "`!encomendas` - Lista pedidos pendentes\n"
                "`!entregar` - Finaliza entrega (abre seletor)\n"
                "`!entregar <id>` - Entrega encomenda específica\n"
                "\n*Ao entregar, o estoque é debitado e a comissão calculada automaticamente.*"
            )

        elif val == "financeiro":
            embed.title = "💰 Financeiro"
            embed.description = (
                "**Pagamentos:** *(Requer Admin)*\n"
                "`/pagar` - Pagamento manual a funcionário\n"
                "`/pagar @user 100 motivo` - Pagamento direto\n"
                "`!pagarestoque @user` - Paga e zera estoque acumulado\n"
                "\n**Relatórios:**\n"
                "`!caixa` - Fluxo de caixa e saldos\n"
                "\n*Pagamentos geram registro de transação automático.*"
            )

        elif val == "precos":
            embed.title = "💲 Preços & Comissões"
            embed.description = (
                "**Configurar Preços:** *(Requer Admin)*\n"
                "`!configurarprecos` - Editor interativo por produto\n"
                "\n**Config Rápida (todos produtos):** *(Requer Admin)*\n"
                "`!configmin` - Preço mínimo + 25% comissão\n"
                "`!configmedio` - Preço médio + 25% comissão\n"
                "`!configmax` - Preço máximo + 25% comissão\n"
                "*Configura automaticamente TODOS os produtos da empresa com o preço de referência selecionado.*\n"
                "\n**Comissão:** *(Requer Admin)*\n"
                "`!comissao` - Define % de repasse (menu)\n"
                "`!comissao 25` - Define 25% direto\n"
                "\n**Visualizar:**\n"
                "`!verprecos` - Tabela completa de preços\n"
                "`!verprecos categoria` - Filtrar por categoria"
            )

        elif val == "admin":
            embed.title = "🛡️ Administração"
            embed.description = (
                "**Setup Inicial:** *(Requer Admin)*\n"
                "`/configurar` - Wizard de configuração\n"
                "`/novaempresa` - Adicionar nova empresa\n"
                "`!modopagamento` - Alternar Produção/Entrega\n"
                "\n**Equipe:** *(Requer Admin)*\n"
                "`/bemvindo` - Cadastrar novo funcionário\n"
                "`/bemvindo @user` - Cadastrar usuário específico\n"
                "`!usuarios` - Listar acessos ao portal\n"
                "`!promover @user` - Promover a Admin\n"
                "`!removeracesso @user` - Remover acesso\n"
                "\n**Utilitários:**\n"
                "`!limparcache` - Recarregar dados do banco\n"
                "`!limpar [n]` - Apagar n mensagens (max 100)\n"
                "`!sync` - Sincronizar comandos slash"
            )

        elif val == "assinatura":
            embed.title = "🔐 Assinatura & Pagamento"
            embed.description = (
                "**Status:**\n"
                "`!assinatura` - Ver status atual do servidor\n"
                "\n**Assinar/Renovar:**\n"
                "`!planos` - Ver planos disponíveis\n"
                "`!assinarpix` - Gerar QR Code PIX\n"
                "`!validarpagamento` - Confirmar pagamento manual\n"
                "\n*Mantenha a assinatura ativa para usar o bot.*"
            )

        embed.set_footer(text="Use !help para voltar ao menu principal")
        await interaction.response.edit_message(embed=embed)

class HelpMenuView(BaseMenuView):
    def __init__(self, user_id):
        super().__init__(user_id=user_id)
        self.add_item(HelpSelect())
        self.add_item(discord.ui.Button(label="Painel Web", url="http://fazendabot.einsof7.com/dashboard/", row=1))

@bot.command(name='help', aliases=['ajuda', 'comandos'])
async def ajuda(ctx):
    """Abre o menu interativo de ajuda."""
    embed = discord.Embed(
        title="🏢 Central de Ajuda - Bot Fazendeiro",
        description="Selecione uma categoria abaixo para ver os comandos.",
        color=discord.Color.blue()
    )
    view = HelpMenuView(user_id=ctx.author.id)
    await ctx.send(embed=embed, view=view)


@bot.command(name='sync')
@commands.has_permissions(administrator=True)
async def sync(ctx, guild_id: int = None):
    """Sincroniza slash commands (Atual: !sync | Global: !sync global)."""
    if guild_id == "global":
        msg = await ctx.send(f"{EMOJI_LOADING} Sincronizando GLOBALMENTE (pode demorar)...")
        try:
            synced = await bot.tree.sync()
            await msg.edit(content=f"{EMOJI_SUCCESS} Globais: {len(synced)} comandos sincronizados!")
        except Exception as e:
            await msg.edit(content=f"❌ Erro Global: {e}")
    else:
        # Sync to current guild (Instant)
        guild = ctx.guild
        msg = await ctx.send(f"{EMOJI_LOADING} Sincronizando neste servidor ({guild.name})...")
        try:
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            await msg.edit(content=f"{EMOJI_SUCCESS} Sincronizados {len(synced)} comandos para este servidor!")
        except Exception as e:
            await msg.edit(content=f"❌ Erro Local: {e}")


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
    funcionarios = await supabase.table('funcionarios').select('id').eq('empresa_id', empresa['id']).execute()

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
    logger.info("Iniciando Bot Fazendeiro...")

    # Inicializa Supabase async client
    await init_supabase()
    logger.info("  [OK] Supabase async client inicializado.")

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
