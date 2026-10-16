"""Create a private auditable speech listening packet; no approval implied."""
from __future__ import annotations
import argparse,csv,html,json,re,shutil
from pathlib import Path
from .offline_speech_audit import model_digest
from .independent_speech_audit import sha

def require(condition,message):
    if not condition:raise ValueError(message)

def generate(*,plan:Path,recordings:Path,asr:Path,destination:Path,
             include_wavs:bool=True)->dict:
    plan,recordings,asr,destination=(Path(x).resolve()
        for x in (plan,recordings,asr,destination))
    require(plan.is_file() and recordings.is_dir() and asr.is_dir(),
        "Frozen plan, source WAV folder and recognition folder required")
    require(not destination.exists() and destination.parent.is_dir(),
        "Review handoff must use a new output folder")
    require(not destination.is_relative_to(recordings)
       and not destination.is_relative_to(asr),
       "Review packet must not overwrite recording or recognition evidence")
    p=json.loads(plan.read_text(encoding="utf8"))
    job=json.loads((asr/"asr_job.json").read_text(encoding="utf8"))
    require(job["plan_sha256"]==sha(plan.read_bytes()),
        "Review packet plan changed since recognition")
    scenes=[(part["part_id"],scene["slide"],n,el)
            for part in p["parts"] for scene in part["slides"]
            for n,el in enumerate(scene["elements"],1)]
    require([x[3]["wav"] for x in scenes]==job["clips"],
        "Scene order and recognition job mismatch")
    rows=[]
    for part,slide,number,el in scenes:
        wav=el["wav"]
        require(re.fullmatch(r"[A-Za-z0-9_.-]+\.wav",wav) is not None,
            "Unsafe path in scene manifest")
        original=recordings/wav
        require(original.is_file() and not original.is_symlink(),
            "Missing original narration recording")
        receipt=asr/(wav+".asr.json")
        transcript=json.loads(receipt.read_text(encoding="utf8")) if receipt.is_file() else None
        if transcript:
            require(transcript["wav_sha256"]==sha(original.read_bytes())
                and transcript["reference_sha256"]==
                    sha(el["spoken_text"].encode("utf8"))
                and transcript["asr_model"]==job["model"]
                and transcript["transcript_sha256"]==
                    sha(transcript["transcript"].encode("utf8")),
                "Stale or tampered speech recognition receipt")
            if job.get("backend")=="offline_faster_whisper":
                require(transcript["model_sha256"]==job["model_sha256"],
                    "Model weights changed")
        rows.append({"part":part,"slide":slide,"element":number,"wav":wav,
            "expected":el["spoken_text"],"recognized":transcript["transcript"]
                if transcript else "",
            "wer":transcript["metrics"]["wer"] if transcript else "",
            "status":transcript["status"] if transcript else "not_transcribed",
            "reviewer_decision":"","reviewer_comments":""})
    destination.mkdir()
    shutil.copy2(plan,destination/"authored_narration_plan.json")
    shutil.copy2(asr/"asr_job.json",destination/"asr_job.json")
    if (asr/"asr_summary.json").exists():
        shutil.copy2(asr/"asr_summary.json",destination/"asr_summary.json")
    (destination/"recognition_receipts").mkdir()
    if include_wavs:(destination/"audio").mkdir()
    for row in rows:
        file=asr/(row["wav"]+".asr.json")
        if file.exists():
            shutil.copy2(file,destination/"recognition_receipts"/file.name)
        if include_wavs:
            target=destination/"audio"/row["wav"]
            shutil.copy2(recordings/row["wav"],target)
            require(sha(target.read_bytes())==sha((recordings/row["wav"]).read_bytes()),
                "Copied listening audio differs")
    with (destination/"lecturer_review_checklist.csv").open("x",newline="",encoding="utf-8-sig") as f:
        columns=list(rows[0])
        writer=csv.DictWriter(f,fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    def H(s):return html.escape(str(s),quote=True)
    ordered=sorted(rows,key=lambda r:(r["status"]!="speech_review_required",
        r["status"]=="machine_asr_consistent_not_certified",
        r["slide"],r["element"]))
    snippets=[]
    for row in ordered:
        flagged=row["status"]!="machine_asr_consistent_not_certified"
        tone="flag" if flagged else "pass"
        player=(f'<audio controls preload="none" src="audio/{H(row["wav"])}"></audio>'
                if include_wavs else "")
        snippets.append(f'''<section class="{tone}">
          <h3>{H(row["part"])} · slide {int(row["slide"])} · element {int(row["element"])}
              <span>{H(row["status"])}</span></h3>
          <p><b>Word-error rate:</b> {H(row["wer"])} · <b>WAV:</b> {H(row["wav"])}</p>
          {player}
          <p><b>Original requested narration</b></p><blockquote>{H(row["expected"])}</blockquote>
          <p><b>Independent machine transcript</b></p><blockquote>{H(row["recognized"]) or "[Not available]"}</blockquote>
          <p><b>Lecturer decision:</b> Not reviewed · <b>Academic certification:</b> None</p>
        </section>''')
    n=sum(x["status"]=="machine_asr_consistent_not_certified" for x in rows)
    k=sum(x["status"]=="speech_review_required" for x in rows)
    missing=len(rows)-n-k
    contents=('''<!doctype html><html lang="en"><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Private MicroGen speech listening review</title>
    <style>body{font:16px/1.5 system-ui,Arial;max-width:920px;margin:25px auto;padding:0 18px}
    section{border:1px solid #d5d8dc;border-radius:8px;padding:14px;margin:16px 0}
    section.flag{border-left:7px solid #bb6716}
    section.pass{border-left:7px solid #26703b}
    blockquote{margin:8px 0;padding:10px;background:#f5f6f7;border-radius:5px}
    audio{width:100%}h3 span{font-size:13px;margin-left:10px}
    .notice{font-weight:bold}</style>
    <h1>MicroGen_AI_Web — private narration listening review</h1>
    <p class="notice">NOT HUMAN VERIFIED · NOT ACADEMICALLY APPROVED · NOT FOR STUDENT PUBLICATION.</p>
    <p>Independent model: '''+H(job["model"])+''' · source narrator: Gemini Kore.
    A machine transcript mismatch may be a recognition error rather than a
    narration defect. Listen and compare every segment.</p>
    <p>Segments: '''+str(len(rows))+''' · machine-consistent: '''+str(n)+'''
    · flagged: '''+str(k)+''' · not transcribed: '''+str(missing)+'''</p>
    <p>Review flagged segments first; the attached checklist lets the lecturer
    record decisions independently. Model weight hash: '''+
    H(job.get("model_sha256","not available"))+'''</p>'''+''.join(snippets)+'''</html>''')
    (destination/"index.html").write_text(contents,encoding="utf8")
    overview={
        "status":"PRIVATE_HUMAN_REVIEW_REQUIRED_NOT_APPROVED",
        "plan_sha256":sha(plan.read_bytes()),"asr_model":job["model"],
        "asr_model_sha256":job.get("model_sha256"),
        "total":len(rows),"machine_consistent":n,"flagged":k,
        "untranscribed":missing,
        "human_listening_approval":False,"academic_approval":False,
        "student_published":False}
    (destination/"review_packet_receipt.json").write_text(json.dumps(
        overview,indent=2)+"\n",encoding="utf8")
    return overview

def main():
    p=argparse.ArgumentParser()
    for name in ("plan","recordings","asr","destination"):
        p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--omit-audio",action="store_true")
    a=p.parse_args()
    print(json.dumps(generate(plan=a.plan,recordings=a.recordings,
        asr=a.asr,destination=a.destination,
        include_wavs=not a.omit_audio),indent=2))
if __name__=="__main__":main()
