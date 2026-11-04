"""Ядро VoiceGuard: определяет, синтезирован ли голос (deepfake) или настоящий.

Модель берётся с Hugging Face (по умолчанию wav2vec2-классификатор
MelodyMachine/Deepfake-audio-detection-V2). Её можно сменить через
переменную окружения VOICEGUARD_MODEL.

Длинные записи режутся на окна по CHUNK_SECONDS, каждое окно
классифицируется отдельно, итог — среднее по окнам. Так видно, если
подделана только часть записи.
"""

from __future__ import annotations

import os
from functools import lru_cache

import librosa
import numpy as np

MODEL_ID = os.getenv("VOICEGUARD_MODEL", "MelodyMachine/Deepfake-audio-detection-V2")
SAMPLE_RATE = 16_000
CHUNK_SECONDS = float(os.getenv("VOICEGUARD_CHUNK_SECONDS", "5"))
MAX_SECONDS = float(os.getenv("VOICEGUARD_MAX_SECONDS", "60"))
FAKE_THRESHOLD = float(os.getenv("VOICEGUARD_THRESHOLD", "0.5"))

# Метки разных моделей приводим к двум: fake / real.
_FAKE_LABELS = {"fake", "spoof", "deepfake", "synthetic", "ai", "label_0"}


@lru_cache(maxsize=1)
def _classifier():
    from transformers import pipeline

    device = 0 if _cuda_available() else -1
    return pipeline("audio-classification", model=MODEL_ID, device=device)


def _cuda_available() -> bool:
    try:
        import torch

        return torch.cuda.is_available()
    except Exception:
        return False


def _fake_score(predictions: list[dict]) -> float:
    """Вероятность класса «fake» из ответа pipeline."""
    for p in predictions:
        if p["label"].lower() in _FAKE_LABELS:
            return float(p["score"])
    # Если fake-метки нет в топе — берём 1 - real.
    for p in predictions:
        if p["label"].lower() in {"real", "bonafide", "bona-fide", "human"}:
            return 1.0 - float(p["score"])
    raise ValueError(f"Неизвестные метки модели: {[p['label'] for p in predictions]}")


def load_audio(path: str) -> np.ndarray:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Файл не найден: {path}")
    audio, _ = librosa.load(path, sr=SAMPLE_RATE, mono=True, duration=MAX_SECONDS)
    if audio.size == 0:
        raise ValueError("Пустая аудиозапись")
    return audio


def analyze_array(audio: np.ndarray) -> dict:
    clf = _classifier()
    step = int(CHUNK_SECONDS * SAMPLE_RATE)
    chunks = [audio[i : i + step] for i in range(0, len(audio), step)]
    # Слишком короткий хвост (<1 c) склеиваем с предыдущим окном.
    if len(chunks) > 1 and len(chunks[-1]) < SAMPLE_RATE:
        chunks[-2] = np.concatenate([chunks[-2], chunks.pop()])

    scores = []
    for chunk in chunks:
        preds = clf({"raw": chunk, "sampling_rate": SAMPLE_RATE}, top_k=None)
        scores.append(_fake_score(preds))

    fake_prob = float(np.mean(scores))
    is_fake = fake_prob >= FAKE_THRESHOLD
    confidence = fake_prob if is_fake else 1 - fake_prob
    return {
        "verdict": "FAKE" if is_fake else "REAL",
        "verdict_ru": "Поддельный (синтезированный) голос" if is_fake else "Настоящий голос",
        "fake_probability": round(fake_prob, 4),
        "confidence": round(confidence, 4),
        "duration_sec": round(len(audio) / SAMPLE_RATE, 2),
        "segments": [
            {
                "start_sec": round(i * CHUNK_SECONDS, 1),
                "fake_probability": round(s, 4),
            }
            for i, s in enumerate(scores)
        ],
        "model": MODEL_ID,
    }


def analyze_file(path: str) -> dict:
    result = analyze_array(load_audio(path))
    result["file"] = os.path.basename(path)
    return result
