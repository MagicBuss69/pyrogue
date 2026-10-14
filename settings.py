"""Core configuration, constants, art palette, and ability specs for the roguelike."""

from pathlib import Path
from typing import Dict, Any, List

GAME_TITLE = "CRYPTS OF THE OBSIDIAN KING"
GAME_SUBTITLE = "ELDRITCH ACTION ROGUELIKE • STEAM EDITION"
GAME_VERSION = "v2.0.0-STEAM"
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

TILE_SIZE = 48

# Dungeon grid dimensions
DUNGEON_WIDTH = 52
DUNGEON_HEIGHT = 40
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
# UNIQUE ART STYLE: "OBSIDIAN NEON-NOIR" PALETTE
# Deep volcanic obsidian shadows contrasted with luminous arcane cyan,
# eldritch magenta, soul-emerald, and molten gold rim-lighting.
# ============================================================================
COLOR_BG = (9, 8, 15)
COLOR_VOID = (6, 5, 11)

# 2.5D Chiseled Obsidian Walls
COLOR_WALL_TOP = (34, 31, 51)
COLOR_WALL_TOP_INNER = (42, 39, 64)
COLOR_WALL_SIDE = (20, 18, 33)
COLOR_WALL_MORTAR = (13, 11, 22)
COLOR_WALL_HIGHLIGHT = (76, 70, 112)
COLOR_WALL_RUNE = (0, 215, 255)

# Stone Slab Floors
COLOR_FLOOR_A = (19, 18, 30)
COLOR_FLOOR_B = (23, 22, 36)
COLOR_FLOOR_CRACK = (13, 12, 21)
COLOR_FLOOR_ACCENT = (33, 31, 49)
COLOR_FLOOR_RUNE = (46, 38, 74)

# Stairs & Portal
COLOR_STAIRS = (255, 200, 68)
COLOR_STAIRS_GLOW = (255, 235, 140)
COLOR_STAIRS_LOCKED = (82, 75, 104)

# Player Palette (Arcane Blade-Weaver)
COLOR_PLAYER = (65, 230, 255)
COLOR_PLAYER_CORE = (225, 252, 255)
COLOR_PLAYER_CAPE = (185, 42, 110)
COLOR_PLAYER_ARMOR = (32, 46, 78)
COLOR_SWORD = (240, 252, 255)
COLOR_SWORD_TRAIL = (65, 230, 255)
COLOR_SWORD_CRIT = (255, 215, 70)

# Ability Colors
COLOR_ABILITY_WHIRLWIND = (80, 240, 255)
COLOR_ABILITY_NOVA = (215, 80, 255)
COLOR_ABILITY_LIGHTNING = (255, 230, 95)
COLOR_ABILITY_DASH = (120, 255, 220)

# Enemy 1: Abyssal Slime (Bioluminescent Acid)
COLOR_SLIME = (70, 245, 130)
COLOR_SLIME_CORE = (25, 145, 75)
COLOR_SLIME_HIGHLIGHT = (195, 255, 215)

# Enemy 2: Void Cultist (Eldritch Astral Weaver)
COLOR_CULTIST = (215, 85, 255)
COLOR_CULTIST_ROBE = (88, 28, 130)
COLOR_PROJECTILE_ENEMY = (250, 95, 230)

# Enemy 3: Bone Juggernaut (Hellforged Colossus)
COLOR_BRUTE = (245, 85, 65)
COLOR_BRUTE_ARMOR = (115, 32, 38)
COLOR_BRUTE_HORN = (240, 228, 205)

# Floor 5 Boss: Malakor, the Obsidian King
COLOR_BOSS = (255, 50, 95)
COLOR_BOSS_CROWN = (255, 215, 65)
COLOR_BOSS_PROJECTILE = (255, 135, 40)

# Pickups & Props
COLOR_PICKUP_HP = (255, 62, 98)
COLOR_PICKUP_GLOW = (255, 155, 180)
COLOR_TORCH_FLAME = (255, 175, 55)
COLOR_TORCH_CORE = (255, 240, 170)
COLOR_CRATE_WOOD = (128, 82, 48)
COLOR_CRATE_BAND = (68, 64, 82)
COLOR_SHRINE = (95, 225, 255)

