# Лог задачи: 01 Выбор модели и MVP-каркас (`task_01_model_selection.md`)

> **Дата создания:** 2026-11-04
> **Исполнитель:** Главный Агент
> **Статус:** ✅ Завершена
> **Связанная сессия:** [`docs/session.md`](../session.md)

---

## 1. Что было сделано
- Развёрнут agent_starter_pack, создан приватный репозиторий https://github.com/IShirol/voiceguard.
- Ядро `voiceguard/detector.py`, веб-демо `app.py` (Gradio), прогон образцов `tools/smoke_test.py`.
- Образцы в `samples/`: 2 синтезированных голоса Windows TTS (EN Zira, RU Irina) + 1 живая речь LibriSpeech.
- Сравнены 5 моделей с Hugging Face, выбрана лучшая.

## 2. Сравнение моделей на `samples/` (fake_en / fake_ru / real_en, p(fake))

| Модель | fake EN | fake RU | real | Итог |
| :--- | :---: | :---: | :---: | :---: |
| **Gustking/wav2vec2-large-xlsr-deepfake-audio-classification** | 0.892 | 0.876 | 0.307 | **3/3** |
| mo-thecreator/Deepfake-audio-detection | 1.000 | 1.000 | 0.999 ❌ | 2/3 |
| garystafford/wav2vec2-deepfake-voice-detector | 0.942 | 0.530 | 0.988 ❌ | 2/3 |
| MelodyMachine/Deepfake-audio-detection-V2 | 0.013 ❌ | 0.000 ❌ | 0.000 | 1/3 |
| abhishtagatya/wav2vec2-base-960h-itw-deepfake | 0.004 ❌ | 0.004 ❌ | 0.004 | 1/3 |

## 3. Зачем так
- Бюджета нет → готовая открытая модель (Apache-2.0) + бесплатный CPU Space, без обучения своей.
- XLSR-53 предобучена на 53 языках — шанс лучше работать на русском и казахском.
- Выборка из 3 файлов мала: перед выступлением нужно добавить свои живые записи (RU/KZ) и современные TTS/клоны и перепроверить порог.

## 4. Потенциальная ценность для базы знаний
- [x] 💡 Таблица сравнения моделей → `knowledge_base/model_selection.md` при закрытии этапа.
