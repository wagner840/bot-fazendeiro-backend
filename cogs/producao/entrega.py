"""
Delivery logic for production cog.
"""

from datetime import datetime, timezone
from decimal import Decimal
import discord
from config import supabase
from database import (
    get_estoque_funcionario,
    get_estoque_global_detalhado,
    remover_do_estoque,
    remover_do_estoque_global,
)


async def entregar_modo_entrega(ctx, empresa, encomenda, func, encomenda_id, bot):
    """
    Lógica de entrega para modo 'entrega'.
    - Usa estoque GLOBAL (de qualquer funcionário)
    - Vendedor ganha comissão independente de quem produziu
    """
    estoque_global = await get_estoque_global_detalhado(empresa['id'])

    itens_disponiveis = []
    itens_faltando = []
    valor_comissao = Decimal('0')

    for item in encomenda['itens_json']:
        precisa = item['quantidade'] - item.get('quantidade_entregue', 0)
        codigo = item['codigo']

        info_estoque = estoque_global.get(codigo, {'quantidade': 0, 'preco_funcionario': 0})
        tem_global = info_estoque['quantidade']
        preco_func = info_estoque.get('preco_funcionario', 0)

        if tem_global >= precisa:
            itens_disponiveis.append({
                'item': item,
                'precisa': precisa,
                'preco_funcionario': preco_func
            })
            valor_comissao += Decimal(str(preco_func)) * precisa
        else:
            itens_faltando.append({
                'item': item,
                'precisa': precisa,
                'tem': tem_global,
                'falta': precisa - tem_global
            })

    if itens_faltando:
        embed = discord.Embed(
            title="❌ Estoque Global Insuficiente",
            description="Não há itens suficientes no estoque da empresa para esta entrega.",
            color=discord.Color.red()
        )

        faltando_text = "\n".join([
            f"• **{i['item']['nome']}**: precisa {i['precisa']}, disponível {i['tem']} (falta {i['falta']})"
            for i in itens_faltando
        ])
        embed.add_field(name="📦 Itens Faltando", value=faltando_text, inline=False)
        embed.set_footer(text="Alguém precisa produzir esses itens primeiro (!add)")
        await ctx.send(embed=embed)
        return

    for item_info in itens_disponiveis:
        item = item_info['item']
        precisa = item_info['precisa']
        await remover_do_estoque_global(empresa['id'], item['codigo'], precisa)

    await supabase.table('encomendas').update({
        'status': 'entregue',
        'data_entrega': datetime.now(timezone.utc).isoformat(),
        'funcionario_responsavel_id': func['id']
    }).eq('id', encomenda_id).execute()

    if valor_comissao > 0:
        await supabase.table('transacoes').insert({
            'empresa_id': empresa['id'],
            'tipo': 'comissao_pendente',
            'valor': float(valor_comissao),
            'descricao': f'Comissão Venda #{encomenda_id}',
            'funcionario_id': func['id']
        }).execute()

    embed = discord.Embed(
        title="✅ Encomenda Entregue!",
        description=f"**ID:** #{encomenda_id}\n**Cliente:** {encomenda['comprador']}\n**Modo:** Comissão por Venda",
        color=discord.Color.green()
    )

    embed.add_field(name="📦 Valor da Venda", value=f"R$ {encomenda['valor_total']:.2f}", inline=True)
    embed.add_field(name="💰 Sua Comissão", value=f"R$ {valor_comissao:.2f}", inline=True)
    embed.set_footer(text="Comissão registrada! Admin pode pagar via !pagarestoque")

    await ctx.send(embed=embed)


