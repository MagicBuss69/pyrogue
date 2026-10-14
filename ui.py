"""Obsidian Neon-Noir rendering engine: dynamic torch lighting, procedural sprites, HUD, ability hotbar, relic choice modal, and Steam menus."""

import math
from typing import Any, Dict, List, Optional, Tuple

import pygame

from dungeon import BreakableCrate, Dungeon, FloorDecal, TorchProp
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
)
from settings import (
    ABILITY_LIGHTNING_COOLDOWN,
    ABILITY_NOVA_COOLDOWN,
    ABILITY_WHIRLWIND_COOLDOWN,
    ABILITY_WHIRLWIND_RADIUS,
    ACHIEVEMENTS_CATALOG,
    BOSS_FLOOR,
    COLOR_ABILITY_DASH,
    COLOR_ABILITY_LIGHTNING,
    COLOR_ABILITY_NOVA,
    COLOR_ABILITY_WHIRLWIND,
    COLOR_BG,
    COLOR_BOSS,
    COLOR_BOSS_CROWN,
    COLOR_BRUTE,
    COLOR_BRUTE_ARMOR,
    COLOR_BRUTE_HORN,
    COLOR_CRATE_BAND,
    COLOR_CRATE_WOOD,
    COLOR_CULTIST,
    COLOR_CULTIST_ROBE,
    COLOR_FLOOR_A,
    COLOR_FLOOR_ACCENT,
    COLOR_FLOOR_B,
    COLOR_FLOOR_CRACK,
    COLOR_GOLD,
    COLOR_HP_BAR,
    COLOR_HP_BG,
    COLOR_PICKUP_GLOW,
    COLOR_PICKUP_HP,
    COLOR_PLAYER,
    COLOR_PLAYER_ARMOR,
    COLOR_PLAYER_CAPE,
    COLOR_PLAYER_CORE,
    COLOR_SLIME,
    COLOR_SLIME_CORE,
    COLOR_SLIME_HIGHLIGHT,
    COLOR_STAIRS,
    COLOR_STAIRS_GLOW,
    COLOR_STAIRS_LOCKED,
    COLOR_SWORD,
    COLOR_SWORD_CRIT,
    COLOR_SWORD_TRAIL,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
    COLOR_TORCH_CORE,
    COLOR_TORCH_FLAME,
    COLOR_UI_BG,
    COLOR_UI_BORDER,
    COLOR_UI_HIGHLIGHT,
    COLOR_UI_PANEL,
    COLOR_VOID,
    COLOR_WALL_HIGHLIGHT,
    COLOR_WALL_MORTAR,
    COLOR_WALL_RUNE,
    COLOR_WALL_SIDE,
    COLOR_WALL_TOP,
    COLOR_WALL_TOP_INNER,
    COLOR_XP_BAR,
    GAME_SUBTITLE,
    GAME_TITLE,
    GAME_VERSION,
    PLAYER_ATTACK_ARC,
    PLAYER_ATTACK_DURATION,
    PLAYER_ATTACK_RANGE,
    PLAYER_DASH_COOLDOWN,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TILE_FLOOR,
    TILE_PILLAR,
    TILE_SIZE,
    TILE_STAIRS_DOWN,
    TILE_WALL,
)


