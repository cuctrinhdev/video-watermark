import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops

OUTPUT_DIR = Path("option/template3")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Remove the old buggy static png so find_template_file picks up bg_bottom.gif
for p in [OUTPUT_DIR / "bg_bottom.png", OUTPUT_DIR / "bg_top.png"]:
    if p.exists():
        p.unlink()
        print(f"Removed {p}")

FONTS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]
FONT_PATH = next((p for p in FONTS if Path(p).is_file()), "/System/Library/Fonts/HelveticaNeue.ttc")

def get_font(size: int):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()

def draw_gradient_v(draw, bbox, col_top, col_bot):
    x0, y0, x1, y1 = bbox
    height = max(1, y1 - y0)
    for y in range(y0, y1):
        ratio = (y - y0) / height
        r = int(col_top[0] * (1 - ratio) + col_bot[0] * ratio)
        g = int(col_top[1] * (1 - ratio) + col_bot[1] * ratio)
        b = int(col_top[2] * (1 - ratio) + col_bot[2] * ratio)
        a = int(col_top[3] * (1 - ratio) + col_bot[3] * ratio) if len(col_top) == 4 else 255
        draw.line([(x0, y), (x1, y)], fill=(r, g, b, a))

def draw_vector_cart(draw, cx, cy, color=(255, 255, 255, 255)):
    # Clean vector shopping cart
    # Basket outline
    draw.line([(cx - 15, cy - 8), (cx - 11, cy - 8)], fill=color, width=3)
    draw.line([(cx - 11, cy - 8), (cx - 7, cy + 6)], fill=color, width=3)
    draw.line([(cx - 7, cy + 6), (cx + 12, cy + 6)], fill=color, width=3)
    draw.line([(cx + 12, cy + 6), (cx + 16, cy - 4)], fill=color, width=3)
    draw.line([(cx - 9, cy - 4), (cx + 16, cy - 4)], fill=color, width=3)
    # 2 Wheels
    draw.ellipse([cx - 6, cy + 9, cx - 1, cy + 14], fill=color)
    draw.ellipse([cx + 7, cy + 9, cx + 12, cy + 14], fill=color)

def draw_vector_voucher(draw, cx, cy, color=(255, 255, 255, 255)):
    # Clean vector ticket coupon
    w, h = 30, 20
    x0 = cx - w // 2
    y0 = cy - h // 2
    x1 = x0 + w
    y1 = y0 + h
    draw.rounded_rectangle([x0, y0, x1, y1], radius=4, outline=color, width=2)
    # Notch left and right
    draw.ellipse([x0 - 4, cy - 4, x0 + 4, cy + 4], fill=(35, 38, 52, 255))
    draw.ellipse([x1 - 4, cy - 4, x1 + 4, cy + 4], fill=(35, 38, 52, 255))
    # Star / percent inside
    draw.line([(cx - 4, cy + 4), (cx + 4, cy - 4)], fill=color, width=2)
    draw.ellipse([cx - 5, cy - 5, cx - 2, cy - 2], fill=color)
    draw.ellipse([cx + 2, cy + 2, cx + 5, cy + 5], fill=color)

def draw_vector_package(draw, cx, cy, color=(255, 255, 255, 255)):
    # Clean vector delivery parcel box
    w, h = 26, 22
    x0 = cx - w // 2
    y0 = cy - h // 2
    x1 = x0 + w
    y1 = y0 + h
    draw.rounded_rectangle([x0, y0, x1, y1], radius=4, outline=color, width=2)
    # Tape crosses
    draw.line([(cx, y0), (cx, y1)], fill=color, width=2)
    draw.line([(x0, cy - 2), (x1, cy - 2)], fill=color, width=2)

def draw_chevron(draw, x, y, size=16, color=(238, 77, 45, 255), width=3):
    # Right-pointing chevron >>
    h = size
    half_h = h // 2
    w = int(size * 0.55)
    draw.line([(x, y - half_h), (x + w, y)], fill=color, width=width)
    draw.line([(x + w, y), (x, y + half_h)], fill=color, width=width)

