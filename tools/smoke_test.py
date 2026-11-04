"""Прогон всех файлов из samples/ через детектор.

Запуск из корня проекта:  .venv/Scripts/python tools/smoke_test.py [папка]
Ожидание: файлы с префиксом fake_ -> FAKE, real_ -> REAL.
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
    r = detector.analyze_file(path)
    expected = "FAKE" if name.startswith("fake") else "REAL" if name.startswith("real") else "?"
    hit = r["verdict"] == expected
    ok += hit
    total += expected != "?"
    print(f"{'OK ' if hit else '-- '} {name:30} {r['verdict']:4}  p(fake)={r['fake_probability']:.3f}  {r['duration_sec']}s")
print(f"\n{ok}/{total} совпало с ожиданием, модель {detector.MODEL_ID}")
