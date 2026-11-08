from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path("option/template3")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Remove bg_top.png so top is completely clear and video is not covered
top_file = OUTPUT_DIR / "bg_top.png"
if top_file.exists():
    top_file.unlink()
    print("Removed bg_top.png (no top clutter)")

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

def create_bottom_steps_bg():
    w, h = 1080, 190
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    # 1. Subtle top fade transition (15px)
    for i in range(15):
        alpha = int(240 * ((i / 15) ** 1.2))
        d.line([(0, i), (w, i)], fill=(20, 20, 26, alpha))

    # 2. Main bar background (sleek dark semi-transparent with Shopee orange tint)
    draw_gradient_v(d, [0, 15, w, h], (26, 26, 34, 245), (14, 14, 20, 250))

    # Top highlight line (Shopee warm gold / orange glow)
    d.line([(0, 15), (w, 15)], fill=(238, 77, 45, 230), width=3)
    d.line([(0, 16), (w, 16)], fill=(255, 180, 0, 180), width=1)

    # 3. Small top category label
    f_lbl = get_font(20)
    lbl_text = "HƯỚNG DẪN MUA HÀNG TRÊN SHOPEE VIDEO"
    l_bbox = f_lbl.getbbox(lbl_text)
    lw = l_bbox[2] - l_bbox[0]
    d.text(((w - lw) // 2, 26), lbl_text, font=f_lbl, fill=(255, 200, 100, 255))

    # 4. Three Steps Pills
    # Step 1: Mua Ngay
    # Step 2: Chọn Mã Voucher
    # Step 3: Đặt Hàng
    steps = [
        {"num": "1", "title": "Bấm Mua Ngay", "icon": "🛒", "bg": (238, 77, 45, 255), "text_col": (255, 255, 255, 255)},
        {"num": "2", "title": "Chọn Voucher", "icon": "🎟️", "bg": (255, 175, 0, 255), "text_col": (0, 0, 0, 255)},
        {"num": "3", "title": "Đặt Hàng", "icon": "📦", "bg": (0, 175, 140, 255), "text_col": (255, 255, 255, 255)},
    ]

    pill_w = 295
    pill_h = 76
    arrow_w = 40
    total_w = pill_w * 3 + arrow_w * 2 + 20
    start_x = (w - total_w) // 2
    pill_y = 66

    f_step_num = get_font(20)
    f_step_title = get_font(26)
    f_arrow = get_font(34)

    curr_x = start_x
    for i, step in enumerate(steps):
        # Pill Container
        d.rounded_rectangle([curr_x, pill_y, curr_x + pill_w, pill_y + pill_h], radius=16, fill=(35, 38, 52, 230), outline=(255, 255, 255, 60), width=2)

        # Left Step Number Circle Badge
        c_size = 46
        cx0 = curr_x + 14
        cy0 = pill_y + (pill_h - c_size) // 2
        d.ellipse([cx0, cy0, cx0 + c_size, cy0 + c_size], fill=step["bg"])
        n_bbox = f_step_num.getbbox(step["num"])
        nw = n_bbox[2] - n_bbox[0]
        nh = n_bbox[3] - n_bbox[1]
        d.text((cx0 + (c_size - nw) // 2, cy0 + (c_size - nh) // 2 - 2), step["num"], font=f_step_num, fill=step["text_col"])

        # Step Title + Icon
        t_str = f"{step['title']} {step['icon']}"
        t_bbox = f_step_title.getbbox(t_str)
        tw = t_bbox[2] - t_bbox[0]
        d.text((cx0 + c_size + 14, pill_y + 22), t_str, font=f_step_title, fill=(255, 255, 255, 255))

        curr_x += pill_w

        # Draw connecting arrow between steps
        if i < len(steps) - 1:
            arr_x = curr_x + 10
            d.text((arr_x + 2, pill_y + 16), "➔", font=f_arrow, fill=(238, 77, 45, 255))
            curr_x += arrow_w + 10

    # 5. Bottom subtle note
    f_sub = get_font(18)
    sub_txt = "⚡ Giảm đến 50% & Miễn phí vận chuyển khi đặt hàng trực tiếp trong video ⚡"
    s_bbox = f_sub.getbbox(sub_txt)
    sw = s_bbox[2] - s_bbox[0]
    d.text(((w - sw) // 2, 154), sub_txt, font=f_sub, fill=(180, 190, 210, 200))

    out_file = OUTPUT_DIR / "bg_bottom.png"
    im.save(out_file, "PNG")
    print(f"Created {out_file} (1080x190)")

if __name__ == "__main__":
    create_bottom_steps_bg()
