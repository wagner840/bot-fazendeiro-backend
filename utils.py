"""
Bot Multi-Empresa Downtown - Utilitários
Decorators, helpers e funções auxiliares.
"""

import discord
from discord.ext import commands
from typing import Optional, Dict, List
from config import PRODUTO_REGEX
from database import get_empresas_by_guild


# ============================================
# DECORATOR - VERIFICAR EMPRESA CONFIGURADA
# ============================================

def empresa_configurada():
    """Decorator que verifica se a empresa está configurada e associa ao contexto.
    Agora detecta automaticamente a empresa baseada no Canal ou Categoria.
    """
    async def predicate(ctx):
        guild_id = str(ctx.guild.id)
        channel_id = str(ctx.channel.id)
        category_id = str(ctx.channel.category.id) if ctx.channel.category else None
        
        empresas = await get_empresas_by_guild(guild_id)
        
        if not empresas:
            await ctx.send("❌ Nenhuma empresa configurada neste servidor. Use `/configurar`.")
            return False

        # 1. Busca exata pelo Canal ou Categoria
        empresa_alvo = None
        for emp in empresas:
            if emp.get('canal_principal_id') == channel_id or \
               emp.get('categoria_id') == category_id:
                empresa_alvo = emp
                break
        
        if empresa_alvo:
            ctx.empresa = empresa_alvo
            ctx.empresas_lista = [empresa_alvo]
            return True

        # 2. Se não estiver em um canal próprio de empresa:
        # Se for comando administrativo (como configurar), permite seguir para seleção
        if len(empresas) == 1:
            ctx.empresa = empresas[0]
            ctx.empresas_lista = empresas
            return True
        else:
            # Caso de múltiplas empresas e canal neutro
            # Vamos permitir que o selecionar_empresa lide com isso
            ctx.empresa = None
            ctx.empresas_lista = empresas
            return True

    return commands.check(predicate)


# ============================================
# HELPER - SELEÇÃO DE EMPRESA (MULTI-EMPRESA)
# ============================================

async def selecionar_empresa(ctx) -> Optional[Dict]:
    """
    Se houver uma única empresa, retorna ela.
    Se houver múltiplas, mostra menu para o usuário escolher.
    """
    if ctx.empresa:
        return ctx.empresa
    
    empresas = ctx.empresas_lista
    
    if not empresas:
        await ctx.send("❌ Nenhuma empresa encontrada.")
        return None
    
    if len(empresas) == 1:
        return empresas[0]
    
    # Múltiplas empresas - mostra menu
    embed = discord.Embed(
        title="🏢 Selecione a Empresa",
        description="Digite o número da empresa:",
        color=discord.Color.blue()
    )
    
    for i, emp in enumerate(empresas, 1):
        tipo = emp.get('tipos_empresa', {}).get('nome', 'Desconhecido')
        embed.add_field(
            name=f"{i}. {emp['nome']}",
            value=f"Tipo: {tipo}",
            inline=False
        )
    
    await ctx.send(embed=embed)
    
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
    
    try:
        msg = await ctx.bot.wait_for('message', timeout=30.0, check=check)
        num = int(msg.content)
        
        if 1 <= num <= len(empresas):
            return empresas[num - 1]
        else:
            await ctx.send("❌ Número inválido.")
            return None
    except:
        await ctx.send("❌ Tempo esgotado.")
        return None


# ============================================
# HELPER - PARSE DE ENTRADA DE PRODUTOS
# ============================================

def parse_item_input(entrada: str) -> List[tuple]:
    """
    Converte entrada como 'pa2 va10 gp5' em lista de (código, quantidade).
    Retorna lista de tuplas: [('pa', 2), ('va', 10), ('gp', 5)]
    """
    matches = PRODUTO_REGEX.findall(entrada)
    return [(codigo.lower(), int(quantidade)) for codigo, quantidade in matches]


# ============================================
# HELPER - FORMATAÇÃO DE VALORES
# ============================================

def formatar_dinheiro(valor: float) -> str:
    """Formata valor como dinheiro."""
    return f"${valor:,.2f}"


def formatar_lista_produtos(produtos: List[Dict], mostrar_preco: bool = True) -> str:
    """Formata lista de produtos para exibição."""
    if not produtos:
        return "Nenhum produto."
    
    linhas = []
    for p in produtos:
        linha = f"• **{p.get('nome', p.get('codigo', '?'))}** x{p.get('quantidade', 0)}"
        if mostrar_preco and 'preco_funcionario' in p:
            valor = p['quantidade'] * float(p['preco_funcionario'])
            linha += f" - {formatar_dinheiro(valor)}"
        linhas.append(linha)
    
    return "\n".join(linhas)


# ============================================
# HELPER - VERIFICAÇÃO DE ADMIN
# ============================================

async def verificar_is_admin(ctx, empresa: Dict) -> bool:
    """Verifica se o usuário é admin/dono da empresa."""
    # Dono do servidor sempre é admin
    if ctx.author.id == ctx.guild.owner_id:
        return True
    
    # Dono da empresa
    if str(ctx.author.id) == empresa.get('proprietario_discord_id'):
        return True
    
    # Tem permissão de administrador
    if ctx.author.guild_permissions.administrator:
        return True
    
    return False
