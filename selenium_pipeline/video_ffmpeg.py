"""Reliable, resumable PDF+WAV to MP4 assembly using FFmpeg (no MoviePy).

Uses per-slide PDF page 1, WAV duration, H.264/AAC fixed-size segments,
then concatenates them. Existing slides.mp4 is never touched until the
candidate is encoded and probed successfully.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from datetime import datetime, timezone
from pathlib import Path

SLIDE_PDF = re.compile(r"^slide([1-9]\d*)\.pdf$", re.I)
SLIDE_WAV = re.compile(r"^slide([1-9]\d*)\.wav$", re.I)


def _files(folder: Path, rx: re.Pattern[str]) -> dict[int, Path]:
    result = {}
    for file in folder.iterdir():
        if file.is_file():
            match = rx.fullmatch(file.name)
            if match:
                result[int(match.group(1))] = file
    return result


def check_inputs(folder: Path) -> list[tuple[int, Path, Path, float]]:
    pdfs = _files(folder, SLIDE_PDF)
    wavs = _files(folder, SLIDE_WAV)
    if not pdfs or not wavs or set(pdfs) != set(wavs):
        raise ValueError("slideN.pdf and slideN.wav sets are empty or differ: "
                         f"PDF={sorted(pdfs)}, WAV={sorted(wavs)}")
    if sorted(pdfs) != list(range(1, len(pdfs) + 1)):
        raise ValueError(f"Slide numbers must be contiguous from 1: {sorted(pdfs)}")
    entries = []
    for number in sorted(pdfs):
        with wave.open(str(wavs[number]), "rb") as sound:
            seconds = sound.getnframes() / sound.getframerate()
        if seconds <= 0.05:
            raise ValueError(f"Invalid audio duration for slide{number}.wav")
        entries.append((number, pdfs[number], wavs[number], seconds))
    return entries


def ffmpeg_executable() -> str:
    import os
    override = os.environ.get("MICROVID_FFMPEG", "").strip()
    if override:
        path = Path(override).expanduser()
        if path.is_file():
            return str(path)
        resolved = shutil.which(override)
        if resolved:
            return resolved
        raise FileNotFoundError(f"MICROVID_FFMPEG not found: {override}")
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError, RuntimeError):
        resolved = shutil.which("ffmpeg")
        if resolved:
            return resolved
    raise FileNotFoundError("FFmpeg unavailable. Install imageio-ffmpeg or FFmpeg.")


def run_ffmpeg(exe: str, args: list[str], *, step: str) -> str:
    result = subprocess.run(
        [exe, "-hide_banner", "-nostdin", "-loglevel", "error", *args],
        capture_output=True, text=True, errors="replace", check=False,
    )
    if result.returncode:
        raise RuntimeError(
            f"FFmpeg {step} exited {result.returncode}:\n{result.stderr[-5000:]}"
        )
    return result.stderr + result.stdout


def validate_video(exe: str, file: Path, min_seconds: float) -> None:
    if not file.is_file() or file.stat().st_size < 2048:
        raise RuntimeError(f"Empty/invalid MP4: {file}")
    probe = subprocess.run(
        [exe, "-hide_banner", "-i", str(file)],
        capture_output=True, text=True, errors="replace", check=False,
    )
    details = probe.stderr + probe.stdout
    if "Video:" not in details or "Audio:" not in details:
        raise RuntimeError("MP4 lacks decodable video or audio stream: "
                           + details[-2500:])
    duration = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", details)
    if not duration:
        raise RuntimeError("FFmpeg could not report MP4 duration")
    seconds = int(duration.group(1))*3600 + int(duration.group(2))*60 + float(duration.group(3))
    if seconds < min_seconds * 0.95:
        raise RuntimeError(f"MP4 unexpectedly short: {seconds:.1f}s; expected >= {min_seconds * 0.95:.1f}s")
    print(f"[video] validated {file.name}: {seconds:.2f}s, "
          f"{file.stat().st_size:,} bytes, video+audio present", flush=True)


def assemble(folder: Path, *, output: str = "slides.mp4", fps: int = 24,
             width: int = 1280, height: int = 720) -> Path:
    import fitz

    folder = folder.expanduser().resolve()
    if not folder.is_dir():
        raise NotADirectoryError(folder)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.mp4", output):
        raise ValueError("Output must be a simple .mp4 filename")
    if fps < 1 or width < 64 or height < 64 or width % 2 or height % 2:
        raise ValueError("fps and even output dimensions must be positive")
    entries = check_inputs(folder)
    ffmpeg = ffmpeg_executable()
    total = sum(row[3] for row in entries)
    print(f"[video] {len(entries)} complete PDF/WAV slide pairs; "
          f"total narration {total:.1f}s; encoder={ffmpeg}", flush=True)

    with tempfile.TemporaryDirectory(prefix=".microgen_video_", dir=folder) as tmp_name:
        tmp = Path(tmp_name)
        segments = []
        for number, pdf, wav, seconds in entries:
            with fitz.open(str(pdf)) as document:
                if document.page_count != 1:
                    raise ValueError(f"{pdf.name} must contain exactly one PDF page")
                page = document[0]
                scale = min(width / page.rect.width, height / page.rect.height)
                pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                frame = tmp / f"frame{number}.png"
                pix.save(str(frame))
            segment = tmp / f"segment{number:04d}.mp4"
            run_ffmpeg(ffmpeg, [
                "-y", "-loop", "1", "-framerate", str(fps),
                "-i", str(frame), "-i", str(wav),
                "-filter:v", f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                             f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
                "-r", str(fps), "-c:a", "aac", "-b:a", "128k",
                "-ar", "44100", "-ac", "2",
                "-t", f"{seconds:.6f}",
                "-movflags", "+faststart", str(segment),
            ], step=f"slide {number}")
            segments.append(segment)
            print(f"[video] encoded slide {number}/{len(entries)} "
                  f"({seconds:.1f}s)", flush=True)

        listing = tmp / "segments.txt"
        listing.write_text("".join(
            "file '" + p.as_posix().replace("'", "'\\''") + "'\n"
            for p in segments
        ), encoding="utf-8")
        candidate = tmp / "candidate.mp4"
        run_ffmpeg(ffmpeg, [
            "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
            "-c", "copy", "-movflags", "+faststart", str(candidate)
        ], step="concat")
        validate_video(ffmpeg, candidate, total)
        dest = folder / output
        if dest.exists():
            archival = folder / ".history" / (
                "video_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
            )
            archival.mkdir(parents=True, exist_ok=False)
            old_copy = archival / output
            shutil.copy2(dest, old_copy)
            print(f"[video] archived previous {output} at {old_copy}", flush=True)
        shutil.copy2(candidate, tmp / "validated.mp4")
        (tmp / "validated.mp4").replace(dest)
    print(f"[video] SUCCESS: {dest}", flush=True)
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reliable FFmpeg slide-PDF/WAV video assembler")
    parser.add_argument("--folder", type=Path, default=Path.cwd())
    parser.add_argument("--output", default="slides.mp4")
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    args = parser.parse_args(argv)
    try:
        assemble(args.folder, output=args.output, fps=args.fps,
                 width=args.width, height=args.height)
    except Exception as exc:
        print(f"[video] FAILED: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
