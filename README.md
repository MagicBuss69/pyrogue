# Crypts of the Obsidian King — Steam Edition (v2.0)

A complete, Steam-ready 2D action roguelike built in Python with `pygame`. Descend 5 procedural floors of the Obsidian Crypts, unleash 4 arcane abilities, collect powerful Relics on level-up, unlock Steam-style achievements, and vanquish **Malakor, the Obsidian King** on Floor 5.

## What's New in v2.0 (Steam Launch Overhaul)

- **Fixed Mouse & Aiming (Zero Mouse Required!)**:
  - The window never traps or grabs your cursor (`pygame.event.set_grab(False)`).
  - **Smart Multi-Modal Aiming**:
    1. **Twin-Stick Arrow Keys**: Press or hold the **Arrow Keys** to aim in any 8-way direction while moving with `WASD`.
    2. **Auto-Target Assist**: Automatically locks onto the nearest monster in melee/mid range so attacks always land cleanly without touching the mouse.
    3. **Movement Aiming**: Faces the direction you move when no enemies are nearby.
    4. **Optional Mouse Aiming**: Only aims toward the mouse cursor when you actively move the mouse.
- **Unique "Obsidian Neon-Noir" Art Style**:
  - 2.5D chiseled obsidian brickwork with bevels, mortar lines, carved glowing runes, and northern wall drop-shadows.
  - Dynamic additive radial lighting on flickering wall sconces/torches, projectiles, stairs, and characters, framed by an atmospheric vignette.
  - Flowing animated cape physics, glowing arcane visor eyes, idle rune-blade rendering, dash afterimages, jagged lightning bolts, and destructible wooden crates.
- **4 Active Player Abilities + 3-Hit Sword Combo**:
  - **Primary Attack (`J` / `SPACE` / Left-Click)**: 3-step crescent blade combo with forward combat lunge; the 3rd hit is a wide golden critical finisher. Deflects enemy projectiles!
  - **Whirlwind Cleave (`Q` / `1` / `U`)**: 360° spinning blade storm that damages all surrounding enemies and shatters incoming projectiles.
  - **Eldritch Nova (`E` / `2` / `I`)**: Fires a ring of 8 piercing arcane lances outward in all directions.
  - **Chain Lightning (`R` / `3` / `O`)**: Calls down high-voltage arcs that jump between up to 4 nearby monsters.
  - **Phantom Dash (`SHIFT` / `K` / Right-Click)**: High-speed invulnerable phase-dash that leaves glowing afterimages and damages enemies you pass through.
- **XP, Level-Up Relic Drafts & Steam Achievements**:
  - Slaying monsters grants XP; leveling up pauses the action to let you draft 1 of 3 **Obsidian Relics** (*Vampiric Obsidian Edge*, *Astral Storm Capacitor*, *Heart of the Colossus*, *Quicksilver Greaves*, *Eldritch Overload Core*).
  - 5 built-in **Steam Achievements** with live in-game unlock toasts and persistence in `highscore.json`.
  - Procedural in-memory retro synth sound effects (`audio.py`) with automatic silent fallback if no audio device is present.

## Project Structure

- `main.py` — Game loop, multi-modal smart aiming, ability execution, combat collision, Relic draft, Pause menu, and state machine.
- `settings.py` — Obsidian Neon-Noir palette, ability tuning, Relic catalog, and Achievement definitions.
- `dungeon.py` — Procedural room & corridor generator, wall torches, breakable crates, blood/rune floor decals, and Floor 5 Boss Sanctum.
- `entities.py` — `Player`, `Enemy` (Venom Slime, Void Cultist, Bone Juggernaut, and Malakor Boss), `Projectile`, `HealthPickup`, `DashAfterimage`, `LightningBoltFX`, and `ShockwaveRingFX`.
- `ui.py` — 2.5D tile & lighting renderer, ability cooldown hotbar, XP/HP HUD, minimap, Relic selection modal, Pause screen, and Main Menu.
- `audio.py` — Zero-dependency procedural sound synthesizer.
- `highscore.py` — Persistent high score, career stats, and achievement storage (`highscore.json`).

## How to Run

```bash
pip install -r requirements.txt
python3 main.py
```

## Controls

| Action | Keyboard (No Mouse Needed) | Alternate / Mouse |
| :--- | :--- | :--- |
| **Move** | `W` `A` `S` `D` | Arrow Keys |
| **Aim Direction** | **Arrow Keys** or Auto-Target | Mouse Cursor |
| **3-Hit Sword Combo** | `SPACE` or `J` | Left Mouse Button |
| **Whirlwind Cleave (AoE)** | `Q` or `1` | `U` |
| **Eldritch Nova (8 Lances)** | `E` or `2` | `I` |
| **Chain Lightning** | `R` or `3` | `O` |
| **Phantom Dash (Dodge)** | `Left Shift` / `Right Shift` | `K` or Right Click |
| **Pause / Resume** | `ESC` or `P` | — |
