-- Hardens trial activation and subscription status checks for production flow
-- Goals:
-- 1) Keep /configurar blocked without active subscription
-- 2) Ensure free-trial activation binds to a Discord user reliably
-- 3) Enforce global one-time trial per Discord user
-- 4) Return consistent days remaining (ceil) for countdown UX

CREATE UNIQUE INDEX IF NOT EXISTS ux_assinaturas_trial_per_discord
ON public.assinaturas (pagador_discord_id)
WHERE tipo = 'trial' AND pagador_discord_id IS NOT NULL;

CREATE OR REPLACE FUNCTION public.verificar_assinatura(p_guild_id text)
RETURNS TABLE(
  ativa boolean,
  status text,
  dias_restantes integer,
  data_expiracao timestamptz,
  plano_nome text,
  tipo text
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_sub record;
BEGIN
  -- Tester has full temporary access
  IF EXISTS (
    SELECT 1
    FROM public.testers t
    WHERE t.guild_id = p_guild_id
      AND t.ativo = true
  ) THEN
    RETURN QUERY
    SELECT
      true,
      'tester'::text,
      999,
      (NOW() + INTERVAL '999 days')::timestamptz,
      'Tester (Acesso Gratuito)'::text,
      'tester'::text;
    RETURN;
  END IF;

  SELECT
    a.status,
    a.data_expiracao,
    a.tipo,
    p.nome AS plano_nome
  INTO v_sub
  FROM public.assinaturas a
  LEFT JOIN public.planos p ON p.id = a.plano_id
  WHERE a.guild_id = p_guild_id
  ORDER BY a.data_expiracao DESC
  LIMIT 1;

  IF NOT FOUND THEN
    RETURN QUERY
    SELECT
      false,
      NULL::text,
      0,
      NULL::timestamptz,
      NULL::text,
      NULL::text;
    RETURN;
  END IF;

  RETURN QUERY
  SELECT
    (v_sub.status = 'ativa' AND v_sub.data_expiracao > NOW()),
    v_sub.status::text,
    GREATEST(
      0,
      CEIL(EXTRACT(EPOCH FROM (v_sub.data_expiracao - NOW())) / 86400.0)::integer
    ),
    v_sub.data_expiracao::timestamptz,
    COALESCE(
      v_sub.plano_nome::text,
      CASE WHEN v_sub.tipo = 'trial' THEN 'Trial Gratuito (3 dias)' ELSE NULL END
    ),
    v_sub.tipo::text;
END;
$$;

CREATE OR REPLACE FUNCTION public.criar_trial(
  p_guild_id text,
  p_pagador_discord_id text DEFAULT NULL
)
RETURNS TABLE(resultado text, mensagem text)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_existing record;
  v_discord_id text := NULLIF(BTRIM(p_pagador_discord_id), '');
BEGIN
  IF p_guild_id IS NULL OR BTRIM(p_guild_id) = '' THEN
    RETURN QUERY SELECT 'invalid_guild'::text, 'Guild inválida para ativação do trial.'::text;
    RETURN;
  END IF;

  -- Fallback when frontend/session does not send Discord ID
  IF v_discord_id IS NULL THEN
    SELECT uf.discord_id
    INTO v_discord_id
    FROM public.usuarios_frontend uf
    WHERE uf.guild_id = p_guild_id
      AND uf.ativo = true
      AND uf.role IN ('superadmin', 'admin')
    ORDER BY
      CASE WHEN uf.role = 'superadmin' THEN 0 ELSE 1 END,
      uf.id ASC
    LIMIT 1;
  END IF;

  IF v_discord_id IS NULL THEN
    SELECT s.proprietario_discord_id
    INTO v_discord_id
    FROM public.servidores s
    WHERE s.guild_id = p_guild_id
      AND s.ativo = true
    ORDER BY s.id DESC
    LIMIT 1;
  END IF;

  IF v_discord_id IS NULL OR BTRIM(v_discord_id) = '' THEN
    RETURN QUERY SELECT
      'invalid_user'::text,
      'Não foi possível identificar o usuário Discord para ativar o trial.'::text;
    RETURN;
  END IF;

  SELECT a.id, a.status, a.tipo, a.data_expiracao
  INTO v_existing
  FROM public.assinaturas a
  WHERE a.guild_id = p_guild_id
  LIMIT 1;

  -- Guild-level one-time trial
  IF v_existing IS NOT NULL AND v_existing.tipo = 'trial' THEN
    RETURN QUERY SELECT
      'already_used'::text,
      'Este servidor já utilizou o período de teste gratuito.'::text;
    RETURN;
  END IF;

  -- User-level one-time trial across all guilds
  IF EXISTS (
    SELECT 1
    FROM public.assinaturas a
    WHERE a.tipo = 'trial'
      AND a.pagador_discord_id = v_discord_id
  ) THEN
    RETURN QUERY SELECT
      'already_used_user'::text,
      'Este usuário já ativou o período de teste gratuito em outro servidor.'::text;
    RETURN;
  END IF;

  -- If guild has active paid subscription, skip trial
  IF v_existing IS NOT NULL
     AND v_existing.status = 'ativa'
     AND v_existing.data_expiracao > NOW()
     AND COALESCE(v_existing.tipo, 'paga') <> 'trial' THEN
    RETURN QUERY SELECT
      'has_active'::text,
      'Este servidor já possui uma assinatura ativa.'::text;
    RETURN;
  END IF;

  -- Create / update as trial
  IF v_existing IS NOT NULL THEN
    UPDATE public.assinaturas
    SET
      tipo = 'trial',
      plano_id = NULL,
      status = 'ativa',
      data_inicio = NOW(),
      data_expiracao = NOW() + INTERVAL '3 days',
      pagador_discord_id = v_discord_id,
      updated_at = NOW()
    WHERE guild_id = p_guild_id;
  ELSE
    INSERT INTO public.assinaturas (
      guild_id,
      tipo,
      plano_id,
      status,
      data_inicio,
      data_expiracao,
      pagador_discord_id
    ) VALUES (
      p_guild_id,
      'trial',
      NULL,
      'ativa',
      NOW(),
      NOW() + INTERVAL '3 days',
      v_discord_id
    );
  END IF;

  -- Keep tenant mirror fields aligned when tenant exists
  UPDATE public.servidores
  SET
    assinatura_ativa = true,
    plano = 'trial'
  WHERE guild_id = p_guild_id;

  RETURN QUERY SELECT
    'success'::text,
    'Período de teste de 3 dias ativado com sucesso!'::text;

EXCEPTION
  WHEN unique_violation THEN
    RETURN QUERY SELECT
      'already_used_user'::text,
      'Este usuário já ativou o período de teste gratuito em outro servidor.'::text;
END;
$$;

GRANT EXECUTE ON FUNCTION public.criar_trial(text, text) TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.verificar_assinatura(text) TO anon, authenticated, service_role;
