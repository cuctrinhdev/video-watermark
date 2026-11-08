import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUTPUT_DIR = Path("option/template3")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FONTS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
]
FONT_PATH = next((p for p in FONTS if Path(p).is_file()), "/System/Library/Fonts/Supplemental/Arial Bold.ttf")

def get_font(size: int):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()

def generate_clean_footer():
    w, h = 1080, 150
    num_frames = 24  # 8 frames per step (8 * 3 = 24 frames)
    frames = []

    f_top = get_font(20)
    f_num = get_font(19)
    f_title = get_font(23)

    steps = [
        ("1", "Bấm Mua Ngay"),
        ("2", "Chọn Voucher"),
        ("3", "Đặt Hàng"),
    ]

    btn_w = 302
    btn_h = 58
    arrow_gap = 38
    total_w = btn_w * 3 + arrow_gap * 2
    start_x = (w - total_w) // 2
    btn_y = 56
    radius = 16

    for f_idx in range(num_frames):
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)

        # 1. Silky smooth top ambient fade (NO harsh border line!)
        fade_h = 14
        for y in range(fade_h):
            ratio = (y / fade_h) ** 1.8
            a = int(255 * ratio)
            d.line([(0, y), (w, y)], fill=(255, 255, 255, a))

        # Solid pure white card background
        d.rectangle([0, fade_h, w, h], fill=(255, 255, 255, 255))

        # 2. Header text: Clean Shopee Orange typography, no noisy flashing dots
        header_text = "HƯỚNG DẪN MUA HÀNG TRÊN SHOPEE VIDEO"
        h_box = f_top.getbbox(header_text)
        hw = h_box[2] - h_box[0]
        d.text(((w - hw) // 2, 18), header_text, font=f_top, fill=(238, 77, 45, 255))

        # 3. Determine active step: 0, 1, or 2
        active_step = f_idx // 8
        frame_in_step = f_idx % 8
        pulse = 0.5 + 0.5 * math.sin((frame_in_step / 8) * math.pi * 2)

        curr_x = start_x
        for s_idx, (num, text) in enumerate(steps):
            is_active = (s_idx == active_step)
            bx0, by0, bx1, by1 = curr_x, btn_y, curr_x + btn_w, btn_y + btn_h

            # Content centering: badge + gap + text
            c_size = 32
            gap = 12
            tb = f_title.getbbox(text)
            txt_w, txt_h = tb[2] - tb[0], tb[3] - tb[1]
            content_w = c_size + gap + txt_w
            cx0 = bx0 + (btn_w - content_w) // 2
            cy0 = by0 + (btn_h - c_size) // 2

            if is_active:
                # Soft pulsing ambient shadow
                glow_alpha = int(70 + 40 * pulse)
                shadow = Image.new("RGBA", (btn_w + 16, btn_h + 16), (0, 0, 0, 0))
                sdraw = ImageDraw.Draw(shadow)
                sdraw.rounded_rectangle([8, 8, 8 + btn_w, 8 + btn_h], radius=radius, fill=(238, 77, 45, glow_alpha))
                shadow = shadow.filter(ImageFilter.GaussianBlur(5))
                im.paste(shadow, (bx0 - 8, by0 - 4), shadow)

                # Vibrant Shopee Orange gradient button
                pill = Image.new("RGBA", (btn_w, btn_h), (0, 0, 0, 0))
                pdraw = ImageDraw.Draw(pill)
                for py in range(btn_h):
                    r_ratio = py / btn_h
                    r = int(255 * (1 - r_ratio) + 238 * r_ratio)
                    g = int(87 * (1 - r_ratio) + 77 * r_ratio)
                    b = int(34 * (1 - r_ratio) + 45 * r_ratio)
                    pdraw.line([(0, py), (btn_w, py)], fill=(r, g, b, 255))
                mask = Image.new("L", (btn_w, btn_h), 0)
                ImageDraw.Draw(mask).rounded_rectangle([0, 0, btn_w, btn_h], radius=radius, fill=255)
                im.paste(pill, (bx0, by0), mask)

                # Pure white badge with bold orange number
                d.ellipse([cx0, cy0, cx0 + c_size, cy0 + c_size], fill=(255, 255, 255, 255))
                nb = f_num.getbbox(num)
                nw, nh = nb[2] - nb[0], nb[3] - nb[1]
                d.text((cx0 + (c_size - nw) // 2, cy0 + (c_size - nh) // 2 - 2), num, font=f_num, fill=(238, 77, 45, 255))

                # Crisp white title
                d.text((cx0 + c_size + gap, by0 + (btn_h - txt_h) // 2 - 2), text, font=f_title, fill=(255, 255, 255, 255))
            else:
                # Inactive clean modern pill
                d.rounded_rectangle([bx0, by0, bx1, by1], radius=radius, fill=(247, 248, 250, 255), outline=(226, 230, 238, 255), width=1)

                # Crisp white circle badge with subtle border
                d.ellipse([cx0, cy0, cx0 + c_size, cy0 + c_size], fill=(255, 255, 255, 255), outline=(218, 222, 230, 255), width=1)
                nb = f_num.getbbox(num)
                nw, nh = nb[2] - nb[0], nb[3] - nb[1]
                d.text((cx0 + (c_size - nw) // 2, cy0 + (c_size - nh) // 2 - 2), num, font=f_num, fill=(107, 114, 128, 255))

                # Dark sleek title
                d.text((cx0 + c_size + gap, by0 + (btn_h - txt_h) // 2 - 2), text, font=f_title, fill=(31, 41, 55, 255))

            curr_x += btn_w

            # Minimalist chevron arrow between buttons
            if s_idx < 2:
                ax = curr_x + 13
                ay = btn_y + btn_h // 2
                is_arr_active = (s_idx == active_step)
                if is_arr_active:
                    arr_col = (238, 77, 45, 255)
                    # Double chevron when active
                    d.line([(ax, ay - 7), (ax + 7, ay)], fill=arr_col, width=2)
                    d.line([(ax + 7, ay), (ax, ay + 7)], fill=arr_col, width=2)
                    d.line([(ax + 8, ay - 7), (ax + 15, ay)], fill=arr_col, width=2)
                    d.line([(ax + 15, ay), (ax + 8, ay + 7)], fill=arr_col, width=2)
                else:
                    arr_col = (203, 213, 225, 255)
                    d.line([(ax + 4, ay - 7), (ax + 11, ay)], fill=arr_col, width=2)
                    d.line([(ax + 11, ay), (ax + 4, ay + 7)], fill=arr_col, width=2)
                curr_x += arrow_gap

        frames.append(im)

    out_gif = OUTPUT_DIR / "bg_bottom.gif"
    frames[0].save(
        out_gif,
        save_all=True,
        append_images=frames[1:],
        duration=90,  # ~2.16s loop
        loop=0,
        disposal=2
    )
    print(f"Generated {out_gif} (1080x150 modern luxury clean footer) successfully!")

if __name__ == "__main__":
    generate_clean_footer()

