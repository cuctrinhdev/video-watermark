import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def get_font(size: int):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/Library/Fonts/Arial Bold.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for p in candidates:
        if Path(p).is_file():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def parse_colors(color_scheme: str, opacity_float: float):
    alpha = int(255 * max(0.05, min(1.0, opacity_float)))
    schemes = {
        # ── Nhóm thuần không viền (Pure / No Border) ──────
        "white":       ((255, 255, 255, alpha), None),
        "yellow":      ((255, 230, 0, alpha), None),
        "red":         ((255, 60, 60, alpha), None),
        "cyan":        ((0, 245, 255, alpha), None),
        "black_plain": ((25, 25, 25, alpha), None),
        "white_plain": ((255, 255, 255, alpha), None),
        "yellow_plain":((255, 230, 0, alpha), None),
        "red_plain":   ((255, 60, 60, alpha), None),
        "cyan_plain":  ((0, 245, 255, alpha), None),

        # ── Nhóm có viền nét (With Stroke Border) ─────────
        "white_stroke": ((255, 255, 255, alpha), (0, 0, 0, alpha)),
        "yellow_stroke":((255, 230, 0, alpha), (0, 0, 0, alpha)),
        "red_stroke":   ((255, 60, 60, alpha), (255, 255, 255, alpha)),
        "cyan_stroke":  ((0, 245, 255, alpha), (0, 0, 0, alpha)),
    }
    return schemes.get(color_scheme, schemes["white"])

def generate_text_overlay(
    width: int,
    height: int,
    text: str,
    layout: str = "border",
    font_size: int = 30,
    opacity: float = 0.85,
    color: str = "white",
    output_path: str = "/tmp/text_overlay.png"
):
    if not text.strip():
        return None

    clean_text = text.strip()
    font = get_font(font_size)
    fill_col, stroke_col = parse_colors(color, opacity)
    has_stroke = stroke_col is not None
    stroke_w = max(1, font_size // 10) if has_stroke else 0

    draw_kwargs = {"fill": fill_col}
    if has_stroke:
        draw_kwargs["stroke_width"] = stroke_w
        draw_kwargs["stroke_fill"] = stroke_col

    # Animated layouts: generate pure text (transparent background, no extra icons)
    if layout in ("bounce", "smooth-glide", "ticker-scroll"):
        text_str = clean_text
        bbox = font.getbbox(text_str)
        bw = bbox[2] - bbox[0]
        bh = bbox[3] - bbox[1]

        pad = max(4, stroke_w * 2 + 2)
        img_w = bw + pad * 2
        img_h = bh + pad * 2

        badge_img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        b_draw = ImageDraw.Draw(badge_img)

        tx = pad - bbox[0]
        ty = pad - bbox[1]
        b_draw.text((tx, ty), text_str, font=font, **draw_kwargs)
        badge_img.save(output_path, "PNG")
        return output_path

    # Static full-screen layouts
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    unit_text = f"{clean_text}   ★   "
    bbox = font.getbbox(unit_text)
    text_w = max(10, bbox[2] - bbox[0])
    text_h = max(10, bbox[3] - bbox[1])

    if layout == "border":
        # 1. Top border
        x = 15
        while x < width:
            draw.text((x, 35), unit_text, font=font, **draw_kwargs)
            x += text_w

        # 2. Bottom border
        x = 15
        while x < width:
            draw.text((x, height - 40 - text_h), unit_text, font=font, **draw_kwargs)
            x += text_w

        # 3. Left border (vertical strip rotated 90 deg)
        strip_len = max(100, height - 180)
        stamp = Image.new("RGBA", (strip_len, text_h + 24), (0, 0, 0, 0))
        stamp_draw = ImageDraw.Draw(stamp)
        sx = 0
        while sx < strip_len:
            stamp_draw.text((sx, 2), unit_text, font=font, **draw_kwargs)
            sx += text_w

        left_strip = stamp.rotate(90, expand=True)
        right_strip = stamp.rotate(270, expand=True)

        overlay.paste(left_strip, (15, 90), left_strip)
        overlay.paste(right_strip, (width - right_strip.width - 15, 90), right_strip)

    elif layout == "diagonal":
        stamp = Image.new("RGBA", (text_w + 40, text_h + 20), (0, 0, 0, 0))
        stamp_draw = ImageDraw.Draw(stamp)
        stamp_draw.text((10, 4), unit_text, font=font, **draw_kwargs)
        rotated = stamp.rotate(28, expand=True, resample=Image.BICUBIC)
        rw, rh = rotated.size
        step_x = rw + 80
        step_y = rh + 90
        for y in range(-rh, height + rh, step_y):
            for x in range(-rw, width + rw, step_x):
                overlay.paste(rotated, (x, y), rotated)

    elif layout == "top-bottom":
        bbox_single = font.getbbox(clean_text)
        single_w = bbox_single[2] - bbox_single[0]
        # Top centered
        draw.text(((width - single_w) // 2, 45), clean_text, font=font, **draw_kwargs)
        # Bottom centered
        draw.text(((width - single_w) // 2, height - 60 - text_h), clean_text, font=font, **draw_kwargs)

    elif layout == "ticker-bottom":
        x = 0
        while x < width + text_w:
            draw.text((x, height - 55 - text_h), unit_text, font=font, **draw_kwargs)
            x += text_w

    overlay.save(output_path, "PNG")
    return output_path
