#!/usr/bin/env python3
"""
One-shot scheduler entry point for GitHub Actions.
Runs a single cycle of: weather push + fun content + task generation + daily report.
No persistent daemon — designed for cron-style execution every 2 hours.
"""
import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import load_json, save_json
from core.task_manager import list_active_tasks, generate_daily_tasks, load_tasks, _expire_old_tasks, save_tasks, cleanup_old_expired, get_user_state


def now_cn() -> datetime:
    """Get current time in China timezone (UTC+8)."""
    return datetime.now(timezone.utc) + timedelta(hours=8)


def main() -> None:
    now = now_cn()
    hour = now.hour
    weekday = now.weekday()  # 0=Monday
    print(f"[scheduler] 运行时间: {now.strftime('%Y-%m-%d %H:%M')} 北京时间 (星期{weekday+1})")

    # ── -1. Heartbeat check: skip if PC is active ──
    try:
        from core.config import load_json
        from datetime import timezone
        hb = load_json("heartbeat.json")
        if hb and hb.get("last_pc_push"):
            last = datetime.fromisoformat(hb["last_pc_push"])
            age = (datetime.now(timezone.utc) - last).total_seconds()
            if age < 540:  # 9 minutes — PC pushes every 10 min
                print(f"[scheduler] PC {age:.0f}秒前推送过，跳过本轮（避免重复）。")
                return
    except Exception:
        pass  # No heartbeat file = first run or PC never pushed

    # ── 0. Quiet hours check (2:00-8:00 → skip all pushes) ──
    if 2 <= hour < 8:
        print(f"[scheduler] 静默时段（2:00-8:00），跳过所有推送。")
        # Only do cleanup during quiet hours
        if hour == 3:
            removed = cleanup_old_expired(days=3)
            print(f"[scheduler] 清理了 {removed} 条过期任务。")
        return

    had_push = False

    # ── Pick ONE action per cycle ──
    import random
    actions = []

    # Morning blessing: 8-9
    if 8 <= hour <= 9:
        actions.append("blessing")

    # Weather: daytime
    if 7 <= hour <= 22:
        actions.extend(["weather"] * 2)

    # Fun content: daytime
    if 7 <= hour <= 23:
        actions.extend(["fun"] * 5)

    # Task generation: only when needed
    tasks = _expire_old_tasks(load_tasks())
    save_tasks(tasks)
    active = [t for t in tasks if t.get("status") == "active"]
    if len(active) < 2:
        actions.extend(["task"] * 3)

    # Daily report: evening
    if 19 <= hour <= 21:
        actions.extend(["report"] * 2)

    # Bedtime story
    if hour == 0:
        actions.extend(["story"] * 3)

    if actions:
        chosen = random.choice(actions)
        print(f"[scheduler] 选择推送类型: {chosen}")

        try:
            if chosen == "blessing":
                from core.fun_content import push_morning_blessing
                push_morning_blessing()
                had_push = True

            elif chosen == "weather":
                from core.weather import push_weather
                push_weather()
                had_push = True

            elif chosen == "fun":
                from core.fun_content import push_random_fun
                push_random_fun()
                had_push = True

            elif chosen == "task":
                generated = generate_daily_tasks()
                for task in generated:
                    print(f"  + {task['name']}")
                from core.notifier import notify
                for task in generated:
                    notify(f"New Quest: {task.get('name', '')}",
                           f"{task.get('description', '')} | {task.get('exp', 0)}EXP + {task.get('gold', 0)}G")
                had_push = True

            elif chosen == "report":
                from core.fun_content import push_daily_report
                push_daily_report()
                had_push = True

            elif chosen == "story":
                from core.fun_content import push_bedtime_story
                push_bedtime_story()
                had_push = True

        except Exception as e:
            print(f"[scheduler] 推送失败: {e}")
    else:
        print("[scheduler] 无可用推送类型。")

    # ── Cleanup (3:00-4:00) ──
    if hour == 3:
        removed = cleanup_old_expired(days=3)
        print(f"[scheduler] 清理了 {removed} 条过期任务。")

    if not had_push:
        print("[scheduler] 本轮无需推送（非推送时段）。")

    print("[scheduler] 完成。")


if __name__ == "__main__":
    main()
