import asyncio
import os
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Optional

import aiofiles
from PIL import Image
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from text_overlay import generate_text_overlay
from logo_animator import animate_static_logo

app = FastAPI(title="Video Watermark & AI Tool")

FFMPEG_BIN = next(
    (p for p in ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "ffmpeg"]
     if shutil.which(p) or (p != "ffmpeg" and Path(p).is_file())),
    "ffmpeg",
)

FFPROBE_BIN = next(
    (p for p in ["/opt/homebrew/bin/ffprobe", "/usr/local/bin/ffprobe", "ffprobe"]
     if shutil.which(p) or (p != "ffprobe" and Path(p).is_file())),
    "ffprobe",
)

REALESRGAN_BIN = str(Path(__file__).parent / "realesrgan" /
                     "realesrgan-ncnn-vulkan-v0.2.0-macos" / "realesrgan-ncnn-vulkan")

REALESRGAN_MODELS = str(Path(__file__).parent / "realesrgan" /
                        "realesrgan-ncnn-vulkan-v0.2.0-macos" / "models")

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
BGM_DIR = Path("bgm_samples")
SHOPEE_GIFS_DIR = Path("shopee_gifs")
OPTION_DIR = Path("option")
TEMPLATE1_DIR = OPTION_DIR / "template1"
TEMPLATE2_DIR = OPTION_DIR / "template2"
TEMPLATE3_DIR = OPTION_DIR / "template3"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
BGM_DIR.mkdir(exist_ok=True)
SHOPEE_GIFS_DIR.mkdir(exist_ok=True)
OPTION_DIR.mkdir(exist_ok=True)
TEMPLATE1_DIR.mkdir(exist_ok=True)
TEMPLATE2_DIR.mkdir(exist_ok=True)
TEMPLATE3_DIR.mkdir(exist_ok=True)


def find_template_file(template_dir: Path, base_name: str) -> Optional[Path]:
    if not template_dir.exists():
        return None
    for f in template_dir.iterdir():
        if f.is_file() and f.stem.lower() == base_name.lower():
            return f
    return None



# ── Helper ─────────────────────────────────────────────────
async def check_has_audio(file_path: Path) -> bool:
    try:
        proc = await asyncio.create_subprocess_exec(
            FFPROBE_BIN, "-v", "error", "-select_streams", "a:0",
            "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        return bool(stdout.strip())
    except Exception:
        return False


async def run_cmd(cmd: list, error_prefix: str = ""):
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr_bytes = await proc.communicate()
    if proc.returncode != 0:
        stderr_text = stderr_bytes.decode(errors="replace")
        error_lines = [l for l in stderr_text.splitlines()
                       if any(k in l for k in ("Error", "error", "Invalid", "failed"))]
        detail = error_lines[-1] if error_lines else stderr_text[-500:]
        raise HTTPException(status_code=422, detail=f"{error_prefix}{detail}")


# ── Static HTML & Assets ──────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def root():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/bgm/{filename}")
async def get_bgm(filename: str):
    file_path = BGM_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="BGM not found")
    return FileResponse(file_path, media_type="audio/mpeg")


@app.get("/shopee-gifs/{filename}")
async def get_shopee_gif(filename: str):
    file_path = SHOPEE_GIFS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Shopee GIF not found")
    return FileResponse(file_path, media_type="image/gif")


@app.get("/template-asset/{template_name}/{filename}")
async def get_template_asset(template_name: str, filename: str):
    tpl_dir = OPTION_DIR / template_name
    file_path = tpl_dir / filename
    if not file_path.exists():
        found = next((f for f in tpl_dir.glob("*") if f.name.lower() == filename.lower()), None)
        if found:
            file_path = found
        else:
            raise HTTPException(status_code=404, detail="Template asset not found")
    if file_path.suffix.lower() == ".gif":
        media_type = "image/gif"
    elif file_path.suffix.lower() in [".mp3", ".wav", ".m4a", ".aac"]:
        media_type = "audio/mpeg"
    else:
        media_type = "image/png"
    return FileResponse(file_path, media_type=media_type)


