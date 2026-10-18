"""Supported games and their per-game profile templates.

Adding a game = adding an entry here (and its art in static/img/games/).
Each game defines:
  - platforms: options for the platform field
  - ign_label: what the in-game name is called for that game
  - fields: game-specific profile fields, stored in profiles.game_meta["fields"].
    Matching gives `weight` points when both players picked the same value — or, for fields with
    match="diff" (roles/positions), when they picked DIFFERENT values, because a squad needs mixed roles.
    `column` mirrors the value into an old profiles column (Battlefield only, for compatibility).
    `must_match` fields are hard filters: players with different values can't play together at all
    (Minecraft Java vs Bedrock, League of Legends servers).
  - crossplay (optional): groups of platforms that can play together. Default: every platform together.
    Players on platforms from different groups are never matched.
  - crossplay_note (optional): one line shown under the form explaining the filter.
"""
from pathlib import Path

from locations import REGIONS, region_label  # noqa: F401  (re-exported for main.py)

LANGUAGES = [
    {"code": "en", "label": "English"},
    {"code": "fa", "label": "Persian"},
    {"code": "tr", "label": "Turkish"},
    {"code": "ar", "label": "Arabic"},
    {"code": "de", "label": "German"},
    {"code": "fr", "label": "French"},
    {"code": "es", "label": "Spanish"},
    {"code": "ru", "label": "Russian"},
]

PC_CONSOLE = ["PC", "PlayStation", "Xbox"]


def _field(fid, label, options, weight, required=True, column=None, match="same", must_match=False):
    f = {"id": fid, "label": label, "options": options, "weight": weight, "required": required, "match": match}
    if must_match:
        f["must_match"] = True
    if column:
        f["column"] = column
    return f


