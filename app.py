import asyncio
import os
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from text_overlay import generate_text_overlay

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
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
BGM_DIR.mkdir(exist_ok=True)


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


# ── Watermark + Resize + Audio Mix ─────────────────────────
@app.post("/process")
async def process_video(
    video: UploadFile = File(...),
    logo: Optional[UploadFile] = File(None),
    bgm_file: Optional[UploadFile] = File(None),
    bgm_preset: Optional[str] = Form("none"),
    video_volume: float = Form(1.0),
    bgm_volume: float = Form(0.20),
    bypass_audio: bool = Form(True),
    speed_factor: float = Form(1.02),
    color_boost: bool = Form(True),
    strip_metadata: bool = Form(True),
    position: str = Form("bottom-right"),
    logo_scale: int = Form(15),
    opacity: float = Form(1.0),
    margin: int = Form(20),
    resolution: str = Form("1080:1920"),
    use_text: bool = Form(False),
    watermark_text: str = Form("Chốt Đơn Ăn Mì"),
    text_layout: str = Form("bounce"),
    text_color: str = Form("yellow"),
    text_size: int = Form(30),
    text_opacity: float = Form(0.85),
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
    if logo and logo.filename and len(logo.filename.strip()) > 0:
        logo_ext = Path(logo.filename).suffix or ".png"
        logo_path = UPLOAD_DIR / f"{job_id}_logo{logo_ext}"
        async with aiofiles.open(logo_path, "wb") as f:
            await f.write(await logo.read())

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

    res_w_str, res_h_str = resolution.split(":")
    res_w, res_h = int(res_w_str), int(res_h_str)

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
    bgm_input_idx = None

    if text_overlay_path and text_overlay_path.exists():
        cmd.extend(["-i", str(text_overlay_path)])
        text_input_idx = input_idx
        input_idx += 1

    if logo_path and logo_path.exists():
        cmd.extend(["-i", str(logo_path)])
        logo_input_idx = input_idx
        input_idx += 1

    if bgm_path and bgm_path.exists():
        cmd.extend(["-stream_loop", "-1", "-i", str(bgm_path)])
        bgm_input_idx = input_idx
        input_idx += 1

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
    base_v_filters = [
        f"scale={res_w}:{res_h}:force_original_aspect_ratio=decrease",
        f"pad={res_w}:{res_h}:(ow-iw)/2:(oh-ih)/2:color=black",
    ]
    if color_boost:
        # Micro color grading & contrast boost (phá pHash và histogram matching)
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
        elif text_layout == "ticker-scroll":
            # Running marquee from right edge to left edge
            speed_px = {"fast": 360, "slow": 140}.get(text_anim_speed, 220)
            x_expr = f"W-mod(t*{speed_px},W+w)"
            y_expr = f"H-h-{pad_y_bottom}"
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

    if bgm_input_idx is not None:
        if has_video_audio:
            orig_audio_filters = []
            if bypass_audio:
                orig_audio_filters.append("asetrate=44100*1.015,aresample=44100")
            if speed_factor and abs(speed_factor - 1.0) >= 0.005:
                orig_audio_filters.append(f"atempo={speed_factor}")
            orig_audio_filters.append(f"volume={video_volume}")
            orig_audio_filters.append("aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo")
            filters.append(f"[0:a]{','.join(orig_audio_filters)}[a_orig]")

            bgm_filters = [f"volume={bgm_volume}", "aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo"]
            filters.append(f"[{bgm_input_idx}:a]{','.join(bgm_filters)}[a_bgm]")

            filters.append("[a_orig][a_bgm]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]")
            audio_map = ["-map", "[aout]"]
        else:
            # Video has no original audio, use BGM directly
            bgm_filters = [f"volume={bgm_volume}", "aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo"]
            filters.append(f"[{bgm_input_idx}:a]{','.join(bgm_filters)}[aout]")
            audio_map = ["-map", "[aout]"]
    else:
        # No BGM
        if has_video_audio:
            orig_audio_filters = []
            if bypass_audio:
                orig_audio_filters.append("asetrate=44100*1.015,aresample=44100")
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
    cmd.extend([
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
    ])
    if audio_map:
        cmd.extend(["-c:a", "aac", "-b:a", "192k"])
    cmd.extend(["-shortest", str(output_path)])

    try:
        await run_cmd(cmd, "FFmpeg watermark: ")
    finally:
        video_path.unlink(missing_ok=True)
        if logo_path:
            logo_path.unlink(missing_ok=True)
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
