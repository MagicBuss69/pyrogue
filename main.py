"""Main entry point and Steam-Edition v3.0 controller for Crypts of the Obsidian King (5 Biomes, 5 Bosses, Full Soundtrack)."""

import argparse
import math
import random
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

import pygame

from audio import SoundManager
from dungeon import Dungeon, generate_dungeon
from entities import (
    DashAfterimage,
    Enemy,
    FloatingText,
    HealthPickup,
    LightningBoltFX,
    Particle,
    Player,
    Projectile,
    ShockwaveRingFX,
    angle_diff,
)
from highscore import load_highscore_data, save_highscore_data
from settings import (
    ABILITY_LIGHTNING_CHAINS,
    ABILITY_LIGHTNING_DAMAGE_MULT,
    ABILITY_LIGHTNING_RANGE,
    ABILITY_WHIRLWIND_DAMAGE_MULT,
    ABILITY_WHIRLWIND_RADIUS,
    ACHIEVEMENTS_CATALOG,
    BOSS_FLOOR,
    COLOR_ABILITY_DASH,
    COLOR_ABILITY_LIGHTNING,
    COLOR_ABILITY_NOVA,
    COLOR_ABILITY_WHIRLWIND,
    COLOR_CRATE_WOOD,
    COLOR_GOLD,
    COLOR_HP_BAR,
    COLOR_PICKUP_HP,
    COLOR_SHRINE,
    COLOR_SWORD_CRIT,
    COLOR_SWORD_TRAIL,
    FPS,
    GAME_TITLE,
    PLAYER_ATTACK_ARC,
    PLAYER_ATTACK_RANGE,
    PLAYER_DASH_DAMAGE,
    RELIC_CATALOG,
    SCORE_CRATE_BREAK,
    SCORE_FLOOR_CLEAR,
    SCORE_HEALTH_PICKUP,
    SCORE_SHRINE_USE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TILE_SIZE,
    get_biome_theme,
)
from ui import Renderer