GAMES = {
    "battlefield": {
        "name": "Battlefield 6",
        "short": "BF6",
        "genre": "Large-scale FPS",
        "accent": "#ff8a3d",
        "platforms": PC_CONSOLE,
        "ign_label": "EA ID",
        "fields": [
            _field("favorite_mode", "Favorite mode", ["Conquest", "Breakthrough", "Rush", "Team Deathmatch", "REDSEC", "Portal"], 18, column="favorite_mode"),
            _field("class_type", "Class", ["Assault", "Engineer", "Support", "Recon", "Vehicle Main"], 8,
                   required=False, column="class_type", match="diff"),
        ],
    },
    "cs2": {
        "name": "Counter-Strike 2",
        "short": "CS2",
        "genre": "Tactical shooter",
        "accent": "#f5b942",
        "platforms": ["PC"],
        "ign_label": "Steam name",
        "fields": [
            _field("mode", "Mode", ["Premier", "Competitive", "Wingman", "Casual", "Deathmatch", "FACEIT"], 12),
            _field("rank", "Rank", ["Unranked", "Silver", "Gold Nova", "Master Guardian", "Legendary Eagle", "Supreme / Global"], 10),
        ],
    },
    "fortnite": {
        "name": "Fortnite",
        "short": "FN",
        "genre": "Battle royale",
        "accent": "#a855f7",
        "platforms": ["PC", "PlayStation", "Xbox", "Switch", "Mobile"],
        "ign_label": "Epic name",
        "fields": [
            _field("mode", "Mode", ["Battle Royale", "Zero Build", "Ranked", "Reload", "Creative"], 14),
            _field("rank", "Rank", ["Unranked", "Bronze", "Silver", "Gold", "Platinum", "Diamond", "Elite", "Champion", "Unreal"], 8),
            _field("style", "Playstyle", ["Casual", "Competitive", "Builder", "Box fighter"], 8),
        ],
    },
    "apex": {
        "name": "Apex Legends",
        "short": "APX",
        "genre": "Squad battle royale",
        "accent": "#ff4d4d",
        "platforms": ["PC", "PlayStation", "Xbox", "Switch"],
        "ign_label": "EA ID",
        "fields": [
            _field("mode", "Mode", ["Battle Royale", "Ranked", "Mixtape"], 12),
            _field("rank", "Rank", ["Unranked", "Rookie", "Bronze", "Silver", "Gold", "Platinum", "Diamond", "Master", "Predator"], 10),
        ],
    },
    "pubg-mobile": {
        "name": "PUBG Mobile",
        "short": "PUBG",
        "genre": "Mobile battle royale",
        "accent": "#f2c14e",
        "platforms": ["Android", "iOS"],
        "ign_label": "PUBG ID",
        "fields": [
            _field("server", "Server", ["Middle East", "Europe", "Asia", "North America", "South America", "KRJP"], 14),
            _field("mode", "Mode", ["Classic", "Ranked", "Arena / TDM", "Metro Royale"], 8),
            _field("tier", "Tier", ["Bronze", "Silver", "Gold", "Platinum", "Diamond", "Crown", "Ace", "Conqueror"], 8),
        ],
    },
    "codm": {
        "name": "Call of Duty: Mobile",
        "short": "CODM",
        "genre": "Mobile shooter",
        "accent": "#3ddc84",
        "platforms": ["Android", "iOS"],
        "ign_label": "CODM name",
        "fields": [
            _field("mode", "Mode", ["Ranked MP", "Battle Royale", "Casual MP", "Zombies"], 12),
            _field("rank", "Rank", ["Rookie", "Veteran", "Elite", "Pro", "Master", "Grandmaster", "Legendary"], 10),
        ],
    },
    "minecraft": {
        "name": "Minecraft",
        "short": "MC",
        "genre": "Sandbox",
        "accent": "#5bd65b",
        "platforms": ["PC", "PlayStation", "Xbox", "Switch", "Mobile"],
        "ign_label": "Minecraft name",
        "crossplay_note": "Java and Bedrock can't play together — you'll only see players on your edition.",
        "fields": [
            _field("edition", "Edition", ["Java", "Bedrock"], 14, must_match=True),
            _field("mode", "Mode", ["Survival", "Creative", "Hardcore", "Minigames / Servers", "Modded"], 10),
            _field("style", "Playstyle", ["Builder", "Explorer", "Redstone", "PvP", "Farmer"], 6),
        ],
    },
    "lol": {
        "name": "League of Legends",
        "short": "LoL",
        "genre": "MOBA",
        "accent": "#4fc3f7",
        "platforms": ["PC"],
        "ign_label": "Riot ID",
        "crossplay_note": "Accounts are tied to a server — you'll only see players on your server.",
        "fields": [
            _field("server", "Server", ["EUW", "EUNE", "NA", "TR", "ME", "KR", "OCE", "BR", "LAN"], 12, must_match=True),
            _field("role", "Main role", ["Top", "Jungle", "Mid", "ADC", "Support", "Fill"], 10, match="diff"),
            _field("rank", "Rank", ["Unranked", "Iron", "Bronze", "Silver", "Gold", "Platinum", "Emerald", "Diamond", "Master+"], 8),
        ],
    },
    "helldivers2": {
        "name": "Helldivers 2",
        "short": "HD2",
        "genre": "Co-op shooter",
        "accent": "#ffd23f",
        "platforms": ["PC", "PlayStation", "Xbox"],
        "ign_label": "In-game name",
        "fields": [
            _field("difficulty", "Difficulty", ["1–3 Easy", "4–6 Medium", "7–8 Hard", "9–10 Helldive"], 12),
            _field("front", "Favorite front", ["Terminids", "Automatons", "Illuminate", "Any"], 8),
        ],
    },
    "fc": {
        "name": "EA SPORTS FC 27",
        "short": "FC27",
        "genre": "Football",
        "accent": "#3fe0c5",
        "platforms": ["PC", "PlayStation", "Xbox", "Switch"],
        "crossplay": [["PC", "PlayStation", "Xbox"], ["Switch"]],
        "crossplay_note": "PC, PlayStation and Xbox play together; Switch players only match with Switch.",
        "ign_label": "EA ID",
        "fields": [
            _field("mode", "Mode", ["Clubs", "The Grounds", "Ultimate Team Co-op", "Seasons / Friendlies"], 14),
            _field("division", "Division", ["Div 10–8", "Div 7–5", "Div 4–2", "Div 1", "Elite"], 10),
            _field("position", "Position", ["Goalkeeper", "Defender", "Midfielder", "Forward", "Any"], 8,
                   required=False, match="diff"),
        ],
    },
    "gta": {
        "name": "GTA Online",
        "short": "GTA",
        "genre": "Open-world crime",
        "accent": "#ff5fa2",
        "platforms": ["PC", "PlayStation", "Xbox"],
        "crossplay": [["PC"], ["PlayStation"], ["Xbox"]],
        "crossplay_note": "No crossplay in GTA Online — you'll only see players on your platform.",
        "ign_label": "Rockstar ID",
        "fields": [
            _field("activity", "Activity", ["Heists", "Business / Grinding", "Races", "Missions", "Free roam", "PvP"], 14),
            _field("style", "Playstyle", ["Money grind", "Casual / fun", "Tryhard", "Roleplay"], 8),
        ],
    },
    "rocket-league": {
        "name": "Rocket League",
        "short": "RL",
        "genre": "Car soccer",
        "accent": "#3b8bff",
        "platforms": ["PC", "PlayStation", "Xbox", "Switch"],
        "ign_label": "Epic name",
        "fields": [
            _field("mode", "Mode", ["2v2 Doubles", "3v3 Standard", "Extra modes", "Casual", "Tournaments"], 14),
            _field("rank", "Rank", ["Unranked", "Bronze", "Silver", "Gold", "Platinum", "Diamond", "Champion",
                                    "Grand Champion", "Supersonic Legend"], 10),
        ],
    },
}

