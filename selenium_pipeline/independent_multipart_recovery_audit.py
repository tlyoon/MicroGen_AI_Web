"""Independently re-audit REAL staged multipart MP4s against originals.

Every source WAV sample, encoded duration, sampled decoded highlight frame
and original file identity is freshly checked. This does NOT and MUST NOT
auto-approve provisional source-word/acoustic-pause highlight hypotheses.
"""
from __future__ import annotations
import argparse,json,math,re,wave
from pathlib import Path

from .figure_source_identity import require,_sha
from .highlight_video_preview import ffmpeg_path,probe_mp4
from .original_highlight_pilot_encode import _encoded_sample_pixels
from .original_wav_multipart_plan import inspect_original_slide_wav_plan

_EVENT = re.compile(r"^slide_([0-9]{2,3})_.+_([0-9]{2,3})$")


def _read_exact_json(path:Path)->dict:
    require(path.is_file() and not path.is_symlink() and path.stat().st_size<1_000_000,
            "Missing/broken/oversized review manifest")
    data=json.loads(path.read_text(encoding="utf8"))
    require(type(data) is dict,"Malformed original media receipt")
    return data


def _same_recorded_pcm_as_originals(folder:Path,part:dict,audio:Path)->int:
    require(audio.is_file() and not audio.is_symlink(),
            "Missing or linked staged narration")
    with wave.open(str(audio),"rb") as encoded_audio:
        require(encoded_audio.getnchannels()==1
                and encoded_audio.getsampwidth()==2
                and encoded_audio.getframerate()==24000
                and encoded_audio.getcomptype()=="NONE",
                "Staged WAV has wrong source PCM format")
        consumed=0
        for number in range(part["slide_start"],part["slide_end"]+1):
            original=folder/f"slide{number}.wav"
            with wave.open(str(original),"rb") as src:
                require(src.getnchannels()==1 and src.getsampwidth()==2
                        and src.getframerate()==24000
                        and src.getcomptype()=="NONE",
                        "Original slide WAV format differs")
                expected=src.readframes(src.getnframes())
            received=encoded_audio.readframes(len(expected)//2)
            require(received==expected,"Staged WAV differs from original PCM samples")
            consumed+=len(expected)//2
        require(encoded_audio.readframes(1)==b""
                and consumed==encoded_audio.getnframes(),
                "Staged WAV missing/adding source audio samples")
    return consumed


def independent_reaudit_multipart(*,folder:Path,staged:Path)->dict:
    folder,staged=(Path(p).absolute() for p in (folder,staged))
    require(folder.is_dir() and staged.is_dir() and
            folder != staged and
            not staged.is_relative_to(folder) and
            not folder.is_relative_to(staged),
            "Separate original and staged folders required")
    for p in (folder,staged):
        for ancestor in (p,*p.parents):
            require(not ancestor.is_symlink()
                    and not getattr(ancestor,"is_junction",lambda:False)(),
                    "Linked review evidence forbidden")
    plan=inspect_original_slide_wav_plan(folder)
    manifest=_read_exact_json(staged/"multipart_review_receipt.json")
    require(manifest.get("status")=="COMPLETE_REAL_ORIGINAL_WAV_MULTIPART_REVIEW_ONLY"
            and manifest.get("original_source_sha256")==plan["source_sha256"]
            and manifest.get("original_slides_sha256")==plan["slides_sha256"]
            and manifest.get("student_publication_authorized") is False
            and manifest.get("spoken_element_highlight_semantics_verified") is False
            and manifest.get("technical_production_approved") is False,
            "Forged or stale staged acceptance receipt")
    expected_parts=plan["proposed_parts"]
    actual_parts=manifest.get("parts")
    require(type(actual_parts) is list
            and len(actual_parts)==len(expected_parts)==manifest.get("part_count"),
            "Missing staged multipart coverage")
    originals={str(p):_sha(p) for p in [folder/"source.pdf",folder/"slides.pdf",
       *(folder/f"slide{i}.wav" for i in range(1,plan["original_wav_count"]+1))]}
    exe=ffmpeg_path()
    reports=[]
    for expected,record in zip(expected_parts,actual_parts):
        require(type(record) is dict
                and record.get("part_id")==expected["part_id"]
                and record.get("slide_start")==expected["slide_start"]
                and record.get("slide_end")==expected["slide_end"]
                and record.get("slide_count")==expected["slide_count"]
                and record.get("spoken_element_alignment_verified") is False
                and record.get("student_publication_authorized") is False,
                "Staged part no longer matches original slide boundary")
        part_dir=staged/expected["part_id"]
        require(part_dir.is_dir() and not part_dir.is_symlink(),
                "Missing isolated review part directory")
        mp4=part_dir/(expected["part_id"]+"_review.mp4")
        require(mp4.is_file() and not mp4.is_symlink()
                and _sha(mp4)==record.get("encoded_mp4_sha256"),
                "Actual encoded media SHA differs from manifest")
        samples=_same_recorded_pcm_as_originals(
            folder,expected,part_dir/"narration.wav")
        measured=probe_mp4(mp4,exe=exe)
        require(0<measured["duration_s"]<600
                and abs(measured["duration_s"]-samples/24000)<.65
                and abs(measured["duration_s"]-record.get("encoded_mp4_duration_s",float("inf")))<.03,
                "Actual encoded media not same sub-600s original narration")
        verification=[]
        saved=record.get("decoded_samples")
        require(type(saved) is list and 2<=len(saved)<=3,
                "Incomplete encoded highlight sample receipts")
        for check in saved:
            require(type(check) is dict and
                    isinstance(check.get("element_id"),str)
                    and type(check.get("at_s")) in (int,float)
                    and math.isfinite(check["at_s"])
                    and 0<check["at_s"]<measured["duration_s"],
                    "Invalid encoded highlight sample locator")
            match=_EVENT.fullmatch(check["element_id"])
            require(match is not None,"Unbound encoded original slide element")
            slide_idx,element_idx=map(int,match.groups())
            require(expected["slide_start"]<=slide_idx<=expected["slide_end"]
                    and 1<=element_idx<=30,
                    "Out-of-range encoded element locator")
            ref=part_dir/"reference_frames"/f"slide_{slide_idx:02d}"/f"highlight_{element_idx:03d}.png"
            require(ref.is_file() and not ref.is_symlink(),
                    "Missing independent reference image for highlight")
            diff=_encoded_sample_pixels(exe,mp4,ref,check["at_s"])
            require(diff<16 and
                    abs(diff-check.get("decoded_mean_rgb_difference",float("inf")))<1,
                    "Fresh decoded encoded pixels no longer match receipt")
            verification.append({"element_id":check["element_id"],
                "sample_at_s":check["at_s"],"decoded_mean_rgb_difference":round(diff,4)})
        reports.append({
            "part_id":expected["part_id"],"slide_start":expected["slide_start"],
            "slide_end":expected["slide_end"],
            "original_pcm_frames_verified":samples,
            "fresh_encoded_mp4_duration_s":measured["duration_s"],
            "fresh_decoded_highlight_samples":verification,
            "encoded_duration_strict_below_600":True,
            "spoken_element_alignment_verified":False,
        })
    require(all(_sha(Path(p))==digest for p,digest in originals.items()),
            "Original source PDF/slides/WAV modified during independent re-audit")
    return {
        "schema_version":1,
        "status":"REAL_ENCODED_MULTIPART_TECHNICAL_REVIEW_VERIFIED_SEMANTIC_ALIGNMENT_BLOCKED",
        "verified_part_count":len(reports),
        "parts":reports,
        "complete_source_slide_coverage":True,
        "source_pcm_sample_equality_verified":True,
        "encoded_duration_under_600_verified":True,
        "sampled_encoded_highlight_pixels_verified":True,
        "speech_to_element_semantic_alignment_verified":False,
        "original_figure_academic_semantics_verified":False,
        "all_visual_elements_highlighted_as_spoken_verified":False,
        "human_listening_qa_verified":False,
        "student_publication_authorized":False,
        "all_original_teaching_assets_preserved":True,
    }


def summarize_original_subtopic_readonly(folder:Path)->dict:
    root=Path(folder).absolute()
    try:
        plan=inspect_original_slide_wav_plan(root)
        return {
            "subchapter":root.name,
            "status":"ORIGINAL_WAV_MULTIPART_PREFLIGHT_AVAILABLE_REPLACEMENT_NOT_VERIFIED",
            "original_wav_count":plan["original_wav_count"],
            "original_total_wav_duration_s":plan["total_original_wav_duration_s"],
            "proposed_parts":[{
                "start":x["slide_start"],"end":x["slide_end"],
                "audio_s":x["original_wav_duration_sum_s"]}
                for x in plan["proposed_parts"]],
            "verified_replacement_mp4_exists":False,
            "spoken_highlight_synchronized":False,
            "publication_authorized":False,
        }
    except Exception as exc:
        return {"subchapter":root.name,
                "status":"ORIGINAL_WAV_PREFLIGHT_BLOCKED",
                "exception_type":type(exc).__name__,
                "publication_authorized":False}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",type=Path,required=True)
    p.add_argument("--staged",type=Path)
    p.add_argument("--preflight-only",action="store_true")
    a=p.parse_args(argv)
    if a.preflight_only:
        result=summarize_original_subtopic_readonly(a.folder)
    else:
        require(a.staged is not None,"Re-audit requires the exact staged review folder")
        result=independent_reaudit_multipart(folder=a.folder,staged=a.staged)
    print(json.dumps(result,indent=2,sort_keys=True))
    return 2

if __name__=="__main__":
    raise SystemExit(main())
