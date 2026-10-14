"""Rendering engine for the dungeon, entities, HUD, minimap, and menu screens."""

import math
from typing import Any, Dict, List, Optional, Tuple

import pygame

from dungeon import Dungeon
from entities import Enemy, FloatingText, HealthPickup, Particle, Player, Projectile
from settings import (
    BOSS_FLOOR,
    COLOR_BG,
    COLOR_BOSS,
    COLOR_BOSS_CROWN,
    COLOR_BRUTE,
    COLOR_BRUTE_ARMOR,
    COLOR_CULTIST,
    COLOR_CULTIST_ROBE,
    COLOR_FLOOR_A,
    COLOR_FLOOR_ACCENT,
    COLOR_FLOOR_B,
    COLOR_GOLD,
    COLOR_HP_BAR,
    COLOR_HP_BG,
    COLOR_PICKUP_GLOW,
    COLOR_PICKUP_HP,
    COLOR_PLAYER,
    COLOR_PLAYER_CAPE,
    COLOR_SLIME,
    COLOR_SLIME_CORE,
    COLOR_STAIRS,
    COLOR_STAIRS_LOCKED,
    COLOR_STAMINA_BAR,
    COLOR_SWORD,
    COLOR_SWORD_TRAIL,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
    COLOR_UI_BG,
    COLOR_UI_BORDER,
    COLOR_VOID,
    COLOR_WALL_HIGHLIGHT,
    COLOR_WALL_SIDE,
    COLOR_WALL_TOP,
    GAME_TITLE,
    PLAYER_ATTACK_ARC,
    PLAYER_ATTACK_DURATION,
    PLAYER_ATTACK_RANGE,
    PLAYER_DASH_COOLDOWN,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TILE_FLOOR,
    TILE_SIZE,
    TILE_STAIRS_DOWN,
    TILE_WALL,
)


