#!/usr/bin/env python3
"""
异世界日常系统 — Isekai Daily Quest System
============================================
动漫风格的现实生活任务派送系统。

用法:
    python main.py <command> [args...]

命令:
    daily / generate            生成今日任务
    tasks list                  列出活跃任务
    tasks complete <id>         完成任务
    tasks expire_now <id>       手动过期任务
    tasks expired               查看已过期任务
    set_state                   更新勇者状态（心情/时间/勇气等）
    add_place                   添加新地点
    add_npc                     添加新NPC
    add_poi                     添加兴趣点(POI)
    set_preference              修改偏好设置
    daemon start                启动后台守护进程
    daemon stop                 停止后台守护进程
    travel generate [--duration N]  生成旅行任务
    travel steps <id>           查看旅行任务步骤
    travel complete_step <id> <n>   完成旅行任务步骤
    travel cancel <id>          取消旅行任务
    encounter on/off            开启/关闭奇遇推送
    encounter generate [location]  生成奇遇任务
    encounter complete <id>     完成奇遇任务
    storyline list              查看故事线进度
    storyline reset <id>        重置故事线
    voice on/off                开关语音
    voice test                  测试语音
    voice rate <100-300>        设置语速
    voice engine <name>         选择语音引擎
    trigger location <name>     模拟位置触发
    status                      查看勇者状态
    weather                     查询天气并推送（动漫风格）
    weather set_city <城市>      设置天气城市
    fun on/off                  开关趣味内容推送
    fun now                     立即推送随机趣味内容
"""

import sys
import os

# Fix Windows console encoding for emoji support
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import task_manager as tm
from core import voice as voice_mod
from core import scheduler as sched_mod
from core import travel as travel_mod
from core import encounter as encounter_mod
from core.notifier import notify
from core.config import load_json, save_json


# ── helpers ──────────────────────────────────────────────────────────────────


def _ensure_sample_data() -> None:
    """Check if data files exist and have content; if not, copy from built-in samples."""
    from pathlib import Path

    data_dir = Path(__file__).parent / "data"
    if not data_dir.exists():
        return  # will be created when saving defaults

    # Trigger loading to auto-create defaults if missing
    load_json("places.json")
    load_json("npcs.json")
    load_json("preferences.json")
    load_json("user_state.json")
    load_json("pois.json")
    load_json("story_templates.json")
    load_json("tasks.json")
    load_json("storylines.json")
    load_json("anime_words.json")
    load_json("config.json")


def _check_voice_event(event: str) -> None:
    """Trigger voice for an event if configured."""
    v = voice_mod.get_voice()
    v.say("", event=event)


# ── command handlers ─────────────────────────────────────────────────────────


def cmd_daily() -> None:
    """Generate today's daily quests."""
    print("🎌 正在生成今日任务...")
    tasks = tm.generate_daily_tasks()

    if not tasks:
        print("  ✗ 未能生成任务。请检查地点/NPC数据或用户状态。")
        return

    state = tm.get_user_state()
    print(f"\n{'=' * 50}")
    print(f"⚔ 勇者状态 | Lv.{state.get('level', 1)} {state.get('title', '')} | {state.get('exp', 0)}EXP | {state.get('gold', 0)}G")
    print(f"  心情: {'❤' * state.get('mood', 3)}{'♡' * (5 - state.get('mood', 3))} | 勇气: {state.get('social_courage', 3)}/5")
    print(f"{'=' * 50}")
    print(f"\n📋 今日任务 ({len(tasks)}个):\n")

    for task in tasks:
        print(tm.format_task(task))
        print()

    # Voice + notify
    for task in tasks:
        title = f"📋 新委托: {task.get('name', '')}"
        msg = f"{task.get('description', '')[:100]} | {task.get('exp', 0)}EXP + {task.get('gold', 0)}G"
        notify(title, msg)

    voice_text = f"今日任务已生成，共{len(tasks)}个委托。"
    voice_mod.get_voice().say(voice_text, event="new_task")


def cmd_tasks_list() -> None:
    """List all active tasks."""
    tasks = tm.list_active_tasks()
    if not tasks:
        print("📋 当前没有活跃任务。运行 `python main.py daily` 生成吧！")
        return

    print(f"\n📋 活跃任务 ({len(tasks)}个):\n")
    for t in tasks:
        print(tm.format_task(t))
        print()