GAME_ORDER = ["battlefield", "cs2", "fortnite", "apex", "pubg-mobile", "codm", "minecraft", "lol", "helldivers2",
              "fc", "gta", "rocket-league"]


def get_game(game_id: str | None) -> dict | None:
    return GAMES.get((game_id or "").strip().lower())


PHOTO_DIR = Path(__file__).parent / "static" / "img" / "games" / "photos"
COVER_VERSION = 2  # bump when a photo in static/img/games/photos changes


def game_summary(game_id: str) -> dict:
    g = GAMES[game_id]
    art = f"/static/img/games/{game_id}.svg"
    has_photo = (PHOTO_DIR / f"{game_id}.jpg").is_file()
    return {
        "id": game_id,
        "name": g["name"],
        "short": g["short"],
        "genre": g["genre"],
        "accent": g["accent"],
        # official key art when we have it, our own SVG art otherwise (and as the fallback if the photo fails)
        "cover": f"/static/img/games/photos/{game_id}.jpg?v={COVER_VERSION}" if has_photo else art,
        "art": art,
        "icon": f"/static/img/games/{game_id}-icon.svg",
    }


def game_meta(game_id: str) -> dict:
    g = GAMES[game_id]
    return {
        **game_summary(game_id),
        "game": game_id,
        "platforms": g["platforms"],
        "ign_label": g["ign_label"],
        "fields": g["fields"],
        "crossplay_note": g.get("crossplay_note", ""),
        "regions": REGIONS,
        "languages": LANGUAGES,
        # kept for older clients (Battlefield page)
        "favorite_modes": next((f["options"] for f in g["fields"] if f["id"] == "favorite_mode"), []),
    }


def can_play_together(game_id: str, platform_a: str | None, platform_b: str | None,
                      fields_a: dict, fields_b: dict) -> bool:
    """False when two players can't be in the same match at all (no crossplay between their platforms,
    or a must_match field such as Minecraft edition / LoL server differs). Unknown values never block."""
    g = GAMES[game_id]
    groups = g.get("crossplay")
    if groups and platform_a and platform_b:
        group_a = next((i for i, grp in enumerate(groups) if platform_a in grp), None)
        group_b = next((i for i, grp in enumerate(groups) if platform_b in grp), None)
        if group_a is not None and group_b is not None and group_a != group_b:
            return False
    for f in g["fields"]:
        if f.get("must_match"):
            a, b = fields_a.get(f["id"]), fields_b.get(f["id"])
            if a and b and a != b:
                return False
    return True


def clean_fields(game_id: str, raw: dict | None) -> tuple[dict, list[str]]:
    """Keep only known fields with allowed values. Returns (fields, missing_required_labels)."""
    g = GAMES[game_id]
    raw = raw or {}
    out, missing = {}, []
    for f in g["fields"]:
        v = str(raw.get(f["id"]) or "").strip()
        if v and v in f["options"]:
            out[f["id"]] = v
        elif f["required"]:
            missing.append(f["label"])
    return out, missing
