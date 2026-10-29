"""Original-media grounded, STRICTLY UNAPPROVED six-part replacement handoff.

Windows/Dell-only production planning uses genuine original slide WAV frames,
actual container duration, original hashes, and the source-mapped storyboard
contracts. It does not synthesize audio, render a new video, or grant release.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import wave
from pathlib import Path
from .original_wav_multipart_plan import inspect_original_slide_wav_plan
from .production_video_contract import _mp4_duration

SECTIONS=("8.4","8.5","8.6")
_OLD_MINIMUM=600.0

def _sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def _require(test,message):
    if not test:raise ValueError(message)

def build_original_replacement_handoff(*,chapter_folder:Path,
                                        sections:tuple[str,...]=SECTIONS)->dict:
    chapter=Path(chapter_folder).absolute()
    _require(chapter.is_dir() and not chapter.is_symlink(),
             "Expected original chapter directory")
    _require(type(sections) is tuple and 1<=len(sections)<=15
             and len(set(sections))==len(sections)
             and all(s and s.replace(".","").isdigit() for s in sections),
             "Unique bounded numeric subchapter names required")
    entries=[]
    for topic in sections:
        folder=chapter/topic
        _require(folder.is_dir() and not folder.is_symlink(),
                 "Genuine original subchapter is missing")
        original=inspect_original_slide_wav_plan(folder)
        legacy=folder/"slides.mp4"
        _require(legacy.is_file() and not legacy.is_symlink(),
                 "Historical encoded video must be inspected, not guessed")
        source_sha=_sha(folder/"source.pdf")
        slides_sha=_sha(folder/"slides.pdf")
        old_sha=_sha(legacy)
        actual=_mp4_duration(legacy)
        _require(actual>=_OLD_MINIMUM,
                 "Historical MP4 does not exceed strict duration cap; do not misclassify")
        _require(original["source_sha256"]==source_sha
                 and original["slides_sha256"]==slides_sha
                 and original["total_original_wav_duration_s"]>0,
                 "Original WAV/PDF source drift")
        parts=[]
        for item in original["proposed_parts"]:
            _require(item["within_audio_only_budget"] is True
                     and item["original_wav_duration_sum_s"]<540.0001,
                     "Original-audio candidate boundary exceeds safe budget")
            parts.append({
                "part_id":item["part_id"],
                "slide_start":item["slide_start"],"slide_end":item["slide_end"],
                "historical_WAV_duration_s":item["original_wav_duration_sum_s"],
                "new_per_element_same_voice_WAVs_received":False,
                "corrected_spoken_text_verified":False,
                "independent_source_math_review_complete":False,
                "word_or_segment_timing_verified":False,
                "visual_highlight_pixels_verified":False,
                "new_actual_encoded_MP4_strictly_under_600s_verified":False,
                "student_publication_authorized":False,
            })
        _require(parts[0]["slide_start"]==1
                 and parts[-1]["slide_end"]==original["original_wav_count"]
                 and all(parts[i]["slide_start"]==parts[i-1]["slide_end"]+1
                         for i in range(1,len(parts))),
                 "Gapped or overlapping historic slide boundaries")
        _require(_sha(folder/"source.pdf")==source_sha
                 and _sha(folder/"slides.pdf")==slides_sha
                 and _sha(legacy)==old_sha,
                 "Protected original changed during planning")
        entries.append({
            "subchapter":topic,
            "original_source_sha256":source_sha,
            "original_slides_sha256":slides_sha,
            "original_historical_MP4_sha256":old_sha,
            "original_encoded_MP4_duration_s":actual,
            "original_MP4_fails_600s":True,
            "original_slide_WAV_count":original["original_wav_count"],
            "original_slide_WAV_duration_s":original["total_original_wav_duration_s"],
            "original_WAV_provenance":[{"slide":x["slide_index"],"sha256":x["sha256"],
                                        "duration_s":x["duration_s"]}
                                       for x in original["wav_evidence"]],
            "part_count":len(parts),"proposed_parts":parts,
            "source_or_historical_media_modified":False,
        })
    return {
        "schema_version":1,
        "status":"ACTUAL_ORIGINAL_VIDEO_REPLACEMENTS_PLANNED_NOT_GENERATED",
        "original_chapter_root":str(chapter),
        "sections":entries,
        "total_new_parts_proposed":sum(x["part_count"] for x in entries),
        "requires_genuine_corrected_TTS_and_math_and_highlight_qa":True,
        "no_legacy_audio_can_be_marked_as_corrected":True,
        "final_duration_must_be_measured_from_actual_encoded_MP4":True,
        "stage_requires_existing_strict_production_video_contract":True,
        "all_independent_academic_review_passes_approved":False,
        "any_new_mp4_created":False,
        "all_parts_accepted":False,
        "student_publication_authorized":False,
    }

def check_replacement_audio_readiness(*,handoff:dict,replacements:dict)->dict:
    """Reject historic WAV relabeling, missing source-verified reviewed speech.

    Produces only per-utterance audio readiness; never certifies words, timing
    or video. All supplied replacement files MUST be outside original chapter.
    """
    _require(handoff.get("schema_version")==1
             and handoff.get("status")=="ACTUAL_ORIGINAL_VIDEO_REPLACEMENTS_PLANNED_NOT_GENERATED",
             "Expected genuine-original-bound planning receipt")
    original=Path(handoff["original_chapter_root"]).absolute()
    _require(type(replacements) is dict,"Replacement map required")
    target={}
    for section in handoff["sections"]:
        sec=section["subchapter"]
        indexed=section["original_WAV_provenance"]
        original_hashes={r["slide"]:r["sha256"] for r in indexed}
        for idx,old in original_hashes.items():
            key=f"{sec}/{idx}"
            candidate=replacements.get(key)
            if candidate is None:
                continue
            _require(type(candidate) is dict and
                     set(candidate)=={"path","source_text_sha256",
                                     "voice_id","provider","source_math_passes"},
                     "Explicit reviewed replacement audio receipt required")
            path=Path(candidate["path"]).absolute()
            _require(path.is_file() and not path.is_symlink()
                     and not path.is_relative_to(original),
                     "Candidate audio must be external and a regular file")
            _require(path.suffix.lower()==".wav"
                     and _sha(path)!=old,
                     "Historical slide WAV cannot masquerade as revised Kore speech")
            try:
                with wave.open(str(path),"rb") as audio:
                    channels=audio.getnchannels()
                    width=audio.getsampwidth()
                    rate=audio.getframerate()
                    frames=audio.getnframes()
                    codec=audio.getcomptype()
                    first=audio.readframes(min(frames,1024))
            except (wave.Error,OSError,EOFError) as exc:
                raise ValueError("Replacement WAV must decode to actual PCM") from exc
            _require(codec=="NONE" and channels==1 and width==2
                     and 16000<=rate<=48000 and frames>=rate//5
                     and any(first),
                     "Replacement WAV must contain nonempty, well-formed PCM narration")
            _require(type(candidate["source_text_sha256"]) is str
                     and len(candidate["source_text_sha256"])==64
                     and candidate["source_math_passes"]==2
                     and candidate["voice_id"]=="Kore"
                     and candidate["provider"] in {"Gemini Flash-Lite TTS",
                                                   "Gemini Flash TTS"},
                     "Real corrected Kore provider/text and two academic passes required")
            # Do NOT assert actual words match text merely from text_hash.
            target[key]={"wav_sha256":_sha(path),
                         "actual_spoken_words_independently_verified":False,
                         "actual_highlight_timing_verified":False,
                         "encoded_part_mp4_verified":False}
    _require(target,"No corrected audio; cannot mark genuine audio progress")
    return {"status":"PCM_REPLACEMENT_CANDIDATES_PRESENT_SPOKEN_CONTENT_UNREVIEWED",
            "replaced":target,"student_publication_authorized":False}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--chapter",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    args=p.parse_args(argv)
    out=args.out.absolute()
    _require(out.parent.is_dir() and not out.exists()
             and not out.is_relative_to(args.chapter.absolute()),
             "Use NEW exclusive external handoff path")
    result=build_original_replacement_handoff(chapter_folder=args.chapter)
    with out.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,sort_keys=True,ensure_ascii=False);f.write("\n")
    print(json.dumps({"status":result["status"],
                      "total_new_parts_proposed":result["total_new_parts_proposed"],
                      "mp4s":[(x["subchapter"],x["original_encoded_MP4_duration_s"])
                              for x in result["sections"]],
                      "video_approved":False,"out":str(out)}))
if __name__=="__main__":
    main()
