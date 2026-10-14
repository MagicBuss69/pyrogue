"""Player, Abilities, Relics, 3 Standard Enemies, 5 Unique Biome Bosses, Projectiles, Pickups, and Visual FX."""

from dataclasses import dataclass, field
import math
import random
from typing import List, Optional, Set, Tuple

from dungeon import Dungeon
from settings import (
    ABILITY_LIGHTNING_CHAINS,
    ABILITY_LIGHTNING_COOLDOWN,
    ABILITY_LIGHTNING_DAMAGE_MULT,
    ABILITY_LIGHTNING_RANGE,
    ABILITY_NOVA_COOLDOWN,
    ABILITY_NOVA_DAMAGE_MULT,
    ABILITY_NOVA_ORB_COUNT,
    ABILITY_NOVA_SPEED,
    ABILITY_WHIRLWIND_COOLDOWN,
    ABILITY_WHIRLWIND_DAMAGE_MULT,
    ABILITY_WHIRLWIND_DURATION,
    ABILITY_WHIRLWIND_RADIUS,
    COLOR_ABILITY_NOVA,
    COLOR_BOSS,
    COLOR_BOSS_PROJECTILE,
    COLOR_BRUTE,
    COLOR_CULTIST,
    COLOR_PLAYER,
    COLOR_PROJECTILE_ENEMY,
    COLOR_SLIME,
    HEALTH_PICKUP_AMOUNT,
    HEALTH_PICKUP_RADIUS,
    PLAYER_ATTACK_ARC,
    PLAYER_ATTACK_COOLDOWN,
    PLAYER_ATTACK_DURATION,
    PLAYER_ATTACK_RANGE,
    PLAYER_BASE_DAMAGE,
    PLAYER_CRIT_CHANCE,
    PLAYER_DASH_COOLDOWN,
    PLAYER_DASH_DURATION,
    PLAYER_DASH_SPEED,
    PLAYER_INVULN_TIME,
    PLAYER_MAX_HP,
    PLAYER_RADIUS,
    PLAYER_SPEED,
    TILE_SIZE,
)

BOSS_TYPES = {
    "boss_broodmother",
    "boss_inquisitor",
    "boss_behemoth",
    "boss_wyrm",
    "boss",
}


def angle_diff(a: float, b: float) -> float:
    """Smallest signed difference between two angles in radians."""
    return (a - b + math.pi) % (2 * math.pi) - math.pi


