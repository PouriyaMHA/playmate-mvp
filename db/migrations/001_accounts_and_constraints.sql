-- PlayMate migration 001 — run once in Supabase → SQL Editor (safe to re-run).
--
-- 1. accounts: one row per user that reserves the PlayMate username for good. Before this, the name lived only on
--    game profiles, so two people could grab the same name at the same moment, and deleting your last game freed it.
-- 2. likes: a person can like another person only once per game (double clicks / two tabs can't duplicate it).
-- 3. indexes for the queries the app runs on every page and every 15-second refresh.
--
-- Checked before writing this (2026-10-18): no username is used by two different users, no duplicate likes.

begin;

create table if not exists public.accounts (
  user_id          uuid primary key references auth.users (id) on delete cascade,
  username         text not null check (username ~ '^[a-z0-9_.-]{3,24}$'),   -- canonical, lowercase
  display_username text not null,                                           -- as the player typed it
  created_at       timestamptz not null default now()
);
create unique index if not exists accounts_username_key on public.accounts (username);

-- No policies on purpose: only the server (secret key) reads and writes this table.
alter table public.accounts enable row level security;

-- Existing players keep the name they already have.
insert into public.accounts (user_id, username, display_username)
select distinct on (p.user_id)
       p.user_id, lower(p.username), coalesce(nullif(p.display_username, ''), p.username)
from public.profiles p
where p.user_id is not null
  and lower(p.username) ~ '^[a-z0-9_.-]{3,24}$'
order by p.user_id, p.created_at nulls last
on conflict (user_id) do nothing;

create unique index if not exists likes_unique_pair on public.likes (from_user_id, to_user_id, game);
create index if not exists likes_to_user_game        on public.likes (to_user_id, game);
create index if not exists profiles_user_id          on public.profiles (user_id);
create index if not exists profiles_game_region_seen on public.profiles (game, region, last_active desc);
create index if not exists blocks_blocked_id         on public.blocks (blocked_id);

commit;

-- Check: every player should now have exactly one account row.
select (select count(distinct user_id) from public.profiles where user_id is not null) as players,
       (select count(*) from public.accounts) as accounts;
