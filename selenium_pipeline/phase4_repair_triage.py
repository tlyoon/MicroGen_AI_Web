"""Review-only selective TTS correction plan; never regenerates on mere ASR uncertainty.

Fails closed if quality evidence changed, rechecks WAVs and ASR transcripts.
Only demonstrable audio-integrity defects can become auto-repair *candidates*.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from .tts_quality_gate import screen,digest

def make(*,plan:Path,audio:Path,quality:Path,out:Path,asr_dir:Path|None=None)->dict:
    plan,audio,quality,out=(Path(x).resolve()
                            for x in (plan,audio,quality,out))
    if (not quality.is_file() or out.exists() or not out.parent.is_dir()
            or out.is_relative_to(audio)):
        raise ValueError("Unsafe or missing input/output repair triage")
    saved=json.loads(quality.read_text(encoding="utf8"))
    verified=screen(plan=plan,audio=audio,asr_dir=asr_dir,output=None)
    if verified!=saved:
        raise ValueError("Quality report stale, tampered, or bound to other recordings")
    decisions=[]
    for row in verified["clips"]:
        acoustic_bad=row["acoustics"]["technical_flags"]
        math_problem=("mathematical_spoken_token_discrepancy" in row["review_flags"])
        if acoustic_bad:
            state="technical_audio_defect_regeneration_candidate"
        elif math_problem or row["asr_status"]=="transcript_mismatch":
            state="listening_and_mathematical_review_required"
        elif row["asr_status"]=="pending_independent_asr":
            state="await_independent_transcription_no_regeneration"
        elif row["review_flags"]:
            state="perceptual_listening_review_required"
        else:
            state="machine_consistent_not_human_approved"
        decisions.append({"wav":row["wav"],
             "wav_sha256":row["wav_sha256"],
             "state":state,
             "technical_flags":acoustic_bad,
             "review_flags":row["review_flags"],
             "automatic_regeneration_executed":False,
             "human_listening_approved":False})
    report={"status":"REPAIR_TRIAGE_REVIEW_ONLY",
         "source_qa_sha256":digest(quality),
         "source_plan_sha256":digest(plan),
         "narration_segment_count":len(decisions),
         "technical_regeneration_candidates":sum(x["state"]==
             "technical_audio_defect_regeneration_candidate" for x in decisions),
         "mathematical_or_transcript_reviews":sum(x["state"]==
             "listening_and_mathematical_review_required" for x in decisions),
         "pending_independent_transcription":sum(x["state"]==
             "await_independent_transcription_no_regeneration" for x in decisions),
         "regeneration_executed":False,
         "speech_approval":False,"academic_approval":False,
         "student_publication":False,"decisions":decisions}
    with out.open("x",encoding="utf8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False);f.write("\n")
    return report

def main():
    p=argparse.ArgumentParser()
    for name in ("plan","audio","quality","output"):
        p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--asr-dir",type=Path)
    args=p.parse_args()
    result=make(plan=args.plan,audio=args.audio,quality=args.quality,
                out=args.output,asr_dir=args.asr_dir)
    print(json.dumps({k:v for k,v in result.items() if k!="decisions"},indent=2))
if __name__=="__main__":main()
