"""Fun content module: anime-style blessings, encouragements, facts, and daily reports."""

import random
from datetime import datetime
from typing import Any

from .config import load_json, save_json
from .task_manager import load_tasks, get_user_state


def get_fun_config() -> dict[str, Any]:
    cfg = load_json("config.json")
    return cfg.get("fun_content", {"enabled": True})


def _pick_unique(key: str, items: list[Any]) -> Any:
    """Pick a random item, avoiding recently used ones. Cycles through all before repeating.

    Args:
        key: Content type key (e.g. 'blessings', 'fun_facts')
        items: List of content items to pick from

    Returns:
        A single item from the list, guaranteed not recently used.
    """
    if not items:
        return None

    hist = load_json("history.json") or {}
    used = set(hist.get(key, {}).get("used", []))

    # Available: items not recently used
    available = [i for i in range(len(items)) if i not in used]

    # If all used, reset cycle
    if not available:
        used = set()
        available = list(range(len(items)))

    # Pick randomly from available
    idx = random.choice(available)
    used.add(idx)

    # Keep only last N to prevent unlimited growth
    # Store as list for JSON
    hist[key] = {"used": list(used)[-30:], "total": len(items)}
    save_json("history.json", hist)

    return items[idx]


def push_morning_blessing() -> bool:
    """Push a morning blessing (once per day). Uses template generator."""
    cfg = get_fun_config()
    if not cfg.get("enabled", True):
        return False

    from .content_gen import generate
    result = generate("blessing")
    if not result:
        return False

    from .notifier import notify_sync as notify
    from .voice import get_voice

    notify("Morning Blessing", result["body"])
    get_voice().say(result["body"][:60], event="fun_content", sync=True)
    return True


def push_encouragement() -> bool:
    """Push a random RPG-style encouragement. Uses template generator."""
    cfg = get_fun_config()
    if not cfg.get("enabled", True):
        return False

    from .content_gen import generate
    result = generate("encouragement")
    if not result:
        return False

    from .notifier import notify_sync as notify
    from .voice import get_voice

    notify("Adventurer's Word", result["body"])
    get_voice().say(result["body"][:60], event="fun_content", sync=True)
    return True


def push_random_fact() -> bool:
    """Push a fun fact wrapped in anime flavor."""
    cfg = get_fun_config()
    if not cfg.get("enabled", True):
        return False

    words = load_json("anime_words.json")
    facts = words.get("fun_facts", [{"fact": "生活本身就是冒险！", "anime": "这就是勇者の真谛！"}])
    fact = _pick_unique("fun_facts", facts)

    msg = f"📚 {fact['fact']}\n\n💬 {fact['anime']}"

    from .notifier import notify_sync as notify
    from .voice import get_voice

    notify("世界の豆知识", msg)
    get_voice().say(f"豆知识：{fact['fact'][:50]}", event="fun_content", sync=True)

    return True


def push_daily_report() -> bool:
    """Push a daily summary report (勇者日报)."""
    cfg = get_fun_config()
    if not cfg.get("enabled", True):
        return False

    state = get_user_state()
    tasks = load_tasks()

    today = datetime.now().strftime("%Y-%m-%d")
    today_completed = [
        t for t in tasks
        if t.get("status") == "completed" and (t.get("completed_at", "")[:10] == today)
    ]
    today_exp = sum(t.get("exp", 0) for t in today_completed)
    today_gold = sum(t.get("gold", 0) for t in today_completed)

    words = load_json("anime_words.json")
    emotions = words.get("emotions", ["干劲满满"])

    lines = [
        f"━━━ ◈ 勇者日报 ◈ ━━━",
        f"",
        f"📅 {today}",
        f"⚔ {state.get('title', '勇者')} — Lv.{state.get('level', 1)}",
        f"",
        f"📋 今日战果:",
        f"  ✅ 完成任务: {len(today_completed)} 个",
        f"  ⭐ 获得经验: {today_exp} EXP",
        f"  💰 获得金币: {today_gold} G",
        f"",
        f"📊 累积状态:",
        f"  🏆 总EXP: {state.get('exp', 0)}",
        f"  💎 总资产: {state.get('gold', 0)} G",
        f"  ❤ 心情: {state.get('mood', 3)}/5",
    ]

    if today_completed:
        lines.append(f"")
        lines.append(f"🎯 今日亮点任务:")
        for t in today_completed[:3]:
            lines.append(f"  ▸ {t.get('name', '未知任务')} (+{t.get('exp', 0)}EXP)")

    # Add a closing quote
    encouragements = words.get("encouragements", ["明天继续加油！"])
    lines.append(f"")
    closing = _pick_unique("encouragements", encouragements)
    lines.append(f"💬 {closing}")

    msg = "\n".join(lines)

    from .notifier import notify_sync as notify
    from .voice import get_voice

    notify("勇者日报", msg)
    get_voice().say(f"勇者日报：今日完成{len(today_completed)}个任务，获得{today_exp}经验值。", event="fun_content", sync=True)

    return True


