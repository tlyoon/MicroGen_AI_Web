"""Reliable, resumable PDF+WAV to MP4 assembly using FFmpeg (no MoviePy).

Uses per-slide PDF page 1, WAV duration, H.264/AAC fixed-size segments,
then concatenates them. Existing slides.mp4 is never touched until the
candidate is encoded and probed successfully.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from queue import Empty, Queue
from threading import Thread
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
    """Watch real encoder progress, not merely a process-exists heartbeat.

    The child keeps its own hard deadline; frozen frame/output timestamps have
    a separate stall deadline. Neither error overwrites an existing MP4.
    """
    timeout = max(1.0, float(os.getenv("MICROGEN_FFMPEG_TIMEOUT_SECONDS", "1200")))
    stall_limit = max(5.0, float(os.getenv("MICROGEN_FFMPEG_STALL_SECONDS", "90")))
    command = [exe, "-hide_banner", "-nostdin", "-loglevel", "error",
               "-progress", "pipe:1", *args]
    print(f"[video] FFmpeg starting {step} (hard={timeout:.0f}s, "
          f"no-progress={stall_limit:.0f}s)", flush=True)
    started = time.monotonic()
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as stderr:
        with subprocess.Popen(command, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=stderr,
                              encoding="utf-8", errors="replace",
                              text=True, bufsize=1) as proc:
            assert proc.stdout is not None
            output: Queue[str | None] = Queue()

            def drain() -> None:
                try:
                    for line in proc.stdout:
                        output.put(line.strip())
                finally:
                    output.put(None)

            reader = Thread(target=drain, daemon=True)
            reader.start()
            last_advance = started
            last_notice = started
            last_frame = -1
            last_seconds = -1.0
            speed = "unknown"
            try:
                while True:
                    try:
                        line = output.get(timeout=1)
                    except Empty:
                        line = ""
                    now = time.monotonic()
                    if line and "=" in line:
                        key, value = line.split("=", 1)
                        if key in {"out_time_us", "out_time_ms"}:
                            try:
                                seconds = float(value) / 1_000_000.0
                            except ValueError:
                                seconds = last_seconds
                            if seconds > last_seconds:
                                last_seconds, last_advance = seconds, now
                        elif key == "frame":
                            try:
                                frame = int(value)
                            except ValueError:
                                frame = last_frame
                            if frame > last_frame:
                                last_frame, last_advance = frame, now
                        elif key == "speed":
                            speed = value
                    if now - last_notice >= 20:
                        print(f"[video] {step}: {now-started:.0f}s elapsed, "
                              f"encoded={max(0.0,last_seconds):.1f}s, "
                              f"frame={max(0,last_frame)}, speed={speed}, "
                              f"no progress={now-last_advance:.0f}s", flush=True)
                        last_notice = now
                    if proc.poll() is not None and not reader.is_alive() and output.empty():
                        break
                    if now - started > timeout:
                        raise TimeoutError(f"FFmpeg {step} exceeded {timeout:.0f}s hard deadline")
                    if now - last_advance > stall_limit:
                        raise TimeoutError(f"FFmpeg {step} made no media progress for "
                                           f"{stall_limit:.0f}s (last media time "
                                           f"{max(0,last_seconds):.1f}s)")
            except BaseException:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=15)
                raise
            finally:
                reader.join(timeout=2)
            stderr.seek(0)
            details = stderr.read()
            if proc.returncode:
                raise RuntimeError(
                    f"FFmpeg {step} exited {proc.returncode}:\n{details[-5000:]}"
                )
    return details

def validate_video(exe: str, file: Path, min_seconds: float) -> None:
    if not file.is_file() or file.stat().st_size < 2048:
        raise RuntimeError(f"Empty/invalid MP4: {file}")
    probe = subprocess.run(
        [exe, "-hide_banner", "-i", str(file)],
        capture_output=True, text=True, errors="replace", check=False,
        timeout=60,
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
    return seconds


def _sha256(file: Path) -> str:
    digest = hashlib.sha256()
    with file.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verified_local_input(source: Path, target: Path, expected_sha256: str) -> Path:
    """Stage one media input onto local storage, detecting stale/racing Drive sync.

    Never allow an FFmpeg process to read an audio track directly from a
    remote/cloud-mounted drive. Intermediate copies are never promoted unless
    the bytes match the input hash captured for this segment.
    """
    # Reject a changed remote input even if an older local cached copy exists.
    if _sha256(source) != expected_sha256:
        raise RuntimeError(f"Input changed during local staging: {source}")
    if target.is_file() and _sha256(target) == expected_sha256:
        return target
    partial = target.with_name(target.name + ".partial")
    try:
        shutil.copy2(source, partial)
        if _sha256(partial) != expected_sha256:
            raise RuntimeError(f"Input changed during local staging: {source}")
        partial.replace(target)
    finally:
        partial.unlink(missing_ok=True)
    return target


def _segment_signature(pdf: Path, wav: Path, seconds: float,
                       fps: int, width: int, height: int) -> dict:
    """Changing a slide, voice, or encoding profile invalidates cached media."""
    return {"pdf_sha256": _sha256(pdf), "wav_sha256": _sha256(wav),
            "duration": round(seconds, 6), "fps": fps,
            "width": width, "height": height, "codec": "h264-aac-static-v2"}


def _video_cache(folder: Path) -> Path:
    """Failure-resilient cache on local storage, never a synced Drive mount."""
    root = Path(os.getenv(
        "MICROGEN_VIDEO_CACHE_ROOT",
        str(Path(os.getenv("LOCALAPPDATA", tempfile.gettempdir()))
            / "MicroGen" / "video_cache")))
    canonical_folder = folder.expanduser().resolve()
    identifier = hashlib.sha256(str(canonical_folder).casefold().encode("utf-8")).hexdigest()[:24]
    target = root / identifier
    target.mkdir(parents=True, exist_ok=True)
    return target

def assemble(folder: Path, *, output: str = "slides.mp4", fps: int = 2,
             width: int = 1280, height: int = 720) -> Path:
    folder = folder.expanduser().resolve()
    if not folder.is_dir():
        raise NotADirectoryError(folder)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.mp4", output):
        raise ValueError("Output must be a simple .mp4 filename")
    if fps < 1 or width < 64 or height < 64 or width % 2 or height % 2:
        raise ValueError("fps and even output dimensions must be positive")
    entries = check_inputs(folder)
    import fitz  # only required for uncached PDF page rasterization
    total = sum(row[3] for row in entries)
    # Refuse known-overlong single-file encodes before spending FFmpeg time.
    # Planning coherent parts is a separate upstream requirement; never
    # repair an overlong talk by trimming the final MP4.
    if total >= 599.5:
        raise ValueError(
            f"Single-video narration is {total:.2f}s, too long for a strict "
            "<600s final MP4. Plan separate coherent highlighted parts."
        )
    ffmpeg = ffmpeg_executable()
    print(f"[video] {len(entries)} complete PDF/WAV slide pairs; "
          f"total narration {total:.1f}s; static-slide fps={fps}; "
          f"encoder={ffmpeg}", flush=True)

    # A retry after a killed worker reuses only segments with matching hashes
    # and verifiable video/audio streams. Never trust an orphan .pending file.
    cache = _video_cache(folder)
    segments = []
    for number, pdf, wav, seconds in entries:
        segment = cache / f"segment{number:04d}.mp4"
        stamp = cache / f"segment{number:04d}.json"
        identity = _segment_signature(pdf, wav, seconds, fps, width, height)
        cached = False
        if segment.is_file() and stamp.is_file():
            try:
                if json.loads(stamp.read_text(encoding="utf-8")) == identity:
                    validate_video(ffmpeg, segment, seconds)
                    cached = True
            except (ValueError, OSError, RuntimeError, subprocess.TimeoutExpired):
                cached = False
        if cached:
            print(f"[video] reused validated slide {number}/{len(entries)}", flush=True)
        else:
            # Both the PDF renderer and FFmpeg read only local scratch files.
            # A remote WAV input was the remaining cause of stalled encoders.
            local_pdf = _verified_local_input(
                pdf, cache / f"input{number}.pdf", identity["pdf_sha256"])
            local_wav = _verified_local_input(
                wav, cache / f"input{number}.wav", identity["wav_sha256"])
            with fitz.open(str(local_pdf)) as document:
                if document.page_count != 1:
                    raise ValueError(f"{pdf.name} must contain exactly one PDF page")
                page = document[0]
                scale = min(width / page.rect.width, height / page.rect.height)
                pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                frame = cache / f"frame{number}.png"
                pix.save(str(frame))
            pending = cache / f".segment{number:04d}.pending.mp4"
            pending.unlink(missing_ok=True)
            run_ffmpeg(ffmpeg, [
                "-y", "-loop", "1", "-framerate", str(fps),
                "-i", str(frame), "-i", str(local_wav),
                "-filter:v", f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                             f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
                "-c:v", "libx264", "-threads:v", "2", "-preset", "veryfast", "-crf", "24",
                "-r", str(fps), "-c:a", "aac", "-b:a", "128k",
                "-ar", "44100", "-ac", "2",
                "-t", f"{seconds:.6f}",
                "-movflags", "+faststart", str(pending),
            ], step=f"slide {number}")
            validate_video(ffmpeg, pending, seconds)
            pending.replace(segment)
            stamp_pending = stamp.with_suffix(".json.pending")
            stamp_pending.write_text(json.dumps(identity, sort_keys=True), encoding="utf-8")
            stamp_pending.replace(stamp)
            print(f"[video] encoded slide {number}/{len(entries)} "
                  f"({seconds:.1f}s)", flush=True)
        segments.append(segment)

    listing = cache / "segments.txt"
    listing.write_text("".join(
        "file '" + p.as_posix().replace("'", "'\\''") + "'\n"
        for p in segments
    ), encoding="utf-8")
    candidate = cache / "candidate.mp4"
    run_ffmpeg(ffmpeg, [
        "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
        "-c", "copy", "-movflags", "+faststart", str(candidate)
    ], step="concat")
    finished_seconds = validate_video(ffmpeg, candidate, total)
    if finished_seconds >= 600.0:
        raise RuntimeError(
            f"Encoded MP4 duration {finished_seconds:.2f}s violates the "
            "strict <600s contract; no video has been published."
        )
    dest = folder / output
    if dest.exists():
        archival = folder / ".history" / (
            "video_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        )
        archival.mkdir(parents=True, exist_ok=False)
        old_copy = archival / output
        shutil.copy2(dest, old_copy)
        print(f"[video] archived previous {output} at {old_copy}", flush=True)
    # Only publish a fully-verified, hash-matched copy. Leave the old final
    # video untouched if Google Drive becomes unavailable during publication.
    staged = folder / ("." + output + f".pending.{os.getpid()}")
    try:
        _verified_local_input(candidate, staged, _sha256(candidate))
        validate_video(ffmpeg, staged, total)
        staged.replace(dest)
    finally:
        staged.unlink(missing_ok=True)

    # Cleanup is strictly nonfatal after publication. On failure, keep the
    # cache so a subsequent invocation can resume without re-encoding.
    try:
        shutil.rmtree(cache)
    except OSError as exc:
        print(f"[video] cached segments retained after publication: {exc}", flush=True)
    print(f"[video] SUCCESS: {dest}", flush=True)
    return dest

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reliable FFmpeg slide-PDF/WAV video assembler")
    parser.add_argument("--folder", type=Path, default=Path.cwd())
    parser.add_argument("--output", default="slides.mp4")
    parser.add_argument("--fps", type=int, default=int(os.getenv("MICROGEN_VIDEO_FPS", "2")))
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
