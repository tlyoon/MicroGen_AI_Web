"""Read-only original 41-slide academic acceptance deficit registry.

The existence of an original WAV, an image, a screen pixel sample, a timed
border or a source text label does not prove that every mathematical term
and every figure detail matches the publisher. Enumerate remaining distinct
needs while preserving the finite REAL successes already witnessed.
Never unlock student publication from an inventory or sample count.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
import pymupdf
from .figure_source_identity import require,_sha
from .original_thomas84_multipart_qa_preview import HIGHLIGHTS
from .original_thomas85_86_multipart_qa_preview import FOCUS,SOURCE
from .original_thomas_all41_independent_joined_qa import STATUS as INDEPENDENT_STATUS
from .original_thomas86_tank_ex62_source_provenance import verify_tank_publisher_source

EXPECTED={"8.4":17,"8.5":11,"8.6":13}
STATUS="READ_ONLY_SOURCE_AUDIO_MATH_FIGURE_41_SLIDE_DEFICIT_INVENTORY_NONPRODUCTION"


def _slides(tex:str)->list[str]:
    parts=re.findall(r"\\begin\{frame\}.*?\\end\{frame\}",tex,re.S)
    require(len(parts)>0,"Original authored frames not detected")
    return parts


def require_pinned_original_section_version(*,section:str,frame_count:int,
                                            publisher_sha:str,slides_pdf_sha:str)->None:
    """Reject mismatched live/regenerated author slides without losing why.

    A publisher PDF may still be identical while the authored lecture has been
    regenerated. Count and PDF SHA are distinct mandatory checks. Never treat
    a new live lecture as the original accepted 41-slide frozen source corpus.
    """
    require(section in EXPECTED,"Unknown publisher-original section")
    problems=[]
    if frame_count!=EXPECTED[section]:
        problems.append(f"FRAME_COUNT expected={EXPECTED[section]} actual={frame_count}")
    if section in SOURCE:
        expected=SOURCE[section]
        if publisher_sha!=expected["publisher_sha"]:
            problems.append(f"PUBLISHER_SHA expected={expected['publisher_sha']} actual={publisher_sha}")
        if slides_pdf_sha!=expected["slides_pdf_sha"]:
            problems.append(f"AUTHOR_PDF_SHA expected={expected['slides_pdf_sha']} actual={slides_pdf_sha}")
    require(not problems,
            f"PINNED_ORIGINAL_SOURCE_SNAPSHOT_MISMATCH section={section}: "
            +"; ".join(problems)
            +". Preserve both versions; do not mutate live source or unlock publication.")


def audit(*,root:Path,checkpoint:Path)->dict:
    root,checkpoint=Path(root).absolute(),Path(checkpoint).absolute()
    require(root.is_dir() and not root.is_symlink(),
            "Physical original publisher root missing")
    prior=checkpoint/"20261101_PR437_INDEPENDENT_ALL41_35_FOCUS_QA"/(
        "INDEPENDENT_ALL41_ORIGINAL_MP4_FRAME_PIXEL_QA.json")
    require(prior.is_file() and not prior.is_symlink(),
            "No independently encoded original source math/figure/audio witness")
    witness=json.loads(prior.read_text(encoding="utf8"))
    require(witness["status"]==INDEPENDENT_STATUS
            and witness["actually_decoded_original_slide_samples_total"]==41
            and witness["actually_decoded_source_proven_highlight_samples_total"]==35
            and witness["student_publication_authorized"] is False
            and witness["all_math_and_figures_elementwise_scientifically_accepted"] is False,
            "Existing source/audio/video pixel facts not independently proven")
    records={}
    sources={}
    for sec,count in EXPECTED.items():
        folder=root/sec
        paths=[folder/n for n in ("source.pdf","slides.tex","slides.pdf","script.txt")]
        paths.extend(folder/f"slide{i}.wav" for i in range(1,count+1))
        require(all(p.is_file() and not p.is_symlink() for p in paths),
                f"Original source, narration, or PCM missing: {sec}")
        before={str(p):_sha(p) for p in paths}
        frames=_slides((folder/"slides.tex").read_text(encoding="utf8"))
        require_pinned_original_section_version(
            section=sec,frame_count=len(frames),
            publisher_sha=_sha(folder/"source.pdf"),
            slides_pdf_sha=_sha(folder/"slides.pdf"))
        tank_source_proof=(verify_tank_publisher_source(folder=folder)
                           if sec=="8.6" else None)
        seen=set(HIGHLIGHTS if sec=="8.4" else FOCUS[sec])
        require(all(1<=i<=count for i in seen),
                f"Audio mathematical events cite invalid source slide in {sec}")
        with pymupdf.open(folder/"source.pdf") as publisher,pymupdf.open(folder/"slides.pdf") as pages:
            require(len(pages)==count and len(publisher)>0,
                    "Original academic authored PDF count is invalid")
            all_book_text="\n".join(p.get_text() for p in publisher)
            for slide,frame in enumerate(frames,1):
                imgs=re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]*)\}",frame)
                graphics=[]
                for name in imgs:
                    image=folder/name
                    require(image.is_file() and not image.is_symlink(),
                            f"Actual author referenced image missing: {image}")
                    graphics.append({"source_file":name,"sha256":_sha(image),
                        "physically_present_in_author_directory":True,
                        "rendered_pdf_has_images":bool(pages[slide-1].get_images(full=True)),
                        "publisher_figure_science_identity_verified":bool(
                            tank_source_proof and slide==11 and name=="Exercise 62.png")})
                # Count _occurrences_ in author equations as an inventory
                # measure, NOT an independently verified scientific claim.
                latex_equation_env=len(re.findall(r"\\\[|\\begin\{(?:align|equation|gather)",frame))
                math_commands=len(re.findall(
                    r"\\(?:frac|int|ln|tan|sin|cos|sqrt|sum|lim|neq|leq|geq|pm|cdot)\b",
                    frame))
                items=len(re.findall(r"\\item\b",frame))
                source_issue=[]
                if not (slide in seen):
                    source_issue.append("NO_PUBLISHER_MATCHED_SOURCE_WAV_PIXEL_FOCUS_CLIP")
                if items>1:
                    source_issue.append("NOT_ALL_INDIVIDUAL_BULLET_REGIONS_SOURCE_AND_WORD_TIMED")
                if math_commands or latex_equation_env:
                    source_issue.append("FULL_EQUIVALENCE_OF_EACH_INTERMEDIATE_MATH_TOKEN_NOT_PROVEN")
                if graphics:
                    source_issue.append("ORIGINAL_FIGURE_PANEL_LABEL_GRAPH_SCIENCE_NOT_FULLY_VERIFIED")
                if sec=="8.6" and slide==11:
                    require(any(x["source_file"]=="Exercise 62.png" for x in graphics)
                            and "Tank Inventory" in frame
                            and bool(pages[slide-1].get_images(full=True)),
                            "Tank rendering changed; correct image identity not proven")
                    require(tank_source_proof is not None
                            and tank_source_proof["publisher_original_exercise_source_text_verified"]
                            and tank_source_proof["author_source_image_same_publisher_visual_verified"],
                            "Publisher-original tank Exercise62 source and author PNG unproven")
                    source_issue.append(
                        "EXERCISE62_PUBLISHER_FIGURE_MATH_PROVEN_BUT_PER_ELEMENT_WORD_TIMING_PENDING")
                if slide in seen:
                    source_issue.append(
                        "ONE_OR_MORE_SCENE_FOCUSES_PASS_BUT_ALL_VISUAL_ELEMENTS_NOT_CERTIFIED")
                if not source_issue:
                    source_issue.append(
                        "SOURCE_CORRESPONDENCE_AND_PER_ELEMENT_UTTERANCE_UNPROVEN")
                records[f"{sec}_slide{slide}"]={
                    "section":sec,"slide":slide,
                    "author_slide_page_raster_source_sha256":_sha(folder/"slides.pdf"),
                    "publisher_original_source_sha256":_sha(folder/"source.pdf"),
                    "original_slide_wav_sha256":_sha(folder/f"slide{slide}.wav"),
                    "actual_original_source_source_spoken_focus_scene_present":slide in seen,
                    "actual_original_pdf_image_count":len(pages[slide-1].get_images(full=True)),
                    "actual_author_image_files":graphics,
                    "author_source_item_count":items,
                    "author_equation_environment_count":latex_equation_env,
                    "author_math_command_occurrence_count":math_commands,
                    "original_mathematical_figure_semantic_and_word_coverage_complete":False,
                    "remaining_source_academic_requirements":source_issue,
                }
        require({str(p):_sha(p) for p in paths}==before,
                "Original textbook/author source or original WAV was modified")
        sources[sec]={"publisher_source_pdf_sha256":_sha(folder/"source.pdf"),
            "original_author_slides_sha256":_sha(folder/"slides.pdf"),
            "slide_count":count,
            "at_least_one_verified_source_focus_slide_count":len(seen),
            "original_slides_without_verified_focus":[i for i in range(1,count+1)
                                                      if i not in seen]}
    require(len(records)==41 and sum(len(set(HIGHLIGHTS if k=="8.4" else FOCUS[k]))
                                    for k in EXPECTED)==35,
            "Publisher sections independently validated source focus count drifted")
    result={"status":STATUS,"original_source_slides":41,
            "original_source_pixel_and_audio_math_focus_slides":35,
            "original_slides_without_any_verified_focus":6,
            "original_sections":sources,
            "publisher_original_tank_exercise62_source_figure_math_verified":True,
            "tank_figures_per_element_word_timing_complete":False,
            "detailed_original_slide_acceptance_deficits":records,
            "author_math_command_counts_are_inventory_only":True,
            "no_exhaustive_academic_math_or_figure_element_approval":True,
            "full_original_production_gate_passed":False,
            "student_publication_authorized":False,
            "next_priority":(
                "Cover the source and real WAV semantics of each unverified visible "
                "region; verify all original author formulas and all publisher figure "
                "panel labels/graph coordinates; Exercise62 publisher visual source is proven, but its individual narration/label synchronization remains unverified. "
                "Then independently rerender and repeat all-section production gate."),
          }
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("root","checkpoint","out"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args(argv)
    path=a.out.absolute()
    require(path.parent.is_dir() and not path.exists() and not path.is_symlink(),
            "Academic deficit inventory must be a new versioned output")
    report=audit(root=a.root,checkpoint=a.checkpoint)
    with path.open("x",encoding="utf8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps({"status":STATUS,"original_slides":41,
                      "verified_spoken_focus_slides":35,
                      "remaining_no_focus_slides":6,
                      "source_figures":sum(len(r["actual_author_image_files"])
                          for r in report["detailed_original_slide_acceptance_deficits"].values()),
                      "tank_original_source_identity_approved":report[
                          "publisher_original_tank_exercise62_source_figure_math_verified"],
                      "student_publication_authorized":False}))
if __name__=="__main__":
    main()
