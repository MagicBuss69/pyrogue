"""Core configuration, 5 Biome Area themes, 5 Floor Bosses, Relics, and Steam Edition constants."""

from pathlib import Path
from typing import Any, Dict, List, Tuple

GAME_TITLE = "CRYPTS OF THE OBSIDIAN KING"
GAME_SUBTITLE = "COMPLETE STEAM EDITION • 5 BIOMES • 5 BOSSES • FULL SOUNDTRACK"
GAME_VERSION = "v3.0.0-GOLD"
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

TILE_SIZE = 48

# Dungeon grid dimensions
DUNGEON_WIDTH = 54
DUNGEON_HEIGHT = 42
BOSS_FLOOR = 5

# Tile types
TILE_VOID = 0
TILE_WALL = 1
TILE_FLOOR = 2
TILE_STAIRS_DOWN = 3
TILE_PILLAR = 4

# High score & progression file path
BASE_DIR = Path(__file__).resolve().parent
HIGHSCORE_FILE = BASE_DIR / "highscore.json"

# ============================================================================
# 5 DISTINCT BIOME AREAS & 5 UNIQUE FLOOR BOSSES
# Every floor has its own architectural palette, lighting, ambient particles,
# background music theme, and a unique Guardian Boss!
# ============================================================================
BIOME_THEMES: Dict[int, Dict[str, Any]] = {
    1: {
        "id": "verdant_catacombs",
        "name": "THE VERDANT OSSUARY",
        "subtitle": "Floor 1 • Bioluminescent Spore Catacombs",
        "wall_top": (28, 48, 38),
        "wall_top_inner": (38, 64, 50),
        "wall_side": (17, 29, 23),
        "wall_mortar": (10, 18, 14),
        "wall_highlight": (72, 130, 96),
        "wall_rune": (75, 255, 150),
        "floor_a": (17, 26, 22),
        "floor_b": (21, 31, 26),
        "floor_crack": (11, 18, 15),
        "floor_accent": (34, 54, 42),
        "torch_color": (95, 255, 145),
        "ambient_particle": (110, 255, 165),
        "boss_type": "boss_broodmother",
        "boss_name": "Broodmother Vexis",
        "boss_title": "Matriarch of the Venom Hive",
        "boss_color": (65, 245, 120),
        "boss_secondary": (195, 255, 95),
        "bgm_track": "biome_1",
    },
    2: {
        "id": "astral_library",
        "name": "THE ASTRAL ARCHIVES",
        "subtitle": "Floor 2 • Forbidden Library of the Void Weavers",
        "wall_top": (42, 28, 66),
        "wall_top_inner": (56, 38, 88),
        "wall_side": (25, 16, 42),
        "wall_mortar": (15, 9, 26),
        "wall_highlight": (132, 88, 196),
        "wall_rune": (225, 95, 255),
        "floor_a": (22, 16, 36),
        "floor_b": (27, 20, 43),
        "floor_crack": (14, 10, 24),
        "floor_accent": (52, 34, 82),
        "torch_color": (215, 95, 255),
        "ambient_particle": (230, 140, 255),
        "boss_type": "boss_inquisitor",
        "boss_name": "High Inquisitor Vaelen",
        "boss_title": "Arch-Prelate of the Astral Choir",
        "boss_color": (215, 80, 255),
        "boss_secondary": (95, 230, 255),
        "bgm_track": "biome_2",
    },
    3: {
        "id": "frostbound_citadel",
        "name": "THE FROSTBOUND CITADEL",
        "subtitle": "Floor 3 • Sub-Zero Rimeforged Bastion",
        "wall_top": (28, 50, 74),
        "wall_top_inner": (38, 68, 98),
        "wall_side": (18, 32, 48),
        "wall_mortar": (11, 20, 32),
        "wall_highlight": (110, 195, 245),
        "wall_rune": (90, 235, 255),
        "floor_a": (18, 28, 42),
        "floor_b": (22, 34, 50),
        "floor_crack": (12, 20, 31),
        "floor_accent": (40, 68, 96),
        "torch_color": (85, 225, 255),
        "ambient_particle": (185, 245, 255),
        "boss_type": "boss_behemoth",
        "boss_name": "Kragor, the Rime Colossus",
        "boss_title": "Shatterer of the Frozen Throne",
        "boss_color": (80, 220, 255),
        "boss_secondary": (225, 250, 255),
        "bgm_track": "biome_3",
    },
    4: {
        "id": "cinder_foundry",
        "name": "THE HELLFORGE FOUNDRY",
        "subtitle": "Floor 4 • Molten Crucible of Ash & Iron",
        "wall_top": (62, 30, 28),
        "wall_top_inner": (84, 40, 36),
        "wall_side": (38, 18, 17),
        "wall_mortar": (22, 10, 10),
        "wall_highlight": (195, 92, 65),
        "wall_rune": (255, 145, 45),
        "floor_a": (30, 17, 17),
        "floor_b": (36, 21, 20),
        "floor_crack": (22, 11, 11),
        "floor_accent": (72, 34, 28),
        "torch_color": (255, 140, 45),
        "ambient_particle": (255, 165, 65),
        "boss_type": "boss_wyrm",
        "boss_name": "Ignis, the Cinder Drake",
        "boss_title": "Sovereign of the Magma Vents",
        "boss_color": (255, 110, 40),
        "boss_secondary": (255, 225, 80),
        "bgm_track": "biome_4",
    },
    5: {
        "id": "obsidian_sanctum",
        "name": "THE OBSIDIAN SANCTUM",
        "subtitle": "Floor 5 • Throne of the Undying Eclipse",
        "wall_top": (36, 31, 54),
        "wall_top_inner": (48, 41, 72),
        "wall_side": (21, 18, 34),
        "wall_mortar": (12, 10, 22),
        "wall_highlight": (115, 82, 145),
        "wall_rune": (255, 55, 105),
        "floor_a": (19, 17, 30),
        "floor_b": (24, 21, 37),
        "floor_crack": (13, 11, 21),
        "floor_accent": (46, 32, 62),
        "torch_color": (255, 65, 105),
        "ambient_particle": (255, 95, 140),
        "boss_type": "boss",
        "boss_name": "Malakor, the Obsidian King",
        "boss_title": "Monarch of the Eternal Abyss",
        "boss_color": (255, 50, 95),
        "boss_secondary": (255, 215, 65),
        "bgm_track": "biome_5",
    },
}


