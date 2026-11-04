"""VoiceGuard — веб-демо для Hugging Face Spaces (Gradio).

Локально: python app.py  ->  http://127.0.0.1:7860
"""

from __future__ import annotations

import gradio as gr

from voiceguard import detector


def check_voice(audio_path: str):
    """Проверить запись: настоящий голос или поддельный (deepfake).

    Args:
        audio_path: путь или URL аудиофайла (wav, mp3, flac, ogg).
    """
    if not audio_path:
        raise gr.Error("Загрузите или запишите аудио")
    r = detector.analyze_file(audio_path)
    label = {
        "Поддельный голос (FAKE)": r["fake_probability"],
        "Настоящий голос (REAL)": 1 - r["fake_probability"],
    }
    seg = "\n".join(
        f"- {s['start_sec']:>5} c: вероятность подделки {s['fake_probability']:.0%}"
        for s in r["segments"]
    )
    details = (
        f"**Вердикт:** {r['verdict_ru']}  \n"
        f"**Уверенность:** {r['confidence']:.0%}  \n"
        f"**Длительность:** {r['duration_sec']} c  \n"
        f"**Модель:** `{r['model']}`\n\n**По сегментам:**\n{seg}"
    )
    return label, details


with gr.Blocks(title="VoiceGuard") as demo:
    gr.Markdown(
        "# 🛡️ VoiceGuard — детектор поддельного голоса\n"
        "Загрузите запись или скажите что-нибудь в микрофон. "
        "Модель оценит, живой это голос или синтезированный (TTS / клонирование)."
    )
    with gr.Row():
        audio = gr.Audio(sources=["upload", "microphone"], type="filepath", label="Аудио")
        with gr.Column():
            out_label = gr.Label(label="Результат", num_top_classes=2)
            out_md = gr.Markdown()
    gr.Button("Проверить", variant="primary").click(check_voice, audio, [out_label, out_md])
    gr.Markdown(
        "_Демо-проект для Digital Qazaqstan Day 2026. "
        "Результат вероятностный и не является экспертизой._"
    )

if __name__ == "__main__":
    demo.launch()