# ── Watermark + Resize + Audio Mix ─────────────────────────
@app.post("/process")
async def process_video(
    video: UploadFile = File(...),
    logo: Optional[UploadFile] = File(None),
    logo_anim: str = Form("pulse"),
    shopee_sticker: Optional[str] = Form("none"),
    template: Optional[str] = Form("template1"),
    bg_top_file: Optional[UploadFile] = File(None),
    bg_bottom_file: Optional[UploadFile] = File(None),
    bgm_file: Optional[UploadFile] = File(None),
    bgm_preset: Optional[str] = Form("none"),
    video_volume: float = Form(1.0),
    bgm_volume: float = Form(0.20),
    bypass_audio: bool = Form(True),
    speed_factor: float = Form(1.02),
    color_boost: bool = Form(True),
    strip_metadata: bool = Form(True),
    position: str = Form("bottom-right"),
    logo_scale: int = Form(75),
    opacity: float = Form(1.0),
    margin: int = Form(0),
    resolution: str = Form("1080:1920"),
    use_text: bool = Form(True),
    watermark_text: str = Form("Chốt Đơn Ăn Mì"),
    text_layout: str = Form("smooth-glide"),
    text_color: str = Form("white"),
    text_size: int = Form(40),
    text_opacity: float = Form(0.50),
    text_anim_speed: str = Form("normal"),
):
    job_id = str(uuid.uuid4())[:8]
    video_ext = Path(video.filename).suffix or ".mp4"
    clean_stem = Path(video.filename).stem[:25]

    video_path = UPLOAD_DIR / f"{job_id}_video{video_ext}"
    output_path = OUTPUT_DIR / f"{job_id}_{clean_stem}_ready.mp4"

    async with aiofiles.open(video_path, "wb") as f:
        await f.write(await video.read())

    logo_path = None
    is_temp_logo = False
    if logo and logo.filename and len(logo.filename.strip()) > 0:
        logo_ext = Path(logo.filename).suffix or ".png"
        raw_logo_path = UPLOAD_DIR / f"{job_id}_raw_logo{logo_ext}"
        async with aiofiles.open(raw_logo_path, "wb") as f:
            await f.write(await logo.read())

        if logo_anim and logo_anim != "none":
            anim_logo_path = UPLOAD_DIR / f"{job_id}_anim_logo.gif"
            logo_path = animate_static_logo(raw_logo_path, logo_anim, anim_logo_path)
            raw_logo_path.unlink(missing_ok=True)
        else:
            logo_path = raw_logo_path

        is_temp_logo = True
    elif shopee_sticker and shopee_sticker != "none":
        preset_sticker = SHOPEE_GIFS_DIR / f"{shopee_sticker}.gif"
        if preset_sticker.exists():
            logo_path = preset_sticker
            is_temp_logo = False
    elif template in ("template1", "template2"):
        tpl_dir = TEMPLATE2_DIR if template == "template2" else TEMPLATE1_DIR
        tpl_logo = find_template_file(tpl_dir, "logo")
        if tpl_logo and tpl_logo.exists():
            default_anim = "bounce" if template == "template2" else "pulse"
            anim_type = logo_anim if logo_anim is not None else default_anim
            if anim_type and anim_type != "none":
                anim_logo_path = UPLOAD_DIR / f"{job_id}_anim_logo.gif"
                logo_path = animate_static_logo(tpl_logo, anim_type, anim_logo_path)
                is_temp_logo = True
            else:
                logo_path = tpl_logo
                is_temp_logo = False

    bgm_path = None
    is_temp_bgm = False
    if bgm_file and bgm_file.filename and len(bgm_file.filename.strip()) > 0:
        bgm_ext = Path(bgm_file.filename).suffix or ".mp3"
        bgm_path = UPLOAD_DIR / f"{job_id}_bgm{bgm_ext}"
        async with aiofiles.open(bgm_path, "wb") as f:
            await f.write(await bgm_file.read())
        is_temp_bgm = True
    elif bgm_preset and bgm_preset != "none":
        preset_file = BGM_DIR / f"{bgm_preset}.mp3"
        if preset_file.exists():
            bgm_path = preset_file
            is_temp_bgm = False
    elif template in ("template1", "template2", "template3"):
        if template == "template3":
            tpl_dir = TEMPLATE3_DIR
        elif template == "template2":
            tpl_dir = TEMPLATE2_DIR
        else:
            tpl_dir = TEMPLATE1_DIR
        tpl_music = find_template_file(tpl_dir, "music")
        if tpl_music and tpl_music.exists():
            bgm_path = tpl_music
            is_temp_bgm = False

    res_w_str, res_h_str = resolution.split(":")
    res_w, res_h = int(res_w_str), int(res_h_str)

    # 2 Backgrounds (Top & Bottom) specifically for Option 3
    bg_top_path = None
    is_temp_bg_top = False
    bg_bottom_path = None
    is_temp_bg_bottom = False

    if template == "template3":
        if bg_top_file and bg_top_file.filename and len(bg_top_file.filename.strip()) > 0:
            top_ext = Path(bg_top_file.filename).suffix or ".png"
            bg_top_path = UPLOAD_DIR / f"{job_id}_bg_top{top_ext}"
            async with aiofiles.open(bg_top_path, "wb") as f:
                await f.write(await bg_top_file.read())
            is_temp_bg_top = True
        else:
            found_top = find_template_file(TEMPLATE3_DIR, "bg_top") or find_template_file(TEMPLATE3_DIR, "top")
            if found_top and found_top.exists():
                bg_top_path = found_top
                is_temp_bg_top = False

        if bg_bottom_file and bg_bottom_file.filename and len(bg_bottom_file.filename.strip()) > 0:
            bot_ext = Path(bg_bottom_file.filename).suffix or ".png"
            bg_bottom_path = UPLOAD_DIR / f"{job_id}_bg_bottom{bot_ext}"
            async with aiofiles.open(bg_bottom_path, "wb") as f:
                await f.write(await bg_bottom_file.read())
            is_temp_bg_bottom = True
        else:
            found_bot = find_template_file(TEMPLATE3_DIR, "bg_bottom") or find_template_file(TEMPLATE3_DIR, "bottom")
            if found_bot and found_bot.exists():
                bg_bottom_path = found_bot
                is_temp_bg_bottom = False

    # 1. Generate text overlay if requested
    text_overlay_path = None
    if use_text and watermark_text.strip():
        text_overlay_path = UPLOAD_DIR / f"{job_id}_text_overlay.png"
        generate_text_overlay(
            width=res_w,
            height=res_h,
            text=watermark_text,
            layout=text_layout,
            font_size=text_size,
            opacity=text_opacity,
            color=text_color,
            output_path=str(text_overlay_path)
        )

    # 2. Build FFmpeg command
    cmd = [FFMPEG_BIN, "-y", "-i", str(video_path)]
    input_idx = 1
    text_input_idx = None
    logo_input_idx = None
    bg_top_input_idx = None
    bg_bottom_input_idx = None
    bgm_input_idx = None

    if text_overlay_path and text_overlay_path.exists():
        cmd.extend(["-i", str(text_overlay_path)])
        text_input_idx = input_idx
        input_idx += 1

    if logo_path and logo_path.exists():
        if logo_path.suffix.lower() == ".gif":
            cmd.extend(["-ignore_loop", "0", "-i", str(logo_path)])
        else:
            cmd.extend(["-i", str(logo_path)])
        logo_input_idx = input_idx
        input_idx += 1

    if bg_top_path and bg_top_path.exists():
        if bg_top_path.suffix.lower() == ".gif":
            cmd.extend(["-ignore_loop", "0", "-i", str(bg_top_path)])
        else:
            cmd.extend(["-i", str(bg_top_path)])
        bg_top_input_idx = input_idx
        input_idx += 1

    if bg_bottom_path and bg_bottom_path.exists():
        if bg_bottom_path.suffix.lower() == ".gif":
            cmd.extend(["-ignore_loop", "0", "-i", str(bg_bottom_path)])
        else:
            cmd.extend(["-i", str(bg_bottom_path)])
        bg_bottom_input_idx = input_idx
        input_idx += 1

    if bgm_path and bgm_path.exists():
        cmd.extend(["-stream_loop", "-1", "-i", str(bgm_path)])
        bgm_input_idx = input_idx
        input_idx += 1

    if margin == 0:
        positions = {
            "top-left":     "0:0",
            "top-right":    "W-w:0",
            "bottom-left":  "0:H-h",
            "bottom-right": "W-w:H-h",
            "center":       "(W-w)/2:(H-h)/2",
        }
    else:
        margin_expr = str(margin)
        positions = {
            "top-left":     f"{margin_expr}:{margin_expr}",
            "top-right":    f"W-w-{margin_expr}:{margin_expr}",
            "bottom-left":  f"{margin_expr}:H-h-{margin_expr}",
            "bottom-right": f"W-w-{margin_expr}:H-h-{margin_expr}",
            "center":       f"(W-w)/2:(H-h)/2",
        }
    overlay_pos = positions.get(position, positions["bottom-right"])
    logo_width = f"iw*{logo_scale}/100"

    # Base scale & pad to target resolution (TikTok 9:16 or selected)
    if template == "template3":
        # Option 3: Giữ nguyên tỷ lệ video tự nhiên + Đè thanh hướng dẫn mua hàng đơn giản ở dưới
        proc_filters = ["crop=iw*0.97:ih*0.97", "noise=alls=3:allf=t"]
        if color_boost:
            proc_filters.append("eq=contrast=1.05:brightness=0.015:saturation=1.08:gamma=0.98,hue=h=1.5,unsharp=3:3:0.7:3:3:0.0")
        if speed_factor and abs(speed_factor - 1.0) >= 0.005:
            proc_filters.append(f"setpts=PTS/{speed_factor}")

        proc_filters.extend([
            f"scale={res_w}:{res_h}:force_original_aspect_ratio=decrease",
            f"pad={res_w}:{res_h}:(ow-iw)/2:(oh-ih)/2:color=black",
        ])

        filters = [f"[0:v]{','.join(proc_filters)}[bg]"]
        curr_bg = "[bg]"

        # Overlay thanh hướng dẫn mua hàng Shopee ở mép dưới
        if bg_bottom_input_idx is not None:
            filters.append(f"[{bg_bottom_input_idx}:v]scale={res_w}:-1,format=rgba[bg_bottom_img]")
            filters.append(f"{curr_bg}[bg_bottom_img]overlay=(W-w)/2:H-h[with_bottom_bg]")
            curr_bg = "[with_bottom_bg]"

        # Overlay thanh top nếu có
        if bg_top_input_idx is not None:
            filters.append(f"[{bg_top_input_idx}:v]scale={res_w}:-1[bg_top_img]")
            filters.append(f"{curr_bg}[bg_top_img]overlay=(W-w)/2:0[with_top_bg]")
            curr_bg = "[with_top_bg]"
    else:
        base_v_filters = []
        if template == "template2":
            # Micro-zoom 2%: crop 98% center before scaling (làm lệch toàn bộ pixel matrix và pHash so với Mẫu 1)
            base_v_filters.append("crop=iw*0.98:ih*0.98")

        base_v_filters.extend([
            f"scale={res_w}:{res_h}:force_original_aspect_ratio=decrease",
            f"pad={res_w}:{res_h}:(ow-iw)/2:(oh-ih)/2:color=black",
        ])

        if color_boost:
            if template == "template2":
                # Tone Mẫu 2: Ấm áp, nịnh mắt, màu tươi đậm hơn + nét chi tiết (phá vỡ hoàn toàn histogram so với Mẫu 1)
                base_v_filters.append("eq=contrast=1.06:brightness=0.02:saturation=1.09,unsharp=3:3:0.8:3:3:0.0")
            else:
                # Tone Mẫu 1: Tự nhiên, sáng nhẹ
                base_v_filters.append("eq=contrast=1.03:brightness=0.01:saturation=1.04")

        if speed_factor and abs(speed_factor - 1.0) >= 0.005:
            # Micro speed adjustment (phá vỡ timeline và frame timestamps)
            base_v_filters.append(f"setpts=PTS/{speed_factor}")

        filters = [f"[0:v]{','.join(base_v_filters)}[bg]"]
        curr_bg = "[bg]"

    # Layer Text overlay
    if text_input_idx is not None:
        pad_x = 30
        pad_y_top = 80
        pad_y_bottom = 150
        if text_layout == "bounce":
            # DVD linear bounce trajectory:
            # Starts top-left (pad_x, pad_y_top), moves diagonally down to bottom-right,
            # reflects to center-left, continuously bouncing across every part of screen
            tx = {"fast": 4.2, "slow": 10.5}.get(text_anim_speed, 6.8)
            ty = {"fast": 2.9, "slow": 7.3}.get(text_anim_speed, 4.7)
            x_expr = f"{pad_x}+(W-w-{pad_x*2})*(1-abs(2*(mod(t,{tx})/{tx})-1))"
            y_expr = f"{pad_y_top}+(H-h-{pad_y_top+pad_y_bottom})*(1-abs(2*(mod(t,{ty})/{ty})-1))"
            text_coord = f"x='{x_expr}':y='{y_expr}'"
        elif text_layout == "smooth-glide":
            # Smooth Lissajous curve floating all across the screen
            tx = {"fast": 4.5, "slow": 11.0}.get(text_anim_speed, 7.2)
            ty = {"fast": 3.1, "slow": 7.8}.get(text_anim_speed, 5.1)
            x_expr = f"{pad_x}+(W-w-{pad_x*2})*(0.5-0.5*cos(2*PI*t/{tx}))"
            y_expr = f"{pad_y_top}+(H-h-{pad_y_top+pad_y_bottom})*(0.5-0.5*cos(2*PI*t/{ty}))"
            text_coord = f"x='{x_expr}':y='{y_expr}'"
        elif text_layout in ("ticker-scroll", "ticker-top"):
            # Running marquee from right edge to left edge (Top safe zone)
            speed_px = {"fast": 360, "slow": 140}.get(text_anim_speed, 220)
            x_expr = f"W-mod(t*{speed_px},W+w)"
            y_expr = "120"
            text_coord = f"x='{x_expr}':y='{y_expr}'"
        elif text_layout == "wave-scroll":
            # Running marquee with gentle vertical sine wave
            speed_px = {"fast": 360, "slow": 140}.get(text_anim_speed, 220)
            x_expr = f"W-mod(t*{speed_px},W+w)"
            y_expr = "130+28*sin(2*PI*t/3.2)"
            text_coord = f"x='{x_expr}':y='{y_expr}'"
        elif text_layout == "ticker-bottom-run":
            # Running marquee along bottom edge (above footer)
            speed_px = {"fast": 360, "slow": 140}.get(text_anim_speed, 220)
            x_expr = f"W-mod(t*{speed_px},W+w)"
            y_expr = f"H-h-{pad_y_bottom+15}"
            text_coord = f"x='{x_expr}':y='{y_expr}'"
        else:
            text_coord = "0:0"

        filters.append(f"{curr_bg}[{text_input_idx}:v]overlay={text_coord}[with_text]")
        curr_bg = "[with_text]"

    # Layer Logo overlay
    if logo_input_idx is not None:
        if opacity >= 1.0:
            filters.append(f"[{logo_input_idx}:v]scale={logo_width}:-1,format=rgba[logo]")
        else:
            filters.append(
                f"[{logo_input_idx}:v]scale={logo_width}:-1,format=rgba,"
                f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='alpha(X,Y)*{opacity}'[logo]"
            )
        filters.append(f"{curr_bg}[logo]overlay={overlay_pos}[out]")
        curr_bg = "[out]"
    else:
        # If no logo, rename last buffer to [out]
        if curr_bg != "[out]":
            filters.append(f"{curr_bg}copy[out]")

    # Audio handling
    has_video_audio = await check_has_audio(video_path)
    audio_map = []

    # Map BGM volume to true perceptual loudness curve:
    # A linear gain of 0.20 only reduces sound by ~14dB, which still sounds like 80%-100% loudness to human ears.
    # pow(v, 1.75) maps 0.20 to ~0.06 (-24.5 dB), which truly sounds like a gentle 20% background volume!
    if bgm_volume <= 1.0:
        eff_bgm_vol = round(pow(max(0.0, float(bgm_volume)), 1.75), 4)
    else:
        eff_bgm_vol = round(float(bgm_volume), 2)

    if template == "template3":
        audio_pitch_rate = "1.032"
    elif template == "template2":
        audio_pitch_rate = "1.028"
    else:
        audio_pitch_rate = "1.015"

    if bgm_input_idx is not None:
        if has_video_audio and video_volume > 0.001:
            orig_audio_filters = []
            if bypass_audio:
                orig_audio_filters.append(f"asetrate=44100*{audio_pitch_rate},aresample=44100")
                if template == "template3":
                    # EQ shift âm phổ chống nhận diện âm thanh Shazam/TikTok
                    orig_audio_filters.append("equalizer=f=120:t=q:w=1.2:g=1.2,equalizer=f=3500:t=q:w=1.0:g=-1")
            if speed_factor and abs(speed_factor - 1.0) >= 0.005:
                orig_audio_filters.append(f"atempo={speed_factor}")
            if video_volume != 1.0:
                orig_audio_filters.append(f"volume={video_volume}")
            orig_audio_filters.append("aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo")
            filters.append(f"[0:a]{','.join(orig_audio_filters)}[a_orig]")

            bgm_filters = [f"volume={eff_bgm_vol}", "aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo"]
            filters.append(f"[{bgm_input_idx}:a]{','.join(bgm_filters)}[a_bgm]")

            filters.append("[a_orig][a_bgm]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]")
            audio_map = ["-map", "[aout]"]
        else:
            # Video has no original audio or user muted video_volume, use BGM directly
            bgm_filters = [f"volume={eff_bgm_vol}", "aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo"]
            filters.append(f"[{bgm_input_idx}:a]{','.join(bgm_filters)}[aout]")
            audio_map = ["-map", "[aout]"]
    else:
        # No BGM
        if has_video_audio and video_volume > 0.001:
            orig_audio_filters = []
            if bypass_audio:
                orig_audio_filters.append(f"asetrate=44100*{audio_pitch_rate},aresample=44100")
                if template == "template3":
                    orig_audio_filters.append("equalizer=f=120:t=q:w=1.2:g=1.2,equalizer=f=3500:t=q:w=1.0:g=-1")
            if speed_factor and abs(speed_factor - 1.0) >= 0.005:
                orig_audio_filters.append(f"atempo={speed_factor}")
            if video_volume != 1.0:
                orig_audio_filters.append(f"volume={video_volume}")
            orig_audio_filters.append("aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo")
            filters.append(f"[0:a]{','.join(orig_audio_filters)}[aout]")
            audio_map = ["-map", "[aout]"]
        else:
            audio_map = []

    filter_complex = ";".join(filters)
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[out]",
        *audio_map,
    ])
    if strip_metadata:
        cmd.extend([
            "-map_metadata", "-1",
            "-fflags", "+bitexact",
            "-flags:v", "+bitexact",
            "-flags:a", "+bitexact",
        ])
    crf_val = "21" if template == "template3" else "22"
    cmd.extend([
        "-c:v", "libx264", "-preset", "fast", "-crf", crf_val,
    ])
    if template == "template3":
        cmd.extend(["-g", "48"])
    if audio_map:
        cmd.extend(["-c:a", "aac", "-b:a", "192k"])
    cmd.extend(["-shortest", str(output_path)])

    try:
        await run_cmd(cmd, "FFmpeg watermark: ")
    finally:
        video_path.unlink(missing_ok=True)
        if logo_path and is_temp_logo:
            logo_path.unlink(missing_ok=True)
        if bg_top_path and is_temp_bg_top:
            bg_top_path.unlink(missing_ok=True)
        if bg_bottom_path and is_temp_bg_bottom:
            bg_bottom_path.unlink(missing_ok=True)
        if text_overlay_path:
            text_overlay_path.unlink(missing_ok=True)
        if bgm_path and is_temp_bgm:
            bgm_path.unlink(missing_ok=True)

    return {
        "job_id": job_id,
        "filename": output_path.name,
        "download_url": f"/download/{job_id}"
    }


