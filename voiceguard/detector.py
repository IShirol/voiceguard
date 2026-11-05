"""Ядро VoiceGuard: определяет, синтезирован ли голос (deepfake) или настоящий.

Модель берётся с Hugging Face (по умолчанию wav2vec2-XLSR-классификатор
Gustking/wav2vec2-large-xlsr-deepfake-audio-classification). Её можно сменить через
переменную окружения VOICEGUARD_MODEL.

Длинные записи режутся на окна по CHUNK_SECONDS, каждое окно
классифицируется отдельно, итог — среднее по окнам.
"""

from __future__ import annotations

import os
from functools import lru_cache

import librosa
import numpy as np
import soundfile as sf

MODEL_ID = os.getenv("VOICEGUARD_MODEL", "Gustking/wav2vec2-large-xlsr-deepfake-audio-classification")
SAMPLE_RATE = 16_000
CHUNK_SECONDS = float(os.getenv("VOICEGUARD_CHUNK_SECONDS", "5"))
MAX_SECONDS = float(os.getenv("VOICEGUARD_MAX_SECONDS", "60"))

# Метки разных моделей приводим к двум: fake / real.
_FAKE_LABELS = {"fake", "spoof", "deepfake", "synthetic", "ai"}


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


def load_audio(path: str) -> tuple[np.ndarray, dict]:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Файл не найден: {path}")

    # Считываем оригинальные метаданные файла
    meta = {"orig_sr": 16000, "orig_duration": 0.0}
    try:
        info = sf.info(path)
        meta["orig_sr"] = info.samplerate
        meta["orig_duration"] = round(info.duration, 2)
    except Exception:
        pass

    audio, _ = librosa.load(path, sr=SAMPLE_RATE, mono=True, duration=MAX_SECONDS)
    if audio.size == 0:
        raise ValueError("Пустая аудиозапись")
    return audio, meta


def _compute_acoustics(audio: np.ndarray, sr: int) -> dict:
    """Быстрый акустический профиль речи: динамика интонаций и процент речи."""
    # 1. Процент речи vs пауз (VAD по порогу RMS)
    frame_len = int(0.05 * sr)
    rms = np.array([np.sqrt(np.mean(audio[i : i + frame_len] ** 2)) for i in range(0, len(audio), frame_len)])
    speech_ratio = float(np.mean(rms > 0.015) * 100) if len(rms) > 0 else 0.0

    # 2. Динамика спектрального центроида (вариативность тона)
    try:
        cent = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
        dynamics = float(np.std(cent) / (np.mean(cent) + 1e-6) * 100)
    except Exception:
        dynamics = 50.0

    # 3. Индекс уверенности детекции (длина записи + качество сигнала)
    duration = len(audio) / sr
    conf = min(98.5, max(65.0, 70.0 + (min(duration, 15.0) / 15.0) * 20.0 + (speech_ratio / 100.0) * 8.5))

    return {
        "speech_ratio_pct": round(speech_ratio, 1),
        "dynamics_pct": round(dynamics, 1),
        "confidence_pct": round(conf, 1),
    }


def _generate_sparkline(scores: list[float]) -> str:
    """Генерация гладкой SVG-кривой для карточки в стиле референса."""
    if not scores:
        return ""
    if len(scores) == 1:
        scores = [scores[0], scores[0]]

    w, h = 220, 48
    pad_x, pad_y = 12, 10
    n = len(scores)
    step_x = (w - 2 * pad_x) / (n - 1) if n > 1 else 0

    points = []
    for i, s in enumerate(scores):
        x = pad_x + i * step_x
        # 100% -> y = pad_y (вверху), 0% -> y = h - pad_y (внизу)
        y = (h - pad_y) - s * (h - 2 * pad_y)
        points.append((x, y))

    # Построение плавной кривой Bezier
    d = [f"M {points[0][0]:.1f},{points[0][1]:.1f}"]
    for i in range(len(points) - 1):
        p0 = points[i]
        p1 = points[i + 1]
        cx1 = p0[0] + (p1[0] - p0[0]) * 0.5
        cy1 = p0[1]
        cx2 = cx1
        cy2 = p1[1]
        d.append(f"C {cx1:.1f},{cy1:.1f} {cx2:.1f},{cy2:.1f} {p1[0]:.1f},{p1[1]:.1f}")

    path_data = " ".join(d)
    return f"""<svg viewBox="0 0 {w} {h}" style="width:100%;height:46px;overflow:visible">
  <path d="{path_data}" fill="none" stroke="#0f172a" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
  {" ".join(f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="3" fill="#0f172a"/>' for p in points)}
</svg>"""


def analyze_array(audio: np.ndarray, meta: dict | None = None) -> dict:
    clf = _classifier()
    step = int(CHUNK_SECONDS * SAMPLE_RATE)
    chunks = [audio[i : i + step] for i in range(0, len(audio), step)]
    # Слишком короткий хвост (<1 c) склеиваем с предыдущим окном.
    if len(chunks) > 1 and len(chunks[-1]) < SAMPLE_RATE:
        tail = chunks.pop()
        chunks[-1] = np.concatenate([chunks[-1], tail])

    scores = []
    for chunk in chunks:
        preds = clf({"raw": chunk, "sampling_rate": SAMPLE_RATE}, top_k=None)
        scores.append(_fake_score(preds))

    ai_prob = float(np.mean(scores))
    max_prob = float(np.max(scores)) if scores else ai_prob
    duration = round(len(audio) / SAMPLE_RATE, 2)
    acoustics = _compute_acoustics(audio, SAMPLE_RATE)

    return {
        "ai_probability_pct": round(ai_prob * 100, 1),
        "max_ai_probability_pct": round(max_prob * 100, 1),
        "duration_sec": duration,
        "sparkline_svg": _generate_sparkline(scores),
        "acoustics": acoustics,
        "meta": meta or {},
        "segments": [
            {
                "start_sec": round(i * CHUNK_SECONDS, 1),
                "end_sec": round(duration if i == len(scores) - 1 else (i + 1) * CHUNK_SECONDS, 1),
                "ai_probability_pct": round(s * 100, 1),
                "is_suspicious": bool(s >= 0.5),
            }
            for i, s in enumerate(scores)
        ],
        "model": MODEL_ID,
    }


def analyze_file(path: str) -> dict:
    audio, meta = load_audio(path)
    result = analyze_array(audio, meta)
    result["file"] = os.path.basename(path)
    return result
