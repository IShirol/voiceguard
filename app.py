"""VoiceGuard — веб-демо (Gradio) в монохромном стиле Frosted Glass.

Палитра по референсу: молочно-белый, светло-серый, графит, чёрный.
Без цветных акцентов: риск передаётся контрастом (белое → чёрное).
После нажатия «Анализ» показывается анимация (эквалайзер + орбита),
затем результаты (функция-генератор).
"""

from __future__ import annotations

import html
import os

import gradio as gr

from voiceguard import detector

DISCLAIMER = (
    "Вероятностная оценка модели wav2vec2-XLSR. Не является экспертизой; "
    "зависит от качества записи, языка и кодека."
)

SAMPLES = {
    "orych": "samples/real_orych_telegram.wav",
    "eleven": "samples/fake_elevenlabs_kuchka.mp3",
    "edge": "samples/fake_edge_kk_daulet.mp3",
    "win": "samples/fake_windows_tts_ru.wav",
}

# Палитра (CSS-переменные из voiceguard/ui.css, переключаются тёмной темой)
INK = "var(--ink)"
GRAPH = "var(--graph)"
MUTED = "var(--muted)"
LINE = "var(--line)"
ONINK = "var(--onink)"

CUSTOM_CSS = open(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "voiceguard", "ui.css"), encoding="utf-8"
).read()


def _tone(pct: float) -> str:
    """Монохромный тон: 0% — светло-серый, 100% — чёрный."""
    p = max(0.0, min(100.0, pct))
    return f"color-mix(in srgb, var(--ink) {p:.0f}%, var(--muted))"


def _header() -> str:
    return f"""
<div style="display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:16px;margin-bottom:22px">
  <div>
    <div style="font-size:13px;color:{MUTED};font-weight:500;margin-bottom:6px">5 ноября 2026 · Digital Qazaqstan Day</div>
    <h1 style="font-size:48px;font-weight:800;letter-spacing:-.04em;line-height:.95;margin:0;color:{INK}">Voice<br>Guard</h1>
  </div>
  <div style="display:flex;gap:8px;align-items:center">
    <div style="background:var(--card);border:1px solid var(--line);border-radius:999px;padding:9px 16px;font-size:13px;font-weight:500">Детектор ИИ-голоса</div>
    <div style="background:{INK};color:{ONINK};border-radius:999px;padding:9px 16px;font-size:13px;font-weight:600">XLSR-53</div>
  </div>
</div>"""


# ---------- Карточки: состояние покоя ----------
def _idle_meter() -> str:
    bars = "".join(
        f'<span style="animation-delay:{i*0.09:.2f}s;opacity:.18"></span>' for i in range(14)
    )
    return f"""
<div class="glass" style="min-height:360px;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center">
  <div class="vg-eq" style="margin-bottom:18px">{bars}</div>
  <div style="font-size:18px;font-weight:700">Готов к анализу</div>
  <div style="font-size:13px;color:{MUTED};max-width:260px;margin-top:6px;line-height:1.45">
    Выберите образец или запишите голос, затем нажмите «Анализ».
  </div>
</div>"""


def _idle_details() -> str:
    def person(ini, name, role):
        return f"""
<div style="display:flex;align-items:center;gap:12px;padding:10px 12px;border-radius:16px;background:rgba(255,255,255,.06)">
  <div class="av" style="width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px">{ini}</div>
  <div><div style="font-weight:600;font-size:14px">{name}</div><div style="font-size:12px;opacity:.55">{role}</div></div>
</div>"""
    return f"""
<div class="ink" style="min-height:360px;display:flex;flex-direction:column;justify-content:space-between">
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:18px">
      <span style="font-size:14px;font-weight:600">Команда</span>
      <span style="font-size:11px;opacity:.6">Уральск · ЗКИТУ</span>
    </div>
    <div style="display:flex;flex-direction:column;gap:8px">
      {person("ОГ", "Гумаров Орынбек", "Разработка, модели")}
      {person("АУ", "Успанов Арсен", "Архитектура, презентация")}
    </div>
  </div>
  <div style="font-size:11px;opacity:.45;margin-top:18px">Руководитель: Сәрсенғалиева А. М.</div>
</div>"""


