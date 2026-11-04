---
title: VoiceGuard
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: gradio
app_file: app.py
pinned: false
license: apache-2.0
short_description: Детектор поддельного (синтезированного) голоса
---

# 🛡️ VoiceGuard — детектор поддельного голоса

Проект Успанова Арсена и Гумарова Орынбека для «IT-Generation: Шаг в будущее»
(Digital Qazaqstan Day 2026, Уральск, 5 ноября 2026).

VoiceGuard определяет, принадлежит ли голос на записи живому человеку или
синтезирован нейросетью (TTS, клонирование голоса). Нужен против
телефонного мошенничества «голосом родственника», фейковых голосовых в
мессенджерах и подделки аудиодоказательств.

## Как устроено

```
         аудио (wav/mp3/микрофон)
                  │
        voiceguard/detector.py
   librosa → 16 кГц моно → окна по 5 с
                  │
   wav2vec2-классификатор с Hugging Face
   (MelodyMachine/Deepfake-audio-detection-V2)
                  │
   вероятность подделки по каждому окну → среднее → FAKE / REAL
          ┌───────┴────────┐
     app.py (Gradio)   mcp_server.py (MCP, stdio)
   веб-демо в HF Space  инструменты для ИИ-ассистентов
   + MCP по SSE
```

Бюджет нулевой: модель открытая (Apache-2.0), хостинг — бесплатный CPU
Space на Hugging Face.

## Быстрый старт (локально)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows;  source .venv/bin/activate — Linux/macOS
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
python app.py                   # веб-демо на http://127.0.0.1:7860
```

## MCP-сервер

Инструменты:

| Инструмент | Что делает |
| :--- | :--- |
| `analyze_voice(file_path)` | Вердикт по одному файлу + оценки по сегментам |
| `analyze_folder(folder_path)` | Пакетная проверка всех аудио в папке |
| `model_info()` | Какая модель и пороги используются |

**Claude Code** подхватывает сервер из [`.mcp.json`](.mcp.json) автоматически
(путь к Python там для Windows; на Linux/macOS — `.venv/bin/python`).

**Claude Desktop / Cursor** — добавить в конфиг:

```json
{
  "mcpServers": {
    "voiceguard": {
      "command": "C:/путь/к/проекту/.venv/Scripts/python.exe",
      "args": ["C:/путь/к/проекту/mcp_server.py"]
    }
  }
}
```

Отладка в браузере: `mcp dev mcp_server.py`.

После деплоя в Space тот же функционал доступен как удалённый MCP:
`https://<user>-voiceguard.hf.space/gradio_api/mcp/sse`.

## Деплой на Hugging Face Spaces

1. На huggingface.co → New Space → SDK: Gradio, hardware: CPU basic (бесплатно).
2. `git remote add space https://huggingface.co/spaces/<user>/voiceguard`
3. `git push space main`

## Настройки (переменные окружения)

| Переменная | По умолчанию | Смысл |
| :--- | :--- | :--- |
| `VOICEGUARD_MODEL` | `MelodyMachine/Deepfake-audio-detection-V2` | Модель на HF |
| `VOICEGUARD_THRESHOLD` | `0.5` | Порог вероятности для вердикта FAKE |
| `VOICEGUARD_CHUNK_SECONDS` | `5` | Длина окна анализа |
| `VOICEGUARD_MAX_SECONDS` | `60` | Сколько секунд записи анализировать |

## Ограничения

Модель обучена на англоязычных датасетах и может ошибаться на казахской и
русской речи, на сильно сжатом звуке (телефон, мессенджеры) и на новых
генераторах голоса. Результат вероятностный и не является экспертизой.

---
Структура памяти агента и регламент работы — [`AGENTS.md`](AGENTS.md), [`docs/start_work.md`](docs/start_work.md).
