"""Genuine original-media production readiness ledger with strict release block.

Distinguishes source visuals, historical remux previews, new corrected PCM,
independent mathematical approval, voice fidelity, narration sync and release.
No Gemini or TTS call; emits only a private machine-local audit receipt.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from .offline_corrected_bundle_verify import verify_original_five_bundle
from .original_replacement_video_handoff import build_original_replacement_handoff
from .production_video_contract import _mp4_duration

class ReadinessError(ValueError):pass
def need(ok,msg):
    if not ok:raise ReadinessError(msg)
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""):h.update(b)
    return h.hexdigest()
def offline_original_readiness(*,chapter:Path,corrected_bundle:Path|None=None,
                               historical_preview_dir:Path|None=None)->dict:
    root=Path(chapter).absolute()
    original=build_original_replacement_handoff(chapter_folder=root)
    sections=original["sections"]
    sources={s["subchapter"]:s["original_source_sha256"] for s in sections}
    preview_visual_count=0
    if corrected_bundle is not None:
        result=verify_original_five_bundle(
            original=root/"8.4",bundle=Path(corrected_bundle))
        need(result["source_sha256"]==sources["8.4"],
             "Five-unit corrected visuals belong to different source")
        preview_visual_count=result["verified_image_count"]
    clips=[]
    if historical_preview_dir is not None:
        folder=Path(historical_preview_dir).absolute()
        receipt=folder/"UNAPPROVED_HISTORICAL_CLIPS.json"
        need(folder.is_dir() and not folder.is_symlink() and receipt.is_file()
             and not receipt.is_symlink(),"Original review-only clips missing")
        manifest=json.loads(receipt.read_text(encoding="utf8"))
        need(manifest.get("status")==
             "SIX_GENUINE_HISTORICAL_REVIEW_MP4_CLIPS_NOT_LECTURE_REPLACEMENTS"
             and manifest.get("clip_count")==6 and len(manifest.get("clips",[]))==6
             and manifest.get("student_publication_authorized") is False
             and manifest.get("actual_speech_to_highlight_synchronization_approved") is False,
             "Historical clips falsely advertised as production media")
        seen=set()
        for item in manifest["clips"]:
            topic=item["section"];part=item["part_id"]
            need(topic in sources and part in ("part_01","part_02")
                 and (topic,part) not in seen
                 and item.get("source_pdf_sha256")==sources[topic]
                 and item.get("original_audio_used") is True
                 and item.get("corrected_math_or_Kore_audio_used") is False
                 and item.get("student_publication_authorized") is False,
                 "Invalid or falsely accepted historical clip identity")
            seen.add((topic,part))
            movie=Path(item["path"]).absolute()
            need(movie.is_file() and not movie.is_symlink()
                 and movie.parent==folder
                 and sha(movie)==item["sha256"],
                 "Preview video altered or outside isolated folder")
            actual=_mp4_duration(movie)
            need(0<actual<600 and abs(actual-item["actual_encoded_duration_s"])<.011,
                 "Real video duration differs from original audit receipt")
            clips.append({"section":topic,"part":part,"duration_s":actual,
                          "historical_only":True,"new_corrected_audio":False})
    blockers=[
        "missing_independent_two_pass_original_source_mathematics_acceptance",
        "missing_actual_verified_corrected_Kore_speech_for_each_changed_utterance",
        "missing_verified_new_speech_to_slide_element_timestamps",
        "missing_six_new_source_corrected_decoded_pixel_accepted_MP4s",
        "missing_strict_final_production_video_contract_pass",
    ]
    return {"status":"ORIGINAL_LECTURE_MEDIA_READINESS_NOT_ACCEPTED",
            "original_source_sha256":sources,
            "actual_original_whole_video_durations_s":{
                s["subchapter"]:s["original_encoded_MP4_duration_s"] for s in sections},
            "corrected_source_visuals_reverified":preview_visual_count,
            "real_historical_review_mp4_count":len(clips),
            "historical_review_clips":clips,
            "corrected_Kore_WAV_accepted_count":0,
            "independent_mathematics_passes_complete":False,
            "per_element_speech_highlight_synchronized":False,
            "strict_new_corrected_video_parts_accepted":0,
            "release_blockers":blockers,
            "student_publication_authorized":False,
            "original_media_modified":False,
            "gemini_requests_sent":0}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--chapter",required=True,type=Path)
    p.add_argument("--bundle",type=Path)
    p.add_argument("--historical-review-clips",type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args(argv);out=a.out.absolute()
    need(out.parent.is_dir() and not out.exists()
         and not out.is_relative_to(a.chapter.absolute()),
         "New external exclusive report only")
    r=offline_original_readiness(chapter=a.chapter,corrected_bundle=a.bundle,
                                 historical_preview_dir=a.historical_review_clips)
    with out.open("x",encoding="utf8") as f:json.dump(r,f,indent=2)
    print(json.dumps({"status":r["status"],
                      "historic_encoded_preview_clips":r["real_historical_review_mp4_count"],
                      "new_corrected_accepted_mp4s":0,
                      "release_blockers":len(r["release_blockers"]),
                      "student_published":False}))
if __name__=="__main__":main()