# ---------- Карточки: анимация ожидания ----------
def _loading_meter() -> str:
    bars = "".join(f'<span style="animation-delay:{i*0.08:.2f}s"></span>' for i in range(18))
    return f"""
<div class="glass" style="min-height:360px;display:flex;flex-direction:column;justify-content:center">
  <div style="font-size:12px;color:{MUTED};font-weight:600;letter-spacing:.06em;text-transform:uppercase">Анализ записи</div>
  <div style="font-size:26px;font-weight:800;letter-spacing:-.02em;margin:6px 0 18px">Слушаю голос<span class="vg-dots"></span></div>
  <div class="vg-eq" style="justify-content:center;margin-bottom:18px">{bars}</div>
  <div class="vg-skel" style="width:90%"></div>
  <div class="vg-skel" style="width:70%"></div>
  <div class="vg-skel" style="width:80%"></div>
</div>"""


def _loading_details() -> str:
    steps = [
        "Декодирование и ресемплинг до 16 кГц",
        "Нарезка на окна по 5 секунд",
        "Нейросеть wav2vec2-XLSR",
        "Акустический профиль",
    ]
    items = "".join(
        f'<div class="vg-step" style="animation-delay:{0.5 + i*0.9:.1f}s;display:flex;gap:10px;align-items:center;font-size:13px;padding:5px 0">'
        f'<span style="width:6px;height:6px;border-radius:50%;background:#fff"></span>{s}</div>'
        for i, s in enumerate(steps)
    )
    return f"""
<div class="ink" style="min-height:360px">
  <div class="vg-orbit"><div class="ring"></div><div class="ring r2"></div><div class="ring r3"></div><div class="core"></div></div>
  {items}
</div>"""


# ---------- Карточки: результат ----------
def _result_meter(r: dict) -> str:
    avg, peak = r["ai_probability_pct"], r["max_ai_probability_pct"]
    ac = r.get("acoustics", {})
    danger = peak >= 50.0

    def row(dot, label, val):
        return (f'<div style="display:flex;justify-content:space-between;font-size:13px;padding:4px 0">'
                f'<span style="display:flex;align-items:center;gap:8px;color:{GRAPH}">'
                f'<span style="width:7px;height:7px;border-radius:50%;background:{dot}"></span>{label}</span>'
                f'<b>{val:.1f}%</b></div>')

    verdict = (
        f'<div style="background:{INK};color:{ONINK};border-radius:999px;padding:11px 16px;font-size:13px;font-weight:600;display:flex;gap:8px;align-items:center">'
        f'<span>↗</span>Найдены фрагменты с признаками ИИ (пик {peak:.0f}%)</div>'
        if danger else
        f'<div style="background:var(--card-solid);color:{INK};border:1px solid {LINE};border-radius:999px;padding:11px 16px;font-size:13px;font-weight:600;display:flex;gap:8px;align-items:center">'
        f'<span>✓</span>Похоже на живую речь</div>'
    )
    return f"""
<div class="glass" style="min-height:360px;display:flex;flex-direction:column;justify-content:space-between">
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center">
      <span style="font-size:14px;font-weight:600">Вероятность ИИ</span>
      <span style="font-size:12px;color:{MUTED}">пик <b style="color:{INK}">{peak:.1f}%</b></span>
    </div>
    <div style="font-size:64px;font-weight:800;letter-spacing:-.04em;line-height:1;margin-top:10px;color:{_tone(avg)}">
      {avg:.1f}<span style="font-size:28px">%</span>
    </div>
    <div style="font-size:12px;color:{MUTED};margin-top:2px">среднее по записи</div>
    <div class="vg-sparkline" style="margin:14px 0 8px">{r.get('sparkline_svg', '')}</div>
    {row(INK, "Достоверность сигнала", ac.get("confidence_pct", 0))}
    {row("#7a7a7a", "Доля речи", ac.get("speech_ratio_pct", 0))}
    {row("#c4c4c4", "Вариативность интонаций", ac.get("dynamics_pct", 0))}
  </div>
  <div style="margin-top:14px">{verdict}</div>
</div>"""