# ── AI Enhance (Real-ESRGAN) ───────────────────────────────
@app.post("/enhance")
async def enhance_video(
    video: UploadFile = File(...),
    scale: int = Form(2),
    model: str = Form("realesr-animevideov3"),
    denoise: bool = Form(True),
):
    if not Path(REALESRGAN_BIN).is_file():
        raise HTTPException(status_code=503,
                            detail="Real-ESRGAN chưa được cài. Vui lòng kiểm tra thư mục realesrgan/")

    job_id = str(uuid.uuid4())[:8]
    video_ext = Path(video.filename).suffix or ".mp4"
    clean_stem = Path(video.filename).stem[:25]
    video_path = UPLOAD_DIR / f"{job_id}_video{video_ext}"
    frames_dir = UPLOAD_DIR / f"{job_id}_frames"
    enhanced_dir = UPLOAD_DIR / f"{job_id}_enhanced"
    output_path = OUTPUT_DIR / f"{job_id}_{clean_stem}_enhanced.mp4"

    frames_dir.mkdir(exist_ok=True)
    enhanced_dir.mkdir(exist_ok=True)

    async with aiofiles.open(video_path, "wb") as f:
        await f.write(await video.read())

    try:
        # 1. Extract FPS
        probe = await asyncio.create_subprocess_exec(
            FFMPEG_BIN, "-i", str(video_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, probe_err = await probe.communicate()
        probe_text = probe_err.decode(errors="replace")

        fps = "24"
        for line in probe_text.splitlines():
            if "fps" in line:
                import re
                m = re.search(r"(\d+(?:\.\d+)?)\s*fps", line)
                if m:
                    fps = m.group(1)
                    break

        # 2. Extract frames as PNG
        await run_cmd([
            FFMPEG_BIN, "-y", "-i", str(video_path),
            str(frames_dir / "frame%08d.png")
        ], "FFmpeg extract: ")

        frames = sorted(frames_dir.glob("*.png"))
        if not frames:
            raise HTTPException(status_code=422, detail="Không thể trích xuất frames từ video")

        # 3. AI Upscale all frames with Real-ESRGAN
        await run_cmd([
            REALESRGAN_BIN,
            "-i", str(frames_dir),
            "-o", str(enhanced_dir),
            "-n", model,
            "-s", str(scale),
            "-m", REALESRGAN_MODELS,
            "-f", "png",
        ], "Real-ESRGAN: ")

        # 4. Apply sharpening if denoise requested
        vf = "unsharp=5:5:0.8:5:5:0.0" if denoise else "copy"

        # 5. Reassemble video with original audio
        await run_cmd([
            FFMPEG_BIN, "-y",
            "-framerate", fps,
            "-i", str(enhanced_dir / "frame%08d.png"),
            "-i", str(video_path),
            "-map", "0:v", "-map", "1:a?",
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac",
            "-shortest",
            str(output_path),
        ], "FFmpeg reassemble: ")

    finally:
        video_path.unlink(missing_ok=True)
        shutil.rmtree(frames_dir, ignore_errors=True)
        shutil.rmtree(enhanced_dir, ignore_errors=True)

    return {
        "job_id": job_id,
        "filename": output_path.name,
        "download_url": f"/download-enhanced/{job_id}"
    }


@app.get("/download/{job_id}")
async def download(job_id: str):
    matches = list(OUTPUT_DIR.glob(f"{job_id}_*ready.mp4"))
    if not matches:
        matches = list(OUTPUT_DIR.glob(f"{job_id}_*.mp4"))
    if not matches:
        raise HTTPException(status_code=404, detail="File không tồn tại hoặc đã bị xóa.")
    path = matches[0]
    return FileResponse(
        path=path,
        media_type="video/mp4",
        filename=f"tiktok_{path.name}"
    )


@app.get("/download-enhanced/{job_id}")
async def download_enhanced(job_id: str):
    matches = list(OUTPUT_DIR.glob(f"{job_id}_*enhanced.mp4"))
    if not matches:
        raise HTTPException(status_code=404, detail="File không tồn tại hoặc đã bị xóa.")
    path = matches[0]
    return FileResponse(
        path=path,
        media_type="video/mp4",
        filename=f"ai_{path.name}"
    )


class BatchZipRequest(BaseModel):
    job_ids: list[str]


@app.post("/create-batch-zip")
async def create_batch_zip(req: BatchZipRequest):
    if not req.job_ids:
        raise HTTPException(status_code=400, detail="Không có job ID nào.")

    batch_id = str(uuid.uuid4())[:8]
    zip_filename = f"batch_{batch_id}_watermarked_videos.zip"
    zip_path = OUTPUT_DIR / zip_filename

    added_count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for jid in req.job_ids:
            matches = list(OUTPUT_DIR.glob(f"{jid}_*ready.mp4"))
            if not matches:
                matches = list(OUTPUT_DIR.glob(f"{jid}_*.mp4"))
            for f in matches:
                zipf.write(f, arcname=f.name)
                added_count += 1

    if added_count == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy video nào để đóng gói ZIP.")

    return {
        "download_url": f"/download-zip/{zip_filename}",
        "filename": zip_filename,
        "count": added_count
    }


@app.get("/download-zip/{filename}")
async def download_zip(filename: str):
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File ZIP không tồn tại hoặc đã bị xóa.")
    return FileResponse(
        path=path,
        media_type="application/zip",
        filename=filename
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)
