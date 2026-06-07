"""Fun content module: anime-style blessings, encouragements, facts, and daily reports."""

import random
from datetime import datetime
from typing import Any

from .config import load_json
from .task_manager import load_tasks, get_user_state


def get_fun_config() -> dict[str, Any]:
    cfg = load_json("config.json")
    return cfg.get("fun_content", {"enabled": True})


def push_morning_blessing() -> bool:
    """Push a morning blessing (once per day)."""
    cfg = get_fun_config()
    if not cfg.get("enabled", True):
        return False

    words = load_json("anime_words.json")
    blessings = words.get("blessings", ["早安，勇者！"])
    blessing = random.choice(blessings)

    from .notifier import notify
    from .voice import get_voice

    notify("朝の祝福", blessing)
    get_voice().say(blessing[:60], event="fun_content")

    return True


def push_encouragement() -> bool:
    """Push a random RPG-style encouragement."""
    cfg = get_fun_config()
    if not cfg.get("enabled", True):
        return False

    words = load_json("anime_words.json")
    encouragements = words.get("encouragements", ["今天也要加油！"])
    msg = random.choice(encouragements)

    from .notifier import notify
    from .voice import get_voice

    notify("冒险者の一言", msg)
    get_voice().say(msg[:60], event="fun_content")

    return True


def push_random_fact() -> bool:
    """Push a fun fact wrapped in anime flavor."""
    cfg = get_fun_config()
    if not cfg.get("enabled", True):
        return False

    words = load_json("anime_words.json")
    facts = words.get("fun_facts", [{"fact": "生活本身就是冒险！", "anime": "这就是勇者の真谛！"}])
    fact = random.choice(facts)

    msg = f"📚 {fact['fact']}\n\n💬 {fact['anime']}"

    from .notifier import notify
    from .voice import get_voice

    notify("世界の豆知识", msg)
    get_voice().say(f"豆知识：{fact['fact'][:50]}", event="fun_content")

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
    lines.append(f"💬 {random.choice(encouragements)}")

    msg = "\n".join(lines)

    from .notifier import notify
    from .voice import get_voice

    notify("勇者日报", msg)
    get_voice().say(f"勇者日报：今日完成{len(today_completed)}个任务，获得{today_exp}经验值。", event="fun_content")

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

    story = random.choice(stories)
    msg = f"🌙 {story['title']}\n\n{story['story']}"

    from .notifier import notify
    from .voice import get_voice

    notify(f"Bedtime Story: {story['title']}", msg)
    get_voice().say("", event="fun_content")  # Don't voice at night

    return True


def push_random_fun() -> str:
    """Push a random type of fun content (for manual trigger). Returns the type pushed."""
    types = ["blessing", "encouragement", "fact"]
    chosen = random.choice(types)

    if chosen == "blessing":
        push_morning_blessing()
    elif chosen == "encouragement":
        push_encouragement()
    else:
        push_random_fact()

    return chosen
