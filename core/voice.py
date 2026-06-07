"""Voice notification module using pyttsx3 (offline) or edge-tts (online)."""

import threading
from typing import Any

from .config import load_json, save_json


class VoiceNotifier:
    """Text-to-speech notifier with configurable engine."""

    def __init__(self) -> None:
        self._engine: Any = None
        self._edge_available = self._check_edge_tts()

    def _check_edge_tts(self) -> bool:
        try:
            import edge_tts  # noqa: F401

            return True
        except ImportError:
            return False

    def _get_config(self) -> dict[str, Any]:
        cfg = load_json("config.json")
        return cfg.get("voice", {})

    def _should_speak(self, event: str) -> bool:
        cfg = self._get_config()
        if not cfg.get("enabled", True):
            return False
        filters = cfg.get("event_filters", [])
        return "all" in filters or event in filters

    def say(self, text: str, event: str = "general") -> None:
        """Speak text in a background thread if voice is enabled and event matches filter."""
        if not self._should_speak(event):
            return

        cfg = self._get_config()
        engine_name = cfg.get("engine", "pyttsx3")

        if engine_name == "edge-tts" and self._edge_available:
            t = threading.Thread(target=self._say_edge, args=(text, cfg), daemon=True)
        else:
            t = threading.Thread(target=self._say_pyttsx3, args=(text, cfg), daemon=True)
        t.start()

    def _say_pyttsx3(self, text: str, cfg: dict[str, Any]) -> None:
        """Speak using pyttsx3 (offline)."""
        try:
            import pyttsx3

            if self._engine is None:
                self._engine = pyttsx3.init()
            engine = self._engine

            rate = cfg.get("rate", 150)
            volume = cfg.get("volume", 1.0)
            voice_id = cfg.get("voice_id", "")

            engine.setProperty("rate", rate)
            engine.setProperty("volume", volume)
            if voice_id:
                # Find matching voice
                voices = engine.getProperty("voices")
                for v in voices:
                    if voice_id in v.id or voice_id in v.name:
                        engine.setProperty("voice", v.id)
                        break

            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"[voice/pyttsx3] TTS失败: {e}")

    def _say_edge(self, text: str, cfg: dict[str, Any]) -> None:
        """Speak using edge-tts (online, more natural)."""
        try:
            import asyncio

            rate = cfg.get("rate", 150)
            # Convert rate to edge-tts format: -50% to +100%
            rate_str = f"{int((rate - 150) / 150 * 100):+d}%"

            async def _run() -> None:
                import edge_tts

                voice = cfg.get("voice_id", "zh-CN-XiaoxiaoNeural")
                communicate = edge_tts.Communicate(text, voice, rate=rate_str)
                # Use a temporary file for playback
                import tempfile
                import os

                # edge-tts requires writing to a file, then playing it
                fd, tmpfile = tempfile.mkstemp(suffix=".mp3")
                os.close(fd)
                try:
                    await communicate.save(tmpfile)
                    # Play using a cross-platform method
                    self._play_audio_file(tmpfile)
                finally:
                    try:
                        os.unlink(tmpfile)
                    except OSError:
                        pass

            asyncio.run(_run())
        except Exception as e:
            print(f"[voice/edge-tts] TTS失败: {e}")

    def _play_audio_file(self, filepath: str) -> None:
        """Play an audio file cross-platform."""
        import platform
        import subprocess
        import sys

        system = platform.system()
        try:
            if system == "Windows":
                subprocess.run(
                    ["powershell", "-c", f"(New-Object Media.SoundPlayer '{filepath}').PlaySync()"],
                    capture_output=True,
                )
            elif system == "Darwin":
                subprocess.run(["afplay", filepath], capture_output=True)
            else:
                # Linux: try multiple players
                for player in ["mpv", "ffplay", "aplay", "paplay"]:
                    try:
                        subprocess.run([player, filepath], capture_output=True, timeout=30)
                        break
                    except (FileNotFoundError, subprocess.TimeoutExpired):
                        continue
        except Exception as e:
            print(f"[voice/playback] 音频播放失败: {e}")

    def stop(self) -> None:
        """Stop the pyttsx3 engine if running."""
        if self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass


# Global singleton
_voice_instance: VoiceNotifier | None = None


def get_voice() -> VoiceNotifier:
    global _voice_instance
    if _voice_instance is None:
        _voice_instance = VoiceNotifier()
    return _voice_instance


def voice_on() -> None:
    cfg = load_json("config.json")
    cfg.setdefault("voice", {})["enabled"] = True
    save_json("config.json", cfg)
    print("✓ 语音播报已开启。")


def voice_off() -> None:
    cfg = load_json("config.json")
    cfg.setdefault("voice", {})["enabled"] = False
    save_json("config.json", cfg)
    print("✓ 语音播报已关闭。")


def voice_test() -> None:
    """Test voice synchronously (waits for speech to finish)."""
    v = get_voice()
    cfg = load_json("config.json").get("voice", {})
    print("✓ 正在播放测试语音...")
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", cfg.get("rate", 150))
        engine.setProperty("volume", cfg.get("volume", 1.0))
        engine.say("这里是异世界日常系统的语音测试。勇者，今天也要加油哦！")
        engine.runAndWait()
        print("✓ 播放完毕。")
    except Exception as e:
        print(f"✗ 语音失败: {e}")


def voice_set_rate(rate: int) -> None:
    rate = max(100, min(300, rate))
    cfg = load_json("config.json")
    cfg.setdefault("voice", {})["rate"] = rate
    save_json("config.json", cfg)
    print(f"✓ 语音速率已设置为 {rate}。")


def voice_set_engine(engine: str) -> None:
    valid = ["pyttsx3", "edge-tts"]
    if engine not in valid:
        print(f"✗ 无效引擎。可用: {', '.join(valid)}")
        return
    cfg = load_json("config.json")
    cfg.setdefault("voice", {})["engine"] = engine
    save_json("config.json", cfg)
    print(f"✓ 语音引擎已设置为 {engine}。")
