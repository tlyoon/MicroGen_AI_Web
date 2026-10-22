"""Classify hash-verified quarantined Gemini JSON without scientific promotion."""
from pathlib import Path
from .gemini_response_recovery import read_quarantined_response
from .series_gemini import decode_storyboard_response
def classify_raw_review_json(*,raw_file:Path,expected_utterance_ids:list[str])->dict:
    if (type(expected_utterance_ids) is not list or not expected_utterance_ids
        or any(type(x) is not str or not x for x in expected_utterance_ids)
        or len(expected_utterance_ids)!=len(set(expected_utterance_ids))):
        raise ValueError("Original utterance scope must be exact and nonempty")
    raw=read_quarantined_response(raw_file)
    try:
        parsed=decode_storyboard_response(raw)
    except (RuntimeError,ValueError):
        return {"status":"UNTRUSTED_INCOMPLETE_OR_NONJSON","mathematically_approved":False}
    rows=parsed.get("rows")
    if (parsed.get("status")!="ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE"
        or type(rows) is not list or len(rows)!=len(expected_utterance_ids)
        or [r.get("utterance_id") if type(r) is dict else None for r in rows]!=expected_utterance_ids):
        return {"status":"UNTRUSTED_JSON_WRONG_ORIGINAL_SCOPE","mathematically_approved":False}
    return {"status":"UNTRUSTED_STRUCTURED_CANDIDATE_NEEDS_PDF_MATH_VERIFICATION",
        "candidate_utterances":len(rows),
        "mathematically_approved":False,"student_publication_authorized":False}