# UI Colors
COLOR_UI_BG = (14, 13, 24)
COLOR_UI_PANEL = (22, 20, 36)
COLOR_UI_BORDER = (78, 72, 118)
COLOR_UI_HIGHLIGHT = (110, 230, 255)
COLOR_TEXT = (242, 240, 252)
COLOR_TEXT_DIM = (152, 146, 182)
COLOR_GOLD = (255, 210, 75)
COLOR_HP_BAR = (240, 58, 82)
COLOR_HP_BG = (52, 20, 32)
COLOR_MANA_BAR = (165, 90, 255)
COLOR_XP_BAR = (70, 235, 180)
COLOR_STAMINA_BAR = (75, 225, 255)

# Player Base Stats
PLAYER_SPEED = 255.0
PLAYER_RADIUS = 15
PLAYER_MAX_HP = 120
PLAYER_BASE_DAMAGE = 26
PLAYER_CRIT_CHANCE = 0.15

# Primary Combo Attack
PLAYER_ATTACK_COOLDOWN = 0.24
PLAYER_ATTACK_DURATION = 0.16
PLAYER_ATTACK_RANGE = 76.0
PLAYER_ATTACK_ARC = 1.85  # wide sweeping arc

# Ability 1: Phantom Dash [SPACE / SHIFT / Right-Click]
PLAYER_DASH_SPEED = 660.0
PLAYER_DASH_DURATION = 0.15
PLAYER_DASH_COOLDOWN = 0.80
PLAYER_DASH_DAMAGE = 18

# Ability 2: Whirlwind Cleave [Q / Key 1 / U] — 360-degree spinning blade storm + projectile deflection
ABILITY_WHIRLWIND_COOLDOWN = 3.2
ABILITY_WHIRLWIND_DURATION = 0.38
ABILITY_WHIRLWIND_RADIUS = 108.0
ABILITY_WHIRLWIND_DAMAGE_MULT = 1.65

# Ability 3: Eldritch Nova [E / Key 2 / I] — Fires 8 piercing arcane lances in a ring
ABILITY_NOVA_COOLDOWN = 4.5
ABILITY_NOVA_ORB_COUNT = 8
ABILITY_NOVA_SPEED = 420.0
ABILITY_NOVA_DAMAGE_MULT = 1.25

# Ability 4: Chain Lightning [R / Key 3 / O] — Calls down high-voltage arcs that jump between up to 4 nearby enemies
ABILITY_LIGHTNING_COOLDOWN = 6.0
ABILITY_LIGHTNING_RANGE = 290.0
ABILITY_LIGHTNING_CHAINS = 4
ABILITY_LIGHTNING_DAMAGE_MULT = 1.85

PLAYER_INVULN_TIME = 0.45

# Pickups & Scoring
HEALTH_PICKUP_AMOUNT = 32
HEALTH_PICKUP_RADIUS = 12
SCORE_HEALTH_PICKUP = 30
SCORE_FLOOR_CLEAR = 250
SCORE_CRATE_BREAK = 15

# Relic Upgrades offered on Level Up
RELIC_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "vampiric_edge",
        "name": "Vampiric Obsidian Edge",
        "desc": "+22% Attack Damage and heal +4 HP on every enemy kill.",
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
        "desc": "+35 Max HP immediately and restore 45 HP.",
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
]

# Steam-Style Achievements
ACHIEVEMENTS_CATALOG: List[Dict[str, str]] = [
    {
        "id": "first_blood",
        "name": "First Blood",
        "desc": "Slay your first denizen of the Obsidian Crypts.",
    },
    {
        "id": "storm_weaver",
        "name": "Arcane Tempest",
        "desc": "Unleash Whirlwind, Eldritch Nova, and Chain Lightning in a run.",
    },
    {
        "id": "centurion",
        "name": "Crypt Centurion",
        "desc": "Reach a score of 1,500 or higher in a single run.",
    },
    {
        "id": "deep_delver",
        "name": "Sanctum Delver",
        "desc": "Descend to Floor 5: The Obsidian Sanctum.",
    },
    {
        "id": "kingslayer",
        "name": "Kingslayer",
        "desc": "Vanquish Malakor, the Obsidian King on Floor 5.",
    },
]