def cmd_tasks_complete(task_id: str) -> None:
    """Complete a task by ID."""
    result = tm.complete_task(task_id)
    if result is None:
        return

    task = result["task"]
    print(f"✅ 任务完成: {task['name']}")
    print(f"   获得: {task['exp']} EXP + {task['gold']} 金币")

    state = tm.get_user_state()
    print(f"   当前: Lv.{state.get('level', 1)} | {state.get('exp', 0)} EXP | {state.get('gold', 0)} G")

    if result.get("leveled_up"):
        print(f"🎉 等级提升！Lv.{result['old_level']} → Lv.{result['new_level']}")
        print(f"   新称号: {result['new_title']}")
        voice_mod.get_voice().say(
            f"等级提升！你现在是{result['new_title']}了！",
            event="level_up",
        )

    voice_mod.get_voice().say(
        f"任务完成！获得{task['exp']}经验值和{task['gold']}金币。",
        event="task_complete",
    )


def cmd_tasks_expire(task_id: str) -> None:
    """Manually expire a task."""
    if tm.expire_task(task_id):
        print(f"💀 任务 {task_id} 已手动过期。")
    else:
        print(f"✗ 无法过期任务 {task_id}。")


def cmd_tasks_expired() -> None:
    """List expired tasks."""
    tasks = tm.list_expired_tasks()
    if not tasks:
        print("📋 没有已过期的任务。")
        return
    print(f"\n💀 已过期任务 ({len(tasks)}个):\n")
    for t in tasks:
        print(f"  [{t.get('id', '?')}] {t.get('name', '未命名')} — {t.get('expires_at', '?')}")


def cmd_set_state() -> None:
    """Update user state interactively."""
    tm.set_state_interactive()


def cmd_add_place() -> None:
    tm.add_place_interactive()


def cmd_add_npc() -> None:
    tm.add_npc_interactive()


def cmd_add_poi() -> None:
    travel_mod.add_poi_interactive()


def cmd_set_preference() -> None:
    tm.set_preference_interactive()


def cmd_status() -> None:
    """Show user state summary."""
    state = tm.get_user_state()
    prefs = tm.get_preferences()
    places = tm.get_places()
    npcs = tm.get_npcs()
    tasks = tm.list_active_tasks()

    print(f"\n{'=' * 50}")
    print(f"⚔ 勇者状态面板")
    print(f"{'=' * 50}")
    print(f"  称号: {state.get('title', '见习')}")
    print(f"  等级: Lv.{state.get('level', 1)} | EXP: {state.get('exp', 0)}")
    print(f"  金币: {state.get('gold', 0)} G")
    print(f"  HP: {state.get('current_hp', 100)}/100")
    print(f"  心情: {'❤' * state.get('mood', 3)}{'♡' * (5 - state.get('mood', 3))} ({state.get('mood', 3)}/5)")
    print(f"  社交勇气: {state.get('social_courage', 3)}/5")
    print(f"  今日可用: {state.get('available_minutes', 60)}分钟 | 最远: {state.get('max_walk_distance', 2000)}m")
    blockers = state.get('blockers', [])
    if blockers:
        print(f"  阻塞: {', '.join(blockers)}")
    print(f"  地点数: {len(places)} | NPC数: {len(npcs)}")
    print(f"  活跃任务: {len(tasks)}个")
    print(f"  偏好任务: {', '.join(prefs.get('preferred_task_types', [])) or '未设置'}")


def cmd_daemon_start() -> None:
    """Start background daemon."""
    import threading

    t = threading.Thread(target=sched_mod.start_daemon, daemon=True)
    t.start()

    # Keep main thread alive
    try:
        while t.is_alive():
            t.join(1)
    except KeyboardInterrupt:
        print("\n收到中断信号...")
        sched_mod.stop_daemon()


def cmd_daemon_stop() -> None:
    sched_mod.stop_daemon()
    print("✓ 已发送停止信号。")


