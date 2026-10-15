"""Supported games and their per-game profile templates.

Adding a game = adding an entry here (and its art in static/img/games/).
Each game defines:
  - platforms: options for the platform field
  - ign_label: what the in-game name is called for that game
  - fields: game-specific profile fields, stored in profiles.game_meta["fields"].
    Matching gives `weight` points when both players picked the same value.
    `column` mirrors the value into an old profiles column (Battlefield only, for compatibility).
"""

REGIONS = [
    {"id": "na-west", "label": "North America West", "cities": ["Vancouver", "Seattle", "San Francisco", "Los Angeles"]},
    {"id": "na-east", "label": "North America East", "cities": ["Toronto", "New York", "Montreal", "Chicago"]},
    {"id": "eu-west", "label": "Europe West", "cities": ["London", "Paris", "Amsterdam", "Madrid"]},
    {"id": "eu-central", "label": "Europe Central", "cities": ["Frankfurt", "Berlin", "Vienna", "Stockholm"]},
    {"id": "middle-east", "label": "Middle East", "cities": ["Tehran", "Istanbul", "Dubai", "Mashhad", "Shiraz", "Isfahan"]},
    {"id": "asia", "label": "Asia", "cities": ["Tokyo", "Seoul", "Singapore", "Mumbai"]},
    {"id": "oceania", "label": "Oceania", "cities": ["Sydney", "Melbourne", "Auckland"]},
    {"id": "south-america", "label": "South America", "cities": ["São Paulo", "Buenos Aires", "Santiago"]},
]

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


def _field(fid, label, options, weight, required=True, column=None):
    f = {"id": fid, "label": label, "options": options, "weight": weight, "required": required}
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
            _field("class_type", "Class", ["Assault", "Engineer", "Support", "Recon", "Vehicle Main"], 12, column="class_type"),
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
            _field("role", "Role", ["Entry", "AWPer", "Support", "Lurker", "IGL"], 8),
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
            _field("role", "Legend class", ["Assault", "Skirmisher", "Recon", "Support", "Controller"], 8),
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
            _field("role", "Role", ["Slayer", "Objective", "Anchor", "Sniper", "Support"], 8),
        ],
    },
    "minecraft": {
        "name": "Minecraft",
        "short": "MC",
        "genre": "Sandbox",
        "accent": "#5bd65b",
        "platforms": ["PC", "PlayStation", "Xbox", "Switch", "Mobile"],
        "ign_label": "Minecraft name",
        "fields": [
            _field("edition", "Edition", ["Java", "Bedrock"], 14),
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
        "fields": [
            _field("server", "Server", ["EUW", "EUNE", "NA", "TR", "ME", "KR", "OCE", "BR", "LAN"], 12),
            _field("role", "Main role", ["Top", "Jungle", "Mid", "ADC", "Support", "Fill"], 10),
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
            _field("role", "Loadout role", ["Anti-tank", "Crowd control", "Support / Stims", "Objectives", "Flex"], 10),
        ],
    },
}

GAME_ORDER = ["battlefield", "cs2", "fortnite", "apex", "pubg-mobile", "codm", "minecraft", "lol", "helldivers2"]


def get_game(game_id: str | None) -> dict | None:
    return GAMES.get((game_id or "").strip().lower())


def game_summary(game_id: str) -> dict:
    g = GAMES[game_id]
    return {
        "id": game_id,
        "name": g["name"],
        "short": g["short"],
        "genre": g["genre"],
        "accent": g["accent"],
        "cover": f"/static/img/games/{game_id}.svg",
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
        "regions": REGIONS,
        "languages": LANGUAGES,
        # kept for older clients (Battlefield page)
        "favorite_modes": next((f["options"] for f in g["fields"] if f["id"] == "favorite_mode"), []),
    }


def region_label(region_id: str | None) -> str:
    for r in REGIONS:
        if r["id"] == region_id:
            return r["label"]
    return region_id or ""


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
