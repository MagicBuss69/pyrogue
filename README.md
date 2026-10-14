# Crypts of the Obsidian King

A complete 2D action roguelike built in Python with `pygame`. Battle through procedurally generated dungeon floors, fight three distinct monster archetypes, collect health pickups, defeat **Malakor, the Obsidian King** on Floor 5, and track your all-time high score.

## Features

- **Main Menu & High Score Persistence**: View your all-time high score, best floor reached, total expeditions, and victories (saved automatically to `highscore.json`).
- **Procedural Dungeon Generation**: Floors 1–4 generate interconnected rooms, corridors, fog-of-war minimap exploration, health pickups, enemy squads, and descending stairs.
- **Player Combat & Movement**:
  - Smooth 8-directional movement with wall-sliding collision (`WASD` or Arrow keys).
  - Directional crescent sword slash (`Left Click`, `SPACE`, or `J`) that damages enemies and can deflect enemy projectiles.
  - Invulnerable evasion dash (`SHIFT`, `Right Click`, or `K`).
- **3 Distinct Enemy Types**:
  1. **Venom Slime**: Compresses and executes rapid hop-lunges toward the player.
  2. **Void Cultist**: Kites at medium range, strafes, and fires arcane bolts when in line of sight.
  3. **Bone Juggernaut**: Heavy armored brute that stalks the player, telegraphs a windup ring, and bull-rushes at high speed.
- **Floor 5 Boss Encounter**: **Malakor, the Obsidian King** in a custom pillared sanctum with a two-phase AI featuring aimed fan volleys, radial fire novas, obsidian charges, and slime minion summons.
- **Health Pickups**: Found in dungeon rooms and occasionally dropped by slain monsters to restore HP and award bonus score.
- **Game Over & Victory Screens**: Full run summary with instant replay (`ENTER` / `R`) or return to the Main Menu (`M`).

## Project Structure

- `main.py` — Entry point, game loop, input handling, and state transitions (`MENU`, `PLAYING`, `GAME_OVER`, `VICTORY`).
- `settings.py` — Screen configuration, gameplay constants, tuning parameters, and color palette.
- `dungeon.py` — Procedural room & corridor generator, line-of-sight raymarching, and wall-sliding physics.
- `entities.py` — `Player`, `Enemy` (3 monster types + Floor 5 Boss), `Projectile`, `HealthPickup`, `Particle`, and `FloatingText`.
- `ui.py` — 2D procedural sprite rendering, camera tracking & screen shake, HUD, minimap, and menu overlays.
- `highscore.py` — JSON-based high score loading and saving (`highscore.json`).

## How to Run

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Launch the game:

```bash
python3 main.py
```

Optional flags:
- `python3 main.py --seed 12345` — Run with a deterministic dungeon seed.
- `python3 main.py --smoke-test` — Run a quick automated verification across all 5 floors.

## Controls

| Action | Primary Key / Mouse | Alternate Key |
| :--- | :--- | :--- |
| Move | `W` `A` `S` `D` | Arrow Keys |
| Sword Attack | Left Mouse Button | `SPACE` or `J` |
| Dash | `Left Shift` / `Right Shift` | Right Mouse Button or `K` |
| Start / Confirm | `ENTER` or `SPACE` | Left Click |
| Return to Menu / Quit | `M` / `ESC` | — |
