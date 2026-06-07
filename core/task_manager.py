"""Task generation, completion, expiration, and state management."""

import random
import uuid
from datetime import datetime, timedelta
from typing import Any

from .config import load_json, save_json

# ── helpers ──────────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now()


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _pick(words: list[str]) -> str:
    return random.choice(words) if words else ""


def _anime() -> dict[str, Any]:
    return load_json("anime_words.json")


def _format_task_name(task_type: str, target: str) -> str:
    """Generate an anime-style task name."""
    w = _anime()
    prefix = _pick(w.get("task_prefixes", ["委托"]))
    loc_desc = _pick(w.get("location_descriptors", [""]))
    emo = _pick(w.get("emotions", [""]))
    parts = [prefix]
    if loc_desc:
        parts.append(loc_desc)
    parts.append(f"「{target}」")
    if emo:
        parts.append(f"({emo})")
    return " ".join(parts)


# ── state helpers ────────────────────────────────────────────────────────────


def get_user_state() -> dict[str, Any]:
    return load_json("user_state.json")


def save_user_state(s: dict[str, Any]) -> None:
    save_json("user_state.json", s)


def get_preferences() -> dict[str, Any]:
    return load_json("preferences.json")


def get_places() -> list[dict[str, Any]]:
    return load_json("places.json")


def get_npcs() -> list[dict[str, Any]]:
    return load_json("npcs.json")


def get_anime_words() -> dict[str, Any]:
    return load_json("anime_words.json")


# ── task CRUD ────────────────────────────────────────────────────────────────


def load_tasks() -> list[dict[str, Any]]:
    return load_json("tasks.json")


def save_tasks(tasks: list[dict[str, Any]]) -> None:
    save_json("tasks.json", tasks)