def _result_details(r: dict) -> str:
    rows = ""
    for s in r["segments"]:
        p = s["ai_probability_pct"]
        rows += f"""
<div style="padding:8px 0;border-bottom:1px solid rgba(255,255,255,.08)">
  <div style="display:flex;justify-content:space-between;font-size:12.5px;margin-bottom:6px">
    <span style="opacity:.7">{s['start_sec']:.0f}–{s['end_sec']:.0f} с</span><b>{p:.0f}%</b>
  </div>
  <div style="height:5px;border-radius:5px;background:rgba(255,255,255,.12)">
    <div style="height:100%;width:{p:.0f}%;border-radius:5px;background:#fff"></div>
  </div>
</div>"""
    sr = r.get("meta", {}).get("orig_sr", 16000)
    return f"""
<div class="ink" style="min-height:360px;display:flex;flex-direction:column;justify-content:space-between">
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
      <span style="font-size:14px;font-weight:600">Обзор файла</span>
      <span style="font-size:11px;background:rgba(255,255,255,.12);padding:3px 10px;border-radius:999px">{sr/1000:.1f} кГц</span>
    </div>
    <div style="font-size:15px;font-weight:600;word-break:break-all">{html.escape(r.get('file', ''))}</div>
    <div style="font-size:12px;opacity:.55;margin-bottom:12px">{r['duration_sec']} с · окон: {len(r['segments'])}</div>
    {rows}
  </div>
  <div style="font-size:11px;opacity:.4;margin-top:14px;line-height:1.4">{DISCLAIMER}</div>
</div>"""


# ---------- Логика ----------
def analyze(audio_path: str):
    if not audio_path:
        raise gr.Error("Загрузите или запишите аудио")
    yield _loading_meter(), _loading_details()
    r = detector.analyze_file(audio_path)
    yield _result_meter(r), _result_details(r)


def _pick(key):
    return lambda: SAMPLES[key] if os.path.exists(SAMPLES[key]) else None


theme = gr.themes.Base(
    primary_hue="neutral", neutral_hue="neutral",
    font=[gr.themes.GoogleFont("Inter"), "sans-serif"],
)

with gr.Blocks(title="VoiceGuard") as demo:
    with gr.Column(elem_id="wrap"):
        with gr.Row(elem_id="vg-top"):
            gr.HTML(_header())
            theme_btn = gr.Button("◐  Тема", elem_classes=["chip", "vg-theme"], size="sm", scale=0, min_width=110)
        with gr.Row(equal_height=True):
            with gr.Column(scale=5):
                with gr.Column(elem_classes=["glass", "vg-input"]):
                    gr.HTML(f"<div style='font-size:16px;font-weight:700'>Аудио</div>"
                            f"<div style='font-size:13px;color:{MUTED};margin:2px 0 12px'>Запишите голос или выберите образец</div>")
                    with gr.Row():
                        b1 = gr.Button("Мой голос", elem_classes=["chip"], size="sm")
                        b2 = gr.Button("ElevenLabs", elem_classes=["chip"], size="sm")
                        b3 = gr.Button("Edge KZ", elem_classes=["chip"], size="sm")
                        b4 = gr.Button("Windows TTS", elem_classes=["chip"], size="sm")
                    audio = gr.Audio(sources=["upload", "microphone"], type="filepath", show_label=False, elem_id="vg-audio")
                    run = gr.Button("↗  Анализ", elem_classes=["pill"])
            with gr.Column(scale=7):
                with gr.Row(equal_height=True):
                    out_m = gr.HTML(_idle_meter())
                    out_d = gr.HTML(_idle_details())

        for b, k in ((b1, "orych"), (b2, "eleven"), (b3, "edge"), (b4, "win")):
            b.click(_pick(k), outputs=[audio])
        theme_btn.click(
            None,
            js="() => { const d = document.body.classList.toggle('vg-dark'); localStorage.setItem('vg-dark', d ? '1' : '0'); }",
        )
        demo.load(None, js="() => { if (localStorage.getItem('vg-dark') === '1') document.body.classList.add('vg-dark'); }")
        run.click(analyze, inputs=[audio], outputs=[out_m, out_d], show_progress="hidden")

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, css=CUSTOM_CSS, theme=theme)
