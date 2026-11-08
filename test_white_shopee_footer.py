import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path("option/template3")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
    draw.line([(cx - 14, cy - 7), (cx - 10, cy - 7)], fill=color, width=3)
    draw.line([(cx - 10, cy - 7), (cx - 6, cy + 6)], fill=color, width=3)
    draw.line([(cx - 6, cy + 6), (cx + 12, cy + 6)], fill=color, width=3)
    draw.line([(cx + 12, cy + 6), (cx + 16, cy - 4)], fill=color, width=3)
    draw.line([(cx - 8, cy - 4), (cx + 16, cy - 4)], fill=color, width=3)
    draw.ellipse([cx - 5, cy + 8, cx - 1, cy + 12], fill=color)
    draw.ellipse([cx + 7, cy + 8, cx + 11, cy + 12], fill=color)

def draw_vector_voucher(draw, cx, cy, color=(255, 255, 255, 255)):
    w, h = 30, 20
    x0, y0, x1, y1 = cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2
    draw.rounded_rectangle([x0, y0, x1, y1], radius=4, outline=color, width=2)
    draw.line([(cx - 4, cy + 4), (cx + 4, cy - 4)], fill=color, width=2)
    draw.ellipse([cx - 5, cy - 5, cx - 2, cy - 2], fill=color)
    draw.ellipse([cx + 2, cy + 2, cx + 5, cy + 5], fill=color)

def draw_vector_package(draw, cx, cy, color=(255, 255, 255, 255)):
    w, h = 26, 22
    x0, y0, x1, y1 = cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2
    draw.rounded_rectangle([x0, y0, x1, y1], radius=4, outline=color, width=2)
    draw.line([(cx, y0), (cx, y1)], fill=color, width=2)
    draw.line([(x0, cy - 2), (x1, cy - 2)], fill=color, width=2)

def draw_animated_arrow(draw, x, y, size=18, is_active=False, pulse_val=0.0):
    half_h = size // 2
    w = int(size * 0.55)
    if is_active:
        c1 = (238, 77, 45, 255)
        c2 = (255, 140, 0, int(160 + 95 * pulse_val))
        draw.line([(x, y - half_h), (x + w, y)], fill=c1, width=3)
        draw.line([(x + w, y), (x, y + half_h)], fill=c1, width=3)
        draw.line([(x + 12, y - half_h), (x + 12 + w, y)], fill=c2, width=3)
        draw.line([(x + 12 + w, y), (x + 12, y + half_h)], fill=c2, width=3)
    else:
        c_dim = (195, 200, 215, 200)
        draw.line([(x + 5, y - half_h), (x + 5 + w, y)], fill=c_dim, width=2)
        draw.line([(x + 5 + w, y), (x + 5, y + half_h)], fill=c_dim, width=2)

