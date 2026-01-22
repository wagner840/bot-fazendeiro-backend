# Guia de Testes Manuais - Bot Fazendeiro

## Pre-requisitos
- Bot rodando (`python main.py`)
- Servidor Discord configurado
- Empresa configurada com produtos

---

## 1. COMANDOS DE CONFIGURACAO

### 1.1 !limparcache
**Objetivo:** Limpar cache e verificar se dados foram recarregados do banco

**Passos:**
1. Digite `!limparcache`
2. Verifique se mostra:
   - Guild ID
   - Servidor encontrado
   - Empresas encontradas

**Resultado Esperado:**
```
Cache Limpo e Recarregado!
Guild ID: XXXXX
Servidor: [nome]
Empresas: X encontrada(s)
Lista: [nome da empresa]
```

**Status:** [ ] Passou / [ ] Falhou

---

### 1.2 !configurar (ver empresa existente)
**Objetivo:** Verificar empresa ja configurada

**Passos:**
1. Digite `!configurar`
2. Deve mostrar informacoes da empresa existente

**Resultado Esperado:**
```
Empresa Configurada!
Nome: [nome]
Tipo: [tipo]
Proprietario: @usuario
```

**Status:** [ ] Passou / [ ] Falhou

---

### 1.3 !empresas
**Objetivo:** Listar todas as empresas do servidor

**Passos:**
1. Digite `!empresas`
2. Deve listar todas as empresas configuradas

**Resultado Esperado:**
```
Empresas do Servidor
1. [nome] - [tipo]
```

**Status:** [ ] Passou / [ ] Falhou

---

### 1.4 !modopagamento
**Objetivo:** Verificar/alterar modo de pagamento

**Passos:**
1. Digite `!modopagamento`
2. Verifique o modo atual
3. Selecione opcao 1 ou 2
4. Confirme a alteracao

**Resultado Esperado:**
```
Modo de pagamento alterado para [PRODUCAO/ENTREGA]!
```

**Status:** [ ] Passou / [ ] Falhou

---

## 2. COMANDOS DE PRECOS

### 2.1 !precos
**Objetivo:** Ver tabela de precos configurados

**Passos:**
1. Digite `!precos`
2. Deve mostrar todos os produtos com precos

**Resultado Esperado:**
```
Tabela de Precos
[nome empresa]
Venda | Funcionario

[categoria] (X)
[codigo] [nome]
$ XX.XX | $ XX.XX
```

**Status:** [ ] Passou / [ ] Falhou

---

### 2.2 !configmin
**Objetivo:** Configurar todos os precos no minimo

**Passos:**
1. Digite `!configmin`
2. Selecione a empresa (se houver mais de uma)
3. Aguarde a configuracao

**Resultado Esperado:**
```
Configurando X produtos com preco MINIMO...
X/X produtos configurados com preco MINIMO!
```

**Status:** [ ] Passou / [ ] Falhou

---

### 2.3 !configmedio
**Objetivo:** Configurar todos os precos no medio

**Passos:**
1. Digite `!configmedio`
2. Selecione a empresa
3. Aguarde a configuracao

**Resultado Esperado:**
```
Configurando X produtos com preco MEDIO...
X/X produtos configurados com preco MEDIO!
```

**Status:** [ ] Passou / [ ] Falhou

---

### 2.4 !configmax
**Objetivo:** Configurar todos os precos no maximo

**Passos:**
1. Digite `!configmax`
2. Selecione a empresa
3. Aguarde a configuracao

**Resultado Esperado:**
```
Configurando X produtos com preco MAXIMO...
X/X produtos configurados com preco MAXIMO!
```

**Status:** [ ] Passou / [ ] Falhou

---

### 2.5 !configurarprecos
**Objetivo:** Configurar precos manualmente

**Passos:**
1. Digite `!configurarprecos`
2. Selecione categoria
3. Configure um produto: `codigo preco_venda preco_func`
4. Digite `pronto` para sair

**Resultado Esperado:**
```
[nome produto]: Venda $X.XX | Funcionario $X.XX
X produtos configurados!
```

**Status:** [ ] Passou / [ ] Falhou

---

### 2.6 !comissao
**Objetivo:** Configurar porcentagem de comissao

**Passos:**
1. Digite `!comissao 30`
2. Ou digite `!comissao` e selecione uma opcao

**Resultado Esperado:**
```
Comissao de 30% aplicada a X produtos!
```

**Status:** [ ] Passou / [ ] Falhou

---

## 3. COMANDOS DE PRODUCAO

