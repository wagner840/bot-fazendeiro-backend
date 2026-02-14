-- Free trial pipeline: click in frontend -> intent -> consume on bot join
-- Keeps /configurar protected while enabling trial activation without manual command.

CREATE TABLE IF NOT EXISTS public.trial_intents (
  id BIGSERIAL PRIMARY KEY,
  discord_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pending', 'consumed', 'expired', 'cancelled')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL,
  consumed_at TIMESTAMPTZ NULL,
  consumed_guild_id TEXT NULL,
  source TEXT NOT NULL DEFAULT 'frontend_click',
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_trial_intents_pending_discord
  ON public.trial_intents (discord_id, created_at DESC)
  WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_trial_intents_pending_expires
  ON public.trial_intents (expires_at)
  WHERE status = 'pending';

ALTER TABLE public.trial_intents ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.trial_intents FROM PUBLIC;
GRANT SELECT, INSERT ON public.trial_intents TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.trial_intents TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.trial_intents_id_seq TO authenticated, service_role;

DROP POLICY IF EXISTS trial_intents_select_own ON public.trial_intents;
CREATE POLICY trial_intents_select_own
ON public.trial_intents
FOR SELECT
TO authenticated
USING (
  discord_id = COALESCE(
    auth.jwt() ->> 'provider_id',
    auth.jwt() -> 'user_metadata' ->> 'provider_id'
  )
);

DROP POLICY IF EXISTS trial_intents_insert_own ON public.trial_intents;
CREATE POLICY trial_intents_insert_own
ON public.trial_intents
FOR INSERT
TO authenticated
WITH CHECK (
  discord_id = COALESCE(
    auth.jwt() ->> 'provider_id',
    auth.jwt() -> 'user_metadata' ->> 'provider_id'
  )
);

CREATE OR REPLACE FUNCTION public.criar_trial_intent(p_discord_id text)
RETURNS TABLE(resultado text, mensagem text, intent_id bigint)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $$
DECLARE
  v_discord_id text := NULLIF(BTRIM(p_discord_id), '');
  v_existing_pending_id bigint;
BEGIN
  IF v_discord_id IS NULL THEN
    RETURN QUERY SELECT
      'invalid_user'::text,
      'Não foi possível identificar o usuário Discord para ativar o trial.'::text,
      NULL::bigint;
    RETURN;
  END IF;

  -- Global one-time trial guard
  IF EXISTS (
    SELECT 1
    FROM public.assinaturas a
    WHERE a.tipo = 'trial'
      AND a.pagador_discord_id = v_discord_id
  ) THEN
    RETURN QUERY SELECT
      'already_used_user'::text,
      'Este usuário já ativou o período de teste gratuito em outro servidor.'::text,
      NULL::bigint;
    RETURN;
  END IF;

  -- Expire stale intents from this user
  UPDATE public.trial_intents
  SET status = 'expired'
  WHERE discord_id = v_discord_id
    AND status = 'pending'
    AND expires_at <= NOW();

  -- Reuse active pending intent to avoid duplicates
  SELECT ti.id
  INTO v_existing_pending_id
  FROM public.trial_intents ti
  WHERE ti.discord_id = v_discord_id
    AND ti.status = 'pending'
    AND ti.expires_at > NOW()
  ORDER BY ti.created_at DESC
  LIMIT 1;

  IF v_existing_pending_id IS NOT NULL THEN
    RETURN QUERY SELECT
      'pending_exists'::text,
      'Intenção de trial já criada. Adicione o bot no servidor para concluir a ativação.'::text,
      v_existing_pending_id;
    RETURN;
  END IF;

  INSERT INTO public.trial_intents (
    discord_id,
    status,
    expires_at,
    source
  )
  VALUES (
    v_discord_id,
    'pending',
    NOW() + INTERVAL '30 minutes',
    'frontend_click'
  )
  RETURNING id INTO v_existing_pending_id;

  RETURN QUERY SELECT
    'success'::text,
    'Intenção de trial registrada. Adicione o bot no servidor para ativar 3 dias de teste.'::text,
    v_existing_pending_id;
END;
$$;

CREATE OR REPLACE FUNCTION public.consumir_trial_intent(p_discord_id text, p_guild_id text)
RETURNS TABLE(resultado text, mensagem text)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $$
DECLARE
  v_discord_id text := NULLIF(BTRIM(p_discord_id), '');
  v_guild_id text := NULLIF(BTRIM(p_guild_id), '');
  v_intent_id bigint;
  v_trial_result record;
BEGIN
  IF v_discord_id IS NULL THEN
    RETURN QUERY SELECT
      'invalid_user'::text,
      'Não foi possível identificar o usuário Discord para consumir o trial.'::text;
    RETURN;
  END IF;

  IF v_guild_id IS NULL THEN
    RETURN QUERY SELECT
      'invalid_guild'::text,
      'Guild inválida para consumo do trial.'::text;
    RETURN;
  END IF;

  -- Expire stale intents first
  UPDATE public.trial_intents
  SET status = 'expired'
  WHERE discord_id = v_discord_id
    AND status = 'pending'
    AND expires_at <= NOW();

  -- Lock one pending intent to avoid concurrent double-consume
  SELECT ti.id
  INTO v_intent_id
  FROM public.trial_intents ti
  WHERE ti.discord_id = v_discord_id
    AND ti.status = 'pending'
    AND ti.expires_at > NOW()
  ORDER BY ti.created_at DESC
  LIMIT 1
  FOR UPDATE SKIP LOCKED;

  IF v_intent_id IS NULL THEN
    RETURN QUERY SELECT
      'no_intent'::text,
      'Nenhuma intenção de trial pendente para este usuário.'::text;
    RETURN;
  END IF;

  -- Mark consumed before activation attempt (short lock scope)
  UPDATE public.trial_intents
  SET
    status = 'consumed',
    consumed_at = NOW(),
    consumed_guild_id = v_guild_id
  WHERE id = v_intent_id;

  SELECT *
  INTO v_trial_result
  FROM public.criar_trial(v_guild_id, v_discord_id)
  LIMIT 1;

  IF v_trial_result.resultado <> 'success' THEN
    UPDATE public.trial_intents
    SET
      status = 'cancelled',
      metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'cancel_reason', v_trial_result.resultado,
        'cancel_message', v_trial_result.mensagem
      )
    WHERE id = v_intent_id;
  END IF;

  RETURN QUERY SELECT
    COALESCE(v_trial_result.resultado, 'error')::text,
    COALESCE(v_trial_result.mensagem, 'Falha ao ativar trial.')::text;
END;
$$;

GRANT EXECUTE ON FUNCTION public.criar_trial_intent(text) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.consumir_trial_intent(text, text) TO service_role;
