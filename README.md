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
   (Gustking/wav2vec2-large-xlsr-deepfake-audio-classification)
                  │
   вероятность подделки по каждому окну → среднее → FAKE / REAL
                  │
     app.py — веб-демо (Gradio) в HF Space
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
python tools/smoke_test.py      # прогон образцов из samples/ (fake_* / real_*)
```

## Деплой на Hugging Face Spaces

1. На huggingface.co → New Space → SDK: Gradio, hardware: CPU basic (бесплатно).
2. `git remote add space https://huggingface.co/spaces/<user>/voiceguard`
3. `git push space main`

## Настройки (переменные окружения)

| Переменная | По умолчанию | Смысл |
| :--- | :--- | :--- |
| `VOICEGUARD_MODEL` | `Gustking/wav2vec2-large-xlsr-deepfake-audio-classification` | Модель на HF |
| `VOICEGUARD_THRESHOLD` | `0.5` | Порог вероятности для вердикта FAKE |
| `VOICEGUARD_CHUNK_SECONDS` | `5` | Длина окна анализа |
| `VOICEGUARD_MAX_SECONDS` | `60` | Сколько секунд записи анализировать |

## Ограничения

Модель обучена на англоязычных датасетах и может ошибаться на казахской и
русской речи, на сильно сжатом звуке (телефон, мессенджеры) и на новых
генераторах голоса. Результат вероятностный и не является экспертизой.

---
Структура памяти агента и регламент работы — [`AGENTS.md`](AGENTS.md), [`docs/start_work.md`](docs/start_work.md).