def generate_white_shopee_footer():
    w, h = 1080, 160
    num_frames = 24  # 8 frames per step (8 * 3 = 24 frames)
    frames = []

    f_top = get_font(21)
    f_num = get_font(22)
    f_title = get_font(24)

    steps_data = [
        {
            "num": "1",
            "title": "Bấm Mua Ngay",
            "drawer": draw_vector_cart,
            "active_top": (255, 87, 34, 255),
            "active_bot": (230, 50, 15, 255),
            "glow": (238, 77, 45, 80)
        },
        {
            "num": "2",
            "title": "Chọn Voucher",
            "drawer": draw_vector_voucher,
            "active_top": (255, 175, 0, 255),
            "active_bot": (235, 130, 0, 255),
            "glow": (255, 175, 0, 80)
        },
        {
            "num": "3",
            "title": "Đặt Hàng",
            "drawer": draw_vector_package,
            "active_top": (0, 185, 135, 255),
            "active_bot": (0, 145, 100, 255),
            "glow": (0, 185, 135, 80)
        },
    ]

    pill_w = 296
    pill_h = 76
    arrow_gap = 46
    total_w = pill_w * 3 + arrow_gap * 2
    start_x = (w - total_w) // 2
    pill_y = 56

    for f_idx in range(num_frames):
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)

        # 1. Background Luxury Pure White Card with top subtle fade
        for i in range(12):
            alpha = int(255 * ((i / 12) ** 1.3))
            d.line([(0, i), (w, i)], fill=(255, 255, 255, alpha))

        # Main solid white body
        draw_gradient_v(d, [0, 12, w, h], (255, 255, 255, 255), (248, 249, 252, 255))

        # Top highlight border: Shopee Orange signature line
        d.line([(0, 12), (w, 12)], fill=(238, 77, 45, 255), width=3)
        d.line([(0, 13), (w, 13)], fill=(255, 160, 40, 200), width=1)

        # 2. Header Title: HƯỚNG DẪN MUA HÀNG TRÊN SHOPEE VIDEO
        header_text = "HƯỚNG DẪN MUA HÀNG TRÊN SHOPEE VIDEO"
        h_box = f_top.getbbox(header_text)
        hw = h_box[2] - h_box[0]
        # Red pulsing live dot
        dot_pulse = 0.5 + 0.5 * math.sin(f_idx * math.pi / 6)
        dot_alpha = int(180 + 75 * dot_pulse)
        d.ellipse([w // 2 - hw // 2 - 24, 23, w // 2 - hw // 2 - 12, 35], fill=(238, 77, 45, dot_alpha))
        d.text(((w - hw) // 2 + 4, 19), header_text, font=f_top, fill=(238, 77, 45, 255))

        # 3. Determine active step: 0, 1, or 2
        active_step = f_idx // 8
        frame_in_step = f_idx % 8
        pulse = math.sin((frame_in_step / 8) * math.pi)

        # Render 3 Steps
        curr_x = start_x
        for s_idx, s in enumerate(steps_data):
            is_active = (s_idx == active_step)

            if is_active:
                # Active box: vibrant gradient, white bold text, slight lift (-2px), shadow
                dy = -2
                bx0, by0, bx1, by1 = curr_x, pill_y + dy, curr_x + pill_w, pill_y + pill_h + dy

                # Soft shadow under active box
                d.rounded_rectangle([bx0 + 2, by0 + 4, bx1 - 2, by1 + 6], radius=16, fill=(0, 0, 0, 30))

                # Gradient fill inside active box
                draw_gradient_v(d, [bx0, by0, bx1, by1], s["active_top"], s["active_bot"])

                # Number Circle Badge (pure white circle with colored number)
                c_size = 46
                cx0 = bx0 + 14
                cy0 = by0 + (pill_h - c_size) // 2
                d.ellipse([cx0, cy0, cx0 + c_size, cy0 + c_size], fill=(255, 255, 255, 255))
                n_box = f_num.getbbox(s["num"])
                nw, nh = n_box[2] - n_box[0], n_box[3] - n_box[1]
                d.text((cx0 + (c_size - nw) // 2, cy0 + (c_size - nh) // 2 - 2), s["num"], font=f_num, fill=s["active_bot"])

                # Title in crisp white
                d.text((cx0 + c_size + 14, by0 + 23), s["title"], font=f_title, fill=(255, 255, 255, 255))

                # Vector Icon in white
                icon_cx = bx0 + pill_w - 32
                icon_cy = by0 + pill_h // 2
                s["drawer"](d, icon_cx, icon_cy, (255, 255, 255, 255))

            else:
                # Inactive box: clean light grey card, dark charcoal text
                bx0, by0, bx1, by1 = curr_x, pill_y, curr_x + pill_w, pill_y + pill_h

                d.rounded_rectangle([bx0, by0, bx1, by1], radius=16, fill=(244, 246, 250, 255), outline=(222, 226, 235, 255), width=1)

                # Muted circle
                c_size = 42
                cx0 = bx0 + 16
                cy0 = by0 + (pill_h - c_size) // 2
                d.ellipse([cx0, cy0, cx0 + c_size, cy0 + c_size], fill=(215, 220, 232, 255))
                n_box = f_num.getbbox(s["num"])
                nw, nh = n_box[2] - n_box[0], n_box[3] - n_box[1]
                d.text((cx0 + (c_size - nw) // 2, cy0 + (c_size - nh) // 2 - 2), s["num"], font=f_num, fill=(90, 95, 110, 255))

                # Charcoal title
                d.text((cx0 + c_size + 14, by0 + 24), s["title"], font=f_title, fill=(60, 65, 80, 255))

                # Muted icon
                icon_cx = bx0 + pill_w - 32
                icon_cy = by0 + pill_h // 2
                s["drawer"](d, icon_cx, icon_cy, (140, 145, 160, 255))

            curr_x += pill_w

            # Animated Chevron Arrow between boxes
            if s_idx < len(steps_data) - 1:
                arr_x = curr_x + 12
                arr_y = pill_y + pill_h // 2
                is_arr_active = (s_idx == active_step)
                draw_animated_arrow(d, arr_x, arr_y, size=18, is_active=is_arr_active, pulse_val=pulse)
                curr_x += arrow_gap

        frames.append(im)

    out_gif = OUTPUT_DIR / "bg_bottom.gif"
    frames[0].save(
        out_gif,
        save_all=True,
        append_images=frames[1:],
        duration=90,  # ~2.1s loop
        loop=0,
        disposal=2
    )
    print(f"Generated {out_gif} (1080x160 white luxury background) successfully!")

if __name__ == "__main__":
    generate_white_shopee_footer()