def get_biome_theme(floor_num: int) -> Dict[str, Any]:
    """Return the biome dictionary for a given floor (clamped 1..5)."""
    clamped = max(1, min(5, int(floor_num)))
    return BIOME_THEMES[clamped]


# Fallback/Default Base Colors
COLOR_BG = (9, 8, 15)
COLOR_VOID = (5, 4, 10)

# Default Wall/Floor colors
COLOR_WALL_TOP = (34, 31, 51)
COLOR_WALL_TOP_INNER = (42, 39, 64)
COLOR_WALL_SIDE = (20, 18, 33)
COLOR_WALL_MORTAR = (13, 11, 22)
COLOR_WALL_HIGHLIGHT = (76, 70, 112)
COLOR_WALL_RUNE = (0, 215, 255)

COLOR_FLOOR_A = (19, 18, 30)
COLOR_FLOOR_B = (23, 22, 36)
COLOR_FLOOR_CRACK = (13, 12, 21)
COLOR_FLOOR_ACCENT = (33, 31, 49)
COLOR_FLOOR_RUNE = (46, 38, 74)

# Stairs & Portal
COLOR_STAIRS = (255, 205, 68)
COLOR_STAIRS_GLOW = (255, 240, 150)
COLOR_STAIRS_LOCKED = (110, 62, 88)

