-- PlayMate migration 004 — run once in Supabase → SQL Editor (safe to re-run).
--
-- set_profile_avatar(uid, a): copy the account avatar onto every game profile of one player by changing ONLY the
-- game_meta.avatar key, in one statement. Before, the server read the whole game_meta, changed the avatar and wrote
-- the old object back — a profile edit saved in between was silently lost (Codex review 5, R5-M01).
-- a = '' removes the avatar. Returns how many profiles changed.
--
-- Only the server may call it (secret key = service_role); browsers can't reach it through the REST API.

create or replace function public.set_profile_avatar(uid uuid, a text)
returns int
language sql
volatile
set search_path = public
as $$
  with changed as (
    update profiles
    set game_meta = case when coalesce(a, '') = '' then coalesce(game_meta, '{}'::jsonb) - 'avatar'
                         else jsonb_set(coalesce(game_meta, '{}'::jsonb), '{avatar}', to_jsonb(a)) end
    where user_id = uid and (game_meta ->> 'avatar') is distinct from nullif(a, '')
    returning 1
  )
  select count(*)::int from changed;
$$;

revoke all on function public.set_profile_avatar(uuid, text) from public, anon, authenticated;
grant execute on function public.set_profile_avatar(uuid, text) to service_role;

notify pgrst, 'reload schema';
