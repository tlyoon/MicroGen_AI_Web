"""Real-source 16-historical-WAV, 29-PDF-block acoustic sample planner.

This uses *only* original recorded PCM, exact original PDF geometry and
crosschecked unapproved candidate receipts.  It is a review plan, NEVER
source mathematics approval, completed highlighting or student publication.
"""
from __future__ import annotations
import argparse
import json
import wave
from pathlib import Path
import pymupdf

from .element_plan_autodraft import file_hash
from .original_thomas84_semantic_mapping_review import EXPECTED_SOURCE_SHA, require
from .original_thomas84_pdf_math_risk import physical_matches

STEM="REVIEW_ONLY_REAL_SOURCE_16_WAV_29_PDF_CANDIDATE_SAMPLE_PLAN"

def sample_windows(total:int, proposals:list[dict], rate:int=24000)->list[dict]:
    """Exact non-overlap sample partition; no estimated or even speech bins."""
    require(type(total) is int and total>0 and rate==24000, "Real 24kHz source PCM needed")
    proposals=sorted(proposals,key=lambda x:(x["begin_s"],x["end_s"]))
    timeline=[]
    cursor=0
    prev=None
    for p in proposals:
        begin=round(p["begin_s"]*rate); finish=round(p["end_s"]*rate)
        require(0<=cursor<=begin<finish<=total, "Missing/overlapping measured acoustic words")
        if begin>cursor:
            # Fill true silence/unmapped speech with static source-slide visual.
            timeline.append({"first_pcm_sample":cursor,"last_pcm_sample_exclusive":begin,
                             "provisional_pdf_target":None,"sentence_index":None})
        timeline.append({"first_pcm_sample":begin,"last_pcm_sample_exclusive":finish,
                         "provisional_pdf_target":p["pdf_target"],
                         "sentence_index":p["sentence_index"]})
        cursor=finish
    if cursor<total:
        timeline.append({"first_pcm_sample":cursor,"last_pcm_sample_exclusive":total,
                         "provisional_pdf_target":None,"sentence_index":None})
    if not timeline:
        timeline=[{"first_pcm_sample":0,"last_pcm_sample_exclusive":total,
                   "provisional_pdf_target":None,"sentence_index":None}]
    # Merge tiny (<0.17 s) unmapped intervals into their neighbor, with an
    # explicit provenance marker; never delete or duplicate samples.
    compact=[]
    for segment in timeline:
        frames=segment["last_pcm_sample_exclusive"]-segment["first_pcm_sample"]
        if compact and segment["provisional_pdf_target"] is None and frames<4080:
            compact[-1]["last_pcm_sample_exclusive"]=segment["last_pcm_sample_exclusive"]
            compact[-1]["includes_unmapped_tail_samples"]=True
        else:
            compact.append(dict(segment))
    # A tiny leading interval is kept static. Encoding may later require a
    # safe visual timing merge; never pretend it is semantically aligned.
    require(compact[0]["first_pcm_sample"]==0
            and compact[-1]["last_pcm_sample_exclusive"]==total
            and all(x["first_pcm_sample"] < x["last_pcm_sample_exclusive"]
                    for x in compact)
            and all(a["last_pcm_sample_exclusive"]==b["first_pcm_sample"]
                    for a,b in zip(compact,compact[1:])),
            "Source PCM real-sample coverage wrong")
    return compact

