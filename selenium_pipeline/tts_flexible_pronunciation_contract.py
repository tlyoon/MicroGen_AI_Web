"""Owner-approved flexible TTS acoustic/phonetic QA contract (27 Oct 2026).

PASS when the delivered speech is recognizably similar to the source script;
do NOT demand verbatim ASR, strict WER <=0.20, accent identity, or perfect
recognition of mathematical vocabulary. ASR is imperfect evidence, not a
transcript oracle. A low-confidence recording is a targeted spot-check, NOT
grounds for regenerating otherwise reasonable audio.

Important distinct constraints:
- A LETTER "c" audibly delivered as the WORD "circa" is a HARD FAIL, not
  a harmless sound-alike.
- An explicitly reversed mathematical sign, inequality direction, domain
  negation or false formula is a HARD FAIL when observable.
- Unintelligible/unrelated content needs a spot check, not an automatic pass.
- File/PCM/source/TTS provenance, independent source mathematics, actual
  utterance timing, <600-second encoded video and release remain separate.

This contract does NOT independently certify voice Kore, spoken words,
academic correctness or student publication, and uses no network calls.
"""
from __future__ import annotations

from difflib import SequenceMatcher
import re

QA_VERSION="TTS_PHONETIC_SIMILARITY_V2_20261027"
# Only stable, already witnessed (or conventional) orthographic renderings of
# the SAME spoken sound; never map distinct mathematical meanings.
_PHONETIC_PHRASES=(
    ("coasts i knew","cosine u"),
    ("coast sign you","cosine u"),
    ("coasts sign you","cosine u"),
    ("cause i knew","cosine u"),
    ("coast sign","cosine"),
    ("coasts sign","cosine"),
    ("high pot news","hypotenuse"),
    ("high partners","hypotenuse"),
    ("high pot new","hypotenuse"),
    ("see can't you","secant u"),
    ("see get you","secant u"),
    ("see it you","secant u"),
    ("see can't","secant"),
    ("see get","secant"),
    ("see it","secant"),
    ("act sequels","x equals"),
    ("acts sequels","x equals"),
    ("x it was","x equals"),
    ("exquisite","x squared"),
    ("pi over to","pi over two"),
    ("pie over to","pi over two"),
    ("it was a","equals a"),
)

_MATH_CRITICAL=frozenset((
    "positive","nonnegative","negative","nonpositive","absolute","zero",
    "degenerate","nondegenerate","secant","sine","cosine","tangent",
    "hypotenuse","opposite","adjacent","pi","plus","minus","least","most",
))
_SIGN_WORDS=frozenset((
    "positive","nonnegative","negative","nonpositive","plus","minus",
    "nondegenerate","degenerate",
))
_TRIG_WORDS=frozenset(("sine","cosine","secant","tangent"))
_GEOMETRY_WORDS=frozenset(("hypotenuse","adjacent","opposite"))
_NUMBER_WORDS=frozenset((
    "zero","one","two","three","four","five","six","seven","eight","nine",
    "ten","eleven","twelve","thirteen","fourteen","fifteen","sixteen",
    "seventeen","eighteen","nineteen","twenty",
))
_SINGLE_DIGIT_WORDS={
    "0":"zero","1":"one","2":"two","3":"three","4":"four","5":"five",
    "6":"six","7":"seven","8":"eight","9":"nine",
}
_MATH_PHRASE_CONTRADICTIONS=(
    ("at least","at most"),
    ("at most","at least"),
    ("less than","greater than"),
    ("greater than","less than"),
    ("increases","decreases"),
    ("decreases","increases"),
    ("plus","minus"),
    ("minus","plus"),
    ("positive","negative"),
    ("negative","positive"),
    ("nonnegative","negative"),
    ("negative","nonnegative"),
    ("nonpositive","positive"),
    ("positive","nonpositive"),
    ("degenerate","nondegenerate"),
    ("nondegenerate","degenerate"),
)


