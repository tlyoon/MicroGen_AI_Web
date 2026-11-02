"""Reconcile genuine 38/41 focused ORIGINAL slide evidence against all scholarly deficits.

Only mark the three newly spoken, independently decoded source rectangles as
supported. Do not remove any mathematical, publisher figure label, script
phoneme, or all-visual-elements requirements without its own full evidence.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .figure_source_identity import require,_sha
from .original_three_section_academic_remaining_inventory import (
    audit,EXPECTED)
from .original_thomas86_all41_thirtyeight_joined_qa import NEW_STATUS
from .original_thomas85_86_multipart_qa_preview import _media_seconds

STATUS="UPDATED_ORIGINAL_THOMAS_41_38_SPOKEN_FOCUS_SCHOLARLY_GAPS_NONPRODUCTION"
PROVED_NEW=("8.6_slide6","8.6_slide11","8.6_slide12")
TITLES=("8.4_slide1","8.5_slide1","8.6_slide1")

def merge_new_real_source_receipt(*,old:dict,proof:dict)->dict:
    require(old["original_source_slides"]==41
            and old["original_source_pixel_and_audio_math_focus_slides"]==35
            and old["student_publication_authorized"] is False
            and old["full_original_production_gate_passed"] is False,
            "Historical source academic inventory must remain fail-closed")
    require(proof["status"]==NEW_STATUS
            and proof["original_source_slides_across_three_sections"]==41
            and proof["original_source_spoken_focus_slides_across_three_sections"]==38
            and proof["new_actual_8_6_joined_original_slide_samples"]==13
            and proof["new_actual_8_6_joined_spoken_element_samples"]==21
            and proof["total_distinct_source_spoken_element_samples_across_three_sections"]==47
            and proof["student_publication_authorized"] is False,
            "New publisher-original audio focus evidence incomplete or misrepresented")
    require(proof["original_8_6_twelve_spoken_focus_slides"]==list(range(2,14))
            and len(proof["actual_source_slide_pixel_qa"])==13
            and len(proof["actual_original_spoken_highlight_pixel_qa"])==21,
            "Final joined §8.6 physical source-pixel and acoustic evidence missing")
    records=old["detailed_original_slide_acceptance_deficits"]
    for key in PROVED_NEW:
        require(not records[key]["actual_original_source_source_spoken_focus_scene_present"]
                and records[key]["publisher_scientific_topic_or_example_source_verified"]
                if key!="8.6_slide11" else
                not records[key]["actual_original_source_source_spoken_focus_scene_present"]
                and any(x.get("publisher_figure_science_identity_verified")
                        for x in records[key]["actual_author_image_files"]),
                f"Cannot promote {key} without original publisher science identity")
        item=records[key]
        require(item["source_math_audio_focus_required"] is True
                and item["presentation_title_only_no_math_focus_required"] is False
                and "NO_PUBLISHER_MATCHED_SOURCE_WAV_PIXEL_FOCUS_CLIP"
                   in item["remaining_source_academic_requirements"],
                "Cannot promote title or already-approved focus as newly spoken")
        item["actual_original_source_source_spoken_focus_scene_present"]=True
        item["remaining_source_academic_requirements"]=[
            x for x in item["remaining_source_academic_requirements"]
            if x!="NO_PUBLISHER_MATCHED_SOURCE_WAV_PIXEL_FOCUS_CLIP"]
        item["remaining_source_academic_requirements"].append(
            "ONE_OR_MORE_SCENE_FOCUSES_PASS_BUT_ALL_VISUAL_ELEMENTS_NOT_CERTIFIED")
        item["new_original_speech_acoustic_and_pdf_pixel_witness_verifiable"]=True
        item["original_mathematical_figure_semantic_and_word_coverage_complete"]=False
    for key in TITLES:
        require(records[key]["presentation_title_only_no_math_focus_required"] is True
                and not records[key]["actual_original_source_source_spoken_focus_scene_present"],
                "Pure Beamer title must remain unhighlighted without math exemption bypass")
    actual_focus=sorted(key for key,x in records.items()
                        if x["actual_original_source_source_spoken_focus_scene_present"])
    remaining=sorted(key for key,x in records.items()
                     if x["source_math_audio_focus_required"]
                     and not x["actual_original_source_source_spoken_focus_scene_present"])
    require(len(actual_focus)==38 and remaining==[]
            and len(records)==41 and all(
                not item["original_mathematical_figure_semantic_and_word_coverage_complete"]
                for item in records.values()),
            "Original academic deficit register incorrectly promotes unsourced math/figure elements")
    images=[(key,img) for key,rec in records.items()
            for img in rec["actual_author_image_files"]]
    output={
        **old,
        "status":STATUS,
        "original_source_pixel_and_audio_math_focus_slides":38,
        "original_slides_without_any_verified_focus":3,
        "original_structural_title_only_slides":list(TITLES),
        "original_substantive_slides_without_approved_source_spoken_focus":remaining,
        "true_original_spoken_element_samples_total":47,
        "historical_35_sample_manifest_retained_read_only":True,
        "new_source_math_audio_pixel_witness_original_slide_keys":list(PROVED_NEW),
        "actual_source_verified_spoken_original_slide_keys":actual_focus,
        "source_images_inventory_total":len(images),
        "source_images_not_yet_certified_in_inventory":sum(
            not img["publisher_figure_science_identity_verified"] for _,img in images),
        "original_all_math_equation_and_figure_label_checks_complete":False,
        "all_original_audio_tts_pronunciation_checks_complete":False,
        "full_original_production_gate_passed":False,
        "student_publication_authorized":False,
        "next_priority":(
            "Independently verify EVERY remaining unproven equation symbol and "
            "source figure label/graph line/axis, and original WAV pronunciation "
            "consistency across all 38 substantive slides. The 47 accepted "
            "real focus samples are not complete elementwise scholarly approval. "
            "Then test the strict Windows release gate. Regenerated live 20/17 "
            "slide lectures require separate academic and media acceptance."),
    }
    # The 8.6 source bibliography remains identical, only sample coverage changed.
    output["original_sections"]["8.6"]["at_least_one_verified_source_focus_slide_count"]=12
    output["original_sections"]["8.6"]["original_slides_without_verified_focus"]=[1]
    require(sum(x["at_least_one_verified_source_focus_slide_count"]
                for x in output["original_sections"].values())==38,
            "Original source per-section focus count incompatible with new proof")
    return output

def audit_current(*,root:Path,checkpoint:Path,new_video_dir:Path)->dict:
    require(new_video_dir.is_dir() and not new_video_dir.is_symlink()
            and not new_video_dir.is_relative_to(root),
            "Independent previous source media outputs absent")
    p=new_video_dir/"ALL41_38_SOURCE_SPOKEN_JOINED_INDEPENDENT_QA.json"
    require(p.is_file() and not p.is_symlink(),
            "No source-bound final joined 38 scene video receipt")
    witness=json.loads(p.read_text("utf8"))
    for part in witness.get("source_8_6_actual_joined_H264_parts",[]):
        path=new_video_dir/(
            f"THOMAS_8.6_38_FOCUS_SOURCE_QA_part{part['part']:02d}.mp4")
        require(path.is_file() and not path.is_symlink()
                and part["mp4_sha256"]==_sha(path)
                and abs(part["real_encoded_seconds"]-_media_seconds(path))<.02
                and part["real_encoded_seconds"]<600,
                "Publisher original 38-spoken-focus final video SHA/duration unverified")
    require(len(witness["source_8_6_actual_joined_H264_parts"])==2,
            "Expected two physical source §8.6 encoded video parts")
    historical=audit(root=root,checkpoint=checkpoint)
    return merge_new_real_source_receipt(old=historical,proof=witness)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("root","checkpoint","new-video-dir","out"):
        p.add_argument("--"+n,type=Path,required=True)
    a=p.parse_args(argv)
    require(a.out.parent.is_dir() and not a.out.exists(),
            "Create only NEW versioned original academic source deficit evidence")
    result=audit_current(root=a.root,checkpoint=a.checkpoint,
                         new_video_dir=a.new_video_dir)
    with a.out.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False)
        f.write("\n")
    print(json.dumps({
        "status":STATUS,
        "original_source_slides":41,
        "verified_spoken_highlight_slides":38,
        "real_source_word_timed_event_samples":47,
        "academic_math_figure_all_elements_approved":False,
        "substantive_unfocused_slides":
            result["original_substantive_slides_without_approved_source_spoken_focus"],
        "student_publication_authorized":False,
    }))

if __name__=="__main__":
    main()
