# Documentação de Comandos - Bot Fazendeiro

## Resumo

| Tipo | Quantidade |
|------|------------|
| Comandos Híbridos (`/` e `!`) | 7 |
| Comandos Prefix (`!`) | 23 |
| **Total** | **30** |

---

## Legenda

| Símbolo | Significado |
|---------|-------------|
| `/comando` | Comando Slash (barra) |
| `!comando` | Comando Prefix (exclamação) |
| `[param]` | Parâmetro opcional |
| `<param>` | Parâmetro obrigatório |

---

## Produção

### `/produzir`
Abre painel de produção para registrar fabricação de itens.

| Info | Valor |
|------|-------|
| **Tipo** | Híbrido (`/` e `!`) |
| **Aliases** | `!add`, `!fabricar` |
| **Permissão** | Empresa configurada |
| **Arquivo** | `cogs/producao.py:363` |

---

### `/estoque`
Mostra estoque pessoal do funcionário.

| Info | Valor |
|------|-------|
| **Tipo** | Híbrido (`/` e `!`) |
| **Aliases** | `!meuestoque` |
| **Parâmetros** | `[@membro]` - ver estoque de outro usuário |
| **Permissão** | Empresa configurada |
| **Arquivo** | `cogs/producao.py:390` |

---

### `!estoqueglobal`
Mostra estoque total da empresa (todos os funcionários).

| Info | Valor |
|------|-------|
| **Tipo** | Prefix |
| **Aliases** | `!verestoque`, `!producao` |
| **Permissão** | Empresa configurada |
| **Arquivo** | `cogs/producao.py:443` |

---

### `!deletar`
Remove itens do estoque pessoal.

| Info | Valor |
|------|-------|
| **Tipo** | Prefix |
| **Aliases** | `!remover` |
| **Permissão** | Empresa configurada |
| **Arquivo** | `cogs/producao.py:437` |

---

### `!produtos`
Lista todos os produtos disponíveis com códigos.

| Info | Valor |
|------|-------|
| **Tipo** | Prefix |
| **Aliases** | `!catalogo`, `!tabela`, `!codigos` |
| **Permissão** | Empresa configurada |
| **Arquivo** | `cogs/producao.py:462` |

---

### `/encomenda`
Cria nova encomenda de cliente com carrinho interativo.

| Info | Valor |
|------|-------|
| **Tipo** | Híbrido (`/` e `!`) |
| **Aliases** | `!novaencomenda`, `!pedido` |
| **Permissão** | Empresa configurada |
| **Arquivo** | `cogs/producao.py:492` |

---

### `!encomendas`
Lista todas as encomendas pendentes.

| Info | Valor |
|------|-------|
| **Tipo** | Prefix |
| **Aliases** | `!pendentes` |
| **Permissão** | Empresa configurada |
| **Arquivo** | `cogs/producao.py:531` |

---

### `!entregar`
Finaliza entrega de uma encomenda e processa comissão.

| Info | Valor |
|------|-------|
| **Tipo** | Prefix |
| **Aliases** | `!entregarencomenda` |
| **Parâmetros** | `[encomenda_id]` |
| **Permissão** | Empresa configurada |
| **Arquivo** | `cogs/producao.py:599` |

---

## Preços

### `!configurarprecos`
Abre editor interativo para configurar preços individuais.

| Info | Valor |
|------|-------|
| **Tipo** | Prefix |
| **Aliases** | `!setprecos`, `!editarprecos` |
| **Permissão** | Administrador |
| **Arquivo** | `cogs/precos.py:139` |

---

### `!configmin` / `!configmedio` / `!configmax`
Auto-configura todos os produtos no preço mínimo/médio/máximo.

| Info | Valor |
|------|-------|
| **Tipo** | Prefix |
| **Permissão** | Administrador |
| **Arquivo** | `cogs/precos.py:173-187` |

> **Nota:** Esses 3 comandos poderiam ser unificados em um só com opção de seleção.

---

### `!verprecos`
Visualiza tabela de preços da empresa.

| Info | Valor |
|------|-------|
| **Tipo** | Prefix |
| **Aliases** | `!precos`, `!listaprecos`, `!tabelaprecos`, `!meusprecos` |
| **Parâmetros** | `[categoria]` - filtrar por categoria |
| **Permissão** | Empresa configurada |
| **Arquivo** | `cogs/precos.py:324` |

---

### `!comissao`
Define porcentagem de comissão dos funcionários.

| Info | Valor |
|------|-------|
| **Tipo** | Prefix |
| **Aliases** | `!porcentagem`, `!setcomissao`, `!definircomissao` |
| **Parâmetros** | `[porcentagem]` - valor 1-100 |
| **Permissão** | Administrador |
| **Arquivo** | `cogs/precos.py:506` |