### 3.1 !produtos
**Objetivo:** Ver catalogo de produtos disponiveis

**Passos:**
1. Digite `!produtos`
2. Deve listar todos os produtos com codigos

**Resultado Esperado:**
```
Catalogo de Produtos
[codigo] [nome] - $X.XX
```

**Status:** [ ] Passou / [ ] Falhou

---

### 3.2 !add
**Objetivo:** Adicionar produtos ao estoque

**Passos:**
1. Digite `!add [codigo]10` (ex: `!add rotulo10`)
2. Ou `!add [codigo] [quantidade]` (ex: `!add rotulo 10`)

**Resultado Esperado:**
```
Producao Registrada!
[nome produto]
+10 (Total: 10)
R$ X.XX acumulado
```

**Status:** [ ] Passou / [ ] Falhou

---

### 3.3 !estoque (ou !2)
**Objetivo:** Ver estoque pessoal

**Passos:**
1. Digite `!estoque`
2. Deve mostrar todos os itens no seu estoque

**Resultado Esperado:**
```
Seu Estoque
[nome] x10 = R$ X.XX
Total: R$ X.XX
```

**Status:** [ ] Passou / [ ] Falhou

---

### 3.4 !deletar (ou !3)
**Objetivo:** Remover produtos do estoque

**Passos:**
1. Digite `!deletar [codigo]5` (ex: `!deletar rotulo5`)
2. Ou `!deletar [codigo] [quantidade]`

**Resultado Esperado:**
```
-5 [nome produto] removido do estoque
```

**Status:** [ ] Passou / [ ] Falhou

---

### 3.5 !estoqueglobal
**Objetivo:** Ver estoque total da empresa

**Passos:**
1. Digite `!estoqueglobal`
2. Deve mostrar estoque de todos os funcionarios

**Resultado Esperado:**
```
Estoque Global
[funcionario]: X itens - R$ X.XX
Total: R$ X.XX
```

**Status:** [ ] Passou / [ ] Falhou

---

## 4. COMANDOS DE ENCOMENDAS

### 4.1 !novaencomenda (ou !4)
**Objetivo:** Criar uma nova encomenda

**Passos:**
1. Digite `!novaencomenda`
2. Digite o nome do cliente
3. Adicione produtos: `codigo quantidade`
4. Digite `pronto`
5. Confirme com `sim`

**Resultado Esperado:**
```
Encomenda Criada com Sucesso!
ID: #X
Cliente: [nome]
Itens: ...
Total: R$ X.XX
Status: Pendente
```

**Status:** [ ] Passou / [ ] Falhou

---

### 4.2 !encomendas (ou !5)
**Objetivo:** Listar encomendas pendentes

**Passos:**
1. Digite `!encomendas`
2. Deve mostrar todas as encomendas pendentes

**Resultado Esperado:**
```
Encomendas Pendentes
#1 - [cliente] - R$ X.XX - Pendente
```

**Status:** [ ] Passou / [ ] Falhou

---

### 4.3 !entregar
**Objetivo:** Entregar uma encomenda

**Passos:**
1. Primeiro adicione os produtos ao estoque: `!add [codigo][qtd]`
2. Digite `!entregar [ID]` (ex: `!entregar 1`)
3. Se nao tiver estoque, confirme com `sim` ou `nao`

**Resultado Esperado:**
```
Encomenda Entregue!
ID: #X
Cliente: [nome]
Valor: R$ X.XX
Comissao: R$ X.XX
```

**Status:** [ ] Passou / [ ] Falhou

---

## 5. COMANDOS FINANCEIROS

### 5.1 !pagar
**Objetivo:** Fazer pagamento manual a funcionario

**Passos:**
1. Digite `!pagar @usuario 100`
2. Confirme com `sim`

**Resultado Esperado:**
```
@usuario recebeu R$ 100.00!
```

**Status:** [ ] Passou / [ ] Falhou

---

### 5.2 !pagarestoque
**Objetivo:** Pagar e zerar estoque do funcionario

**Passos:**
1. Funcionario deve ter estoque (use `!add` primeiro)
2. Digite `!pagarestoque @usuario`
3. Verifique valores mostrados
4. Confirme com `sim`

**Resultado Esperado:**
```
@usuario recebeu R$ X.XX! Estoque zerado e comissoes pagas.
```

**Status:** [ ] Passou / [ ] Falhou

---

### 5.3 !caixa
**Objetivo:** Ver relatorio financeiro

**Passos:**
1. Digite `!caixa`
2. Deve mostrar saldos e estoques

