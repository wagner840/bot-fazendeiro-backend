# Bot Fazendeiro - Design SaaS Multi-Tenant

**Data:** 2026-01-20
**Status:** Aprovado
**Versão:** 1.0

---

## 1. Visão Geral

Transformar o Bot Fazendeiro em um sistema SaaS multi-tenant seguro e escalável, permitindo:

- Distribuição para múltiplos servidores Discord
- Cobrança de mensalidade por servidor
- Isolamento completo de dados entre servidores
- Sistema de permissões granular (Admin/Funcionário)
- Login seguro via Discord OAuth

---

## 2. Requisitos Definidos

| Aspecto | Decisão |
|---------|---------|
| **Tenant (inquilino)** | Por Servidor Discord (guild_id) |
| **Empresas** | N empresas por servidor |
| **Funcionários** | N funcionários, vinculados a N empresas |
| **Acesso Funcionário** | Login único, vê todas suas empresas |
| **Permissões Func.** | GET geral + INSERT/UPDATE em estoque e encomendas |
| **Autenticação** | Discord OAuth via Supabase Auth |
| **Cobrança** | Preço fixo por servidor (implementar depois) |
| **Gateway Pagamento** | Implementar posteriormente |

---

## 3. Hierarquia de Roles

```
🔴 SUPERADMIN (DEV)
│   └── Acesso TOTAL a TODOS os servidores
│
└── 🟡 ADMIN (dono do servidor)
    │   └── Acesso TOTAL ao SEU servidor apenas
    │
    └── 🟢 FUNCIONÁRIO
        └── SELECT geral + INSERT/UPDATE em estoque e encomendas
```

---

## 4. Arquitetura de Dados

### 4.1 Nova Tabela: servidores (Tenant Principal)

```sql
CREATE TABLE servidores (
    id SERIAL PRIMARY KEY,
    guild_id TEXT UNIQUE NOT NULL,
    nome TEXT NOT NULL,
    proprietario_discord_id TEXT NOT NULL,
    plano TEXT DEFAULT 'basico',
    assinatura_ativa BOOLEAN DEFAULT false,
    data_criacao TIMESTAMPTZ DEFAULT now(),
    ativo BOOLEAN DEFAULT true
);

CREATE INDEX idx_servidores_guild ON servidores(guild_id);
CREATE INDEX idx_servidores_proprietario ON servidores(proprietario_discord_id);
```

### 4.2 Nova Tabela: usuarios_frontend

```sql
CREATE TABLE usuarios_frontend (
    id SERIAL PRIMARY KEY,
    discord_id TEXT UNIQUE NOT NULL,
    guild_id TEXT,                        -- NULL para superadmin
    role TEXT DEFAULT 'funcionario',      -- 'superadmin', 'admin', 'funcionario'
    ativo BOOLEAN DEFAULT true,
    criado_em TIMESTAMPTZ DEFAULT now(),
    criado_por TEXT,

    CONSTRAINT valid_role CHECK (role IN ('superadmin', 'admin', 'funcionario'))
);

CREATE INDEX idx_usuarios_discord ON usuarios_frontend(discord_id);
CREATE INDEX idx_usuarios_guild ON usuarios_frontend(guild_id);
```

### 4.3 Nova Tabela: funcionario_empresa (Muitos-para-Muitos)

```sql
CREATE TABLE funcionario_empresa (
    id SERIAL PRIMARY KEY,
    funcionario_id INTEGER NOT NULL REFERENCES funcionarios(id),
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    cargo TEXT DEFAULT 'funcionario',
    data_vinculo TIMESTAMPTZ DEFAULT now(),
    ativo BOOLEAN DEFAULT true,

    UNIQUE(funcionario_id, empresa_id)
);

CREATE INDEX idx_func_empresa_func ON funcionario_empresa(funcionario_id);
CREATE INDEX idx_func_empresa_emp ON funcionario_empresa(empresa_id);
```

### 4.4 Modificar Tabela: empresas

