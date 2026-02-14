-- Enforce one free trial per Discord user across all guilds

-- 1) Guardrail at data level: only one non-null trial per discord user
CREATE UNIQUE INDEX IF NOT EXISTS ux_assinaturas_trial_per_discord
ON public.assinaturas (pagador_discord_id)
WHERE tipo = 'trial' AND pagador_discord_id IS NOT NULL;

-- 2) Guardrail at business level in RPC
CREATE OR REPLACE FUNCTION public.criar_trial(
  p_guild_id text,
  p_pagador_discord_id text DEFAULT NULL::text
)
RETURNS TABLE(resultado text, mensagem text)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
DECLARE
  v_existing record;
BEGIN
  -- Require user identity to bind trial ownership
  IF p_pagador_discord_id IS NULL OR btrim(p_pagador_discord_id) = '' THEN
    RETURN QUERY SELECT
      'invalid_user'::text,
      'Não foi possível identificar o usuário Discord para ativar o trial.'::text;
    RETURN;
  END IF;

  -- Check if guild already has any subscription
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
      AND a.pagador_discord_id = p_pagador_discord_id
  ) THEN
    RETURN QUERY SELECT
      'already_used_user'::text,
      'Este usuário já ativou o período de teste gratuito em outro servidor.'::text;
    RETURN;
  END IF;

  -- If guild has active paid subscription, skip trial
  IF v_existing IS NOT NULL AND v_existing.status = 'ativa' AND v_existing.data_expiracao > NOW() THEN
    RETURN QUERY SELECT
      'has_active'::text,
      'Este servidor já possui uma assinatura ativa.'::text;
    RETURN;
  END IF;

  -- Create / update subscription as trial for this guild
  IF v_existing IS NOT NULL THEN
    UPDATE public.assinaturas
    SET
      tipo = 'trial',
      plano_id = NULL,
      status = 'ativa',
      data_inicio = NOW(),
      data_expiracao = NOW() + INTERVAL '3 days',
      pagador_discord_id = p_pagador_discord_id,
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
    )
    VALUES (
      p_guild_id,
      'trial',
      NULL,
      'ativa',
      NOW(),
      NOW() + INTERVAL '3 days',
      p_pagador_discord_id
    );
  END IF;

  RETURN QUERY SELECT
    'success'::text,
    'Período de teste de 3 dias ativado com sucesso!'::text;

EXCEPTION
  WHEN unique_violation THEN
    RETURN QUERY SELECT
      'already_used_user'::text,
      'Este usuário já ativou o período de teste gratuito em outro servidor.'::text;
END;
$function$;