def make_animated_footer():
    w, h = 1080, 190
    num_frames = 20
    frames = []

    f_top_lbl = get_font(21)
    f_step_num = get_font(21)
    f_step_title = get_font(24)
    f_sub = get_font(18)

    steps = [
        {"num": "1", "title": "Bấm Mua Ngay", "drawer": draw_vector_cart, "base_col": (238, 77, 45)},
        {"num": "2", "title": "Chọn Voucher", "drawer": draw_vector_voucher, "base_col": (255, 175, 0)},
        {"num": "3", "title": "Đặt Hàng", "drawer": draw_vector_package, "base_col": (0, 185, 145)},
    ]

    pill_w = 295
    pill_h = 76
    arrow_gap = 48
    total_w = pill_w * 3 + arrow_gap * 2
    start_x = (w - total_w) // 2
    pill_y = 66

    for f_idx in range(num_frames):
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)

        # 1. Background dark glassy gradient
        for i in range(14):
            alpha = int(245 * ((i / 14) ** 1.3))
            d.line([(0, i), (w, i)], fill=(18, 18, 24, alpha))

        draw_gradient_v(d, [0, 14, w, h], (22, 22, 30, 245), (12, 12, 18, 250))

        # Glowing accent line at top
        d.line([(0, 14), (w, 14)], fill=(238, 77, 45, 240), width=3)
        d.line([(0, 15), (w, 15)], fill=(255, 195, 0, 180), width=1)

        # 2. Top Header text
        top_txt = "HƯỚNG DẪN MUA HÀNG TRÊN SHOPEE VIDEO"
        t_box = f_top_lbl.getbbox(top_txt)
        tw = t_box[2] - t_box[0]
        d.text(((w - tw) // 2, 25), top_txt, font=f_top_lbl, fill=(255, 215, 100, 255))

        # 3. Steps rendering with sequential pulse and running chevron arrows
        curr_x = start_x
        # Active step wave: 0 -> 1 -> 2
        active_step_phase = (f_idx / num_frames) * 3

        for s_idx, s in enumerate(steps):
            # Check pulse for current step
            dist = abs(active_step_phase - s_idx)
            is_active = dist < 0.8
            border_alpha = 255 if is_active else 80
            bg_alpha = 240 if is_active else 200

            # Pill Box
            d.rounded_rectangle(
                [curr_x, pill_y, curr_x + pill_w, pill_y + pill_h],
                radius=16,
                fill=(34, 37, 50, bg_alpha),
                outline=(255, 255, 255, border_alpha),
                width=2
            )

            # Left Circle Badge
            c_size = 46
            cx0 = curr_x + 14
            cy0 = pill_y + (pill_h - c_size) // 2
            d.ellipse([cx0, cy0, cx0 + c_size, cy0 + c_size], fill=(*s["base_col"], 255))

            # Number
            n_box = f_step_num.getbbox(s["num"])
            nw = n_box[2] - n_box[0]
            nh = n_box[3] - n_box[1]
            num_col = (0, 0, 0, 255) if s["num"] == "2" else (255, 255, 255, 255)
            d.text((cx0 + (c_size - nw) // 2, cy0 + (c_size - nh) // 2 - 2), s["num"], font=f_step_num, fill=num_col)

            # Title
            t_box = f_step_title.getbbox(s["title"])
            d.text((cx0 + c_size + 14, pill_y + 24), s["title"], font=f_step_title, fill=(255, 255, 255, 255))

            # Vector Icon on the right of title
            icon_cx = curr_x + pill_w - 32
            icon_cy = pill_y + pill_h // 2
            s["drawer"](d, icon_cx, icon_cy, (255, 255, 255, 240))

            curr_x += pill_w

            # Running animated arrows between steps: >>
            if s_idx < len(steps) - 1:
                arr_start_x = curr_x + 8
                arr_cy = pill_y + pill_h // 2

                # Animated running wave for arrows (1 to 3 chevrons running)
                for c_i in range(3):
                    c_x = arr_start_x + c_i * 12
                    # Phase wave
                    phase = (f_idx / num_frames * 4 - c_i * 0.4) % 1.0
                    alpha = int(80 + 175 * (math.sin(phase * math.pi) ** 2))
                    arr_col = (255, 120, 40, alpha)
                    draw_chevron(d, c_x, arr_cy, size=18, color=arr_col, width=3)

                curr_x += arrow_gap

        # 4. Sweep specular shimmer highlight across all pills (chạy sáng kim loại)
        sweep_x = int(-220 + (w + 440) * (f_idx / num_frames))
        shimmer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shimmer)
        sd.polygon([
            (sweep_x, pill_y - 4),
            (sweep_x + 45, pill_y - 4),
            (sweep_x + 95, pill_y + pill_h + 4),
            (sweep_x + 50, pill_y + pill_h + 4),
        ], fill=(255, 255, 255, 55))
        im = Image.alpha_composite(im, shimmer)
        d = ImageDraw.Draw(im)

        # 5. Bottom Guarantee Subtitle (NO EMOJIS, pure Vietnamese with star symbols)
        sub_txt = "★  Giảm đến 50%  •  Miễn phí vận chuyển  •  Giao hàng toàn quốc  ★"
        s_box = f_sub.getbbox(sub_txt)
        sw = s_box[2] - s_box[0]
        d.text(((w - sw) // 2, 154), sub_txt, font=f_sub, fill=(200, 210, 230, 220))

        frames.append(im)

    out_gif = OUTPUT_DIR / "bg_bottom.gif"
    frames[0].save(
        out_gif,
        save_all=True,
        append_images=frames[1:],
        duration=65,  # ~1.3s loop
        loop=0,
        disposal=2
    )
    print(f"Generated {out_gif} with {len(frames)} frames!")

if __name__ == "__main__":
    make_animated_footer()
