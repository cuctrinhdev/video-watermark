import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path("shopee_gifs")
OUTPUT_DIR.mkdir(exist_ok=True)

FONT_PATH = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
if not Path(FONT_PATH).is_file():
    FONT_PATH = "/System/Library/Fonts/HelveticaNeue.ttc"

def get_font(size: int):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()

def draw_shopee_s_logo(draw, center_x, center_y, size, color=(255, 255, 255, 255)):
    # Draw simple elegant Shopee bag silhouette
    w = int(size * 0.7)
    h = int(size * 0.8)
    x0 = center_x - w // 2
    y0 = center_y - h // 2 + int(size * 0.1)
    x1 = x0 + w
    y1 = y0 + h
    # Bag body
    draw.rounded_rectangle([x0, y0, x1, y1], radius=max(3, int(size * 0.1)), fill=color)
    # Cutout inside handle
    hw = int(w * 0.45)
    hh = int(h * 0.35)
    hx0 = center_x - hw // 2
    hy0 = y0 - hh // 2
    draw.arc([hx0, hy0, hx0 + hw, hy0 + hh], start=180, end=0, fill=color, width=max(2, int(size * 0.08)))
    # Draw "S" curve inside bag
    s_font = get_font(int(size * 0.45))
    s_bbox = s_font.getbbox("S")
    sw = s_bbox[2] - s_bbox[0]
    sh = s_bbox[3] - s_bbox[1]
    draw.text((center_x - sw // 2, y0 + h // 2 - sh // 2 - 1), "S", font=s_font, fill=(238, 77, 45, 255))

# ── 1. SHOPEE BAG BOUNCING GIF ─────────────────────────────
def make_shopee_bag_gif():
    w, h = 220, 220
    num_frames = 18
    frames = []

    for i in range(num_frames):
        theta = (2 * math.pi * i) / num_frames
        # Bounce trajectory (squash & stretch)
        dy = int(-18 * abs(math.sin(theta)))
        squash = 0.08 * math.cos(theta * 2)
        rot = 4 * math.sin(theta)

        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)

        # Shadow on floor
        shadow_w = int(100 * (1 - dy / -40))
        shadow_h = int(14 * (1 - dy / -40))
        d.ellipse([w // 2 - shadow_w // 2, 185 - shadow_h // 2, w // 2 + shadow_w // 2, 185 + shadow_h // 2], fill=(0, 0, 0, 40))

        # Bag container stamp
        bw, bh = 140, 140
        stamp = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        sd = ImageDraw.Draw(stamp)

        # Orange outer bag
        bag_x0, bag_y0 = 20, 30
        bag_x1, bag_y1 = 120, 130
        sd.rounded_rectangle([bag_x0, bag_y0, bag_x1, bag_y1], radius=16, fill=(238, 77, 45, 255), outline=(255, 255, 255, 255), width=3)
        # Bag handle
        sd.arc([48, 12, 92, 48], start=180, end=0, fill=(238, 77, 45, 255), width=6)
        sd.arc([48, 12, 92, 48], start=180, end=0, fill=(255, 255, 255, 255), width=2)
        # White "S" Shopee symbol
        draw_shopee_s_logo(sd, 70, 80, 56)

        # Rotate & scale stamp
        curr_bw = max(10, int(bw * (1 + squash)))
        curr_bh = max(10, int(bh * (1 - squash)))
        scaled = stamp.resize((curr_bw, curr_bh), Image.BILINEAR)
        rotated = scaled.rotate(rot, resample=Image.BICUBIC, expand=True)

        rw, rh = rotated.size
        center_x = w // 2
        center_y = 105 + dy
        im.paste(rotated, (center_x - rw // 2, center_y - rh // 2), rotated)

        # Shopee text label at bottom
        f_lbl = get_font(20)
        lbl_text = "Shopee"
        lbbox = f_lbl.getbbox(lbl_text)
        lw = lbbox[2] - lbbox[0]
        # White stroke + orange fill
        d.text(((w - lw) // 2, 180), lbl_text, font=f_lbl, fill=(238, 77, 45, 255), stroke_width=3, stroke_fill=(255, 255, 255, 255))

        frames.append(im)

    frames[0].save(OUTPUT_DIR / "shopee_bag.gif", save_all=True, append_images=frames[1:], duration=70, loop=0, disposal=2)
    print("Saved shopee_bag.gif")

# ── 2. SHOPEE FREESHIP EXTRA BADGE ─────────────────────────
def make_shopee_freeship_gif():
    w, h = 300, 72
    num_frames = 20
    frames = []

    f_bold = get_font(18)
    f_sub = get_font(12)

    for i in range(num_frames):
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)

        # Pulse scale
        pulse = 1.0 + 0.025 * math.sin(2 * math.pi * i / num_frames)
        bw = int(w * 0.94 * pulse)
        bh = int(h * 0.88 * pulse)
        x0 = (w - bw) // 2
        y0 = (h - bh) // 2
        x1 = x0 + bw
        y1 = y0 + bh

        # Outer glow
        d.rounded_rectangle([x0 - 2, y0 - 2, x1 + 2, y1 + 2], radius=bh // 2, fill=(0, 0, 0, 60))
        # Green Freeship body
        d.rounded_rectangle([x0, y0, x1, y1], radius=bh // 2, fill=(0, 180, 155, 255), outline=(255, 255, 255, 255), width=2)

        # Left orange badge circle
        circle_d = bh - 6
        cx0 = x0 + 3
        cy0 = y0 + 3
        d.ellipse([cx0, cy0, cx0 + circle_d, cy0 + circle_d], fill=(238, 77, 45, 255))
        # Draw small 'S'
        draw_shopee_s_logo(d, cx0 + circle_d // 2, cy0 + circle_d // 2, 28)

        # Text labels
        d.text((cx0 + circle_d + 12, y0 + 10), "FREESHIP EXTRA", font=f_bold, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0, 100, 85, 255))
        d.text((cx0 + circle_d + 14, y0 + 34), "MIỄN PHÍ VẬN CHUYỂN", font=f_sub, fill=(255, 255, 220, 255))

        # Shimmer highlight bar passing left to right
        shine_pos = int(-40 + (w + 80) * (i / num_frames))
        shine_overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shine_overlay)
        sd.polygon([
            (shine_pos, y0),
            (shine_pos + 20, y0),
            (shine_pos + 45, y1),
            (shine_pos + 25, y1)
        ], fill=(255, 255, 255, 75))
        im = Image.alpha_composite(im, shine_overlay)

        frames.append(im)

    frames[0].save(OUTPUT_DIR / "shopee_freeship.gif", save_all=True, append_images=frames[1:], duration=75, loop=0, disposal=2)
    print("Saved shopee_freeship.gif")

# ── 3. SHOPEE LIVE PULSING BADGE ───────────────────────────
def make_shopee_live_gif():
    w, h = 240, 70
    num_frames = 16
    frames = []

    f_title = get_font(20)
    f_tag = get_font(13)

    for i in range(num_frames):
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)

        bx0, by0 = 8, 8
        bx1, by1 = w - 8, h - 8
        # Gradient / Orange pill
        d.rounded_rectangle([bx0, by0, bx1, by1], radius=(by1 - by0) // 2, fill=(238, 77, 45, 255), outline=(255, 255, 255, 255), width=2)

        # Animated sound equalizer bars
        bar_x = bx0 + 20
        bar_base_y = by1 - 18
        for b_idx in range(4):
            # Dynamic height oscillation
            phase = (i / num_frames) * 2 * math.pi + b_idx * 1.2
            bar_h = int(8 + 14 * abs(math.sin(phase)))
            d.rounded_rectangle([bar_x + b_idx * 7, bar_base_y - bar_h, bar_x + b_idx * 7 + 4, bar_base_y], radius=2, fill=(255, 255, 255, 255))

        # Shopee LIVE text
        d.text((bar_x + 36, by0 + 8), "Shopee", font=f_title, fill=(255, 255, 255, 255))
        # LIVE pill tag in bright red/yellow
        live_blink = abs(math.sin(math.pi * i / num_frames))
        live_bg = (255, 230, 0, 255) if live_blink > 0.5 else (255, 255, 255, 255)
        d.rounded_rectangle([w - 68, by0 + 13, w - 16, by1 - 13], radius=6, fill=live_bg)
        d.text((w - 60, by0 + 14), "LIVE", font=f_tag, fill=(220, 30, 30, 255))

        frames.append(im)

    frames[0].save(OUTPUT_DIR / "shopee_live.gif", save_all=True, append_images=frames[1:], duration=80, loop=0, disposal=2)
    print("Saved shopee_live.gif")

# ── 4. SHOPEE VOUCHER TICKET BADGE ─────────────────────────
def make_shopee_voucher_gif():
    w, h = 280, 75
    num_frames = 16
    frames = []

    f_bold = get_font(18)
    f_sub = get_font(13)

    for i in range(num_frames):
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)

        hover = int(3 * math.sin(2 * math.pi * i / num_frames))
        y0 = 8 + hover
        y1 = h - 8 + hover
        x0, x1 = 8, w - 8

        # Main coupon body
        d.rounded_rectangle([x0, y0, x1, y1], radius=10, fill=(255, 90, 40, 255), outline=(255, 255, 255, 255), width=2)

        # Ticket semicircular cutout on left & right edge
        mid_y = (y0 + y1) // 2
        d.ellipse([x0 - 8, mid_y - 8, x0 + 8, mid_y + 8], fill=(0, 0, 0, 0))
        d.ellipse([x1 - 8, mid_y - 8, x1 + 8, mid_y + 8], fill=(0, 0, 0, 0))

        # Divider dashed line
        div_x = x0 + 60
        for dy in range(y0 + 6, y1 - 6, 7):
            d.line([(div_x, dy), (div_x, dy + 4)], fill=(255, 255, 255, 180), width=2)

        # Left star & 'S'
        draw_shopee_s_logo(d, x0 + 32, mid_y, 34)

        # Text
        d.text((div_x + 14, y0 + 8), "VOUCHER SHOPEE", font=f_bold, fill=(255, 255, 255, 255))
        d.text((div_x + 16, y0 + 32), "GIẢM ĐẾN 50% - MUA NGAY", font=f_sub, fill=(255, 240, 180, 255))

        # Star sparkle twinkle
        star_sparkle = abs(math.sin(math.pi * i / num_frames))
        if star_sparkle > 0.4:
            d.text((w - 28, y0 + 4), "✦", font=f_bold, fill=(255, 255, 255, int(255 * star_sparkle)))

        frames.append(im)

    frames[0].save(OUTPUT_DIR / "shopee_voucher.gif", save_all=True, append_images=frames[1:], duration=85, loop=0, disposal=2)
    print("Saved shopee_voucher.gif")

if __name__ == "__main__":
    make_shopee_bag_gif()
    make_shopee_freeship_gif()
    make_shopee_live_gif()
    make_shopee_voucher_gif()
    print("All Shopee GIFs generated successfully!")
