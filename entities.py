"""Player, Enemies, Boss, Projectiles, Health Pickups, and Visual Effects."""

from dataclasses import dataclass, field
import math
import random
from typing import List, Optional, Set, Tuple

from dungeon import Dungeon
from settings import (
    COLOR_BOSS,
    COLOR_BOSS_PROJECTILE,
    COLOR_BRUTE,
    COLOR_CULTIST,
    COLOR_PICKUP_HP,
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
    PLAYER_DASH_COOLDOWN,
    PLAYER_DASH_DURATION,
    PLAYER_DASH_SPEED,
    PLAYER_INVULN_TIME,
    PLAYER_MAX_HP,
    PLAYER_RADIUS,
    PLAYER_SPEED,
    TILE_SIZE,
)


def angle_diff(a: float, b: float) -> float:
    """Smallest signed difference between two angles in radians."""
    diff = (a - b + math.pi) % (2 * math.pi) - math.pi
    return diff


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

    def update(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= max(0.0, 1.0 - 4.5 * dt)
        self.vy *= max(0.0, 1.0 - 4.5 * dt)
        self.lifetime -= dt
        return self.lifetime > 0


@dataclass
class FloatingText:
    """Floating combat or pickup text."""

    x: float
    y: float
    text: str
    color: Tuple[int, int, int]
    lifetime: float = 0.85
    max_lifetime: float = 0.85
    vy: float = -42.0

    def update(self, dt: float) -> bool:
        self.y += self.vy * dt
        self.vy *= max(0.0, 1.0 - 2.0 * dt)
        self.lifetime -= dt
        return self.lifetime > 0


@dataclass
class Projectile:
    """Ranged orb fired by enemies or the boss."""

    x: float
    y: float
    vx: float
    vy: float
    damage: int
    radius: float = 7.0
    color: Tuple[int, int, int] = COLOR_PROJECTILE_ENEMY
    lifetime: float = 3.2
    from_player: bool = False
    alive: bool = True

    def update(self, dt: float, dungeon: Dungeon) -> None:
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False
            return
        self.x += self.vx * dt
        self.y += self.vy * dt
        if dungeon.circle_collides_walls(self.x, self.y, self.radius * 0.7):
            self.alive = False


@dataclass
class HealthPickup:
    """Heart / potion pickup that restores player HP."""

    x: float
    y: float
    heal_amount: int = HEALTH_PICKUP_AMOUNT
    radius: float = HEALTH_PICKUP_RADIUS
    bob_timer: float = 0.0
    collected: bool = False

    def update(self, dt: float) -> None:
        self.bob_timer += dt * 3.5


class Player:
    """Playable dungeon delver with movement, dash, and directional sword slash."""

    def __init__(self, x: float, y: float) -> None:
        self.x: float = x
        self.y: float = y
        self.radius: float = PLAYER_RADIUS
        self.max_hp: int = PLAYER_MAX_HP
        self.hp: int = PLAYER_MAX_HP
        self.speed: float = PLAYER_SPEED
        self.damage: int = PLAYER_BASE_DAMAGE

        self.facing_angle: float = 0.0
        self.attack_timer: float = 0.0
        self.attack_cooldown: float = 0.0
        self.attack_angle: float = 0.0
        self.attack_swing_dir: int = 1
        self.hit_targets_this_swing: Set[int] = set()

        self.dash_timer: float = 0.0
        self.dash_cooldown: float = 0.0
        self.dash_dx: float = 1.0
        self.dash_dy: float = 0.0

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
    def is_dashing(self) -> bool:
        return self.dash_timer > 0.0

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def start_attack(self, aim_angle: Optional[float] = None) -> bool:
        if self.attack_cooldown > 0.0 or self.attack_timer > 0.0:
            return False
        if aim_angle is not None:
            self.facing_angle = aim_angle
        self.attack_angle = self.facing_angle
        self.attack_timer = PLAYER_ATTACK_DURATION
        self.attack_cooldown = PLAYER_ATTACK_COOLDOWN
        self.attack_swing_dir *= -1
        self.hit_targets_this_swing.clear()
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
        self.dash_timer = PLAYER_DASH_DURATION
        self.dash_cooldown = PLAYER_DASH_COOLDOWN
        self.invuln_timer = max(self.invuln_timer, PLAYER_DASH_DURATION)
        return True

    def take_damage(self, amount: int, source_x: float, source_y: float) -> int:
        if self.invuln_timer > 0.0 or not self.alive:
            return 0
        actual = max(1, int(amount))
        self.hp = max(0, self.hp - actual)
        self.invuln_timer = PLAYER_INVULN_TIME
        self.hurt_flash_timer = 0.2
        dx = self.x - source_x
        dy = self.y - source_y
        dist = math.hypot(dx, dy)
        if dist > 0.01:
            self.knockback_vx = (dx / dist) * 260.0
            self.knockback_vy = (dy / dist) * 260.0
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
    ) -> None:
        if self.attack_timer > 0.0:
            self.attack_timer = max(0.0, self.attack_timer - dt)
        if self.attack_cooldown > 0.0:
            self.attack_cooldown = max(0.0, self.attack_cooldown - dt)
        if self.dash_timer > 0.0:
            self.dash_timer = max(0.0, self.dash_timer - dt)
        if self.dash_cooldown > 0.0:
            self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        if self.invuln_timer > 0.0:
            self.invuln_timer = max(0.0, self.invuln_timer - dt)
        if self.hurt_flash_timer > 0.0:
            self.hurt_flash_timer = max(0.0, self.hurt_flash_timer - dt)

        if aim_angle is not None and not self.is_attacking:
            self.facing_angle = aim_angle
        elif (abs(move_dx) > 0.01 or abs(move_dy) > 0.01) and not self.is_attacking:
            self.facing_angle = math.atan2(move_dy, move_dx)

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
                self.walk_anim_timer += dt * 10.0
            else:
                vx = 0.0
                vy = 0.0
                self.is_moving = False

        vx += self.knockback_vx
        vy += self.knockback_vy
        self.knockback_vx *= max(0.0, 1.0 - 10.0 * dt)
        self.knockback_vy *= max(0.0, 1.0 - 10.0 * dt)

        self.x, self.y, _ = dungeon.move_with_sliding(
            self.x, self.y, vx, vy, self.radius, dt
        )


