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
    # Clean vector shopping cart
    draw.line([(cx - 14, cy - 7), (cx - 10, cy - 7)], fill=color, width=3)
    draw.line([(cx - 10, cy - 7), (cx - 6, cy + 6)], fill=color, width=3)
    draw.line([(cx - 6, cy + 6), (cx + 12, cy + 6)], fill=color, width=3)
    draw.line([(cx + 12, cy + 6), (cx + 16, cy - 4)], fill=color, width=3)
    draw.line([(cx - 8, cy - 4), (cx + 16, cy - 4)], fill=color, width=3)
    draw.ellipse([cx - 5, cy + 9, cx - 1, cy + 13], fill=color)
    draw.ellipse([cx + 7, cy + 9, cx + 11, cy + 13], fill=color)

def draw_vector_voucher(draw, cx, cy, color=(255, 255, 255, 255)):
    # Clean vector ticket coupon
    w, h = 30, 20
    x0, y0, x1, y1 = cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2
    draw.rounded_rectangle([x0, y0, x1, y1], radius=4, outline=color, width=2)
    draw.line([(cx - 4, cy + 4), (cx + 4, cy - 4)], fill=color, width=2)
    draw.ellipse([cx - 5, cy - 5, cx - 2, cy - 2], fill=color)
    draw.ellipse([cx + 2, cy + 2, cx + 5, cy + 5], fill=color)

def draw_vector_package(draw, cx, cy, color=(255, 255, 255, 255)):
    # Clean vector delivery parcel
    w, h = 26, 22
    x0, y0, x1, y1 = cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2
    draw.rounded_rectangle([x0, y0, x1, y1], radius=4, outline=color, width=2)
    draw.line([(cx, y0), (cx, y1)], fill=color, width=2)
    draw.line([(x0, cy - 2), (x1, cy - 2)], fill=color, width=2)

def draw_animated_arrow(draw, x, y, size=18, is_active=False, pulse_val=0.0):
    half_h = size // 2
    w = int(size * 0.55)
    if is_active:
        # 2 glowing chevrons running
        c1 = (255, 220, 80, 255)
        c2 = (255, 90, 40, int(150 + 105 * pulse_val))
        draw.line([(x, y - half_h), (x + w, y)], fill=c1, width=3)
        draw.line([(x + w, y), (x, y + half_h)], fill=c1, width=3)
        draw.line([(x + 12, y - half_h), (x + 12 + w, y)], fill=c2, width=3)
        draw.line([(x + 12 + w, y), (x + 12, y + half_h)], fill=c2, width=3)
    else:
        c_dim = (90, 95, 115, 140)
        draw.line([(x + 5, y - half_h), (x + 5 + w, y)], fill=c_dim, width=2)
        draw.line([(x + 5 + w, y), (x + 5, y + half_h)], fill=c_dim, width=2)