def _expire_old_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mark tasks past their expires_at as expired."""
    now = _now()
    for t in tasks:
        if t.get("status") != "expired" and t.get("expires_at"):
            expires = datetime.fromisoformat(t["expires_at"])
            if expires < now:
                t["status"] = "expired"
    return tasks


def list_active_tasks() -> list[dict[str, Any]]:
    """Return unexpired, uncompleted tasks sorted by remaining time."""
    tasks = _expire_old_tasks(load_tasks())
    save_tasks(tasks)
    active = [t for t in tasks if t.get("status") == "active"]
    active.sort(key=lambda t: t.get("expires_at", ""))
    return active


def list_expired_tasks() -> list[dict[str, Any]]:
    """Return expired tasks."""
    _expire_old_tasks(load_tasks())
    tasks = load_tasks()
    return [t for t in tasks if t.get("status") == "expired"]


def get_task_by_id(task_id: str) -> dict[str, Any] | None:
    tasks = load_tasks()
    for t in tasks:
        if t.get("id") == task_id:
            return t
    return None


# ── daily task generation ────────────────────────────────────────────────────


def _level_for_exp(exp: int) -> int:
    """Calculate level from cumulative exp. Staircase formula."""
    level = 1
    threshold = 50
    acc = 0
    while exp >= acc + threshold:
        acc += threshold
        level += 1
        threshold = int(threshold * 1.5)
    return level


def _title_for_level(level: int) -> str:
    titles = _anime().get("rank_titles", {})
    return titles.get(str(min(level, 8)), "传说之上")


def generate_daily_tasks() -> list[dict[str, Any]]:
    """Generate 1~4 daily tasks based on current user state, places, and NPCs."""

    state = get_user_state()
    prefs = get_preferences()
    places = get_places()
    npcs: list[dict[str, Any]] = get_npcs()
    words = get_anime_words()

    mood = state.get("mood", 3)
    available = state.get("available_minutes", 60)
    max_dist = state.get("max_walk_distance", 2000)
    courage = state.get("social_courage", 3)
    blockers = state.get("blockers", [])
    forbidden = prefs.get("forbidden_actions", [])
    preferred = prefs.get("preferred_task_types", [])

    # Filter places by distance
    reachable = [p for p in places if p.get("distance_m", 9999) <= max_dist]
    if not reachable:
        reachable = places  # fallback: show all

    # Decide task count: mood higher → more tasks
    count = max(1, min(4, mood))
    if blockers:
        count = max(1, count - len(blockers))

    generated: list[dict[str, Any]] = []

    for _ in range(count):
        place = random.choice(reachable) if reachable else None
        npc = None
        # Pick NPC if courage allows and there are NPCs at this place
        if place and courage >= 2:
            place_npcs = [n for n in npcs if n.get("location") == place.get("name")]
            if place_npcs:
                npc = random.choice(place_npcs)

        task_type = _pick_task_type(courage, preferred, forbidden)

        task = _build_task(task_type, place, npc, state, words)
        if task:
            generated.append(task)

    # Replace old active daily tasks
    tasks = _expire_old_tasks(load_tasks())
    tasks = [t for t in tasks if t.get("status") != "active" or t.get("type") not in ("daily", None)]
    tasks.extend(generated)
    save_tasks(tasks)

    return generated


def _pick_task_type(courage: int, preferred: list[str], forbidden: list[str]) -> str:
    """Choose a task type respecting user constraints."""
    pool: dict[str, int] = {
        "dialogue": 2,
        "explore": 2,
        "observe": 2,
        "photo": 1,
        "smile": 1,
        "gesture": 1,
    }

    if courage <= 2:
        pool["dialogue"] = 0  # avoid forced convo

    # Remove forbidden
    for f in forbidden:
        f_lower = f.lower()
        for key in list(pool):
            if key in f_lower or f_lower in key:
                pool[key] = 0

    # Boost preferred
    for p in preferred:
        p_lower = p.lower()
        for key in pool:
            if key in p_lower or p_lower in key:
                pool[key] += 3

    valid = [k for k, v in pool.items() if v > 0]
    if not valid:
        valid = ["observe"]
    return random.choice(valid)


def _build_task(
    task_type: str,
    place: dict[str, Any] | None,
    npc: dict[str, Any] | None,
    state: dict[str, Any],
    words: dict[str, Any],
) -> dict[str, Any] | None:
    """Build a single task of the given type."""
    if not place:
        return None

    name = ""
    action_desc = ""
    condition = ""
    exp_reward = 10
    gold_reward = 5
    time_est = 5  # minutes
    distance = place.get("distance_m", 0)

    npc_title = _pick(words.get("npc_titles", [])) or "村人"

    if task_type == "dialogue" and npc:
        name = _format_task_name("dialogue", npc["name"])
        tmpl = _pick(npc.get("interaction_templates", ["和{npc}交谈"]))
        action_desc = tmpl.replace("{npc}", npc["name"])
        if "{drink}" in action_desc:
            action_desc = action_desc.replace("{drink}", random.choice(["拿铁", "美式", "抹茶拿铁", "热可可"]))
        condition = f"与「{npc['name']}」完成一次对话"
        exp_reward = 20
        gold_reward = 10
        time_est = random.randint(3, 10)

    elif task_type == "explore":
        name = _format_task_name("explore", place["name"])
        action_desc = f"前往「{place['name']}」进行探索。{place.get('memo', '')}"
        condition = f"到达「{place['name']}」并停留至少5分钟"
        exp_reward = 25
        gold_reward = 15
        time_est = random.randint(10, 20)

    elif task_type == "observe":
        name = _format_task_name("observe", place["name"])
        targets = ["一棵有趣的树", "路人的穿搭", "建筑的细节", "天空的颜色", "身边的声音"]
        obs = random.choice(targets)
        action_desc = f"在「{place['name']}」附近，静下心来观察：{obs}"
        condition = f"记录一个你观察到的细节（文字或照片）"
        exp_reward = 15
        gold_reward = 5
        time_est = random.randint(5, 10)

    elif task_type == "photo":
        name = _format_task_name("photo", place["name"])
        action_desc = f"在「{place['name']}」找一个有趣的角落拍一张照片"
        condition = "拍摄一张照片并保存"
        exp_reward = 15
        gold_reward = 10
        time_est = random.randint(2, 5)

    elif task_type == "smile":
        name = _format_task_name("smile", place["name"])
        action_desc = f"在「{place['name']}」对遇到的一个人微笑"
        condition = "对一个人微笑（对方看到即可，无需互动）"
        exp_reward = 10
        gold_reward = 5
        time_est = random.randint(1, 3)

    elif task_type == "gesture":
        name = _format_task_name("gesture", place["name"])
        gestures = ["帮忙扶一下门", "捡起地上的垃圾丢入垃圾桶", "给路边的小猫一个善意的眼神", "对服务人员说一声谢谢"]
        g = random.choice(gestures)
        action_desc = f"在「{place['name']}」做一个善意的动作：{g}"
        condition = f"完成动作：{g}"
        exp_reward = 10
        gold_reward = 5
        time_est = random.randint(1, 5)

    else:
        return None

    # Adjust reward based on user state
    if state.get("reward_sensitive", False):
        gold_reward = int(gold_reward * (1 + state.get("level", 1) * 0.1))

    expires_hours = random.uniform(2, 6)
    expires_at = _now() + timedelta(hours=expires_hours)

    return {
        "id": str(uuid.uuid4())[:8],
        "type": task_type,
        "name": name,
        "description": action_desc,
        "condition": condition,
        "exp": exp_reward,
        "gold": gold_reward,
        "estimated_minutes": time_est,
        "walk_distance_m": distance,
        "place": place["name"],
        "npc": npc["name"] if npc else None,
        "expires_at": _iso(expires_at),
        "status": "active",
        "created_at": _iso(_now()),
        "completed_at": None,
    }


# ── task actions ─────────────────────────────────────────────────────────────


def complete_task(task_id: str) -> dict[str, Any] | None:
    """Complete a task, award exp/gold, check level up."""
    tasks = _expire_old_tasks(load_tasks())

    task = None
    for t in tasks:
        if t.get("id") == task_id:
            task = t
            break

    if task is None:
        print("✗ 任务不存在。")
        return None
    if task.get("status") == "expired":
        print("✗ 该任务已过期，无法完成。")
        return None
    if task.get("status") == "completed":
        print("✗ 该任务已经完成过了。")
        return None

    # Also update npc last_interaction
    npc_name = task.get("npc")
    if npc_name:
        npcs = get_npcs()
        for n in npcs:
            if n["name"] == npc_name:
                n["last_interaction"] = _now().strftime("%Y-%m-%d")
                break
        save_json("npcs.json", npcs)

    task["status"] = "completed"
    task["completed_at"] = _iso(_now())
    save_tasks(tasks)

    # Award
    state = get_user_state()
    old_level = state.get("level", 1)
    state["exp"] = state.get("exp", 0) + task.get("exp", 0)
    state["gold"] = state.get("gold", 0) + task.get("gold", 0)

    new_level = _level_for_exp(state["exp"])
    state["level"] = new_level
    state["title"] = _title_for_level(new_level)

    leveled_up = new_level > old_level
    if leveled_up:
        state["current_hp"] = 100  # full heal on level up

    save_user_state(state)

    return {
        "task": task,
        "leveled_up": leveled_up,
        "new_level": new_level,
        "new_title": state["title"],
        "old_level": old_level,
    }


def expire_task(task_id: str) -> bool:
    """Manually expire a task."""
    tasks = load_tasks()
    for t in tasks:
        if t.get("id") == task_id and t.get("status") == "active":
            t["status"] = "expired"
            save_tasks(tasks)
            return True
    return False


def cleanup_old_expired(days: int = 3) -> int:
    """Remove expired tasks older than `days` days. Returns count removed."""
    tasks = load_tasks()
    cutoff = _now() - timedelta(days=days)
    before = len(tasks)
    tasks = [
        t
        for t in tasks
        if not (
            t.get("status") == "expired"
            and t.get("expires_at")
            and datetime.fromisoformat(t["expires_at"]) < cutoff
        )
    ]
    after = len(tasks)
    save_tasks(tasks)
    return before - after


# ── data management commands ─────────────────────────────────────────────────


def add_place_interactive() -> None:
    """Interactively add a new place."""
    places = get_places()
    print("── 添加新地点 ──")
    name = input("地点名称: ").strip()
    if not name:
        print("已取消。")
        return
    ptype = input("类型(cafe/park/office/shop/other): ").strip() or "other"
    dist_str = input("距离(米): ").strip()
    try:
        dist = int(dist_str) if dist_str else 0
    except ValueError:
        dist = 0
    npcs_str = input("已知NPC(逗号分隔): ").strip()
    known_npcs = [n.strip() for n in npcs_str.split(",")] if npcs_str else []
    memo = input("备注: ").strip()

    places.append({
        "name": name,
        "type": ptype,
        "distance_m": dist,
        "known_npcs": known_npcs,
        "memo": memo,
    })
    save_json("places.json", places)
    print(f"✓ 地点「{name}」已添加。")


def add_npc_interactive() -> None:
    """Interactively add a new NPC."""
    npcs = get_npcs()
    print("── 添加新NPC ──")
    name = input("NPC名称: ").strip()
    if not name:
        print("已取消。")
        return
    location = input("所在地点: ").strip()
    facts_str = input("已知事实(逗号分隔): ").strip()
    known_facts = [f.strip() for f in facts_str.split(",")] if facts_str else []
    templates_str = input("对话模板(逗号分隔): ").strip()
    templates = [t.strip() for t in templates_str.split(",")] if templates_str else ["和{npc}聊聊"]

    npcs.append({
        "name": name,
        "location": location,
        "known_facts": known_facts,
        "interaction_templates": templates,
        "last_interaction": "",
    })
    save_json("npcs.json", npcs)
    print(f"✓ NPC「{name}」已添加。")


def set_preference_interactive() -> None:
    """Interactively set a preference value."""
    prefs = get_preferences()
    print("── 修改偏好 ──")
    print("可用字段: dislike_topics, like_topics, forbidden_actions, preferred_task_types, reward_sensitive")
    field = input("要修改的字段: ").strip()
    if field not in prefs:
        print("✗ 无效字段。")
        return
    if field == "reward_sensitive":
        val = input("值(true/false): ").strip().lower()
        prefs[field] = val == "true"
    else:
        val = input("新值(逗号分隔): ").strip()
        prefs[field] = [v.strip() for v in val.split(",")] if val else []
    save_json("preferences.json", prefs)
    print(f"✓ {field} 已更新。")


def set_state_interactive() -> None:
    """Interactively update user state (mood, time, courage, etc.)."""
    state = get_user_state()
    print("── 更新勇者状态 ──")
    print("(直接回车跳过不修改)")

    old_mood = state.get("mood", 3)

    msg = f"心情 (1-5) [{state.get('mood', 3)}]: "
    v = input(msg).strip()
    if v:
        state["mood"] = max(1, min(5, int(v)))

    msg = f"今日可用时间/分钟 [{state.get('available_minutes', 60)}]: "
    v = input(msg).strip()
    if v:
        state["available_minutes"] = int(v)

    msg = f"最大步行距离/米 [{state.get('max_walk_distance', 2000)}]: "
    v = input(msg).strip()
    if v:
        state["max_walk_distance"] = int(v)

    msg = f"社交勇气 (1-5) [{state.get('social_courage', 3)}]: "
    v = input(msg).strip()
    if v:
        state["social_courage"] = max(1, min(5, int(v)))

    msg = f"阻塞因素(逗号分隔) [{','.join(state.get('blockers', []))}]: "
    v = input(msg).strip()
    if v:
        state["blockers"] = [b.strip() for b in v.split(",") if b.strip()]
    elif v == "":
        state["blockers"] = []

    save_user_state(state)
    print(f"✓ 状态已更新。情绪：{state['mood']}，可用时间：{state['available_minutes']}分钟")

    # Check for mood improvement → trigger encouragement (handled by caller)


# ── task display ─────────────────────────────────────────────────────────────


def format_task(t: dict[str, Any]) -> str:
    """Pretty-print a single task."""
    remaining = ""
    if t.get("expires_at") and t.get("status") == "active":
        expires = datetime.fromisoformat(t["expires_at"])
        left = expires - _now()
        if left.total_seconds() > 0:
            h = int(left.total_seconds() // 3600)
            m = int((left.total_seconds() % 3600) // 60)
            remaining = f"剩余 {h}小时{m}分钟"
        else:
            remaining = "已过期"

    status_icon = {"active": "⚡", "completed": "✅", "expired": "💀"}.get(t.get("status", ""), "❓")

    lines = [
        f"{status_icon} [{t.get('id', '?')}] {t.get('name', '未命名')}",
        f"   类型: {t.get('type', '通用')} | 地点: {t.get('place', '任意')} | NPC: {t.get('npc', '无')}",
        f"   描述: {t.get('description', '')}",
        f"   条件: {t.get('condition', '')}",
        f"   奖励: {t.get('exp', 0)} EXP + {t.get('gold', 0)} 金币 | 预估: {t.get('estimated_minutes', 0)}分钟 | 距离: {t.get('walk_distance_m', 0)}m",
        f"   状态: {t.get('status', '?')} | {remaining}",
    ]
    return "\n".join(lines)