```sql
-- Adicionar coluna servidor_id
ALTER TABLE empresas
    ADD COLUMN servidor_id INTEGER REFERENCES servidores(id);

-- Migrar dados existentes (executar uma vez)
-- INSERT INTO servidores (guild_id, nome, proprietario_discord_id)
-- SELECT DISTINCT guild_id, nome, proprietario_discord_id FROM empresas;

-- UPDATE empresas e
-- SET servidor_id = (SELECT s.id FROM servidores s WHERE s.guild_id = e.guild_id);

-- Remover constraint antiga após migração
-- ALTER TABLE empresas DROP CONSTRAINT IF EXISTS empresas_guild_id_key;
```

### 4.5 Diagrama de Relacionamentos

```
SERVIDOR (tenant)
│
├── usuarios_frontend
│   ├── discord_id
│   └── role: superadmin | admin | funcionario
│
├── EMPRESA 1
│   ├── funcionario_empresa (vínculo N:N)
│   │   ├── Funcionário A ←──┐
│   │   └── Funcionário B    │
│   └── produtos, estoque    │
│                            │
├── EMPRESA 2                │
│   ├── funcionario_empresa  │
│   │   ├── Funcionário A ←──┘ (mesmo func. em múltiplas empresas)
│   │   └── Funcionário C
│   └── produtos, estoque
│
└── EMPRESA N...
```

---

## 5. Row Level Security (RLS)

### 5.1 Funções Auxiliares

```sql
-- Obtém discord_id do usuário logado (do JWT)
CREATE OR REPLACE FUNCTION auth.discord_id()
RETURNS TEXT AS $$
  SELECT COALESCE(
    current_setting('request.jwt.claims', true)::json->>'sub',
    (current_setting('request.jwt.claims', true)::json->'user_metadata'->>'provider_id')
  );
$$ LANGUAGE SQL STABLE;

-- Verifica se usuário é SUPERADMIN (DEV)
CREATE OR REPLACE FUNCTION auth.is_superadmin()
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM usuarios_frontend
    WHERE discord_id = auth.discord_id()
      AND role = 'superadmin'
      AND ativo = true
  );
$$ LANGUAGE SQL STABLE SECURITY DEFINER;

-- Obtém guild_id do usuário logado
CREATE OR REPLACE FUNCTION auth.user_guild_id()
RETURNS TEXT AS $$
  SELECT guild_id FROM usuarios_frontend
  WHERE discord_id = auth.discord_id()
    AND ativo = true
  LIMIT 1;
$$ LANGUAGE SQL STABLE SECURITY DEFINER;

-- Verifica se usuário é admin DO SEU SERVIDOR
CREATE OR REPLACE FUNCTION auth.is_admin()
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM usuarios_frontend
    WHERE discord_id = auth.discord_id()
      AND role = 'admin'
      AND ativo = true
  );
$$ LANGUAGE SQL STABLE SECURITY DEFINER;

-- Obtém empresas que o usuário tem acesso
CREATE OR REPLACE FUNCTION auth.user_empresa_ids()
RETURNS SETOF INTEGER AS $$
BEGIN
  -- Se superadmin, retorna TODAS
  IF (SELECT auth.is_superadmin()) THEN
    RETURN QUERY SELECT id FROM empresas;
    RETURN;
  END IF;

  -- Se admin, retorna todas do SEU servidor
  IF (SELECT auth.is_admin()) THEN
    RETURN QUERY
      SELECT e.id FROM empresas e
      JOIN servidores s ON s.id = e.servidor_id
      WHERE s.guild_id = auth.user_guild_id();
    RETURN;
  END IF;

  -- Se funcionário, retorna apenas onde está vinculado
  RETURN QUERY
    SELECT fe.empresa_id
    FROM funcionario_empresa fe
    JOIN funcionarios f ON f.id = fe.funcionario_id
    WHERE f.discord_id = auth.discord_id()
      AND fe.ativo = true;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;
```

### 5.2 Habilitar RLS em Todas as Tabelas

