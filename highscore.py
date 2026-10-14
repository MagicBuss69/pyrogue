"""High score, run statistics, and Steam-style achievement persistence manager."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from settings import HIGHSCORE_FILE


DEFAULT_HIGHSCORE_DATA: Dict[str, Any] = {
    "high_score": 0,
    "best_floor": 1,
    "total_runs": 0,
    "victories": 0,
    "total_kills": 0,
    "achievements": [],
}


def load_highscore_data(filepath: Path = HIGHSCORE_FILE) -> Dict[str, Any]:
    """Load high score stats and unlocked achievements from disk."""
    data = {
        "high_score": 0,
        "best_floor": 1,
        "total_runs": 0,
        "victories": 0,
        "total_kills": 0,
        "achievements": [],
    }
    if not filepath.exists():
        return data
    try:
        raw = json.loads(filepath.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            data["high_score"] = max(0, int(raw.get("high_score", 0)))
            data["best_floor"] = max(1, int(raw.get("best_floor", 1)))
            data["total_runs"] = max(0, int(raw.get("total_runs", 0)))
            data["victories"] = max(0, int(raw.get("victories", 0)))
            data["total_kills"] = max(0, int(raw.get("total_kills", 0)))
            ach = raw.get("achievements", [])
            if isinstance(ach, list):
                data["achievements"] = [str(a) for a in ach]
    except (OSError, ValueError, TypeError):
        pass
    return data


def save_highscore_data(
    score: int,
    floor: int,
    victory: bool = False,
    kills: int = 0,
    unlocked_achievements: Optional[List[str]] = None,
    filepath: Path = HIGHSCORE_FILE,
) -> Dict[str, Any]:
    """Update and persist high score data and achievements after a run."""
    data = load_highscore_data(filepath)
    is_new_high = score > data["high_score"]
    data["high_score"] = max(data["high_score"], int(score))
    data["best_floor"] = max(data["best_floor"], int(floor))
    data["total_runs"] += 1
    data["total_kills"] = data.get("total_kills", 0) + max(0, int(kills))
    if victory:
        data["victories"] += 1

    existing_ach = set(data.get("achievements", []))
    if unlocked_achievements:
        for ach_id in unlocked_achievements:
            existing_ach.add(str(ach_id))
    if score >= 1500:
        existing_ach.add("centurion")
    if floor >= 5:
        existing_ach.add("deep_delver")
    if victory:
        existing_ach.add("kingslayer")
    data["achievements"] = sorted(existing_ach)

    try:
        filepath.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass

    result = dict(data)
    result["is_new_high"] = is_new_high
    return result