def _tokens(text:str)->list[str]:
    if not isinstance(text,str):
        raise ValueError("TTS reference/recognition must be textual")
    value=text.casefold().replace("π"," pi ").replace("θ"," theta ")
    value=value.replace("non-negative","nonnegative")
    value=value.replace("non negative","nonnegative")
    value=value.replace("non-positive","nonpositive")
    value=value.replace("non positive","nonpositive")
    value=value.replace("non-degenerate","nondegenerate")
    value=value.replace("non degenerate","nondegenerate")
    value=value.replace("end-point","endpoint").replace("end point","endpoint")
    value=value.replace("zero-length","zero length")
    value=value.replace("pi/2","pi over two")
    tokens=re.findall(r"[a-z]+|\d+",value)
    return [_SINGLE_DIGIT_WORDS.get(t,t) for t in tokens]


def canonical_phonetic_tokens(reference:str,recognized:str)->tuple[list[str],list[str]]:
    """Only reference-context-safe approximations, not semantic substitutions."""
    original=_tokens(reference)
    heard=_tokens(recognized)
    recorded=" ".join(heard)
    for src,dst in _PHONETIC_PHRASES:
        recorded=re.sub(r"(?<!\w)"+re.escape(src)+r"(?!\w)",dst,recorded)
    heard=recorded.split()
    expected=set(original)
    # Isolated algebraic letters are often transcribed as ordinary sounds:
    # "x"/"eggs", "u"/"you", "pi"/"pie", "c"/"see".
    one_word_alternatives={
        "x":("eggs","acts","ex","ax","eq"),
        "u":("you","new"),
        "pi":("pie",),
        "c":("see","sea"),
        "sine":("sign",),
        "for":("four",),
        "two":("to",),
    }
    # Do NOT generalize to 'circa' or collapse positive with negative.
    mapping={}
    for exact,sounds in one_word_alternatives.items():
        if exact in expected:
            for sound in sounds:
                if sound not in expected:
                    mapping[sound]=exact
    heard=[mapping.get(w,w) for w in heard]
    # Ordinary inflection is not a pronunciation defect.
    for singular,plural in (
        ("side","sides"),("leg","legs"),("length","lengths"),
        ("identity","identities"),("radical","radicals"),
        ("value","values"),("angle","angles"),("equals","equal"),
    ):
        if singular in expected and plural not in expected:
            heard=[singular if w==plural else w for w in heard]
        if plural in expected and singular not in expected:
            heard=[plural if w==singular else w for w in heard]
    return original,heard


def _explicit_critical_contradictions(
    source_tokens:list[str], heard_tokens:list[str]
)->list[str]:
    """Detect substantiated wrong *direction*, not mere ASR omissions."""
    reasons=[]
    original=" ".join(source_tokens)
    recognized=" ".join(heard_tokens)
    # The user explicitly requires that letter 'c' not be pronounced "circa".
    # "see" / "sea" are ordinary acceptable spellings of spoken letter C.
    if "c" in source_tokens and "circa" in heard_tokens and "circa" not in source_tokens:
        reasons.append("LETTER_C_INCORRECTLY_EXPANDED_TO_CIRCA")
    # Exact sequence of critical math polarities after safe normalization.
    exp=[w for w in source_tokens if w in _SIGN_WORDS]
    got=[w for w in heard_tokens if w in _SIGN_WORDS]
    if exp and got and len(exp)==len(got) and exp!=got:
        reasons.append("EXPLICIT_MATHEMATICAL_SIGN_OR_DEGENERACY_REVERSAL")
    # Swapping specific numbers, scientific trig functions, or geometric
    # roles is not harmless phonetic variation when ASR explicitly captures a
    # different well-formed mathematical term sequence.
    for vocab,code in (
        (_TRIG_WORDS,"EXPLICIT_TRIGONOMETRIC_FUNCTION_CHANGED"),
        (_GEOMETRY_WORDS,"EXPLICIT_TRIANGLE_SIDE_ROLE_CHANGED"),
        (_NUMBER_WORDS,"EXPLICIT_SPOKEN_NUMBER_CHANGED"),
    ):
        expected=[t for t in source_tokens if t in vocab]
        heard=[t for t in heard_tokens if t in vocab]
        if expected and heard and len(expected)==len(heard) and expected!=heard:
            reasons.append(code)
    # Phrases with mutually exclusive meanings should not be normalized to
    # homophones. Compare only when the direction is actually in ASR.
    for correct,wrong in _MATH_PHRASE_CONTRADICTIONS:
        if " " not in correct or " " not in wrong:
            continue  # individual signs above are handled in aligned order
        if re.search(r"\b"+re.escape(correct)+r"\b",original):
            if re.search(r"\b"+re.escape(wrong)+r"\b",recognized) and not re.search(
                r"\b"+re.escape(correct)+r"\b",recognized
            ):
                reasons.append("EXPLICIT_MATHEMATICAL_RELATION_DIRECTION_CHANGED")
                break
    return sorted(set(reasons))


