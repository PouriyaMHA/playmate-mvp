-- PlayMate migration 003 — run once in Supabase → SQL Editor (safe to re-run).
--
-- delete_account_data(uid): removes everything PlayMate stores about one account — likes sent and received, blocks
-- and reports either way, every game profile and the reserved username — in ONE transaction: either all of it is
-- gone or none of it (before, six separate requests could stop halfway). The login itself is deleted afterwards
-- by the server through Supabase Auth. Returns how many rows went, per table.
--
-- Only the server may call it (secret key = service_role); browsers can't reach it through the REST API.

create or replace function public.delete_account_data(uid uuid)
returns jsonb
language plpgsql
volatile
set search_path = public
as $$
declare
  n_likes int; n_blocks int; n_profiles int; n_accounts int;
begin
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

notify pgrst, 'reload schema';
