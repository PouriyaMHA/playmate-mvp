-- PlayMate migration 006 — run once in Supabase → SQL Editor (safe to re-run).
--
-- 1. delete_account_data(uid) now locks the player's accounts row FIRST, like set_account_avatar /
--    sync_profile_avatar (migration 005) do. Every function that touches one player's account and profiles takes the
--    locks in the same order (accounts → profiles), so an account deletion and an avatar change at the same moment
--    queue up instead of deadlocking (Codex review 7, R7-M02).
-- 2. set_profile_avatar (migration 004) is retired: it copied an avatar given by the caller, bypassing
--    accounts.avatar (the source of truth since 005). The app no longer calls it.
--
-- Only the server may call these (secret key = service_role).

create or replace function public.delete_account_data(uid uuid)
returns jsonb
language plpgsql
volatile
set search_path = public
as $$
declare
  n_likes int; n_blocks int; n_profiles int; n_accounts int;
begin
  perform 1 from accounts where user_id = uid for update;   -- same lock order as the avatar functions
  delete from likes where from_user_id = uid or to_user_id = uid;
  get diagnostics n_likes = row_count;
  delete from blocks where blocker_id = uid or blocked_id = uid;
  get diagnostics n_blocks = row_count;
  delete from profiles where user_id = uid;
  get diagnostics n_profiles = row_count;
  delete from accounts where user_id = uid;
  get diagnostics n_accounts = row_count;
  return jsonb_build_object('likes', n_likes, 'blocks', n_blocks, 'profiles', n_profiles, 'accounts', n_accounts);
end;
$$;

revoke all on function public.delete_account_data(uuid) from public, anon, authenticated;
grant execute on function public.delete_account_data(uuid) to service_role;

drop function if exists public.set_profile_avatar(uuid, text);

notify pgrst, 'reload schema';
