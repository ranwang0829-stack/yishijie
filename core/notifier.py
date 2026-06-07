"""Notification module: ntfy.sh mobile push + plyer desktop toast."""

import threading

from .config import load_json


def _get_ntfy_config() -> tuple[str, str]:
    cfg = load_json("config.json")
    topic = cfg.get("ntfy_topic", "")
    server = cfg.get("ntfy_server", "https://ntfy.sh")
    return topic, server


def _safe_title(title: str) -> str:
    """Convert Chinese/emoji title to ASCII for HTTP header, using friendly mappings."""
    mappings: dict[str, str] = {
        "王国天气": "Weather Report",
        "朝の祝福": "Morning Blessing",
        "冒险者の一言": "Adventurer's Word",
        "世界の豆知识": "Fun Fact",
        "勇者日报": "Daily Report",
        "新委托": "New Quest",
        "新daily": "New Quest",
        "新explore": "New Explore",
        "新travel": "New Travel",
        "新encounter": "New Encounter",
        "任务即将过期": "Quest Expiring!",
        "位置触发": "Location Found",
        "紧急提醒": "URGENT",
        "旅行任务": "Travel Quest",
        "奇遇": "Encounter",
    }
    for cn, en in mappings.items():
        if cn in title:
            return en
    safe = title.encode("ascii", errors="ignore").decode("ascii").strip()
    return safe or "Isekai Daily"


def send_ntfy(title: str, message: str, priority: str = "default") -> bool:
    """Send a push notification via ntfy.sh. Returns True on success."""
    topic, server = _get_ntfy_config()
    if not topic:
        return False  # silently skip if not configured

    try:
        import requests

        url = f"{server.rstrip('/')}/{topic}"

        # HTTP headers only support ASCII; sanitize title for the header
        # and prepend the real title to message body
        safe = _safe_title(title)
        if safe != title:
            message = f"{title}\n\n{message}"

        resp = requests.post(
            url,
            data=message.encode("utf-8"),
            headers={
                "Title": safe,
                "Priority": priority,
                "Tags": "japanese_goblin",
            },
            timeout=10,
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"[ntfy] 推送失败: {e}")
        return False


def send_desktop(title: str, message: str) -> bool:
    """Send a desktop toast notification via plyer. Returns True on success."""
    try:
        from plyer import notification

        notification.notify(
            title=title,
            message=message,
            app_name="异世界日常系统",
            timeout=5,
        )
        return True
    except Exception as e:
        print(f"[desktop] 桌面通知失败: {e}")
        return False


def notify(title: str, message: str, priority: str = "default") -> None:
    """Send both ntfy and desktop notifications (fire-and-forget in thread).
    Use notify_sync() for one-shot scripts to ensure delivery before exit."""
    notify_sync(title, message, priority, threaded=True)


def notify_sync(title: str, message: str, priority: str = "default", threaded: bool = False) -> bool:
    """Send notifications. When threaded=False, blocks until ntfy completes.
    Returns True if ntfy was sent successfully."""
    if threaded:
        def _run() -> None:
            send_ntfy(title, message, priority)
            send_desktop(title, message)
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return True
    else:
        ok = send_ntfy(title, message, priority)
        send_desktop(title, message)
        return ok