@dataclass
class EnemyActionEvents:
    """Events emitted by an enemy during its AI update."""

    projectiles: List[Projectile] = field(default_factory=list)
    spawned_minions: List["Enemy"] = field(default_factory=list)
    shockwave: bool = False


class Enemy:
    """Base enemy class supporting 3 distinct enemy types plus the Floor 5 Boss."""

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
        self.ai_timer: float = random.uniform(0.2, 0.9)
        self.state: str = "idle"
        self.state_timer: float = 0.0
        self.charge_dx: float = 0.0
        self.charge_dy: float = 0.0
        self.boss_phase: int = 1
        self.attack_sequence: int = 0

        scale = 1.0 + 0.14 * (floor_num - 1)

        if enemy_type == "slime":
            # Type 1: Venom Slime — rhythmic hop-lunges toward the player
            self.name = "Venom Slime"
            self.radius = 14.0
            self.max_hp = int(38 * scale)
            self.damage = int(10 + 2 * (floor_num - 1))
            self.speed = 155.0
            self.score_value = 50 * floor_num
            self.color = COLOR_SLIME
            self.aggro_range = 340.0
        elif enemy_type == "cultist":
            # Type 2: Void Cultist — kites at mid-range and shoots arcane bolts
            self.name = "Void Cultist"
            self.radius = 14.0
            self.max_hp = int(32 * scale)
            self.damage = int(12 + 2 * (floor_num - 1))
            self.speed = 125.0
            self.score_value = 75 * floor_num
            self.color = COLOR_CULTIST
            self.aggro_range = 430.0
        elif enemy_type == "brute":
            # Type 3: Bone Juggernaut — tanky charger with telegraphed bull-rush
            self.name = "Bone Juggernaut"
            self.radius = 19.0
            self.max_hp = int(72 * scale)
            self.damage = int(18 + 3 * (floor_num - 1))
            self.speed = 92.0
            self.score_value = 110 * floor_num
            self.color = COLOR_BRUTE
            self.aggro_range = 370.0
        elif enemy_type == "boss":
            # Floor 5 Boss: Malakor, the Obsidian King
            self.name = "Malakor, the Obsidian King"
            self.radius = 28.0
            self.max_hp = 520
            self.damage = 24
            self.speed = 115.0
            self.score_value = 2500
            self.color = COLOR_BOSS
            self.aggro_range = 680.0
            self.ai_timer = 1.4
        else:
            raise ValueError(f"Unknown enemy type: {enemy_type}")

        self.hp: int = self.max_hp

    @property
    def alive(self) -> bool:
        return self.hp > 0

    @property
    def is_boss(self) -> bool:
        return self.enemy_type == "boss"

    def take_damage(self, amount: int, source_x: float, source_y: float) -> int:
        if not self.alive:
            return 0
        actual = max(1, int(amount))
        self.hp = max(0, self.hp - actual)
        self.hurt_flash_timer = 0.14
        dx = self.x - source_x
        dy = self.y - source_y
        dist = math.hypot(dx, dy)
        kb_mult = 0.25 if self.is_boss else (0.55 if self.enemy_type == "brute" else 1.0)
        if dist > 0.01:
            self.knockback_vx = (dx / dist) * 280.0 * kb_mult
            self.knockback_vy = (dy / dist) * 280.0 * kb_mult
        return actual

    def update(
        self, dt: float, player: Player, dungeon: Dungeon
    ) -> EnemyActionEvents:
        events = EnemyActionEvents()
        self.anim_timer += dt * 5.0
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
        elif self.enemy_type == "boss":
            vx, vy = self._update_boss(dt, dx, dy, dist, dungeon, events)

        vx += self.knockback_vx
        vy += self.knockback_vy
        self.knockback_vx *= max(0.0, 1.0 - 9.0 * dt)
        self.knockback_vy *= max(0.0, 1.0 - 9.0 * dt)

        self.x, self.y, hit_wall = dungeon.move_with_sliding(
            self.x, self.y, vx, vy, self.radius, dt
        )
        if hit_wall and self.state == "charging":
            self.state = "cooldown"
            self.state_timer = 0.55

        return events

    def _update_slime(
        self, dt: float, dx: float, dy: float, dist: float
    ) -> Tuple[float, float]:
        """Slime AI: alternates between brief compression and fast hop-lunges toward player."""
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
        """Cultist AI: maintains medium distance (kites away if player is close) and fires bolts."""
        if dist > self.aggro_range:
            return (0.0, 0.0)

        nx = dx / dist if dist > 0.01 else 1.0
        ny = dy / dist if dist > 0.01 else 0.0

        vx, vy = 0.0, 0.0
        preferred_min = 145.0
        preferred_max = 260.0

        if dist < preferred_min:
            # Retreat from player
            vx = -nx * self.speed
            vy = -ny * self.speed
        elif dist > preferred_max:
            # Advance toward player
            vx = nx * self.speed * 0.85
            vy = ny * self.speed * 0.85
        else:
            # Strafe perpendicular to player
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
        """Brute AI: stalks player, telegraphs a fierce windup, then charges at high speed."""
        if dist > self.aggro_range and self.state == "idle":
            return (0.0, 0.0)

        nx = dx / dist if dist > 0.01 else 1.0
        ny = dy / dist if dist > 0.01 else 0.0

        self.state_timer -= dt
        if self.state == "idle":
            if (
                dist < 240.0
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
            # Lock direction during windup telegraph
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

    def _update_boss(
        self,
        dt: float,
        dx: float,
        dy: float,
        dist: float,
        dungeon: Dungeon,
        events: EnemyActionEvents,
    ) -> Tuple[float, float]:
        """Boss AI: multi-phase encounter with radial fire novas, aimed volleys, dashes, and minion summons."""
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
                # Emit radial burst at end of boss charge
                ring_count = 10 if self.boss_phase == 2 else 8
                for i in range(ring_count):
                    ang = (2 * math.pi * i) / ring_count
                    events.projectiles.append(
                        Projectile(
                            x=self.x,
                            y=self.y,
                            vx=math.cos(ang) * 230.0,
                            vy=math.sin(ang) * 230.0,
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
                # Pattern 0: Aimed fan volley at player
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
                # Pattern 1: Telegraphed Obsidian Charge
                self.state = "windup"
                self.state_timer = 0.55 / phase_mult
                self.charge_dx = nx
                self.charge_dy = ny
                return (0.0, 0.0)

            elif pattern == 2:
                # Pattern 2: Spiral / radial nova
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
                # Pattern 3: Summon Venom Slime minion if not overcrowded
                spawn_ang = random.uniform(0, 2 * math.pi)
                sx = self.x + math.cos(spawn_ang) * (TILE_SIZE * 1.4)
                sy = self.y + math.sin(spawn_ang) * (TILE_SIZE * 1.4)
                if not dungeon.circle_collides_walls(sx, sy, 15.0):
                    events.spawned_minions.append(
                        Enemy("slime", sx, sy, floor_num=3, room_index=self.room_index)
                    )
                self.ai_timer = 1.75 / phase_mult

        return (nx * self.speed * phase_mult, ny * self.speed * phase_mult)