---

## Financeiro

### `/pagar`
Realiza pagamento manual a funcionário.

| Info | Valor |
|------|-------|
| **Tipo** | Híbrido (`/` e `!`) |
| **Aliases** | `!pagamento` |
| **Parâmetros** | `[@membro] [valor] [descrição]` |
| **Permissão** | Administrador |
| **Arquivo** | `cogs/financeiro.py:156` |

---

### `!pagarestoque`
Paga e zera estoque/comissões acumuladas do funcionário.

| Info | Valor |
|------|-------|
| **Tipo** | Prefix |
| **Aliases** | `!pe` |
| **Parâmetros** | `<@membro>` |
| **Permissão** | Administrador |
| **Arquivo** | `cogs/financeiro.py:249` |

---

### `!caixa`
Mostra relatório financeiro (fluxo de caixa).

| Info | Valor |
|------|-------|
| **Tipo** | Prefix |
| **Aliases** | `!financeiro` |
| **Permissão** | Gerenciar Mensagens |
| **Arquivo** | `cogs/financeiro.py:301` |

---

## Administração

### `/configurar`
Wizard para configurar primeira empresa do servidor.

| Info | Valor |
|------|-------|
| **Tipo** | Híbrido (`/` e `!`) |
| **Aliases** | `!setup` |
| **Permissão** | Administrador |
| **Arquivo** | `cogs/admin.py:71` |

---

### `/novaempresa`
Cria nova empresa adicional no servidor.

| Info | Valor |
|------|-------|
| **Tipo** | Híbrido (`/` e `!`) |
| **Permissão** | Administrador |
| **Arquivo** | `cogs/admin.py:392` |

---

### `!empresas`
Lista todas as empresas configuradas no servidor.

| Info | Valor |
|------|-------|
| **Tipo** | Prefix |
| **Aliases** | `!listaempresas` |
| **Permissão** | Nenhuma |
| **Arquivo** | `cogs/admin.py:244` |

---

### `!modopagamento`
Altera método de pagamento (produção vs entrega).

| Info | Valor |
|------|-------|
| **Tipo** | Prefix |
| **Aliases** | `!setpagamento`, `!metodopagamento` |
| **Permissão** | Administrador |
| **Arquivo** | `cogs/admin.py:175` |

---

### `!limparcache`
Limpa cache local e recarrega dados do banco.

| Info | Valor |
|------|-------|
| **Tipo** | Prefix |
| **Aliases** | `!clearcache`, `!recarregar` |
| **Permissão** | Administrador |
| **Arquivo** | `cogs/admin.py:37` |

---

### `/bemvindo`
Cria canal privado e registra novo funcionário.

| Info | Valor |
|------|-------|
| **Tipo** | Híbrido (`/` e `!`) |
| **Aliases** | `!welcome` |
| **Parâmetros** | `[@membro]` |
| **Permissão** | Gerenciar Canais |
| **Arquivo** | `cogs/admin.py:535` |

---

### `!usuarios`
Lista usuários com acesso ao portal frontend.

| Info | Valor |
|------|-------|
| **Tipo** | Prefix |
| **Aliases** | `!useraccess`, `!acessos` |
| **Permissão** | Administrador |
| **Arquivo** | `cogs/admin.py:418` |

---

### `!removeracesso`
Remove acesso ao portal de um usuário.

| Info | Valor |
|------|-------|
| **Tipo** | Prefix |
| **Parâmetros** | `<@membro>` |
| **Permissão** | Administrador |
| **Arquivo** | `cogs/admin.py:457` |

---

### `!promover`
Promove usuário a admin do portal.

| Info | Valor |
|------|-------|
| **Tipo** | Prefix |
| **Parâmetros** | `<@membro>` |
| **Permissão** | Administrador |
| **Arquivo** | `cogs/admin.py:486` |

---

### `!limpar`
Limpa mensagens do canal (1-100).

| Info | Valor |
|------|-------|
| **Tipo** | Prefix |
| **Parâmetros** | `[quantidade]` - padrão 10 |
| **Permissão** | Gerenciar Mensagens |
| **Arquivo** | `cogs/admin.py:672` |

---

## Assinatura

### `!assinatura`
Mostra status da assinatura do servidor.

| Info | Valor |
|------|-------|
| **Tipo** | Prefix |
| **Aliases** | `!status`, `!plano` |
| **Permissão** | Nenhuma (gratuito) |
| **Arquivo** | `cogs/assinatura.py:78` |

---

### `!assinarpix`
Mostra link de pagamento para assinar/renovar.

