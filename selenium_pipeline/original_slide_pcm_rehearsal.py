"""Real original slide/WAV technical rehearsal, preserving every teaching asset.

This renders the actual existing slide while its actual existing slide WAV
plays. It is NOT spoken-to-element highlighting, nor a publishable lecture.
"""
from __future__ import annotations
import json,subprocess,wave
from pathlib import Path
import pymupdf
from .figure_source_identity import require,_sha
from .original_wav_multipart_plan import inspect_original_slide_wav_plan
from .runner import blocks
from .highlight_video_preview import ffmpeg_path,probe_mp4

def rehearse_original_slide(*,folder:Path,slide_number:int,
                            destination:Path,exe:str|None=None)->dict:
    folder,destination=Path(folder).absolute(),Path(destination).absolute()
    require(type(slide_number) is int and slide_number>0
            and destination.parent.is_dir() and not destination.exists()
            and not destination.is_relative_to(folder)
            and not folder.is_relative_to(destination),
            "Use independent new review folder; original media immutable")
    original=inspect_original_slide_wav_plan(folder)
    wavs=original["wav_evidence"]
    require(slide_number<=len(wavs)
            and wavs[slide_number-1]["slide_index"]==slide_number,
            "Missing original recorded slide")
    wav=folder/wavs[slide_number-1]["relative_name"]
    script=folder/"script.txt"
    require(script.is_file() and not script.is_symlink(),
            "Missing exact existing original narration")
    script_hash=_sha(script)
    text=blocks(script.read_text(encoding="utf-8-sig"))
    require(len(text)==len(wavs) and text[slide_number-1][0]==slide_number,
            "Original narration, slide and WAV order disagree")
    expected_wav_sha=wavs[slide_number-1]["sha256"]
    with wave.open(str(wav),"rb") as audio:
        require(audio.getcomptype()=="NONE"
                and audio.getframerate()>0 and audio.getnframes()>0
                and audio.getnchannels()==1 and audio.getsampwidth()==2,
                "Original real slide audio must be supported mono PCM16 WAV")
        seconds=audio.getnframes()/audio.getframerate()
    require(.1<seconds<540,"Unsupported original whole-slide WAV duration")
    with pymupdf.open(folder/"slides.pdf") as pdf:
        require(len(pdf)==len(wavs),"Source slide count changed")
        pix=pdf[slide_number-1].get_pixmap(
            matrix=pymupdf.Matrix(2,2),
            colorspace=pymupdf.csRGB,alpha=False)
        png=pix.tobytes("png")
    original_pdf_sha=original["slides_sha256"]
    require(_sha(folder/"slides.pdf")==original_pdf_sha
            and _sha(wav)==expected_wav_sha
            and _sha(script)==script_hash,
            "Original real slide/audio/text mutated before staging")
    destination.mkdir()
    from PIL import Image
    import io
    # Stable even dimensions required by yuv420p.
    with Image.open(io.BytesIO(png)) as frame:
        w,h=frame.size
        frame.convert("RGB").resize((w+w%2,h+h%2)).save(
            destination/"slide.png")
    runner=exe or ffmpeg_path()
    movie=destination/"original_slide_technical_rehearsal.mp4"
    command=[runner,"-hide_banner","-loglevel","error","-nostdin",
        "-loop","1","-framerate","10","-i",str(destination/"slide.png"),
        "-i",str(wav),"-c:v","libx264","-preset","ultrafast",
        "-pix_fmt","yuv420p","-c:a","aac","-shortest",
        "-y",str(movie)]
    result=subprocess.run(command,capture_output=True,timeout=120)
    require(result.returncode==0 and movie.is_file(),"Original slide audio rehearsal encode failed")
    encoded=probe_mp4(movie,exe=runner)
    require(0<encoded["duration_s"]<600
            and abs(encoded["duration_s"]-seconds)<.5,
            "Encoded lecture preview exceeds strict original-audio timing")
    require(_sha(folder/"slides.pdf")==original_pdf_sha
            and _sha(wav)==expected_wav_sha
            and _sha(script)==script_hash,
            "Original teaching inputs changed during video rehearsal")
    receipt={"status":"GENUINE_ORIGINAL_SLIDE_WAV_TECHNICAL_REHEARSAL_ONLY",
             "slide":slide_number,"original_slides_sha256":original_pdf_sha,
             "original_wav_sha256":expected_wav_sha,
             "original_script_sha256":script_hash,
             "original_wav_duration_s":round(seconds,4),
             "actual_mp4_encoded_duration_s":encoded["duration_s"],
             "actual_preview_mp4_sha256":_sha(movie),
             "actual_spoken_word_element_timing_verified":False,
             "element_level_highlighting_implemented":False,
             "academic_listening_qa_verified":False,
             "production_media_approved":False,
             "student_publication_authorized":False}
    with (destination/"receipt.json").open("x",encoding="utf8") as out:
        json.dump(receipt,out,indent=2)
        out.write("\n")
    return receipt
