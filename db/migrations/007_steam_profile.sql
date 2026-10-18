-- PlayMate migration 007 — run once in Supabase → SQL Editor (safe to re-run).
--
-- profiles.steam_profile: an optional Steam profile for Steam games played on PC, stored as the path after
-- https://steamcommunity.com/ ("id/<custom>" or "profiles/<SteamID64>"; the server validates and normalizes it).
-- Private like in_game_username / discord_username: only the owner and mutual squadmates ever see it.

alter table public.profiles add column if not exists steam_profile text;

notify pgrst, 'reload schema';