class Renderer:
    """Handles all 2D rendering, camera projection, and UI overlays."""

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        pygame.font.init()
        self.font_title = pygame.font.SysFont("dejavusans", 48, bold=True)
        self.font_subtitle = pygame.font.SysFont("dejavusans", 26, bold=True)
        self.font_md = pygame.font.SysFont("dejavusans", 20, bold=True)
        self.font_sm = pygame.font.SysFont("dejavusans", 16)
        self.font_xs = pygame.font.SysFont("dejavusans", 13, bold=True)

        self.cam_x: float = 0.0
        self.cam_y: float = 0.0
        self.shake_timer: float = 0.0
        self.shake_magnitude: float = 0.0

    def trigger_shake(self, magnitude: float = 6.0, duration: float = 0.16) -> None:
        self.shake_magnitude = max(self.shake_magnitude, magnitude)
        self.shake_timer = max(self.shake_timer, duration)

    def update_camera(self, target_x: float, target_y: float, dt: float) -> None:
        desired_x = target_x - SCREEN_WIDTH * 0.5
        desired_y = target_y - SCREEN_HEIGHT * 0.5
        lerp = min(1.0, dt * 10.0)
        self.cam_x += (desired_x - self.cam_x) * lerp
        self.cam_y += (desired_y - self.cam_y) * lerp

        if self.shake_timer > 0.0:
            self.shake_timer = max(0.0, self.shake_timer - dt)
            if self.shake_timer <= 0.0:
                self.shake_magnitude = 0.0

    def get_camera_offset(self, time_sec: float) -> Tuple[int, int]:
        ox = int(self.cam_x)
        oy = int(self.cam_y)
        if self.shake_timer > 0.0:
            ox += int(math.sin(time_sec * 65.0) * self.shake_magnitude)
            oy += int(math.cos(time_sec * 53.0) * self.shake_magnitude)
        return (ox, oy)

    def render_gameplay(
        self,
        dungeon: Dungeon,
        player: Player,
        enemies: List[Enemy],
        projectiles: List[Projectile],
        pickups: List[HealthPickup],
        particles: List[Particle],
        floating_texts: List[FloatingText],
        score: int,
        high_score: int,
        time_sec: float,
        banner_text: str = "",
        banner_timer: float = 0.0,
    ) -> None:
        self.screen.fill(COLOR_VOID)
        cam_ox, cam_oy = self.get_camera_offset(time_sec)

        self._draw_dungeon(dungeon, cam_ox, cam_oy, time_sec)
        self._draw_pickups(pickups, cam_ox, cam_oy)
        self._draw_enemies(enemies, cam_ox, cam_oy)
        self._draw_player(player, cam_ox, cam_oy)
        self._draw_projectiles(projectiles, cam_ox, cam_oy)
        self._draw_particles(particles, cam_ox, cam_oy)
        self._draw_floating_texts(floating_texts, cam_ox, cam_oy)

        self._draw_hud(
            player=player,
            dungeon=dungeon,
            enemies=enemies,
            score=score,
            high_score=high_score,
            banner_text=banner_text,
            banner_timer=banner_timer,
        )

    def _draw_dungeon(
        self, dungeon: Dungeon, cam_ox: int, cam_oy: int, time_sec: float
    ) -> None:
        start_tx = max(0, cam_ox // TILE_SIZE - 1)
        end_tx = min(dungeon.width, (cam_ox + SCREEN_WIDTH) // TILE_SIZE + 2)
        start_ty = max(0, cam_oy // TILE_SIZE - 1)
        end_ty = min(dungeon.height, (cam_oy + SCREEN_HEIGHT) // TILE_SIZE + 2)

        for ty in range(start_ty, end_ty):
            for tx in range(start_tx, end_tx):
                tile = dungeon.grid[ty][tx]
                if tile == 0:
                    continue

                sx = tx * TILE_SIZE - cam_ox
                sy = ty * TILE_SIZE - cam_oy
                rect = pygame.Rect(sx, sy, TILE_SIZE, TILE_SIZE)

                if tile == TILE_WALL:
                    pygame.draw.rect(self.screen, COLOR_WALL_SIDE, rect)
                    top_rect = pygame.Rect(sx, sy, TILE_SIZE, TILE_SIZE - 10)
                    pygame.draw.rect(self.screen, COLOR_WALL_TOP, top_rect)
                    pygame.draw.line(
                        self.screen,
                        COLOR_WALL_HIGHLIGHT,
                        (sx, sy),
                        (sx + TILE_SIZE - 1, sy),
                        2,
                    )
                    pygame.draw.rect(self.screen, (20, 18, 30), rect, 1)
                elif tile in (TILE_FLOOR, TILE_STAIRS_DOWN):
                    base_col = COLOR_FLOOR_A if (tx + ty) % 2 == 0 else COLOR_FLOOR_B
                    pygame.draw.rect(self.screen, base_col, rect)
                    if (tx * 7 + ty * 13) % 11 == 0:
                        speck = pygame.Rect(sx + 12, sy + 16, 6, 4)
                        pygame.draw.rect(self.screen, COLOR_FLOOR_ACCENT, speck)

                    if tile == TILE_STAIRS_DOWN:
                        self._draw_stairs(sx, sy, dungeon.stairs_unlocked, time_sec)

    def _draw_stairs(
        self, sx: int, sy: int, unlocked: bool, time_sec: float
    ) -> None:
        outer = pygame.Rect(sx + 4, sy + 4, TILE_SIZE - 8, TILE_SIZE - 8)
        col = COLOR_STAIRS if unlocked else COLOR_STAIRS_LOCKED
        pygame.draw.rect(self.screen, (14, 12, 22), outer, border_radius=6)
        pygame.draw.rect(self.screen, col, outer, 3, border_radius=6)

        for step in range(4):
            step_rect = pygame.Rect(
                sx + 10 + step * 3,
                sy + 11 + step * 7,
                TILE_SIZE - 20 - step * 6,
                5,
            )
            pygame.draw.rect(self.screen, col, step_rect, border_radius=2)

        if unlocked:
            pulse = int(4 + 3 * math.sin(time_sec * 5.0))
            cx = sx + TILE_SIZE // 2
            cy = sy + TILE_SIZE // 2
            pygame.draw.circle(self.screen, COLOR_GOLD, (cx, cy), pulse, 1)

    def _draw_pickups(
        self, pickups: List[HealthPickup], cam_ox: int, cam_oy: int
    ) -> None:
        for p in pickups:
            if p.collected:
                continue
            sx = int(p.x - cam_ox)
            sy = int(p.y - cam_oy + math.sin(p.bob_timer) * 4.0)

            # Soft shadow
            pygame.draw.ellipse(
                self.screen,
                (12, 10, 18),
                pygame.Rect(sx - 10, int(p.y - cam_oy) + 8, 20, 7),
            )
            # Outer glow
            pygame.draw.circle(self.screen, COLOR_PICKUP_GLOW, (sx, sy), int(p.radius + 3), 2)
            pygame.draw.circle(self.screen, COLOR_PICKUP_HP, (sx, sy), int(p.radius))
            # White healing cross
            pygame.draw.rect(self.screen, (255, 255, 255), pygame.Rect(sx - 2, sy - 6, 4, 12))
            pygame.draw.rect(self.screen, (255, 255, 255), pygame.Rect(sx - 6, sy - 2, 12, 4))

    def _draw_player(self, player: Player, cam_ox: int, cam_oy: int) -> None:
        sx = int(player.x - cam_ox)
        sy = int(player.y - cam_oy)

        # Draw sword slash arc behind/around player if attacking
        if player.is_attacking:
            self._draw_sword_slash(player, sx, sy)

        # Shadow
        pygame.draw.ellipse(
            self.screen,
            (10, 9, 16),
            pygame.Rect(sx - 14, sy + 9, 28, 10),
        )

        bob = int(math.sin(player.walk_anim_timer * 2.0) * 2.5) if player.is_moving else 0
        body_col = (
            (255, 255, 255)
            if player.hurt_flash_timer > 0.0
            else (165, 235, 255) if player.is_dashing else COLOR_PLAYER
        )

        # Cape / shoulders
        pygame.draw.circle(self.screen, COLOR_PLAYER_CAPE, (sx, sy + 2 + bob), int(player.radius))
        # Main hero body
        pygame.draw.circle(self.screen, body_col, (sx, sy - 2 + bob), int(player.radius - 2))
        pygame.draw.circle(self.screen, (25, 40, 68), (sx, sy - 2 + bob), int(player.radius - 2), 2)

        # Visor / eyes facing aim direction
        ex = sx + int(math.cos(player.facing_angle) * 6)
        ey = sy - 3 + bob + int(math.sin(player.facing_angle) * 6)
        pygame.draw.circle(self.screen, (255, 255, 255), (ex, ey), 4)
        pygame.draw.circle(self.screen, (20, 30, 55), (ex, ey), 2)

    def _draw_sword_slash(self, player: Player, sx: int, sy: int) -> None:
        progress = 1.0 - (player.attack_timer / PLAYER_ATTACK_DURATION)
        half_arc = PLAYER_ATTACK_ARC * 0.5
        start_ang = player.attack_angle - half_arc
        end_ang = player.attack_angle + half_arc

        # Draw sweeping crescent polygon
        points: List[Tuple[int, int]] = [(sx, sy)]
        steps = 12
        for i in range(steps + 1):
            t = i / steps
            ang = start_ang + (end_ang - start_ang) * t
            px = sx + int(math.cos(ang) * PLAYER_ATTACK_RANGE)
            py = sy + int(math.sin(ang) * PLAYER_ATTACK_RANGE)
            points.append((px, py))

        if len(points) >= 3:
            pygame.draw.polygon(self.screen, COLOR_SWORD_TRAIL, points, 2)

        # Draw current blade position
        if player.attack_swing_dir > 0:
            blade_ang = start_ang + (end_ang - start_ang) * progress
        else:
            blade_ang = end_ang - (end_ang - start_ang) * progress

        bx = sx + int(math.cos(blade_ang) * (PLAYER_ATTACK_RANGE + 4))
        by = sy + int(math.sin(blade_ang) * (PLAYER_ATTACK_RANGE + 4))
        pygame.draw.line(self.screen, COLOR_SWORD, (sx, sy), (bx, by), 5)

    def _draw_enemies(
        self, enemies: List[Enemy], cam_ox: int, cam_oy: int
    ) -> None:
        for e in enemies:
            if not e.alive:
                continue
            sx = int(e.x - cam_ox)
            sy = int(e.y - cam_oy)
            r = int(e.radius)

            # Shadow
            pygame.draw.ellipse(
                self.screen,
                (10, 9, 16),
                pygame.Rect(sx - r, sy + r - 6, r * 2, 10),
            )

            col = (255, 255, 255) if e.hurt_flash_timer > 0.0 else e.color

            if e.enemy_type == "slime":
                squish = int(math.sin(e.anim_timer * 2.2) * 3)
                rect = pygame.Rect(
                    sx - r - squish // 2,
                    sy - r + squish,
                    (r + squish // 2) * 2,
                    (r - squish // 2) * 2,
                )
                pygame.draw.ellipse(self.screen, COLOR_SLIME_CORE, rect)
                inner = rect.inflate(-6, -6)
                pygame.draw.ellipse(self.screen, col, inner)
                pygame.draw.circle(self.screen, (20, 45, 25), (sx - 4, sy - 2), 3)
                pygame.draw.circle(self.screen, (20, 45, 25), (sx + 4, sy - 2), 3)

            elif e.enemy_type == "cultist":
                pts = [
                    (sx, sy - r - 4),
                    (sx - r, sy + r),
                    (sx + r, sy + r),
                ]
                pygame.draw.polygon(self.screen, COLOR_CULTIST_ROBE, pts)
                pygame.draw.circle(self.screen, col, (sx, sy - 3), r - 3)
                # Glowing arcane eyes
                pygame.draw.circle(self.screen, (255, 240, 120), (sx - 4, sy - 4), 2)
                pygame.draw.circle(self.screen, (255, 240, 120), (sx + 4, sy - 4), 2)

            elif e.enemy_type == "brute":
                # Telegraph windup ring
                if e.state == "windup":
                    pygame.draw.circle(self.screen, (255, 210, 70), (sx, sy), r + 8, 2)
                body_rect = pygame.Rect(sx - r, sy - r, r * 2, r * 2)
                pygame.draw.rect(self.screen, COLOR_BRUTE_ARMOR, body_rect, border_radius=6)
                inner_rect = body_rect.inflate(-6, -6)
                pygame.draw.rect(self.screen, col, inner_rect, border_radius=4)
                # Horns
                pygame.draw.polygon(
                    self.screen,
                    (230, 220, 200),
                    [(sx - r + 2, sy - r + 4), (sx - r - 6, sy - r - 6), (sx - r + 8, sy - r)],
                )
                pygame.draw.polygon(
                    self.screen,
                    (230, 220, 200),
                    [(sx + r - 2, sy - r + 4), (sx + r + 6, sy - r - 6), (sx + r - 8, sy - r)],
                )

            elif e.enemy_type == "boss":
                if e.state == "windup":
                    pygame.draw.circle(self.screen, (255, 200, 60), (sx, sy), r + 14, 3)
                if e.boss_phase == 2:
                    aura_r = r + 6 + int(math.sin(e.anim_timer * 3.0) * 4)
                    pygame.draw.circle(self.screen, (255, 90, 40), (sx, sy), aura_r, 2)

                pygame.draw.circle(self.screen, (70, 18, 38), (sx, sy), r)
                pygame.draw.circle(self.screen, col, (sx, sy), r - 4)
                # Golden crown
                crown_pts = [
                    (sx - 16, sy - r + 4),
                    (sx - 12, sy - r - 10),
                    (sx - 5, sy - r - 2),
                    (sx, sy - r - 13),
                    (sx + 5, sy - r - 2),
                    (sx + 12, sy - r - 10),
                    (sx + 16, sy - r + 4),
                ]
                pygame.draw.polygon(self.screen, COLOR_BOSS_CROWN, crown_pts)
                pygame.draw.circle(self.screen, (255, 245, 180), (sx - 8, sy - 4), 4)
                pygame.draw.circle(self.screen, (255, 245, 180), (sx + 8, sy - 4), 4)

            # Individual enemy health bar (non-boss or damaged)
            if not e.is_boss and e.hp < e.max_hp:
                bar_w = r * 2
                bar_h = 5
                bx = sx - r
                by = sy - r - 11
                pygame.draw.rect(self.screen, COLOR_HP_BG, pygame.Rect(bx, by, bar_w, bar_h))
                fill_w = max(1, int(bar_w * (e.hp / e.max_hp)))
                pygame.draw.rect(self.screen, COLOR_HP_BAR, pygame.Rect(bx, by, fill_w, bar_h))

    def _draw_projectiles(
        self, projectiles: List[Projectile], cam_ox: int, cam_oy: int
    ) -> None:
        for proj in projectiles:
            if not proj.alive:
                continue
            sx = int(proj.x - cam_ox)
            sy = int(proj.y - cam_oy)
            pygame.draw.circle(self.screen, proj.color, (sx, sy), int(proj.radius + 2))
            pygame.draw.circle(self.screen, (255, 255, 255), (sx, sy), max(2, int(proj.radius - 2)))

    def _draw_particles(
        self, particles: List[Particle], cam_ox: int, cam_oy: int
    ) -> None:
        for pt in particles:
            sx = int(pt.x - cam_ox)
            sy = int(pt.y - cam_oy)
            ratio = max(0.1, pt.lifetime / pt.max_lifetime)
            rad = max(1, int(pt.size * ratio))
            pygame.draw.circle(self.screen, pt.color, (sx, sy), rad)

    def _draw_floating_texts(
        self, texts: List[FloatingText], cam_ox: int, cam_oy: int
    ) -> None:
        for ft in texts:
            sx = int(ft.x - cam_ox)
            sy = int(ft.y - cam_oy)
            surf = self.font_xs.render(ft.text, True, ft.color)
            shadow = self.font_xs.render(ft.text, True, (0, 0, 0))
            self.screen.blit(shadow, (sx - surf.get_width() // 2 + 1, sy + 1))
            self.screen.blit(surf, (sx - surf.get_width() // 2, sy))

    def _draw_hud(
        self,
        player: Player,
        dungeon: Dungeon,
        enemies: List[Enemy],
        score: int,
        high_score: int,
        banner_text: str,
        banner_timer: float,
    ) -> None:
        panel = pygame.Rect(16, 16, 330, 104)
        pygame.draw.rect(self.screen, COLOR_UI_BG, panel, border_radius=8)
        pygame.draw.rect(self.screen, COLOR_UI_BORDER, panel, 2, border_radius=8)

        # HP Bar
        hp_label = self.font_sm.render(
            f"HP  {player.hp} / {player.max_hp}", True, COLOR_TEXT
        )
        self.screen.blit(hp_label, (30, 26))
        hp_bar_bg = pygame.Rect(30, 48, 220, 18)
        pygame.draw.rect(self.screen, COLOR_HP_BG, hp_bar_bg, border_radius=4)
        hp_ratio = max(0.0, min(1.0, player.hp / player.max_hp))
        hp_bar_fill = pygame.Rect(30, 48, int(220 * hp_ratio), 18)
        pygame.draw.rect(self.screen, COLOR_HP_BAR, hp_bar_fill, border_radius=4)
        pygame.draw.rect(self.screen, COLOR_UI_BORDER, hp_bar_bg, 1, border_radius=4)

        # Dash stamina bar
        dash_ready = 1.0 - min(1.0, player.dash_cooldown / PLAYER_DASH_COOLDOWN)
        dash_label = self.font_xs.render("DASH [SHIFT]", True, COLOR_TEXT_DIM)
        self.screen.blit(dash_label, (30, 74))
        dash_bg = pygame.Rect(125, 77, 125, 10)
        pygame.draw.rect(self.screen, (28, 35, 52), dash_bg, border_radius=3)
        dash_fill = pygame.Rect(125, 77, int(125 * dash_ready), 10)
        pygame.draw.rect(self.screen, COLOR_STAMINA_BAR, dash_fill, border_radius=3)

        # Floor & Score info on right side of panel
        floor_txt = self.font_md.render(
            f"FLOOR {dungeon.floor_num}/{BOSS_FLOOR}", True, COLOR_GOLD
        )
        self.screen.blit(floor_txt, (30, 94))

        score_panel = pygame.Rect(360, 16, 250, 74)
        pygame.draw.rect(self.screen, COLOR_UI_BG, score_panel, border_radius=8)
        pygame.draw.rect(self.screen, COLOR_UI_BORDER, score_panel, 2, border_radius=8)

        score_surf = self.font_md.render(f"SCORE: {score}", True, COLOR_TEXT)
        best_surf = self.font_sm.render(
            f"HIGH SCORE: {max(score, high_score)}", True, COLOR_GOLD
        )
        enemies_left = sum(1 for e in enemies if e.alive)
        rem_surf = self.font_xs.render(
            f"Hostiles Remaining: {enemies_left}", True, COLOR_TEXT_DIM
        )
        self.screen.blit(score_surf, (374, 24))
        self.screen.blit(best_surf, (374, 48))
        self.screen.blit(rem_surf, (374, 68))

        # Boss Health Bar at top center when on Boss Floor
        boss = next((e for e in enemies if e.is_boss and e.alive), None)
        if boss is not None:
            bw = 460
            bh = 22
            bx = (SCREEN_WIDTH - bw) // 2
            by = 24
            boss_bg = pygame.Rect(bx - 10, by - 8, bw + 20, 56)
            pygame.draw.rect(self.screen, COLOR_UI_BG, boss_bg, border_radius=8)
            pygame.draw.rect(self.screen, COLOR_BOSS, boss_bg, 2, border_radius=8)

            title = self.font_sm.render(
                f"{boss.name}  (Phase {boss.boss_phase})", True, COLOR_GOLD
            )
            self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, by - 2))

            bar_rect = pygame.Rect(bx, by + 20, bw, bh)
            pygame.draw.rect(self.screen, COLOR_HP_BG, bar_rect, border_radius=4)
            fill = int(bw * max(0.0, boss.hp / boss.max_hp))
            pygame.draw.rect(
                self.screen,
                COLOR_BOSS,
                pygame.Rect(bx, by + 20, fill, bh),
                border_radius=4,
            )
            pygame.draw.rect(self.screen, COLOR_UI_BORDER, bar_rect, 1, border_radius=4)

        # Minimap in top-right corner
        self._draw_minimap(dungeon, player, enemies)

        # Floor announcement banner
        if banner_timer > 0.0 and banner_text:
            bsurf = self.font_subtitle.render(banner_text, True, COLOR_GOLD)
            bx = SCREEN_WIDTH // 2 - bsurf.get_width() // 2
            by = 105
            bg_rect = pygame.Rect(
                bx - 18, by - 8, bsurf.get_width() + 36, bsurf.get_height() + 16
            )
            pygame.draw.rect(self.screen, COLOR_UI_BG, bg_rect, border_radius=6)
            pygame.draw.rect(self.screen, COLOR_GOLD, bg_rect, 2, border_radius=6)
            self.screen.blit(bsurf, (bx, by))

    def _draw_minimap(
        self, dungeon: Dungeon, player: Player, enemies: List[Enemy]
    ) -> None:
        scale = 3
        mw = dungeon.width * scale
        mh = dungeon.height * scale
        mx = SCREEN_WIDTH - mw - 18
        my = 16

        bg = pygame.Rect(mx - 6, my - 6, mw + 12, mh + 12)
        pygame.draw.rect(self.screen, COLOR_UI_BG, bg, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_UI_BORDER, bg, 2, border_radius=6)

        for ty in range(dungeon.height):
            for tx in range(dungeon.width):
                if not dungeon.explored[ty][tx]:
                    continue
                tile = dungeon.grid[ty][tx]
                if tile == TILE_FLOOR:
                    pygame.draw.rect(
                        self.screen,
                        (62, 60, 88),
                        pygame.Rect(mx + tx * scale, my + ty * scale, scale, scale),
                    )
                elif tile == TILE_STAIRS_DOWN:
                    pygame.draw.rect(
                        self.screen,
                        COLOR_GOLD,
                        pygame.Rect(mx + tx * scale, my + ty * scale, scale + 1, scale + 1),
                    )

        for e in enemies:
            if not e.alive:
                continue
            etx = int(e.x // TILE_SIZE)
            ety = int(e.y // TILE_SIZE)
            if 0 <= etx < dungeon.width and 0 <= ety < dungeon.height and dungeon.explored[ety][etx]:
                pygame.draw.rect(
                    self.screen,
                    (240, 75, 85),
                    pygame.Rect(mx + etx * scale, my + ety * scale, scale, scale),
                )

        ptx = int(player.x // TILE_SIZE)
        pty = int(player.y // TILE_SIZE)
        pygame.draw.rect(
            self.screen,
            COLOR_PLAYER,
            pygame.Rect(mx + ptx * scale - 1, my + pty * scale - 1, scale + 2, scale + 2),
        )

    def render_main_menu(
        self, hs_data: Dict[str, Any], selected_index: int, time_sec: float
    ) -> None:
        self.screen.fill(COLOR_BG)

        # Decorative background dungeon grid lines
        for x in range(0, SCREEN_WIDTH, 64):
            pygame.draw.line(self.screen, (18, 17, 28), (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, 64):
            pygame.draw.line(self.screen, (18, 17, 28), (0, y), (SCREEN_WIDTH, y))

        card = pygame.Rect(SCREEN_WIDTH // 2 - 360, 70, 720, 580)
        pygame.draw.rect(self.screen, COLOR_UI_BG, card, border_radius=14)
        pygame.draw.rect(self.screen, COLOR_UI_BORDER, card, 3, border_radius=14)

        title_surf = self.font_title.render(GAME_TITLE, True, COLOR_GOLD)
        self.screen.blit(
            title_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 105)
        )

        sub_surf = self.font_sm.render(
            "Descend 5 Procedural Floors • Slay 3 Distinct Monster Types • Defeat Malakor on Floor 5",
            True,
            COLOR_TEXT_DIM,
        )
        self.screen.blit(
            sub_surf, (SCREEN_WIDTH // 2 - sub_surf.get_width() // 2, 168)
        )

        # High Score Banner
        stats_box = pygame.Rect(SCREEN_WIDTH // 2 - 250, 210, 500, 88)
        pygame.draw.rect(self.screen, (26, 24, 40), stats_box, border_radius=8)
        pygame.draw.rect(self.screen, COLOR_GOLD, stats_box, 2, border_radius=8)

        hs_txt = self.font_subtitle.render(
            f"HIGH SCORE: {hs_data.get('high_score', 0)}", True, COLOR_GOLD
        )
        meta_txt = self.font_sm.render(
            f"Best Floor: {hs_data.get('best_floor', 1)}   |   Runs: {hs_data.get('total_runs', 0)}   |   Victories: {hs_data.get('victories', 0)}",
            True,
            COLOR_TEXT,
        )
        self.screen.blit(hs_txt, (SCREEN_WIDTH // 2 - hs_txt.get_width() // 2, 224))
        self.screen.blit(meta_txt, (SCREEN_WIDTH // 2 - meta_txt.get_width() // 2, 264))

        # Menu options
        options = ["START NEW EXPEDITION (ENTER / SPACE)", "QUIT GAME (ESC)"]
        for idx, label in enumerate(options):
            is_sel = idx == selected_index
            btn_rect = pygame.Rect(SCREEN_WIDTH // 2 - 230, 325 + idx * 62, 460, 48)
            bg_col = (46, 42, 74) if is_sel else (24, 22, 36)
            border_col = COLOR_GOLD if is_sel else COLOR_UI_BORDER
            pygame.draw.rect(self.screen, bg_col, btn_rect, border_radius=8)
            pygame.draw.rect(self.screen, border_col, btn_rect, 2, border_radius=8)

            txt_col = COLOR_GOLD if is_sel else COLOR_TEXT
            surf = self.font_md.render(label, True, txt_col)
            self.screen.blit(
                surf,
                (
                    SCREEN_WIDTH // 2 - surf.get_width() // 2,
                    btn_rect.centery - surf.get_height() // 2,
                ),
            )

        # Controls & Enemy Guide
        guide_lines = [
            "CONTROLS:  WASD / Arrows = Move   |   Left Click / SPACE / J = Sword Attack   |   SHIFT / Right Click = Dash",
            "ENEMIES:   Venom Slime (Hop Lunge)  •  Void Cultist (Ranged Kiter)  •  Bone Juggernaut (Bull-Rush Charger)",
            "GOAL:      Collect crimson Health Pickups, descend the golden stairs, and vanquish the Boss on Floor 5!",
        ]
        for i, line in enumerate(guide_lines):
            gsurf = self.font_xs.render(line, True, COLOR_TEXT_DIM)
            self.screen.blit(
                gsurf, (SCREEN_WIDTH // 2 - gsurf.get_width() // 2, 475 + i * 26)
            )

    def render_end_screen(
        self,
        victory: bool,
        score: int,
        floor_num: int,
        hs_data: Dict[str, Any],
    ) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 6, 14, 215))
        self.screen.blit(overlay, (0, 0))

        card = pygame.Rect(SCREEN_WIDTH // 2 - 280, 140, 560, 430)
        pygame.draw.rect(self.screen, COLOR_UI_BG, card, border_radius=12)
        border_col = COLOR_GOLD if victory else COLOR_HP_BAR
        pygame.draw.rect(self.screen, border_col, card, 3, border_radius=12)

        heading = "VICTORY! THE OBSIDIAN KING HAS FALLEN" if victory else "YOU HAVE FALLEN IN THE CRYPTS"
        h_surf = self.font_subtitle.render(heading, True, border_col)
        self.screen.blit(
            h_surf, (SCREEN_WIDTH // 2 - h_surf.get_width() // 2, 178)
        )

        if hs_data.get("is_new_high"):
            badge = self.font_md.render("★ NEW HIGH SCORE RECORD! ★", True, COLOR_GOLD)
            self.screen.blit(
                badge, (SCREEN_WIDTH // 2 - badge.get_width() // 2, 225)
            )

        lines = [
            f"Final Score: {score}",
            f"All-Time High Score: {hs_data.get('high_score', score)}",
            f"Floor Reached: {floor_num} / {BOSS_FLOOR}",
            f"Total Expeditions: {hs_data.get('total_runs', 1)}",
        ]
        for i, line in enumerate(lines):
            lsurf = self.font_md.render(line, True, COLOR_TEXT)
            self.screen.blit(
                lsurf, (SCREEN_WIDTH // 2 - lsurf.get_width() // 2, 272 + i * 36)
            )

        prompt = self.font_sm.render(
            "Press ENTER / R to Play Again   |   Press M for Main Menu   |   Press ESC to Quit",
            True,
            COLOR_GOLD,
        )
        self.screen.blit(
            prompt, (SCREEN_WIDTH // 2 - prompt.get_width() // 2, 495)
        )
