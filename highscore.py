"""High score persistence manager."""

import json
from pathlib import Path
from typing import Any, Dict

from settings import HIGHSCORE_FILE


DEFAULT_HIGHSCORE_DATA: Dict[str, Any] = {
    "high_score": 0,
    "best_floor": 1,
    "total_runs": 0,
    "victories": 0,
}


def load_highscore_data(filepath: Path = HIGHSCORE_FILE) -> Dict[str, Any]:
    """Load high score stats from disk, returning defaults if missing or invalid."""
    data = dict(DEFAULT_HIGHSCORE_DATA)
    if not filepath.exists():
        return data
    try:
        raw = json.loads(filepath.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            data["high_score"] = max(0, int(raw.get("high_score", 0)))
            data["best_floor"] = max(1, int(raw.get("best_floor", 1)))
            data["total_runs"] = max(0, int(raw.get("total_runs", 0)))
            data["victories"] = max(0, int(raw.get("victories", 0)))
    except (OSError, ValueError, TypeError):
        pass
    return data


def save_highscore_data(
    score: int,
    floor: int,
    victory: bool = False,
    filepath: Path = HIGHSCORE_FILE,
) -> Dict[str, Any]:
    """Update and persist high score data after a run."""
    data = load_highscore_data(filepath)
    is_new_high = score > data["high_score"]
    data["high_score"] = max(data["high_score"], int(score))
    data["best_floor"] = max(data["best_floor"], int(floor))
    data["total_runs"] += 1
    if victory:
        data["victories"] += 1

    try:
        filepath.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass

    result = dict(data)
    result["is_new_high"] = is_new_high
    return result
