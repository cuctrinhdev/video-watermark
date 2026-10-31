import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops

def animate_static_logo(input_path: Path, anim_type: str, output_path: Path) -> Path:
    """
    Takes a static image (PNG/JPG/WebP) and generates a smooth looping animated GIF
    based on anim_type:
      - 'spin': 360° continuous rotation
      - 'pulse': Heartbeat pulse (scaling up/down)
      - 'shimmer': Glossy specular shine sweeping across the logo
      - 'bounce': Squash & stretch bounce with animated floor shadow
      - 'wiggle': Gentle floating sway / oscillation
      - 'fade': Breathing glow / opacity oscillation
    Returns output_path if animated, or input_path if 'none'/error.
    """
    if not input_path or not input_path.is_file():
        return input_path

    if not anim_type or anim_type == "none":
        return input_path

    try:
        base = Image.open(input_path).convert("RGBA")
    except Exception:
        return input_path

    w, h = base.size
    # If image is too large, resize to max 400px for speed and crispness
    max_dim = 400
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        w, h = max(10, int(w * scale)), max(10, int(h * scale))
        base = base.resize((w, h), Image.BICUBIC)

    frames = []
    num_frames = 18

    if anim_type == "spin":
        num_frames = 30
        diag = int(math.hypot(w, h)) + 8
        canvas = Image.new("RGBA", (diag, diag), (0, 0, 0, 0))
        canvas.paste(base, ((diag - w) // 2, (diag - h) // 2), base)
        for i in range(num_frames):
            angle = -360.0 * (i / num_frames)
            frames.append(canvas.rotate(angle, resample=Image.BICUBIC))
        duration = 60

    elif anim_type == "pulse":
        num_frames = 24
        cw, ch = int(w * 1.16), int(h * 1.16)
        for i in range(num_frames):
            s = 1.0 + 0.07 * math.sin(2 * math.pi * i / num_frames)
            sw, sh = max(1, int(w * s)), max(1, int(h * s))
            resized = base.resize((sw, sh), Image.BICUBIC)
            c = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
            c.paste(resized, ((cw - sw) // 2, (ch - sh) // 2), resized)
            frames.append(c)
        duration = 70

    elif anim_type == "shimmer":
        num_frames = 24
        alpha = base.split()[3]
        band_w = max(24, w // 4)
        for i in range(num_frames):
            shine = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            sd = ImageDraw.Draw(shine)
            sx = int(-band_w * 2 + (w + band_w * 3) * (i / num_frames))
            sd.polygon([
                (sx, 0),
                (sx + band_w, 0),
                (sx + band_w + int(h * 0.4), h),
                (sx + int(h * 0.4), h)
            ], fill=(255, 255, 255, 125))
            shine.putalpha(ImageChops.multiply(alpha, shine.split()[3]))
            frames.append(Image.alpha_composite(base, shine))
        duration = 70

    elif anim_type == "bounce":
        # Slow, gentle Squash & Stretch bounce (1 single smooth hop per 2.1s loop)
        num_frames = 28
        duration = 75  # 28 * 75ms = 2100ms total loop
        bw, bh = int(w * 1.18), int(h * 1.36)
        floor_y = bh - 10
        for i in range(num_frames):
            t = i / num_frames
            # Natural gravity arc with smooth apex hang time
            jump = (math.sin(math.pi * t)) ** 1.8
            dy = int(-0.16 * h * jump)
            # Gentle squash on contact (+0.05), slight stretch in air (-0.05)
            sq = 0.05 * math.cos(2 * math.pi * t)

            c = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
            cd = ImageDraw.Draw(c)

            # Floor shadow (contracts and lightens gracefully at peak)
            sh_factor = max(0.55, 1.0 - 0.45 * jump)
            sh_w = max(4, int(w * 0.65 * sh_factor))
            sh_h = max(3, int(10 * sh_factor))
            sh_alpha = int(50 * sh_factor)
            cd.ellipse(
                [(bw - sh_w) // 2, floor_y - sh_h // 2, (bw + sh_w) // 2, floor_y + sh_h // 2],
                fill=(0, 0, 0, sh_alpha)
            )

            # Squash-stretch logo
            lw, lh = max(1, int(w * (1 + sq))), max(1, int(h * (1 - sq)))
            res = base.resize((lw, lh), Image.BICUBIC)
            c.paste(res, ((bw - lw) // 2, floor_y - lh + dy), res)
            frames.append(c)

    elif anim_type == "wiggle":
        # Slow floating sway (2.1s cycle, gentle 4.5° tilt with subtle vertical bob)
        num_frames = 28
        duration = 75
        ww, wh = int(w * 1.18), int(h * 1.18)
        c_w = Image.new("RGBA", (ww, wh), (0, 0, 0, 0))
        c_w.paste(base, ((ww - w) // 2, (wh - h) // 2), base)
        for i in range(num_frames):
            theta = 2 * math.pi * i / num_frames
            ang = 4.5 * math.sin(theta)
            dy = int(3 * math.cos(theta))
            w_rot = c_w.rotate(ang, resample=Image.BICUBIC)
            if dy != 0:
                c_shift = Image.new("RGBA", (ww, wh), (0, 0, 0, 0))
                c_shift.paste(w_rot, (0, dy), w_rot)
                frames.append(c_shift)
            else:
                frames.append(w_rot)

    elif anim_type == "fade":
        num_frames = 24
        duration = 70
        r, g, b, a = base.split()
        for i in range(num_frames):
            factor = 0.35 + 0.65 * (0.5 + 0.5 * math.cos(2 * math.pi * i / num_frames))
            new_a = a.point(lambda p: int(p * factor))
            f_im = base.copy()
            f_im.putalpha(new_a)
            frames.append(f_im)

    else:
        return input_path

    try:
        output_path.parent.mkdir(exist_ok=True)
        frames[0].save(
            output_path,
            save_all=True,
            append_images=frames[1:],
            duration=duration,
            loop=0,
            disposal=2
        )
        return output_path
    except Exception as e:
        print(f"Error animating logo: {e}")
        return input_path
