"""Carry independent model ASR evidence across strictly visual-only plan rebinding.

This does not transcribe new audio, fabricate missing transcripts or certify
word-level fidelity. Strictly copies existing model ASR clips with unchanged
WAV SHA-256 and spoken-text SHA-256 into a *new* job bound to the exact
layout-only authored plan. Preserves incomplete ASR status and provenance.
"""
from __future__ import annotations
import argparse,hashlib,json,shutil
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""):h.update(b)
    return h.hexdigest()

def need(ok,msg):
    if not ok: raise ValueError(msg)

def load(p): return json.loads(Path(p).read_text(encoding="utf8"))

def write_new(p,value):
    with Path(p).open("x",encoding="utf8") as stream:
        json.dump(value,stream,indent=2,ensure_ascii=False)
        stream.write("\n")

def migrate(*,original_plan:Path,rebound_plan:Path,original_asr:Path,
            audio:Path,layout_receipt:Path,out:Path)->dict:
    original_plan,rebound_plan,original_asr,audio,layout_receipt,out=map(
        lambda p:Path(p).resolve(),
        (original_plan,rebound_plan,original_asr,audio,layout_receipt,out))
    need(original_plan.is_file() and rebound_plan.is_file()
         and original_asr.is_dir() and audio.is_dir()
         and layout_receipt.is_file() and not out.exists()
         and out.parent.is_dir(),"Missing source data or output already exists")
    need(not out.is_relative_to(original_asr) and
         not out.is_relative_to(audio) and
         out!=original_plan.parent,
         "Output must be outside original audio/ASR/plan directories")
    old=load(original_plan);new=load(rebound_plan)
    receipt=load(layout_receipt)
    job=load(original_asr/"asr_job.json")
    need(old["status"]==new["status"]=="author_specified_unapproved_element_narration"
         and new["layout_only_rebind_from_voice_plan_sha256"]==sha(original_plan)
         and receipt["old_voice_bound_plan_sha256"]==sha(original_plan)
         and receipt["new_slides_sha256"]==new["slides_sha256"]
         and new["layout_only_rebind_receipt_sha256"]==receipt["figure_resize_receipt_sha256"]
         and receipt["source_sha256"]==new["source_sha256"]==old["source_sha256"]
         and receipt["all_original_wav_bytes_and_text_hashes_verified"] is True
         and receipt["academic_approval"] is False
         and receipt["production_approved"] is False,
         "Not an independently documented visual-only rebind")
    expected=dict(old)
    expected["slides_sha256"]=new["slides_sha256"]
    expected["layout_only_rebind_from_voice_plan_sha256"]=sha(original_plan)
    expected["layout_only_rebind_receipt_sha256"]=new["layout_only_rebind_receipt_sha256"]
    need(expected==new,"New authored plan changed narration or source semantics")
    scenes=[el for p in new["parts"] for s in p["slides"] for el in s["elements"]]
    need(job["plan_sha256"]==sha(original_plan)
         and job["model"] in ("gemini-3.1-flash-lite","gemini-3.5-flash")
         and job["source_model"]=="gemini-3.8-flash-lite-tts"
         and job["clips"]==[el["wav"] for el in scenes],
         "Original ASR job is not bound to original exact narration plan")
    rows=[]
    for item in scenes:
        name=item["wav"]
        wav=audio/name
        need(wav.is_file() and not wav.is_symlink(),"Missing or unsafe audio clip")
        r=original_asr/(name+".asr.json")
        if not r.exists(): continue
        x=load(r)
        txt=hashlib.sha256(item["spoken_text"].encode("utf8")).hexdigest()
        need(x["wav"]==name and x["wav_sha256"]==sha(wav)
             and x["reference_sha256"]==txt
             and x["asr_model"]==job["model"]
             and x["transcript_sha256"]==
                 hashlib.sha256(x["transcript"].encode("utf8")).hexdigest()
             and x["audible_word_fidelity_certified"] is False,
             "Stale or fabricated original ASR transcript detected")
        rows.append((name,x))
    out.mkdir()
    new_job=dict(job)
    new_job["plan_sha256"]=sha(rebound_plan)
    new_job["layout_only_carryover_original_asr_job_sha256"]=sha(original_asr/"asr_job.json")
    new_job["status"]="independent_model_asr_review_only"
    # Keep job canonical to the generic independent_speech_audit format:
    # additional provenance is stored in a separate migration receipt.
    del new_job["layout_only_carryover_original_asr_job_sha256"]
    write_new(out/"asr_job.json",new_job)
    for name,row in rows:
        write_new(out/(name+".asr.json"),row)
    summary={
        "status":"PARTIAL_ASR_REVIEW_ONLY_LAYOUT_CARRYOVER",
        "old_plan_sha256":sha(original_plan),
        "new_plan_sha256":sha(rebound_plan),
        "original_asr_job_sha256":sha(original_asr/"asr_job.json"),
        "layout_receipt_sha256":sha(layout_receipt),
        "model":job["model"],
        "total_clips":len(scenes),
        "previously_machine_transcribed":len(rows),
        "unverified_clips":len(scenes)-len(rows),
        "independent_model_not_independent_vendor":True,
        "no_new_transcription_created":True,
        "human_word_fidelity_certified":False,
        "production_approved":False}
    write_new(out/"layout_carryover_receipt.json",summary)
    return summary

def main():
    p=argparse.ArgumentParser()
    for arg in ("original-plan","rebound-plan","original-asr","audio",
                "layout-receipt","out"):
        p.add_argument("--"+arg,required=True,type=Path)
    args={k.replace("-","_"):v for k,v in vars(p.parse_args()).items()}
    print(json.dumps(migrate(**args),indent=2))
if __name__=="__main__":main()
