#!/usr/bin/env python3
"""PC startup welcome — greets the user with an isekai-style voice message."""
import sys
import os
import random
import asyncio
import tempfile
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import load_json
from core.weather import fetch_weather


def pick_greeting() -> str:
    """Pick a random isekai-style welcome message."""
    now = datetime.now()
    hour = now.hour
    if 5 <= hour < 11:
        time_word = "早上好"
        time_flavor = "晨曦初现，新的冒险即将开始！"
    elif 11 <= hour < 14:
        time_word = "中午好"
        time_flavor = "日正当空，勇者の斗志正在巅峰！"
    elif 14 <= hour < 18:
        time_word = "下午好"
        time_flavor = "午后阳光正好，适合外出探索。"
    elif 18 <= hour < 22:
        time_word = "晚上好"
        time_flavor = "夜幕降临，是时候回顾今日の冒险了。"
    else:
        time_word = "夜深了"
        time_flavor = "星空灿烂，守夜人正在值班。辛苦了，勇者。"

    greetings = [
        f"{time_word}！异世界日常系统已启动。{time_flavor}",
        f"欢迎回来，勇者！{time_word}。{time_flavor}",
        f"系统启动完毕。{time_word}，我一直在等你呢。{time_flavor}",
        f"叮！异世界连接成功。{time_word}，准备好今天的冒险了吗？{time_flavor}",
        f"{time_word}～今天也要元气满满！{time_flavor}",
    ]

    return random.choice(greetings)


def add_weather_to_greeting(greeting: str) -> str:
    """Append weather info if available."""
    cfg = load_json("config.json")
    city = cfg.get("weather", {}).get("city", "Changchun")
    try:
        data = fetch_weather(city)
        if data:
            curr = data["current_condition"][0]
            temp = curr.get("temp_C", "?")
            cond = curr.get("weatherDesc", [{}])[0].get("value", "?")
            return f"{greeting}\n\n今日{city}天气：{cond}，气温{temp}度。"
    except Exception:
        pass
    return greeting


async def speak(text: str, voice_id: str) -> str:
    """Generate MP3 with edge-tts, return file path."""
    import edge_tts
    fd, tmpfile = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    communicate = edge_tts.Communicate(text, voice_id)
    await communicate.save(tmpfile)
    return tmpfile


def main() -> None:
    cfg = load_json("config.json")
    voice_cfg = cfg.get("voice", {})
    voice_id = voice_cfg.get("voice_id") or "zh-CN-XiaoyiNeural"

    greeting = pick_greeting()
    greeting = add_weather_to_greeting(greeting)

    print(f"[Welcome] {greeting}")

    try:
        tmpfile = asyncio.run(speak(greeting, voice_id))
        os.startfile(tmpfile)
        # Wait for playback
        import time
        time.sleep(len(greeting) * 0.3 + 3)  # rough estimate
        os.unlink(tmpfile)
    except Exception as e:
        print(f"[Welcome] Voice failed: {e}")
        # Fallback to pyttsx3
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(greeting)
            engine.runAndWait()
        except Exception:
            pass


if __name__ == "__main__":
    main()