def cmd_travel_generate(args: list[str]) -> None:
    """Generate a travel quest."""
    duration = 60
    lat, lon = 0.0, 0.0

    for i, a in enumerate(args):
        if a == "--duration" and i + 1 < len(args):
            duration = max(30, min(120, int(args[i + 1])))
        if a == "--lat" and i + 1 < len(args):
            lat = float(args[i + 1])
        if a == "--lon" and i + 1 < len(args):
            lon = float(args[i + 1])

    print(f"🗺 正在生成旅行任务(目标时长: {duration}分钟)...")
    task = travel_mod.generate_travel(user_lat=lat, user_lon=lon, preferred_duration=duration)

    if task:
        print(f"\n{'=' * 50}")
        print(f"🗺 旅行任务已生成!")
        print(f"{'=' * 50}")
        print(tm.format_task(task))
        print(f"\n📌 步骤 ({task.get('total_steps', 0)}站):")
        for step in task.get("steps", []):
            icon = "⬜" if not step.get("completed") else "✅"
            print(f"  {icon} 第{step['index'] + 1}站: {step['poi_name']} → {step['action']}")

        voice_mod.get_voice().say(
            f"旅行任务已生成！{task.get('total_steps', 0)}站路线，预计{task.get('estimated_minutes', 0)}分钟。",
            event="new_task",
        )


def cmd_travel_steps(task_id: str) -> None:
    """View travel quest steps."""
    steps = travel_mod.travel_steps(task_id)
    if steps is None:
        return
    print(f"\n📌 旅行步骤 ({len(steps)}站):\n")
    for s in steps:
        status = "✅" if s.get("completed") else "⬜"
        print(f"  {status} 第{s['index'] + 1}站: [{s['poi_id']}] {s['poi_name']}")
        print(f"     动作: {s['action']}")
        print(f"     预估: {s.get('estimated_minutes', 0)}分钟 | 距离: {s.get('segment_distance_m', 0)}m")
        print(f"     奖励: {s.get('reward_exp', 0)}EXP + {s.get('reward_gold', 0)}G")
        print()


def cmd_travel_complete_step(task_id: str, step_index: str) -> None:
    """Complete a travel step."""
    try:
        idx = int(step_index)
    except ValueError:
        print("✗ 步骤索引必须是数字。")
        return

    result = travel_mod.complete_travel_step(task_id, idx)
    if result:
        print(f"✅ 步骤 {idx} 完成！")
        print(f"   获得: {result.get('exp', 0)} EXP + {result.get('gold', 0)} G")

        if result.get("bonus"):
            print(f"🎉 全部步骤完成！额外奖励: {result.get('bonus_exp', 0)}EXP + {result.get('bonus_gold', 0)}G")
            voice_mod.get_voice().say("旅行任务全部完成！干得漂亮，勇者！", event="task_complete")
        else:
            voice_mod.get_voice().say("步骤完成！继续前进吧！", event="task_complete")


def cmd_travel_cancel(task_id: str) -> None:
    """Cancel a travel quest."""
    if travel_mod.cancel_travel(task_id):
        print(f"✓ 旅行任务 {task_id} 已取消。")
    else:
        print(f"✗ 未找到活跃的旅行任务 {task_id}。")


def cmd_encounter_on() -> None:
    encounter_mod.set_encounter_enabled(True)


def cmd_encounter_off() -> None:
    encounter_mod.set_encounter_enabled(False)


def cmd_encounter_generate(args: list[str]) -> None:
    """Generate an encounter quest."""
    location = args[0] if args else ""
    task = encounter_mod.generate_encounter(location_hint=location)
    if task:
        print(f"\n✨ 奇遇任务已生成!")
        print(tm.format_task(task))
        if task.get("suggested_opener"):
            print(f"   💬 建议开场白: {task['suggested_opener']}")
        if task.get("likely_appearance"):
            print(f"   👤 外貌提示: {task['likely_appearance']}")
        voice_mod.get_voice().say(f"奇遇任务已触发：{task['name']}", event="new_task")


def cmd_encounter_complete(task_id: str) -> None:
    """Complete an encounter quest."""
    result = encounter_mod.complete_encounter(task_id)
    if result is None:
        return

    task = result.get("task", {})
    print(f"✅ 奇遇完成: {task.get('name', '')}")
    print(f"   获得: {task.get('exp', 0)} EXP + {task.get('gold', 0)} G")

    if result.get("storyline_advanced"):
        print(f"📖 故事线推进至第{result.get('next_chapter', 0) + 1}章")
        voice_mod.get_voice().say("故事线已推进！", event="storyline_chapter")

    if result.get("storyline_completed"):
        print(f"🎊 故事线「{result.get('storyline_name', '')}」全部完成！")
        voice_mod.get_voice().say(
            f"故事线{result.get('storyline_name', '')}全部完成！恭喜！",
            event="storyline_chapter",
        )