def push_bedtime_story() -> bool:
    """Push an isekai-themed bedtime story (for late night)."""
    cfg = get_fun_config()
    if not cfg.get("enabled", True):
        return False

    words = load_json("anime_words.json")
    stories = words.get("bedtime_stories", [])
    if not stories:
        return False

    story = _pick_unique("bedtime_stories", stories)
    msg = f"🌙 {story['title']}\n\n{story['story']}"

    from .notifier import notify_sync as notify
    from .voice import get_voice

    notify(f"Bedtime Story: {story['title']}", msg)
    get_voice().say("", event="fun_content", sync=True)  # Don't voice at night

    return True


def push_npc_spotlight() -> bool:
    """Push a random NPC spotlight from npcs.json."""
    cfg = get_fun_config()
    if not cfg.get("enabled", True):
        return False

    from .config import load_json as _lj
    npcs = _lj("npcs.json")
    if not npcs:
        return False

    npc = _pick_unique("npc_spotlight", npcs)
    facts = npc.get("known_facts", [])
    fact_text = "\n".join(f"  • {f}" for f in facts[:3]) if facts else "  神秘の人物..."

    msg = (
        f"👤 NPC图鉴：{npc['name']}\n\n"
        f"📍 出没地点：{npc.get('location', '未知')}\n"
        f"📝 已知情报：\n{fact_text}\n\n"
        f"💬 上次相遇：{npc.get('last_interaction', '尚未相遇')}"
    )

    from .notifier import notify_sync as notify
    from .voice import get_voice

    notify(f"NPC: {npc['name']}", msg)
    get_voice().say(f"NPC图鉴：{npc['name']}，出没于{npc.get('location', '')}", event="fun_content", sync=True)
    return True


def push_place_discovery() -> bool:
    """Push a random place discovery from places.json."""
    cfg = get_fun_config()
    if not cfg.get("enabled", True):
        return False

    from .config import load_json as _lj
    places = _lj("places.json")
    if not places:
        return False

    place = _pick_unique("place_discovery", places)
    npcs = ", ".join(place.get("known_npcs", [])) or "暂无"
    dist = place.get("distance_m", 0)
    dist_text = f"{dist}m" if dist > 0 else "你所在の位置"

    type_emoji = {"cafe": "☕", "park": "🌳", "office": "🏢", "shop": "🛒", "discovered": "🗺"}
    emoji = type_emoji.get(place.get("type", ""), "📍")

    msg = (
        f"{emoji} 地点发现：{place['name']}\n\n"
        f"🏷 类型：{place.get('type', '未知')}\n"
        f"📏 距离：{dist_text}\n"
        f"👥 已知NPC：{npcs}\n"
        f"📝 备注：{place.get('memo', '等待探索')}"
    )

    from .notifier import notify_sync as notify
    from .voice import get_voice

    notify(f"Place: {place['name']}", msg)
    get_voice().say(f"地点发现：{place['name']}，距离{dist_text}", event="fun_content", sync=True)
    return True


def push_micro_quest() -> bool:
    """Push a random micro quest. Uses template generator."""
    cfg = get_fun_config()
    if not cfg.get("enabled", True):
        return False

    from .content_gen import generate
    result = generate("micro_quest")
    if not result:
        return False

    from .notifier import notify_sync as notify
    from .voice import get_voice

    notify("Micro Quest", result["body"])
    get_voice().say(result["body"][:60], event="fun_content", sync=True)
    return True