def build_plan(*,original:Path,candidates:Path,physical:Path,math:Path,out:Path)->dict:
    root=Path(original).resolve()
    cpath=Path(candidates).resolve(); ppath=Path(physical).resolve()
    mpath=Path(math).resolve();target=Path(out).absolute()
    require(root.is_dir() and all(p.is_file() and not p.is_symlink()
        for p in (cpath,ppath,mpath)) and target.parent.is_dir()
        and not target.exists() and not target.is_relative_to(root.parent),
        "Source missing or review plan would overwrite protected originals")
    original_pdf=root/"source.pdf"
    require(file_hash(original_pdf)==EXPECTED_SOURCE_SHA,"Textbook identity changed")
    c=json.loads(cpath.read_text(encoding="utf8"))
    p=json.loads(ppath.read_text(encoding="utf8"))
    m=json.loads(mpath.read_text(encoding="utf8"))
    require(c.get("status")=="REAL_SOURCE_PDF_ACOUSTIC_VISUAL_WORKLIST_NOT_SEMANTICALLY_APPROVED"
        and p.get("status")=="PHYSICALLY_REVERIFIED_PDF_TARGETS_SEMANTICALLY_UNAPPROVED"
        and m.get("status")=="ORIGINAL_SOURCE_DOMAIN_TRIG_CONFLICT_SCAN_UNAPPROVED"
        and c.get("student_publication_authorized") is False
        and p.get("student_publication_authorized") is False
        and m.get("student_publication_authorized") is False
        and p.get("candidate_receipt_sha256")==file_hash(cpath)
        and m.get("pr336_physical_receipt_sha256")==file_hash(ppath)
        and len(p["candidates"])==len(m["candidates"])==29,
        "Missing chain-of-evidence for real original PDF candidates")
    physical_map={(x["slide"],x["sentence_index"]):x for x in p["candidates"]}
    math_map={(x["slide"],x["sentence_index"]):x for x in m["candidates"]}
    require(len(physical_map)==len(math_map)==29,"Duplicate source target assignments")
    output=[]
    count=0
    in_order=[x for x in range(1,18) if x!=4]
    require([x.get("slide") for x in c["slides"]]==in_order,
            "Missing original historic slide")
    with pymupdf.open(root/"slides.pdf") as pdf:
        require(len(pdf)==17,"Actual slides.pdf not 17 slides")
        for slide in c["slides"]:
            n=slide["slide"]
            audio=root/f"slide{n}.wav"
            require(file_hash(audio)==slide["source_wav_sha256"],
                    "Protected original audio content changed")
            with wave.open(str(audio),"rb") as wav:
                require(wav.getnchannels()==1 and wav.getsampwidth()==2
                        and wav.getframerate()==24000
                        and wav.getcomptype()=="NONE",
                        "Wrong original WAV format")
                frames=wav.getnframes()
                sourcepcm=wav.readframes(frames)
                require(len(sourcepcm)==frames*2,"Truncated genuine PCM source")
            proposed=[]
            for seg in slide["candidate_segments"]:
                if not seg["unique_target_review_priority"]:
                    continue
                key=(n,seg["sentence_index"])
                row=physical_map[key]; rule=math_map[key]
                require(row["physical_pdf_geometry_and_text_verified"] is True
                    and row["semantic_math_approved"] is False
                    and row["release_highlight_allowed"] is False
                    and not rule["provable_local_term_conflicts"]
                    and rule["whole_source_math_verified"] is False
                    and seg["eligible_for_final_student_highlight"] is False
                    and seg["speech_to_visible_math_semantics_approved"] is False,
                    "Contradictory source-math or misrepresented approval")
                visual=seg["candidate_targets"][0]
                require(visual["original_pdf_element_id"]==row["element_id"]
                    and row["element_id"]==rule["original_pdf_element_id"]
                    and physical_matches(pdf[n-1],visual)
                    and seg["actual_recorded_word_start_second"] is not None,
                    "Nonphysical original-PDF/acoustic highlight")
                proposed.append({
                    "begin_s":seg["actual_recorded_word_start_second"],
                    "end_s":seg["actual_recorded_word_end_second"],
                    "sentence_index":seg["sentence_index"],
                    "pdf_target":visual["original_pdf_element_id"]})
            rows=sample_windows(frames,proposed)
            count+=len(proposed)
            output.append({"slide":n,"original_pcm_sha256":slide["source_wav_sha256"],
                "original_pcm_total_samples":frames,
                "real_acoustic_pdf_highlight_hypotheses":len(proposed),
                "sample_exact_timeline":rows,
                "full_element_semantics_approved":False})
    require(count==29 and len(output)==16 and
            file_hash(original_pdf)==EXPECTED_SOURCE_SHA,
            "Actual 29 mapped hypotheses/inventory/source preservation failed")
    result={"schema_version":1,"status":STEM,
        "source_pdf_sha256":EXPECTED_SOURCE_SHA,
        "original_slides_pdf_sha256":file_hash(root/"slides.pdf"),
        "source_candidate_receipt_sha256":file_hash(cpath),
        "physical_pdf_audit_sha256":file_hash(ppath),
        "math_conflict_audit_sha256":file_hash(mpath),
        "historical_original_slides_planned":16,
        "actual_source_pdf_acoustic_candidates":count,
        "source_pcm_sample_coverage_verified":True,
        "unmapped_spoken_elements_remain":True,
        "full_lecture_semantics_approved":False,
        "student_publication_authorized":False,"paid_requests":0,
        "historical_slides":output}
    with target.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    return result

def main():
    ap=argparse.ArgumentParser()
    for x in ("original","candidates","physical","math","out"):
        ap.add_argument("--"+x,required=True,type=Path)
    d=vars(ap.parse_args())
    r=build_plan(**d)
    print(json.dumps({k:v for k,v in r.items()
        if k!="historical_slides"},indent=2))
if __name__=="__main__":main()
