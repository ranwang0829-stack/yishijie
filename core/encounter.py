"""Encounter quest module: stranger-interaction quests and storyline system."""

import random
import uuid
from datetime import datetime, timedelta
from typing import Any

from .config import load_json, save_json, is_in_idle_window
from .task_manager import load_tasks, save_tasks, get_user_state, save_user_state


def _now() -> datetime:
    return datetime.now()


def _iso(dt: datetime) -> str:
    return dt.isoformat()


# ── encounter on/off ─────────────────────────────────────────────────────────


def encounter_enabled() -> bool:
    cfg = load_json("config.json")
    return cfg.get("encounter_enabled", False)


def set_encounter_enabled(on: bool) -> None:
    cfg = load_json("config.json")
    cfg["encounter_enabled"] = on
    save_json("config.json", cfg)
    status = "开启" if on else "关闭"
    print(f"✓ 奇遇推送已{status}。")


# ── encounter generation ────────────────────────────────────────────────────


def generate_encounter(location_hint: str = "") -> dict[str, Any] | None:
    """Generate an encounter quest from story templates.

    Args:
        location_hint: Optional location to bias encounter generation.
    """
    state = get_user_state()
    courage = state.get("social_courage", 3)

    if courage < 3:
        print("⚠ 社交勇气不足(需要≥3)，奇遇任务生成受限。")
        return None

    templates = load_json("story_templates.json")
    if not templates:
        print("✗ 没有可用的故事模板。")
        return None

    # Pick a template — prefer ones that have been started
    active_storylines = load_json("storylines.json")
    active_ids = {s["story_id"] for s in active_storylines}

    # Templates with active storylines get priority
    prioritized = [t for t in templates if t["id"] in active_ids]
    if prioritized:
        template = random.choice(prioritized)
    else:
        template = random.choice(templates)

    # Find the current chapter
    storyline_id = template["id"]
    current_chapter = 0
    for sl in active_storylines:
        if sl["story_id"] == storyline_id:
            current_chapter = sl.get("current_chapter", 0)
            break

    chapters = template.get("chapters", [])
    if current_chapter >= len(chapters):
        print(f"✓ 故事线「{template['title']}」所有章节已完成！")
        return None

    chapter = chapters[current_chapter]

    # Check if there's already an active encounter for this chapter
    existing = [t for t in load_tasks() if t.get("storyline_id") == storyline_id and t.get("chapter") == current_chapter and t.get("status") == "active"]
    if existing:
        print(f"⚠ 故事线「{template['title']}」第{current_chapter + 1}章已有活跃的奇遇任务。")
        return existing[0]

    # Build encounter task
    time_window_start = _now()
    time_window_end = _now() + timedelta(days=random.randint(1, 3))

    name = f"奇遇「{template['title']}」第{current_chapter + 1}章: {chapter['title']}"

    task = {
        "id": str(uuid.uuid4())[:8],
        "type": "encounter",
        "name": name,
        "description": chapter.get("backstory", ""),
        "condition": chapter.get("minimum_interaction", "完成互动"),
        "exp": chapter.get("reward_exp", 30),
        "gold": chapter.get("reward_gold", 20),
        "estimated_minutes": random.randint(10, 30),
        "walk_distance_m": random.randint(0, 500),
        "backstory": chapter.get("backstory", ""),
        "time_window_start": _iso(time_window_start),
        "time_window_end": _iso(time_window_end),
        "likely_appearance": chapter.get("likely_appearance", ""),
        "suggested_opener": chapter.get("suggested_opener", ""),
        "minimum_interaction": chapter.get("minimum_interaction", ""),
        "storyline_id": storyline_id,
        "chapter": current_chapter,
        "chapter_title": chapter.get("title", ""),
        "expires_at": _iso(time_window_end),
        "status": "active",
        "created_at": _iso(_now()),
        "completed_at": None,
        "place": location_hint or "随机地点",
    }

    if is_in_idle_window():
        task["gold"] = int(task["gold"] * 1.15)

    tasks = load_tasks()
    tasks.append(task)
    save_tasks(tasks)

    return task


# ── complete encounter ──────────────────────────────────────────────────────


def complete_encounter(task_id: str) -> dict[str, Any] | None:
    """Complete an encounter quest and advance storyline if applicable."""
    tasks = load_tasks()
    task = None
    for t in tasks:
        if t.get("id") == task_id:
            task = t
            break

    if not task or task.get("type") != "encounter":
        print("✗ 奇遇任务不存在。")
        return None
    if task.get("status") != "active":
        print("✗ 任务已过期或已完成。")
        return None

    task["status"] = "completed"
    task["completed_at"] = _iso(_now())
    save_tasks(tasks)

    # Award
    state = get_user_state()
    state["exp"] = state.get("exp", 0) + task.get("exp", 0)
    state["gold"] = state.get("gold", 0) + task.get("gold", 0)
    save_user_state(state)

    # Advance storyline
    sid = task.get("storyline_id")
    chapter = task.get("chapter", 0)
    storyline_name = task.get("name", "")

    result: dict[str, Any] = {"task": task, "storyline_advanced": False}

    if sid is not None:
        storylines = load_json("storylines.json")
        found = False
        for sl in storylines:
            if sl["story_id"] == sid:
                sl["current_chapter"] = chapter + 1
                sl["completed_chapters"] = sl.get("completed_chapters", [])
                sl["completed_chapters"].append(chapter)
                sl["last_updated"] = _iso(_now())
                found = True
                break
        if not found:
            storylines.append({
                "story_id": sid,
                "story_name": storyline_name.split(":")[0].replace("奇遇「", "").rstrip("」"),
                "current_chapter": chapter + 1,
                "completed_chapters": [chapter],
                "started_at": _iso(_now()),
                "last_updated": _iso(_now()),
            })

        save_json("storylines.json", storylines)

        # Check if story completed
        templates = load_json("story_templates.json")
        for tmpl in templates:
            if tmpl["id"] == sid:
                total = len(tmpl.get("chapters", []))
                if chapter + 1 >= total:
                    result["storyline_completed"] = True
                    result["storyline_name"] = tmpl["title"]
                break

        result["storyline_advanced"] = True
        result["next_chapter"] = chapter + 1

    return result


# ── storyline commands ──────────────────────────────────────────────────────


def storyline_list() -> list[dict[str, Any]]:
    """List all active storylines."""
    storylines = load_json("storylines.json")
    templates = load_json("story_templates.json")
    templates_by_id = {t["id"]: t for t in templates}

    results: list[dict[str, Any]] = []
    for sl in storylines:
        sid = sl["story_id"]
        tmpl = templates_by_id.get(sid, {})
        total = len(tmpl.get("chapters", []))
        current = sl.get("current_chapter", 0)

        next_condition = ""
        if current < total:
            ch = tmpl["chapters"][current]
            next_condition = ch.get("unlock_condition", "自动解锁") or "自动解锁"

        results.append({
            **sl,
            "total_chapters": total,
            "next_chapter_title": tmpl["chapters"][current]["title"] if current < total else "已完成",
            "next_unlock_condition": next_condition,
            "completed": current >= total,
        })

    return results


def storyline_reset(story_id: str) -> bool:
    """Reset a storyline to start over."""
    storylines = load_json("storylines.json")
    before = len(storylines)
    storylines = [s for s in storylines if s["story_id"] != story_id]
    after = len(storylines)
    if before == after:
        print(f"✗ 未找到故事线 ID: {story_id}")
        return False
    save_json("storylines.json", storylines)
    print(f"✓ 故事线已重置。")
    return True
