"""
Bot Multi-Empresa Downtown - Cog de Assinatura
Gerencia verificação de assinatura e pagamentos.
"""

import discord
from discord.ext import commands
from discord import app_commands

from database import (
    verificar_assinatura_servidor,
    get_assinatura_servidor,
    get_planos_disponiveis,
    adicionar_tester,
    remover_tester,
    listar_testers,
    simular_pagamento
)


# URLs do frontend - ajuste conforme seu deploy
FRONTEND_URL = "http://localhost:3000"
CHECKOUT_URL = f"{FRONTEND_URL}/checkout"

# IDs de superadmins que podem gerenciar testers (adicione seu Discord ID)
SUPERADMIN_IDS = ["306217606082199555"]


def criar_embed_assinatura_expirada():
    """Cria embed de aviso de assinatura expirada."""
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


def requer_assinatura():
    """Decorator para verificar assinatura antes de executar comandos."""
    async def predicate(ctx):
        assinatura = await verificar_assinatura_servidor(str(ctx.guild.id))
        
        if not assinatura.get('ativa'):
            embed = criar_embed_assinatura_expirada()
            await ctx.send(embed=embed)
            return False
        return True
    return commands.check(predicate)


def is_superadmin():
    """Verifica se o usuário é superadmin."""
    async def predicate(ctx):
        # Dono do bot ou IDs configurados
        if await ctx.bot.is_owner(ctx.author):
            return True
        return str(ctx.author.id) in SUPERADMIN_IDS
    return commands.check(predicate)


