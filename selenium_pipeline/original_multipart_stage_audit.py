"""Read-only, independent audit of genuine original-WAV multipart MP4 previews.

Freshly checks original PCM WAV hashes and actual encoded MP4 durations.
Accepting a technical whole-slide preview NEVER satisfies spoken-element sync.
"""
from __future__ import annotations
import json
from pathlib import Path
from .figure_source_identity import require,_sha
from .original_wav_multipart_plan import inspect_original_slide_wav_plan
from .highlight_video_preview import probe_mp4,ffmpeg_path

def audit_whole_slide_staging(*,root:Path,staged:Path,names:tuple[str,...],start_part:int=1)->dict:
    root,staged=Path(root).absolute(),Path(staged).absolute()
    require(root.is_dir() and staged.is_dir()
            and not staged.is_relative_to(root)
            and type(names) is tuple and len(set(names))==len(names)
            and 1<=len(names)<=30
            and type(start_part) is int and 1<=start_part<=40,
            "Isolated original-asset technical preview stage required")
    items=[]
    for name in names:
        require(type(name) is str and name.replace(".","").isdigit()
                and name.count(".")==1 and ".." not in name,
                "Subchapter name cannot leave original teaching root")
        folder=root/name
        receipt_path=staged/f"{name.replace('.','_')}_receipt.json"
        require(receipt_path.is_file(),"Missing independently created review checkpoint")
        row=json.loads(receipt_path.read_text(encoding="utf8"))
        require(row.get("subchapter")==name
                and row.get("student_publication_authorized") is False
                and row.get("element_spoken_word_sync_verified") is False
                and type(row.get("parts")) is list,
                "Forged production status or altered subchapter receipt")
        original=inspect_original_slide_wav_plan(folder)
        expected=original["proposed_parts"]
        verified=[]
        require(row.get("starting_part_number",1)==start_part,
                "Staging starting-part must match selected independent review")
        for relative_index,piece in enumerate(row["parts"]):
            idx=start_part-1+relative_index
            require(idx<len(expected)
                    and piece.get("part_id")==expected[idx]["part_id"]
                    and piece.get("status")=="GENUINE_WHOLE_SLIDE_MULTIPART_REVIEW_ONLY",
                    "Part missing, reordered or failed; no technical acceptance")
            bundle=staged/name/piece["part_id"]
            path=bundle/"whole_slide_multipart_review.mp4"
            evidence=json.loads((bundle/"multipart_receipt.json").read_text(encoding="utf8"))
            require(path.is_file() and _sha(path)==piece.get("sha256")
                    and evidence.get("mp4_sha256")==piece["sha256"]
                    and evidence.get("student_publication_authorized") is False
                    and evidence.get("actual_words_on_screen_timing_verified") is False
                    and evidence.get("element_level_highlight_verified") is False
                    and evidence.get("original_file_sha256",{}).get("source.pdf")
                        ==original["source_sha256"]
                    and evidence.get("original_file_sha256",{}).get("slides.pdf")
                        ==original["slides_sha256"]
                    and evidence.get("slide_range")==
                        [expected[idx]["slide_start"],expected[idx]["slide_end"]],
                    "Source provenance or actual preview MP4 content changed")
            inspected=probe_mp4(path,exe=ffmpeg_path())
            planned_seconds=expected[idx]["original_wav_duration_sum_s"]
            require(0<inspected["duration_s"]<600
                    and abs(inspected["duration_s"]-planned_seconds)<.75
                    and abs(inspected["duration_s"]-piece["encoded_seconds"])<.11,
                    "Measured encoded preview breaks original PCM clock")
            verified.append({"part_id":piece["part_id"],
                             "actual_mp4_sha256":piece["sha256"],
                             "actual_encoded_duration_s":inspected["duration_s"],
                             "original_wav_s":planned_seconds})
        items.append({"name":name,
                      "verified_original_whole_slide_review_parts":verified,
                      "unreviewed_part_count":len(expected)-len(verified),
                      "all_parts_technically_reviewed":start_part==1 and len(expected)==len(verified),
                      "student_publication_authorized":False})
    return {"status":"FRESH_ORIGINAL_WAV_ENCODED_PREVIEW_AUDIT_REVIEW_ONLY",
            "items":items,
            "total_verified_preview_parts":sum(
                len(i["verified_original_whole_slide_review_parts"])
                for i in items),
            "all_lecture_parts_technically_present":all(
                x["all_parts_technically_reviewed"] for x in items),
            "source_semantic_element_sync_verified":False,
            "human_academic_listening_qa_verified":False,
            "production_mp4_replacements_approved":False,
            "student_publication_authorized":False}