**Resultado Esperado:**
```
Caixa - [nome empresa]
Total Saldos: R$ X.XX
Total Estoque: R$ X.XX
TOTAL: R$ X.XX
```

**Status:** [ ] Passou / [ ] Falhou

---

## 6. COMANDOS DE USUARIOS

### 6.1 !usuarios
**Objetivo:** Listar usuarios com acesso ao frontend

**Passos:**
1. Digite `!usuarios`
2. Deve listar todos os usuarios

**Resultado Esperado:**
```
Usuarios com Acesso ao Painel
@usuario - Admin
```

**Status:** [ ] Passou / [ ] Falhou

---

### 6.2 !bemvindo
**Objetivo:** Cadastrar novo funcionario e dar acesso ao frontend

**Passos:**
1. Digite `!bemvindo @novousuario`
2. Deve criar canal privado e dar acesso

**Resultado Esperado:**
```
Bem-vindo @novousuario!
Canal criado: #nome-canal
Acesso ao painel liberado
```

**Status:** [ ] Passou / [ ] Falhou

---

### 6.3 !promover
**Objetivo:** Promover usuario para admin

**Passos:**
1. Digite `!promover @usuario`
2. Confirme se necessario

**Resultado Esperado:**
```
@usuario promovido para Admin!
```

**Status:** [ ] Passou / [ ] Falhou

---

### 6.4 !removeracesso
**Objetivo:** Remover acesso do frontend

**Passos:**
1. Digite `!removeracesso @usuario`
2. Confirme se necessario

**Resultado Esperado:**
```
Acesso de @usuario removido!
```

**Status:** [ ] Passou / [ ] Falhou

---

## 7. COMANDO DE AJUDA

### 7.1 !help
**Objetivo:** Ver todos os comandos disponiveis

**Passos:**
1. Digite `!help`
2. Deve mostrar todos os comandos organizados

**Resultado Esperado:**
```
Bot Multi-Empresa Downtown
Empresa(s): [nome]
Configuracao (Admin): ...
Config. de Precos (Admin): ...
Producao: ...
Encomendas: ...
Financeiro (Admin): ...
```

**Status:** [ ] Passou / [ ] Falhou

---

## RESUMO DOS TESTES

| Categoria | Comando | Status |
|-----------|---------|--------|
| Config | !limparcache | [ ] |
| Config | !configurar | [ ] |
| Config | !empresas | [ ] |
| Config | !modopagamento | [ ] |
| Precos | !precos | [ ] |
| Precos | !configmin | [ ] |
| Precos | !configmedio | [ ] |
| Precos | !configmax | [ ] |
| Precos | !configurarprecos | [ ] |
| Precos | !comissao | [ ] |
| Producao | !produtos | [ ] |
| Producao | !add | [ ] |
| Producao | !estoque | [ ] |
| Producao | !deletar | [ ] |
| Producao | !estoqueglobal | [ ] |
| Encomendas | !novaencomenda | [ ] |
| Encomendas | !encomendas | [ ] |
| Encomendas | !entregar | [ ] |
| Financeiro | !pagar | [ ] |
| Financeiro | !pagarestoque | [ ] |
| Financeiro | !caixa | [ ] |
| Usuarios | !usuarios | [ ] |
| Usuarios | !bemvindo | [ ] |
| Usuarios | !promover | [ ] |
| Usuarios | !removeracesso | [ ] |
| Ajuda | !help | [ ] |

**Total:** 26 comandos
**Passou:** ____
**Falhou:** ____

---

## FLUXO DE TESTE COMPLETO (Recomendado)

Execute os comandos nesta ordem para testar o fluxo completo:

```
1. !help                    - Ver comandos
2. !limparcache             - Limpar cache
3. !empresas                - Ver empresas
4. !precos                  - Ver precos atuais
5. !configmin               - Setar precos minimos
6. !precos                  - Verificar precos atualizados
7. !produtos                - Ver catalogo
8. !add rotulo100           - Adicionar 100 rotulos
9. !estoque                 - Ver estoque pessoal
10. !novaencomenda          - Criar encomenda
    > cliente_teste
    > rotulo 50
    > pronto
    > sim
11. !encomendas             - Ver pendentes
12. !entregar [ID]          - Entregar encomenda
13. !estoque                - Verificar estoque reduzido
14. !pagarestoque @usuario  - Pagar estoque restante
    > sim
15. !caixa                  - Ver relatorio final
16. !usuarios               - Ver usuarios
```
