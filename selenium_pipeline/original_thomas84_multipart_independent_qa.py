"""Independent actual decoded-frame QA for NON-PRODUCTION full §8.4 MP4 preview.

Checks all 17 actual joined-video slide displays against the corrected
PDF raster, and independently samples 5 source-verifiable highlight events
inside the joined parts (not just the preconcat individual source clips).
Figure axis ticks and 12 unmapped slides remain UNAPPROVED by contract.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import pymupdf
from PIL import Image,ImageChops,ImageStat

from .figure_source_identity import require,_sha
from .original_math_sync_video_verify import count_yellow_border
from .original_thomas84_slide4_three_equation_sync import count_source_equation_side_border
from .original_thomas84_multipart_qa_preview import (
    _duration,HIGHLIGHTS,source_highlights)

def _reference_slide(pdf:Path,i:int)->Image.Image:
    with pymupdf.open(pdf) as doc:
        pix=doc[i-1].get_pixmap(matrix=pymupdf.Matrix(2,2),alpha=False)
        real=Image.frombytes("RGB",(pix.width,pix.height),pix.samples)
        # The source FFmpeg video pipeline normalizes H.264 frames to even
        # dimensions, 726x545 => 726x544, with the same bilinear scaling.
        return real.resize((real.width//2*2,real.height//2*2),
                           Image.Resampling.BILINEAR)

def _decoded(part:Path,seconds:float,out:Path)->Image.Image:
    from .video_ffmpeg import ffmpeg_executable
    require(not out.exists(),"Never overwrite source-proof decoded scene")
    r=subprocess.run([ffmpeg_executable(),"-hide_banner","-loglevel","error",
        "-i",str(part),"-ss",f"{seconds:.4f}","-frames:v","1",str(out)],
        capture_output=True,text=True,timeout=45)
    require(r.returncode==0 and out.is_file(),"Unable to independently decode joined MP4")
    return Image.open(out).convert("RGB")

def check(*,original:Path,corrected:Path,checkpoint:Path,
          out:Path,qa_dir:Path)->dict:
    original,corrected,checkpoint,out=[Path(x).absolute() for x in
                                      (original,corrected,checkpoint,out)]
    qa_dir=Path(qa_dir).absolute()
    require(qa_dir.is_dir() and not qa_dir.is_symlink()
            and qa_dir!=out and not qa_dir.is_relative_to(out),
            "Independent decoded frame evidence must use an external exclusive directory")
    report=out/"MULTIPART_SOURCE_CORRECTED_QA_NOT_FOR_STUDENTS.json"
    require(report.is_file() and not report.is_symlink(),
            "No real source-corrected multipart video manifest")
    manifest=json.loads(report.read_text(encoding="utf8"))
    require(manifest["status"]==
            "FULL_17_SLIDE_TWO_PART_SOURCE_CORRECTED_QA_PREVIEW_NOT_PRODUCTION"
            and manifest["source_slide_count"]==17
            and manifest["source_verified_element_highlight_slide_numbers"]
               ==sorted(HIGHLIGHTS)
            and manifest["full_academic_and_element_highlight_acceptance"] is False
            and manifest["student_publication_authorized"] is False
            and manifest["original_source_sha256"]==_sha(original/"source.pdf")
            and manifest["corrected_academic_pdf_sha256"]==
                _sha(corrected/"slides.pdf"),
            "Original source identities or QA nonpublication contract invalid")
    verified=[]
    highlighted=[]
    encountered=[]
    for part in manifest["parts"]:
        file=Path(part["mp4_path"])
        require(file.parent==out and _sha(file)==part["mp4_sha256"]
                and _duration(file)<600 and part["is_production_accepted"] is False,
                "Joined original lecture MP4 changed or exceeds 600 seconds")
        elapsed=0.
        offsets={}
        for i in part["source_slide_numbers"]:
            component=(checkpoint/HIGHLIGHTS[i][0]/HIGHLIGHTS[i][1]
                       if i in HIGHLIGHTS else
                       out/f"original_source_slide{i:02d}_NO_ELEMENT_APPROVAL.mp4")
            require(component.is_file() and not component.is_symlink(),
                    "Missing actual source slide MP4 source for independent verification")
            offsets[i]=elapsed
            elapsed+=_duration(component)
            encountered.append(i)
            # Guard against rare concat packet timebase drift near transitions
            # by sampling 1.5 sec into each slide, not at a cut boundary.
            second=offsets[i]+min(1.5,_duration(component)*.5)
            frame=qa_dir/f"joined_independent_slide{i:02d}_preview.png"
            observed=_decoded(file,second,frame)
            expected=_reference_slide(corrected/"slides.pdf",i)
            require(observed.size==expected.size,
                    f"Joined slide{i} actual pixels wrong dimensions")
            avg=sum(ImageStat.Stat(ImageChops.difference(
                observed,expected)).mean)/3
            require(avg<12.,
                    f"Joined MP4 original slide{i} wrong scene: avg RGB delta={avg:.2f}")
            verified.append({"original_slide":i,"part":part["part_number"],
                             "joined_time_s":round(second,3),
                             "joined_frame_sha256":_sha(frame),
                             "original_pdf_avg_absolute_rgb_difference":round(avg,3),
                             "correct_original_visual_page_preserved":True})
        # Sample real source-proof highlights from actual JOINED H264 stream.
        for i in part["source_slide_numbers"]:
            if i not in HIGHLIGHTS:
                continue
            if i in (6,17):
                doc=json.loads((checkpoint/"20261101_PR407_CORRECTED_REAL_TIMED_HIGHLIGHTS"/
                                f"corrected_thomas84_slide{i}_real_sync.json").read_text(encoding="utf8"))
                event=doc["source_grounded_visual_event_targets"][-1]
                rect=event["rect_pt"]
                middle=(event["source_bound_speech_start_s"]+
                        event["source_bound_speech_end_s"])/2
            elif i==4:
                doc=json.loads((checkpoint/HIGHLIGHTS[i][0]/
                                "thomas84_slide4_source_synchronized_equations.json").read_text(encoding="utf8"))
                rect=doc["source_grounded_target_rectangles_pt"]["sine"]
                a,b=doc["real_speech_word_anchor_intervals_s"]["sine"]
                middle=(a+b)/2
            elif i==7:
                doc=json.loads((checkpoint/HIGHLIGHTS[i][0]/
                                "thomas84_slide7_inverse_domain_provenance.json").read_text(encoding="utf8"))
                e=doc["real_original_inverse_branch_events"]["two_arcsecant_branches"]
                rect=e["rect_pt"]
                middle=(e["real_audio_start_s"]+e["real_audio_end_s"])/2
            elif i==8:
                doc=json.loads((checkpoint/HIGHLIGHTS[i][0]/
                                "thomas84_slide8_source_procedure_qa.json").read_text(encoding="utf8"))
                rect=doc["original_publisher_corresponding_procedure_steps"]["2"]["rect_pt"]
                a,b=doc["genuine_spoken_procedure_step_intervals_s"]["2"]
                middle=(a+b)/2
            elif i==5:
                doc=json.loads((checkpoint/HIGHLIGHTS[i][0]/
                                "thomas84_slide5_source_math_sync_qa.json").read_text(encoding="utf8"))
                event=doc["original_textbook_chains"][0]
                rect=event["slide_rect_pt"]
                middle=10.
            elif i==9:
                doc=json.loads((checkpoint/HIGHLIGHTS[i][0]/
                                "original_thomas84_slide9_math_sync_qa.json").read_text(encoding="utf8"))
                rect=doc["source_chain_witness"]["rendered_slide_rect_pt"]
                middle=37.
            else:
                doc=json.loads((checkpoint/HIGHLIGHTS[i][0]/
                                "thomas84_slide12_math_sync_provenance.json").read_text(encoding="utf8"))
                rect=doc["original_source_equation_target"]["rendered_slide_rect_pt"]
                middle=25.
            second=offsets[i]+middle
            frame=qa_dir/f"joined_independent_highlight_slide{i:02d}.png"
            _decoded(file,second,frame)
            probes=(count_source_equation_side_border(frame,rect)
                    if i in (4,7,8) else count_yellow_border(frame,rect))
            require(probes>=6,
                    f"JOINED original source slide{i} spoken-element focus missing: {probes}/8")
            highlighted.append({"original_slide":i,
                "part":part["part_number"],"joined_time_s":round(second,3),
                "source_element_yellow_border_probes":probes,
                "correct_source_bound_highlight_pixels_verified":True})
    require(encountered==list(range(1,18))
            and [i["original_slide"] for i in highlighted]==sorted(HIGHLIGHTS),
            "Joined original source slide or mathematical visual focus incomplete")
    result={"status":"INDEPENDENT_17_SLIDE_MULTIPART_ENCODED_FRAME_QA_PASS_NONPRODUCTION",
        "original_source_sha256":manifest["original_source_sha256"],
        "corrected_academic_pdf_sha256":manifest["corrected_academic_pdf_sha256"],
        "joined_part_mp4_sha256":[part["mp4_sha256"] for part in manifest["parts"]],
        "real_joined_source_slide_samples":verified,
        "real_joined_mathematical_highlight_samples":highlighted,
        "source_slide_count_verified":len(verified),
        "source_element_highlight_count_verified":len(highlighted),
        "each_joined_part_strictly_under_600_seconds":True,
        "full_original_course_academic_approval":False,
        "unverified_other_nine_slide_element_mapping":True,
        "student_publication_authorized":False}
    outfile=qa_dir/"INDEPENDENT_MULTIPART_VIDEO_FRAME_VERIFICATION_REVIEW_ONLY.json"
    with outfile.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2)
        f.write("\n")
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for field in ("original","corrected","checkpoint","out","qa-dir"):
        p.add_argument("--"+field,type=Path,required=True)
    a=p.parse_args(argv)
    result=check(original=a.original,corrected=a.corrected,
                 checkpoint=a.checkpoint,out=a.out,qa_dir=a.qa_dir)
    print(json.dumps({"status":result["status"],
        "slides":result["source_slide_count_verified"],
        "combined_highlights":result["source_element_highlight_count_verified"]}))
if __name__=="__main__":
    main()