def cmd_storyline_list() -> None:
    """List storylines."""
    storylines = encounter_mod.storyline_list()
    if not storylines:
        print("📖 当前没有进行中的故事线。开启奇遇来开始一段故事吧！")
        return

    print(f"\n📖 故事线 ({len(storylines)}条):\n")
    for sl in storylines:
        prog = f"{sl.get('current_chapter', 0)}/{sl.get('total_chapters', '?')}"
        status = "✅ 完成" if sl.get("completed") else "📖 进行中"
        print(f"  {status} {sl.get('story_name', '?')} — 进度: {prog}")
        if not sl.get("completed"):
            print(f"    下一章: {sl.get('next_chapter_title', '?')}")
            print(f"    解锁条件: {sl.get('next_unlock_condition', '?')}")
        print()


def cmd_storyline_reset(story_id: str) -> None:
    encounter_mod.storyline_reset(story_id)


def cmd_voice_on() -> None:
    voice_mod.voice_on()


def cmd_voice_off() -> None:
    voice_mod.voice_off()


def cmd_voice_test() -> None:
    voice_mod.voice_test()


def cmd_voice_rate(rate: str) -> None:
    try:
        voice_mod.voice_set_rate(int(rate))
    except ValueError:
        print("✗ 速率必须是数字 (100-300)。")


def cmd_voice_engine(engine: str) -> None:
    voice_mod.voice_set_engine(engine)


def cmd_weather(args: list[str]) -> None:
    """Query weather and push."""
    from core.weather import push_weather

    if args and args[0] == "set_city" and len(args) > 1:
        city = args[1]
        cfg = load_json("config.json")
        cfg.setdefault("weather", {})["city"] = city
        save_json("config.json", cfg)
        print(f"✓ 天气城市已设置为: {city}")

    print("🌤 正在获取天气数据...")
    if push_weather():
        print("✓ 天气已推送到手机。")
    else:
        print("✗ 天气获取失败，请检查网络或城市名称。")


def cmd_fun(args: list[str]) -> None:
    """Handle fun content commands."""
    from core.fun_content import push_random_fun

    cfg = load_json("config.json")

    if not args:
        print("用法: fun on/off | fun now")
        return

    sub = args[0]
    if sub == "on":
        cfg["fun_content"] = {"enabled": True}
        save_json("config.json", cfg)
        print("✓ 趣味内容推送已开启。")
    elif sub == "off":
        cfg["fun_content"] = {"enabled": False}
        save_json("config.json", cfg)
        print("✓ 趣味内容推送已关闭。")
    elif sub == "now":
        print("🎲 正在推送随机趣味内容...")
        chosen = push_random_fun()
        type_names = {"blessing": "朝の祝福", "encouragement": "冒险者の一言", "fact": "世界の豆知识"}
        print(f"✓ 已推送: {type_names.get(chosen, chosen)}")
    else:
        print("用法: fun on/off | fun now")


def cmd_trigger(location: str) -> None:
    """Simulate location-based task trigger."""
    print(f"📍 触发位置: {location}")

    places = tm.get_places()
    matching = [p for p in places if location.lower() in p.get("name", "").lower() or location.lower() in p.get("type", "").lower()]

    if matching:
        place = matching[0]
        print(f"   匹配地点: {place['name']} (距离: {place.get('distance_m', 0)}m)")

        # Generate a short task for this location
        state = tm.get_user_state()
        from core.task_manager import _build_task, _pick_task_type

        prefs = tm.get_preferences()
        task_type = _pick_task_type(state.get("social_courage", 3), prefs.get("preferred_task_types", []), prefs.get("forbidden_actions", []))
        npcs = tm.get_npcs()
        place_npcs = [n for n in npcs if n.get("location") == place.get("name")]
        npc = place_npcs[0] if place_npcs else None

        task = _build_task(task_type, place, npc, state, tm.get_anime_words())
        if task:
            tasks = tm.load_tasks()
            tasks.append(task)
            tm.save_tasks(tasks)

            print(f"\n📋 位置触发任务:\n")
            print(tm.format_task(task))

            notify(
                f"📍 位置触发: {task.get('name', '')}",
                task.get("description", "")[:100],
            )
            voice_mod.get_voice().say(
                f"附近发现新委托：{task.get('name', '')}",
                event="new_task",
            )
    else:
        print(f"   未找到匹配地点。可用地点: {[p['name'] for p in places]}")


