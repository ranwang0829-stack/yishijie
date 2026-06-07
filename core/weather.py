"""Weather module: fetch weather from wttr.in and format in anime style."""

import json
import random
import time
from datetime import datetime
from typing import Any

from .config import load_json, save_json

# Simple in-memory cache
_cache: dict[str, Any] = {"data": None, "ts": 0.0, "city": ""}


def get_weather_config() -> dict[str, Any]:
    cfg = load_json("config.json")
    return cfg.get("weather", {"enabled": True, "city": "Beijing"})


def fetch_weather(city: str) -> dict[str, Any] | None:
    """Fetch weather data from wttr.in. Returns raw dict or None on failure."""
    global _cache

    # Use cache if fresh (< 1 hour)
    if _cache["data"] and _cache["city"] == city and (time.time() - _cache["ts"]) < 3600:
        return _cache["data"]

    try:
        import requests

        url = f"https://wttr.in/{city}?format=j1"
        resp = requests.get(url, timeout=15, headers={"User-Agent": "IsekaiDailySystem/1.0"})
        if resp.status_code != 200:
            print(f"[weather] API returned {resp.status_code}")
            return None

        data = resp.json()
        _cache["data"] = data
        _cache["ts"] = time.time()
        _cache["city"] = city
        return data
    except Exception as e:
        print(f"[weather] 获取失败: {e}")
        return None


def _get_anime_weather(condition: str) -> tuple[str, str]:
    """Get anime-style weather description and advice."""
    words = load_json("anime_words.json")
    weather_map = words.get("weather_descriptions", {})
    advice_map = words.get("weather_advice", {})

    # Match condition to our descriptions
    desc_list = ["天气变幻莫测...但这正是冒险の醍醐味！"]
    for key, descs in weather_map.items():
        if key.lower() in condition.lower():
            desc_list = descs
            break

    desc = random.choice(desc_list)

    # Pick advice based on condition
    condition_lower = condition.lower()
    if any(w in condition_lower for w in ["clear", "sunny", "晴"]):
        advice = random.choice(advice_map.get("clear", advice_map["default"]))
    elif any(w in condition_lower for w in ["rain", "drizzle", "shower", "雨"]):
        advice = random.choice(advice_map.get("rain", advice_map["default"]))
    elif any(w in condition_lower for w in ["snow", "雪"]):
        advice = random.choice(advice_map.get("snow", advice_map["default"]))
    elif any(w in condition_lower for w in ["thunder", "storm", "雷", "暴"]):
        advice = random.choice(advice_map.get("extreme", advice_map["default"]))
    else:
        advice = random.choice(advice_map["default"])

    return desc, advice


def format_weather_anime(data: dict[str, Any], city: str) -> str:
    """Format weather data into anime-style message."""
    try:
        current = data["current_condition"][0]
        temp_c = current.get("temp_C", "?")
        humidity = current.get("humidity", "?")
        wind_speed = current.get("windspeedKmph", "?")
        condition = current.get("weatherDesc", [{}])[0].get("value", "未知")
        feels_like = current.get("FeelsLikeC", temp_c)
        uv_index = current.get("uvIndex", "?")

        # Astronomy data
        astronomy = data.get("weather", [{}])[0].get("astronomy", [{}])[0] if data.get("weather") else {}
        sunrise = astronomy.get("sunrise", "?")
        sunset = astronomy.get("sunset", "?")

        anime_desc, advice = _get_anime_weather(condition)

        lines = [
            f"━━━ ◈ 王国天气通报 ◈ ━━━",
            f"",
            f"🌍 观测所: {city}",
            f"🌡 气温: {temp_c}°C (体感 {feels_like}°C)",
            f"💧 湿度: {humidity}%",
            f"💨 风速: {wind_speed} km/h",
            f"☀ 日出: {sunrise} | 日落: {sunset}",
            f"☀ UV指数: {uv_index}",
            f"",
            f"📜 贤者の解读:",
            f"{anime_desc}",
            f"",
            f"⚔ 勇者行动建议:",
            f"{advice}",
        ]

        return "\n".join(lines)
    except Exception as e:
        print(f"[weather] 格式化失败: {e}")
        return f"天气数据获取成功，但解读失败...(魔法波动干扰中){e}"


def push_weather(force_city: str = "") -> bool:
    """Fetch weather and push via notification. Returns True on success."""
    cfg = get_weather_config()
    if not cfg.get("enabled", True):
        return False

    city = force_city or cfg.get("city", "Beijing")
    data = fetch_weather(city)

    if data is None:
        return False

    msg = format_weather_anime(data, city)

    from .notifier import notify_sync as notify

    notify(f"王国天气 - {city}", msg)

    # Voice: short summary only
    try:
        current = data["current_condition"][0]
        temp = current.get("temp_C", "?")
        cond = current.get("weatherDesc", [{}])[0].get("value", "")
        from .voice import get_voice
        get_voice().say(f"{city}天气：{cond}，气温{temp}度。", event="weather")
    except Exception:
        pass

    return True
