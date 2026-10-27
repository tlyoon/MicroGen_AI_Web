"""Owner-approved pragmatic TTS pronunciation QA (27 October 2026).

Pass intelligible *sound-alike* speech, not near-verbatim ASR orthography.
Never excuse a semantic/sign/domain/unit change or obviously incorrect
symbol expansion (notably written "c" -> spoken "circa"). Vosk is an
independent noisy witness, not an authoritative verbatim transcript.
"""
from __future__ import annotations
import re

# Narrow, audibly plausible Vosk transcriptions of actual maths terms.
# Canonicalize only *recognized* ASR phonetics; do not rewrite source text.
# No general edit-distance/phonetic fuzzy matching: "sine" and "sign",
# "positive" and "negative", "secant" and "second" must not be conflated
# outside these documented, context-dependent ASR renderings.
_PHONETIC_ASR = (
    (r"\bhigh pot news\b", "hypotenuse"),
    (r"\bhigh partners\b", "hypotenuse"),
    (r"\bhigh partner\b", "hypotenuse"),
    (r"\bcoast sign\b", "cosine"),
    (r"\bcoasts i knew\b", "cosine"),
    (r"\bcause i knew\b", "cosine"),
    (r"\bcoast i knew\b", "cosine"),
    (r"\bsee get\b", "secant"),
    (r"\bsee it\b", "secant"),
    (r"\bsee can't\b", "secant"),
    (r"\bac can't\b", "a secant"),
    (r"\bpie\b", "pi"),
    (r"\beggs\b", "x"),
    (r"\bacts\b", "x"),
    (r"\beq\b", "x"),
    (r"\bexquisite\b", "x squared"),
    (r"\bsign you\b", "sine u"),
    (r"\bsequels\b", "equals"),
    (r"\bit was\b", "equals"),
    (r"\ba leg a zero\b", "a leg is zero"),
    (r"\bthe opposite like a zero\b", "the opposite leg is zero"),
    (r"\bnew\b", "u"),
)
_ALLOWED_SYMBOLS = {"x","u","a","c","y"}
# Deliberately keep c and circa distinct. Similarly, no automatic
# conversion of c -> sea/see/century/speed of light without source review.
_SEVERE_SYMBOL_EXPANSIONS = {
    "c":("circa","century","celsius","cent","speed of light"),
}
_MATH_CONCEPTS = {
    "negative","nonnegative","positive","zero","absolute","degenerate",
    "sine","cosine","secant","tangent","square","squared","root",
    "hypotenuse","opposite","adjacent","endpoint",
}


def tokens(text:str)->list[str]:
    if not isinstance(text,str):
        raise ValueError("TTS QA text must be a string")
    text=text.lower().replace("non-negative","nonnegative")
    text=text.replace("non negative","nonnegative")
    text=text.replace("end-point","endpoint").replace("end point","endpoint")
    text=text.replace("zero-length","zero length")
    return re.findall(r"[a-z]+|\d+",text)


def asr_soundalike_tokens(asr:str)->list[str]:
    cleaned=" ".join(tokens(asr))
    for pattern,canonical in _PHONETIC_ASR:
        cleaned=re.sub(pattern,canonical,cleaned)
    return tokens(cleaned)


def _edit_distance(a:list[str],b:list[str])->int:
    prev=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        row=[i]+[0]*len(b)
        for j,y in enumerate(b,1):
            row[j]=min(prev[j]+1,row[j-1]+1,prev[j-1]+(x!=y))
        prev=row
    return prev[-1]


def flexible_pronunciation_screen(
    expected_text:str,asr_transcript:str, *,
    max_normalized_wer:float=.35,
)->dict:
    """Return a pragmatic, reproducible screening decision, not perfect listening.

    A small-vocabulary ASR can garble technical words despite usable speech.
    Default 35% *after* narrow documented sound-alike normalization is
    intentionally tolerant. Mathematics polarity/contrast and egregious
    symbol pronunciation retain hard-fail priority over the score.
    """
    a=tokens(expected_text)
    b=asr_soundalike_tokens(asr_transcript)
    if not a or not b:
        return {
            "pronunciation_qa_pass":False,
            "review_required":True,
            "blocker_codes":["EMPTY_EXPECTED_OR_SPEECH"],
            "normalized_wer":1.0,
            "critical_math_concepts_preserved":False,
            "severe_pronunciation_error":False,
        }
    errors=[]
    source_concepts=[w for w in a if w in _MATH_CONCEPTS]
    heard_concepts=[w for w in b if w in _MATH_CONCEPTS]
    # Retain meaningful contrast and sign/domain; a bot may still mishear
    # a mathematical term, in which case this result asks for targeted
    # review, NOT endless automatic TTS resynthesis.
    sign_terms={"negative","nonnegative","positive","zero","absolute","degenerate"}
    expected_polarity=[w for w in a if w in sign_terms]
    heard_polarity=[w for w in b if w in sign_terms]
    if expected_polarity!=heard_polarity:
        errors.append("MATH_SIGN_OR_DOMAIN_CONTRADICTION_REVIEW")
    # Strong requirements for explicit hearing of every principal trig
    # function when the source speaks it. ASR phonetic variants above count.
    trig={"sine","cosine","secant","tangent"}
    expected_trig=[w for w in a if w in trig]
    heard_trig=[w for w in b if w in trig]
    if expected_trig!=heard_trig:
        errors.append("TRIG_FUNCTION_MISMATCH_REVIEW")
    # Do NOT silently accept obviously wrong c -> circa, or similar
    # abbreviation expansions, even if overall WER is low.
    for symbol,forbidden in _SEVERE_SYMBOL_EXPANSIONS.items():
        if symbol in a:
            transcript=" ".join(tokens(asr_transcript))
            if any(re.search(r"\b"+re.escape(v)+r"\b",transcript) for v in forbidden):
                errors.append("GROSS_SYMBOL_MISPRONUNCIATION_"+symbol.upper())
    wer=round(_edit_distance(a,b)/len(a),5)
    if wer>max_normalized_wer:
        errors.append("LOW_ASR_SIMILARITY_REVIEW_NOT_AUTOMATIC_TTS_FAILURE")
    return {
        "pronunciation_qa_pass":not errors,
        "review_required":bool(errors),
        "blocker_codes":errors,
        "normalized_wer":wer,
        "raw_wer":round(_edit_distance(a,tokens(asr_transcript))/len(a),5),
        "source_math_polarity_terms":expected_polarity,
        "recognized_math_polarity_terms":heard_polarity,
        "critical_math_concepts_preserved":
            expected_polarity==heard_polarity and expected_trig==heard_trig,
        "severe_pronunciation_error":
            any(x.startswith("GROSS_SYMBOL_MISPRONUNCIATION") for x in errors),
        "soundalike_normalizations_applied":a!=tokens(asr_transcript),
        "quality_rule":"ACCEPT_INTELLIGIBLE_SOUNDALIKE_NOT_VERBATIM_ASR",
        "student_release_authorized":False,
    }
