"""Procedural dungeon generator for floors 1-5."""

from dataclasses import dataclass, field
import math
import random
from typing import List, Optional, Tuple

from settings import (
    BOSS_FLOOR,
    DUNGEON_HEIGHT,
    DUNGEON_WIDTH,
    TILE_FLOOR,
    TILE_SIZE,
    TILE_STAIRS_DOWN,
    TILE_VOID,
    TILE_WALL,
)


@dataclass
class Room:
    """Rectangular dungeon room in tile coordinates."""

    x: int
    y: int
    w: int
    h: int
    room_type: str = "normal"  # "start", "normal", "exit", "boss"
    cleared: bool = False
    visited: bool = False

    @property
    def right(self) -> int:
        return self.x + self.w

    @property
    def bottom(self) -> int:
        return self.y + self.h

    @property
    def center_tile(self) -> Tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)

    @property
    def center_px(self) -> Tuple[float, float]:
        cx, cy = self.center_tile
        return ((cx + 0.5) * TILE_SIZE, (cy + 0.5) * TILE_SIZE)

    def intersects(self, other: "Room", padding: int = 2) -> bool:
        return (
            self.x - padding < other.right
            and self.right + padding > other.x
            and self.y - padding < other.bottom
            and self.bottom + padding > other.y
        )

    def contains_pixel(self, px: float, py: float) -> bool:
        tx = int(px // TILE_SIZE)
        ty = int(py // TILE_SIZE)
        return self.x <= tx < self.right and self.y <= ty < self.bottom

    def random_floor_pixel(
        self, rng: random.Random, margin: int = 1
    ) -> Tuple[float, float]:
        tx = rng.randint(self.x + margin, max(self.x + margin, self.right - 1 - margin))
        ty = rng.randint(self.y + margin, max(self.y + margin, self.bottom - 1 - margin))
        return ((tx + 0.5) * TILE_SIZE, (ty + 0.5) * TILE_SIZE)


@dataclass
class EnemySpawnSpec:
    """Specification for an enemy to spawn on the floor."""

    enemy_type: str  # "slime", "cultist", "brute", "boss"
    x: float
    y: float
    room_index: int


@dataclass
class PickupSpawnSpec:
    """Specification for a pickup item to spawn on the floor."""

    pickup_type: str  # "health"
    x: float
    y: float


@dataclass
class Dungeon:
    """Represents a generated dungeon floor."""

    floor_num: int
    width: int
    height: int
    grid: List[List[int]]
    rooms: List[Room] = field(default_factory=list)
    explored: List[List[bool]] = field(default_factory=list)
    player_start: Tuple[float, float] = (0.0, 0.0)
    stairs_tile: Optional[Tuple[int, int]] = None
    stairs_unlocked: bool = False
    enemy_spawns: List[EnemySpawnSpec] = field(default_factory=list)
    pickup_spawns: List[PickupSpawnSpec] = field(default_factory=list)

    def is_walkable(self, tx: int, ty: int) -> bool:
        if tx < 0 or ty < 0 or tx >= self.width or ty >= self.height:
            return False
        tile = self.grid[ty][tx]
        return tile in (TILE_FLOOR, TILE_STAIRS_DOWN)

    def is_wall(self, tx: int, ty: int) -> bool:
        if tx < 0 or ty < 0 or tx >= self.width or ty >= self.height:
            return True
        return self.grid[ty][tx] == TILE_WALL

    def reveal_around(self, px: float, py: float, radius_tiles: int = 8) -> None:
        cx = int(px // TILE_SIZE)
        cy = int(py // TILE_SIZE)
        r_sq = radius_tiles * radius_tiles
        for ty in range(max(0, cy - radius_tiles), min(self.height, cy + radius_tiles + 1)):
            for tx in range(max(0, cx - radius_tiles), min(self.width, cx + radius_tiles + 1)):
                if (tx - cx) ** 2 + (ty - cy) ** 2 <= r_sq:
                    self.explored[ty][tx] = True

        for room in self.rooms:
            if room.contains_pixel(px, py):
                room.visited = True
                for ty in range(max(0, room.y - 1), min(self.height, room.bottom + 1)):
                    for tx in range(max(0, room.x - 1), min(self.width, room.right + 1)):
                        self.explored[ty][tx] = True

    def circle_collides_walls(self, px: float, py: float, radius: float) -> bool:
        """Check if a circle at (px, py) overlaps any non-walkable tile."""
        min_tx = int((px - radius) // TILE_SIZE)
        max_tx = int((px + radius) // TILE_SIZE)
        min_ty = int((py - radius) // TILE_SIZE)
        max_ty = int((py + radius) // TILE_SIZE)

        for ty in range(min_ty, max_ty + 1):
            for tx in range(min_tx, max_tx + 1):
                if not self.is_walkable(tx, ty):
                    # Closest point on tile AABB to circle center
                    rx = max(tx * TILE_SIZE, min(px, (tx + 1) * TILE_SIZE))
                    ry = max(ty * TILE_SIZE, min(py, (ty + 1) * TILE_SIZE))
                    dx = px - rx
                    dy = py - ry
                    if dx * dx + dy * dy < radius * radius:
                        return True
        return False

    def move_with_sliding(
        self, x: float, y: float, vx: float, vy: float, radius: float, dt: float
    ) -> Tuple[float, float, bool]:
        """Move an entity with axis-separated wall sliding. Returns (nx, ny, hit_wall)."""
        hit_wall = False
        nx = x + vx * dt
        if self.circle_collides_walls(nx, y, radius):
            nx = x
            hit_wall = True

        ny = y + vy * dt
        if self.circle_collides_walls(nx, ny, radius):
            ny = y
            hit_wall = True

        return nx, ny, hit_wall

    def has_line_of_sight(
        self, x1: float, y1: float, x2: float, y2: float
    ) -> bool:
        """Raymarch between two pixel points to see if any wall blocks line of sight."""
        dist = math.hypot(x2 - x1, y2 - y1)
        if dist < 1.0:
            return True
        steps = max(2, int(dist / (TILE_SIZE * 0.35)))
        for i in range(1, steps):
            t = i / steps
            px = x1 + (x2 - x1) * t
            py = y1 + (y2 - y1) * t
            tx = int(px // TILE_SIZE)
            ty = int(py // TILE_SIZE)
            if not self.is_walkable(tx, ty):
                return False
        return True


def _carve_room(grid: List[List[int]], room: Room) -> None:
    for ty in range(room.y, room.bottom):
        for tx in range(room.x, room.right):
            grid[ty][tx] = TILE_FLOOR


def _carve_h_corridor(grid: List[List[int]], x1: int, x2: int, y: int) -> None:
    start, end = min(x1, x2), max(x1, x2)
    for tx in range(start, end + 1):
        for dy in (0, 1):
            if 1 <= y + dy < len(grid) - 1 and 1 <= tx < len(grid[0]) - 1:
                grid[y + dy][tx] = TILE_FLOOR


def _carve_v_corridor(grid: List[List[int]], y1: int, y2: int, x: int) -> None:
    start, end = min(y1, y2), max(y1, y2)
    for ty in range(start, end + 1):
        for dx in (0, 1):
            if 1 <= ty < len(grid) - 1 and 1 <= x + dx < len(grid[0]) - 1:
                grid[ty][x + dx] = TILE_FLOOR


def _surround_floors_with_walls(grid: List[List[int]]) -> None:
    height = len(grid)
    width = len(grid[0])
    for ty in range(height):
        for tx in range(width):
            if grid[ty][tx] == TILE_VOID:
                # Check 8-neighborhood for any floor tile
                near_floor = False
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = ty + dy, tx + dx
                        if 0 <= ny < height and 0 <= nx < width:
                            if grid[ny][nx] in (TILE_FLOOR, TILE_STAIRS_DOWN):
                                near_floor = True
                                break
                    if near_floor:
                        break
                if near_floor:
                    grid[ty][tx] = TILE_WALL


def generate_dungeon(
    floor_num: int, seed: Optional[int] = None
) -> Dungeon:
    """Generate a procedural dungeon layout for the given floor."""
    rng = random.Random(seed)
    width = DUNGEON_WIDTH
    height = DUNGEON_HEIGHT
    grid = [[TILE_VOID for _ in range(width)] for _ in range(height)]
    explored = [[False for _ in range(width)] for _ in range(height)]

    if floor_num >= BOSS_FLOOR:
        return _generate_boss_floor(floor_num, width, height, grid, explored, rng)

    rooms: List[Room] = []
    target_rooms = min(13, 7 + floor_num)
    max_attempts = 160

    for _ in range(max_attempts):
        if len(rooms) >= target_rooms:
            break
        w = rng.randint(6, 11)
        h = rng.randint(6, 10)
        x = rng.randint(3, width - w - 4)
        y = rng.randint(3, height - h - 4)
        candidate = Room(x=x, y=y, w=w, h=h)
        if any(candidate.intersects(existing, padding=2) for existing in rooms):
            continue
        _carve_room(grid, candidate)
        rooms.append(candidate)

    # Guarantee at least 5 rooms even if random placement was tight
    if len(rooms) < 4:
        fallback_coords = [(4, 4, 8, 7), (20, 5, 9, 8), (35, 6, 8, 8), (22, 22, 10, 9)]
        for fx, fy, fw, fh in fallback_coords:
            candidate = Room(x=fx, y=fy, w=fw, h=fh)
            if not any(candidate.intersects(r, padding=1) for r in rooms):
                _carve_room(grid, candidate)
                rooms.append(candidate)

    # Connect rooms via minimum-spanning-like chain + extra loop connections
    for i in range(1, len(rooms)):
        cx1, cy1 = rooms[i - 1].center_tile
        cx2, cy2 = rooms[i].center_tile
        if rng.random() < 0.5:
            _carve_h_corridor(grid, cx1, cx2, cy1)
            _carve_v_corridor(grid, cy1, cy2, cx2)
        else:
            _carve_v_corridor(grid, cy1, cy2, cx1)
            _carve_h_corridor(grid, cx1, cx2, cy2)

    # Add 1-2 extra loops for tactical navigation
    if len(rooms) >= 5:
        for _ in range(2):
            r_a, r_b = rng.sample(rooms, 2)
            cx1, cy1 = r_a.center_tile
            cx2, cy2 = r_b.center_tile
            _carve_h_corridor(grid, cx1, cx2, cy1)
            _carve_v_corridor(grid, cy1, cy2, cx2)

    rooms[0].room_type = "start"
    rooms[0].cleared = True

    # Pick the room farthest from start as the stairs room
    start_cx, start_cy = rooms[0].center_tile
    exit_room_idx = max(
        range(1, len(rooms)),
        key=lambda idx: math.hypot(
            rooms[idx].center_tile[0] - start_cx,
            rooms[idx].center_tile[1] - start_cy,
        ),
    )
    rooms[exit_room_idx].room_type = "exit"
    stairs_tx, stairs_ty = rooms[exit_room_idx].center_tile
    grid[stairs_ty][stairs_tx] = TILE_STAIRS_DOWN

    _surround_floors_with_walls(grid)

    enemy_spawns: List[EnemySpawnSpec] = []
    pickup_spawns: List[PickupSpawnSpec] = []

    # Populate enemies and health pickups
    enemy_pool = _get_enemy_pool_for_floor(floor_num)
    for idx, room in enumerate(rooms):
        if idx == 0:
            continue

        min_enemies = 2 if floor_num == 1 else 2 + (floor_num // 2)
        max_enemies = 3 + floor_num
        count = rng.randint(min_enemies, max_enemies)

        placed_positions: List[Tuple[float, float]] = []
        if idx == exit_room_idx:
            placed_positions.append(room.center_px)

        for _ in range(count):
            etype = rng.choice(enemy_pool)
            for _attempt in range(20):
                px, py = room.random_floor_pixel(rng, margin=1)
                if all(math.hypot(px - ox, py - oy) >= TILE_SIZE * 0.9 for ox, oy in placed_positions):
                    placed_positions.append((px, py))
                    enemy_spawns.append(
                        EnemySpawnSpec(enemy_type=etype, x=px, y=py, room_index=idx)
                    )
                    break

        # Spawn health pickups in some rooms (guaranteed at least 2 per floor)
        if rng.random() < 0.45:
            hx, hy = room.random_floor_pixel(rng, margin=1)
            pickup_spawns.append(PickupSpawnSpec(pickup_type="health", x=hx, y=hy))

    while len(pickup_spawns) < 2 and len(rooms) > 1:
        r = rng.choice(rooms[1:])
        hx, hy = r.random_floor_pixel(rng, margin=1)
        pickup_spawns.append(PickupSpawnSpec(pickup_type="health", x=hx, y=hy))

    dungeon = Dungeon(
        floor_num=floor_num,
        width=width,
        height=height,
        grid=grid,
        rooms=rooms,
        explored=explored,
        player_start=rooms[0].center_px,
        stairs_tile=(stairs_tx, stairs_ty),
        stairs_unlocked=True,
        enemy_spawns=enemy_spawns,
        pickup_spawns=pickup_spawns,
    )
    dungeon.reveal_around(*dungeon.player_start)
    return dungeon


def _generate_boss_floor(
    floor_num: int,
    width: int,
    height: int,
    grid: List[List[int]],
    explored: List[List[bool]],
    rng: random.Random,
) -> Dungeon:
    """Create the Floor 5 Obsidian Sanctum boss arena."""
    antechamber = Room(x=width // 2 - 4, y=height - 11, w=8, h=7, room_type="start", cleared=True)
    arena = Room(x=width // 2 - 11, y=6, w=22, h=18, room_type="boss")

    _carve_room(grid, antechamber)
    _carve_room(grid, arena)
    _carve_v_corridor(grid, arena.bottom - 1, antechamber.y + 1, width // 2 - 1)

    # Add 4 tactical pillars inside the boss arena for cover against projectiles
    pillar_offsets = [(-5, -4), (4, -4), (-5, 3), (4, 3)]
    acx, acy = arena.center_tile
    for dx, dy in pillar_offsets:
        px, py = acx + dx, acy + dy
        for oy in range(2):
            for ox in range(2):
                grid[py + oy][px + ox] = TILE_WALL

    _surround_floors_with_walls(grid)

    boss_x, boss_y = arena.center_px
    enemy_spawns = [
        EnemySpawnSpec(enemy_type="boss", x=boss_x, y=boss_y - TILE_SIZE * 2, room_index=1),
    ]

    # Place health pickups in the antechamber and corners of the arena
    pickup_spawns = [
        PickupSpawnSpec(
            pickup_type="health",
            x=(antechamber.x + 1.5) * TILE_SIZE,
            y=(antechamber.y + 1.5) * TILE_SIZE,
        ),
        PickupSpawnSpec(
            pickup_type="health",
            x=(arena.x + 2.5) * TILE_SIZE,
            y=(arena.bottom - 2.5) * TILE_SIZE,
        ),
        PickupSpawnSpec(
            pickup_type="health",
            x=(arena.right - 2.5) * TILE_SIZE,
            y=(arena.bottom - 2.5) * TILE_SIZE,
        ),
    ]

    rooms = [antechamber, arena]
    dungeon = Dungeon(
        floor_num=floor_num,
        width=width,
        height=height,
        grid=grid,
        rooms=rooms,
        explored=explored,
        player_start=antechamber.center_px,
        stairs_tile=None,
        stairs_unlocked=False,
        enemy_spawns=enemy_spawns,
        pickup_spawns=pickup_spawns,
    )
    dungeon.reveal_around(*dungeon.player_start, radius_tiles=10)
    return dungeon


def _get_enemy_pool_for_floor(floor_num: int) -> List[str]:
    """Return weighted enemy types based on dungeon floor progression."""
    if floor_num == 1:
        return ["slime", "slime", "slime", "cultist", "brute"]
    if floor_num == 2:
        return ["slime", "slime", "cultist", "cultist", "brute"]
    if floor_num == 3:
        return ["slime", "cultist", "cultist", "brute", "brute"]
    return ["slime", "cultist", "cultist", "brute", "brute", "brute"]
