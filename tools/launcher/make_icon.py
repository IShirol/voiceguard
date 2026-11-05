"""Генератор нативной Windows-иконки VoiceGuard (app.ico).

Создает высококачественную многослойную иконку с изображением защитного щита
и динамической звуковой волны в стилистике Frosted Glass / Dark Cyberpunk.
Размеры: 256x256, 128x128, 64x64, 48x48, 32x32, 16x16.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter


def create_voiceguard_icon(output_path: Path):
    # Работаем в высоком разрешении для антиалиасинга (1024x1024)
    canvas_size = 1024
    img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    center_x = canvas_size // 2
    center_y = canvas_size // 2

    # Фоновый мягкий круг-свечение (Cyan / Deep Blue Glow)
    glow = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_radius = 420
    glow_bbox = [
        center_x - glow_radius,
        center_y - glow_radius + 20,
        center_x + glow_radius,
        center_y + glow_radius + 20,
    ]
    glow_draw.ellipse(glow_bbox, fill=(30, 90, 180, 110))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=60))
    img.alpha_composite(glow)

    # Координаты щита (Shield Polygon / Bezier approximation)
    # Щит: верхний край слегка опущен к центру или слегка изогнут, бока прямые, затем сходятся внизу к острию.
    top = 130
    bottom = 890
    left = 170
    right = 854
    mid_x = 512

    shield_points = [
        (mid_x, top + 40),      # верхний центр
        (right - 40, top),      # верхний правый угол
        (right, top + 80),      # плавный поворот
        (right, 520),           # правая боковая грань
        (mid_x, bottom),        # острие щита
        (left, 520),            # левая боковая грань
        (left, top + 80),       # левый плавный поворот
        (left + 40, top),       # верхний левый угол
    ]

    # Слой внешнего ободка щита (Frosted Glass Border / Silver & Cyan gradient illusion)
    border_img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    border_draw = ImageDraw.Draw(border_img)
    border_draw.polygon(shield_points, fill=(56, 189, 248, 230))  # Light Cyan #38bdf8
    border_img = border_img.filter(ImageFilter.GaussianBlur(radius=8))
    img.alpha_composite(border_img)

    # Тело щита (Глубокий матовый темный индиго/графит #0d1527)
    inner_margin = 28
    inner_shield_points = [
        (mid_x, top + 40 + inner_margin),
        (right - 40 - inner_margin, top + inner_margin),
        (right - inner_margin, top + 80 + inner_margin // 2),
        (right - inner_margin, 510),
        (mid_x, bottom - inner_margin * 1.5),
        (left + inner_margin, 510),
        (left + inner_margin, top + 80 + inner_margin // 2),
        (left + 40 + inner_margin, top + inner_margin),
    ]

    body_img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    body_draw = ImageDraw.Draw(body_img)
    body_draw.polygon(inner_shield_points, fill=(13, 21, 39, 245))  # Deep Navy / Frosted dark
    img.alpha_composite(body_img)

    # Стилизованная звуковая аудиоволна (Audio Wave Bars) в центре
    # Столбики эквалайзера разной высоты
    bars = [
        (350, 110),
        (400, 200),
        (450, 310),
        (512, 420),  # Центральный самый высокий
        (574, 310),
        (624, 200),
        (674, 110),
    ]

    wave_img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    wave_draw = ImageDraw.Draw(wave_img)

    bar_width = 24
    wave_center_y = 500

    for bx, bh in bars:
        b_top = wave_center_y - bh // 2
        b_bottom = wave_center_y + bh // 2
        wave_draw.rounded_rectangle(
            [bx - bar_width // 2, b_top, bx + bar_width // 2, b_bottom],
            radius=12,
            fill=(56, 189, 248, 255),  # Cyan
        )

    # Свечение волны
    wave_glow = wave_img.filter(ImageFilter.GaussianBlur(radius=14))
    img.alpha_composite(wave_glow)
    img.alpha_composite(wave_img)

    # Верхний стеклянный блик (Glossy overlay)
    gloss_img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    gloss_draw = ImageDraw.Draw(gloss_img)
    gloss_draw.ellipse(
        [left + 60, top + 20, right - 60, top + 420],
        fill=(255, 255, 255, 35),
    )
    gloss_img = gloss_img.filter(ImageFilter.GaussianBlur(radius=16))
    img.alpha_composite(gloss_img)

    # Сохраняем в различных разрешениях для высококачественного .ico
    output_path.parent.mkdir(parents=True, exist_ok=True)
    icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    
    # Ресайзим суперсемплированную картинку
    base_256 = img.resize((256, 256), Image.Resampling.LANCZOS)
    base_256.save(
        output_path,
        format="ICO",
        sizes=icon_sizes,
    )
    print(f"Icon successfully generated at: {output_path}")


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "app.ico"
    create_voiceguard_icon(out)
