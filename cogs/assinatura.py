"""
Bot Multi-Empresa Downtown - Cog de Assinatura
Gerencia verificação de assinatura e pagamentos.
"""

import aiohttp
import discord
import os
from discord.ext import commands
from discord import app_commands

from database import (
    verificar_assinatura_servidor,
    get_assinatura_servidor,
    get_planos_disponiveis,
    adicionar_tester,
    remover_tester,
    listar_testers,
    simular_pagamento,
    buscar_pagamento_pendente_usuario,
    atualizar_pagamento_guild,
    ativar_assinatura_servidor
)
from config import FRONTEND_URL, CHECKOUT_URL, SUPERADMIN_IDS, ASAAS_API_KEY, ASAAS_API_URL, supabase


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
        """Valida manualmente um pagamento pendente ou pago, confirmando no Asaas."""
        try:
            discord_id = str(ctx.author.id)
            guild_id = str(ctx.guild.id)
            
            await ctx.send(f"🔍 Buscando transações recentes para <@{discord_id}>...")
            
            # Busca qualquer pagamento recente (pendente ou pago)
            pagamento = await buscar_pagamento_pendente_usuario(discord_id)
            
            if not pagamento:
                await ctx.send("❌ Nenhum registro de pagamento encontrado.\nCertifique-se de ter gerado o QR Code recentemente.")
                return
                
            pix_id = pagamento['pix_id']
            valor = pagamento.get('valor', 0)
            plano_id = pagamento.get('plano_id')
            status_db = pagamento.get('status')

            # Validação de segurança: garante que o pagamento pertence ao usuário
            if pagamento.get('discord_id') and pagamento['discord_id'] != discord_id:
                await ctx.send("❌ Este pagamento não pertence a você.")
                return

            # 1. Vincular ao servidor atual se necessário
            if pagamento['guild_id'] != guild_id and pagamento['guild_id'] == 'pending_activation':
                await ctx.send(f"🔗 Vinculando pagamento de R$ {valor} a este servidor...")
                updated = await atualizar_pagamento_guild(pix_id, guild_id)
                if not updated:
                    await ctx.send("❌ Erro ao vincular pagamento.")
                    return
            elif pagamento['guild_id'] != guild_id:
                await ctx.send(f"⚠️ Atenção: Este pagamento está vinculado a outro servidor (ID: {pagamento['guild_id']}).\nNão posso transferi-lo automaticamente.")
                return

            # 2. Verificação Real no Asaas
            # Se status já é 'pago' no banco, confiamos no banco (Webhook funcionou) e apenas ativamos a assinatura
            if status_db == 'pago':
                await ctx.send("✅ Pagamento já consta como confirmado no sistema. Ativando assinatura...")
                success = await ativar_assinatura_servidor(guild_id, plano_id, discord_id)
                if success:
                    await ctx.send(f"🎉 **Sucesso!** Assinatura ativa para **{ctx.guild.name}**.")
                else:
                    await ctx.send("❌ Erro ao ativar assinatura (Erro Interno).")
                return

            # Se 'pendente', consultamos a API do Asaas
            await ctx.send("🌐 Consultando Banco Central/Asaas para confirmação...")
            
            headers = {"access_token": ASAAS_API_KEY}
            
            if not ASAAS_API_KEY:
                await ctx.send("❌ API Key não configurada. Não é possível validar pagamento.")
                return
            else:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"{ASAAS_API_URL}/payments/{pix_id}", headers=headers) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                status_real = data.get('status')
                            else:
                                await ctx.send(f"❌ Erro de comunicação com o gateway de pagamento (Status {resp.status}).")
                                return
                except Exception as e:
                    await ctx.send(f"❌ Erro de conexão: {e}")
                    return

            # 3. Processa Resultado
            if status_real in ['RECEIVED', 'CONFIRMED']:
                await ctx.send("💸 Pagamento confirmado! Finalizando configuração...")
                
                await supabase.table('pagamentos_pix').update({'status': 'pago'}).eq('pix_id', pix_id).execute()
                
                success = await ativar_assinatura_servidor(guild_id, plano_id, discord_id)
                
                if success:
                    await ctx.send(f"🎉 **Parabéns!** O servidor **{ctx.guild.name}** está com assinatura ativa!\nUse `!configurar` para iniciar.")
                else:
                    await ctx.send("❌ Assinatura não pôde ser ativada no banco de dados.")
            elif status_real == 'PENDING':
                await ctx.send("⏳ O pagamento ainda está pendente no banco. Tente novamente em alguns segundos.")
            else:
                await ctx.send(f"❌ O status do pagamento é: {status_real}. Não foi possível ativar.")
        except ImportError as ie:
            await ctx.send(f"❌ Erro de configuração interna (Import): {ie}")
            from logging_config import logger
            logger.error(f"Erro no comando validarpagamento: {ie}")
        except Exception as e:
            await ctx.send(f"❌ Ocorreu um erro inesperado: {e}")
            from logging_config import logger
            logger.error(f"Erro no comando validarpagamento: {e}")


async def setup(bot):
    await bot.add_cog(Assinatura(bot))

