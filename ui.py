"""AAA 2.5D Biome & Boss Rendering Engine: 5 Distinct Biome Architectural Palettes, 5 Hand-Crafted Boss Sprites, Shrines, Dynamic Lighting, Codex, and Steam UI."""

import math
from typing import Any, Dict, List, Optional, Tuple

import pygame

from dungeon import ArcaneShrine, BreakableCrate, Dungeon, FloorDecal, TorchProp
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
    BIOME_THEMES,
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
    COLOR_GOLD,
    COLOR_HP_BAR,
    COLOR_HP_BG,
    COLOR_PICKUP_GLOW,
    COLOR_PICKUP_HP,
    COLOR_PLAYER,
    COLOR_PLAYER_ARMOR,
    COLOR_PLAYER_CAPE,
    COLOR_PLAYER_CORE,
    COLOR_SHRINE,
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
    COLOR_UI_BG,
    COLOR_UI_BORDER,
    COLOR_UI_HIGHLIGHT,
    COLOR_UI_PANEL,
    COLOR_VOID,
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
    get_biome_theme,
)


class Renderer:
    """Handles 5-Biome 2.5D architectural rendering, 5 Boss sprites, additive lighting, and Steam UI."""

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        pygame.font.init()
        self.font_title = pygame.font.SysFont("dejavusans", 44, bold=True)
        self.font_subtitle = pygame.font.SysFont("dejavusans", 23, bold=True)
        self.font_md = pygame.font.SysFont("dejavusans", 18, bold=True)
        self.font_sm = pygame.font.SysFont("dejavusans", 14, bold=True)
        self.font_xs = pygame.font.SysFont("dejavusans", 12, bold=True)

        self.cam_x: float = 0.0
        self.cam_y: float = 0.0
        self.shake_timer: float = 0.0
        self.shake_magnitude: float = 0.0

        self.glow_cache: Dict[Tuple[int, Tuple[int, int, int]], pygame.Surface] = {}
        self.vignette_surface = self._build_vignette()

    def _build_vignette(self) -> pygame.Surface:
        surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for i in range(6):
            thickness = 28
            inset = i * 18
            alpha = max(0, 78 - i * 13)
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
            alpha = int(30 * (1.0 - (step - 1) / 5.0))
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
        music_on: bool = True,
    ) -> None:
        biome = get_biome_theme(dungeon.floor_num)
        self.screen.fill(COLOR_VOID)
        cam_ox, cam_oy = self.get_camera_offset(time_sec)

        self._draw_dungeon(dungeon, biome, cam_ox, cam_oy, time_sec)
        self._draw_decals(dungeon.decals, cam_ox, cam_oy, time_sec)
        self._draw_shrines(dungeon.shrines, cam_ox, cam_oy, time_sec)
        self._draw_crates(dungeon.crates, cam_ox, cam_oy)
        self._draw_torches(dungeon.torches, biome, cam_ox, cam_oy, time_sec)
        self._draw_pickups(pickups, cam_ox, cam_oy, time_sec)
        self._draw_shockwaves(shockwaves, cam_ox, cam_oy)
        self._draw_afterimages(afterimages, cam_ox, cam_oy)
        self._draw_enemies(enemies, cam_ox, cam_oy, time_sec)
        self._draw_player(player, cam_ox, cam_oy, time_sec)
        self._draw_projectiles(projectiles, cam_ox, cam_oy)
        self._draw_lightning_bolts(lightning_bolts, cam_ox, cam_oy)
        self._draw_particles(particles, cam_ox, cam_oy)
        self._draw_biome_ambient_motes(biome, time_sec)
        self._draw_floating_texts(floating_texts, cam_ox, cam_oy)

        self.screen.blit(self.vignette_surface, (0, 0))
        self._draw_aim_reticle(player, enemies, cam_ox, cam_oy, time_sec)

        self._draw_hud(
            player=player,
            dungeon=dungeon,
            biome=biome,
            enemies=enemies,
            score=score,
            high_score=high_score,
            banner_text=banner_text,
            banner_timer=banner_timer,
            toast_text=toast_text,
            toast_timer=toast_timer,
            music_on=music_on,
        )

    def _draw_biome_ambient_motes(
        self, biome: Dict[str, Any], time_sec: float
    ) -> None:
        """Render floating biome-specific atmospheric spores, embers, or frost crystals."""
        mote_col = biome["ambient_particle"]
        for i in range(18):
            mx = int((i * 197 + time_sec * (16 + (i % 4) * 6)) % SCREEN_WIDTH)
            my = int(
                (SCREEN_HEIGHT - (i * 113 + time_sec * (22 + (i % 5) * 7)) % SCREEN_HEIGHT)
            )
            sz = 2 if i % 3 != 0 else 3
            pygame.draw.circle(self.screen, mote_col, (mx, my), sz)

    def _draw_dungeon(
        self,
        dungeon: Dungeon,
        biome: Dict[str, Any],
        cam_ox: int,
        cam_oy: int,
        time_sec: float,
    ) -> None:
        start_tx = max(0, cam_ox // TILE_SIZE - 1)
        end_tx = min(dungeon.width, (cam_ox + SCREEN_WIDTH) // TILE_SIZE + 2)
        start_ty = max(0, cam_oy // TILE_SIZE - 1)
        end_ty = min(dungeon.height, (cam_oy + SCREEN_HEIGHT) // TILE_SIZE + 2)

        w_top = biome["wall_top"]
        w_inner = biome["wall_top_inner"]
        w_side = biome["wall_side"]
        w_mortar = biome["wall_mortar"]
        w_hi = biome["wall_highlight"]
        w_rune = biome["wall_rune"]
        fl_a = biome["floor_a"]
        fl_b = biome["floor_b"]
        fl_crack = biome["floor_crack"]
        fl_acc = biome["floor_accent"]

        for ty in range(start_ty, end_ty):
            for tx in range(start_tx, end_tx):
                tile = dungeon.grid[ty][tx]
                if tile == 0:
                    continue

                sx = tx * TILE_SIZE - cam_ox
                sy = ty * TILE_SIZE - cam_oy
                rect = pygame.Rect(sx, sy, TILE_SIZE, TILE_SIZE)

                if tile in (TILE_WALL, TILE_PILLAR):
                    # 2.5D Chiseled Biome Stone Block
                    pygame.draw.rect(self.screen, w_side, rect)
                    top_rect = pygame.Rect(sx, sy, TILE_SIZE, TILE_SIZE - 13)
                    pygame.draw.rect(self.screen, w_top, top_rect)
                    bevel_rect = pygame.Rect(sx + 4, sy + 4, TILE_SIZE - 8, TILE_SIZE - 21)
                    pygame.draw.rect(self.screen, w_inner, bevel_rect, border_radius=4)

                    # Brick courses on front face
                    pygame.draw.line(
                        self.screen,
                        w_mortar,
                        (sx, sy + TILE_SIZE - 13),
                        (sx + TILE_SIZE, sy + TILE_SIZE - 13),
                        2,
                    )
                    pygame.draw.line(
                        self.screen,
                        w_mortar,
                        (sx + TILE_SIZE // 2, sy + TILE_SIZE - 13),
                        (sx + TILE_SIZE // 2, sy + TILE_SIZE),
                        2,
                    )
                    # Specular top rim highlight
                    pygame.draw.line(
                        self.screen,
                        w_hi,
                        (sx + 2, sy + 1),
                        (sx + TILE_SIZE - 3, sy + 1),
                        2,
                    )
                    # Glowing biome rune carved into pillars and select walls
                    if tile == TILE_PILLAR or (tx * 17 + ty * 31) % 15 == 0:
                        pygame.draw.rect(
                            self.screen,
                            w_rune,
                            pygame.Rect(sx + TILE_SIZE // 2 - 4, sy + 10, 8, 14),
                            2,
                        )
                    pygame.draw.rect(self.screen, w_mortar, rect, 1)

                elif tile in (TILE_FLOOR, TILE_STAIRS_DOWN):
                    base_col = fl_a if (tx + ty) % 2 == 0 else fl_b
                    pygame.draw.rect(self.screen, base_col, rect)
                    pygame.draw.rect(self.screen, fl_crack, rect, 1)

                    # Ornate inlaid stone tile inner trim
                    hval = (tx * 13 + ty * 29) % 19
                    if hval == 0:
                        pygame.draw.line(
                            self.screen,
                            fl_crack,
                            (sx + 8, sy + 10),
                            (sx + 26, sy + 28),
                            2,
                        )
                    elif hval in (3, 7):
                        speck = pygame.Rect(sx + 10, sy + 10, TILE_SIZE - 20, TILE_SIZE - 20)
                        pygame.draw.rect(self.screen, fl_acc, speck, 1, border_radius=3)
                    elif hval == 11:
                        pygame.draw.circle(
                            self.screen, fl_acc, (sx + TILE_SIZE // 2, sy + TILE_SIZE // 2), 3
                        )

                    # Drop shadow cast by northern wall
                    if ty > 0 and dungeon.grid[ty - 1][tx] in (TILE_WALL, TILE_PILLAR):
                        shadow_rect = pygame.Rect(sx, sy, TILE_SIZE, 10)
                        pygame.draw.rect(self.screen, w_mortar, shadow_rect)

                    if tile == TILE_STAIRS_DOWN:
                        self._draw_stairs(sx, sy, dungeon.stairs_unlocked, time_sec)

    def _draw_stairs(
        self, sx: int, sy: int, unlocked: bool, time_sec: float
    ) -> None:
        cx = sx + TILE_SIZE // 2
        cy = sy + TILE_SIZE // 2
        col = COLOR_STAIRS if unlocked else COLOR_STAIRS_LOCKED
        self.draw_glow(cx, cy, 50 if unlocked else 32, col)

        outer = pygame.Rect(sx + 4, sy + 4, TILE_SIZE - 8, TILE_SIZE - 8)
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
        else:
            # Padlock cross bars indicating Boss must be defeated first
            pygame.draw.line(
                self.screen, (255, 80, 110), (sx + 8, sy + 8), (sx + TILE_SIZE - 8, sy + TILE_SIZE - 8), 3
            )
            pygame.draw.line(
                self.screen, (255, 80, 110), (sx + TILE_SIZE - 8, sy + 8), (sx + 8, sy + TILE_SIZE - 8), 3
            )

    def _draw_shrines(
        self,
        shrines: List[ArcaneShrine],
        cam_ox: int,
        cam_oy: int,
        time_sec: float,
    ) -> None:
        for s in shrines:
            sx = int(s.x - cam_ox)
            sy = int(s.y - cam_oy)
            if sx < -60 or sx > SCREEN_WIDTH + 60 or sy < -60 or sy > SCREEN_HEIGHT + 60:
                continue

            col = (
                (95, 250, 145)
                if s.shrine_type == "vitality"
                else (255, 110, 85)
                if s.shrine_type == "fury"
                else COLOR_SHRINE
            )
            if not s.used:
                self.draw_glow(sx, sy, 52, col)

            # Pedestal base
            base_rect = pygame.Rect(sx - 18, sy - 6, 36, 22)
            pygame.draw.rect(self.screen, (36, 34, 54), base_rect, border_radius=5)
            pygame.draw.rect(
                self.screen, col if not s.used else (75, 70, 95), base_rect, 2, border_radius=5
            )

            # Floating crystal obelisk above pedestal
            bob = int(math.sin(time_sec * 4.2) * 4) if not s.used else 0
            gem_pts = [
                (sx, sy - 26 + bob),
                (sx - 11, sy - 11 + bob),
                (sx, sy + 2 + bob),
                (sx + 11, sy - 11 + bob),
            ]
            pygame.draw.polygon(
                self.screen, col if not s.used else (68, 64, 88), gem_pts
            )
            pygame.draw.polygon(self.screen, (255, 255, 255), gem_pts, 2)

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
                    ang = time_sec * 0.55 + (i * math.pi / 3.0)
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
        biome: Dict[str, Any],
        cam_ox: int,
        cam_oy: int,
        time_sec: float,
    ) -> None:
        biome_torch = biome["torch_color"]
        boss_torch = biome["boss_color"]
        for t in torches:
            sx = int(t.x - cam_ox)
            sy = int(t.y - cam_oy)
            if sx < -80 or sx > SCREEN_WIDTH + 80 or sy < -80 or sy > SCREEN_HEIGHT + 80:
                continue
            flicker = math.sin(time_sec * 9.0 + t.phase) * 3.5
            glow_col = boss_torch if t.color_variant == "boss" else biome_torch
            self.draw_glow(sx, sy, int(54 + flicker), glow_col)
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
            self.draw_glow(sx, sy, 32, COLOR_PICKUP_HP)

            pygame.draw.ellipse(
                self.screen,
                (10, 8, 16),
                pygame.Rect(sx - 11, int(p.y - cam_oy) + 9, 22, 7),
            )
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

        self.draw_glow(sx, sy, 48, COLOR_PLAYER)

        if player.is_whirlwinding:
            self._draw_whirlwind_fx(player, sx, sy, time_sec)

        if player.is_attacking:
            self._draw_sword_slash(player, sx, sy)

        # Ground shadow
        pygame.draw.ellipse(
            self.screen,
            (8, 7, 14),
            pygame.Rect(sx - 16, sy + 10, 32, 10),
        )

        bob = int(math.sin(player.walk_anim_timer * 2.0) * 2.5) if player.is_moving else 0

        # Flowing battle cloak
        cape_dx = -math.cos(player.facing_angle)
        cape_dy = -math.sin(player.facing_angle)
        flutter = math.sin(time_sec * 14.0) * 4.5
        cape_pts = [
            (sx + int(cape_dy * 9), sy + bob),
            (sx - int(cape_dy * 9), sy + bob),
            (
                sx + int(cape_dx * 24 + cape_dy * flutter),
                sy + int(cape_dy * 24 - cape_dx * flutter) + 4,
            ),
        ]
        pygame.draw.polygon(self.screen, COLOR_PLAYER_CAPE, cape_pts)

        # Armored pauldrons
        perp_x = -math.sin(player.facing_angle)
        perp_y = math.cos(player.facing_angle)
        for side in (-1, 1):
            px = sx + int(perp_x * side * 11)
            py = sy + bob + int(perp_y * side * 11)
            pygame.draw.circle(self.screen, COLOR_PLAYER_ARMOR, (px, py), 7)
            pygame.draw.circle(self.screen, COLOR_PLAYER, (px, py), 7, 1)

        body_col = (
            (255, 255, 255)
            if player.hurt_flash_timer > 0.0
            else COLOR_ABILITY_DASH if player.is_dashing else COLOR_PLAYER
        )
        pygame.draw.circle(self.screen, COLOR_PLAYER_ARMOR, (sx, sy + bob), int(player.radius))
        pygame.draw.circle(self.screen, body_col, (sx, sy - 2 + bob), int(player.radius - 2))
        pygame.draw.circle(
            self.screen, COLOR_PLAYER_CORE, (sx, sy - 3 + bob), int(player.radius - 7)
        )
        # Templar helm crest
        crest_x = sx + int(math.cos(player.facing_angle) * 9)
        crest_y = sy - 3 + bob + int(math.sin(player.facing_angle) * 9)
        pygame.draw.line(self.screen, COLOR_GOLD, (sx, sy - 3 + bob), (crest_x, crest_y), 3)

        # Glowing Arcane Visor Eyes
        ex = sx + int(math.cos(player.facing_angle) * 6)
        ey = sy - 3 + bob + int(math.sin(player.facing_angle) * 6)
        for side in (-1, 1):
            eye_pos = (int(ex + perp_x * 3.5 * side), int(ey + perp_y * 3.5 * side))
            pygame.draw.circle(self.screen, (15, 22, 42), eye_pos, 3)
            pygame.draw.circle(self.screen, (255, 245, 160), eye_pos, 2)

        # Idle Rune Greatsword held at player's side when not swinging
        if not player.is_attacking and not player.is_whirlwinding:
            hand_ang = player.facing_angle + 0.65 * player.attack_swing_dir
            hx = sx + int(math.cos(hand_ang) * 14)
            hy = sy + int(math.sin(hand_ang) * 14)
            tip_x = hx + int(math.cos(player.facing_angle - 0.2 * player.attack_swing_dir) * 22)
            tip_y = hy + int(math.sin(player.facing_angle - 0.2 * player.attack_swing_dir) * 22)
            pygame.draw.line(self.screen, COLOR_SWORD_TRAIL, (hx, hy), (tip_x, tip_y), 5)
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
        reach = PLAYER_ATTACK_RANGE * (1.24 if is_finisher else 1.0)
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
                    sx + int(math.cos(ang) * (reach * 0.50)),
                    sy + int(math.sin(ang) * (reach * 0.50)),
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
            if sx < -90 or sx > SCREEN_WIDTH + 90 or sy < -90 or sy > SCREEN_HEIGHT + 90:
                continue

            self.draw_glow(sx, sy, int(r * 2.0), e.color)

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
                pygame.draw.circle(self.screen, COLOR_SLIME_HIGHLIGHT, (sx - 4, sy - 5), 3)
                pygame.draw.circle(self.screen, (18, 35, 22), (sx - 5, sy - 1), 3)
                pygame.draw.circle(self.screen, (18, 35, 22), (sx + 5, sy - 1), 3)

            elif e.enemy_type == "cultist":
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

            elif e.enemy_type == "boss_broodmother":
                # BOSS 1: Broodmother Vexis (Arachnid Venom Matriarch with 8 articulated legs & egg sac)
                for side in (-1, 1):
                    for leg_i in range(4):
                        ang = (leg_i - 1.5) * 0.42 + math.sin(time_sec * 10 + leg_i) * 0.12
                        lx = sx + int(math.cos(ang) * side * (r + 14))
                        ly = sy + int(math.sin(ang) * (r + 10))
                        pygame.draw.line(self.screen, (40, 140, 70), (sx, sy), (lx, ly), 3)
                pygame.draw.circle(self.screen, (22, 85, 45), (sx, sy - 6), int(r * 0.85))
                pygame.draw.circle(self.screen, col, (sx, sy + 2), r - 2)
                # Cluster of 6 glowing spider eyes
                for ex_off in (-8, -3, 3, 8):
                    pygame.draw.circle(self.screen, (255, 250, 95), (sx + ex_off, sy + 4), 3)

            elif e.enemy_type == "boss_inquisitor":
                # BOSS 2: High Inquisitor Vaelen (Floating Astral Seraph with Halo & Orbiting Grimoires)
                pygame.draw.circle(self.screen, (95, 235, 255), (sx, sy - r - 6), 14, 2)
                for i in range(3):
                    ang = time_sec * 3.0 + i * (2.0 * math.pi / 3.0)
                    ox = sx + int(math.cos(ang) * (r + 14))
                    oy = sy + int(math.sin(ang) * (r + 14))
                    pygame.draw.rect(self.screen, (95, 235, 255), pygame.Rect(ox - 5, oy - 7, 10, 14), border_radius=2)
                robe_pts = [(sx, sy - r - 8), (sx - r, sy + r), (sx + r, sy + r)]
                pygame.draw.polygon(self.screen, (64, 18, 105), robe_pts)
                pygame.draw.polygon(self.screen, col, robe_pts, 3)
                pygame.draw.circle(self.screen, (20, 10, 34), (sx, sy - 4), 10)
                pygame.draw.circle(self.screen, (95, 245, 255), (sx - 4, sy - 4), 3)
                pygame.draw.circle(self.screen, (95, 245, 255), (sx + 4, sy - 4), 3)

            elif e.enemy_type == "boss_behemoth":
                # BOSS 3: Kragor, the Rime Colossus (Crystalline Ice Golem with Spiked Glacial Pauldrons)
                if e.state == "windup":
                    pygame.draw.circle(self.screen, (180, 245, 255), (sx, sy), r + 14, 3)
                oct_pts = []
                for i in range(8):
                    ang = i * (math.pi / 4.0) + math.pi / 8.0
                    oct_pts.append((sx + int(math.cos(ang) * r), sy + int(math.sin(ang) * r)))
                pygame.draw.polygon(self.screen, (32, 95, 140), oct_pts)
                pygame.draw.polygon(self.screen, col, oct_pts, 3)
                # Frost crystal horns
                pygame.draw.polygon(self.screen, (225, 250, 255), [(sx - 14, sy - r + 4), (sx - 24, sy - r - 12), (sx - 6, sy - r)])
                pygame.draw.polygon(self.screen, (225, 250, 255), [(sx + 14, sy - r + 4), (sx + 24, sy - r - 12), (sx + 6, sy - r)])
                pygame.draw.circle(self.screen, (255, 255, 255), (sx - 8, sy - 3), 4)
                pygame.draw.circle(self.screen, (255, 255, 255), (sx + 8, sy - 3), 4)

            elif e.enemy_type == "boss_wyrm":
                # BOSS 4: Ignis, the Cinder Drake (Molten Winged Dragon with Flapping Magma Wings)
                wing_span = int(16 + math.sin(time_sec * 11.0) * 7)
                left_wing = [(sx - 10, sy), (sx - r - wing_span, sy - 18), (sx - r - 6, sy + 14)]
                right_wing = [(sx + 10, sy), (sx + r + wing_span, sy - 18), (sx + r + 6, sy + 14)]
                pygame.draw.polygon(self.screen, (165, 42, 24), left_wing)
                pygame.draw.polygon(self.screen, (165, 42, 24), right_wing)
                pygame.draw.polygon(self.screen, (255, 195, 65), left_wing, 2)
                pygame.draw.polygon(self.screen, (255, 195, 65), right_wing, 2)
                pygame.draw.circle(self.screen, (115, 28, 18), (sx, sy), r)
                pygame.draw.circle(self.screen, col, (sx, sy), r - 4)
                pygame.draw.circle(self.screen, (255, 245, 120), (sx - 8, sy - 4), 4)
                pygame.draw.circle(self.screen, (255, 245, 120), (sx + 8, sy - 4), 4)

            elif e.enemy_type == "boss":
                # BOSS 5: Malakor, the Obsidian King
                if e.state == "windup":
                    pygame.draw.circle(self.screen, (255, 210, 65), (sx, sy), r + 15, 3)
                if e.boss_phase == 2:
                    aura_r = r + 8 + int(math.sin(e.anim_timer * 3.0) * 5)
                    pygame.draw.circle(self.screen, (255, 100, 40), (sx, sy), aura_r, 3)

                for i in range(4):
                    ang = time_sec * 3.2 + i * (math.pi * 0.5)
                    ox = sx + int(math.cos(ang) * (r + 13))
                    oy = sy + int(math.sin(ang) * (r + 13))
                    pygame.draw.circle(self.screen, COLOR_BOSS_CROWN, (ox, oy), 5)

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
        self,
        player: Player,
        enemies: List[Enemy],
        cam_ox: int,
        cam_oy: int,
        time_sec: float,
    ) -> None:
        """Draw directional aim chevron and auto-lock target indicator."""
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

        # If in AUTO aim mode, highlight the locked-on enemy with a subtle target ring
        if player.aim_mode == "AUTO":
            nearest = None
            best_d = 215.0
            for e in enemies:
                if not e.alive:
                    continue
                d = math.hypot(e.x - player.x, e.y - player.y)
                if d < best_d:
                    best_d = d
                    nearest = e
            if nearest is not None:
                tx = int(nearest.x - cam_ox)
                ty = int(nearest.y - cam_oy)
                pygame.draw.circle(
                    self.screen,
                    COLOR_UI_HIGHLIGHT,
                    (tx, ty),
                    int(nearest.radius + 7 + math.sin(time_sec * 10) * 2),
                    1,
                )

    def _draw_hud(
        self,
        player: Player,
        dungeon: Dungeon,
        biome: Dict[str, Any],
        enemies: List[Enemy],
        score: int,
        high_score: int,
        banner_text: str,
        banner_timer: float,
        toast_text: str,
        toast_timer: float,
        music_on: bool,
    ) -> None:
        # Top-Left Status Panel
        panel = pygame.Rect(16, 14, 360, 118)
        pygame.draw.rect(self.screen, COLOR_UI_BG, panel, border_radius=10)
        pygame.draw.rect(self.screen, biome["wall_highlight"], panel, 2, border_radius=10)

        hp_label = self.font_sm.render(
            f"HP  {player.hp} / {player.max_hp}", True, COLOR_TEXT
        )
        lvl_label = self.font_sm.render(f"LVL {player.level}", True, COLOR_GOLD)
        self.screen.blit(hp_label, (28, 22))
        self.screen.blit(lvl_label, (300, 22))

        hp_bar_bg = pygame.Rect(28, 44, 332, 16)
        pygame.draw.rect(self.screen, COLOR_HP_BG, hp_bar_bg, border_radius=4)
        hp_ratio = max(0.0, min(1.0, player.hp / player.max_hp))
        pygame.draw.rect(
            self.screen,
            COLOR_HP_BAR,
            pygame.Rect(28, 44, int(332 * hp_ratio), 16),
            border_radius=4,
        )
        pygame.draw.rect(self.screen, COLOR_UI_BORDER, hp_bar_bg, 1, border_radius=4)

        # XP Bar
        xp_bg = pygame.Rect(28, 65, 332, 8)
        pygame.draw.rect(self.screen, (20, 32, 34), xp_bg, border_radius=3)
        xp_ratio = max(0.0, min(1.0, player.xp / max(1, player.xp_to_next)))
        pygame.draw.rect(
            self.screen,
            COLOR_XP_BAR,
            pygame.Rect(28, 65, int(332 * xp_ratio), 8),
            border_radius=3,
        )

        biome_txt = self.font_xs.render(
            f"AREA {dungeon.floor_num}/{BOSS_FLOOR}: {biome['name']}",
            True,
            biome["wall_rune"],
        )
        aim_txt = self.font_xs.render(
            f"AIM: {player.aim_mode}  |  BGM [M]: {'ON' if music_on else 'MUTED'}  |  CODEX [C/TAB]",
            True,
            COLOR_TEXT_DIM,
        )
        self.screen.blit(biome_txt, (28, 80))
        self.screen.blit(aim_txt, (28, 100))

        # Score & Hostiles Panel
        score_panel = pygame.Rect(386, 14, 228, 82)
        pygame.draw.rect(self.screen, COLOR_UI_BG, score_panel, border_radius=10)
        pygame.draw.rect(self.screen, COLOR_UI_BORDER, score_panel, 2, border_radius=10)

        score_surf = self.font_md.render(f"SCORE: {score}", True, COLOR_TEXT)
        best_surf = self.font_xs.render(
            f"BEST: {max(score, high_score)}", True, COLOR_GOLD
        )
        enemies_left = sum(1 for e in enemies if e.alive)
        portal_state = "OPEN" if dungeon.stairs_unlocked else "BOSS SEALED"
        rem_surf = self.font_xs.render(
            f"Hostiles: {enemies_left}  •  Portal: {portal_state}", True, COLOR_TEXT_DIM
        )
        self.screen.blit(score_surf, (400, 20))
        self.screen.blit(best_surf, (400, 44))
        self.screen.blit(rem_surf, (400, 64))

        # Bottom-Center Steam-Style Ability Hotbar
        self._draw_ability_hotbar(player)

        # Floor Guardian Boss Health Bar at Top-Center (Active on EVERY Floor when Boss is alive!)
        boss = next((e for e in enemies if e.is_boss and e.alive), None)
        if boss is not None:
            bw = 420
            bh = 18
            bx = (SCREEN_WIDTH - bw) // 2 + 80
            by = 18
            boss_bg = pygame.Rect(bx - 12, by - 4, bw + 24, 58)
            pygame.draw.rect(self.screen, COLOR_UI_BG, boss_bg, border_radius=8)
            pygame.draw.rect(self.screen, boss.color, boss_bg, 2, border_radius=8)

            title = self.font_sm.render(
                f"★ {boss.name.upper()} (Phase {boss.boss_phase}) ★",
                True,
                COLOR_GOLD,
            )
            sub = self.font_xs.render(boss.subtitle, True, COLOR_TEXT_DIM)
            self.screen.blit(title, (bx + bw // 2 - title.get_width() // 2, by))
            self.screen.blit(sub, (bx + bw // 2 - sub.get_width() // 2, by + 17))

            bar_rect = pygame.Rect(bx, by + 34, bw, bh)
            pygame.draw.rect(self.screen, COLOR_HP_BG, bar_rect, border_radius=4)
            fill = int(bw * max(0.0, boss.hp / boss.max_hp))
            pygame.draw.rect(
                self.screen,
                boss.color,
                pygame.Rect(bx, by + 34, fill, bh),
                border_radius=4,
            )
            pygame.draw.rect(self.screen, COLOR_UI_BORDER, bar_rect, 1, border_radius=4)

        self._draw_minimap(dungeon, player, enemies)

        if banner_timer > 0.0 and banner_text:
            bsurf = self.font_subtitle.render(banner_text, True, COLOR_GOLD)
            bx = SCREEN_WIDTH // 2 - bsurf.get_width() // 2
            by = 104
            bg_rect = pygame.Rect(
                bx - 18, by - 8, bsurf.get_width() + 36, bsurf.get_height() + 16
            )
            pygame.draw.rect(self.screen, COLOR_UI_BG, bg_rect, border_radius=8)
            pygame.draw.rect(self.screen, biome["wall_rune"], bg_rect, 2, border_radius=8)
            self.screen.blit(bsurf, (bx, by))

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
            ("SWORD", "J / SPACE", 0.0, 1.0, COLOR_SWORD_TRAIL),
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

        slot_w = 106
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
        mx = SCREEN_WIDTH - mw - 16
        my = 14

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
            if 0 <= etx < dungeon.width and 0 <= ety < dungeon.height and (
                dungeon.explored[ety][etx] or e.is_boss
            ):
                sz = scale + 2 if e.is_boss else scale
                col = COLOR_GOLD if e.is_boss else (250, 70, 90)
                pygame.draw.rect(
                    self.screen,
                    col,
                    pygame.Rect(mx + etx * scale, my + ety * scale, sz, sz),
                )

        ptx = int(player.x // TILE_SIZE)
        pty = int(player.y // TILE_SIZE)
        pygame.draw.rect(
            self.screen,
            COLOR_PLAYER,
            pygame.Rect(mx + ptx * scale - 1, my + pty * scale - 1, scale + 2, scale + 2),
        )

    def render_codex_overlay(self) -> None:
        """Render the 5-Biome & 5-Boss Bestiary Codex screen."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 5, 13, 232))
        self.screen.blit(overlay, (0, 0))

        card = pygame.Rect(SCREEN_WIDTH // 2 - 480, 44, 960, 632)
        pygame.draw.rect(self.screen, COLOR_UI_BG, card, border_radius=14)
        pygame.draw.rect(self.screen, COLOR_GOLD, card, 3, border_radius=14)

        title = self.font_subtitle.render(
            "ROYAL CODEX — 5 BIOME REALMS & 5 FLOOR GUARDIAN BOSSES",
            True,
            COLOR_GOLD,
        )
        sub = self.font_xs.render(
            "Every Floor features its own Biome Architecture, Musical Score, and Guardian Boss. Press [ESC / C / TAB / ENTER] to Close.",
            True,
            COLOR_UI_HIGHLIGHT,
        )
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 66))
        self.screen.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, 100))

        boss_descriptions = {
            1: "Abilities: 5-Globule Acid Spray, Venomous Leap Slam + Ring, Summons Slime Hatchlings.",
            2: "Abilities: Astral Twin-Spiral Nova, Precision Void Lances, Phase-Blink Teleport.",
            3: "Abilities: Sub-Zero Avalanche Charge, Glacial Shatter Nova, Frost Cone Barrage.",
            4: "Abilities: Dragon Breath Flame Stream, Magma Trail Rush, Molten Supernova Ring.",
            5: "Abilities: 2-Phase Obsidian Monarch — Fan Volley, Meteor Slam, Astral Ring & Summons.",
        }

        for fl in range(1, 6):
            bm = BIOME_THEMES[fl]
            row = pygame.Rect(SCREEN_WIDTH // 2 - 440, 134 + (fl - 1) * 102, 880, 90)
            pygame.draw.rect(self.screen, bm["floor_b"], row, border_radius=10)
            pygame.draw.rect(self.screen, bm["wall_rune"], row, 2, border_radius=10)

            # Boss emblem badge
            cx = row.x + 48
            cy = row.centery
            pygame.draw.circle(self.screen, bm["wall_top"], (cx, cy), 30)
            pygame.draw.circle(self.screen, bm["boss_color"], (cx, cy), 22)
            pygame.draw.circle(self.screen, bm["boss_secondary"], (cx, cy), 22, 3)

            b_head = self.font_md.render(
                f"FLOOR {fl}: {bm['name']}  —  BOSS: {bm['boss_name'].upper()}",
                True,
                bm["boss_color"],
            )
            b_sub = self.font_xs.render(
                f"{bm['boss_title']}   •   {bm['subtitle']}",
                True,
                COLOR_TEXT,
            )
            b_abilities = self.font_xs.render(
                boss_descriptions[fl],
                True,
                COLOR_GOLD,
            )
            self.screen.blit(b_head, (row.x + 94, row.y + 12))
            self.screen.blit(b_sub, (row.x + 94, row.y + 38))
            self.screen.blit(b_abilities, (row.x + 94, row.y + 62))

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

    def render_pause_overlay(self, selected_idx: int, music_on: bool) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 5, 12, 205))
        self.screen.blit(overlay, (0, 0))

        card = pygame.Rect(SCREEN_WIDTH // 2 - 230, 155, 460, 390)
        pygame.draw.rect(self.screen, COLOR_UI_BG, card, border_radius=12)
        pygame.draw.rect(self.screen, COLOR_UI_BORDER, card, 3, border_radius=12)

        t_surf = self.font_subtitle.render("EXPEDITION PAUSED", True, COLOR_GOLD)
        self.screen.blit(t_surf, (SCREEN_WIDTH // 2 - t_surf.get_width() // 2, 180))

        opts = [
            "RESUME EXPEDITION (ESC / ENTER)",
            "OPEN BOSS & BIOME CODEX (C)",
            f"TOGGLE MUSIC: {'ON' if music_on else 'MUTED'} (M)",
            "RESTART FLOOR 1 (R)",
            "RETURN TO MAIN MENU",
            "QUIT TO DESKTOP",
        ]
        for i, label in enumerate(opts):
            is_sel = i == selected_idx
            btn = pygame.Rect(SCREEN_WIDTH // 2 - 190, 232 + i * 48, 380, 38)
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
        self,
        hs_data: Dict[str, Any],
        selected_index: int,
        time_sec: float,
        music_on: bool = True,
    ) -> None:
        self.screen.fill(COLOR_BG)

        # Animated perspective grid & 5-biome colored embers
        for x in range(0, SCREEN_WIDTH, 64):
            pygame.draw.line(self.screen, (16, 14, 28), (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, 64):
            pygame.draw.line(self.screen, (16, 14, 28), (0, y), (SCREEN_WIDTH, y))

        biome_cols = [BIOME_THEMES[i]["boss_color"] for i in range(1, 6)]
        for i in range(30):
            ex = int((i * 173 + time_sec * (22 + (i % 5) * 8)) % SCREEN_WIDTH)
            ey = int((SCREEN_HEIGHT - (i * 97 + time_sec * (35 + (i % 4) * 12)) % SCREEN_HEIGHT))
            col = biome_cols[i % len(biome_cols)]
            pygame.draw.circle(self.screen, col, (ex, ey), 2 + (i % 2))

        card = pygame.Rect(SCREEN_WIDTH // 2 - 460, 24, 920, 672)
        pygame.draw.rect(self.screen, COLOR_UI_BG, card, border_radius=16)
        pygame.draw.rect(self.screen, COLOR_UI_BORDER, card, 3, border_radius=16)

        title_surf = self.font_title.render(GAME_TITLE, True, COLOR_GOLD)
        self.screen.blit(
            title_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 44)
        )
        sub_surf = self.font_sm.render(
            f"{GAME_SUBTITLE}  •  {GAME_VERSION}", True, COLOR_UI_HIGHLIGHT
        )
        self.screen.blit(
            sub_surf, (SCREEN_WIDTH // 2 - sub_surf.get_width() // 2, 96)
        )

        # Career & High Score Banner
        stats_box = pygame.Rect(SCREEN_WIDTH // 2 - 410, 126, 820, 68)
        pygame.draw.rect(self.screen, COLOR_UI_PANEL, stats_box, border_radius=10)
        pygame.draw.rect(self.screen, COLOR_GOLD, stats_box, 2, border_radius=10)

        hs_txt = self.font_subtitle.render(
            f"HIGH SCORE: {hs_data.get('high_score', 0)}", True, COLOR_GOLD
        )
        unlocked_count = len(hs_data.get("achievements", []))
        meta_txt = self.font_xs.render(
            f"Best Floor: {hs_data.get('best_floor', 1)}/5  |  Runs: {hs_data.get('total_runs', 0)}  |  Victories: {hs_data.get('victories', 0)}  |  Bosses Slain: {hs_data.get('bosses_slain', 0)}  |  Kills: {hs_data.get('total_kills', 0)}  |  Trophies: {unlocked_count}/{len(ACHIEVEMENTS_CATALOG)}",
            True,
            COLOR_TEXT,
        )
        self.screen.blit(hs_txt, (SCREEN_WIDTH // 2 - hs_txt.get_width() // 2, 134))
        self.screen.blit(meta_txt, (SCREEN_WIDTH // 2 - meta_txt.get_width() // 2, 168))

        options = [
            "START NEW EXPEDITION (ENTER / SPACE)",
            "BOSS & BIOME CODEX — 5 AREAS & 5 BOSSES (C)",
            f"SOUNDTRACK & AUDIO: {'ON' if music_on else 'MUTED'} (M)",
            "QUIT TO DESKTOP (ESC)",
        ]
        for idx, label in enumerate(options):
            is_sel = idx == selected_index
            btn_rect = pygame.Rect(SCREEN_WIDTH // 2 - 260, 206 + idx * 44, 520, 38)
            bg_col = (44, 38, 76) if is_sel else COLOR_UI_PANEL
            border_col = COLOR_GOLD if is_sel else COLOR_UI_BORDER
            pygame.draw.rect(self.screen, bg_col, btn_rect, border_radius=8)
            pygame.draw.rect(self.screen, border_col, btn_rect, 2, border_radius=8)

            txt_col = COLOR_GOLD if is_sel else COLOR_TEXT
            surf = self.font_sm.render(label, True, txt_col)
            self.screen.blit(
                surf,
                (
                    SCREEN_WIDTH // 2 - surf.get_width() // 2,
                    btn_rect.centery - surf.get_height() // 2,
                ),
            )

        # 5 Bosses Preview Strip on Main Menu
        boss_strip_y = 390
        strip_lbl = self.font_xs.render(
            "5 DISTINCT BIOME REALMS & 5 GUARDIAN BOSSES:", True, COLOR_GOLD
        )
        self.screen.blit(strip_lbl, (SCREEN_WIDTH // 2 - 410, boss_strip_y))
        for fl in range(1, 6):
            bm = BIOME_THEMES[fl]
            bx = SCREEN_WIDTH // 2 - 410 + (fl - 1) * 166
            by = boss_strip_y + 18
            brect = pygame.Rect(bx, by, 158, 56)
            pygame.draw.rect(self.screen, bm["floor_b"], brect, border_radius=7)
            pygame.draw.rect(self.screen, bm["boss_color"], brect, 2, border_radius=7)
            f_txt = self.font_xs.render(f"F{fl}: {bm['boss_name'][:16]}", True, bm["boss_color"])
            a_txt = self.font_xs.render(bm["name"][4:20], True, COLOR_TEXT_DIM)
            self.screen.blit(f_txt, (bx + 8, by + 8))
            self.screen.blit(a_txt, (bx + 8, by + 30))

        # Controls & Abilities Showcase Box
        info_box = pygame.Rect(SCREEN_WIDTH // 2 - 410, 474, 820, 118)
        pygame.draw.rect(self.screen, COLOR_UI_PANEL, info_box, border_radius=10)
        pygame.draw.rect(self.screen, COLOR_UI_BORDER, info_box, 2, border_radius=10)

        guide_lines = [
            "CONTROLS (NO MOUSE REQUIRED — KEYBOARD, TWIN-STICK & MOUSE SUPPORTED):",
            "• MOVE: WASD   |   AIM: Arrow Keys, Auto-Target Nearest Enemy, or Mouse   |   SHRINES: Walk over to claim blessing",
            "• ATTACK: [J] / [SPACE] (3-Hit Crescent Combo)   |   [Q/1] Whirlwind   |   [E/2] Eldritch Nova   |   [R/3] Chain Lightning   |   [SHIFT/K] Dash",
            "• AUDIO & UI: [M] Toggle Soundtrack   |   [-/+] Adjust Volume   |   [C / TAB] Boss & Biome Codex   |   [P / ESC] Pause",
        ]
        for i, line in enumerate(guide_lines):
            col = COLOR_UI_HIGHLIGHT if i == 0 else COLOR_TEXT
            gsurf = self.font_xs.render(line, True, col)
            self.screen.blit(gsurf, (info_box.x + 16, info_box.y + 10 + i * 26))

        # 8 Steam Achievements Grid at bottom of Main Menu
        ach_unlocked = set(hs_data.get("achievements", []))
        ach_y = 602
        for i, ach in enumerate(ACHIEVEMENTS_CATALOG):
            is_un = ach["id"] in ach_unlocked
            col_idx = i % 4
            row_idx = i // 4
            ax = SCREEN_WIDTH // 2 - 410 + col_idx * 208
            ay = ach_y + row_idx * 40
            arect = pygame.Rect(ax, ay, 198, 34)
            pygame.draw.rect(
                self.screen,
                (30, 46, 42) if is_un else (18, 16, 28),
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
            badge = "★ " if is_un else "• "
            asurf = self.font_xs.render(
                f"{badge}{ach['name']}",
                True,
                COLOR_GOLD if is_un else COLOR_TEXT_DIM,
            )
            self.screen.blit(asurf, (ax + 10, ay + 9))

    def render_end_screen(
        self,
        victory: bool,
        score: int,
        floor_num: int,
        player_level: int,
        kills: int,
        bosses_slain: int,
        hs_data: Dict[str, Any],
    ) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 6, 14, 225))
        self.screen.blit(overlay, (0, 0))

        card = pygame.Rect(SCREEN_WIDTH // 2 - 320, 110, 640, 490)
        pygame.draw.rect(self.screen, COLOR_UI_BG, card, border_radius=14)
        border_col = COLOR_GOLD if victory else COLOR_HP_BAR
        pygame.draw.rect(self.screen, border_col, card, 3, border_radius=14)

        heading = (
            "VICTORY! ALL 5 BIOME LORDS VANQUISHED!"
            if victory
            else "YOU HAVE FALLEN IN THE CRYPTS"
        )
        h_surf = self.font_subtitle.render(heading, True, border_col)
        self.screen.blit(
            h_surf, (SCREEN_WIDTH // 2 - h_surf.get_width() // 2, 145)
        )

        if hs_data.get("is_new_high"):
            badge = self.font_md.render("★ NEW HIGH SCORE RECORD! ★", True, COLOR_GOLD)
            self.screen.blit(
                badge, (SCREEN_WIDTH // 2 - badge.get_width() // 2, 188)
            )

        biome_name = get_biome_theme(floor_num)["name"]
        lines = [
            f"Final Score: {score}   (Best: {hs_data.get('high_score', score)})",
            f"Area Reached: Floor {floor_num}/{BOSS_FLOOR} — {biome_name}",
            f"Hero Level: {player_level}   •   Floor Bosses Vanquished: {bosses_slain}/5",
            f"Monsters Slain This Run: {kills}",
            f"Career Expeditions: {hs_data.get('total_runs', 1)}   •   Career Victories: {hs_data.get('victories', 0)}",
        ]
        for i, line in enumerate(lines):
            lsurf = self.font_md.render(line, True, COLOR_TEXT)
            self.screen.blit(
                lsurf, (SCREEN_WIDTH // 2 - lsurf.get_width() // 2, 236 + i * 38)
            )

        prompt = self.font_sm.render(
            "Press ENTER / R to Play Again   |   Press M for Main Menu   |   Press ESC to Quit",
            True,
            COLOR_GOLD,
        )
        self.screen.blit(
            prompt, (SCREEN_WIDTH // 2 - prompt.get_width() // 2, 535)
        )
