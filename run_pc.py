#!/usr/bin/env python3
"""
PC本地推送脚本 — 带语音播报。
每30分钟运行一次，完成：天气+趣味内容+任务检查+睡前故事+语音朗读。
同时写入心跳文件，GitHub Actions 检测到心跳后会跳过推送，避免重复。
"""
import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import load_json, save_json
from core.voice import get_voice
from core.task_manager import load_tasks, _expire_old_tasks, save_tasks, generate_daily_tasks, cleanup_old_expired


def write_heartbeat() -> None:
    """Write heartbeat so GitHub Actions skips when PC is active."""
    save_json("heartbeat.json", {
        "last_pc_push": datetime.now(timezone.utc).isoformat(),
        "host": os.environ.get("COMPUTERNAME", "PC"),
    })


def now_cn() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=8)


def main() -> None:
    now = now_cn()
    hour = now.hour
    print(f"[PC] 运行时间: {now.strftime('%Y-%m-%d %H:%M')}")

    voice = get_voice()
    had_push = False

    # Quiet hours check
    if 2 <= hour < 8:
        print(f"[PC] 静默时段（2:00-8:00），跳过所有推送。")
        if hour == 3:
            cleanup_old_expired(days=3)
        return

    # ── Pick ONE action per cycle (避免一次推送多条) ──
    actions = []

    # Weather: daytime, weight 2
    if 7 <= hour <= 22:
        actions.extend(["weather", "weather"])

    # Fun content: daytime, weight 5
    if 7 <= hour <= 23:
        actions.extend(["fun"] * 5)

    # Task generation: only when needed, weight 3
    tasks = _expire_old_tasks(load_tasks())
    save_tasks(tasks)
    active = [t for t in tasks if t.get("status") == "active"]
    if len(active) < 2:
        actions.extend(["task"] * 3)

    # Daily report: evening, weight 2
    if 19 <= hour <= 21:
        actions.extend(["report", "report"])

    # Bedtime story: midnight
    if hour == 0:
        actions.extend(["story"] * 3)

    if not actions:
        print("[PC] 无可用推送类型。")
    else:
        import random
        chosen = random.choice(actions)
        print(f"[PC] 选择推送类型: {chosen}")

        try:
            if chosen == "weather":
                from core.weather import push_weather, fetch_weather
                cfg = load_json("config.json")
                city = cfg.get("weather", {}).get("city", "Changchun")
                data = fetch_weather(city)
                if data:
                    push_weather()
                    curr = data["current_condition"][0]
                    cond = curr.get("weatherDesc", [{}])[0].get("value", "")
                    temp = curr.get("temp_C", "?")
                    voice.say(f"{city}天气：{cond}，{temp}度。", event="weather")
                    had_push = True

            elif chosen == "fun":
                from core.fun_content import push_random_fun
                push_random_fun()
                had_push = True

            elif chosen == "task":
                generated = generate_daily_tasks()
                for task in generated:
                    voice.say(f"新委托：{task['name']}", event="new_task")
                had_push = True

            elif chosen == "story":
                from core.fun_content import push_bedtime_story
                push_bedtime_story()
                had_push = True

            elif chosen == "report":
                from core.fun_content import push_daily_report
                push_daily_report()
                voice.say("勇者日报已生成。", event="fun_content")
                had_push = True

        except Exception as e:
            print(f"[PC] 推送失败: {e}")

    # ── Heartbeat ──
    write_heartbeat()
    print(f"[PC] 心跳已写入。推送数: {'有' if had_push else '无'}")

    # ── Commit heartbeat to GitHub ──
    try:
        import subprocess
        subprocess.run(
            ["C:/Program Files/Git/bin/git.exe", "-C", os.path.dirname(__file__),
             "add", "data/heartbeat.json", "data/tasks.json", "data/user_state.json"],
            capture_output=True, timeout=15)
        subprocess.run(
            ["C:/Program Files/Git/bin/git.exe", "-C", os.path.dirname(__file__),
             "commit", "-m", "PC heartbeat [auto]"],
            capture_output=True, timeout=15)
        subprocess.run(
            ["C:/Program Files/Git/bin/git.exe", "-C", os.path.dirname(__file__), "push"],
            capture_output=True, timeout=30)
        print("[PC] 心跳已同步到 GitHub。")
    except Exception:
        print("[PC] 心跳同步跳过（GitHub不可达）。")


if __name__ == "__main__":
    main()
