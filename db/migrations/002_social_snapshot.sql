-- PlayMate migration 002 — run once in Supabase → SQL Editor (safe to re-run).
--
-- social_snapshot(viewer, g, with_profiles): everything the server needs about one player's likes in one game —
-- likes in both directions, blocks (either way, any game) and the other players' profiles — read by ONE SQL
-- statement, so from ONE snapshot. Contact info is therefore only ever returned together with the likes and blocks
-- that allow it (Codex review 3, R3-H03), and the answer is a single JSON value, so PostgREST's 1000-row cap can't
-- cut the lists short (R3-M03). Blocked players' profiles are never returned.
--
-- Only the server may call it (secret key = service_role); browsers can't reach it through the REST API.

create or replace function public.social_snapshot(viewer uuid, g text, with_profiles boolean default true)
returns jsonb
language sql
stable
set search_path = public
as $$
  with l as (
    select from_user_id, to_user_id, created_at
    from likes
    where game = g and (from_user_id = viewer or to_user_id = viewer)
  ), b as (
    select case when blocker_id = viewer then blocked_id else blocker_id end as other
    from blocks
    where blocker_id = viewer or blocked_id = viewer
  )
  select jsonb_build_object(
    'likes',    coalesce((select jsonb_agg(to_jsonb(l)) from l), '[]'::jsonb),
    'blocked',  coalesce((select jsonb_agg(distinct b.other) from b where b.other is not null), '[]'::jsonb),
    'profiles', coalesce((
      select jsonb_agg(to_jsonb(p))
      from profiles p
      where with_profiles
        and p.game = g
        and p.user_id in (select case when from_user_id = viewer then to_user_id else from_user_id end from l)
        and p.user_id not in (select other from b where other is not null)
    ), '[]'::jsonb)
  );
$$;

revoke all on function public.social_snapshot(uuid, text, boolean) from public, anon, authenticated;
grant execute on function public.social_snapshot(uuid, text, boolean) to service_role;

notify pgrst, 'reload schema';