@dataclass
class Particle:
    """Visual particle for hit sparks, blood, heals, and explosions."""

    x: float
    y: float
    vx: float
    vy: float
    color: Tuple[int, int, int]
    size: float
    lifetime: float
    max_lifetime: float
    glow: bool = False

    def update(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= max(0.0, 1.0 - 4.5 * dt)
        self.vy *= max(0.0, 1.0 - 4.5 * dt)
        self.lifetime -= dt
        return self.lifetime > 0


@dataclass
class DashAfterimage:
    """Translucent ghost silhouette left behind during Phantom Dash or Whirlwind."""

    x: float
    y: float
    radius: float
    color: Tuple[int, int, int]
    lifetime: float = 0.24
    max_lifetime: float = 0.24

    def update(self, dt: float) -> bool:
        self.lifetime -= dt
        return self.lifetime > 0


@dataclass
class LightningBoltFX:
    """Jagged electric arc connecting two world points for Chain Lightning."""

    points: List[Tuple[float, float]]
    color: Tuple[int, int, int]
    lifetime: float = 0.25
    max_lifetime: float = 0.25

    def update(self, dt: float) -> bool:
        self.lifetime -= dt
        return self.lifetime > 0


@dataclass
class ShockwaveRingFX:
    """Expanding energy ring for Whirlwind, Nova, or Boss slams."""

    x: float
    y: float
    radius: float
    max_radius: float
    color: Tuple[int, int, int]
    lifetime: float = 0.28
    max_lifetime: float = 0.28

    def update(self, dt: float) -> bool:
        self.lifetime -= dt
        progress = 1.0 - max(0.0, self.lifetime / self.max_lifetime)
        self.radius = self.max_radius * progress
        return self.lifetime > 0


@dataclass
class FloatingText:
    """Floating combat damage, crit, level-up, or pickup text."""

    x: float
    y: float
    text: str
    color: Tuple[int, int, int]
    lifetime: float = 0.85
    max_lifetime: float = 0.85
    vy: float = -48.0
    scale: float = 1.0

    def update(self, dt: float) -> bool:
        self.y += self.vy * dt
        self.vy *= max(0.0, 1.0 - 2.2 * dt)
        self.lifetime -= dt
        return self.lifetime > 0


@dataclass
class Projectile:
    """Ranged orb or lance fired by either the Player (Eldritch Nova) or Enemies/Bosses."""

    x: float
    y: float
    vx: float
    vy: float
    damage: int
    radius: float = 7.0
    color: Tuple[int, int, int] = COLOR_PROJECTILE_ENEMY
    lifetime: float = 3.2
    from_player: bool = False
    piercing: bool = False
    hit_enemy_ids: Set[int] = field(default_factory=set)
    alive: bool = True

    def update(self, dt: float, dungeon: Dungeon) -> None:
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False
            return
        self.x += self.vx * dt
        self.y += self.vy * dt
        if dungeon.circle_collides_walls(self.x, self.y, self.radius * 0.65):
            self.alive = False


@dataclass
class HealthPickup:
    """Crimson Elixir pickup that restores player HP."""

    x: float
    y: float
    heal_amount: int = HEALTH_PICKUP_AMOUNT
    radius: float = HEALTH_PICKUP_RADIUS
    bob_timer: float = 0.0
    collected: bool = False

    def update(self, dt: float) -> None:
        self.bob_timer += dt * 3.8


class Player:
    """Playable Arcane Blade-Weaver with 3-hit combo, 4 abilities, smart aiming, and XP/Relics."""

    def __init__(self, x: float, y: float) -> None:
        self.x: float = x
        self.y: float = y
        self.radius: float = PLAYER_RADIUS
        self.max_hp: int = PLAYER_MAX_HP
        self.hp: int = PLAYER_MAX_HP
        self.speed: float = PLAYER_SPEED
        self.damage: int = PLAYER_BASE_DAMAGE
        self.crit_chance: float = PLAYER_CRIT_CHANCE
        self.ability_power_mult: float = 1.0
        self.cooldown_Multiplier: float = 1.0
        self.vampiric_heal: int = 0
        self.cinder_dash: bool = False

        # Progression / Level / Relics
        self.level: int = 1
        self.xp: int = 0
        self.xp_to_next: int = 95
        self.relics: List[str] = []

        # Facing & Smart Aim
        self.facing_angle: float = 0.0
        self.aim_mode: str = "AUTO"  # "AUTO", "KEYS", "MOVE", "MOUSE"

        # Primary 3-step Sword Combo
        self.attack_timer: float = 0.0
        self.attack_cooldown: float = 0.0
        self.attack_angle: float = 0.0
        self.attack_swing_dir: int = 1
        self.combo_step: int = 0
        self.combo_reset_timer: float = 0.0
        self.hit_targets_this_swing: Set[int] = set()

        # Ability 1: Phantom Dash (SPACE / SHIFT / Right-Click)
        self.dash_timer: float = 0.0
        self.dash_cooldown: float = 0.0
        self.dash_dx: float = 1.0
        self.dash_dy: float = 0.0
        self.dash_hit_ids: Set[int] = set()
        self.afterimage_spawn_timer: float = 0.0

        # Ability 2: Whirlwind Cleave (Q / 1 / U)
        self.whirlwind_timer: float = 0.0
        self.whirlwind_cooldown: float = 0.0
        self.whirlwind_hit_ids: Set[int] = set()

        # Ability 3: Eldritch Nova (E / 2 / I)
        self.nova_cooldown: float = 0.0

        # Ability 4: Chain Lightning (R / 3 / O)
        self.lightning_cooldown: float = 0.0

        self.invuln_timer: float = 0.0
        self.hurt_flash_timer: float = 0.0
        self.knockback_vx: float = 0.0
        self.knockback_vy: float = 0.0
        self.walk_anim_timer: float = 0.0
        self.is_moving: bool = False

    @property
    def is_attacking(self) -> bool:
        return self.attack_timer > 0.0

    @property
    def is_whirlwinding(self) -> bool:
        return self.whirlwind_timer > 0.0

    @property
    def is_dashing(self) -> bool:
        return self.dash_timer > 0.0

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def apply_relic(self, relic_id: str) -> None:
        self.relics.append(relic_id)
        if relic_id == "vampiric_edge":
            self.damage = int(self.damage * 1.22)
            self.vampiric_heal += 5
        elif relic_id == "storm_capacitor":
            self.cooldown_Multiplier *= 0.75
        elif relic_id == "titan_heart":
            self.max_hp += 40
            self.heal(50)
        elif relic_id == "quicksilver_boots":
            self.speed *= 1.18
            self.crit_chance = min(0.80, self.crit_chance + 0.15)
        elif relic_id == "arcane_overload":
            self.ability_power_mult *= 1.35
        elif relic_id == "phoenix_aegis":
            self.max_hp += 25
            self.heal(35)
            self.damage = int(self.damage * 1.15)
            self.cinder_dash = True

    def gain_xp(self, amount: int) -> bool:
        """Add XP and return True if the player leveled up."""
        self.xp += amount
        if self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level += 1
            self.xp_to_next = int(self.xp_to_next * 1.32)
            self.max_hp += 12
            self.damage += 3
            self.heal(25)
            return True
        return False

    def roll_damage(self, base_dmg: float) -> Tuple[int, bool]:
        is_crit = random.random() < self.crit_chance
        dmg = int(base_dmg * (1.75 if is_crit else 1.0))
        return max(1, dmg), is_crit

    def start_attack(self, aim_angle: Optional[float] = None) -> bool:
        if self.attack_cooldown > 0.0 or self.attack_timer > 0.0:
            return False
        if aim_angle is not None:
            self.facing_angle = aim_angle
        self.attack_angle = self.facing_angle

        if self.combo_reset_timer > 0.0:
            self.combo_step = (self.combo_step + 1) % 3
        else:
            self.combo_step = 0

        self.combo_reset_timer = 0.68
        self.attack_timer = PLAYER_ATTACK_DURATION
        self.attack_cooldown = PLAYER_ATTACK_COOLDOWN * self.cooldown_Multiplier
        self.attack_swing_dir *= -1
        self.hit_targets_this_swing.clear()

        lunge = 115.0 if self.combo_step < 2 else 185.0
        self.knockback_vx += math.cos(self.attack_angle) * lunge
        self.knockback_vy += math.sin(self.attack_angle) * lunge
        return True

    def start_dash(self, move_dx: float, move_dy: float) -> bool:
        if self.dash_cooldown > 0.0 or self.dash_timer > 0.0:
            return False
        if abs(move_dx) < 0.01 and abs(move_dy) < 0.01:
            self.dash_dx = math.cos(self.facing_angle)
            self.dash_dy = math.sin(self.facing_angle)
        else:
            norm = math.hypot(move_dx, move_dy)
            self.dash_dx = move_dx / norm
            self.dash_dy = move_dy / norm
            self.facing_angle = math.atan2(self.dash_dy, self.dash_dx)
        self.dash_timer = PLAYER_DASH_DURATION
        self.dash_cooldown = PLAYER_DASH_COOLDOWN * self.cooldown_Multiplier
        self.invuln_timer = max(self.invuln_timer, PLAYER_DASH_DURATION + 0.09)
        self.dash_hit_ids.clear()
        return True

    def start_whirlwind(self) -> bool:
        """Ability Q: 360-degree spinning blade storm."""
        if self.whirlwind_cooldown > 0.0 or self.whirlwind_timer > 0.0:
            return False
        self.whirlwind_timer = ABILITY_WHIRLWIND_DURATION
        self.whirlwind_cooldown = ABILITY_WHIRLWIND_COOLDOWN * self.cooldown_Multiplier
        self.whirlwind_hit_ids.clear()
        self.invuln_timer = max(self.invuln_timer, 0.22)
        return True

    def cast_eldritch_nova(self) -> List[Projectile]:
        """Ability E: Ring of piercing arcane lances."""
        if self.nova_cooldown > 0.0:
            return []
        self.nova_cooldown = ABILITY_NOVA_COOLDOWN * self.cooldown_Multiplier
        orbs: List[Projectile] = []
        dmg = int(self.damage * ABILITY_NOVA_DAMAGE_MULT * self.ability_power_mult)
        for i in range(ABILITY_NOVA_ORB_COUNT):
            ang = self.facing_angle + (2.0 * math.pi * i) / ABILITY_NOVA_ORB_COUNT
            orbs.append(
                Projectile(
                    x=self.x + math.cos(ang) * (self.radius + 6),
                    y=self.y + math.sin(ang) * (self.radius + 6),
                    vx=math.cos(ang) * ABILITY_NOVA_SPEED,
                    vy=math.sin(ang) * ABILITY_NOVA_SPEED,
                    damage=dmg,
                    radius=8.5,
                    color=COLOR_ABILITY_NOVA,
                    lifetime=1.45,
                    from_player=True,
                    piercing=True,
                )
            )
        return orbs

    def can_cast_lightning(self) -> bool:
        return self.lightning_cooldown <= 0.0

    def trigger_lightning_cooldown(self) -> None:
        self.lightning_cooldown = ABILITY_LIGHTNING_COOLDOWN * self.cooldown_Multiplier

    def take_damage(self, amount: int, source_x: float, source_y: float) -> int:
        if self.invuln_timer > 0.0 or not self.alive:
            return 0
        actual = max(1, int(amount))
        self.hp = max(0, self.hp - actual)
        self.invuln_timer = PLAYER_INVULN_TIME
        self.hurt_flash_timer = 0.22
        dx = self.x - source_x
        dy = self.y - source_y
        dist = math.hypot(dx, dy)
        if dist > 0.01:
            self.knockback_vx = (dx / dist) * 280.0
            self.knockback_vy = (dy / dist) * 280.0
        return actual

    def heal(self, amount: int) -> int:
        if self.hp >= self.max_hp:
            return 0
        before = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        return self.hp - before

    def update(
        self,
        dt: float,
        move_dx: float,
        move_dy: float,
        aim_angle: Optional[float],
        dungeon: Dungeon,
    ) -> Optional[DashAfterimage]:
        if self.attack_timer > 0.0:
            self.attack_timer = max(0.0, self.attack_timer - dt)
        if self.attack_cooldown > 0.0:
            self.attack_cooldown = max(0.0, self.attack_cooldown - dt)
        if self.combo_reset_timer > 0.0:
            self.combo_reset_timer = max(0.0, self.combo_reset_timer - dt)
        if self.dash_timer > 0.0:
            self.dash_timer = max(0.0, self.dash_timer - dt)
        if self.dash_cooldown > 0.0:
            self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        if self.whirlwind_timer > 0.0:
            self.whirlwind_timer = max(0.0, self.whirlwind_timer - dt)
        if self.whirlwind_cooldown > 0.0:
            self.whirlwind_cooldown = max(0.0, self.whirlwind_cooldown - dt)
        if self.nova_cooldown > 0.0:
            self.nova_cooldown = max(0.0, self.nova_cooldown - dt)
        if self.lightning_cooldown > 0.0:
            self.lightning_cooldown = max(0.0, self.lightning_cooldown - dt)
        if self.invuln_timer > 0.0:
            self.invuln_timer = max(0.0, self.invuln_timer - dt)
        if self.hurt_flash_timer > 0.0:
            self.hurt_flash_timer = max(0.0, self.hurt_flash_timer - dt)

        if aim_angle is not None and not self.is_attacking:
            self.facing_angle = aim_angle
        elif (abs(move_dx) > 0.01 or abs(move_dy) > 0.01) and not self.is_attacking:
            self.facing_angle = math.atan2(move_dy, move_dx)

        spawned_ghost: Optional[DashAfterimage] = None
        if self.is_dashing or self.is_whirlwinding:
            self.afterimage_spawn_timer -= dt
            if self.afterimage_spawn_timer <= 0.0:
                self.afterimage_spawn_timer = 0.030
                g_col = (255, 140, 50) if self.cinder_dash else COLOR_PLAYER
                spawned_ghost = DashAfterimage(
                    x=self.x,
                    y=self.y,
                    radius=self.radius,
                    color=g_col,
                )

        if self.is_dashing:
            vx = self.dash_dx * PLAYER_DASH_SPEED
            vy = self.dash_dy * PLAYER_DASH_SPEED
            self.is_moving = True
        else:
            norm = math.hypot(move_dx, move_dy)
            if norm > 0.01:
                vx = (move_dx / norm) * self.speed
                vy = (move_dy / norm) * self.speed
                self.is_moving = True
                self.walk_anim_timer += dt * 11.0
            else:
                vx = 0.0
                vy = 0.0
                self.is_moving = False

        vx += self.knockback_vx
        vy += self.knockback_vy
        self.knockback_vx *= max(0.0, 1.0 - 11.0 * dt)
        self.knockback_vy *= max(0.0, 1.0 - 11.0 * dt)

        self.x, self.y, _ = dungeon.move_with_sliding(
            self.x, self.y, vx, vy, self.radius, dt
        )
        return spawned_ghost


@dataclass
class EnemyActionEvents:
    """Events emitted by an enemy or boss during its AI update."""

    projectiles: List[Projectile] = field(default_factory=list)
    spawned_minions: List["Enemy"] = field(default_factory=list)
    shockwave: bool = False


class Enemy:
    """Supports 3 standard enemy archetypes plus 5 distinct Biome Bosses (Floors 1-5)."""

    _next_id: int = 1

    def __init__(
        self,
        enemy_type: str,
        x: float,
        y: float,
        floor_num: int = 1,
        room_index: int = 0,
    ) -> None:
        self.id: int = Enemy._next_id
        Enemy._next_id += 1

        self.enemy_type: str = enemy_type
        self.x: float = x
        self.y: float = y
        self.room_index: int = room_index
        self.floor_num: int = floor_num

        self.knockback_vx: float = 0.0
        self.knockback_vy: float = 0.0
        self.hurt_flash_timer: float = 0.0
        self.anim_timer: float = random.uniform(0.0, 6.28)
        self.ai_timer: float = random.uniform(0.3, 0.9)
        self.state: str = "idle"
        self.state_timer: float = 0.0
        self.charge_dx: float = 0.0
        self.charge_dy: float = 0.0
        self.boss_phase: int = 1
        self.attack_sequence: int = 0
        self.subtitle: str = ""
        self.achievement_id: Optional[str] = None

        scale = 1.0 + 0.14 * (floor_num - 1)

        if enemy_type == "slime":
            self.name = "Venom Slime"
            self.radius = 15.0
            self.max_hp = int(38 * scale)
            self.damage = int(10 + 2 * (floor_num - 1))
            self.speed = 158.0
            self.score_value = 50 * floor_num
            self.xp_value = 26
            self.color = COLOR_SLIME
            self.aggro_range = 360.0

        elif enemy_type == "cultist":
            self.name = "Void Cultist"
            self.radius = 15.0
            self.max_hp = int(34 * scale)
            self.damage = int(12 + 2 * (floor_num - 1))
            self.speed = 128.0
            self.score_value = 80 * floor_num
            self.xp_value = 34
            self.color = COLOR_CULTIST
            self.aggro_range = 450.0

        elif enemy_type == "brute":
            self.name = "Bone Juggernaut"
            self.radius = 20.0
            self.max_hp = int(76 * scale)
            self.damage = int(18 + 3 * (floor_num - 1))
            self.speed = 96.0
            self.score_value = 120 * floor_num
            self.xp_value = 48
            self.color = COLOR_BRUTE
            self.aggro_range = 390.0

        # ====================================================================
        # 5 UNIQUE FLOOR BOSSES (4 New Area Guardians + Malakor on Floor 5)
        # ====================================================================
        elif enemy_type == "boss_broodmother":
            self.name = "Broodmother Vexis"
            self.subtitle = "Matriarch of the Venom Hive"
            self.radius = 26.0
            self.max_hp = 260
            self.damage = 16
            self.speed = 115.0
            self.score_value = 800
            self.xp_value = 120
            self.color = (65, 245, 120)
            self.aggro_range = 560.0
            self.ai_timer = 1.2
            self.achievement_id = "hive_breaker"

        elif enemy_type == "boss_inquisitor":
            self.name = "High Inquisitor Vaelen"
            self.subtitle = "Arch-Prelate of the Astral Choir"
            self.radius = 25.0
            self.max_hp = 340
            self.damage = 18
            self.speed = 132.0
            self.score_value = 1200
            self.xp_value = 150
            self.color = (215, 80, 255)
            self.aggro_range = 600.0
            self.ai_timer = 1.15
            self.achievement_id = "silence_choir"

        elif enemy_type == "boss_behemoth":
            self.name = "Kragor, the Rime Colossus"
            self.subtitle = "Shatterer of the Frozen Throne"
            self.radius = 29.0
            self.max_hp = 440
            self.damage = 22
            self.speed = 108.0
            self.score_value = 1600
            self.xp_value = 180
            self.color = (80, 220, 255)
            self.aggro_range = 600.0
            self.ai_timer = 1.2
            self.achievement_id = "frost_shatter"

        elif enemy_type == "boss_wyrm":
            self.name = "Ignis, the Cinder Drake"
            self.subtitle = "Sovereign of the Magma Vents"
            self.radius = 28.0
            self.max_hp = 520
            self.damage = 23
            self.speed = 138.0
            self.score_value = 2200
            self.xp_value = 210
            self.color = (255, 110, 40)
            self.aggro_range = 640.0
            self.ai_timer = 1.1
            self.achievement_id = "wyrm_slayer"

        elif enemy_type == "boss":
            self.name = "Malakor, the Obsidian King"
            self.subtitle = "Monarch of the Eternal Abyss"
            self.radius = 32.0
            self.max_hp = 680
            self.damage = 25
            self.speed = 122.0
            self.score_value = 3500
            self.xp_value = 300
            self.color = COLOR_BOSS
            self.aggro_range = 740.0
            self.ai_timer = 1.2
            self.achievement_id = "kingslayer"

        else:
            raise ValueError(f"Unknown enemy type: {enemy_type}")

        self.hp: int = self.max_hp

    @property
    def alive(self) -> bool:
        return self.hp > 0

    @property
    def is_boss(self) -> bool:
        return self.enemy_type in BOSS_TYPES

    def take_damage(self, amount: int, source_x: float, source_y: float) -> int:
        if not self.alive:
            return 0
        actual = max(1, int(amount))
        self.hp = max(0, self.hp - actual)
        self.hurt_flash_timer = 0.14
        dx = self.x - source_x
        dy = self.y - source_y
        dist = math.hypot(dx, dy)
        kb_mult = 0.22 if self.is_boss else (0.50 if self.enemy_type == "brute" else 1.0)
        if dist > 0.01:
            self.knockback_vx = (dx / dist) * 290.0 * kb_mult
            self.knockback_vy = (dy / dist) * 290.0 * kb_mult
        return actual

    def update(
        self, dt: float, player: Player, dungeon: Dungeon
    ) -> EnemyActionEvents:
        events = EnemyActionEvents()
        self.anim_timer += dt * 5.2
        if self.hurt_flash_timer > 0.0:
            self.hurt_flash_timer = max(0.0, self.hurt_flash_timer - dt)

        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)

        vx = 0.0
        vy = 0.0

        if self.enemy_type == "slime":
            vx, vy = self._update_slime(dt, dx, dy, dist)
        elif self.enemy_type == "cultist":
            vx, vy = self._update_cultist(dt, dx, dy, dist, dungeon, events)
        elif self.enemy_type == "brute":
            vx, vy = self._update_brute(dt, dx, dy, dist, dungeon)
        elif self.enemy_type == "boss_broodmother":
            vx, vy = self._update_boss_broodmother(dt, dx, dy, dist, dungeon, events)
        elif self.enemy_type == "boss_inquisitor":
            vx, vy = self._update_boss_inquisitor(dt, dx, dy, dist, dungeon, events)
        elif self.enemy_type == "boss_behemoth":
            vx, vy = self._update_boss_behemoth(dt, dx, dy, dist, dungeon, events)
        elif self.enemy_type == "boss_wyrm":
            vx, vy = self._update_boss_wyrm(dt, dx, dy, dist, dungeon, events)
        elif self.enemy_type == "boss":
            vx, vy = self._update_boss_malakor(dt, dx, dy, dist, dungeon, events)

        vx += self.knockback_vx
        vy += self.knockback_vy
        self.knockback_vx *= max(0.0, 1.0 - 9.0 * dt)
        self.knockback_vy *= max(0.0, 1.0 - 9.0 * dt)

        self.x, self.y, hit_wall = dungeon.move_with_sliding(
            self.x, self.y, vx, vy, self.radius, dt
        )
        if hit_wall and self.state == "charging":
            self.state = "cooldown"
            self.state_timer = 0.50
            events.shockwave = True

        return events

    def _update_slime(
        self, dt: float, dx: float, dy: float, dist: float
    ) -> Tuple[float, float]:
        if dist > self.aggro_range:
            return (0.0, 0.0)

        self.state_timer -= dt
        if self.state == "idle":
            if self.state_timer <= 0.0:
                self.state = "windup"
                self.state_timer = 0.25
                if dist > 0.01:
                    self.charge_dx = dx / dist
                    self.charge_dy = dy / dist
            return (0.0, 0.0)
        if self.state == "windup":
            if self.state_timer <= 0.0:
                self.state = "hop"
                self.state_timer = 0.36
            return (0.0, 0.0)
        if self.state == "hop":
            if self.state_timer <= 0.0:
                self.state = "idle"
                self.state_timer = random.uniform(0.30, 0.55)
                return (0.0, 0.0)
            return (self.charge_dx * self.speed * 1.65, self.charge_dy * self.speed * 1.65)

        self.state = "idle"
        return (0.0, 0.0)

    def _update_cultist(
        self,
        dt: float,
        dx: float,
        dy: float,
        dist: float,
        dungeon: Dungeon,
        events: EnemyActionEvents,
    ) -> Tuple[float, float]:
        if dist > self.aggro_range:
            return (0.0, 0.0)

        nx = dx / dist if dist > 0.01 else 1.0
        ny = dy / dist if dist > 0.01 else 0.0

        vx, vy = 0.0, 0.0
        preferred_min = 145.0
        preferred_max = 260.0

        if dist < preferred_min:
            vx = -nx * self.speed
            vy = -ny * self.speed
        elif dist > preferred_max:
            vx = nx * self.speed * 0.85
            vy = ny * self.speed * 0.85
        else:
            strafe_dir = 1.0 if (self.id % 2 == 0) else -1.0
            vx = -ny * self.speed * 0.65 * strafe_dir
            vy = nx * self.speed * 0.65 * strafe_dir

        self.ai_timer -= dt
        if self.ai_timer <= 0.0:
            if dungeon.has_line_of_sight(self.x, self.y, self.x + dx, self.y + dy):
                bolt_speed = 265.0 + 15.0 * (self.floor_num - 1)
                events.projectiles.append(
                    Projectile(
                        x=self.x + nx * (self.radius + 6),
                        y=self.y + ny * (self.radius + 6),
                        vx=nx * bolt_speed,
                        vy=ny * bolt_speed,
                        damage=self.damage,
                        radius=6.5,
                        color=COLOR_PROJECTILE_ENEMY,
                    )
                )
                self.ai_timer = max(1.15, 1.95 - 0.12 * self.floor_num)
            else:
                self.ai_timer = 0.45

        return (vx, vy)

    def _update_brute(
        self,
        dt: float,
        dx: float,
        dy: float,
        dist: float,
        dungeon: Dungeon,
    ) -> Tuple[float, float]:
        if dist > self.aggro_range and self.state == "idle":
            return (0.0, 0.0)

        nx = dx / dist if dist > 0.01 else 1.0
        ny = dy / dist if dist > 0.01 else 0.0

        self.state_timer -= dt
        if self.state == "idle":
            if (
                dist < 245.0
                and self.state_timer <= 0.0
                and dungeon.has_line_of_sight(self.x, self.y, self.x + dx, self.y + dy)
            ):
                self.state = "windup"
                self.state_timer = 0.52
                self.charge_dx = nx
                self.charge_dy = ny
                return (0.0, 0.0)
            return (nx * self.speed, ny * self.speed)

        if self.state == "windup":
            if self.state_timer <= 0.0:
                self.state = "charging"
                self.state_timer = 0.55
            return (0.0, 0.0)

        if self.state == "charging":
            if self.state_timer <= 0.0:
                self.state = "cooldown"
                self.state_timer = 0.65
                return (0.0, 0.0)
            return (self.charge_dx * self.speed * 3.25, self.charge_dy * self.speed * 3.25)

        if self.state == "cooldown":
            if self.state_timer <= 0.0:
                self.state = "idle"
                self.state_timer = 1.1
            return (0.0, 0.0)

        self.state = "idle"
        return (0.0, 0.0)

    # ------------------------------------------------------------------------
    # BOSS 1: BROODMOTHER VEXIS (Floor 1 — Acid Globules, Leap Slam & Hatchlings)
    # ------------------------------------------------------------------------
    def _update_boss_broodmother(
        self,
        dt: float,
        dx: float,
        dy: float,
        dist: float,
        dungeon: Dungeon,
        events: EnemyActionEvents,
    ) -> Tuple[float, float]:
        if self.hp <= self.max_hp * 0.5:
            self.boss_phase = 2
        if dist > self.aggro_range:
            return (0.0, 0.0)

        nx = dx / dist if dist > 0.01 else 1.0
        ny = dy / dist if dist > 0.01 else 0.0
        pm = 1.25 if self.boss_phase == 2 else 1.0

        self.state_timer -= dt
        if self.state == "charging":
            if self.state_timer <= 0.0:
                self.state = "idle"
                events.shockwave = True
                # Acid burst on landing
                for i in range(8):
                    ang = (2 * math.pi * i) / 8
                    events.projectiles.append(
                        Projectile(
                            x=self.x,
                            y=self.y,
                            vx=math.cos(ang) * 210.0,
                            vy=math.sin(ang) * 210.0,
                            damage=13,
                            radius=7.5,
                            color=(95, 255, 130),
                        )
                    )
                return (0.0, 0.0)
            return (self.charge_dx * self.speed * 2.8 * pm, self.charge_dy * self.speed * 2.8 * pm)

        if self.state == "windup":
            if self.state_timer <= 0.0:
                self.state = "charging"
                self.state_timer = 0.44
            return (0.0, 0.0)

        self.ai_timer -= dt
        if self.ai_timer <= 0.0:
            pat = self.attack_sequence % 3
            self.attack_sequence += 1
            if pat == 0:
                # Venomous 5-globule fan
                base = math.atan2(dy, dx)
                for i in range(5):
                    ang = base + (i - 2) * 0.22
                    events.projectiles.append(
                        Projectile(
                            x=self.x + math.cos(ang) * 24,
                            y=self.y + math.sin(ang) * 24,
                            vx=math.cos(ang) * 245.0,
                            vy=math.sin(ang) * 245.0,
                            damage=14,
                            radius=7.5,
                            color=(120, 255, 105),
                        )
                    )
                self.ai_timer = 1.5 / pm
            elif pat == 1:
                self.state = "windup"
                self.state_timer = 0.48
                self.charge_dx, self.charge_dy = nx, ny
                self.ai_timer = 1.6 / pm
                return (0.0, 0.0)
            else:
                # Spawn a slime hatchling
                ang = random.uniform(0, 6.28)
                sx = self.x + math.cos(ang) * 48.0
                sy = self.y + math.sin(ang) * 48.0
                if not dungeon.circle_collides_walls(sx, sy, 15.0):
                    events.spawned_minions.append(
                        Enemy("slime", sx, sy, floor_num=1, room_index=self.room_index)
                    )
                self.ai_timer = 1.8 / pm

        return (nx * self.speed * pm, ny * self.speed * pm)

    # ------------------------------------------------------------------------
    # BOSS 2: HIGH INQUISITOR VAELEN (Floor 2 — Astral Spiral, Blink & Cross Beams)
    # ------------------------------------------------------------------------
    def _update_boss_inquisitor(
        self,
        dt: float,
        dx: float,
        dy: float,
        dist: float,
        dungeon: Dungeon,
        events: EnemyActionEvents,
    ) -> Tuple[float, float]:
        if self.hp <= self.max_hp * 0.5:
            self.boss_phase = 2
        if dist > self.aggro_range:
            return (0.0, 0.0)

        nx = dx / dist if dist > 0.01 else 1.0
        ny = dy / dist if dist > 0.01 else 0.0
        pm = 1.25 if self.boss_phase == 2 else 1.0

        # Strafe orbit around player
        strafe_vx = -ny * self.speed * 0.85 * pm
        strafe_vy = nx * self.speed * 0.85 * pm
        if dist > 230.0:
            strafe_vx += nx * self.speed * 0.65
            strafe_vy += ny * self.speed * 0.65
        elif dist < 130.0:
            strafe_vx -= nx * self.speed * 0.75
            strafe_vy -= ny * self.speed * 0.75

        self.ai_timer -= dt
        if self.ai_timer <= 0.0:
            pat = self.attack_sequence % 3
            self.attack_sequence += 1
            if pat == 0:
                # Twin-spiral astral orb burst
                count = 10 if self.boss_phase == 1 else 14
                for i in range(count):
                    ang = self.anim_timer + (2 * math.pi * i) / count
                    events.projectiles.append(
                        Projectile(
                            x=self.x,
                            y=self.y,
                            vx=math.cos(ang) * 235.0,
                            vy=math.sin(ang) * 235.0,
                            damage=16,
                            radius=7.0,
                            color=(220, 90, 255),
                        )
                    )
                self.ai_timer = 1.45 / pm
            elif pat == 1:
                # Precision aimed lance salvo
                base = math.atan2(dy, dx)
                for i in range(4):
                    ang = base + (i - 1.5) * 0.14
                    events.projectiles.append(
                        Projectile(
                            x=self.x + math.cos(ang) * 24,
                            y=self.y + math.sin(ang) * 24,
                            vx=math.cos(ang) * 320.0,
                            vy=math.sin(ang) * 320.0,
                            damage=17,
                            radius=7.5,
                            color=(95, 235, 255),
                        )
                    )
                self.ai_timer = 1.35 / pm
            else:
                # Astral Teleport step + shockwave
                step_ang = random.uniform(0, 6.28)
                tx = self.x + math.cos(step_ang) * 110.0
                ty = self.y + math.sin(step_ang) * 110.0
                if not dungeon.circle_collides_walls(tx, ty, self.radius):
                    self.x, self.y = tx, ty
                    events.shockwave = True
                self.ai_timer = 1.50 / pm

        return (strafe_vx, strafe_vy)

    # ------------------------------------------------------------------------
    # BOSS 3: KRAGOR, THE RIME COLOSSUS (Floor 3 — Avalanche Rush & Ice Shards)
    # ------------------------------------------------------------------------
    def _update_boss_behemoth(
        self,
        dt: float,
        dx: float,
        dy: float,
        dist: float,
        dungeon: Dungeon,
        events: EnemyActionEvents,
    ) -> Tuple[float, float]:
        if self.hp <= self.max_hp * 0.5:
            self.boss_phase = 2
        if dist > self.aggro_range:
            return (0.0, 0.0)

        nx = dx / dist if dist > 0.01 else 1.0
        ny = dy / dist if dist > 0.01 else 0.0
        pm = 1.25 if self.boss_phase == 2 else 1.0

        self.state_timer -= dt
        if self.state == "charging":
            if self.state_timer <= 0.0:
                self.state = "cooldown"
                self.state_timer = 0.40
                events.shockwave = True
                # Shatter ring of glacial spikes
                shards = 10 if self.boss_phase == 1 else 14
                for i in range(shards):
                    ang = (2 * math.pi * i) / shards
                    events.projectiles.append(
                        Projectile(
                            x=self.x,
                            y=self.y,
                            vx=math.cos(ang) * 250.0,
                            vy=math.sin(ang) * 250.0,
                            damage=19,
                            radius=8.0,
                            color=(105, 235, 255),
                        )
                    )
                return (0.0, 0.0)
            return (self.charge_dx * self.speed * 3.3 * pm, self.charge_dy * self.speed * 3.3 * pm)

        if self.state == "windup":
            if self.state_timer <= 0.0:
                self.state = "charging"
                self.state_timer = 0.54
            return (0.0, 0.0)

        if self.state == "cooldown":
            if self.state_timer <= 0.0:
                self.state = "idle"
            return (0.0, 0.0)

        self.ai_timer -= dt
        if self.ai_timer <= 0.0:
            if self.attack_sequence % 2 == 0:
                self.state = "windup"
                self.state_timer = 0.52 / pm
                self.charge_dx, self.charge_dy = nx, ny
                self.attack_sequence += 1
                self.ai_timer = 1.6 / pm
                return (0.0, 0.0)
            else:
                # Frost cone barrage
                base = math.atan2(dy, dx)
                for i in range(6):
                    ang = base + (i - 2.5) * 0.20
                    events.projectiles.append(
                        Projectile(
                            x=self.x + math.cos(ang) * 26,
                            y=self.y + math.sin(ang) * 26,
                            vx=math.cos(ang) * 270.0,
                            vy=math.sin(ang) * 270.0,
                            damage=18,
                            radius=8.0,
                            color=(175, 245, 255),
                        )
                    )
                self.attack_sequence += 1
                self.ai_timer = 1.5 / pm

        return (nx * self.speed * pm, ny * self.speed * pm)

    # ------------------------------------------------------------------------
    # BOSS 4: IGNIS, THE CINDER DRAKE (Floor 4 — Dragon Breath Stream & Meteor Ring)
    # ------------------------------------------------------------------------
    def _update_boss_wyrm(
        self,
        dt: float,
        dx: float,
        dy: float,
        dist: float,
        dungeon: Dungeon,
        events: EnemyActionEvents,
    ) -> Tuple[float, float]:
        if self.hp <= self.max_hp * 0.5:
            self.boss_phase = 2
        if dist > self.aggro_range:
            return (0.0, 0.0)

        nx = dx / dist if dist > 0.01 else 1.0
        ny = dy / dist if dist > 0.01 else 0.0
        pm = 1.28 if self.boss_phase == 2 else 1.0

        self.state_timer -= dt
        if self.state == "charging":
            if self.state_timer <= 0.0:
                self.state = "idle"
                events.shockwave = True
                return (0.0, 0.0)
            # Emit trailing fireballs while dashing!
            if random.random() < 0.35:
                perp_ang = math.atan2(self.charge_dy, self.charge_dx) + math.pi * 0.5
                for side in (-1, 1):
                    events.projectiles.append(
                        Projectile(
                            x=self.x,
                            y=self.y,
                            vx=math.cos(perp_ang) * side * 190.0,
                            vy=math.sin(perp_ang) * side * 190.0,
                            damage=18,
                            radius=7.0,
                            color=(255, 130, 40),
                        )
                    )
            return (self.charge_dx * self.speed * 3.1 * pm, self.charge_dy * self.speed * 3.1 * pm)

        if self.state == "windup":
            if self.state_timer <= 0.0:
                self.state = "charging"
                self.state_timer = 0.52
            return (0.0, 0.0)

        self.ai_timer -= dt
        if self.ai_timer <= 0.0:
            pat = self.attack_sequence % 3
            self.attack_sequence += 1
            if pat == 0:
                # Flamethrower cone volley
                base = math.atan2(dy, dx)
                for i in range(7):
                    ang = base + (i - 3) * 0.15
                    spd = 260.0 + (i % 2) * 45.0
                    events.projectiles.append(
                        Projectile(
                            x=self.x + math.cos(ang) * 26,
                            y=self.y + math.sin(ang) * 26,
                            vx=math.cos(ang) * spd,
                            vy=math.sin(ang) * spd,
                            damage=20,
                            radius=8.0,
                            color=(255, 150, 45),
                        )
                    )
                self.ai_timer = 1.35 / pm
            elif pat == 1:
                self.state = "windup"
                self.state_timer = 0.46 / pm
                self.charge_dx, self.charge_dy = nx, ny
                self.ai_timer = 1.5 / pm
                return (0.0, 0.0)
            else:
                # Molten supernova ring
                count = 12 if self.boss_phase == 1 else 16
                for i in range(count):
                    ang = self.anim_timer + (2 * math.pi * i) / count
                    events.projectiles.append(
                        Projectile(
                            x=self.x,
                            y=self.y,
                            vx=math.cos(ang) * 230.0,
                            vy=math.sin(ang) * 230.0,
                            damage=19,
                            radius=7.5,
                            color=(255, 200, 65),
                        )
                    )
                self.ai_timer = 1.55 / pm

        return (nx * self.speed * pm, ny * self.speed * pm)

    # ------------------------------------------------------------------------
    # BOSS 5: MALAKOR, THE OBSIDIAN KING (Floor 5 Final Boss)
    # ------------------------------------------------------------------------
    def _update_boss_malakor(
        self,
        dt: float,
        dx: float,
        dy: float,
        dist: float,
        dungeon: Dungeon,
        events: EnemyActionEvents,
    ) -> Tuple[float, float]:
        if self.hp <= self.max_hp * 0.5:
            self.boss_phase = 2

        if dist > self.aggro_range:
            return (0.0, 0.0)

        nx = dx / dist if dist > 0.01 else 1.0
        ny = dy / dist if dist > 0.01 else 0.0
        phase_mult = 1.28 if self.boss_phase == 2 else 1.0

        self.state_timer -= dt

        if self.state == "charging":
            if self.state_timer <= 0.0:
                self.state = "idle"
                self.ai_timer = 1.0 / phase_mult
                events.shockwave = True
                ring_count = 10 if self.boss_phase == 2 else 8
                for i in range(ring_count):
                    ang = (2 * math.pi * i) / ring_count
                    events.projectiles.append(
                        Projectile(
                            x=self.x,
                            y=self.y,
                            vx=math.cos(ang) * 235.0,
                            vy=math.sin(ang) * 235.0,
                            damage=18,
                            radius=8.0,
                            color=COLOR_BOSS_PROJECTILE,
                        )
                    )
                return (0.0, 0.0)
            return (
                self.charge_dx * self.speed * 3.1 * phase_mult,
                self.charge_dy * self.speed * 3.1 * phase_mult,
            )

        if self.state == "windup":
            if self.state_timer <= 0.0:
                self.state = "charging"
                self.state_timer = 0.52
            return (0.0, 0.0)

        self.ai_timer -= dt
        if self.ai_timer <= 0.0:
            pattern = self.attack_sequence % 4
            self.attack_sequence += 1

            if pattern == 0:
                base_ang = math.atan2(dy, dx)
                fan_count = 5 if self.boss_phase == 1 else 7
                spread = 0.18
                for i in range(fan_count):
                    offset = (i - (fan_count - 1) / 2.0) * spread
                    ang = base_ang + offset
                    events.projectiles.append(
                        Projectile(
                            x=self.x + math.cos(ang) * (self.radius + 8),
                            y=self.y + math.sin(ang) * (self.radius + 8),
                            vx=math.cos(ang) * 285.0,
                            vy=math.sin(ang) * 285.0,
                            damage=18,
                            radius=7.5,
                            color=COLOR_BOSS_PROJECTILE,
                        )
                    )
                self.ai_timer = 1.55 / phase_mult

            elif pattern == 1:
                self.state = "windup"
                self.state_timer = 0.55 / phase_mult
                self.charge_dx = nx
                self.charge_dy = ny
                return (0.0, 0.0)

            elif pattern == 2:
                num_orbs = 12 if self.boss_phase == 1 else 16
                rot_offset = self.anim_timer
                for i in range(num_orbs):
                    ang = rot_offset + (2 * math.pi * i) / num_orbs
                    events.projectiles.append(
                        Projectile(
                            x=self.x,
                            y=self.y,
                            vx=math.cos(ang) * 210.0,
                            vy=math.sin(ang) * 210.0,
                            damage=16,
                            radius=7.0,
                            color=COLOR_PROJECTILE_ENEMY,
                        )
                    )
                self.ai_timer = 1.65 / phase_mult

            else:
                spawn_ang = random.uniform(0, 2 * math.pi)
                sx = self.x + math.cos(spawn_ang) * (TILE_SIZE * 1.4)
                sy = self.y + math.sin(spawn_ang) * (TILE_SIZE * 1.4)
                if not dungeon.circle_collides_walls(sx, sy, 15.0):
                    events.spawned_minions.append(
                        Enemy("slime", sx, sy, floor_num=3, room_index=self.room_index)
                    )
                self.ai_timer = 1.75 / phase_mult

        return (nx * self.speed * phase_mult, ny * self.speed * phase_mult)
