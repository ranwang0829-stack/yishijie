"""Background daemon scheduler using the schedule library."""

import signal
import sys
import time
from datetime import datetime
from typing import Any

from .config import load_json, is_in_idle_window
from .task_manager import (
    load_tasks,
    list_active_tasks,
    generate_daily_tasks,
    get_user_state,
    _expire_old_tasks,
    save_tasks,
    cleanup_old_expired,
)
from .notifier import notify
from .voice import get_voice


class DaemonScheduler:
    """Background scheduler that periodically checks and pushes tasks."""

    def __init__(self) -> None:
        self._running = False
        self._voice = get_voice()

    def start(self) -> None:
        """Start the daemon loop."""
        import schedule

        self._running = True

        # Schedule periodic checks
        cfg = load_json("config.json")
        daemon_cfg = cfg.get("daemon", {})
        interval = daemon_cfg.get("check_interval_minutes", 120)

        schedule.every(interval).minutes.do(self._periodic_check)

        # Daily cleanup at 3 AM
        schedule.every().day.at("03:00").do(self._daily_cleanup)

        # Expiration check every 15 minutes
        schedule.every(15).minutes.do(self._expiration_check)

        # Weather push every 3 hours (daytime: 7:00-22:00)
        schedule.every().day.at("07:13").do(self._weather_push)
        schedule.every().day.at("13:37").do(self._weather_push)
        schedule.every().day.at("18:47").do(self._weather_push)

        # Fun content pushes
        schedule.every().day.at("08:37").do(self._morning_blessing)
        schedule.every(150).minutes.do(self._fun_push)
        schedule.every().day.at("20:13").do(self._daily_report)

        print(f"👾 守护进程已启动。")
        print(f"   任务检查间隔: {interval} 分钟")
        print(f"   每日清理: 03:00")
        print(f"   过期检查: 每15分钟")
        print(f"   天气推送: 每天 07:13 / 13:37 / 18:47")
        print(f"   趣味推送: 朝の祝福 08:37 + 每150分钟 + 勇者日报 20:13")
        print(f"   按 Ctrl+C 停止守护进程。")

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        while self._running:
            try:
                schedule.run_pending()
                time.sleep(30)  # Sleep 30 seconds between checks
            except KeyboardInterrupt:
                self._running = False
            except Exception as e:
                print(f"[daemon] 循环异常: {e}")
                time.sleep(60)

        print("👾 守护进程已停止。")

    def stop(self) -> None:
        """Signal the daemon to stop."""
        self._running = False

    def _handle_shutdown(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals gracefully."""
        print("\n正在优雅停止守护进程...")
        self._running = False

    def _periodic_check(self) -> None:
        """Core check: generate tasks if there are too few active ones."""
        now = datetime.now().strftime("%H:%M")
        print(f"[daemon] {now} 周期性任务检查...")

        tasks = _expire_old_tasks(load_tasks())
        save_tasks(tasks)
        active = [t for t in tasks if t.get("status") == "active"]

        cfg = load_json("config.json")
        min_tasks = cfg.get("daemon", {}).get("push_if_tasks_less_than", 2)

        if len(active) < min_tasks:
            print(f"[daemon] 活跃任务({len(active)})不足{min_tasks}个，生成新任务...")
            generated = generate_daily_tasks()

            # Notify for each new task
            for task in generated:
                self._push_task(task)
                # Also check for idle window bonus
                if is_in_idle_window():
                    print(f"[daemon] 空闲时段加成已应用。")
        else:
            print(f"[daemon] 活跃任务数({len(active)})充足，跳过生成。")

    def _expiration_check(self) -> None:
        """Check for tasks about to expire and send warnings."""
        tasks = _expire_old_tasks(load_tasks())
        save_tasks(tasks)

        from datetime import timedelta

        now = datetime.now()
        for t in tasks:
            if t.get("status") != "active":
                continue
            if not t.get("expires_at"):
                continue
            expires = datetime.fromisoformat(t["expires_at"])
            remaining = expires - now
            # Warning at 15 minutes
            if timedelta(minutes=14) < remaining <= timedelta(minutes=16):
                msg = f"紧急提醒：委托「{t.get('name', '未知')}」即将消失！"
                notify("⏰ 任务即将过期", msg, priority="high")
                self._voice.say(msg, event="task_expiring")

    def _daily_cleanup(self) -> None:
        """Clean up old expired tasks."""
        print("[daemon] 执行每日过期任务清理...")
        removed = cleanup_old_expired(days=3)
        print(f"[daemon] 已清理 {removed} 条过期任务。")

    def _push_task(self, task: dict[str, Any]) -> None:
        """Push a task notification and voice alert."""
        title = f"📋 新{task.get('type', '任务')}: {task.get('name', '')}"
        message = f"{task.get('description', '')} | 奖励: {task.get('exp', 0)}EXP + {task.get('gold', 0)}金币 | 限时: {task.get('estimated_minutes', 0)}分钟"

        notify(title, message)

        # Voice: short version (max ~30 chars)
        voice_text = f"新委托：{task.get('name', '')}. {task.get('description', '')}"
        if len(voice_text) > 80:
            voice_text = voice_text[:77] + "..."
        self._voice.say(voice_text, event="new_task")

    def _weather_push(self) -> None:
        """Push weather update."""
        now = datetime.now().strftime("%H:%M")
        print(f"[daemon] {now} 天气推送...")
        try:
            from .weather import push_weather
            push_weather()
        except Exception as e:
            print(f"[daemon] 天气推送失败: {e}")

    def _morning_blessing(self) -> None:
        """Push morning blessing."""
        now = datetime.now().strftime("%H:%M")
        print(f"[daemon] {now} 朝の祝福推送...")
        try:
            from .fun_content import push_morning_blessing
            push_morning_blessing()
        except Exception as e:
            print(f"[daemon] 祝福推送失败: {e}")

    def _fun_push(self) -> None:
        """Push random fun content."""
        now = datetime.now().strftime("%H:%M")
        hour = datetime.now().hour
        # Only push during waking hours (7-23)
        if 7 <= hour <= 23:
            print(f"[daemon] {now} 趣味内容推送...")
            try:
                from .fun_content import push_random_fun
                push_random_fun()
            except Exception as e:
                print(f"[daemon] 趣味推送失败: {e}")

    def _daily_report(self) -> None:
        """Push daily summary report."""
        now = datetime.now().strftime("%H:%M")
        print(f"[daemon] {now} 勇者日报推送...")
        try:
            from .fun_content import push_daily_report
            push_daily_report()
        except Exception as e:
            print(f"[daemon] 日报推送失败: {e}")


# Global singleton
_daemon: DaemonScheduler | None = None


def get_daemon() -> DaemonScheduler:
    global _daemon
    if _daemon is None:
        _daemon = DaemonScheduler()
    return _daemon


def start_daemon() -> None:
    get_daemon().start()


def stop_daemon() -> None:
    get_daemon().stop()