```sql
ALTER TABLE servidores ENABLE ROW LEVEL SECURITY;
ALTER TABLE empresas ENABLE ROW LEVEL SECURITY;
ALTER TABLE funcionarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE funcionario_empresa ENABLE ROW LEVEL SECURITY;
ALTER TABLE produtos_empresa ENABLE ROW LEVEL SECURITY;
ALTER TABLE estoque_produtos ENABLE ROW LEVEL SECURITY;
ALTER TABLE encomendas ENABLE ROW LEVEL SECURITY;
ALTER TABLE historico_pagamentos ENABLE ROW LEVEL SECURITY;
ALTER TABLE usuarios_frontend ENABLE ROW LEVEL SECURITY;
ALTER TABLE produtos_referencia ENABLE ROW LEVEL SECURITY;
ALTER TABLE tipos_empresa ENABLE ROW LEVEL SECURITY;
```

### 5.3 Políticas por Tabela

#### servidores
```sql
CREATE POLICY "servidor_select" ON servidores FOR SELECT
  USING (auth.is_superadmin() OR guild_id = auth.user_guild_id());

CREATE POLICY "servidor_update" ON servidores FOR UPDATE
  USING (auth.is_superadmin() OR (auth.is_admin() AND guild_id = auth.user_guild_id()));

CREATE POLICY "servidor_insert" ON servidores FOR INSERT
  WITH CHECK (auth.is_superadmin());

CREATE POLICY "servidor_delete" ON servidores FOR DELETE
  USING (auth.is_superadmin());
```

#### empresas
```sql
CREATE POLICY "empresas_select" ON empresas FOR SELECT
  USING (auth.is_superadmin() OR id IN (SELECT auth.user_empresa_ids()));

CREATE POLICY "empresas_insert" ON empresas FOR INSERT
  WITH CHECK (auth.is_superadmin() OR auth.is_admin());

CREATE POLICY "empresas_update" ON empresas FOR UPDATE
  USING (auth.is_superadmin() OR (auth.is_admin() AND id IN (SELECT auth.user_empresa_ids())));

CREATE POLICY "empresas_delete" ON empresas FOR DELETE
  USING (auth.is_superadmin());
```

#### estoque_produtos (Funcionário pode INSERT/UPDATE)
```sql
CREATE POLICY "estoque_select" ON estoque_produtos FOR SELECT
  USING (auth.is_superadmin() OR empresa_id IN (SELECT auth.user_empresa_ids()));

CREATE POLICY "estoque_insert" ON estoque_produtos FOR INSERT
  WITH CHECK (auth.is_superadmin() OR empresa_id IN (SELECT auth.user_empresa_ids()));

CREATE POLICY "estoque_update" ON estoque_produtos FOR UPDATE
  USING (auth.is_superadmin() OR empresa_id IN (SELECT auth.user_empresa_ids()));

CREATE POLICY "estoque_delete" ON estoque_produtos FOR DELETE
  USING (auth.is_superadmin() OR auth.is_admin());
```

#### encomendas (Funcionário pode INSERT/UPDATE)
```sql
CREATE POLICY "encomendas_select" ON encomendas FOR SELECT
  USING (auth.is_superadmin() OR empresa_id IN (SELECT auth.user_empresa_ids()));

CREATE POLICY "encomendas_insert" ON encomendas FOR INSERT
  WITH CHECK (auth.is_superadmin() OR empresa_id IN (SELECT auth.user_empresa_ids()));

CREATE POLICY "encomendas_update" ON encomendas FOR UPDATE
  USING (auth.is_superadmin() OR empresa_id IN (SELECT auth.user_empresa_ids()));

CREATE POLICY "encomendas_delete" ON encomendas FOR DELETE
  USING (auth.is_superadmin() OR auth.is_admin());
```

#### produtos_empresa (Funcionário só SELECT)
```sql
CREATE POLICY "produtos_select" ON produtos_empresa FOR SELECT
  USING (auth.is_superadmin() OR empresa_id IN (SELECT auth.user_empresa_ids()));

CREATE POLICY "produtos_insert" ON produtos_empresa FOR INSERT
  WITH CHECK (auth.is_superadmin() OR auth.is_admin());

CREATE POLICY "produtos_update" ON produtos_empresa FOR UPDATE
  USING (auth.is_superadmin() OR auth.is_admin());

CREATE POLICY "produtos_delete" ON produtos_empresa FOR DELETE
  USING (auth.is_superadmin() OR auth.is_admin());
```

