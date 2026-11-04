"""VoiceGuard — веб-демо для Hugging Face Spaces (Gradio).

Показывает только вероятность того, что голос сгенерирован ИИ (0–100 %).
Вердиктов «подделка / настоящий» нет: это оценка, а не гарантия.

Локально: python app.py  ->  http://127.0.0.1:7860
"""

from __future__ import annotations

import html

import gradio as gr

from voiceguard import detector

DISCLAIMER = (
    "Это вероятностная оценка нейросети, а не гарантия и не экспертиза. "
    "Результат зависит от качества записи, языка и способа генерации голоса."
)


def _color(pct: float) -> str:
    # Плавно от зелёного (0 %) через жёлтый к красному (100 %).
    hue = 120 - 120 * pct / 100
    return f"hsl({hue:.0f}, 70%, 45%)"


def _meter(pct: float) -> str:
    return f"""
<div style="font-family:inherit">
  <div style="font-size:15px;opacity:.8">Вероятность, что голос сгенерирован ИИ</div>
  <div style="font-size:56px;font-weight:700;line-height:1.1;color:{_color(pct)}">{pct:.0f}%</div>
  <div style="height:14px;border-radius:7px;background:linear-gradient(90deg,hsl(120,70%,45%),hsl(60,70%,45%),hsl(0,70%,45%));position:relative;margin:10px 0 4px">
    <div style="position:absolute;left:calc({pct:.1f}% - 2px);top:-4px;width:4px;height:22px;background:currentColor;border-radius:2px"></div>
  </div>
  <div style="display:flex;justify-content:space-between;font-size:12px;opacity:.7"><span>0%</span><span>50%</span><span>100%</span></div>
</div>"""


def check_voice(audio_path: str):
    """Оценить вероятность (0–100 %) того, что голос на записи сгенерирован ИИ.

    Args:
        audio_path: путь или URL аудиофайла (wav, mp3, flac, ogg, m4a).
    """
    if not audio_path:
        raise gr.Error("Загрузите или запишите аудио")
    r = detector.analyze_file(audio_path)
    rows = "".join(
        f"<tr><td>{s['start_sec']:.0f}–{s['start_sec'] + detector.CHUNK_SECONDS:.0f} c</td>"
        f"<td style='color:{_color(s['ai_probability_pct'])};font-weight:600'>{s['ai_probability_pct']:.0f}%</td></tr>"
        for s in r["segments"]
    )
    details = (
        f"<p>Длительность: {r['duration_sec']} c · модель: <code>{html.escape(r['model'])}</code></p>"
        f"<table><tr><th>Фрагмент</th><th>Вероятность ИИ</th></tr>{rows}</table>"
        f"<p style='opacity:.75;font-size:13px'>⚠️ {DISCLAIMER}</p>"
    )
    return _meter(r["ai_probability_pct"]), details


with gr.Blocks(title="VoiceGuard") as demo:
    gr.Markdown(
        "# 🛡️ VoiceGuard — детектор поддельного голоса\n"
        "Загрузите запись или скажите что-нибудь в микрофон. "
        "Нейросеть оценит **вероятность** того, что голос синтезирован ИИ (TTS / клонирование)."
    )
    with gr.Row():
        audio = gr.Audio(sources=["upload", "microphone"], type="filepath", label="Аудио")
        with gr.Column():
            out_meter = gr.HTML()
            out_details = gr.HTML()
    gr.Button("Оценить", variant="primary").click(check_voice, audio, [out_meter, out_details])
    gr.Markdown(f"_Демо-проект для Digital Qazaqstan Day 2026. {DISCLAIMER}_")

if __name__ == "__main__":
    demo.launch()
