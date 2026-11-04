"""Генерирует нейросетевые «поддельные» голоса (Microsoft Edge TTS, бесплатно) в samples/.

Запуск из корня проекта:  .venv/Scripts/python tools/make_fakes.py
Требует: pip install edge-tts
"""
import asyncio
import os

import edge_tts

OUT = "samples"
PHRASES = {
    "ru": "Мама, привет, это я. Я попал в аварию, телефон разбился. Срочно переведи деньги на этот номер, потом всё объясню.",
    "kk": "Сәлеметсіз бе, бұл банктің қауіпсіздік қызметі. Картаңызға күдікті әрекет тіркелді, кодты айтыңызшы.",
}
VOICES = {
    "ru-RU-DmitryNeural": "ru",
    "ru-RU-SvetlanaNeural": "ru",
    "kk-KZ-DauletNeural": "kk",
    "kk-KZ-AigulNeural": "kk",
}


async def main():
    os.makedirs(OUT, exist_ok=True)
    for voice, lang in VOICES.items():
        name = voice.split("-")[2].replace("Neural", "").lower()
        path = os.path.join(OUT, f"fake_edge_{lang}_{name}.mp3")
        for attempt in range(3):
            try:
                await edge_tts.Communicate(PHRASES[lang], voice).save(path)
                print("saved", path)
                break
            except edge_tts.exceptions.NoAudioReceived:
                await asyncio.sleep(2)
        else:
            print("FAILED", voice)


asyncio.run(main())