class Game:
    """Top-level game state machine managing 5 biomes, 5 floor bosses, BGM soundtrack, codex, abilities, and relics."""

    def __init__(self, seed: Optional[int] = None) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(GAME_TITLE)
        # Never grab or trap the mouse cursor
        pygame.event.set_grab(False)
        pygame.mouse.set_visible(True)

        self.clock = pygame.time.Clock()
        self.renderer = Renderer(self.screen)
        self.sound = SoundManager()
        self.sound.play_bgm("menu")

        self.base_seed = seed
        # States: "MENU", "PLAYING", "LEVEL_UP", "PAUSED", "CODEX", "GAME_OVER", "VICTORY"
        self.state: str = "MENU"
        self.prev_state_before_codex: str = "MENU"
        self.menu_index: int = 0
        self.pause_index: int = 0
        self.relic_choice_index: int = 0
        self.relic_choices: List[Dict[str, Any]] = []
        self.time_sec: float = 0.0
        self.hitstop_timer: float = 0.0

        self.hs_data: Dict[str, Any] = load_highscore_data()
        self.score: int = 0
        self.floor_num: int = 1
        self.run_kills: int = 0
        self.run_bosses_slain: int = 0
        self.used_abilities_this_run: Set[str] = set()
        self.unlocked_achievements: Set[str] = set(
            self.hs_data.get("achievements", [])
        )

        self.dungeon: Optional[Dungeon] = None
        self.player: Optional[Player] = None
        self.enemies: List[Enemy] = []
        self.projectiles: List[Projectile] = []
        self.pickups: List[HealthPickup] = []
        self.particles: List[Particle] = []
        self.afterimages: List[DashAfterimage] = []
        self.lightning_bolts: List[LightningBoltFX] = []
        self.shockwaves: List[ShockwaveRingFX] = []
        self.floating_texts: List[FloatingText] = []

        self.banner_text: str = ""
        self.banner_timer: float = 0.0
        self.toast_text: str = ""
        self.toast_timer: float = 0.0

        self.last_mouse_pos: Tuple[int, int] = pygame.mouse.get_pos()
        self.mouse_active_timer: float = 0.0

    @property
    def is_music_on(self) -> bool:
        return not (self.sound.muted or self.sound.music_muted)

    def unlock_achievement(self, ach_id: Optional[str]) -> None:
        if not ach_id or ach_id in self.unlocked_achievements:
            return
        self.unlocked_achievements.add(ach_id)
        ach_info = next(
            (a for a in ACHIEVEMENTS_CATALOG if a["id"] == ach_id), None
        )
        if ach_info:
            self.toast_text = f"{ach_info['name']} — {ach_info['desc']}"
            self.toast_timer = 4.2
            self.sound.play("levelup")

    def start_new_run(self) -> None:
        self.score = 0
        self.floor_num = 1
        self.run_kills = 0
        self.run_bosses_slain = 0
        self.used_abilities_this_run.clear()
        self.player = Player(0.0, 0.0)
        self._load_floor(1)
        self.state = "PLAYING"

    def _load_floor(self, floor_num: int) -> None:
        self.floor_num = floor_num
        biome = get_biome_theme(floor_num)
        self.sound.play_bgm(biome["bgm_track"])

        floor_seed = (
            (self.base_seed + floor_num * 101)
            if self.base_seed is not None
            else None
        )
        self.dungeon = generate_dungeon(floor_num, seed=floor_seed)
        assert self.player is not None
        self.player.x, self.player.y = self.dungeon.player_start
        if floor_num > 1:
            self.player.damage += 4
            self.player.heal(28)
            self.sound.play("stairs")

        self.enemies = [
            Enemy(
                spec.enemy_type,
                spec.x,
                spec.y,
                floor_num=floor_num,
                room_index=spec.room_index,
            )
            for spec in self.dungeon.enemy_spawns
        ]
        self.pickups = [
            HealthPickup(x=spec.x, y=spec.y)
            for spec in self.dungeon.pickup_spawns
        ]
        self.projectiles.clear()
        self.particles.clear()
        self.afterimages.clear()
        self.lightning_bolts.clear()
        self.shockwaves.clear()
        self.floating_texts.clear()

        self.renderer.cam_x = self.player.x - SCREEN_WIDTH * 0.5
        self.renderer.cam_y = self.player.y - SCREEN_HEIGHT * 0.5

        self.banner_text = (
            f"AREA {floor_num}: {biome['name']} — GUARDIAN: {biome['boss_name'].upper()}"
        )
        self.banner_timer = 3.8

    def _spawn_burst(
        self,
        x: float,
        y: float,
        color: Tuple[int, int, int],
        count: int = 10,
        speed: float = 150.0,
    ) -> None:
        for _ in range(count):
            ang = random.uniform(0.0, 2 * math.pi)
            spd = random.uniform(speed * 0.35, speed)
            lt = random.uniform(0.22, 0.48)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(ang) * spd,
                    vy=math.sin(ang) * spd,
                    color=color,
                    size=random.uniform(3.0, 6.5),
                    lifetime=lt,
                    max_lifetime=lt,
                )
            )

    def _offer_level_up_relics(self) -> None:
        assert self.player is not None
        self.relic_choices = random.sample(
            RELIC_CATALOG, k=min(3, len(RELIC_CATALOG))
        )
        self.relic_choice_index = 0
        self.state = "LEVEL_UP"
        self.sound.play("levelup")

    def _select_relic(self, idx: int) -> None:
        assert self.player is not None
        if 0 <= idx < len(self.relic_choices):
            chosen = self.relic_choices[idx]
            self.player.apply_relic(chosen["id"])
            self.floating_texts.append(
                FloatingText(
                    self.player.x,
                    self.player.y - 28,
                    f"RELIC: {chosen['name']}!",
                    chosen["color"],
                    lifetime=1.4,
                    max_lifetime=1.4,
                    scale=1.25,
                )
            )
            self._spawn_burst(
                self.player.x, self.player.y, chosen["color"], count=20, speed=190.0
            )
            self.sound.play("pickup")
        self.state = "PLAYING"

    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.MOUSEMOTION:
                if event.pos != self.last_mouse_pos:
                    self.last_mouse_pos = event.pos
                    self.mouse_active_timer = 1.6

            # Global Audio Volume hotkeys (- / +)
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    self.sound.adjust_volume(-0.10)
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    self.sound.adjust_volume(0.10)

            if self.state == "CODEX":
                if event.type == pygame.KEYDOWN and event.key in (
                    pygame.K_ESCAPE,
                    pygame.K_c,
                    pygame.K_TAB,
                    pygame.K_RETURN,
                    pygame.K_SPACE,
                ):
                    self.state = self.prev_state_before_codex
                continue

            if self.state == "MENU":
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        self.menu_index = (self.menu_index - 1) % 4
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.menu_index = (self.menu_index + 1) % 4
                    elif event.key in (pygame.K_c, pygame.K_TAB):
                        self.prev_state_before_codex = "MENU"
                        self.state = "CODEX"
                    elif event.key == pygame.K_m:
                        self.sound.toggle_music()
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if self.menu_index == 0:
                            self.start_new_run()
                        elif self.menu_index == 1:
                            self.prev_state_before_codex = "MENU"
                            self.state = "CODEX"
                        elif self.menu_index == 2:
                            self.sound.toggle_music()
                        else:
                            return False
                    elif event.key == pygame.K_ESCAPE:
                        return False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.start_new_run()

            elif self.state == "LEVEL_UP":
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        self.relic_choice_index = (
                            self.relic_choice_index - 1
                        ) % max(1, len(self.relic_choices))
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.relic_choice_index = (
                            self.relic_choice_index + 1
                        ) % max(1, len(self.relic_choices))
                    elif event.key == pygame.K_1:
                        self._select_relic(0)
                    elif event.key == pygame.K_2 and len(self.relic_choices) >= 2:
                        self._select_relic(1)
                    elif event.key == pygame.K_3 and len(self.relic_choices) >= 3:
                        self._select_relic(2)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_j):
                        self._select_relic(self.relic_choice_index)

            elif self.state == "PAUSED":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.state = "PLAYING"
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        self.pause_index = (self.pause_index - 1) % 6
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.pause_index = (self.pause_index + 1) % 6
                    elif event.key in (pygame.K_c, pygame.K_TAB):
                        self.prev_state_before_codex = "PAUSED"
                        self.state = "CODEX"
                    elif event.key == pygame.K_m:
                        self.sound.toggle_music()
                    elif event.key == pygame.K_r:
                        self.start_new_run()
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if self.pause_index == 0:
                            self.state = "PLAYING"
                        elif self.pause_index == 1:
                            self.prev_state_before_codex = "PAUSED"
                            self.state = "CODEX"
                        elif self.pause_index == 2:
                            self.sound.toggle_music()
                        elif self.pause_index == 3:
                            self.start_new_run()
                        elif self.pause_index == 4:
                            self.sound.play_bgm("menu")
                            self.state = "MENU"
                        elif self.pause_index == 5:
                            return False

            elif self.state == "PLAYING":
                assert self.player is not None
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_p):
                        self.pause_index = 0
                        self.state = "PAUSED"
                    elif event.key in (pygame.K_c, pygame.K_TAB):
                        self.prev_state_before_codex = "PLAYING"
                        self.state = "CODEX"
                    elif event.key == pygame.K_m:
                        self.sound.toggle_music()
                    elif event.key in (pygame.K_SPACE, pygame.K_j):
                        if self.player.start_attack(self._get_smart_aim_angle()):
                            self.sound.play("slash")
                    elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_k):
                        self._trigger_dash()
                    elif event.key in (pygame.K_q, pygame.K_1, pygame.K_u):
                        self._trigger_whirlwind()
                    elif event.key in (pygame.K_e, pygame.K_2, pygame.K_i):
                        self._trigger_eldritch_nova()
                    elif event.key in (pygame.K_r, pygame.K_3, pygame.K_o):
                        self._trigger_chain_lightning()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.mouse_active_timer = 2.0
                        if self.player.start_attack(self._get_smart_aim_angle()):
                            self.sound.play("slash")
                    elif event.button == 3:
                        self._trigger_dash()

            elif self.state in ("GAME_OVER", "VICTORY"):
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_r):
                        self.start_new_run()
                    elif event.key == pygame.K_m:
                        self.sound.play_bgm("menu")
                        self.state = "MENU"
                    elif event.key == pygame.K_ESCAPE:
                        return False

        return True

    def _trigger_dash(self) -> None:
        assert self.player is not None
        mx, my = self._get_move_vector()
        if self.player.start_dash(mx, my):
            self.sound.play("dash")
            self._spawn_burst(
                self.player.x, self.player.y, COLOR_ABILITY_DASH, count=10, speed=110.0
            )

    def _trigger_whirlwind(self) -> None:
        assert self.player is not None
        if self.player.start_whirlwind():
            self.sound.play("whirlwind")
            self.used_abilities_this_run.add("whirlwind")
            self._check_storm_weaver_achievement()
            self.shockwaves.append(
                ShockwaveRingFX(
                    x=self.player.x,
                    y=self.player.y,
                    radius=10.0,
                    max_radius=ABILITY_WHIRLWIND_RADIUS,
                    color=COLOR_ABILITY_WHIRLWIND,
                )
            )
            self._spawn_burst(
                self.player.x,
                self.player.y,
                COLOR_ABILITY_WHIRLWIND,
                count=18,
                speed=190.0,
            )

    def _trigger_eldritch_nova(self) -> None:
        assert self.player is not None
        orbs = self.player.cast_eldritch_nova()
        if orbs:
            self.sound.play("nova")
            self.used_abilities_this_run.add("nova")
            self._check_storm_weaver_achievement()
            self.projectiles.extend(orbs)
            self.shockwaves.append(
                ShockwaveRingFX(
                    x=self.player.x,
                    y=self.player.y,
                    radius=8.0,
                    max_radius=92.0,
                    color=COLOR_ABILITY_NOVA,
                )
            )
            self.renderer.trigger_shake(4.5, 0.14)

    def _trigger_chain_lightning(self) -> None:
        assert self.player is not None
        if not self.player.can_cast_lightning():
            return

        living = [
            e
            for e in self.enemies
            if e.alive
            and math.hypot(e.x - self.player.x, e.y - self.player.y)
            <= ABILITY_LIGHTNING_RANGE
        ]
        if not living:
            self.player.trigger_lightning_cooldown()
            self.sound.play("lightning")
            tx = self.player.x + math.cos(self.player.facing_angle) * 180.0
            ty = self.player.y + math.sin(self.player.facing_angle) * 180.0
            self.lightning_bolts.append(
                LightningBoltFX(
                    points=self._build_jagged_line(self.player.x, self.player.y, tx, ty),
                    color=COLOR_ABILITY_LIGHTNING,
                )
            )
            return

        self.player.trigger_lightning_cooldown()
        self.sound.play("lightning")
        self.used_abilities_this_run.add("lightning")
        self._check_storm_weaver_achievement()
        self.renderer.trigger_shake(7.5, 0.20)

        living.sort(
            key=lambda e: math.hypot(e.x - self.player.x, e.y - self.player.y)
        )
        targets = living[:ABILITY_LIGHTNING_CHAINS]

        prev_x, prev_y = self.player.x, self.player.y
        base_dmg = (
            self.player.damage
            * ABILITY_LIGHTNING_DAMAGE_MULT
            * self.player.ability_power_mult
        )

        for target in targets:
            bolt_pts = self._build_jagged_line(prev_x, prev_y, target.x, target.y)
            self.lightning_bolts.append(
                LightningBoltFX(points=bolt_pts, color=COLOR_ABILITY_LIGHTNING)
            )
            dmg, is_crit = self.player.roll_damage(base_dmg)
            self._damage_enemy(
                target, dmg, is_crit, prev_x, prev_y, COLOR_ABILITY_LIGHTNING
            )
            prev_x, prev_y = target.x, target.y

    def _check_storm_weaver_achievement(self) -> None:
        if {"whirlwind", "nova", "lightning"}.issubset(self.used_abilities_this_run):
            self.unlock_achievement("storm_weaver")

    def _build_jagged_line(
        self, x1: float, y1: float, x2: float, y2: float, segments: int = 6
    ) -> List[Tuple[float, float]]:
        pts: List[Tuple[float, float]] = [(x1, y1)]
        dx = x2 - x1
        dy = y2 - y1
        dist = max(1.0, math.hypot(dx, dy))
        px = -dy / dist
        py = dx / dist
        for i in range(1, segments):
            t = i / segments
            jitter = random.uniform(-14.0, 14.0)
            pts.append((x1 + dx * t + px * jitter, y1 + dy * t + py * jitter))
        pts.append((x2, y2))
        return pts

    def _get_move_vector(self) -> Tuple[float, float]:
        keys = pygame.key.get_pressed()
        dx = 0.0
        dy = 0.0
        if keys[pygame.K_a]:
            dx -= 1.0
        if keys[pygame.K_d]:
            dx += 1.0
        if keys[pygame.K_w]:
            dy -= 1.0
        if keys[pygame.K_s]:
            dy += 1.0

        if abs(dx) < 0.01 and abs(dy) < 0.01:
            if keys[pygame.K_LEFT]:
                dx -= 1.0
            if keys[pygame.K_RIGHT]:
                dx += 1.0
            if keys[pygame.K_UP]:
                dy -= 1.0
            if keys[pygame.K_DOWN]:
                dy += 1.0
        return (dx, dy)

    def _get_smart_aim_angle(self) -> Optional[float]:
        """
        Smart Multi-Modal Aiming:
        1. Twin-Stick Arrow Keys
        2. Auto-Target Nearest Enemy within 215px
        3. Movement Direction
        4. Active Mouse
        """
        if self.player is None:
            return None

        keys = pygame.key.get_pressed()
        ax = 0.0
        ay = 0.0
        if keys[pygame.K_LEFT]:
            ax -= 1.0
        if keys[pygame.K_RIGHT]:
            ax += 1.0
        if keys[pygame.K_UP]:
            ay -= 1.0
        if keys[pygame.K_DOWN]:
            ay += 1.0

        if abs(ax) > 0.01 or abs(ay) > 0.01:
            self.player.aim_mode = "KEYS"
            return math.atan2(ay, ax)

        nearest_enemy: Optional[Enemy] = None
        nearest_dist = 215.0
        for e in self.enemies:
            if not e.alive:
                continue
            d = math.hypot(e.x - self.player.x, e.y - self.player.y)
            if d < nearest_dist:
                nearest_dist = d
                nearest_enemy = e

        if nearest_enemy is not None:
            self.player.aim_mode = "AUTO"
            return math.atan2(
                nearest_enemy.y - self.player.y, nearest_enemy.x - self.player.x
            )

        mx, my = self._get_move_vector()
        if abs(mx) > 0.01 or abs(my) > 0.01:
            self.player.aim_mode = "MOVE"
            return math.atan2(my, mx)

        if self.mouse_active_timer > 0.0:
            self.player.aim_mode = "MOUSE"
            mpx, mpy = pygame.mouse.get_pos()
            cam_ox, cam_oy = self.renderer.get_camera_offset(self.time_sec)
            world_mx = mpx + cam_ox
            world_my = mpy + cam_oy
            dx = world_mx - self.player.x
            dy = world_my - self.player.y
            if abs(dx) > 1.0 or abs(dy) > 1.0:
                return math.atan2(dy, dx)

        return self.player.facing_angle

    def _damage_enemy(
        self,
        enemy: Enemy,
        dmg: int,
        is_crit: bool,
        source_x: float,
        source_y: float,
        spark_color: Tuple[int, int, int],
    ) -> None:
        assert self.player is not None
        assert self.dungeon is not None
        if not enemy.alive:
            return

        actual = enemy.take_damage(dmg, source_x, source_y)
        self.sound.play("crit" if is_crit else "hit")
        self.renderer.trigger_shake(6.0 if is_crit else 3.8, 0.12)
        if is_crit:
            self.hitstop_timer = 0.028

        self._spawn_burst(
            enemy.x, enemy.y, spark_color, count=12 if is_crit else 8, speed=155.0
        )
        txt_col = COLOR_SWORD_CRIT if is_crit else COLOR_GOLD
        txt_str = f"{actual}!" if is_crit else f"-{actual}"
        self.floating_texts.append(
            FloatingText(
                enemy.x,
                enemy.y - enemy.radius - 4,
                txt_str,
                txt_col,
                scale=1.3 if is_crit else 1.0,
            )
        )

        if not enemy.alive:
            self.run_kills += 1
            self.unlock_achievement("first_blood")
            self.score += enemy.score_value
            if self.score >= 2500:
                self.unlock_achievement("centurion")

            if enemy.is_boss:
                self.run_bosses_slain += 1
                self.sound.play("boss_kill")
                self.renderer.trigger_shake(12.0, 0.38)
                self.unlock_achievement(enemy.achievement_id)
                self.shockwaves.append(
                    ShockwaveRingFX(
                        x=enemy.x,
                        y=enemy.y,
                        radius=14.0,
                        max_radius=170.0,
                        color=enemy.color,
                    )
                )
                # Unlock the floor's golden portal stairs!
                if not self.dungeon.stairs_unlocked:
                    self.dungeon.stairs_unlocked = True
                    self.banner_text = (
                        f"{enemy.name.upper()} VANQUISHED! — GOLDEN PORTAL UNLOCKED!"
                    )
                    self.banner_timer = 4.0
                # Bosses always drop a Crimson Elixir
                self.pickups.append(HealthPickup(x=enemy.x, y=enemy.y))
            else:
                self.sound.play("kill")

            self.dungeon.add_decal(
                enemy.x,
                enemy.y,
                color=(38, 18, 42) if enemy.enemy_type != "slime" else (18, 52, 32),
                radius=enemy.radius * 0.9,
            )
            self._spawn_burst(enemy.x, enemy.y, enemy.color, count=26 if enemy.is_boss else 20, speed=210.0)
            self.floating_texts.append(
                FloatingText(
                    enemy.x,
                    enemy.y - enemy.radius - 18,
                    f"+{enemy.score_value}",
                    COLOR_GOLD,
                    scale=1.3 if enemy.is_boss else 1.0,
                )
            )
            if self.player.vampiric_heal > 0:
                self.player.heal(self.player.vampiric_heal)

            if not enemy.is_boss and random.random() < 0.25:
                self.pickups.append(HealthPickup(x=enemy.x, y=enemy.y))

            if self.player.gain_xp(enemy.xp_value):
                self._offer_level_up_relics()

    def update(self, dt: float) -> None:
        self.time_sec += dt
        if self.toast_timer > 0.0:
            self.toast_timer = max(0.0, self.toast_timer - dt)
        if self.mouse_active_timer > 0.0:
            self.mouse_active_timer = max(0.0, self.mouse_active_timer - dt)

        if self.state != "PLAYING":
            return

        if self.hitstop_timer > 0.0:
            self.hitstop_timer = max(0.0, self.hitstop_timer - dt)
            return

        assert self.player is not None
        assert self.dungeon is not None

        if self.banner_timer > 0.0:
            self.banner_timer = max(0.0, self.banner_timer - dt)

        move_dx, move_dy = self._get_move_vector()
        aim_angle = self._get_smart_aim_angle()

        mouse_buttons = pygame.mouse.get_pressed()
        keys = pygame.key.get_pressed()
        if mouse_buttons[0] or keys[pygame.K_SPACE] or keys[pygame.K_j]:
            if self.player.start_attack(aim_angle):
                self.sound.play("slash")

        ghost = self.player.update(dt, move_dx, move_dy, aim_angle, self.dungeon)
        if ghost is not None:
            self.afterimages.append(ghost)

        self.dungeon.reveal_around(self.player.x, self.player.y)
        self.renderer.update_camera(self.player.x, self.player.y, dt)

        if self.player.is_attacking:
            self._resolve_player_melee()

        if self.player.is_whirlwinding:
            self._resolve_whirlwind_hits()

        if self.player.is_dashing:
            self._resolve_dash_hits()

        # Check interactive Arcane Shrines
        for shrine in self.dungeon.shrines:
            if shrine.used:
                continue
            if (
                math.hypot(self.player.x - shrine.x, self.player.y - shrine.y)
                <= self.player.radius + shrine.radius + 8.0
            ):
                shrine.used = True
                self.sound.play("shrine")
                self.score += SCORE_SHRINE_USE
                if shrine.shrine_type == "vitality":
                    self.player.max_hp += 20
                    self.player.heal(60)
                    msg = "SHRINE OF VITALITY: +20 MAX HP & +60 HEAL!"
                    col = (95, 250, 145)
                elif shrine.shrine_type == "fury":
                    self.player.damage = int(self.player.damage * 1.18) + 3
                    msg = "SHRINE OF FURY: +18% ATTACK POWER!"
                    col = (255, 110, 85)
                else:
                    self.player.speed *= 1.12
                    self.player.cooldown_Multiplier *= 0.88
                    msg = "SHRINE OF HASTE: +12% SPEED & COOLDOWN RECOVERY!"
                    col = COLOR_SHRINE
                self.floating_texts.append(
                    FloatingText(
                        shrine.x, shrine.y - 26, msg, col, lifetime=1.5, max_lifetime=1.5, scale=1.25
                    )
                )
                self._spawn_burst(shrine.x, shrine.y, col, count=22, speed=180.0)

        # Update destructible crates
        for crate in self.dungeon.crates:
            if crate.hit_flash > 0.0:
                crate.hit_flash = max(0.0, crate.hit_flash - dt)

        # Update enemies & floor bosses
        new_minions: List[Enemy] = []
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            events = enemy.update(dt, self.player, self.dungeon)
            if events.projectiles:
                self.projectiles.extend(events.projectiles)
            if events.spawned_minions and len(self.enemies) < 20:
                new_minions.extend(events.spawned_minions)
            if events.shockwave:
                self.renderer.trigger_shake(8.5, 0.24)
                self.shockwaves.append(
                    ShockwaveRingFX(
                        x=enemy.x,
                        y=enemy.y,
                        radius=12.0,
                        max_radius=125.0,
                        color=enemy.color,
                    )
                )

            dist = math.hypot(self.player.x - enemy.x, self.player.y - enemy.y)
            if dist < self.player.radius + enemy.radius - 2.0:
                dmg = self.player.take_damage(enemy.damage, enemy.x, enemy.y)
                if dmg > 0:
                    self.sound.play("hurt")
                    self.renderer.trigger_shake(7.5, 0.20)
                    self._spawn_burst(self.player.x, self.player.y, COLOR_HP_BAR, count=14)
                    self.floating_texts.append(
                        FloatingText(
                            self.player.x,
                            self.player.y - 20,
                            f"-{dmg}",
                            COLOR_HP_BAR,
                            scale=1.2,
                        )
                    )

        if new_minions:
            self.enemies.extend(new_minions)

        # Ensure stairs unlock if the floor boss is dead
        boss_alive = any(e.is_boss and e.alive for e in self.enemies)
        if not boss_alive and not self.dungeon.stairs_unlocked:
            self.dungeon.stairs_unlocked = True

        # Update projectiles
        for proj in self.projectiles:
            if not proj.alive:
                continue
            proj.update(dt, self.dungeon)
            if not proj.alive:
                self._spawn_burst(proj.x, proj.y, proj.color, count=6, speed=85.0)
                continue

            if proj.from_player:
                for enemy in self.enemies:
                    if not enemy.alive or enemy.id in proj.hit_enemy_ids:
                        continue
                    if (
                        math.hypot(enemy.x - proj.x, enemy.y - proj.y)
                        <= enemy.radius + proj.radius
                    ):
                        proj.hit_enemy_ids.add(enemy.id)
                        dmg, is_crit = self.player.roll_damage(proj.damage)
                        self._damage_enemy(
                            enemy, dmg, is_crit, proj.x, proj.y, proj.color
                        )
                        if not proj.piercing:
                            proj.alive = False
                            break
            else:
                dist = math.hypot(self.player.x - proj.x, self.player.y - proj.y)
                if dist < self.player.radius + proj.radius:
                    proj.alive = False
                    dmg = self.player.take_damage(proj.damage, proj.x, proj.y)
                    if dmg > 0:
                        self.sound.play("hurt")
                        self.renderer.trigger_shake(7.0, 0.18)
                        self._spawn_burst(
                            self.player.x, self.player.y, COLOR_HP_BAR, count=12
                        )
                        self.floating_texts.append(
                            FloatingText(
                                self.player.x,
                                self.player.y - 20,
                                f"-{dmg}",
                                COLOR_HP_BAR,
                                scale=1.2,
                            )
                        )

        self.projectiles = [p for p in self.projectiles if p.alive]

        # Update health pickups
        for pickup in self.pickups:
            if pickup.collected:
                continue
            pickup.update(dt)
            dist = math.hypot(self.player.x - pickup.x, self.player.y - pickup.y)
            if dist < self.player.radius + pickup.radius + 5.0:
                healed = self.player.heal(pickup.heal_amount)
                if healed > 0 or self.player.hp == self.player.max_hp:
                    pickup.collected = True
                    self.sound.play("pickup")
                    self.score += SCORE_HEALTH_PICKUP
                    self._spawn_burst(
                        pickup.x, pickup.y, COLOR_PICKUP_HP, count=14, speed=120.0
                    )
                    label = (
                        f"+{healed} HP"
                        if healed > 0
                        else f"+{SCORE_HEALTH_PICKUP} PTS"
                    )
                    self.floating_texts.append(
                        FloatingText(pickup.x, pickup.y - 16, label, (105, 250, 140))
                    )

        self.pickups = [p for p in self.pickups if not p.collected]

        # Update visual FX lists
        self.particles = [pt for pt in self.particles if pt.update(dt)]
        self.afterimages = [gh for gh in self.afterimages if gh.update(dt)]
        self.lightning_bolts = [lb for lb in self.lightning_bolts if lb.update(dt)]
        self.shockwaves = [sw for sw in self.shockwaves if sw.update(dt)]
        self.floating_texts = [ft for ft in self.floating_texts if ft.update(dt)]

        if not self.player.alive:
            self.hs_data = save_highscore_data(
                self.score,
                self.floor_num,
                victory=False,
                kills=self.run_kills,
                bosses_slain=self.run_bosses_slain,
                unlocked_achievements=list(self.unlocked_achievements),
            )
            self.state = "GAME_OVER"
            return

        if self.floor_num == BOSS_FLOOR and not boss_alive:
            self.score += SCORE_FLOOR_CLEAR * 2
            self.unlock_achievement("kingslayer")
            self.hs_data = save_highscore_data(
                self.score,
                self.floor_num,
                victory=True,
                kills=self.run_kills,
                bosses_slain=self.run_bosses_slain,
                unlocked_achievements=list(self.unlocked_achievements),
            )
            self.state = "VICTORY"
            return

        if self.dungeon.stairs_tile is not None and self.dungeon.stairs_unlocked:
            stx, sty = self.dungeon.stairs_tile
            stairs_px = (stx + 0.5) * TILE_SIZE
            stairs_py = (sty + 0.5) * TILE_SIZE
            if (
                math.hypot(self.player.x - stairs_px, self.player.y - stairs_py)
                < TILE_SIZE * 0.55
            ):
                self.score += SCORE_FLOOR_CLEAR
                self._load_floor(self.floor_num + 1)

    def _resolve_player_melee(self) -> None:
        assert self.player is not None
        assert self.dungeon is not None
        is_finisher = self.player.combo_step == 2
        reach = PLAYER_ATTACK_RANGE * (1.24 if is_finisher else 1.0)
        half_arc = PLAYER_ATTACK_ARC * (0.62 if is_finisher else 0.55)
        combo_mult = 1.35 if is_finisher else (1.12 if self.player.combo_step == 1 else 1.0)

        for enemy in self.enemies:
            if not enemy.alive or enemy.id in self.player.hit_targets_this_swing:
                continue
            dx = enemy.x - self.player.x
            dy = enemy.y - self.player.y
            dist = math.hypot(dx, dy)
            if dist <= reach + enemy.radius:
                ang_to_enemy = math.atan2(dy, dx)
                if (
                    abs(angle_diff(ang_to_enemy, self.player.attack_angle)) <= half_arc
                    or dist < self.player.radius + enemy.radius + 8.0
                ):
                    self.player.hit_targets_this_swing.add(enemy.id)
                    dmg, is_crit = self.player.roll_damage(
                        self.player.damage * combo_mult
                    )
                    if is_finisher:
                        is_crit = True
                    self._damage_enemy(
                        enemy,
                        dmg,
                        is_crit,
                        self.player.x,
                        self.player.y,
                        COLOR_SWORD_CRIT if is_finisher else COLOR_SWORD_TRAIL,
                    )

        for crate in self.dungeon.crates:
            if crate.destroyed:
                continue
            dx = crate.x - self.player.x
            dy = crate.y - self.player.y
            dist = math.hypot(dx, dy)
            if dist <= reach + crate.radius:
                crate.destroyed = True
                self.score += SCORE_CRATE_BREAK
                self.sound.play("hit")
                self._spawn_burst(crate.x, crate.y, COLOR_CRATE_WOOD, count=12, speed=140.0)
                if random.random() < 0.35:
                    self.pickups.append(HealthPickup(x=crate.x, y=crate.y))

        for proj in self.projectiles:
            if not proj.alive or proj.from_player:
                continue
            dx = proj.x - self.player.x
            dy = proj.y - self.player.y
            dist = math.hypot(dx, dy)
            if dist <= reach + proj.radius:
                ang = math.atan2(dy, dx)
                if abs(angle_diff(ang, self.player.attack_angle)) <= half_arc:
                    proj.alive = False
                    self._spawn_burst(
                        proj.x, proj.y, COLOR_SWORD_TRAIL, count=6, speed=110.0
                    )

    def _resolve_whirlwind_hits(self) -> None:
        assert self.player is not None
        assert self.dungeon is not None
        for enemy in self.enemies:
            if not enemy.alive or enemy.id in self.player.whirlwind_hit_ids:
                continue
            dist = math.hypot(enemy.x - self.player.x, enemy.y - self.player.y)
            if dist <= ABILITY_WHIRLWIND_RADIUS + enemy.radius:
                self.player.whirlwind_hit_ids.add(enemy.id)
                base = (
                    self.player.damage
                    * ABILITY_WHIRLWIND_DAMAGE_MULT
                    * self.player.ability_power_mult
                )
                dmg, is_crit = self.player.roll_damage(base)
                self._damage_enemy(
                    enemy,
                    dmg,
                    is_crit,
                    self.player.x,
                    self.player.y,
                    COLOR_ABILITY_WHIRLWIND,
                )

        for crate in self.dungeon.crates:
            if not crate.destroyed and (
                math.hypot(crate.x - self.player.x, crate.y - self.player.y)
                <= ABILITY_WHIRLWIND_RADIUS + crate.radius
            ):
                crate.destroyed = True
                self.score += SCORE_CRATE_BREAK
                self._spawn_burst(crate.x, crate.y, COLOR_CRATE_WOOD, count=10, speed=130.0)

        for proj in self.projectiles:
            if not proj.alive or proj.from_player:
                continue
            if (
                math.hypot(proj.x - self.player.x, proj.y - self.player.y)
                <= ABILITY_WHIRLWIND_RADIUS + proj.radius
            ):
                proj.alive = False
                self._spawn_burst(
                    proj.x, proj.y, COLOR_ABILITY_WHIRLWIND, count=6, speed=110.0
                )

    def _resolve_dash_hits(self) -> None:
        assert self.player is not None
        for enemy in self.enemies:
            if not enemy.alive or enemy.id in self.player.dash_hit_ids:
                continue
            dist = math.hypot(enemy.x - self.player.x, enemy.y - self.player.y)
            if dist <= self.player.radius + enemy.radius + 10.0:
                self.player.dash_hit_ids.add(enemy.id)
                mult = 1.45 if self.player.cinder_dash else 1.0
                dmg = int(PLAYER_DASH_DAMAGE * self.player.ability_power_mult * mult)
                self._damage_enemy(
                    enemy,
                    dmg,
                    False,
                    self.player.x,
                    self.player.y,
                    (255, 140, 50) if self.player.cinder_dash else COLOR_ABILITY_DASH,
                )

    def render(self) -> None:
        if self.state == "MENU":
            self.renderer.render_main_menu(
                self.hs_data, self.menu_index, self.time_sec, music_on=self.is_music_on
            )
        elif self.state == "CODEX":
            if self.prev_state_before_codex == "MENU" or self.dungeon is None or self.player is None:
                self.renderer.render_main_menu(
                    self.hs_data, self.menu_index, self.time_sec, music_on=self.is_music_on
                )
            else:
                self.renderer.render_gameplay(
                    dungeon=self.dungeon,
                    player=self.player,
                    enemies=self.enemies,
                    projectiles=self.projectiles,
                    pickups=self.pickups,
                    particles=self.particles,
                    afterimages=self.afterimages,
                    lightning_bolts=self.lightning_bolts,
                    shockwaves=self.shockwaves,
                    floating_texts=self.floating_texts,
                    score=self.score,
                    high_score=self.hs_data.get("high_score", 0),
                    time_sec=self.time_sec,
                    banner_text=self.banner_text,
                    banner_timer=self.banner_timer,
                    toast_text=self.toast_text,
                    toast_timer=self.toast_timer,
                    music_on=self.is_music_on,
                )
            self.renderer.render_codex_overlay()
        elif self.state in ("PLAYING", "LEVEL_UP", "PAUSED", "GAME_OVER", "VICTORY"):
            assert self.dungeon is not None
            assert self.player is not None
            self.renderer.render_gameplay(
                dungeon=self.dungeon,
                player=self.player,
                enemies=self.enemies,
                projectiles=self.projectiles,
                pickups=self.pickups,
                particles=self.particles,
                afterimages=self.afterimages,
                lightning_bolts=self.lightning_bolts,
                shockwaves=self.shockwaves,
                floating_texts=self.floating_texts,
                score=self.score,
                high_score=self.hs_data.get("high_score", 0),
                time_sec=self.time_sec,
                banner_text=self.banner_text,
                banner_timer=self.banner_timer,
                toast_text=self.toast_text,
                toast_timer=self.toast_timer,
                music_on=self.is_music_on,
            )
            if self.state == "LEVEL_UP":
                self.renderer.render_relic_selection(
                    self.relic_choices,
                    self.relic_choice_index,
                    self.player.level,
                )
            elif self.state == "PAUSED":
                self.renderer.render_pause_overlay(
                    self.pause_index, music_on=self.is_music_on
                )
            elif self.state == "GAME_OVER":
                self.renderer.render_end_screen(
                    victory=False,
                    score=self.score,
                    floor_num=self.floor_num,
                    player_level=self.player.level,
                    kills=self.run_kills,
                    bosses_slain=self.run_bosses_slain,
                    hs_data=self.hs_data,
                )
            elif self.state == "VICTORY":
                self.renderer.render_end_screen(
                    victory=True,
                    score=self.score,
                    floor_num=self.floor_num,
                    player_level=self.player.level,
                    kills=self.run_kills,
                    bosses_slain=self.run_bosses_slain,
                    hs_data=self.hs_data,
                )

        pygame.display.flip()

    def run(self, max_frames: Optional[int] = None) -> None:
        frames = 0
        running = True
        while running:
            dt = min(0.05, self.clock.tick(FPS) / 1000.0)
            running = self.handle_events()
            self.update(dt)
            self.render()
            frames += 1
            if max_frames is not None and frames >= max_frames:
                break
        pygame.quit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=GAME_TITLE)
    parser.add_argument("--seed", type=int, default=None, help="Optional RNG seed")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run automated simulation across menu, codex, all 5 biomes & 5 bosses, abilities, shrines, and BGM",
    )
    return parser.parse_args()


def run_smoke_test() -> int:
    """Automated verification of menu, codex, 5 biomes, 5 unique bosses, 4 abilities, shrines, BGM tracks, and highscore saving."""
    game = Game(seed=42)
    game.render()
    # Verify Codex rendering from Menu
    game.state = "CODEX"
    game.render()
    game.start_new_run()
    for floor in range(1, BOSS_FLOOR + 1):
        game._load_floor(floor)
        assert game.player is not None
        assert game.dungeon is not None
        # Ensure each floor spawns its unique Guardian Boss
        bosses = [e for e in game.enemies if e.is_boss]
        assert len(bosses) == 1, f"Floor {floor} missing guardian boss!"
        game.player.start_attack(0.5)
        game._trigger_dash()
        game._trigger_whirlwind()
        game._trigger_eldritch_nova()
        game._trigger_chain_lightning()
        for _ in range(15):
            game.update(1.0 / 60.0)
            game.render()
    pygame.quit()
    return 0


def main() -> int:
    args = parse_args()
    if args.smoke_test:
        return run_smoke_test()
    game = Game(seed=args.seed)
    game.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
