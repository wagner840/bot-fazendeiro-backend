"""
Bot Multi-Empresa Downtown - Cog Financeiro
Comandos para pagamentos e relatórios financeiros.
"""

import asyncio
from decimal import Decimal
import discord
from discord.ext import commands
from config import supabase
from database import (
    get_funcionario_by_discord_id,
    get_estoque_funcionario
)
from utils import empresa_configurada, selecionar_empresa
from ui_utils import create_success_embed, create_error_embed, create_warning_embed, handle_interaction_error

class PagamentoConfirmView(discord.ui.View):
    def __init__(self, ctx, func_db: dict, membro: discord.Member, valor: float, descricao: str):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.func_db = func_db
        self.membro = membro
        self.valor = valor
        self.descricao = descricao
        self.value = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Apenas quem iniciou o comando pode usar os botões.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirmar Pagamento", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()
        
        # Lógica de Pagamento
        try:
            # 1. Insert History
            supabase.table('historico_pagamentos').insert({
                'funcionario_id': self.func_db['id'],
                'tipo': 'manual',
                'valor': self.valor,
                'descricao': self.descricao
            }).execute()
            
            # 2. Update Balance
            novo_saldo = float(Decimal(str(self.func_db['saldo'])) + Decimal(str(self.valor)))
            
            supabase.table('funcionarios').update({
                'saldo': novo_saldo
            }).eq('id', self.func_db['id']).execute()
            
            # 3. Success Feedback
            embed = create_success_embed("Pagamento Realizado!")
            embed.add_field(name="Funcionário", value=self.membro.mention)
            embed.add_field(name="Valor", value=f"R$ {self.valor:.2f}")
            embed.add_field(name="Descrição", value=self.descricao)
            embed.set_footer(text=f"Novo Saldo: R$ {novo_saldo:.2f}")
            
            await interaction.response.edit_message(embed=embed, view=None)
            
        except Exception as e:
            await handle_interaction_error(interaction, e)

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.red, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        embed = create_warning_embed("Cancelado", "Pagamento cancelado pelo administrador.")
        await interaction.response.edit_message(embed=embed, view=None)