#### usuarios_frontend
```sql
CREATE POLICY "usuarios_select" ON usuarios_frontend FOR SELECT
  USING (
    auth.is_superadmin()
    OR discord_id = auth.discord_id()
    OR (auth.is_admin() AND guild_id = auth.user_guild_id())
  );

CREATE POLICY "usuarios_insert" ON usuarios_frontend FOR INSERT
  WITH CHECK (auth.is_superadmin() OR auth.is_admin());

CREATE POLICY "usuarios_update" ON usuarios_frontend FOR UPDATE
  USING (auth.is_superadmin() OR (auth.is_admin() AND guild_id = auth.user_guild_id()));

CREATE POLICY "usuarios_delete" ON usuarios_frontend FOR DELETE
  USING (auth.is_superadmin());
```

#### tipos_empresa e produtos_referencia (Tabelas de referência - todos podem ler)
```sql
CREATE POLICY "tipos_empresa_select" ON tipos_empresa FOR SELECT
  USING (true);

CREATE POLICY "tipos_empresa_modify" ON tipos_empresa FOR ALL
  USING (auth.is_superadmin());

CREATE POLICY "produtos_ref_select" ON produtos_referencia FOR SELECT
  USING (true);

CREATE POLICY "produtos_ref_modify" ON produtos_referencia FOR ALL
  USING (auth.is_superadmin());
```

### 5.4 Matriz de Permissões

| Tabela | Superadmin | Admin | Funcionário |
|--------|------------|-------|-------------|
| servidores | ALL (todos) | SELECT, UPDATE (só seu) | SELECT (só seu) |
| empresas | ALL | ALL (do servidor) | SELECT (só suas) |
| funcionarios | ALL | ALL (do servidor) | SELECT |
| funcionario_empresa | ALL | ALL | SELECT |
| produtos_empresa | ALL | ALL | SELECT |
| **estoque_produtos** | ALL | ALL | **SELECT, INSERT, UPDATE** |
| **encomendas** | ALL | ALL | **SELECT, INSERT, UPDATE** |
| historico_pagamentos | ALL | ALL | SELECT (só seus) |
| usuarios_frontend | ALL | SELECT, INSERT, UPDATE | SELECT (só ele) |
| tipos_empresa | ALL | SELECT | SELECT |
| produtos_referencia | ALL | SELECT | SELECT |

---

## 6. Autenticação Frontend

### 6.1 Configurar Discord OAuth no Supabase

1. Acessar Supabase Dashboard > Authentication > Providers
2. Habilitar Discord
3. Configurar Client ID e Client Secret do Discord Developer Portal
4. Redirect URL: `https://seu-projeto.supabase.co/auth/v1/callback`

### 6.2 AuthContext.tsx

```typescript
import { createContext, useContext, useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import type { User, Session } from '@supabase/supabase-js';

type Role = 'superadmin' | 'admin' | 'funcionario';

interface UserProfile {
  discord_id: string;
  guild_id: string | null;
  role: Role;
  ativo: boolean;
}

interface AuthContextType {
  user: User | null;
  session: Session | null;
  profile: UserProfile | null;
  isLoading: boolean;
  isSuperAdmin: boolean;
  isAdmin: boolean;
  isFuncionario: boolean;
  signInWithDiscord: () => Promise<void>;
  signOut: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      if (session?.user) loadProfile(session.user);
      else setIsLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        setSession(session);
        setUser(session?.user ?? null);
        if (session?.user) await loadProfile(session.user);
        else setProfile(null);
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  async function loadProfile(user: User) {
    try {
      const discordId = user.user_metadata?.provider_id;

      const { data, error } = await supabase
        .from('usuarios_frontend')
        .select('*')
        .eq('discord_id', discordId)
        .eq('ativo', true)
        .single();

      if (error || !data) {
        await signOut();
        return;
      }

      setProfile(data);
    } finally {
      setIsLoading(false);
    }
  }

  async function signInWithDiscord() {
    await supabase.auth.signInWithOAuth({
      provider: 'discord',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
        scopes: 'identify guilds',
      },
    });
  }

  async function signOut() {
    await supabase.auth.signOut();
    setProfile(null);
  }

  const value: AuthContextType = {
    user,
    session,
    profile,
    isLoading,
    isSuperAdmin: profile?.role === 'superadmin',
    isAdmin: profile?.role === 'admin' || profile?.role === 'superadmin',
    isFuncionario: profile?.role === 'funcionario',
    signInWithDiscord,
    signOut,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be inside AuthProvider');
  return context;
};
```

