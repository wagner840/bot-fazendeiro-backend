"""
Auto-configuration functions for prices (min/medio/max).
"""

import discord
from database import (
    get_produtos_referencia,
    configurar_produto_empresa
)
from utils import selecionar_empresa


async def configurar_precos_com_feedback(ctx, empresa, modo: str):
    """Helper function to configure prices with visual feedback."""
    produtos_ref = await get_produtos_referencia(empresa['tipo_empresa_id'], guild_id=str(ctx.guild.id))

    if not produtos_ref:
        await ctx.send("Nenhum produto disponivel.")
        return

    modos = {
        'minimo': {'emoji': '', 'cor': discord.Color.blue(), 'nome': 'MINIMO'},
        'medio': {'emoji': '', 'cor': discord.Color.gold(), 'nome': 'MEDIO'},
        'maximo': {'emoji': '', 'cor': discord.Color.green(), 'nome': 'MAXIMO'}
    }
    cfg = modos[modo]

    progress_msg = await ctx.send(f"{cfg['emoji']} Configurando {len(produtos_ref)} produtos com preco **{cfg['nome']}**...")

    configurados = 0
    produtos_config = []

    for p in produtos_ref:
        # Parse min/max handling None
        p_min_raw = p.get('preco_minimo')
        p_max_raw = p.get('preco_maximo')

        p_min = float(p_min_raw) if p_min_raw is not None else None
        p_max = float(p_max_raw) if p_max_raw is not None else None

        preco_venda = 0.0

        if modo == 'minimo':
            if p_min is not None:
                preco_venda = p_min
            elif p_max is not None:
                preco_venda = p_max  # Fallback to max if min missing
            else:
                continue  # Skip if no price

        elif modo == 'maximo':
            if p_max is not None:
                preco_venda = p_max
            elif p_min is not None:
                preco_venda = p_min  # Fallback to min if max missing
            else:
                continue

        else:  # medio
            if p_min is not None and p_max is not None:
                preco_venda = (p_min + p_max) / 2
            elif p_min is not None:
                preco_venda = p_min
            elif p_max is not None:
                preco_venda = p_max
            else:
                continue

        preco_func = round(preco_venda * 0.25, 2)

        if await configurar_produto_empresa(empresa['id'], p['id'], preco_venda, preco_func):
            configurados += 1
            produtos_config.append({
                'codigo': p['codigo'],
                'nome': p['nome'],
                'categoria': p.get('categoria', 'Outros'),
                'preco_venda': preco_venda,
                'preco_func': preco_func
            })

    try:
        await progress_msg.delete()
    except:
        pass

    # Embed principal
    embed_sucesso = discord.Embed(
        title=f"OK Precos Configurados no {cfg['nome']}!",
        description=f"{cfg['emoji']} **{configurados}/{len(produtos_ref)}** produtos de **{empresa['nome']}** atualizados.",
        color=cfg['cor']
    )

    # Agrupa por categoria
    categorias = {}
    for p in produtos_config:
        cat = p['categoria']
        if cat not in categorias:
            categorias[cat] = []
        categorias[cat].append(p)

    for cat, prods in list(categorias.items())[:6]:
        preview = "\n".join([f"`{p['codigo']}` ${p['preco_venda']:.2f}" for p in prods[:3]])
        if len(prods) > 3:
            preview += f"\n*+{len(prods) - 3} mais*"
        embed_sucesso.add_field(name=f"{cat} ({len(prods)})", value=preview, inline=True)

    embed_sucesso.add_field(
        name="Comandos Uteis",
        value="`!verprecos` - Ver todos os precos\n`!verprecos [categoria]` - Ver por categoria",
        inline=False
    )
    embed_sucesso.set_footer(text="Pagamento Funcionario = 25% do preco de venda")

    await ctx.send(embed=embed_sucesso)

    # Embed com tabela de precos
    embed_precos = discord.Embed(
        title=f"Tabela de Precos - {cfg['nome']}",
        description=f"Precos configurados para **{empresa['nome']}**:",
        color=cfg['cor']
    )

    for p in produtos_config[:24]:
        embed_precos.add_field(
            name=f"`{p['codigo']}`",
            value=f"**{p['nome'][:18]}**\n${p['preco_venda']:.2f} | ${p['preco_func']:.2f}",
            inline=True
        )

    if len(produtos_config) > 24:
        embed_precos.set_footer(text=f"... e mais {len(produtos_config) - 24} produtos. Use !verprecos para ver todos.")

    await ctx.send(embed=embed_precos)
