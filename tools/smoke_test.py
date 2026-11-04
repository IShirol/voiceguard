"""Прогон всех файлов из samples/ через детектор — для сравнения моделей.

Запуск из корня проекта:  .venv/Scripts/python tools/smoke_test.py [папка]
Ожидание: у fake_* вероятность ИИ высокая, у real_* — низкая.
Порог 50 % здесь только для подсчёта «попаданий» при сравнении моделей,
пользователю приложение показывает лишь процент.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from voiceguard import detector  # noqa: E402

folder = sys.argv[1] if len(sys.argv) > 1 else "samples"
ok = total = 0
for name in sorted(os.listdir(folder)):
    path = os.path.join(folder, name)
    if not os.path.isfile(path):
        continue
    pct = detector.analyze_file(path)["ai_probability_pct"]
    expected_high = name.startswith("fake") if name.startswith(("fake", "real")) else None
    hit = expected_high is not None and (pct >= 50) == expected_high
    ok += hit
    total += expected_high is not None
    print(f"{'OK ' if hit else '-- '} {name:30} ИИ: {pct:5.1f}%")
print(f"\n{ok}/{total} совпало с ожиданием, модель {detector.MODEL_ID}")
