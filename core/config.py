"""Configuration and data file loading/saving utilities."""

import json
import os
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent.parent / "data"


def _path(filename: str) -> Path:
    return DATA_DIR / filename


def load_json(filename: str) -> Any:
    """Load a JSON data file. Returns default empty structure if missing."""
    filepath = _path(filename)
    if not filepath.exists():
        _init_defaults(filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filename: str, data: Any) -> None:
    """Save data to a JSON file atomically."""
    filepath = _path(filename)
    os.makedirs(filepath.parent, exist_ok=True)
    tmp = str(filepath) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, filepath)


def _init_defaults(filename: str) -> None:
    """Create default data files if they don't exist."""
    os.makedirs(DATA_DIR, exist_ok=True)

    defaults: dict[str, Any] = {
        "config.json": {
            "ntfy_topic": "",
            "ntfy_server": "https://ntfy.sh",
            "use_osm_api": False,
            "voice": {
                "enabled": True,
                "engine": "pyttsx3",
                "rate": 150,
                "volume": 1.0,
                "voice_id": "",
                "event_filters": ["new_task", "task_expiring", "task_complete", "level_up", "storyline_chapter", "weather", "fun_content"],
            },
            "idle_windows": ["12:00-13:30", "18:00-19:00"],
            "daemon": {"check_interval_minutes": 120, "push_if_tasks_less_than": 2},
            "weather": {"enabled": True, "city": "Beijing"},
            "fun_content": {"enabled": True},
        },
        "places.json": [],
        "npcs.json": [],
        "preferences.json": {
            "dislike_topics": [],
            "like_topics": [],
            "forbidden_actions": [],
            "preferred_task_types": [],
            "reward_sensitive": True,
        },
        "user_state.json": {
            "level": 1,
            "exp": 0,
            "gold": 50,
            "title": "见习勇者",
            "current_hp": 100,
            "mood": 3,
            "available_minutes": 60,
            "max_walk_distance": 2000,
            "social_courage": 3,
            "blockers": [],
        },
        "tasks.json": [],
        "pois.json": [],
        "story_templates.json": [],
        "storylines.json": [],
        "anime_words.json": {
            "task_prefixes": ["王命", "委托", "讨伐", "探索", "试炼", "修行"],
            "npc_titles": ["贤者", "战士", "魔法师", "商人", "情报贩子", "旅人"],
            "action_verbs": ["发动", "触发", "解锁", "觉醒", "习得"],
            "reward_descriptions": ["经验值结晶", "金币袋", "魔石碎片", "祝福之光"],
            "location_descriptors": ["秘境", "隐れ里", "圣域", "迷宫入口", "传送点"],
            "emotions": ["干劲满满", "小鹿乱撞", "心头一暖", "豁然开朗"],
            "rank_titles": {
                "1": "见习勇者",
                "2": "初级冒险者",
                "3": "独当一面的战士",
                "4": "王国骑士",
                "5": "近卫队长",
                "6": "圣殿守护者",
                "7": "传说中的勇者",
                "8": "次元超越者",
            },
        },
    }

    data = defaults.get(filename, [])
    save_json(filename, data)


def get_idle_windows() -> list[tuple[str, str]]:
    """Parse idle window strings into (start, end) tuples."""
    cfg = load_json("config.json")
    windows: list[tuple[str, str]] = []
    for w in cfg.get("idle_windows", []):
        parts = w.split("-")
        if len(parts) == 2:
            windows.append((parts[0].strip(), parts[1].strip()))
    return windows


def is_in_idle_window() -> bool:
    """Check if current time falls within any idle window."""
    from datetime import datetime

    now = datetime.now().strftime("%H:%M")
    for start, end in get_idle_windows():
        if start <= now <= end:
            return True
    return False