### 6.3 ProtectedRoute.tsx

```typescript
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: ('superadmin' | 'admin' | 'funcionario')[];
}

export function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
  const { user, profile, isLoading } = useAuth();

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (!user || !profile) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(profile.role)) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <>{children}</>;
}
```

### 6.4 Estrutura de Rotas

```typescript
<Routes>
  {/* Públicas */}
  <Route path="/login" element={<Login />} />
  <Route path="/auth/callback" element={<AuthCallback />} />
  <Route path="/unauthorized" element={<Unauthorized />} />

  {/* Todos autenticados */}
  <Route path="/" element={
    <ProtectedRoute><Dashboard /></ProtectedRoute>
  } />
  <Route path="/empresas" element={
    <ProtectedRoute><Empresas /></ProtectedRoute>
  } />
  <Route path="/encomendas" element={
    <ProtectedRoute><Encomendas /></ProtectedRoute>
  } />
  <Route path="/estoque" element={
    <ProtectedRoute><Estoque /></ProtectedRoute>
  } />

  {/* Apenas Admin */}
  <Route path="/admin/usuarios" element={
    <ProtectedRoute allowedRoles={['superadmin', 'admin']}>
      <GerenciarUsuarios />
    </ProtectedRoute>
  } />
  <Route path="/financeiro" element={
    <ProtectedRoute allowedRoles={['superadmin', 'admin']}>
      <Financeiro />
    </ProtectedRoute>
  } />

  {/* Apenas Superadmin */}
  <Route path="/superadmin/*" element={
    <ProtectedRoute allowedRoles={['superadmin']}>
      <SuperAdminPanel />
    </ProtectedRoute>
  } />
</Routes>
```

---

## 7. Modificações no Bot Discord

O bot precisa ser atualizado para suportar múltiplas empresas por servidor.

### 7.1 Comando !bemvindo Atualizado

```python
@bot.command(name='bemvindo')
@commands.has_permissions(administrator=True)
async def bemvindo(ctx, membro: discord.Member, empresa_nome: str = None):
    """
    Registra funcionário e vincula a uma empresa.
    Uso: !bemvindo @usuario [nome_empresa]
    Se não especificar empresa, mostra lista para escolher.
    """
    guild_id = str(ctx.guild.id)

    # Buscar servidor
    servidor = await get_servidor_by_guild(guild_id)
    if not servidor:
        return await ctx.send("Servidor não configurado.")

    # Buscar empresas do servidor
    empresas = await get_empresas_servidor(servidor['id'])

    if len(empresas) == 0:
        return await ctx.send("Nenhuma empresa cadastrada neste servidor.")

    if len(empresas) == 1:
        empresa = empresas[0]
    elif empresa_nome:
        empresa = next((e for e in empresas if e['nome'].lower() == empresa_nome.lower()), None)
        if not empresa:
            return await ctx.send(f"Empresa '{empresa_nome}' não encontrada.")
    else:
        # Mostrar seleção de empresas
        embed = criar_embed_selecao_empresa(empresas)
        # ... lógica de seleção interativa

    # Criar/buscar funcionário
    funcionario = await get_or_create_funcionario(membro, servidor['id'])

    # Vincular funcionário à empresa
    await vincular_funcionario_empresa(funcionario['id'], empresa['id'])

    # Criar canal privado
    # ...
```

### 7.2 Nova Estrutura de Cache

```python
# Cache por servidor (não mais por guild_id diretamente)
servidores_cache: Dict[str, Dict] = {}      # guild_id -> servidor
empresas_cache: Dict[int, List[Dict]] = {}  # servidor_id -> [empresas]
funcionarios_cache: Dict[str, Dict] = {}    # channel_id -> funcionario
vinculos_cache: Dict[int, List[int]] = {}   # funcionario_id -> [empresa_ids]
```

