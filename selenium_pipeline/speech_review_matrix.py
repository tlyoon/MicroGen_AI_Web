"""Plain-language per-segment listening review matrix from real ASR receipts.

Does not infer word accuracy or fill missing transcriptions. Outputs an
academic/listening review handoff; student publication remains disabled.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,re
from pathlib import Path

def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1048576),b""):h.update(chunk)
    return h.hexdigest()

def build(*,plan:Path,asr:Path,audio:Path,out_csv:Path,out_json:Path)->dict:
    plan,asr,audio,out_csv,out_json=map(lambda p:Path(p).resolve(),
        (plan,asr,audio,out_csv,out_json))
    if not plan.is_file() or not asr.is_dir() or not audio.is_dir():
        raise ValueError("Missing plan, ASR directory or audio")
    if out_csv.exists() or out_json.exists() or not out_csv.parent.is_dir() or not out_json.parent.is_dir():
        raise ValueError("Both review output paths must be new")
    job=json.loads((asr/"asr_job.json").read_text(encoding="utf8"))
    expected=json.loads(plan.read_text(encoding="utf8"))
    if job["plan_sha256"]!=sha(plan):
        raise ValueError("ASR evidence bound to a different exact plan")
    segments=[(s["slide"],el) for part in expected["parts"]
              for s in part["slides"] for el in s["elements"]]
    if job["clips"]!=[el["wav"] for _,el in segments]:
        raise ValueError("Speech segments differ from independently checked ASR job")
    rows=[]
    for slide,el in segments:
        name=el["wav"]
        if not re.fullmatch(r"[a-zA-Z0-9_.-]+\.wav",name):
            raise ValueError("Unsafe source WAV filename")
        wav=audio/name
        if not wav.is_file() or wav.is_symlink():
            raise ValueError("Source narration WAV missing")
        receipt=asr/(name+".asr.json")
        status="pending_independent_asr"
        wer=None
        transcript=""
        if receipt.is_file():
            info=json.loads(receipt.read_text(encoding="utf8"))
            refhash=hashlib.sha256(el["spoken_text"].encode("utf8")).hexdigest()
            transcripthash=hashlib.sha256(info["transcript"].encode("utf8")).hexdigest()
            if (info["wav"]!=name or info["wav_sha256"]!=sha(wav)
                 or info["reference_sha256"]!=refhash
                 or info["transcript_sha256"]!=transcripthash
                 or info["asr_model"]!=job["model"]):
                raise ValueError("Stale/changed ASR transcript in review matrix")
            wer=info["metrics"]["wer"]
            transcript=info["transcript"]
            status="asr_consistent_not_human_verified" if info["metrics"]["machine_asr_consistent"] else "asr_mismatch_needs_listening"
        rows.append({
            "slide":slide,"wav":name,
            "status":status,
            "asr_wer":wer,
            "intended_spoken_script":el["spoken_text"],
            "model_heard_transcript":transcript,
            "human_listening_approved":False,
            "mathematical_source_approved":False})
    headers=list(rows[0])
    with out_csv.open("x",encoding="utf-8-sig",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    summary={
        "status":"ACADEMIC_AND_SPEECH_REVIEW_NOT_COMPLETED",
        "total":len(rows),
        "consistent_not_certified":sum(x["status"]=="asr_consistent_not_human_verified" for x in rows),
        "flagged":sum(x["status"]=="asr_mismatch_needs_listening" for x in rows),
        "pending":sum(x["status"]=="pending_independent_asr" for x in rows),
        "flagged_clip_ids":[x["wav"] for x in rows if x["status"]=="asr_mismatch_needs_listening"],
        "asr_job_sha256":sha(asr/"asr_job.json"),
        "plan_sha256":sha(plan),
        "human_listening_approved":False,
        "academic_approved":False,"production_approved":False,
        "all_segments":rows}
    with out_json.open("x",encoding="utf8") as f:
        json.dump(summary,f,indent=2,ensure_ascii=False);f.write("\n")
    return {k:v for k,v in summary.items() if k!="all_segments"}

def main():
    p=argparse.ArgumentParser()
    for k in ("plan","asr","audio","out-csv","out-json"):
        p.add_argument("--"+k,required=True,type=Path)
    args={k.replace("-","_"):v for k,v in vars(p.parse_args()).items()}
    print(json.dumps(build(**args),indent=2))
if __name__=="__main__": main()