| Info | Valor |
|------|-------|
| **Tipo** | Prefix |
| **Aliases** | `!renovar`, `!assinar` |
| **Permissão** | Nenhuma (gratuito) |
| **Arquivo** | `cogs/assinatura.py:115` |

---

### `!planos`
Lista todos os planos de assinatura disponíveis.

| Info | Valor |
|------|-------|
| **Tipo** | Prefix |
| **Permissão** | Nenhuma (gratuito) |
| **Arquivo** | `cogs/assinatura.py:144` |

---

### `!validarpagamento`
Valida pagamento pendente com gateway Asaas.

| Info | Valor |
|------|-------|
| **Tipo** | Prefix |
| **Aliases** | `!verificarpagamento`, `!claimpayment` |
| **Permissão** | Nenhuma |
| **Arquivo** | `cogs/assinatura.py:256` |

---

## Comandos de Superadmin

Apenas donos do bot e usuários na whitelist podem usar.

### `!addtester`
Adiciona servidor como tester (acesso gratuito).

| Info | Valor |
|------|-------|
| **Parâmetros** | `[guild_id] <motivo>` |
| **Arquivo** | `cogs/assinatura.py:180` |

---

### `!removetester`
Remove servidor da lista de testers.

| Info | Valor |
|------|-------|
| **Parâmetros** | `[guild_id]` |
| **Arquivo** | `cogs/assinatura.py:202` |

---

### `!testers`
Lista todos os servidores com acesso tester.

| Info | Valor |
|------|-------|
| **Arquivo** | `cogs/assinatura.py:215` |

---

### `!simularpagamento`
Simula pagamento PIX para testes.

| Info | Valor |
|------|-------|
| **Aliases** | `!simpay`, `!testpay` |
| **Parâmetros** | `[guild_id]` |
| **Arquivo** | `cogs/assinatura.py:241` |

---

## Comandos Gerais

### `!help`
Abre menu interativo de ajuda.

| Info | Valor |
|------|-------|
| **Tipo** | Prefix |
| **Aliases** | `!ajuda`, `!comandos` |
| **Permissão** | Nenhuma |
| **Arquivo** | `main.py:266` |

---

### `!sync`
Sincroniza comandos slash com Discord.

| Info | Valor |
|------|-------|
| **Tipo** | Prefix |
| **Parâmetros** | `[guild_id]` ou "global" |
| **Permissão** | Administrador |
| **Arquivo** | `main.py:278` |

---

### `!empresa`
Mostra informações da empresa ativa.

| Info | Valor |
|------|-------|
| **Tipo** | Prefix |
| **Aliases** | `!info` |
| **Permissão** | Nenhuma |
| **Arquivo** | `main.py` |

---

## Análise de Segurança

### Problemas Corrigidos

| Status | Comando | Correção Aplicada |
|--------|---------|-------------------|
| ✅ | `/pagar`, `!pagarestoque` | Alterado para `administrator=True` |
| ✅ | `!promover` | Adicionada verificação se já é admin |
| ✅ | `!validarpagamento` | Adicionada validação de ownership do pagamento |

### Comandos sem Proteção de Permissão

Estes comandos só dependem do decorator `@empresa_configurada()`:

- `!produzir` - Qualquer funcionário pode produzir
- `!estoque` - Qualquer um pode ver estoque
- `!deletar` - Qualquer funcionário pode deletar seu estoque
- `!produtos` - Qualquer um pode ver catálogo
- `!encomenda` - Qualquer funcionário pode criar encomendas
- `!encomendas` - Qualquer um pode ver encomendas
- `!entregar` - Qualquer funcionário pode entregar (valida estoque próprio)

---

## Recomendações de Melhoria Futuras

### Prioridade Média

1. **Unificar comandos de preço** - `!configmin`, `!configmedio`, `!configmax` deveriam ser um menu só
2. **Audit log** - Registrar ações administrativas (remoções, promoções, pagamentos)
3. **Rate limiting** - Adicionar cooldown em comandos de pagamento

### Prioridade Baixa

1. **Remover aliases numéricos** - `!2`, `!3`, `!5` são confusos
2. **Padronizar nomes** - Alguns em português, outros em inglês
3. **Mais comandos slash** - Converter comandos populares para slash

---

## Decoradores de Permissão

| Decorator | Função |
|-----------|--------|
| `@commands.has_permissions(administrator=True)` | Requer admin do Discord |
| `@commands.has_permissions(manage_messages=True)` | Requer gerenciar mensagens |
| `@commands.has_permissions(manage_channels=True)` | Requer gerenciar canais |
| `@empresa_configurada()` | Requer empresa configurada no servidor |
| `@is_superadmin()` | Apenas donos do bot |
| `@bot.check` (global) | Verifica assinatura ativa |

---

*Documentação atualizada - Bot Fazendeiro v1.0*
