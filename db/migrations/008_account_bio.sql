-- PlayMate migration 008 — run once in Supabase → SQL Editor (safe to re-run).
--
-- accounts.bio becomes the ONE source of truth for a player's bio (it lived in the Auth user's app_metadata, which
-- the server rewrites as a whole object — two edits at once could bring an old bio back). The match list reads the
-- bios of the 20 players it returns from here in one query (pre-launch #2: bio on the match card).
--
-- An empty string means "cleared on purpose"; NULL means "never set". The backfill only fills NULLs, so re-running
-- this file can never bring back a bio that was cleared or edited since.

begin;

alter table public.accounts add column if not exists bio text;

update public.accounts a
   set bio = left(regexp_replace(btrim(u.raw_app_meta_data -> 'playmate' ->> 'bio'), '[<>]', '', 'g'), 280)
  from auth.users u
 where u.id = a.user_id
   and a.bio is null
   and coalesce(btrim(u.raw_app_meta_data -> 'playmate' ->> 'bio'), '') <> '';

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'accounts_bio_check') then
    alter table public.accounts add constraint accounts_bio_check
      check (bio is null or (char_length(bio) <= 280 and bio !~ '[<>]'));
  end if;
end $$;

commit;

notify pgrst, 'reload schema';

-- Check: accounts with a bio / accounts
select count(nullif(bio, '')) as with_bio, count(*) as accounts from public.accounts;
