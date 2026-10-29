"""Revalidate a REAL original Slide4 five-unit preview bundle before audio.

Read only; never turn an unreviewed image into an accepted spoken video.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from PIL import Image,ImageChops
import pymupdf
from .highlight_frames import emphasize_source_rectangles
from .original_slide4_math_correction_pilot import prepare_corrected_original_slide4
from .original_slide4_five_visual_candidates import inspect_original_slide4_five_visual_candidates

class OfflineBundleError(ValueError):pass
def need(ok,message):
    if not ok:raise OfflineBundleError(message)
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""):h.update(b)
    return h.hexdigest()
def strict_json(path):
    def unique(pairs):
        obj={}
        for k,v in pairs:
            need(k not in obj,"Duplicate bundle JSON key")
            obj[k]=v
        return obj
    need(path.is_file() and not path.is_symlink() and path.stat().st_size<200000,
         "Missing/linked/oversized bundle JSON")
    return json.loads(path.read_text(encoding="utf8"),object_pairs_hook=unique)
def verify_original_five_bundle(*,original:Path,bundle:Path)->dict:
    root=Path(original).absolute()
    dest=Path(bundle).absolute()
    need(root.is_dir() and dest.is_dir() and not dest.is_symlink()
         and not dest.is_relative_to(root),"Separate original and local bundle required")
    doc=strict_json(dest/"FIVE_CORRECTED_SEGMENTS_UNAPPROVED.json")
    need(doc.get("status")=="GENUINE_ORIGINAL_FIVE_CORRECTED_SEGMENTS_VISUALLY_STAGED_NOT_APPROVED"
         and doc.get("segment_count")==5 and doc.get("slide")==4
         and doc.get("real_new_TTS_WAV_count")==0
         and doc.get("independent_two_pass_math_acceptance") is False
         and doc.get("actual_MP4_accepted") is False
         and doc.get("student_publication_authorized") is False,
         "Not a valid unapproved original bundle")
    paths=("source.pdf","slides.pdf","script.txt","slide4.wav")
    original_sha={name:sha(root/name) for name in paths}
    for name,field in zip(paths,("source_sha256","slides_sha256","script_sha256",
                                 "historical_slide4_WAV_sha256")):
        need(doc.get(field)==original_sha[name],"Original source/media drift")
    plan=prepare_corrected_original_slide4(folder=root)
    figures=inspect_original_slide4_five_visual_candidates(folder=root)
    units=doc.get("source_verified_tts_highlight_units")
    need(type(units) is list and len(units)==5,"Must be five source-aligned units")
    preview=dest/"source_visual_preview"
    need(preview.is_dir() and not preview.is_symlink(),"Missing real preview assets")
    allowed={"UNAPPROVED_source_slide4_candidate_%03d.png"%i for i in range(1,6)}
    need({p.name for p in preview.iterdir()}==allowed,
         "Extra/missing source preview images")
    with pymupdf.open(root/"slides.pdf") as slides:
        need(len(slides)>=4,"Original source Slide4 missing")
        pix=slides[3].get_pixmap(matrix=pymupdf.Matrix(2,2),alpha=False)
        original_rgb=Image.frombytes("RGB",(pix.width,pix.height),pix.samples)
    for i,(u,expected,figure) in enumerate(zip(units,plan["corrected_utterances"],
                                               figures["utterance_candidates"]),1):
        need(type(u) is dict and
             u.get("original_utterance_id")==expected["original_utterance_id"]
             and u.get("corrected_tts_text")==expected["revised_narration"]
             and u.get("corrected_tts_text_sha256")==expected["revised_text_sha256"]
             and u.get("source_verified_visual_target_id")==figure["review_target_id"]
             and u.get("bbox_pdf_pt")==figure["candidate_highlight_bbox_pdf_pt"]
             and u.get("preferred_voice")=="Kore"
             and u.get("preferred_provider")=="Gemini web Flash-Lite TTS"
             and u.get("revised_text_independently_approved") is False
             and u.get("corrected_real_WAV_exists") is False
             and u.get("actual_chunk_start_ms") is None
             and u.get("actual_chunk_end_ms") is None,
             "Corrected text/target/voice/timing metadata changed")
        relative=f"source_visual_preview/UNAPPROVED_source_slide4_candidate_{i:03d}.png"
        need(u.get("preview_png_relative_path")==relative
             and u.get("tts_audio_relative_path_expected")==f"new_Kore_utterance_{i:03d}.wav",
             "Stale or unexpected audio/PNG path")
        image=dest/relative
        need(image.is_file() and not image.is_symlink()
             and sha(image)==u.get("preview_png_sha256"),
             "Preview pixel bytes changed")
        with Image.open(image) as actual:
            need(actual.format=="PNG" and actual.width>=500
                 and actual.height>=250,"Corrupted source visual")
            actual.load()
            expected_pixels=emphasize_source_rectangles(
                original_rgb,[u["bbox_pdf_pt"]],scale=2)
            need(actual.size==expected_pixels.size
                 and ImageChops.difference(actual.convert("RGB"),
                                           expected_pixels).getbbox() is None,
                 "Real original PDF highlight pixels differ despite manifest/hash")
        need(not (dest/u["tts_audio_relative_path_expected"]).exists(),
             "Unregistered new audio appeared; requires separate ingestion")
    need(all(sha(root/name)==digest for name,digest in original_sha.items()),
         "Original changed during verification")
    return {"status":"FIVE_REAL_SOURCE_IMAGES_AND_CORRECTED_TEXT_VERIFIED_AUDIO_UNAPPROVED",
            "source_sha256":original_sha["source.pdf"],
            "verified_image_count":5,"verified_corrected_text_count":5,
            "independent_math_approved":False,"tts_audio_validated":False,
            "new_video_accepted":False,"student_publication_authorized":False}