def evaluate_tts_soundalike(
    expected_text:str, asr_text:str, *,
    source_audio_is_genuine_pcm:bool=True,
    source_text_identity_verified:bool=True,
)->dict:
    """Adaptive intelligibility screen, not a byte-for-byte dictation exam.

    PASS / PASS_WITH_MINOR_VARIATIONS let WAV advance through TTS-quality
    screening; REVIEW_UNCLEAR_AUDIO asks for a targeted check; FAIL_CONFIRMED
    prevents known severe wrong pronunciations or inverted mathematical facts.
    Regardless, source/voice/content/publication certifications remain separate.
    """
    ref,heard=canonical_phonetic_tokens(expected_text,asr_text)
    if not ref:
        raise ValueError("Empty original-source narration cannot be approved")
    similarity=round(
        SequenceMatcher(None,ref,heard,autojunk=False).ratio(),5
    ) if heard else 0.0
    expected_critical={w for w in ref if w in _MATH_CRITICAL}
    heard_critical={w for w in heard if w in _MATH_CRITICAL}
    math_recall=(round(len(expected_critical & heard_critical)/
                       len(expected_critical),4)
                 if expected_critical else 1.0)
    severe=_explicit_critical_contradictions(ref,heard)
    if not source_audio_is_genuine_pcm or not source_text_identity_verified:
        decision="FAIL_INVALID_AUDIO_OR_SOURCE"
        severe.append("MISSING_GENUINE_SOURCE_REGISTERED_PCM_EVIDENCE")
    elif severe:
        decision="FAIL_CONFIRMED_CRITICAL_PRONUNCIATION"
    elif not heard or similarity<.50:
        decision="REVIEW_UNCLEAR_AUDIO"
    elif similarity>=.67:
        decision="PASS_SIMILAR_SOUND"
    else:
        decision="PASS_WITH_MINOR_VARIATIONS"
    return {
        "contract_version":QA_VERSION,
        "tts_qa_decision":decision,
        "tts_qa_soundalike_pass":decision in (
            "PASS_SIMILAR_SOUND","PASS_WITH_MINOR_VARIATIONS"),
        "phonetic_token_similarity":similarity,
        "canonical_reference_token_count":len(ref),
        "canonical_asr_token_count":len(heard),
        "recognized_math_concept_fraction":math_recall,
        "recognized_math_terms_advisory_only":True,
        "exact_ASR_word_error_rate_hard_threshold":False,
        "minor_accent_phonetic_word_spacing_variations_allowed":True,
        "critical_errors":severe,
        "automatic_regeneration_solely_due_to_ASR_WER_forbidden":True,
        "same_voice_Kore_independently_certified":False,
        "independent_source_academic_review_approved":False,
        "video_speech_to_source_elements_verified_by_this_check":False,
        "student_publication_authorized_by_this_check":False,
    }