def generate_active_steps_gif():
    w, h = 1080, 200
    num_frames = 24  # 8 frames per step (8 * 3 = 24 frames)
    frames = []

    f_top = get_font(20)
    f_num = get_font(22)
    f_title = get_font(24)
    f_sub = get_font(17)

    steps_data = [
        {
            "num": "1",
            "title": "Bấm Mua Ngay",
            "drawer": draw_vector_cart,
            "active_top": (255, 85, 45, 255),
            "active_bot": (215, 40, 15, 255),
            "glow": (255, 80, 40, 160)
        },
        {
            "num": "2",
            "title": "Chọn Voucher",
            "drawer": draw_vector_voucher,
            "active_top": (255, 190, 10, 255),
            "active_bot": (230, 135, 0, 255),
            "glow": (255, 190, 10, 160)
        },
        {
            "num": "3",
            "title": "Đặt Hàng",
            "drawer": draw_vector_package,
            "active_top": (0, 195, 145, 255),
            "active_bot": (0, 150, 110, 255),
            "glow": (0, 195, 145, 160)
        },
    ]

    pill_w = 296
    pill_h = 76
    arrow_gap = 46
    total_w = pill_w * 3 + arrow_gap * 2
    start_x = (w - total_w) // 2
    pill_y = 66

    for f_idx in range(num_frames):
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)

        # 1. Background dark glassy bar
        for i in range(16):
            alpha = int(245 * ((i / 16) ** 1.3))
            d.line([(0, i), (w, i)], fill=(16, 18, 26, alpha))

        draw_gradient_v(d, [0, 16, w, h], (20, 22, 30, 245), (10, 12, 18, 252))

        # Top highlight border
        d.line([(0, 16), (w, 16)], fill=(238, 77, 45, 240), width=3)
        d.line([(0, 17), (w, 17)], fill=(255, 195, 0, 160), width=1)

        # 2. Top Category Badge Header
        header_text = "HƯỚNG DẪN MUA HÀNG TRÊN SHOPEE VIDEO"
        h_box = f_top.getbbox(header_text)
        hw = h_box[2] - h_box[0]
        # Red pulsing live dot
        dot_pulse = 0.5 + 0.5 * math.sin(f_idx * math.pi / 6)
        dot_alpha = int(180 + 75 * dot_pulse)
        d.ellipse([w // 2 - hw // 2 - 24, 28, w // 2 - hw // 2 - 12, 40], fill=(255, 45, 30, dot_alpha))
        d.text(((w - hw) // 2 + 6, 24), header_text, font=f_top, fill=(255, 220, 110, 255))

        # 3. Determine active step: 0, 1, or 2
        active_step = f_idx // 8
        frame_in_step = f_idx % 8
        # Breathing pulse intensity inside the active step (0.0 to 1.0)
        pulse = math.sin((frame_in_step / 8) * math.pi)

        # Render the 3 steps
        curr_x = start_x
        for s_idx, s in enumerate(steps_data):
            is_active = (s_idx == active_step)

            if is_active:
                # Active box: slight vertical lift (-2px), vibrant gradient fill, bright white border with outer glow
                dy = -2
                bx0, by0, bx1, by1 = curr_x, pill_y + dy, curr_x + pill_w, pill_y + pill_h + dy

                # Outer glow ring
                glow_col = s["glow"]
                d.rounded_rectangle([bx0 - 3, by0 - 3, bx1 + 3, by1 + 3], radius=18, fill=(*glow_col[:3], 50))

                # Gradient fill inside active box
                draw_gradient_v(d, [bx0, by0, bx1, by1], s["active_top"], s["active_bot"])

                # Bright white border
                d.rounded_rectangle([bx0, by0, bx1, by1], radius=16, outline=(255, 255, 255, 255), width=2)

                # Number Circle Badge (solid white with color text for maximum pop)
                c_size = 46
                cx0 = bx0 + 14
                cy0 = by0 + (pill_h - c_size) // 2
                d.ellipse([cx0, cy0, cx0 + c_size, cy0 + c_size], fill=(255, 255, 255, 255))
                n_box = f_num.getbbox(s["num"])
                nw, nh = n_box[2] - n_box[0], n_box[3] - n_box[1]
                d.text((cx0 + (c_size - nw) // 2, cy0 + (c_size - nh) // 2 - 2), s["num"], font=f_num, fill=s["active_bot"])

                # Title in crisp bold white with subtle dark drop shadow
                d.text((cx0 + c_size + 14 + 1, by0 + 23 + 1), s["title"], font=f_title, fill=(0, 0, 0, 160))
                d.text((cx0 + c_size + 14, by0 + 23), s["title"], font=f_title, fill=(255, 255, 255, 255))

                # Vector Icon
                icon_cx = bx0 + pill_w - 32
                icon_cy = by0 + pill_h // 2
                s["drawer"](d, icon_cx, icon_cy, (255, 255, 255, 255))

            else:
                # Inactive box: sleek muted dark glass
                bx0, by0, bx1, by1 = curr_x, pill_y, curr_x + pill_w, pill_y + pill_h

                d.rounded_rectangle([bx0, by0, bx1, by1], radius=16, fill=(28, 30, 42, 210), outline=(255, 255, 255, 45), width=1)

                # Dimmed circle
                c_size = 42
                cx0 = bx0 + 16
                cy0 = by0 + (pill_h - c_size) // 2
                d.ellipse([cx0, cy0, cx0 + c_size, cy0 + c_size], fill=(45, 48, 65, 220))
                n_box = f_num.getbbox(s["num"])
                nw, nh = n_box[2] - n_box[0], n_box[3] - n_box[1]
                d.text((cx0 + (c_size - nw) // 2, cy0 + (c_size - nh) // 2 - 2), s["num"], font=f_num, fill=(160, 165, 185, 255))

                # Dimmed title
                d.text((cx0 + c_size + 14, by0 + 24), s["title"], font=f_title, fill=(175, 180, 200, 230))

                # Dimmed vector icon
                icon_cx = bx0 + pill_w - 32
                icon_cy = by0 + pill_h // 2
                s["drawer"](d, icon_cx, icon_cy, (160, 165, 185, 180))

            curr_x += pill_w

            # Render Animated Chevron Arrow between boxes
            if s_idx < len(steps_data) - 1:
                arr_x = curr_x + 12
                arr_y = pill_y + pill_h // 2
                # Arrow is active when its left step is active or transitioning
                is_arr_active = (s_idx == active_step)
                draw_animated_arrow(d, arr_x, arr_y, size=18, is_active=is_arr_active, pulse_val=pulse)
                curr_x += arrow_gap

        # 4. Clean Subtitle at Bottom
        sub_text = "⚡ Giảm đến 50%  •  Miễn phí vận chuyển  •  Giao hàng toàn quốc ⚡"
        s_box = f_sub.getbbox(sub_text)
        sw = s_box[2] - s_box[0]
        d.text(((w - sw) // 2, 160), sub_text, font=f_sub, fill=(200, 210, 230, 210))

        frames.append(im)

    out_gif = OUTPUT_DIR / "bg_bottom.gif"
    frames[0].save(
        out_gif,
        save_all=True,
        append_images=frames[1:],
        duration=90,  # 90ms * 24 = 2160ms (~2.1s loop)
        loop=0,
        disposal=2
    )
    print(f"Generated {out_gif} with {len(frames)} active-step frames successfully!")

if __name__ == "__main__":
    generate_active_steps_gif()
