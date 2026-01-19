# 🏢 Bot Multi-Empresa Downtown v2.1
## Guia Completo de Comandos

---

# 🚀 Primeiros Passos (Admin)

1. **Configurar Empresa:**
   `!configurar` - Escolha o tipo da sua empresa (ex: Restaurante, Fazenda)

2. **Configurar Produtos:**
   `!configurarauto` - Configura TODOS os produtos automaticamente com preço médio.
   `!configurarprecos` - Configuração manual passo-a-passo por categoria.

3. **Criar Canais de Funcionários:**
   `!bemvindo @usuario` - Cria um canal privado para o funcionário trabalhar.

---

# 📚 Catálogo e Preços

| Comando | Descrição |
|---------|-----------|
| `!produtos` | Ver todas as categorias disponíveis |
| `!produtos [categoria]` | Ver produtos de uma categoria (ex: `!produtos Bebidas`) |
| `!buscar [nome]` | Pesquisar produto por nome ou código (ex: `!buscar milho`) |
| `!infoproduto [codigo]` | Ver detalhes completos, preços min/max e lucro |
| `!verprecos` | Lista rápida de preços de venda e pagamento |

**Exemplo:** `!buscar cerveja` mostrará todos os tipos de cerveja e seus códigos.

---

# 👷 Área do Funcionário
*(Estes comandos funcionam APENAS no seu canal privado)*

## 📦 Produção e Estoque
| Comando | Descrição |
|---------|-----------|
| `!add [codigo][qtd]` | Adicionar produtos ao seu estoque |
| `!estoque` | Ver o que você tem produzido e valores a receber |
| `!deletar [codigo][qtd]` | Remover produtos do seu estoque |
| `!meusaldo` | Ver saldo acumulado de pagamentos anteriores |

**Exemplo:** `!add milho100 trigo50` (Adiciona 100 milhos e 50 trigos)

## 📋 Encomendas
| Comando | Descrição |
|---------|-----------|
| `!novaencomenda "Cliente" [itens]` | Criar novo pedido para um cliente |
| `!encomendas` | Ver lista de encomendas pendentes |
| `!entregar [ID]` | Entregar encomenda (usa seu estoque) |

**Exemplo:** `!novaencomenda "João Silva" cerveja10`

---

# ⚙️ Gestão (Exclusivo Admin)

## 💰 Financeiro
| Comando | Descrição |
|---------|-----------|
| `!pagar @funcionario` | Paga o funcionário e zera o estoque dele |
| `!caixa` | Relatório financeiro geral da empresa |
| `!estoqueglobal` | Ver estoque total somado de todos funcionários |
| `!funcionarios` | Lista todos funcionários e seus saldos |

## 🏷️ Ajuste de Preços
| Comando | Descrição |
|---------|-----------|
| `!alterarpreco [cod] [venda]` | Aletrar preço de venda (Pagamento será 25%) |
| `!alterarpreco [cod] [venda] [pgto]` | Alterar preço de venda e pagamento manual |

**Exemplo:** `!alterarpreco cerveja 5.00`

---

# ⚠️ Dicas Importantes
- **Códigos:** Use códigos simples e curtos (ex: `milho`, `trigo`, `carne`).
- **Quantidade:** Coloque a quantidade COLADA no código (ex: `milho10`).
- **Isolamento:** Cada servidor do Discord é uma empresa separada.
- **Ajuda:** Use `!help` a qualquer momento para ver este menu no Discord.