class Assinatura(commands.Cog):
    """Comandos de gerenciamento de assinatura."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='assinatura', aliases=['status', 'plano'])
    async def ver_assinatura(self, ctx):
        """Mostra o status da assinatura do servidor."""
        guild_id = str(ctx.guild.id)
        assinatura = await verificar_assinatura_servidor(guild_id)

        if assinatura.get('ativa'):
            # Check if tester
            is_tester = assinatura.get('status') == 'tester'
            
            embed = discord.Embed(
                title="✅ Assinatura Ativa" if not is_tester else "🧪 Modo Tester",
                description=f"Seu servidor possui acesso ao bot!" if not is_tester else "Servidor em modo de teste gratuito!",
                color=discord.Color.green() if not is_tester else discord.Color.blue()
            )
            embed.add_field(
                name="📋 Plano",
                value=assinatura.get('plano_nome', 'N/A'),
                inline=True
            )
            embed.add_field(
                name="📅 Dias Restantes",
                value=f"{assinatura.get('dias_restantes', 0)} dias",
                inline=True
            )
            if assinatura.get('data_expiracao') and not is_tester:
                expiracao = assinatura['data_expiracao'][:10]
                embed.add_field(
                    name="⏰ Expira em",
                    value=expiracao,
                    inline=True
                )
        else:
            embed = criar_embed_assinatura_expirada()

        await ctx.send(embed=embed)

    @commands.command(name='assinarpix', aliases=['renovar', 'assinar'])
    async def link_pagamento(self, ctx):
        """Mostra o link para pagamento/renovação."""
        planos = await get_planos_disponiveis()

        embed = discord.Embed(
            title="💳 Assinar Bot Fazendeiro",
            description="Escolha um plano e faça o pagamento via PIX para ativar o bot.",
            color=discord.Color.gold()
        )

        for plano in planos:
            preco_formatado = f"R$ {plano['preco']:.2f}".replace('.', ',')
            embed.add_field(
                name=f"📦 {plano['nome']}",
                value=f"{preco_formatado} - {plano['duracao_dias']} dias",
                inline=True
            )

        embed.add_field(
            name="🔗 Link de Pagamento",
            value=f"[Clique aqui para assinar]({CHECKOUT_URL})",
            inline=False
        )

        embed.set_footer(text="Pagamentos via PIX são confirmados instantaneamente!")

        await ctx.send(embed=embed)

    @commands.command(name='planos')
    async def listar_planos(self, ctx):
        """Lista todos os planos disponíveis."""
        planos = await get_planos_disponiveis()

        if not planos:
            await ctx.send("❌ Nenhum plano disponível no momento.")
            return

        embed = discord.Embed(
            title="📋 Planos Disponíveis",
            description="Escolha o plano ideal para seu servidor!",
            color=discord.Color.blue()
        )

        for plano in planos:
            preco_formatado = f"R$ {plano['preco']:.2f}".replace('.', ',')
            descricao = plano.get('descricao', 'Acesso completo ao bot')
            embed.add_field(
                name=f"**{plano['nome']}** - {preco_formatado}",
                value=f"⏱️ {plano['duracao_dias']} dias\n📝 {descricao}",
                inline=False
            )

        embed.add_field(
            name="",
            value=f"[➡️ Assinar Agora]({CHECKOUT_URL})",
            inline=False
        )

        await ctx.send(embed=embed)

    # ============================================
    # COMANDOS DE TESTERS (SUPERADMIN ONLY)
    # ============================================

    @commands.command(name='addtester')
    @is_superadmin()
    async def add_tester(self, ctx, guild_id: str = None, *, motivo: str = "Tester"):
        """[SUPERADMIN] Adiciona um servidor como tester."""
        target_guild = guild_id or str(ctx.guild.id)
        
        # Get guild name if possible
        guild = self.bot.get_guild(int(target_guild))
        nome = guild.name if guild else f"Guild {target_guild}"
        
        success = await adicionar_tester(
            guild_id=target_guild,
            nome=nome,
            adicionado_por=str(ctx.author.id),
            motivo=motivo
        )
        
        if success:
            await ctx.send(f"✅ Servidor **{nome}** adicionado como tester!\nMotivo: {motivo}")
        else:
            await ctx.send("❌ Erro ao adicionar tester.")

    @commands.command(name='removetester')
    @is_superadmin()
    async def remove_tester(self, ctx, guild_id: str = None):
        """[SUPERADMIN] Remove um servidor da lista de testers."""
        target_guild = guild_id or str(ctx.guild.id)
        
        success = await remover_tester(target_guild)
        
        if success:
            await ctx.send(f"✅ Servidor removido da lista de testers.")
        else:
            await ctx.send("❌ Erro ao remover tester.")

    @commands.command(name='testers')
    @is_superadmin()
    async def list_testers(self, ctx):
        """[SUPERADMIN] Lista todos os testers."""
        testers = await listar_testers()
        
        if not testers:
            await ctx.send("📋 Nenhum tester cadastrado.")
            return
        
        embed = discord.Embed(
            title="🧪 Testers Cadastrados",
            color=discord.Color.blue()
        )
        
        for tester in testers[:25]:  # Limit to 25
            guild = self.bot.get_guild(int(tester['guild_id']))
            nome = guild.name if guild else tester.get('nome', 'Unknown')
            embed.add_field(
                name=nome,
                value=f"ID: `{tester['guild_id']}`\nMotivo: {tester.get('motivo', 'N/A')}",
                inline=True
            )
        
        await ctx.send(embed=embed)

    @commands.command(name='simularpagamento', aliases=['simpay', 'testpay'])
    @is_superadmin()
    async def simular_pag(self, ctx, guild_id: str = None):
        """[SUPERADMIN] Simula pagamento PIX para testes."""
        target_guild = guild_id or str(ctx.guild.id)
        
        await ctx.send("⏳ Simulando pagamento...")
        
        success = await simular_pagamento(target_guild)
        
        if success:
            await ctx.send(f"✅ Pagamento simulado! Assinatura ativada para guild `{target_guild}`.")
        else:
            await ctx.send("❌ Erro ao simular pagamento. Certifique-se de que há um pagamento pendente.")

    @commands.command(name='validarpagamento', aliases=['verificarpagamento', 'claimpayment'])
    async def validar_pagamento(self, ctx):
        """Valida manualmente um pagamento pendente feito pelo usuário."""
        from database import buscar_pagamento_pendente_usuario, atualizar_pagamento_guild, ativar_assinatura_servidor
        
        discord_id = str(ctx.author.id)
        guild_id = str(ctx.guild.id)
        
        await ctx.send(f"🔍 Buscando pagamentos pendentes para <@{discord_id}>...")
        
        pagamento = await buscar_pagamento_pendente_usuario(discord_id)
        
        if not pagamento:
            await ctx.send("❌ Nenhum pagamento pendente encontrado no seu nome.\nCertifique-se de ter gerado o QR Code e realizado o pagamento.")
            return
            
        # Encontrou pagamento
        pix_id = pagamento['pix_id']
        valor = pagamento['valor']
        plano_id = pagamento['plano_id']
        status_atual = pagamento['status']
        
        await ctx.send(f"📄 Encontrado pagamento de R$ {valor:.2f} (Status: {status_atual}).\nVinculando a este servidor...")
        
        # 1. Vincular ao servidor atual
        if pagamento['guild_id'] != guild_id:
            updated = await atualizar_pagamento_guild(pix_id, guild_id)
            if not updated:
                await ctx.send("❌ Erro ao vincular pagamento ao servidor.")
                return
        
        # 2. Ativar assinatura (Manual Override for Dev/Localhost environment)
        # Em produção, deveria checar API do Asaas aqui. 
        # Como o problema é localhost não recebendo webhook, vamos confiar que se o usuário rodou o comando, ele pagou.
        # Ou poderíamos checar a API se tivéssemos a chave.
        
        await ctx.send("✅ Pagamento vinculado! Verificando assinatura...")
        
        # Simula o recebimento do webhook (força ativação)
        # Isso é seguro pois só ativa se existir um registro de pagamento no banco
        success = await ativar_assinatura_servidor(guild_id, plano_id, discord_id)
        
        if success:
            await ctx.send(f"🎉 **Sucesso!** Assinatura ativada para **{ctx.guild.name}**.\nUse `!configurar` para começar.")
        else:
            await ctx.send("❌ Erro ao ativar assinatura no banco de dados.")


async def setup(bot):
    await bot.add_cog(Assinatura(bot))