async def entregar_modo_producao(ctx, empresa, encomenda, func, encomenda_id, bot):
    """
    Lógica de entrega para modo 'producao'.
    - Usa estoque PESSOAL do funcionário
    - Só ganha comissão pelos itens que ele mesmo produziu
    """
    estoque = await get_estoque_funcionario(func['id'], empresa['id'])
    estoque_dict = {e['produto_codigo']: e['quantidade'] for e in estoque}

    itens_com_estoque = []
    itens_sem_estoque = []
    valor_comissao = Decimal('0')

    for item in encomenda['itens_json']:
        precisa = item['quantidade'] - item.get('quantidade_entregue', 0)
        tem = estoque_dict.get(item['codigo'], 0)

        if tem >= precisa:
            itens_com_estoque.append({
                'item': item,
                'precisa': precisa,
                'tem': tem
            })
            preco_func = next(
                (e['preco_funcionario'] for e in estoque if e['produto_codigo'] == item['codigo']),
                0
            )
            valor_comissao += Decimal(str(preco_func)) * precisa
        else:
            itens_sem_estoque.append({
                'item': item,
                'precisa': precisa,
                'tem': tem,
                'falta': precisa - tem
            })

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    if itens_sem_estoque:
        embed = discord.Embed(
            title="⚠️ Estoque Insuficiente",
            description="Você não tem todos os itens no seu estoque pessoal.",
            color=discord.Color.orange()
        )

        faltando_text = "\n".join([
            f"• **{i['item']['nome']}**: precisa {i['precisa']}, tem {i['tem']} (falta {i['falta']})"
            for i in itens_sem_estoque
        ])
        embed.add_field(name="📦 Itens Faltando", value=faltando_text, inline=False)

        if itens_com_estoque:
            tem_text = "\n".join([
                f"• **{i['item']['nome']}**: {i['precisa']}x ✅"
                for i in itens_com_estoque
            ])
            embed.add_field(name="✅ Itens que Você Tem", value=tem_text, inline=False)

        embed.add_field(
            name="❓ Entregar mesmo assim?",
            value="Se você entregar **SEM** ter fabricado os produtos:\n"
                  "• A venda será registrada normalmente\n"
                  "• ❌ Você **NÃO receberá comissão** pelos itens que não fabricou\n\n"
                  "Digite **sim** para entregar ou **não** para cancelar",
            inline=False
        )

        if itens_com_estoque:
            embed.set_footer(text=f"💰 Comissão garantida (itens que você tem): R$ {valor_comissao:.2f}")
        else:
            embed.set_footer(text="💰 Sem comissão (você não fabricou nenhum item)")

        await ctx.send(embed=embed)

        try:
            msg = await bot.wait_for('message', timeout=30.0, check=check)
            if msg.content.lower() not in ['sim', 's', 'yes', 'y']:
                await ctx.send("❌ Entrega cancelada.\n💡 Use `!add codigo10` para adicionar produtos ao seu estoque primeiro.")
                return
        except:
            await ctx.send("❌ Tempo esgotado. Entrega cancelada.")
            return

    for item_info in itens_com_estoque:
        item = item_info['item']
        precisa = item_info['precisa']
        await remover_do_estoque(func['id'], empresa['id'], item['codigo'], precisa)

    await supabase.table('encomendas').update({
        'status': 'entregue',
        'data_entrega': datetime.now(timezone.utc).isoformat(),
        'funcionario_responsavel_id': func['id']
    }).eq('id', encomenda_id).execute()

    if valor_comissao > 0:
        await supabase.table('transacoes').insert({
            'empresa_id': empresa['id'],
            'tipo': 'comissao_pendente',
            'valor': float(valor_comissao),
            'descricao': f'Comissão Encomenda #{encomenda_id}',
            'funcionario_id': func['id']
        }).execute()

    embed = discord.Embed(
        title="✅ Encomenda Entregue!",
        description=f"**ID:** #{encomenda_id}\n**Cliente:** {encomenda['comprador']}",
        color=discord.Color.green()
    )

    embed.add_field(name="📦 Valor da Venda", value=f"R$ {encomenda['valor_total']:.2f}", inline=True)

    if valor_comissao > 0:
        embed.add_field(name="💰 Comissão Acumulada", value=f"R$ {valor_comissao:.2f}", inline=True)
        embed.set_footer(text="Comissão registrada! Use !pagarestoque para receber.")
    else:
        embed.add_field(name="💰 Sua Comissão", value="R$ 0.00", inline=True)
        embed.set_footer(text="Sem comissão pois você não fabricou os itens.")

    if itens_sem_estoque:
        sem_comissao = "\n".join([f"• {i['item']['nome']} ({i['precisa']}x)" for i in itens_sem_estoque])
        embed.add_field(
            name="⚠️ Entregue SEM Comissão",
            value=sem_comissao,
            inline=False
        )

    await ctx.send(embed=embed)