class Renderer:
    """Handles Obsidian Neon-Noir 2.5D rendering, additive glow lighting, and Steam UI."""

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        pygame.font.init()
        self.font_title = pygame.font.SysFont("dejavusans", 46, bold=True)
        self.font_subtitle = pygame.font.SysFont("dejavusans", 24, bold=True)
        self.font_md = pygame.font.SysFont("dejavusans", 19, bold=True)
        self.font_sm = pygame.font.SysFont("dejavusans", 15, bold=True)
        self.font_xs = pygame.font.SysFont("dejavusans", 13, bold=True)

        self.cam_x: float = 0.0
        self.cam_y: float = 0.0
        self.shake_timer: float = 0.0
        self.shake_magnitude: float = 0.0

        # Pre-baked radial glow surfaces for fast additive lighting
        self.glow_cache: Dict[Tuple[int, Tuple[int, int, int]], pygame.Surface] = {}
        self.vignette_surface = self._build_vignette()

    def _build_vignette(self) -> pygame.Surface:
        surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        cx = SCREEN_WIDTH * 0.5
        cy = SCREEN_HEIGHT * 0.5
        max_r = math.hypot(cx, cy)
        # Draw subtle dark edge framing rects/rings
        for i in range(6):
            thickness = 28
            inset = i * 18
            alpha = max(0, 75 - i * 13)
            rect = pygame.Rect(
                inset,
                inset,
                SCREEN_WIDTH - inset * 2,
                SCREEN_HEIGHT - inset * 2,
            )
            pygame.draw.rect(surf, (4, 3, 9, alpha), rect, thickness)
        return surf

    def _get_glow_surface(
        self, radius: int, color: Tuple[int, int, int]
    ) -> pygame.Surface:
        key = (radius, color)
        if key in self.glow_cache:
            return self.glow_cache[key]
        size = radius * 2
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        for step in range(5, 0, -1):
            r = int(radius * (step / 5.0))
            alpha = int(28 * (1.0 - (step - 1) / 5.0))
            pygame.draw.circle(
                surf, (color[0], color[1], color[2], alpha), (radius, radius), r
            )
        self.glow_cache[key] = surf
        return surf

    def draw_glow(
        self, x: int, y: int, radius: int, color: Tuple[int, int, int]
    ) -> None:
        if x < -radius or x > SCREEN_WIDTH + radius or y < -radius or y > SCREEN_HEIGHT + radius:
            return
        glow = self._get_glow_surface(radius, color)
        self.screen.blit(
            glow, (x - radius, y - radius), special_flags=pygame.BLEND_RGBA_ADD
        )

    def trigger_shake(self, magnitude: float = 6.5, duration: float = 0.16) -> None:
        self.shake_magnitude = max(self.shake_magnitude, magnitude)
        self.shake_timer = max(self.shake_timer, duration)

    def update_camera(self, target_x: float, target_y: float, dt: float) -> None:
        desired_x = target_x - SCREEN_WIDTH * 0.5
        desired_y = target_y - SCREEN_HEIGHT * 0.5
        lerp = min(1.0, dt * 11.0)
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
            ox += int(math.sin(time_sec * 68.0) * self.shake_magnitude)
            oy += int(math.cos(time_sec * 57.0) * self.shake_magnitude)
        return (ox, oy)

    def render_gameplay(
        self,
        dungeon: Dungeon,
        player: Player,
        enemies: List[Enemy],
        projectiles: List[Projectile],
        pickups: List[HealthPickup],
        particles: List[Particle],
        afterimages: List[DashAfterimage],
        lightning_bolts: List[LightningBoltFX],
        shockwaves: List[ShockwaveRingFX],
        floating_texts: List[FloatingText],
        score: int,
        high_score: int,
        time_sec: float,
        banner_text: str = "",
        banner_timer: float = 0.0,
        toast_text: str = "",
        toast_timer: float = 0.0,
    ) -> None:
        self.screen.fill(COLOR_VOID)
        cam_ox, cam_oy = self.get_camera_offset(time_sec)

        self._draw_dungeon(dungeon, cam_ox, cam_oy, time_sec)
        self._draw_decals(dungeon.decals, cam_ox, cam_oy, time_sec)
        self._draw_crates(dungeon.crates, cam_ox, cam_oy)
        self._draw_torches(dungeon.torches, cam_ox, cam_oy, time_sec)
        self._draw_pickups(pickups, cam_ox, cam_oy, time_sec)
        self._draw_shockwaves(shockwaves, cam_ox, cam_oy)
        self._draw_afterimages(afterimages, cam_ox, cam_oy)
        self._draw_enemies(enemies, cam_ox, cam_oy, time_sec)
        self._draw_player(player, cam_ox, cam_oy, time_sec)
        self._draw_projectiles(projectiles, cam_ox, cam_oy)
        self._draw_lightning_bolts(lightning_bolts, cam_ox, cam_oy)
        self._draw_particles(particles, cam_ox, cam_oy)
        self._draw_floating_texts(floating_texts, cam_ox, cam_oy)

        # Atmospheric vignette
        self.screen.blit(self.vignette_surface, (0, 0))

        # Custom tactical reticle at aim direction & mouse position
        self._draw_aim_reticle(player, cam_ox, cam_oy, time_sec)

        self._draw_hud(
            player=player,
            dungeon=dungeon,
            enemies=enemies,
            score=score,
            high_score=high_score,
            banner_text=banner_text,
            banner_timer=banner_timer,
            toast_text=toast_text,
            toast_timer=toast_timer,
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

                if tile in (TILE_WALL, TILE_PILLAR):
                    # 2.5D Chiseled Obsidian Block
                    pygame.draw.rect(self.screen, COLOR_WALL_SIDE, rect)
                    top_rect = pygame.Rect(sx, sy, TILE_SIZE, TILE_SIZE - 12)
                    pygame.draw.rect(self.screen, COLOR_WALL_TOP, top_rect)
                    bevel_rect = pygame.Rect(sx + 4, sy + 4, TILE_SIZE - 8, TILE_SIZE - 20)
                    pygame.draw.rect(self.screen, COLOR_WALL_TOP_INNER, bevel_rect, border_radius=3)

                    # Brick mortar lines on front face
                    pygame.draw.line(
                        self.screen,
                        COLOR_WALL_MORTAR,
                        (sx, sy + TILE_SIZE - 12),
                        (sx + TILE_SIZE, sy + TILE_SIZE - 12),
                        2,
                    )
                    pygame.draw.line(
                        self.screen,
                        COLOR_WALL_HIGHLIGHT,
                        (sx + 1, sy + 1),
                        (sx + TILE_SIZE - 2, sy + 1),
                        2,
                    )
                    # Glowing cyan/gold rune carved into pillars and select walls
                    if tile == TILE_PILLAR or (tx * 17 + ty * 31) % 19 == 0:
                        rune_col = (
                            COLOR_WALL_RUNE
                            if tile != TILE_PILLAR
                            else (255, 95, 130)
                        )
                        pygame.draw.rect(
                            self.screen,
                            rune_col,
                            pygame.Rect(sx + TILE_SIZE // 2 - 3, sy + 12, 6, 12),
                            1,
                        )
                    pygame.draw.rect(self.screen, COLOR_WALL_MORTAR, rect, 1)

                elif tile in (TILE_FLOOR, TILE_STAIRS_DOWN):
                    base_col = COLOR_FLOOR_A if (tx + ty) % 2 == 0 else COLOR_FLOOR_B
                    pygame.draw.rect(self.screen, base_col, rect)
                    # Subtle stone tile border & bevel
                    pygame.draw.rect(self.screen, COLOR_FLOOR_CRACK, rect, 1)

                    hval = (tx * 13 + ty * 29) % 17
                    if hval == 0:
                        pygame.draw.line(
                            self.screen,
                            COLOR_FLOOR_CRACK,
                            (sx + 8, sy + 10),
                            (sx + 24, sy + 28),
                            2,
                        )
                    elif hval == 3:
                        speck = pygame.Rect(sx + 14, sy + 18, 6, 4)
                        pygame.draw.rect(self.screen, COLOR_FLOOR_ACCENT, speck)

                    # Soft drop shadow below northern wall
                    if ty > 0 and dungeon.grid[ty - 1][tx] in (TILE_WALL, TILE_PILLAR):
                        shadow_rect = pygame.Rect(sx, sy, TILE_SIZE, 9)
                        pygame.draw.rect(self.screen, (11, 10, 18), shadow_rect)

                    if tile == TILE_STAIRS_DOWN:
                        self._draw_stairs(sx, sy, dungeon.stairs_unlocked, time_sec)

    def _draw_stairs(
        self, sx: int, sy: int, unlocked: bool, time_sec: float
    ) -> None:
        cx = sx + TILE_SIZE // 2
        cy = sy + TILE_SIZE // 2
        if unlocked:
            self.draw_glow(cx, cy, 48, COLOR_STAIRS)

        outer = pygame.Rect(sx + 4, sy + 4, TILE_SIZE - 8, TILE_SIZE - 8)
        col = COLOR_STAIRS if unlocked else COLOR_STAIRS_LOCKED
        pygame.draw.rect(self.screen, (10, 9, 18), outer, border_radius=6)
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
            pulse = int(6 + 4 * math.sin(time_sec * 5.5))
            pygame.draw.circle(self.screen, COLOR_STAIRS_GLOW, (cx, cy), pulse, 2)

    def _draw_decals(
        self,
        decals: List[FloorDecal],
        cam_ox: int,
        cam_oy: int,
        time_sec: float,
    ) -> None:
        for d in decals:
            sx = int(d.x - cam_ox)
            sy = int(d.y - cam_oy)
            r = int(d.radius)
            if sx < -r or sx > SCREEN_WIDTH + r or sy < -r or sy > SCREEN_HEIGHT + r:
                continue
            if d.kind == "rune":
                pygame.draw.circle(self.screen, d.color, (sx, sy), r, 2)
                pygame.draw.circle(self.screen, d.color, (sx, sy), int(r * 0.68), 1)
                for i in range(6):
                    ang = time_sec * 0.5 + (i * math.pi / 3.0)
                    px = sx + int(math.cos(ang) * r * 0.82)
                    py = sy + int(math.sin(ang) * r * 0.82)
                    pygame.draw.circle(self.screen, d.color, (px, py), 3)
            elif d.kind == "scorch":
                pygame.draw.circle(self.screen, (14, 12, 20), (sx, sy), r)
                pygame.draw.circle(self.screen, d.color, (sx, sy), r, 2)
            else:
                pygame.draw.circle(self.screen, d.color, (sx, sy), r)
                pygame.draw.circle(self.screen, d.color, (sx + r // 2, sy - r // 3), max(2, r // 2))

    def _draw_crates(
        self, crates: List[BreakableCrate], cam_ox: int, cam_oy: int
    ) -> None:
        for c in crates:
            if c.destroyed:
                continue
            sx = int(c.x - cam_ox)
            sy = int(c.y - cam_oy)
            r = int(c.radius)
            if sx < -32 or sx > SCREEN_WIDTH + 32 or sy < -32 or sy > SCREEN_HEIGHT + 32:
                continue
            pygame.draw.ellipse(
                self.screen, (9, 8, 15), pygame.Rect(sx - r, sy + r - 5, r * 2, 9)
            )
            box = pygame.Rect(sx - r, sy - r, r * 2, r * 2)
            col = (255, 255, 255) if c.hit_flash > 0 else COLOR_CRATE_WOOD
            pygame.draw.rect(self.screen, col, box, border_radius=4)
            pygame.draw.rect(self.screen, COLOR_CRATE_BAND, box, 3, border_radius=4)
            pygame.draw.line(
                self.screen, COLOR_CRATE_BAND, (sx - r + 3, sy), (sx + r - 3, sy), 2
            )
            pygame.draw.circle(self.screen, (95, 215, 255), (sx, sy), 3)

    def _draw_torches(
        self,
        torches: List[TorchProp],
        cam_ox: int,
        cam_oy: int,
        time_sec: float,
    ) -> None:
        for t in torches:
            sx = int(t.x - cam_ox)
            sy = int(t.y - cam_oy)
            if sx < -80 or sx > SCREEN_WIDTH + 80 or sy < -80 or sy > SCREEN_HEIGHT + 80:
                continue
            flicker = math.sin(time_sec * 9.0 + t.phase) * 3.0
            glow_col = (
                (85, 210, 255)
                if t.color_variant == "arcane"
                else (255, 65, 100) if t.color_variant == "crimson" else COLOR_TORCH_FLAME
            )
            self.draw_glow(sx, sy, int(52 + flicker), glow_col)
            # Sconce bracket
            pygame.draw.rect(
                self.screen, (60, 56, 78), pygame.Rect(sx - 3, sy + 2, 6, 8)
            )
            pygame.draw.circle(self.screen, glow_col, (sx, sy - 2), int(6 + flicker * 0.3))
            pygame.draw.circle(self.screen, COLOR_TORCH_CORE, (sx, sy - 2), 3)

    def _draw_pickups(
        self,
        pickups: List[HealthPickup],
        cam_ox: int,
        cam_oy: int,
        time_sec: float,
    ) -> None:
        for p in pickups:
            if p.collected:
                continue
            sx = int(p.x - cam_ox)
            sy = int(p.y - cam_oy + math.sin(p.bob_timer) * 4.5)
            self.draw_glow(sx, sy, 30, COLOR_PICKUP_HP)

            pygame.draw.ellipse(
                self.screen,
                (10, 8, 16),
                pygame.Rect(sx - 11, int(p.y - cam_oy) + 9, 22, 7),
            )
            # Ornate Crimson Flask
            pygame.draw.circle(self.screen, COLOR_PICKUP_GLOW, (sx, sy), int(p.radius + 3), 2)
            pygame.draw.circle(self.screen, COLOR_PICKUP_HP, (sx, sy), int(p.radius))
            pygame.draw.rect(self.screen, (255, 255, 255), pygame.Rect(sx - 2, sy - 6, 4, 12))
            pygame.draw.rect(self.screen, (255, 255, 255), pygame.Rect(sx - 6, sy - 2, 12, 4))

    def _draw_shockwaves(
        self, shockwaves: List[ShockwaveRingFX], cam_ox: int, cam_oy: int
    ) -> None:
        for sw in shockwaves:
            sx = int(sw.x - cam_ox)
            sy = int(sw.y - cam_oy)
            r = max(4, int(sw.radius))
            pygame.draw.circle(self.screen, sw.color, (sx, sy), r, 3)

    def _draw_afterimages(
        self, afterimages: List[DashAfterimage], cam_ox: int, cam_oy: int
    ) -> None:
        for ghost in afterimages:
            sx = int(ghost.x - cam_ox)
            sy = int(ghost.y - cam_oy)
            ratio = max(0.1, ghost.lifetime / ghost.max_lifetime)
            r = max(3, int(ghost.radius * ratio))
            pygame.draw.circle(self.screen, ghost.color, (sx, sy), r, 2)

    def _draw_player(
        self, player: Player, cam_ox: int, cam_oy: int, time_sec: float
    ) -> None:
        sx = int(player.x - cam_ox)
        sy = int(player.y - cam_oy)

        # Ambient hero aura
        self.draw_glow(sx, sy, 44, COLOR_PLAYER)

        # Whirlwind 360 blade storm graphic
        if player.is_whirlwinding:
            self._draw_whirlwind_fx(player, sx, sy, time_sec)

        # Primary 3-step sword slash arc
        if player.is_attacking:
            self._draw_sword_slash(player, sx, sy)

        # Ground shadow
        pygame.draw.ellipse(
            self.screen,
            (8, 7, 14),
            pygame.Rect(sx - 15, sy + 10, 30, 10),
        )

        bob = int(math.sin(player.walk_anim_timer * 2.0) * 2.5) if player.is_moving else 0

        # Flowing crimson-magenta scarf/cape trailing behind facing direction
        cape_dx = -math.cos(player.facing_angle)
        cape_dy = -math.sin(player.facing_angle)
        flutter = math.sin(time_sec * 14.0) * 4.0
        cape_pts = [
            (sx + int(cape_dy * 8), sy + bob),
            (sx - int(cape_dy * 8), sy + bob),
            (
                sx + int(cape_dx * 22 + cape_dy * flutter),
                sy + int(cape_dy * 22 - cape_dx * flutter) + 4,
            ),
        ]
        pygame.draw.polygon(self.screen, COLOR_PLAYER_CAPE, cape_pts)

        # Obsidian shoulder pauldrons
        pygame.draw.circle(
            self.screen, COLOR_PLAYER_ARMOR, (sx, sy + 1 + bob), int(player.radius + 1)
        )

        body_col = (
            (255, 255, 255)
            if player.hurt_flash_timer > 0.0
            else COLOR_ABILITY_DASH if player.is_dashing else COLOR_PLAYER
        )
        pygame.draw.circle(self.screen, body_col, (sx, sy - 2 + bob), int(player.radius - 2))
        pygame.draw.circle(
            self.screen, COLOR_PLAYER_CORE, (sx, sy - 3 + bob), int(player.radius - 7)
        )
        pygame.draw.circle(
            self.screen, (18, 28, 52), (sx, sy - 2 + bob), int(player.radius - 2), 2
        )

        # Glowing Arcane Visor Eyes pointing toward aim direction
        ex = sx + int(math.cos(player.facing_angle) * 6)
        ey = sy - 3 + bob + int(math.sin(player.facing_angle) * 6)
        perp_x = -math.sin(player.facing_angle) * 3.5
        perp_y = math.cos(player.facing_angle) * 3.5
        for side in (-1, 1):
            eye_pos = (int(ex + perp_x * side), int(ey + perp_y * side))
            pygame.draw.circle(self.screen, (15, 22, 42), eye_pos, 3)
            pygame.draw.circle(self.screen, (255, 245, 160), eye_pos, 2)

        # Idle Rune Blade held at player's side when not swinging
        if not player.is_attacking and not player.is_whirlwinding:
            hand_ang = player.facing_angle + 0.65 * player.attack_swing_dir
            hx = sx + int(math.cos(hand_ang) * 14)
            hy = sy + int(math.sin(hand_ang) * 14)
            tip_x = hx + int(math.cos(player.facing_angle - 0.2 * player.attack_swing_dir) * 20)
            tip_y = hy + int(math.sin(player.facing_angle - 0.2 * player.attack_swing_dir) * 20)
            pygame.draw.line(self.screen, COLOR_SWORD_TRAIL, (hx, hy), (tip_x, tip_y), 4)
            pygame.draw.line(self.screen, COLOR_SWORD, (hx, hy), (tip_x, tip_y), 2)

    def _draw_whirlwind_fx(
        self, player: Player, sx: int, sy: int, time_sec: float
    ) -> None:
        r = int(ABILITY_WHIRLWIND_RADIUS)
        pygame.draw.circle(self.screen, COLOR_ABILITY_WHIRLWIND, (sx, sy), r, 3)
        pygame.draw.circle(self.screen, (220, 252, 255), (sx, sy), int(r * 0.72), 2)
        for i in range(4):
            ang = time_sec * 26.0 + i * (math.pi * 0.5)
            bx = sx + int(math.cos(ang) * r)
            by = sy + int(math.sin(ang) * r)
            pygame.draw.line(self.screen, COLOR_SWORD, (sx, sy), (bx, by), 4)

    def _draw_sword_slash(self, player: Player, sx: int, sy: int) -> None:
        progress = 1.0 - (player.attack_timer / PLAYER_ATTACK_DURATION)
        is_finisher = player.combo_step == 2
        reach = PLAYER_ATTACK_RANGE * (1.22 if is_finisher else 1.0)
        trail_col = COLOR_SWORD_CRIT if is_finisher else COLOR_SWORD_TRAIL

        half_arc = PLAYER_ATTACK_ARC * (0.62 if is_finisher else 0.5)
        start_ang = player.attack_angle - half_arc
        end_ang = player.attack_angle + half_arc

        outer_pts: List[Tuple[int, int]] = []
        inner_pts: List[Tuple[int, int]] = []
        steps = 14
        for i in range(steps + 1):
            t = i / steps
            ang = start_ang + (end_ang - start_ang) * t
            outer_pts.append(
                (sx + int(math.cos(ang) * reach), sy + int(math.sin(ang) * reach))
            )
            inner_pts.append(
                (
                    sx + int(math.cos(ang) * (reach * 0.52)),
                    sy + int(math.sin(ang) * (reach * 0.52)),
                )
            )

        crescent_poly = outer_pts + list(reversed(inner_pts))
        if len(crescent_poly) >= 4:
            pygame.draw.polygon(self.screen, trail_col, crescent_poly)
            pygame.draw.polygon(self.screen, COLOR_SWORD, crescent_poly, 2)

        if player.attack_swing_dir > 0:
            blade_ang = start_ang + (end_ang - start_ang) * progress
        else:
            blade_ang = end_ang - (end_ang - start_ang) * progress

        bx = sx + int(math.cos(blade_ang) * (reach + 8))
        by = sy + int(math.sin(blade_ang) * (reach + 8))
        pygame.draw.line(self.screen, COLOR_SWORD, (sx, sy), (bx, by), 5)

    def _draw_enemies(
        self, enemies: List[Enemy], cam_ox: int, cam_oy: int, time_sec: float
    ) -> None:
        for e in enemies:
            if not e.alive:
                continue
            sx = int(e.x - cam_ox)
            sy = int(e.y - cam_oy)
            r = int(e.radius)
            if sx < -80 or sx > SCREEN_WIDTH + 80 or sy < -80 or sy > SCREEN_HEIGHT + 80:
                continue

            self.draw_glow(sx, sy, int(r * 1.9), e.color)

            pygame.draw.ellipse(
                self.screen,
                (8, 7, 14),
                pygame.Rect(sx - r, sy + r - 6, r * 2, 10),
            )

            col = (255, 255, 255) if e.hurt_flash_timer > 0.0 else e.color

            if e.enemy_type == "slime":
                squish = int(math.sin(e.anim_timer * 2.4) * 3.5)
                if e.state == "windup":
                    squish = -5
                rect = pygame.Rect(
                    sx - r - squish // 2,
                    sy - r + squish,
                    (r + squish // 2) * 2,
                    (r - squish // 2) * 2,
                )
                pygame.draw.ellipse(self.screen, COLOR_SLIME_CORE, rect)
                inner = rect.inflate(-5, -5)
                pygame.draw.ellipse(self.screen, col, inner)
                # Bioluminescent nucleus + specular highlight
                pygame.draw.circle(self.screen, COLOR_SLIME_HIGHLIGHT, (sx - 4, sy - 5), 3)
                pygame.draw.circle(self.screen, (18, 35, 22), (sx - 5, sy - 1), 3)
                pygame.draw.circle(self.screen, (18, 35, 22), (sx + 5, sy - 1), 3)

            elif e.enemy_type == "cultist":
                # Floating astral ring beneath cultist
                pygame.draw.ellipse(
                    self.screen,
                    COLOR_CULTIST,
                    pygame.Rect(sx - r - 2, sy + r - 9, (r + 2) * 2, 8),
                    1,
                )
                pts = [
                    (sx, sy - r - 6),
                    (sx - r - 2, sy + r),
                    (sx + r + 2, sy + r),
                ]
                pygame.draw.polygon(self.screen, COLOR_CULTIST_ROBE, pts)
                pygame.draw.polygon(self.screen, col, pts, 2)
                pygame.draw.circle(self.screen, (24, 12, 38), (sx, sy - 3), r - 4)
                pygame.draw.circle(self.screen, (255, 240, 110), (sx - 4, sy - 4), 2)
                pygame.draw.circle(self.screen, (255, 240, 110), (sx + 4, sy - 4), 2)

            elif e.enemy_type == "brute":
                if e.state == "windup":
                    pygame.draw.circle(self.screen, (255, 215, 70), (sx, sy), r + 9, 3)
                    # Draw telegraph charge vector line
                    tx = sx + int(e.charge_dx * 120)
                    ty = sy + int(e.charge_dy * 120)
                    pygame.draw.line(self.screen, (255, 90, 70), (sx, sy), (tx, ty), 2)

                body_rect = pygame.Rect(sx - r, sy - r, r * 2, r * 2)
                pygame.draw.rect(self.screen, COLOR_BRUTE_ARMOR, body_rect, border_radius=6)
                inner_rect = body_rect.inflate(-6, -6)
                pygame.draw.rect(self.screen, col, inner_rect, border_radius=4)
                pygame.draw.polygon(
                    self.screen,
                    COLOR_BRUTE_HORN,
                    [(sx - r + 2, sy - r + 4), (sx - r - 8, sy - r - 8), (sx - r + 9, sy - r)],
                )
                pygame.draw.polygon(
                    self.screen,
                    COLOR_BRUTE_HORN,
                    [(sx + r - 2, sy - r + 4), (sx + r + 8, sy - r - 8), (sx + r - 9, sy - r)],
                )
                pygame.draw.circle(self.screen, (255, 235, 130), (sx - 6, sy - 3), 3)
                pygame.draw.circle(self.screen, (255, 235, 130), (sx + 6, sy - 3), 3)

            elif e.enemy_type == "boss":
                if e.state == "windup":
                    pygame.draw.circle(self.screen, (255, 210, 65), (sx, sy), r + 15, 3)
                if e.boss_phase == 2:
                    aura_r = r + 8 + int(math.sin(e.anim_timer * 3.0) * 5)
                    pygame.draw.circle(self.screen, (255, 100, 40), (sx, sy), aura_r, 3)

                # Orbiting obsidian shards
                for i in range(4):
                    ang = time_sec * 3.2 + i * (math.pi * 0.5)
                    ox = sx + int(math.cos(ang) * (r + 12))
                    oy = sy + int(math.sin(ang) * (r + 12))
                    pygame.draw.circle(self.screen, COLOR_BOSS_CROWN, (ox, oy), 4)

                pygame.draw.circle(self.screen, (64, 14, 34), (sx, sy), r)
                pygame.draw.circle(self.screen, col, (sx, sy), r - 4)
                crown_pts = [
                    (sx - 18, sy - r + 4),
                    (sx - 13, sy - r - 11),
                    (sx - 6, sy - r - 2),
                    (sx, sy - r - 15),
                    (sx + 6, sy - r - 2),
                    (sx + 13, sy - r - 11),
                    (sx + 18, sy - r + 4),
                ]
                pygame.draw.polygon(self.screen, COLOR_BOSS_CROWN, crown_pts)
                pygame.draw.circle(self.screen, (255, 245, 180), (sx - 8, sy - 4), 4)
                pygame.draw.circle(self.screen, (255, 245, 180), (sx + 8, sy - 4), 4)

            if not e.is_boss and e.hp < e.max_hp:
                bar_w = r * 2 + 4
                bar_h = 5
                bx = sx - bar_w // 2
                by = sy - r - 12
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
            self.draw_glow(sx, sy, int(proj.radius * 2.8), proj.color)
            pygame.draw.circle(self.screen, proj.color, (sx, sy), int(proj.radius + 2))
            pygame.draw.circle(
                self.screen, (255, 255, 255), (sx, sy), max(2, int(proj.radius - 2))
            )

    def _draw_lightning_bolts(
        self, bolts: List[LightningBoltFX], cam_ox: int, cam_oy: int
    ) -> None:
        for bolt in bolts:
            if len(bolt.points) < 2:
                continue
            screen_pts = [(int(px - cam_ox), int(py - cam_oy)) for px, py in bolt.points]
            pygame.draw.lines(self.screen, bolt.color, False, screen_pts, 5)
            pygame.draw.lines(self.screen, (255, 255, 255), False, screen_pts, 2)

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
            font = self.font_md if ft.scale > 1.15 else self.font_xs
            surf = font.render(ft.text, True, ft.color)
            shadow = font.render(ft.text, True, (0, 0, 0))
            self.screen.blit(shadow, (sx - surf.get_width() // 2 + 2, sy + 2))
            self.screen.blit(surf, (sx - surf.get_width() // 2, sy))

    def _draw_aim_reticle(
        self, player: Player, cam_ox: int, cam_oy: int, time_sec: float
    ) -> None:
        """Draw directional aim indicator around player so aiming is crystal clear even without a mouse."""
        sx = int(player.x - cam_ox)
        sy = int(player.y - cam_oy)
        dist = 44
        rx = sx + int(math.cos(player.facing_angle) * dist)
        ry = sy + int(math.sin(player.facing_angle) * dist)
        perp_x = -math.sin(player.facing_angle) * 5
        perp_y = math.cos(player.facing_angle) * 5
        tip_x = sx + int(math.cos(player.facing_angle) * (dist + 9))
        tip_y = sy + int(math.sin(player.facing_angle) * (dist + 9))
        chevron = [
            (tip_x, tip_y),
            (int(rx + perp_x), int(ry + perp_y)),
            (int(rx - perp_x), int(ry - perp_y)),
        ]
        pygame.draw.polygon(self.screen, COLOR_UI_HIGHLIGHT, chevron)

    def _draw_hud(
        self,
        player: Player,
        dungeon: Dungeon,
        enemies: List[Enemy],
        score: int,
        high_score: int,
        banner_text: str,
        banner_timer: float,
        toast_text: str,
        toast_timer: float,
    ) -> None:
        # Top-Left Status Panel
        panel = pygame.Rect(16, 16, 350, 114)
        pygame.draw.rect(self.screen, COLOR_UI_BG, panel, border_radius=10)
        pygame.draw.rect(self.screen, COLOR_UI_BORDER, panel, 2, border_radius=10)

        hp_label = self.font_sm.render(
            f"HP  {player.hp} / {player.max_hp}", True, COLOR_TEXT
        )
        lvl_label = self.font_sm.render(f"LVL {player.level}", True, COLOR_GOLD)
        self.screen.blit(hp_label, (30, 24))
        self.screen.blit(lvl_label, (290, 24))

        hp_bar_bg = pygame.Rect(30, 46, 320, 16)
        pygame.draw.rect(self.screen, COLOR_HP_BG, hp_bar_bg, border_radius=4)
        hp_ratio = max(0.0, min(1.0, player.hp / player.max_hp))
        pygame.draw.rect(
            self.screen,
            COLOR_HP_BAR,
            pygame.Rect(30, 46, int(320 * hp_ratio), 16),
            border_radius=4,
        )
        pygame.draw.rect(self.screen, COLOR_UI_BORDER, hp_bar_bg, 1, border_radius=4)

        # XP Bar
        xp_bg = pygame.Rect(30, 68, 320, 9)
        pygame.draw.rect(self.screen, (20, 32, 34), xp_bg, border_radius=3)
        xp_ratio = max(0.0, min(1.0, player.xp / max(1, player.xp_to_next)))
        pygame.draw.rect(
            self.screen,
            COLOR_XP_BAR,
            pygame.Rect(30, 68, int(320 * xp_ratio), 9),
            border_radius=3,
        )

        floor_txt = self.font_sm.render(
            f"FLOOR {dungeon.floor_num}/{BOSS_FLOOR}", True, COLOR_GOLD
        )
        aim_txt = self.font_xs.render(
            f"AIM: {player.aim_mode} (Arrows/WASD/Mouse)", True, COLOR_TEXT_DIM
        )
        self.screen.blit(floor_txt, (30, 86))
        self.screen.blit(aim_txt, (145, 88))

        # Score & Hostiles Panel
        score_panel = pygame.Rect(378, 16, 240, 78)
        pygame.draw.rect(self.screen, COLOR_UI_BG, score_panel, border_radius=10)
        pygame.draw.rect(self.screen, COLOR_UI_BORDER, score_panel, 2, border_radius=10)

        score_surf = self.font_md.render(f"SCORE: {score}", True, COLOR_TEXT)
        best_surf = self.font_xs.render(
            f"BEST: {max(score, high_score)}", True, COLOR_GOLD
        )
        enemies_left = sum(1 for e in enemies if e.alive)
        rem_surf = self.font_xs.render(
            f"Hostiles Alive: {enemies_left}", True, COLOR_TEXT_DIM
        )
        self.screen.blit(score_surf, (392, 23))
        self.screen.blit(best_surf, (392, 48))
        self.screen.blit(rem_surf, (392, 67))

        # Bottom-Center Steam-Style Ability Hotbar
        self._draw_ability_hotbar(player)

        # Boss Health Bar at top center when on Floor 5
        boss = next((e for e in enemies if e.is_boss and e.alive), None)
        if boss is not None:
            bw = 440
            bh = 20
            bx = (SCREEN_WIDTH - bw) // 2 + 40
            by = 22
            boss_bg = pygame.Rect(bx - 12, by - 6, bw + 24, 54)
            pygame.draw.rect(self.screen, COLOR_UI_BG, boss_bg, border_radius=8)
            pygame.draw.rect(self.screen, COLOR_BOSS, boss_bg, 2, border_radius=8)

            title = self.font_sm.render(
                f"{boss.name}  (Phase {boss.boss_phase})", True, COLOR_GOLD
            )
            self.screen.blit(title, (bx + bw // 2 - title.get_width() // 2, by - 1))

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

        self._draw_minimap(dungeon, player, enemies)

        if banner_timer > 0.0 and banner_text:
            bsurf = self.font_subtitle.render(banner_text, True, COLOR_GOLD)
            bx = SCREEN_WIDTH // 2 - bsurf.get_width() // 2
            by = 108
            bg_rect = pygame.Rect(
                bx - 18, by - 8, bsurf.get_width() + 36, bsurf.get_height() + 16
            )
            pygame.draw.rect(self.screen, COLOR_UI_BG, bg_rect, border_radius=8)
            pygame.draw.rect(self.screen, COLOR_GOLD, bg_rect, 2, border_radius=8)
            self.screen.blit(bsurf, (bx, by))

        # Steam-style Achievement Popup Toast in bottom-right
        if toast_timer > 0.0 and toast_text:
            tsurf = self.font_sm.render(toast_text, True, COLOR_GOLD)
            sub = self.font_xs.render("STEAM ACHIEVEMENT UNLOCKED", True, COLOR_UI_HIGHLIGHT)
            tw = max(tsurf.get_width(), sub.get_width()) + 34
            tx = SCREEN_WIDTH - tw - 20
            ty = SCREEN_HEIGHT - 78
            trect = pygame.Rect(tx, ty, tw, 58)
            pygame.draw.rect(self.screen, COLOR_UI_PANEL, trect, border_radius=8)
            pygame.draw.rect(self.screen, COLOR_GOLD, trect, 2, border_radius=8)
            self.screen.blit(sub, (tx + 16, ty + 9))
            self.screen.blit(tsurf, (tx + 16, ty + 29))

    def _draw_ability_hotbar(self, player: Player) -> None:
        slots = [
            ("ATK", "J / LMB", 0.0, 1.0, COLOR_SWORD_TRAIL),
            (
                "WHIRLWIND",
                "Q / 1",
                player.whirlwind_cooldown,
                ABILITY_WHIRLWIND_COOLDOWN * player.cooldown_Multiplier,
                COLOR_ABILITY_WHIRLWIND,
            ),
            (
                "NOVA",
                "E / 2",
                player.nova_cooldown,
                ABILITY_NOVA_COOLDOWN * player.cooldown_Multiplier,
                COLOR_ABILITY_NOVA,
            ),
            (
                "LIGHTNING",
                "R / 3",
                player.lightning_cooldown,
                ABILITY_LIGHTNING_COOLDOWN * player.cooldown_Multiplier,
                COLOR_ABILITY_LIGHTNING,
            ),
            (
                "DASH",
                "SHIFT/K",
                player.dash_cooldown,
                PLAYER_DASH_COOLDOWN * player.cooldown_Multiplier,
                COLOR_ABILITY_DASH,
            ),
        ]

        slot_w = 104
        slot_h = 56
        gap = 10
        total_w = len(slots) * slot_w + (len(slots) - 1) * gap
        start_x = (SCREEN_WIDTH - total_w) // 2
        y = SCREEN_HEIGHT - slot_h - 14

        for i, (name, keybind, cd, max_cd, col) in enumerate(slots):
            sx = start_x + i * (slot_w + gap)
            rect = pygame.Rect(sx, y, slot_w, slot_h)
            pygame.draw.rect(self.screen, COLOR_UI_BG, rect, border_radius=8)

            ready = cd <= 0.01
            border_c = col if ready else (52, 48, 74)
            pygame.draw.rect(self.screen, border_c, rect, 2, border_radius=8)

            if not ready and max_cd > 0:
                ratio = min(1.0, cd / max_cd)
                fill_h = int(slot_h * (1.0 - ratio))
                fill_rect = pygame.Rect(sx + 2, y + slot_h - fill_h, slot_w - 4, fill_h)
                pygame.draw.rect(self.screen, (28, 26, 46), fill_rect, border_radius=6)

            name_surf = self.font_xs.render(name, True, col if ready else COLOR_TEXT_DIM)
            self.screen.blit(
                name_surf, (sx + slot_w // 2 - name_surf.get_width() // 2, y + 8)
            )

            if ready:
                kb_surf = self.font_xs.render(f"[{keybind}]", True, COLOR_TEXT)
            else:
                kb_surf = self.font_xs.render(f"{cd:.1f}s", True, COLOR_GOLD)
            self.screen.blit(
                kb_surf, (sx + slot_w // 2 - kb_surf.get_width() // 2, y + 30)
            )

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
                        (58, 55, 86),
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
                    (250, 70, 90),
                    pygame.Rect(mx + etx * scale, my + ety * scale, scale, scale),
                )

        ptx = int(player.x // TILE_SIZE)
        pty = int(player.y // TILE_SIZE)
        pygame.draw.rect(
            self.screen,
            COLOR_PLAYER,
            pygame.Rect(mx + ptx * scale - 1, my + pty * scale - 1, scale + 2, scale + 2),
        )

    def render_relic_selection(
        self,
        choices: List[Dict[str, Any]],
        selected_idx: int,
        player_level: int,
    ) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 5, 12, 210))
        self.screen.blit(overlay, (0, 0))

        title = self.font_subtitle.render(
            f"LEVEL {player_level} REACHED! — CHOOSE AN OBSIDIAN RELIC",
            True,
            COLOR_GOLD,
        )
        sub = self.font_sm.render(
            "Use UP/DOWN or 1/2/3 and press ENTER/SPACE to claim your power",
            True,
            COLOR_TEXT_DIM,
        )
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 130))
        self.screen.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, 168))

        for i, relic in enumerate(choices):
            is_sel = i == selected_idx
            card = pygame.Rect(SCREEN_WIDTH // 2 - 290, 220 + i * 112, 580, 94)
            bg_c = (38, 34, 64) if is_sel else COLOR_UI_PANEL
            border_c = relic["color"] if is_sel else COLOR_UI_BORDER
            pygame.draw.rect(self.screen, bg_c, card, border_radius=10)
            pygame.draw.rect(self.screen, border_c, card, 3 if is_sel else 2, border_radius=10)

            head = self.font_md.render(
                f"[{i + 1}]  {relic['name']}", True, relic["color"]
            )
            desc = self.font_sm.render(relic["desc"], True, COLOR_TEXT)
            self.screen.blit(head, (card.x + 22, card.y + 18))
            self.screen.blit(desc, (card.x + 22, card.y + 52))

    def render_pause_overlay(self, selected_idx: int) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 5, 12, 200))
        self.screen.blit(overlay, (0, 0))

        card = pygame.Rect(SCREEN_WIDTH // 2 - 220, 190, 440, 320)
        pygame.draw.rect(self.screen, COLOR_UI_BG, card, border_radius=12)
        pygame.draw.rect(self.screen, COLOR_UI_BORDER, card, 3, border_radius=12)

        t_surf = self.font_subtitle.render("EXPEDITION PAUSED", True, COLOR_GOLD)
        self.screen.blit(t_surf, (SCREEN_WIDTH // 2 - t_surf.get_width() // 2, 218))

        opts = [
            "RESUME EXPEDITION (ESC / ENTER)",
            "RESTART FLOOR 1 (R)",
            "RETURN TO MAIN MENU (M)",
            "QUIT TO DESKTOP",
        ]
        for i, label in enumerate(opts):
            is_sel = i == selected_idx
            btn = pygame.Rect(SCREEN_WIDTH // 2 - 180, 275 + i * 50, 360, 40)
            pygame.draw.rect(
                self.screen,
                (42, 38, 70) if is_sel else COLOR_UI_PANEL,
                btn,
                border_radius=7,
            )
            pygame.draw.rect(
                self.screen,
                COLOR_GOLD if is_sel else COLOR_UI_BORDER,
                btn,
                2,
                border_radius=7,
            )
            lsurf = self.font_sm.render(
                label, True, COLOR_GOLD if is_sel else COLOR_TEXT
            )
            self.screen.blit(
                lsurf,
                (SCREEN_WIDTH // 2 - lsurf.get_width() // 2, btn.centery - lsurf.get_height() // 2),
            )

    def render_main_menu(
        self, hs_data: Dict[str, Any], selected_index: int, time_sec: float
    ) -> None:
        self.screen.fill(COLOR_BG)

        # Animated perspective grid & floating arcane embers
        for x in range(0, SCREEN_WIDTH, 64):
            pygame.draw.line(self.screen, (16, 14, 28), (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, 64):
            pygame.draw.line(self.screen, (16, 14, 28), (0, y), (SCREEN_WIDTH, y))

        for i in range(24):
            ex = int((i * 173 + time_sec * (22 + (i % 5) * 8)) % SCREEN_WIDTH)
            ey = int((SCREEN_HEIGHT - (i * 97 + time_sec * (35 + (i % 4) * 12)) % SCREEN_HEIGHT))
            col = COLOR_PLAYER if i % 2 == 0 else COLOR_CULTIST
            pygame.draw.circle(self.screen, col, (ex, ey), 2 + (i % 2))

        card = pygame.Rect(SCREEN_WIDTH // 2 - 440, 38, 880, 644)
        pygame.draw.rect(self.screen, COLOR_UI_BG, card, border_radius=16)
        pygame.draw.rect(self.screen, COLOR_UI_BORDER, card, 3, border_radius=16)

        title_surf = self.font_title.render(GAME_TITLE, True, COLOR_GOLD)
        self.screen.blit(
            title_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 62)
        )
        sub_surf = self.font_sm.render(
            f"{GAME_SUBTITLE}  •  {GAME_VERSION}", True, COLOR_UI_HIGHLIGHT
        )
        self.screen.blit(
            sub_surf, (SCREEN_WIDTH // 2 - sub_surf.get_width() // 2, 118)
        )

        # Career & High Score Banner
        stats_box = pygame.Rect(SCREEN_WIDTH // 2 - 380, 152, 760, 74)
        pygame.draw.rect(self.screen, COLOR_UI_PANEL, stats_box, border_radius=10)
        pygame.draw.rect(self.screen, COLOR_GOLD, stats_box, 2, border_radius=10)

        hs_txt = self.font_subtitle.render(
            f"HIGH SCORE: {hs_data.get('high_score', 0)}", True, COLOR_GOLD
        )
        unlocked_count = len(hs_data.get("achievements", []))
        meta_txt = self.font_xs.render(
            f"Best Floor: {hs_data.get('best_floor', 1)}/5   |   Expeditions: {hs_data.get('total_runs', 0)}   |   Victories: {hs_data.get('victories', 0)}   |   Kills: {hs_data.get('total_kills', 0)}   |   Achievements: {unlocked_count}/{len(ACHIEVEMENTS_CATALOG)}",
            True,
            COLOR_TEXT,
        )
        self.screen.blit(hs_txt, (SCREEN_WIDTH // 2 - hs_txt.get_width() // 2, 162))
        self.screen.blit(meta_txt, (SCREEN_WIDTH // 2 - meta_txt.get_width() // 2, 198))

        options = [
            "START NEW EXPEDITION (ENTER / SPACE)",
            "QUIT TO DESKTOP (ESC)",
        ]
        for idx, label in enumerate(options):
            is_sel = idx == selected_index
            btn_rect = pygame.Rect(SCREEN_WIDTH // 2 - 240, 244 + idx * 54, 480, 44)
            bg_col = (44, 38, 76) if is_sel else COLOR_UI_PANEL
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

        # Controls & Abilities Showcase Box (Mouse-free friendly!)
        info_box = pygame.Rect(SCREEN_WIDTH // 2 - 390, 362, 780, 175)
        pygame.draw.rect(self.screen, COLOR_UI_PANEL, info_box, border_radius=10)
        pygame.draw.rect(self.screen, COLOR_UI_BORDER, info_box, 2, border_radius=10)

        guide_lines = [
            "NO MOUSE REQUIRED — FULL KEYBOARD, TWIN-STICK & MOUSE SUPPORT:",
            "• MOVE: WASD   |   AIM: Arrow Keys, Auto-Target Nearest Enemy, or Mouse",
            "• SWORD COMBO: [J] / [SPACE] / Left-Click (3-Hit Arcane Crescent Combo + Projectile Deflect)",
            "• [Q] or [1]: Whirlwind Cleave (360° Blade Storm)   |   [E] or [2]: Eldritch Nova (8 Piercing Lances)",
            "• [R] or [3]: Chain Lightning (Arcs to 4 Enemies)    |   [SHIFT] or [K]: Phantom Dash (Invulnerable)",
        ]
        for i, line in enumerate(guide_lines):
            col = COLOR_UI_HIGHLIGHT if i == 0 else COLOR_TEXT
            gsurf = self.font_xs.render(line, True, col)
            self.screen.blit(gsurf, (info_box.x + 20, info_box.y + 14 + i * 30))

        # Achievements Strip at bottom of Main Menu
        ach_unlocked = set(hs_data.get("achievements", []))
        ach_y = 552
        ach_title = self.font_xs.render("STEAM ACHIEVEMENTS:", True, COLOR_GOLD)
        self.screen.blit(ach_title, (SCREEN_WIDTH // 2 - 390, ach_y))
        for i, ach in enumerate(ACHIEVEMENTS_CATALOG):
            is_un = ach["id"] in ach_unlocked
            ax = SCREEN_WIDTH // 2 - 390 + i * 158
            ay = ach_y + 22
            arect = pygame.Rect(ax, ay, 150, 48)
            pygame.draw.rect(
                self.screen,
                (32, 44, 42) if is_un else (20, 18, 30),
                arect,
                border_radius=6,
            )
            pygame.draw.rect(
                self.screen,
                COLOR_XP_BAR if is_un else (55, 50, 75),
                arect,
                2 if is_un else 1,
                border_radius=6,
            )
            asurf = self.font_xs.render(
                ach["name"], True, COLOR_XP_BAR if is_un else COLOR_TEXT_DIM
            )
            status_surf = self.font_xs.render(
                "UNLOCKED" if is_un else "LOCKED",
                True,
                COLOR_GOLD if is_un else (95, 90, 120),
            )
            self.screen.blit(asurf, (ax + 8, ay + 7))
            self.screen.blit(status_surf, (ax + 8, ay + 26))

    def render_end_screen(
        self,
        victory: bool,
        score: int,
        floor_num: int,
        player_level: int,
        kills: int,
        hs_data: Dict[str, Any],
    ) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 6, 14, 220))
        self.screen.blit(overlay, (0, 0))

        card = pygame.Rect(SCREEN_WIDTH // 2 - 300, 120, 600, 470)
        pygame.draw.rect(self.screen, COLOR_UI_BG, card, border_radius=14)
        border_col = COLOR_GOLD if victory else COLOR_HP_BAR
        pygame.draw.rect(self.screen, border_col, card, 3, border_radius=14)

        heading = (
            "VICTORY! THE OBSIDIAN KING HAS FALLEN"
            if victory
            else "YOU HAVE FALLEN IN THE CRYPTS"
        )
        h_surf = self.font_subtitle.render(heading, True, border_col)
        self.screen.blit(
            h_surf, (SCREEN_WIDTH // 2 - h_surf.get_width() // 2, 155)
        )

        if hs_data.get("is_new_high"):
            badge = self.font_md.render("★ NEW HIGH SCORE RECORD! ★", True, COLOR_GOLD)
            self.screen.blit(
                badge, (SCREEN_WIDTH // 2 - badge.get_width() // 2, 200)
            )

        lines = [
            f"Final Score: {score}",
            f"All-Time High Score: {hs_data.get('high_score', score)}",
            f"Floor Reached: {floor_num} / {BOSS_FLOOR}   •   Hero Level: {player_level}",
            f"Monsters Slain This Run: {kills}",
            f"Total Career Expeditions: {hs_data.get('total_runs', 1)}",
        ]
        for i, line in enumerate(lines):
            lsurf = self.font_md.render(line, True, COLOR_TEXT)
            self.screen.blit(
                lsurf, (SCREEN_WIDTH // 2 - lsurf.get_width() // 2, 248 + i * 36)
            )

        prompt = self.font_sm.render(
            "Press ENTER / R to Play Again   |   Press M for Main Menu   |   Press ESC to Quit",
            True,
            COLOR_GOLD,
        )
        self.screen.blit(
            prompt, (SCREEN_WIDTH // 2 - prompt.get_width() // 2, 520)
        )
