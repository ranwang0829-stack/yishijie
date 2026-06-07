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
            if age < 5400:  # 90 minutes — PC pushes every 96 min
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

    # ── 1. Morning blessing (8:00-9:00) ──
    if 7 <= hour <= 9:
        try:
            from core.fun_content import push_morning_blessing
            print("[scheduler] 朝の祝福推送...")
            push_morning_blessing()
            had_push = True
        except Exception as e:
            print(f"[scheduler] 祝福失败: {e}")

    # ── 2. Weather push (daytime 7:00-22:00, every 2h) ──
    if 7 <= hour <= 22:
        try:
            from core.weather import push_weather
            print("[scheduler] 天气推送...")
            push_weather()
            had_push = True
        except Exception as e:
            print(f"[scheduler] 天气失败: {e}")

    # ── 3. Fun content push (daytime, alternating) ──
    if 7 <= hour <= 23:
        try:
            from core.fun_content import push_random_fun
            print("[scheduler] 趣味内容推送...")
            push_random_fun()
            had_push = True
        except Exception as e:
            print(f"[scheduler] 趣味失败: {e}")

    # ── 4. Task generation check ──
    try:
        tasks = _expire_old_tasks(load_tasks())
        save_tasks(tasks)
        active = [t for t in tasks if t.get("status") == "active"]
        cfg = load_json("config.json")
        min_tasks = cfg.get("daemon", {}).get("push_if_tasks_less_than", 2)

        if len(active) < min_tasks:
            print(f"[scheduler] 活跃任务不足({len(active)}<{min_tasks})，生成新任务...")
            generated = generate_daily_tasks()
            for task in generated:
                print(f"  + {task['name']}")
            # Push notifications for new tasks
            from core.notifier import notify
            for task in generated:
                notify(
                    f"New Quest: {task.get('name', '')}",
                    f"{task.get('description', '')} | {task.get('exp', 0)}EXP + {task.get('gold', 0)}G",
                )
            had_push = True
        else:
            print(f"[scheduler] 活跃任务充足({len(active)}个)，跳过生成。")
    except Exception as e:
        print(f"[scheduler] 任务生成失败: {e}")

    # ── 5. Daily report (20:00-21:00) ──
    if 19 <= hour <= 21:
        try:
            from core.fun_content import push_daily_report
            print("[scheduler] 勇者日报推送...")
            push_daily_report()
            had_push = True
        except Exception as e:
            print(f"[scheduler] 日报失败: {e}")

    # ── 6. Bedtime story (0:00) ──
    if hour == 0:
        try:
            from core.fun_content import push_bedtime_story
            print("[scheduler] 睡前故事推送...")
            push_bedtime_story()
            had_push = True
        except Exception as e:
            print(f"[scheduler] 睡前故事失败: {e}")

    # ── 7. Daily cleanup (3:00-4:00) ──
    if hour == 3:
        removed = cleanup_old_expired(days=3)
        print(f"[scheduler] 清理了 {removed} 条过期任务。")

    if not had_push:
        print("[scheduler] 本轮无需推送（非推送时段）。")

    print("[scheduler] 完成。")


if __name__ == "__main__":
    main()
