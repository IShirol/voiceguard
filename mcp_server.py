"""VoiceGuard MCP-сервер (stdio).

Даёт ИИ-ассистенту (Claude Code, Claude Desktop, Cursor) инструменты
для проверки аудиозаписей на синтезированный голос.

Запуск вручную:    python mcp_server.py
Отладка в браузере: mcp dev mcp_server.py
"""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from voiceguard import detector

mcp = FastMCP("voiceguard")

AUDIO_EXT = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".opus", ".webm"}


@mcp.tool()
def analyze_voice(file_path: str) -> dict:
    """Проверить аудиофайл: настоящий голос или поддельный (deepfake / TTS / клон).

    Args:
        file_path: абсолютный путь к аудиофайлу (wav, mp3, flac, ogg, m4a).

    Returns:
        verdict (FAKE/REAL), fake_probability (0..1), confidence,
        duration_sec и оценки по 5-секундным сегментам.
    """
    return detector.analyze_file(file_path)


@mcp.tool()
def analyze_folder(folder_path: str) -> list[dict]:
    """Проверить все аудиофайлы в папке (без подпапок).

    Args:
        folder_path: абсолютный путь к папке с аудио.
    """
    results = []
    for name in sorted(os.listdir(folder_path)):
        if os.path.splitext(name)[1].lower() not in AUDIO_EXT:
            continue
        path = os.path.join(folder_path, name)
        try:
            r = detector.analyze_file(path)
            r.pop("segments", None)
            results.append(r)
        except Exception as e:  # один битый файл не должен ронять весь отчёт
            results.append({"file": name, "error": str(e)})
    return results


@mcp.tool()
def model_info() -> dict:
    """Какая модель используется и с какими настройками."""
    return {
        "model": detector.MODEL_ID,
        "model_url": f"https://huggingface.co/{detector.MODEL_ID}",
        "chunk_seconds": detector.CHUNK_SECONDS,
        "max_seconds": detector.MAX_SECONDS,
        "fake_threshold": detector.FAKE_THRESHOLD,
    }


if __name__ == "__main__":
    mcp.run()