---

## 8. Plano de Implementação

### Fase 1: Banco de Dados (Prioridade Alta)
1. [ ] Criar tabela `servidores`
2. [ ] Criar tabela `usuarios_frontend`
3. [ ] Criar tabela `funcionario_empresa`
4. [ ] Modificar tabela `empresas` (adicionar servidor_id)
5. [ ] Migrar dados existentes
6. [ ] Criar funções auxiliares RLS
7. [ ] Habilitar RLS em todas as tabelas
8. [ ] Criar políticas RLS

### Fase 2: Autenticação Frontend (Prioridade Alta)
1. [ ] Configurar Discord OAuth no Supabase
2. [ ] Criar AuthContext.tsx
3. [ ] Criar ProtectedRoute.tsx
4. [ ] Criar página de Login
5. [ ] Criar página de Callback
6. [ ] Criar página Unauthorized
7. [ ] Atualizar App.tsx com rotas protegidas

### Fase 3: Painel Admin (Prioridade Média)
1. [ ] Criar página GerenciarUsuarios
2. [ ] Implementar CRUD de usuários do frontend
3. [ ] Implementar seleção de role (admin/funcionario)
4. [ ] Criar página GerenciarEmpresas (múltiplas)

### Fase 4: Atualizar Bot Discord (Prioridade Média)
1. [ ] Atualizar comando !bemvindo para múltiplas empresas
2. [ ] Atualizar comando !configurar para criar servidor automaticamente
3. [ ] Atualizar cache para nova estrutura
4. [ ] Adicionar comando !empresas (listar empresas do servidor)
5. [ ] Atualizar comandos para aceitar empresa como parâmetro

### Fase 5: Superadmin Panel (Prioridade Baixa)
1. [ ] Criar dashboard com todos os servidores
2. [ ] Implementar métricas gerais
3. [ ] Criar gestão de planos/assinaturas

### Fase 6: Sistema de Pagamentos (Futuro)
1. [ ] Escolher gateway (Stripe/Mercado Pago/Asaas)
2. [ ] Implementar checkout
3. [ ] Implementar webhooks de pagamento
4. [ ] Criar lógica de ativação/desativação por assinatura

---

## 9. Considerações de Segurança

### 9.1 Checklist de Segurança

- [ ] RLS habilitado em TODAS as tabelas
- [ ] Funções SECURITY DEFINER para operações sensíveis
- [ ] Validação de discord_id no JWT
- [ ] Sem chaves de service_role no frontend
- [ ] Rate limiting nas APIs
- [ ] Logs de auditoria para operações críticas

### 9.2 Variáveis de Ambiente

```env
# Frontend (APENAS anon key)
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...  # Apenas anon key!

# Backend Bot (pode ter service_role para operações admin)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...    # Service role (nunca expor)
DISCORD_TOKEN=xxx
```

### 9.3 Inserir Superadmin (Você)

```sql
-- Executar uma vez após criar as tabelas
INSERT INTO usuarios_frontend (discord_id, guild_id, role)
VALUES ('SEU_DISCORD_ID', NULL, 'superadmin');
```

---

## 10. Estimativa de Esforço

| Fase | Complexidade | Dependências |
|------|--------------|--------------|
| 1. Banco de Dados | Média | Nenhuma |
| 2. Auth Frontend | Alta | Fase 1 |
| 3. Painel Admin | Média | Fase 2 |
| 4. Bot Discord | Média | Fase 1 |
| 5. Superadmin | Baixa | Fase 2, 3 |
| 6. Pagamentos | Alta | Fase 5 |

---

## 11. Próximos Passos

1. **Imediato:** Implementar Fase 1 (Banco de Dados)
2. **Curto prazo:** Implementar Fase 2 (Auth)
3. **Médio prazo:** Fases 3 e 4 (Admin + Bot)
4. **Longo prazo:** Fases 5 e 6 (Superadmin + Pagamentos)

---

**Documento aprovado em:** 2026-01-20
**Autor:** Claude + Wagner
