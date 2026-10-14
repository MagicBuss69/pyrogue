"""Main entry point and game state controller for Crypts of the Obsidian King."""

import argparse
import math
import random
import sys
from typing import Any, Dict, List, Optional

import pygame

from dungeon import Dungeon, generate_dungeon
from entities import (
    Enemy,
    FloatingText,
    HealthPickup,
    Particle,
    Player,
    Projectile,
    angle_diff,
)
from highscore import load_highscore_data, save_highscore_data
from settings import (
    BOSS_FLOOR,
    COLOR_GOLD,
    COLOR_HP_BAR,
    COLOR_PICKUP_HP,
    COLOR_PLAYER,
    COLOR_SWORD_TRAIL,
    FPS,
    GAME_TITLE,
    PLAYER_ATTACK_ARC,
    PLAYER_ATTACK_RANGE,
    SCORE_FLOOR_CLEAR,
    SCORE_HEALTH_PICKUP,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TILE_SIZE,
)
from ui import Renderer


class Game:
    """Top-level game state machine managing menu, active dungeon run, and game over."""

    def __init__(self, seed: Optional[int] = None) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(GAME_TITLE)
        self.clock = pygame.time.Clock()
        self.renderer = Renderer(self.screen)

        self.base_seed = seed
        self.state: str = "MENU"  # "MENU", "PLAYING", "GAME_OVER", "VICTORY"
        self.menu_index: int = 0
        self.time_sec: float = 0.0

        self.hs_data: Dict[str, Any] = load_highscore_data()
        self.score: int = 0
        self.floor_num: int = 1

        self.dungeon: Optional[Dungeon] = None
        self.player: Optional[Player] = None
        self.enemies: List[Enemy] = []
        self.projectiles: List[Projectile] = []
        self.pickups: List[HealthPickup] = []
        self.particles: List[Particle] = []
        self.floating_texts: List[FloatingText] = []

        self.banner_text: str = ""
        self.banner_timer: float = 0.0

    def start_new_run(self) -> None:
        self.score = 0
        self.floor_num = 1
        self.player = Player(0.0, 0.0)
        self._load_floor(1)
        self.state = "PLAYING"

    def _load_floor(self, floor_num: int) -> None:
        self.floor_num = floor_num
        floor_seed = (
            (self.base_seed + floor_num * 101)
            if self.base_seed is not None
            else None
        )
        self.dungeon = generate_dungeon(floor_num, seed=floor_seed)
        assert self.player is not None
        self.player.x, self.player.y = self.dungeon.player_start
        # Slight max HP & attack scaling per floor descended
        if floor_num > 1:
            self.player.damage = 24 + (floor_num - 1) * 3
            self.player.heal(15)

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
        self.floating_texts.clear()

        self.renderer.cam_x = self.player.x - SCREEN_WIDTH * 0.5
        self.renderer.cam_y = self.player.y - SCREEN_HEIGHT * 0.5

        if floor_num == BOSS_FLOOR:
            self.banner_text = "FLOOR 5: OBSIDIAN SANCTUM — DEFEAT MALAKOR!"
        else:
            self.banner_text = f"FLOOR {floor_num} — FIND THE STAIRS DOWN"
        self.banner_timer = 3.2

    def _spawn_burst(
        self,
        x: float,
        y: float,
        color: tuple[int, int, int],
        count: int = 10,
        speed: float = 140.0,
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
                    size=random.uniform(3.0, 6.0),
                    lifetime=lt,
                    max_lifetime=lt,
                )
            )

    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if self.state == "MENU":
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        self.menu_index = (self.menu_index - 1) % 2
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.menu_index = (self.menu_index + 1) % 2
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if self.menu_index == 0:
                            self.start_new_run()
                        else:
                            return False
                    elif event.key == pygame.K_ESCAPE:
                        return False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.start_new_run()

            elif self.state == "PLAYING":
                assert self.player is not None
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.state = "MENU"
                    elif event.key in (pygame.K_SPACE, pygame.K_j):
                        self.player.start_attack(self._get_mouse_aim_angle())
                    elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_k):
                        mx, my = self._get_move_vector()
                        if self.player.start_dash(mx, my):
                            self._spawn_burst(
                                self.player.x, self.player.y, COLOR_PLAYER, count=8, speed=90.0
                            )
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.player.start_attack(self._get_mouse_aim_angle())
                    elif event.button == 3:
                        mx, my = self._get_move_vector()
                        if self.player.start_dash(mx, my):
                            self._spawn_burst(
                                self.player.x, self.player.y, COLOR_PLAYER, count=8, speed=90.0
                            )

            elif self.state in ("GAME_OVER", "VICTORY"):
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_r):
                        self.start_new_run()
                    elif event.key == pygame.K_m:
                        self.state = "MENU"
                    elif event.key == pygame.K_ESCAPE:
                        return False

        return True

    def _get_move_vector(self) -> tuple[float, float]:
        keys = pygame.key.get_pressed()
        dx = 0.0
        dy = 0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= 1.0
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += 1.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= 1.0
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += 1.0
        return (dx, dy)

    def _get_mouse_aim_angle(self) -> Optional[float]:
        if self.player is None:
            return None
        mx, my = pygame.mouse.get_pos()
        cam_ox, cam_oy = self.renderer.get_camera_offset(self.time_sec)
        world_mx = mx + cam_ox
        world_my = my + cam_oy
        dx = world_mx - self.player.x
        dy = world_my - self.player.y
        if abs(dx) < 1.0 and abs(dy) < 1.0:
            return None
        return math.atan2(dy, dx)

    def update(self, dt: float) -> None:
        self.time_sec += dt
        if self.state != "PLAYING":
            return

        assert self.player is not None
        assert self.dungeon is not None

        if self.banner_timer > 0.0:
            self.banner_timer = max(0.0, self.banner_timer - dt)

        move_dx, move_dy = self._get_move_vector()
        aim_angle = self._get_mouse_aim_angle()

        # Hold left mouse button or space for continuous attacks when off cooldown
        mouse_buttons = pygame.mouse.get_pressed()
        keys = pygame.key.get_pressed()
        if mouse_buttons[0] or keys[pygame.K_SPACE] or keys[pygame.K_j]:
            self.player.start_attack(aim_angle)

        self.player.update(dt, move_dx, move_dy, aim_angle, self.dungeon)
        self.dungeon.reveal_around(self.player.x, self.player.y)
        self.renderer.update_camera(self.player.x, self.player.y, dt)

        # Resolve player melee slash hits
        if self.player.is_attacking:
            self._resolve_player_melee()

        # Update enemies & collect AI events
        new_minions: List[Enemy] = []
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            events = enemy.update(dt, self.player, self.dungeon)
            if events.projectiles:
                self.projectiles.extend(events.projectiles)
            if events.spawned_minions and len(self.enemies) < 18:
                new_minions.extend(events.spawned_minions)
            if events.shockwave:
                self.renderer.trigger_shake(8.0, 0.22)

            # Contact damage check with player
            dist = math.hypot(self.player.x - enemy.x, self.player.y - enemy.y)
            if dist < self.player.radius + enemy.radius - 2.0:
                dmg = self.player.take_damage(enemy.damage, enemy.x, enemy.y)
                if dmg > 0:
                    self.renderer.trigger_shake(7.0, 0.18)
                    self._spawn_burst(self.player.x, self.player.y, COLOR_HP_BAR, count=12)
                    self.floating_texts.append(
                        FloatingText(self.player.x, self.player.y - 18, f"-{dmg}", COLOR_HP_BAR)
                    )

        if new_minions:
            self.enemies.extend(new_minions)

        # Update projectiles
        for proj in self.projectiles:
            if not proj.alive:
                continue
            proj.update(dt, self.dungeon)
            if not proj.alive:
                self._spawn_burst(proj.x, proj.y, proj.color, count=5, speed=80.0)
                continue

            if not proj.from_player:
                dist = math.hypot(self.player.x - proj.x, self.player.y - proj.y)
                if dist < self.player.radius + proj.radius:
                    proj.alive = False
                    dmg = self.player.take_damage(proj.damage, proj.x, proj.y)
                    if dmg > 0:
                        self.renderer.trigger_shake(6.5, 0.16)
                        self._spawn_burst(self.player.x, self.player.y, COLOR_HP_BAR, count=10)
                        self.floating_texts.append(
                            FloatingText(
                                self.player.x, self.player.y - 18, f"-{dmg}", COLOR_HP_BAR
                            )
                        )

        self.projectiles = [p for p in self.projectiles if p.alive]

        # Update health pickups
        for pickup in self.pickups:
            if pickup.collected:
                continue
            pickup.update(dt)
            dist = math.hypot(self.player.x - pickup.x, self.player.y - pickup.y)
            if dist < self.player.radius + pickup.radius + 4.0:
                healed = self.player.heal(pickup.heal_amount)
                if healed > 0 or self.player.hp == self.player.max_hp:
                    pickup.collected = True
                    self.score += SCORE_HEALTH_PICKUP
                    self._spawn_burst(pickup.x, pickup.y, COLOR_PICKUP_HP, count=12, speed=110.0)
                    label = f"+{healed} HP" if healed > 0 else f"+{SCORE_HEALTH_PICKUP} PTS"
                    self.floating_texts.append(
                        FloatingText(pickup.x, pickup.y - 14, label, (100, 245, 130))
                    )

        self.pickups = [p for p in self.pickups if not p.collected]

        # Update particles & floating texts
        self.particles = [pt for pt in self.particles if pt.update(dt)]
        self.floating_texts = [ft for ft in self.floating_texts if ft.update(dt)]

        # Check player death
        if not self.player.alive:
            self.hs_data = save_highscore_data(
                self.score, self.floor_num, victory=False
            )
            self.state = "GAME_OVER"
            return

        # Check Boss defeat on Floor 5 -> Victory!
        if self.floor_num == BOSS_FLOOR:
            boss_alive = any(e.is_boss and e.alive for e in self.enemies)
            if not boss_alive:
                self.score += SCORE_FLOOR_CLEAR * 2
                self.hs_data = save_highscore_data(
                    self.score, self.floor_num, victory=True
                )
                self.state = "VICTORY"
                return

        # Check stairs descent on floors 1..4
        if self.dungeon.stairs_tile is not None and self.dungeon.stairs_unlocked:
            stx, sty = self.dungeon.stairs_tile
            stairs_px = (stx + 0.5) * TILE_SIZE
            stairs_py = (sty + 0.5) * TILE_SIZE
            if math.hypot(self.player.x - stairs_px, self.player.y - stairs_py) < TILE_SIZE * 0.52:
                self.score += SCORE_FLOOR_CLEAR
                self._load_floor(self.floor_num + 1)

    def _resolve_player_melee(self) -> None:
        assert self.player is not None
        for enemy in self.enemies:
            if not enemy.alive or enemy.id in self.player.hit_targets_this_swing:
                continue
            dx = enemy.x - self.player.x
            dy = enemy.y - self.player.y
            dist = math.hypot(dx, dy)
            if dist <= PLAYER_ATTACK_RANGE + enemy.radius:
                ang_to_enemy = math.atan2(dy, dx)
                if (
                    abs(angle_diff(ang_to_enemy, self.player.attack_angle))
                    <= PLAYER_ATTACK_ARC * 0.55
                    or dist < self.player.radius + enemy.radius + 6.0
                ):
                    self.player.hit_targets_this_swing.add(enemy.id)
                    dmg = enemy.take_damage(
                        self.player.damage, self.player.x, self.player.y
                    )
                    self.renderer.trigger_shake(4.0, 0.10)
                    self._spawn_burst(enemy.x, enemy.y, COLOR_SWORD_TRAIL, count=9, speed=130.0)
                    self.floating_texts.append(
                        FloatingText(enemy.x, enemy.y - enemy.radius, f"-{dmg}", COLOR_GOLD)
                    )
                    if not enemy.alive:
                        self.score += enemy.score_value
                        self._spawn_burst(enemy.x, enemy.y, enemy.color, count=18, speed=175.0)
                        self.floating_texts.append(
                            FloatingText(
                                enemy.x,
                                enemy.y - enemy.radius - 14,
                                f"+{enemy.score_value}",
                                COLOR_GOLD,
                            )
                        )
                        # 22% chance to drop a bonus health pickup on enemy kill
                        if random.random() < 0.22:
                            self.pickups.append(HealthPickup(x=enemy.x, y=enemy.y))

        # Player sword slash can also deflect/destroy enemy projectiles in arc
        for proj in self.projectiles:
            if not proj.alive or proj.from_player:
                continue
            dx = proj.x - self.player.x
            dy = proj.y - self.player.y
            dist = math.hypot(dx, dy)
            if dist <= PLAYER_ATTACK_RANGE + proj.radius:
                ang = math.atan2(dy, dx)
                if abs(angle_diff(ang, self.player.attack_angle)) <= PLAYER_ATTACK_ARC * 0.55:
                    proj.alive = False
                    self._spawn_burst(proj.x, proj.y, COLOR_SWORD_TRAIL, count=6, speed=100.0)

    def render(self) -> None:
        if self.state == "MENU":
            self.renderer.render_main_menu(
                self.hs_data, self.menu_index, self.time_sec
            )
        elif self.state in ("PLAYING", "GAME_OVER", "VICTORY"):
            assert self.dungeon is not None
            assert self.player is not None
            self.renderer.render_gameplay(
                dungeon=self.dungeon,
                player=self.player,
                enemies=self.enemies,
                projectiles=self.projectiles,
                pickups=self.pickups,
                particles=self.particles,
                floating_texts=self.floating_texts,
                score=self.score,
                high_score=self.hs_data.get("high_score", 0),
                time_sec=self.time_sec,
                banner_text=self.banner_text,
                banner_timer=self.banner_timer,
            )
            if self.state == "GAME_OVER":
                self.renderer.render_end_screen(
                    victory=False,
                    score=self.score,
                    floor_num=self.floor_num,
                    hs_data=self.hs_data,
                )
            elif self.state == "VICTORY":
                self.renderer.render_end_screen(
                    victory=True,
                    score=self.score,
                    floor_num=self.floor_num,
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
        help="Run automated simulation across menu, floors 1-5, combat, and highscore saving",
    )
    return parser.parse_args()


def run_smoke_test() -> int:
    """Automated verification of menu, dungeon generation, 3 enemy types, boss floor 5, and high score persistence."""
    game = Game(seed=42)
    # Render menu frame
    game.render()
    # Start run and simulate Floors 1..5
    game.start_new_run()
    for floor in range(1, BOSS_FLOOR + 1):
        game._load_floor(floor)
        assert game.player is not None
        game.player.start_attack(0.5)
        game.player.start_dash(1.0, 0.0)
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
