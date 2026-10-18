-- PlayMate migration 005 — run once in Supabase → SQL Editor (safe to re-run).
--
-- 1. accounts.avatar becomes the ONE source of truth for a player's avatar (it used to live only in the Auth user's
--    app_metadata and was copied onto every game profile). Every avatar change and every copy onto the profiles
--    first locks the player's accounts row, so they run one after another and a copy always uses the newest value —
--    an older request can no longer overwrite a newer avatar (Codex review 6, R6-M02).
-- 2. profiles / likes / blocks get foreign keys to auth.users with ON DELETE CASCADE: a save that was still in flight
--    while the account was deleted can no longer leave an orphan public profile (or like/block) behind (R6-M01).
--    Checked before writing this (2026-10-18): no orphan rows in production.
--
-- Functions: only the server may call them (secret key = service_role).

begin;

alter table public.accounts add column if not exists avatar text;
update public.accounts a
   set avatar = nullif(u.raw_app_meta_data -> 'playmate' ->> 'avatar', '')
  from auth.users u
 where u.id = a.user_id and a.avatar is null;

-- copy the account avatar onto every game profile (only the game_meta.avatar key); waits for any avatar change
-- of this player that is still running, then uses the newest value
create or replace function public.sync_profile_avatar(uid uuid)
returns int
language plpgsql
volatile
set search_path = public
as $$
declare
  v text;
  n int;
begin
  select avatar into v from accounts where user_id = uid for update;
  if not found then
    return 0;
  end if;
  update profiles
     set game_meta = case when v is null then coalesce(game_meta, '{}'::jsonb) - 'avatar'
                          else jsonb_set(coalesce(game_meta, '{}'::jsonb), '{avatar}', to_jsonb(v)) end
   where user_id = uid and (game_meta ->> 'avatar') is distinct from v;
  get diagnostics n = row_count;
  return n;
end;
$$;

-- change the avatar ('' = none) and copy it onto the profiles, in one transaction
create or replace function public.set_account_avatar(uid uuid, a text)
returns int
language plpgsql
volatile
set search_path = public
as $$
begin
  update accounts set avatar = nullif(a, '') where user_id = uid;   -- holds the row lock until commit
  return sync_profile_avatar(uid);
end;
$$;

revoke all on function public.sync_profile_avatar(uuid) from public, anon, authenticated;
revoke all on function public.set_account_avatar(uuid, text) from public, anon, authenticated;
grant execute on function public.sync_profile_avatar(uuid) to service_role;
grant execute on function public.set_account_avatar(uuid, text) to service_role;

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'profiles_user_id_fkey') then
    alter table public.profiles add constraint profiles_user_id_fkey
      foreign key (user_id) references auth.users (id) on delete cascade;
  end if;
  if not exists (select 1 from pg_constraint where conname = 'likes_from_user_id_fkey') then
    alter table public.likes add constraint likes_from_user_id_fkey
      foreign key (from_user_id) references auth.users (id) on delete cascade;
  end if;
  if not exists (select 1 from pg_constraint where conname = 'likes_to_user_id_fkey') then
    alter table public.likes add constraint likes_to_user_id_fkey
      foreign key (to_user_id) references auth.users (id) on delete cascade;
  end if;
  if not exists (select 1 from pg_constraint where conname = 'blocks_blocker_id_fkey') then
    alter table public.blocks add constraint blocks_blocker_id_fkey
      foreign key (blocker_id) references auth.users (id) on delete cascade;
  end if;
  if not exists (select 1 from pg_constraint where conname = 'blocks_blocked_id_fkey') then
    alter table public.blocks add constraint blocks_blocked_id_fkey
      foreign key (blocked_id) references auth.users (id) on delete cascade;
  end if;
end $$;

commit;

notify pgrst, 'reload schema';

-- Check: every player's avatar copied over (accounts with an avatar / accounts)
select count(avatar) as with_avatar, count(*) as accounts from public.accounts;
