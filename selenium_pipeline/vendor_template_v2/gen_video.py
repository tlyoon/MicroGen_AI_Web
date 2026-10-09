# -*- coding: utf-8 -*

# MicroGen_AI Educational Automation Package
# � 2025 Dr. Yoon Tiem Leong, School of Physics, Universiti Sains Malaysia.
# This file is part of the MicroGen_AI package.
# Licensed under the MIT License (see LICENSE file in the project root).
# You may not use this file except in compliance with the License.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

# gen_video.py
# ---------------------------------------------------------------
# PDF slide images + per-slide WAV -> slides.mp4
# Spyder/Windows-safe: guarded entrypoint, limited threads, clean closes
# Shows % progress while writing the video.
# ---------------------------------------------------------------

import os, sys, re, time
from pathlib import Path

# ---- crash-avoid env knobs (set BEFORE heavy imports) ----
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_MAX_THREADS", "1")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
# Optional: let imageio-ffmpeg pick bundled ffmpeg
os.environ.setdefault("IMAGEIO_FFMPEG_EXE", "")

def _check_deps():
    """Fail fast with a clear message if deps are missing."""
    missing = []
    try:
        import numpy as _np  # noqa
    except Exception:
        missing.append("numpy")
    try:
        import moviepy  # noqa
        import moviepy.editor as _mp  # noqa
    except Exception:
        missing.append("moviepy")
    try:
        import proglog  # noqa
    except Exception:
        missing.append("proglog")
    try:
        import pdf2image  # noqa
    except Exception:
        missing.append("pdf2image")
    if missing:
        print("Missing packages:", ", ".join(missing))
        print("Install in THIS environment, e.g.:")
        print("  python -m pip install moviepy==1.0.3 proglog==0.1.10 decorator==4.4.2 imageio imageio[ffmpeg] pdf2image numpy")
        sys.exit(1)

# ---------- Progress logger (prints % complete) ----------
from proglog import ProgressBarLogger
class SimpleLogger(ProgressBarLogger):
    def bars_callback(self, bar, attr, value, old_value=None):
        # 't' is the main time/progress bar MoviePy uses
        if bar == 't':
            total = self.bars[bar].get('total') or 0
            if total:
                pct = (value / total) * 100
                print(f"\rVideo creation: {pct:5.1f}% done", end="", flush=True)

def build_video(output_filename: str = "slides.mp4"):
    import numpy as np
    import moviepy.editor as mp
    from pdf2image import convert_from_path

    videofile = output_filename

    # Remove previous output if present
    try:
        Path(videofile).unlink()
    except Exception:
        pass

    # Find files: slideN.pdf + slideN.wav (N = 1..)
    pdf_files = sorted(
        [f for f in os.listdir(".") if f.lower().endswith(".pdf") and re.match(r"slide\d+\.pdf", f, re.IGNORECASE)],
        key=lambda x: int(re.search(r"\d+", x).group()),
    )
    wav_files = sorted(
        [f for f in os.listdir(".") if f.lower().endswith(".wav") and re.match(r"slide\d+\.wav", f, re.IGNORECASE)],
        key=lambda x: int(re.search(r"\d+", x).group()),
    )

    if not pdf_files or not wav_files:
        print("Error: No PDF or WAV files found using pattern 'slideN.pdf' / 'slideN.wav'.")
        sys.exit(1)

    if len(pdf_files) != len(wav_files):
        print(f"len(pdf_files)={len(pdf_files)}; len(wav_files)={len(wav_files)}")
        print("Error: Number of PDF and WAV files does not match. Abort.")
        sys.exit(1)
    else:
        print(f"len(pdf_files)={len(pdf_files)}; len(wav_files)={len(wav_files)}")
        print("Number of PDF and WAV tallies. Generating video ...")

    image_clips, audio_clips = [], []

    # Build per-slide image clip with duration = audio duration
    for pdf_file, wav_file in zip(pdf_files, wav_files):
        if not (Path(pdf_file).exists() and Path(wav_file).exists()):
            print(f"Error: Both {pdf_file} and {wav_file} must exist. Abort.")
            sys.exit(1)

        try:
            images = convert_from_path(pdf_file, dpi=200)
            if not images:
                print(f"Error: Could not convert PDF {pdf_file} to image.")
                sys.exit(1)

            image = images[0]
            if image.mode != "RGB":
                image = image.convert("RGB")

            image_array = np.array(image)
            audio_clip = mp.AudioFileClip(wav_file)
            image_clip = mp.ImageClip(image_array).set_duration(audio_clip.duration)

            image_clips.append(image_clip)
            audio_clips.append(audio_clip)
            print(f"processing ({pdf_file}, {wav_file})")

        except Exception as e:
            print(f"Error processing {pdf_file} or {wav_file}: {e}")
            print("os.path.exists(pdf_file)", Path(pdf_file).exists())
            print("os.path.exists(wav_file)", Path(wav_file).exists())
            sys.exit(1)

    # Concatenate and write
    if not image_clips:
        print("No valid image clips found. Cannot create video.")
        sys.exit(1)

    final_clip = None
    final_audio = None
    try:
        final_clip = mp.concatenate_videoclips(image_clips, method="compose")
        final_audio = mp.concatenate_audioclips(audio_clips)
        # Carry FPS on the clip itself as well as passing it to write_videofile.
        # MoviePy 1.0.3 can lose the fps keyword through its decorator wrapper
        # when a mismatched external decorator package is imported on Windows.
        # A clip-level FPS keeps ffmpeg_writer from receiving fps=None.
        final_clip = final_clip.set_audio(final_audio).set_fps(24)

        # Safer defaults for Spyder/Windows + progress logger
        final_clip.write_videofile(
            videofile,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            threads=1,            # stability in IDEs
            preset="medium",
            verbose=True,
            logger=SimpleLogger() # <-- percent progress here
        )
        print("\nVideo writing complete.")
        print(f"Video created successfully: {videofile}")

    except Exception as e:
        print(f"An error occurred during video creation: {e}")
        sys.exit(1)

    finally:
        # Close all clips to release resources
        try:
            if final_clip is not None:
                final_clip.close()
        except Exception:
            pass
        try:
            if final_audio is not None:
                final_audio.close()
        except Exception:
            pass
        for clip in image_clips:
            try:
                clip.close()
            except Exception:
                pass
        for clip in audio_clips:
            try:
                clip.close()
            except Exception:
                pass
        print("Clips closed to release resources.")

def main():
    _check_deps()

    # Optional diagnostics
    try:
        import imageio_ffmpeg
        print("ffmpeg exe:", imageio_ffmpeg.get_ffmpeg_exe())
    except Exception:
        print("Warning: imageio-ffmpeg not found; MoviePy may fail to write video.")

    # Build the video
    out = "slides.mp4"
    build_video(out)

if __name__ == "__main__":
    # Windows/Spyder-safe multiprocessing guard
    import multiprocessing as mp
    mp.freeze_support()
    try:
        mp.set_start_method("spawn", force=True)
    except RuntimeError:
        pass

    # Recommended for Spyder: disable UMR in Preferences (optional)
    main()
    time.sleep(1)