class FinanceiroCog(commands.Cog, name="Financeiro"):
    """Comandos de pagamentos e relatórios financeiros."""

    def __init__(self, bot):
        self.bot = bot

    # ============================================
    # PAGAR FUNCIONÁRIO
    # ============================================

    @commands.hybrid_command(name='pagar', aliases=['pagamento'], description="Realiza pagamento manual a um funcionário.")
    @commands.has_permissions(manage_messages=True)
    @empresa_configurada()
    async def pagar_funcionario(self, ctx, membro: discord.Member, valor: float, *, descricao: str = "Pagamento"):
        """Registra pagamento manual com confirmação."""
        empresa = await selecionar_empresa(ctx)
        if not empresa: return
        
        func = await get_funcionario_by_discord_id(str(membro.id))
        if not func:
            await ctx.send(embed=create_error_embed("Erro", f"{membro.display_name} não cadastrado."), ephemeral=True)
            return
        
        if valor <= 0:
            await ctx.send(embed=create_error_embed("Erro", "Valor deve ser positivo."), ephemeral=True)
            return
        
        # Envia View de Confirmação
        view = PagamentoConfirmView(ctx, func, membro, valor, descricao)
        embed = create_warning_embed("Confirmar Pagamento?", f"Você está prestes a pagar **R$ {valor:.2f}** para {membro.mention}.")
        embed.add_field(name="Motivo", value=descricao)
        
        await ctx.send(embed=embed, view=view)

    # ============================================
    # PAGAR ESTOQUE
    # ============================================

    @commands.command(name='pagarestoque', aliases=['pe'])
    @commands.has_permissions(manage_messages=True)
    @empresa_configurada()
    async def pagar_estoque(self, ctx, membro: discord.Member):
        """Paga e zera estoque do funcionário (+ comissões de vendas)."""
        empresa = await selecionar_empresa(ctx)
        if not empresa:
            return
        
        func = await get_funcionario_by_discord_id(str(membro.id))
        if not func:
            await ctx.send(f"❌ {membro.display_name} não cadastrado.")
            return
        
        # 1. Calcula valor do Estoque Atual
        estoque = await get_estoque_funcionario(func['id'], empresa['id'])
        valor_estoque = Decimal('0')
        if estoque:
            for item in estoque:
                valor_estoque += Decimal(str(item['preco_funcionario'])) * item['quantidade']
        
        # 2. Calcula Comissões Pendentes (Vendas/Entregas)
        comissoes = supabase.table('transacoes').select('*').eq('empresa_id', empresa['id']).eq('funcionario_id', func['id']).eq('tipo', 'comissao_pendente').execute()
        valor_pendente = Decimal('0')
        pendentes_ids = []
        if comissoes.data:
            for c in comissoes.data:
                valor_pendente += Decimal(str(c['valor']))
                pendentes_ids.append(c['id'])
        
        total_pagar = valor_estoque + valor_pendente
        
        if total_pagar <= 0:
            await ctx.send(f"❌ {membro.display_name} não tem valores a receber (Estoque vazio e sem comissões pendentes).")
            return
        
        # Confirmação
        embed = discord.Embed(
            title=f"💰 Pagamento - {membro.display_name}",
            description="Confirme com `sim` para realizar o pagamento e zerar pendências.",
            color=discord.Color.gold()
        )
        
        embed.add_field(name="📦 Valor em Estoque", value=f"R$ {valor_estoque:.2f}", inline=True)
        embed.add_field(name="📄 Comissões Pendentes", value=f"R$ {valor_pendente:.2f}", inline=True)
        embed.add_field(name="💵 TOTAL A PAGAR", value=f"**R$ {total_pagar:.2f}**", inline=False)
        
        if estoque:
            detalhes_estoque = "\n".join([f"• {i['nome']} ({i['quantidade']}x)" for i in estoque[:5]])
            if len(estoque) > 5: detalhes_estoque += "\n..."
            embed.add_field(name="Detalhes Estoque", value=detalhes_estoque, inline=False)
            
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['sim', 's']
        
        try:
            await self.bot.wait_for('message', timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("❌ Cancelado.")
            return
        
        # Processa Pagamento
        
        # 1. Registra Histórico
        supabase.table('historico_pagamentos').insert({
            'funcionario_id': func['id'],
            'tipo': 'estoque_acumulado',
            'valor': float(total_pagar),
            'descricao': f'Pagamento Acumulado (Estoque: R${valor_estoque:.2f} + Vendas: R${valor_pendente:.2f})'
        }).execute()
        
        # 2. Atualiza Saldo do Funcionário
        supabase.table('funcionarios').update({
            'saldo': float(Decimal(str(func['saldo'])) + total_pagar)
        }).eq('id', func['id']).execute()
        
        # 3. Limpa Estoque
        if estoque:
            supabase.table('estoque_produtos').delete().eq('funcionario_id', func['id']).eq('empresa_id', empresa['id']).execute()
            
        # 4. Atualiza Comissões Pendentes para Pagas
        if pendentes_ids:
            supabase.table('transacoes').update({'tipo': 'comissao_paga'}).in_('id', pendentes_ids).execute()
        
        await ctx.send(f"✅ {membro.mention} recebeu **R$ {total_pagar:.2f}**! Estoque zerado e comissões pagas.")

    # ============================================
    # CAIXA / RELATÓRIO FINANCEIRO
    # ============================================

    @commands.command(name='caixa', aliases=['financeiro'])
    @commands.has_permissions(manage_messages=True)
    @empresa_configurada()
    async def verificar_caixa(self, ctx):
        """Relatório financeiro."""
        empresa = await selecionar_empresa(ctx)
        if not empresa:
            return
        
        funcionarios = supabase.table('funcionarios').select('*').eq('empresa_id', empresa['id']).eq('ativo', True).execute()
        
        total_saldos = Decimal('0')
        total_estoque = Decimal('0')
        detalhes = []
        
        if funcionarios.data:
            for func in funcionarios.data:
                saldo = Decimal(str(func['saldo']))
                total_saldos += saldo
                
                estoque = await get_estoque_funcionario(func['id'], empresa['id'])
                valor_estoque = Decimal('0')
                if estoque:
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


async def setup(bot):
    await bot.add_cog(FinanceiroCog(bot))
