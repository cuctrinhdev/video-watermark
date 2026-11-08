import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUTPUT_DIR = Path("option/template3")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Find clean bold fonts on macOS
FONTS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]
FONT_PATH = next((p for p in FONTS if Path(p).is_file()), "/System/Library/Fonts/HelveticaNeue.ttc")

def get_font(size: int, bold: bool = True):
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

def draw_shopee_s_logo(draw, center_x, center_y, size, bag_col=(255, 255, 255, 255), s_col=(238, 77, 45, 255)):
    w = int(size * 0.72)
    h = int(size * 0.82)
    x0 = center_x - w // 2
    y0 = center_y - h // 2 + int(size * 0.1)
    x1 = x0 + w
    y1 = y0 + h
    draw.rounded_rectangle([x0, y0, x1, y1], radius=max(3, int(size * 0.12)), fill=bag_col)
    hw = int(w * 0.46)
    hh = int(h * 0.36)
    hx0 = center_x - hw // 2
    hy0 = y0 - hh // 2
    draw.arc([hx0, hy0, hx0 + hw, hy0 + hh], start=180, end=0, fill=bag_col, width=max(2, int(size * 0.08)))
    s_font = get_font(int(size * 0.44))
    s_bbox = s_font.getbbox("S")
    sw = s_bbox[2] - s_bbox[0]
    sh = s_bbox[3] - s_bbox[1]
    draw.text((center_x - sw // 2, y0 + h // 2 - sh // 2 - 2), "S", font=s_font, fill=s_col)

# ════════════════════════════════════════════════════════════════
# 1. TOP BACKGROUND (1080 x 320)
# ════════════════════════════════════════════════════════════════
def create_top_bg():
    w, h = 1080, 320
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    # 1. Background gradient (Shopee signature deep orange)
    draw_gradient_v(d, [0, 0, w, h - 25], (255, 87, 34, 255), (218, 52, 21, 255))

    # Bottom shadow / fade transition
    for i in range(25):
        alpha = int(255 * (1.0 - (i / 25) ** 1.3))
        d.line([(0, h - 25 + i), (w, h - 25 + i)], fill=(218, 52, 21, alpha))

    # 2. Golden border accent line at the bottom
    d.line([(0, h - 25), (w, h - 25)], fill=(255, 230, 0, 220), width=3)

    # 3. Top Status Pill (Shopee Video Live/Mall badge)
    pill_w, pill_h = 380, 44
    pill_x0 = (w - pill_w) // 2
    pill_y0 = 24
    d.rounded_rectangle([pill_x0, pill_y0, pill_x0 + pill_w, pill_y0 + pill_h], radius=22, fill=(0, 0, 0, 70), outline=(255, 255, 255, 120), width=2)
    # Red LIVE blinking dot
    d.ellipse([pill_x0 + 18, pill_y0 + 13, pill_x0 + 36, pill_y0 + 31], fill=(255, 40, 40, 255), outline=(255, 255, 255, 255), width=2)
    f_badge = get_font(21)
    d.text((pill_x0 + 46, pill_y0 + 10), "SHOPEE VIDEO • SĂN SALE", font=f_badge, fill=(255, 255, 255, 255))

    # 4. Main Headline: FLASH SALE ĐỘC QUYỀN
    f_main = get_font(52)
    main_text = "⚡ FLASH SALE HÔM NAY ⚡"
    m_bbox = f_main.getbbox(main_text)
    mw = m_bbox[2] - m_bbox[0]
    mx = (w - mw) // 2
    my = 88
    # 3D shadow & crisp stroke
    d.text((mx + 2, my + 3), main_text, font=f_main, fill=(140, 20, 0, 200))
    d.text((mx, my), main_text, font=f_main, fill=(255, 235, 59, 255), stroke_width=3, stroke_fill=(180, 20, 0, 255))

    # 5. Three Trust/Discount Badges
    badges = [
        {"icon": "🚚", "text": "FREESHIP 0Đ", "bg": (0, 160, 140, 255)},
        {"icon": "🎟️", "text": "GIẢM ĐẾN 50%", "bg": (230, 40, 30, 255)},
        {"icon": "⭐", "text": "CHÍNH HÃNG 100%", "bg": (195, 120, 0, 255)},
    ]
    b_w = 310
    b_h = 58
    spacing = 24
    start_x = (w - (b_w * 3 + spacing * 2)) // 2
    by0 = 175

    for idx, b in enumerate(badges):
        bx0 = start_x + idx * (b_w + spacing)
        # Badge body
        d.rounded_rectangle([bx0, by0, bx0 + b_w, by0 + b_h], radius=14, fill=b["bg"], outline=(255, 255, 255, 220), width=2)
        # Badge text
        f_b = get_font(25)
        full_lbl = f"{b['icon']} {b['text']}"
        l_bbox = f_b.getbbox(full_lbl)
        lw = l_bbox[2] - l_bbox[0]
        d.text((bx0 + (b_w - lw) // 2, by0 + 14), full_lbl, font=f_b, fill=(255, 255, 255, 255))

    # Decorative sparkles
    f_star = get_font(28)
    d.text((45, 95), "✦", font=f_star, fill=(255, 240, 150, 220))
    d.text((w - 75, 95), "✦", font=f_star, fill=(255, 240, 150, 220))

    out_file = OUTPUT_DIR / "bg_top.png"
    im.save(out_file, "PNG")
    print(f"Created {out_file}")

# ════════════════════════════════════════════════════════════════
# 2. BOTTOM BACKGROUND (1080 x 360)
# ════════════════════════════════════════════════════════════════
def create_bottom_bg():
    w, h = 1080, 360
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    # Top fade transition
    for i in range(25):
        alpha = int(255 * ((i / 25) ** 1.3))
        d.line([(0, i), (w, i)], fill=(218, 52, 21, alpha))

    # Main gradient body
    draw_gradient_v(d, [0, 25, w, h], (218, 52, 21, 255), (170, 30, 8, 255))

    # Golden border accent line at the top
    d.line([(0, 25), (w, 25)], fill=(255, 230, 0, 220), width=3)

    # 1. Headline Callout
    f_callout = get_font(30)
    callout_txt = "👇 ƯU ĐÃI ĐỘC QUYỀN TRÊN VIDEO — SỐ LƯỢNG CÓ HẠN 👇"
    c_bbox = f_callout.getbbox(callout_txt)
    cw = c_bbox[2] - c_bbox[0]
    d.text(((w - cw) // 2, 45), callout_txt, font=f_callout, fill=(255, 245, 170, 255), stroke_width=1, stroke_fill=(120, 20, 0, 255))

    # 2. Large Interactive Shopping Cart CTA Card
    card_w = 980
    card_h = 135
    card_x0 = (w - card_w) // 2
    card_y0 = 95
    # Card glow & body
    d.rounded_rectangle([card_x0 - 2, card_y0 - 2, card_x0 + card_w + 2, card_y0 + card_h + 2], radius=24, fill=(255, 220, 0, 80))
    d.rounded_rectangle([card_x0, card_y0, card_x0 + card_w, card_y0 + card_h], radius=22, fill=(255, 255, 255, 255), outline=(255, 215, 0, 255), width=3)

    # Left Cart Badge (Orange circle)
    c_rad = 46
    cx = card_x0 + 65
    cy = card_y0 + card_h // 2
    d.ellipse([cx - c_rad, cy - c_rad, cx + c_rad, cy + c_rad], fill=(238, 77, 45, 255))
    # Draw Shopee Bag in white
    draw_shopee_s_logo(d, cx, cy, 54, bag_col=(255, 255, 255, 255), s_col=(238, 77, 45, 255))

    # CTA Text inside card
    f_cta_main = get_font(38)
    f_cta_sub = get_font(25)

    cta_main_text = "👉 BẤM VÀO GIỎ HÀNG GÓC TRÁI"
    d.text((cx + c_rad + 20, card_y0 + 20), cta_main_text, font=f_cta_main, fill=(220, 35, 15, 255))

    cta_sub_text = "Nhận Voucher Giảm 50% + Miễn Phí Giao Hàng"
    d.text((cx + c_rad + 22, card_y0 + 74), cta_sub_text, font=f_cta_sub, fill=(70, 70, 70, 255))

    # Right side pulse button "MUA NGAY"
    btn_w, btn_h = 210, 84
    btn_x0 = card_x0 + card_w - btn_w - 20
    btn_y0 = card_y0 + (card_h - btn_h) // 2
    d.rounded_rectangle([btn_x0, btn_y0, btn_x0 + btn_w, btn_y0 + btn_h], radius=18, fill=(238, 77, 45, 255), outline=(255, 255, 255, 255), width=2)
    f_btn = get_font(30)
    btn_lbl = "MUA NGAY"
    b_bbox = f_btn.getbbox(btn_lbl)
    bw = b_bbox[2] - b_bbox[0]
    d.text((btn_x0 + (btn_w - bw) // 2, btn_y0 + 24), btn_lbl, font=f_btn, fill=(255, 255, 255, 255))

    # 3. Bottom Trust Guarantee Bar
    f_trust = get_font(23)
    trust_text = "🛡️ Đổi trả miễn phí 15 ngày  •  Kiểm tra hàng trước khi nhận  •  Hàng chính hãng 100%"
    t_bbox = f_trust.getbbox(trust_text)
    tw = t_bbox[2] - t_bbox[0]
    d.text(((w - tw) // 2, 260), trust_text, font=f_trust, fill=(255, 240, 220, 240))

    # Final copyright/safe margin hint
    f_sub2 = get_font(18)
    sub2 = "⚡ Giá ưu đãi chỉ áp dụng khi mua trực tiếp qua Shopee Video này ⚡"
    s2_bbox = f_sub2.getbbox(sub2)
    s2_w = s2_bbox[2] - s2_bbox[0]
    d.text(((w - s2_w) // 2, 305), sub2, font=f_sub2, fill=(255, 210, 180, 200))

    out_file = OUTPUT_DIR / "bg_bottom.png"
    im.save(out_file, "PNG")
    print(f"Created {out_file}")

if __name__ == "__main__":
    create_top_bg()
    create_bottom_bg()
    print("All Shopee Backgrounds created successfully!")