def push_life_tip() -> bool:
    """Push a life tip in anime style. Uses template generator."""
    cfg = get_fun_config()
    if not cfg.get("enabled", True):
        return False

    from .content_gen import generate
    result = generate("life_tip")
    if not result:
        return False

    from .notifier import notify_sync as notify
    from .voice import get_voice

    notify("Life Tip", result["body"])
    get_voice().say(result["body"][:60], event="fun_content", sync=True)
    return True


def push_anime_quote() -> bool:
    """Push an anime-style inspirational quote. Uses template generator."""
    cfg = get_fun_config()
    if not cfg.get("enabled", True):
        return False

    from .content_gen import generate
    result = generate("anime_quote")
    if not result:
        return False

    from .notifier import notify_sync as notify
    from .voice import get_voice

    notify("Anime Quote", result["body"])
    get_voice().say(result["body"][:60], event="fun_content", sync=True)
    return True


def push_kingdom_news() -> bool:
    """Push a fictional kingdom news bulletin. Uses template generator."""
    cfg = get_fun_config()
    if not cfg.get("enabled", True):
        return False

    from .content_gen import generate
    result = generate("kingdom_news")
    if not result:
        return False

    from .notifier import notify_sync as notify
    from .voice import get_voice

    notify("Kingdom News", result["body"])
    get_voice().say(result["body"][:60], event="fun_content", sync=True)
    return True


def push_isekai_slang() -> bool:
    """Push an isekai slang term with definition and usage."""
    cfg = get_fun_config()
    if not cfg.get("enabled", True):
        return False
    from .content_gen import generate
    result = generate("isekai_slang")
    if not result:
        return False
    from .notifier import notify_sync as notify
    from .voice import get_voice
    notify("Isekai Slang", result["body"])
    get_voice().say(f"异世界黑话：{result['body'][:50]}", event="fun_content", sync=True)
    return True


def push_isekai_recipe() -> bool:
    """Push an isekai-style simple recipe."""
    cfg = get_fun_config()
    if not cfg.get("enabled", True):
        return False
    from .content_gen import generate
    result = generate("isekai_recipe")
    if not result:
        return False
    from .notifier import notify_sync as notify
    from .voice import get_voice
    notify("Isekai Recipe", result["body"])
    get_voice().say(f"异世界食谱：{result['body'][:50]}", event="fun_content", sync=True)
    return True


def push_isekai_motivation() -> bool:
    """Push a high-energy isekai motivation message."""
    cfg = get_fun_config()
    if not cfg.get("enabled", True):
        return False
    from .content_gen import generate
    result = generate("isekai_motivation")
    if not result:
        return False
    from .notifier import notify_sync as notify
    from .voice import get_voice
    notify("Isekai Motivation", result["body"])
    get_voice().say(result["body"][:60], event="fun_content", sync=True)
    return True


def push_random_fun() -> str:
    """Push a random type of fun content. Returns the type pushed."""
    types = [
        "blessing", "encouragement", "fact",
        "npc", "place", "micro_quest",
        "life_tip", "anime_quote", "kingdom_news",
        "isekai_slang", "isekai_recipe", "isekai_motivation",
    ]
    chosen = random.choice(types)

    if chosen == "blessing":
        push_morning_blessing()
    elif chosen == "encouragement":
        push_encouragement()
    elif chosen == "fact":
        push_random_fact()
    elif chosen == "npc":
        push_npc_spotlight()
    elif chosen == "place":
        push_place_discovery()
    elif chosen == "micro_quest":
        push_micro_quest()
    elif chosen == "life_tip":
        push_life_tip()
    elif chosen == "anime_quote":
        push_anime_quote()
    elif chosen == "isekai_slang":
        push_isekai_slang()
    elif chosen == "isekai_recipe":
        push_isekai_recipe()
    elif chosen == "isekai_motivation":
        push_isekai_motivation()
    else:
        push_kingdom_news()

    return chosen
