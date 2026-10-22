"""Independent original-verbatim and fixed primary Kore model handoff inspection."""
import hashlib,math
from pathlib import Path
from .figure_source_identity import _sha
MODEL="gemini-3.8-flash-lite-tts"
VOICE="Kore"
def audit_nonbilled_kore_handoff(*,folder:Path,report:dict)->dict:
    f=Path(folder)
    if (type(report) is not dict or
        report.get("status")!="AI_SOURCE_CITED_VERBATIM_KORE_TTS_HANDOFF_NOT_DISPATCHED" or
        report.get("paid_TTS_request_made") is not False or
        report.get("production_release_allowed") is not False or
        report.get("student_publication_authorized") is not False or
        report.get("primary_model")!=MODEL or report.get("primary_voice")!=VOICE):
        raise ValueError("Only undispatched original-verbatim Kore jobs permitted")
    for name,key in (("source.pdf","source_sha256"),("slides.pdf","slides_sha256"),
                     ("script.txt","script_sha256")):
        p=f/name
        if not p.is_file() or p.is_symlink() or _sha(p)!=report.get(key):
            raise ValueError("Original source attachment has drifted")
    total=report.get("narration_total")
    jobs=report.get("actual_verbatim_jobs")
    unresolved=report.get("unresolved_utterance_ids")
    if (type(total) is not int or total<1 or
        type(jobs) is not list or type(unresolved) is not list or
        report.get("AI_source_agreed_segments")!=len(jobs) or
        report.get("unresolved_source_segments")!=len(unresolved) or
        len(jobs)+len(unresolved)!=total):
        raise ValueError("Original narration segment coverage incomplete")
    seen=set()
    for j in jobs:
        if type(j) is not dict or j.get("model")!=MODEL or j.get("voice")!=VOICE:
            raise ValueError("Inconsistent primary Kore voice/model")
        uid=j.get("job_id");txt=j.get("spoken_text")
        bbox=j.get("target_pdf_page_bbox_pt")
        if (type(uid) is not str or not uid or uid in seen or
            type(txt) is not str or not txt.strip() or
            hashlib.sha256(txt.encode("utf8")).hexdigest()!=j.get("spoken_text_sha256")
            or type(bbox) is not list or len(bbox)!=4 or
            any(type(v) not in (float,int) or not math.isfinite(v) for v in bbox)
            or not (bbox[2]>bbox[0] and bbox[3]>bbox[1])):
            raise ValueError("TTS text/hash/slide geometry provenance is insufficient")
        seen.add(uid)
    if any(type(uid) is not str or uid in seen for uid in unresolved) or len(set(unresolved))!=len(unresolved):
        raise ValueError("Unresolved source units overlap actual TTS jobs")
    return {"status":"NONBILLED_KORE_SOURCE_HANDOFF_RECHECKED",
        "total_original_utterances":total,"source_math_agreed_jobs":len(jobs),
        "unresolved_review":len(unresolved),"actual_pcm_wav_count":0,
        "speech_fidelity_verified":False,"student_publication_authorized":False}