# Player Palette (Arcane Blade-Weaver)
COLOR_PLAYER = (65, 230, 255)
COLOR_PLAYER_CORE = (225, 252, 255)
COLOR_PLAYER_CAPE = (205, 42, 105)
COLOR_PLAYER_ARMOR = (34, 48, 82)
COLOR_SWORD = (245, 252, 255)
COLOR_SWORD_TRAIL = (65, 230, 255)
COLOR_SWORD_CRIT = (255, 215, 70)

# Ability Colors
COLOR_ABILITY_WHIRLWIND = (80, 240, 255)
COLOR_ABILITY_NOVA = (215, 80, 255)
COLOR_ABILITY_LIGHTNING = (255, 230, 95)
COLOR_ABILITY_DASH = (120, 255, 220)

# Standard Enemies
COLOR_SLIME = (70, 245, 130)
COLOR_SLIME_CORE = (25, 145, 75)
COLOR_SLIME_HIGHLIGHT = (195, 255, 215)

COLOR_CULTIST = (215, 85, 255)
COLOR_CULTIST_ROBE = (88, 28, 130)
COLOR_PROJECTILE_ENEMY = (250, 95, 230)

COLOR_BRUTE = (245, 85, 65)
COLOR_BRUTE_ARMOR = (115, 32, 38)
COLOR_BRUTE_HORN = (240, 228, 205)

# Boss Palettes
COLOR_BOSS = (255, 50, 95)
COLOR_BOSS_CROWN = (255, 215, 65)
COLOR_BOSS_PROJECTILE = (255, 135, 40)

# Pickups & Props
COLOR_PICKUP_HP = (255, 62, 98)
COLOR_PICKUP_GLOW = (255, 155, 180)
COLOR_TORCH_FLAME = (255, 175, 55)
COLOR_TORCH_CORE = (255, 245, 185)
COLOR_CRATE_WOOD = (134, 86, 50)
COLOR_CRATE_BAND = (74, 70, 90)
COLOR_SHRINE = (95, 235, 255)

# UI Colors
COLOR_UI_BG = (13, 12, 23)
COLOR_UI_PANEL = (22, 20, 38)
COLOR_UI_BORDER = (82, 76, 126)
COLOR_UI_HIGHLIGHT = (110, 235, 255)
COLOR_TEXT = (244, 242, 254)
COLOR_TEXT_DIM = (158, 152, 188)
COLOR_GOLD = (255, 212, 78)
COLOR_HP_BAR = (242, 58, 84)
COLOR_HP_BG = (52, 20, 32)
COLOR_MANA_BAR = (165, 90, 255)
COLOR_XP_BAR = (70, 235, 180)
COLOR_STAMINA_BAR = (75, 225, 255)

# Player Base Stats
PLAYER_SPEED = 262.0
PLAYER_RADIUS = 15
PLAYER_MAX_HP = 135
PLAYER_BASE_DAMAGE = 28
PLAYER_CRIT_CHANCE = 0.16

# Primary Combo Attack
PLAYER_ATTACK_COOLDOWN = 0.23
PLAYER_ATTACK_DURATION = 0.16
PLAYER_ATTACK_RANGE = 78.0
PLAYER_ATTACK_ARC = 1.90

# Ability 1: Phantom Dash [SPACE / SHIFT / Right-Click]
PLAYER_DASH_SPEED = 670.0
PLAYER_DASH_DURATION = 0.15
PLAYER_DASH_COOLDOWN = 0.78
PLAYER_DASH_DAMAGE = 20

# Ability 2: Whirlwind Cleave [Q / Key 1 / U]
ABILITY_WHIRLWIND_COOLDOWN = 3.0
ABILITY_WHIRLWIND_DURATION = 0.38
ABILITY_WHIRLWIND_RADIUS = 112.0
ABILITY_WHIRLWIND_DAMAGE_MULT = 1.70

