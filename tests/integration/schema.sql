-- Self-contained copy of the production schema BEFORE the numbered migrations (db/migrations/*), for the CI
-- integration job only (tests/integration). Copied from the production catalog on 2026-10-18: columns, defaults,
-- constraints and unique indexes — including the legacy ones — RLS on, no policies, Supabase's roles and grants.
-- Never point this at a real database.

create extension if not exists pgcrypto;

-- Supabase roles (PostgREST switches to the JWT's "role"); service_role bypasses RLS like on Supabase
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then create role anon nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then create role authenticated nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'service_role') then create role service_role nologin bypassrls; end if;
end $$;
grant usage on schema public to anon, authenticated, service_role;
-- Supabase's default privileges: every new table/function in public is granted to all three API roles
alter default privileges in schema public grant all on tables to anon, authenticated, service_role;
alter default privileges in schema public grant all on sequences to anon, authenticated, service_role;
alter default privileges in schema public grant execute on functions to anon, authenticated, service_role;

create schema if not exists auth;
create table if not exists auth.users (
  id         uuid primary key default gen_random_uuid(),
  email      text,
  raw_app_meta_data jsonb default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table public.profiles (
  id               uuid primary key default gen_random_uuid(),
  username         text not null,
  platform         text,
  region           text,
  class_type       text,
  favorite_mode    text,
  languages        text,
  created_at       timestamptz default now(),
  mic              text,
  game             text not null default 'battlefield',
  city             text,
  in_game_username text,
  profile_pic_url  text,
  wallpaper_url    text,
  game_meta        jsonb not null default '{}'::jsonb,
  last_active      timestamptz,
  display_username text,
  user_id          uuid,
  looking_until    timestamptz,
  discord_username text,
  constraint profiles_user_id_game_unique unique (user_id, game)
);
create unique index profiles_game_ign_unique on public.profiles (game, lower(trim(in_game_username)))
  where in_game_username is not null and trim(in_game_username) <> '';
create unique index profiles_user_game_unique on public.profiles (user_id, game) where user_id is not null;
create unique index profiles_username_game_lower_uniq on public.profiles (lower(trim(username)), game);
create unique index profiles_username_game_unique on public.profiles (username, game);
create index profiles_user_id_idx on public.profiles (user_id);

create table public.likes (
  id           uuid primary key default gen_random_uuid(),
  from_user    text,
  to_user      text,
  game         text,
  created_at   timestamp not null default now(),
  from_user_id uuid,
  to_user_id   uuid,
  constraint unique_like_per_pair unique (from_user, to_user, game)
);
create index likes_from_user_id_idx on public.likes (from_user_id);
create index likes_to_user_id_idx on public.likes (to_user_id);
create unique index likes_lower_triplet_uniq on public.likes (lower(trim(from_user)), lower(trim(to_user)), game);
create unique index likes_unique_from_to_game on public.likes (from_user, to_user, game);
create unique index likes_unique_user_game on public.likes (from_user_id, to_user_id, game)
  where from_user_id is not null and to_user_id is not null;

create table public.blocks (
  id         uuid primary key default gen_random_uuid(),
  blocker_id uuid not null,
  blocked_id uuid not null,
  game       text not null default 'battlefield',
  reported   boolean not null default false,
  reason     text,
  created_at timestamptz not null default now(),
  constraint blocks_blocker_id_blocked_id_game_key unique (blocker_id, blocked_id, game)
);

alter table public.profiles enable row level security;
alter table public.likes enable row level security;
alter table public.blocks enable row level security;