# ── main CLI router ──────────────────────────────────────────────────────────


def print_help() -> None:
    print(__doc__)


def main() -> None:
    _ensure_sample_data()

    args = sys.argv[1:] if len(sys.argv) > 1 else ["help"]

    if not args:
        print_help()
        return

    cmd = args[0].lower()

    try:
        # ── daily / generate ──
        if cmd in ("daily", "generate"):
            cmd_daily()

        # ── tasks ──
        elif cmd == "tasks":
            sub = args[1] if len(args) > 1 else "list"
            if sub == "list":
                cmd_tasks_list()
            elif sub == "complete" and len(args) > 2:
                cmd_tasks_complete(args[2])
            elif sub == "expire_now" and len(args) > 2:
                cmd_tasks_expire(args[2])
            elif sub == "expired":
                cmd_tasks_expired()
            else:
                print("用法: tasks list | tasks complete <id> | tasks expire_now <id> | tasks expired")

        # ── set_state ──
        elif cmd == "set_state":
            cmd_set_state()

        # ── add ──
        elif cmd == "add_place":
            cmd_add_place()
        elif cmd == "add_npc":
            cmd_add_npc()
        elif cmd == "add_poi":
            cmd_add_poi()

        # ── set_preference ──
        elif cmd == "set_preference":
            cmd_set_preference()

        # ── status ──
        elif cmd == "status":
            cmd_status()

        # ── daemon ──
        elif cmd == "daemon":
            sub = args[1] if len(args) > 1 else ""
            if sub == "start":
                cmd_daemon_start()
            elif sub == "stop":
                cmd_daemon_stop()
            else:
                print("用法: daemon start | daemon stop")

        # ── travel ──
        elif cmd == "travel":
            sub = args[1] if len(args) > 1 else ""
            if sub == "generate":
                cmd_travel_generate(args[2:])
            elif sub == "steps" and len(args) > 2:
                cmd_travel_steps(args[2])
            elif sub == "complete_step" and len(args) > 3:
                cmd_travel_complete_step(args[2], args[3])
            elif sub == "cancel" and len(args) > 2:
                cmd_travel_cancel(args[2])
            else:
                print("用法: travel generate [--duration N] | travel steps <id> | travel complete_step <id> <n> | travel cancel <id>")

        # ── encounter ──
        elif cmd == "encounter":
            sub = args[1] if len(args) > 1 else ""
            if sub == "on":
                cmd_encounter_on()
            elif sub == "off":
                cmd_encounter_off()
            elif sub == "generate":
                cmd_encounter_generate(args[2:])
            elif sub == "complete" and len(args) > 2:
                cmd_encounter_complete(args[2])
            else:
                print("用法: encounter on/off | encounter generate [location] | encounter complete <id>")

        # ── storyline ──
        elif cmd == "storyline":
            sub = args[1] if len(args) > 1 else "list"
            if sub == "list":
                cmd_storyline_list()
            elif sub == "reset" and len(args) > 2:
                cmd_storyline_reset(args[2])
            else:
                print("用法: storyline list | storyline reset <id>")

        # ── voice ──
        elif cmd == "voice":
            sub = args[1] if len(args) > 1 else ""
            if sub == "on":
                cmd_voice_on()
            elif sub == "off":
                cmd_voice_off()
            elif sub == "test":
                cmd_voice_test()
            elif sub == "rate" and len(args) > 2:
                cmd_voice_rate(args[2])
            elif sub == "engine" and len(args) > 2:
                cmd_voice_engine(args[2])
            else:
                print("用法: voice on/off | voice test | voice rate <100-300> | voice engine <pyttsx3|edge-tts>")

        # ── trigger ──
        elif cmd == "trigger":
            sub = args[1] if len(args) > 1 else ""
            if sub == "location" and len(args) > 2:
                cmd_trigger(args[2])
            else:
                print("用法: trigger location <name>")

        # ── weather ──
        elif cmd == "weather":
            cmd_weather(args[1:])

        # ── fun ──
        elif cmd == "fun":
            cmd_fun(args[1:])

        # ── help ──
        elif cmd in ("help", "-h", "--help"):
            print_help()

        else:
            print(f"未知命令: {cmd}")
            print("运行 `python main.py help` 查看帮助。")

    except KeyboardInterrupt:
        print("\n👋 再见，勇者！")
    except Exception as e:
        print(f"✗ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
