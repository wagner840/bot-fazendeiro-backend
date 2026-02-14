-- Explicit policy for service role on webhook_events.

do $$
begin
  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'webhook_events'
      and policyname = 'webhook_events_service_role_all'
  ) then
    create policy "webhook_events_service_role_all"
      on public.webhook_events
      as permissive
      for all
      to service_role
      using (true)
      with check (true);
  end if;
end
$$;