# Ability 3: Eldritch Nova [E / Key 2 / I]
ABILITY_NOVA_COOLDOWN = 4.2
ABILITY_NOVA_ORB_COUNT = 8
ABILITY_NOVA_SPEED = 430.0
ABILITY_NOVA_DAMAGE_MULT = 1.30

# Ability 4: Chain Lightning [R / Key 3 / O]
ABILITY_LIGHTNING_COOLDOWN = 5.5
ABILITY_LIGHTNING_RANGE = 300.0
ABILITY_LIGHTNING_CHAINS = 4
ABILITY_LIGHTNING_DAMAGE_MULT = 1.90

PLAYER_INVULN_TIME = 0.48

# Pickups & Scoring
HEALTH_PICKUP_AMOUNT = 35
HEALTH_PICKUP_RADIUS = 12
SCORE_HEALTH_PICKUP = 35
SCORE_FLOOR_CLEAR = 300
SCORE_CRATE_BREAK = 20
SCORE_SHRINE_USE = 100

# Relic Upgrades offered on Level Up
RELIC_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "vampiric_edge",
        "name": "Vampiric Obsidian Edge",
        "desc": "+22% Attack Damage and heal +5 HP on every enemy kill.",
        "color": (255, 75, 110),
    },
    {
        "id": "storm_capacitor",
        "name": "Astral Storm Capacitor",
        "desc": "All Ability Cooldowns (Q, E, R, Dash) recover 25% faster.",
        "color": (90, 235, 255),
    },
    {
        "id": "titan_heart",
        "name": "Heart of the Colossus",
        "desc": "+40 Max HP immediately and restore 50 HP.",
        "color": (95, 245, 145),
    },
    {
        "id": "quicksilver_boots",
        "name": "Quicksilver Greaves",
        "desc": "+18% Movement Speed and +15% Critical Strike Chance.",
        "color": (255, 215, 80),
    },
    {
        "id": "arcane_overload",
        "name": "Eldritch Overload Core",
        "desc": "+35% Ability Damage (Whirlwind, Eldritch Nova, Chain Lightning).",
        "color": (210, 95, 255),
    },
    {
        "id": "phoenix_aegis",
        "name": "Cinderforged Aegis",
        "desc": "+25 Max HP, +15% Damage, and Dash leaves scorching fire.",
        "color": (255, 145, 55),
    },
]

# Steam-Style Achievements (8 Total)
ACHIEVEMENTS_CATALOG: List[Dict[str, str]] = [
    {
        "id": "first_blood",
        "name": "First Blood",
        "desc": "Slay your first denizen of the Crypts.",
    },
    {
        "id": "hive_breaker",
        "name": "Hive Breaker",
        "desc": "Defeat Broodmother Vexis in the Verdant Ossuary (Floor 1).",
    },
    {
        "id": "silence_choir",
        "name": "Silence the Choir",
        "desc": "Defeat High Inquisitor Vaelen in the Astral Archives (Floor 2).",
    },
    {
        "id": "frost_shatter",
        "name": "Glacier Shatterer",
        "desc": "Defeat Kragor, the Rime Colossus in the Frostbound Citadel (Floor 3).",
    },
    {
        "id": "wyrm_slayer",
        "name": "Dragonslayer",
        "desc": "Defeat Ignis, the Cinder Drake in the Hellforge Foundry (Floor 4).",
    },
    {
        "id": "storm_weaver",
        "name": "Arcane Tempest",
        "desc": "Unleash Whirlwind, Eldritch Nova, and Chain Lightning in a run.",
    },
    {
        "id": "centurion",
        "name": "Crypt Centurion",
        "desc": "Reach a score of 2,500 or higher in a single run.",
    },
    {
        "id": "kingslayer",
        "name": "Kingslayer",
        "desc": "Vanquish Malakor, the Obsidian King on Floor 5.",
    },
]
