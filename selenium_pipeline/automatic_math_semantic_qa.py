"""Reusable, conservative mathematical semantics lint BEFORE every TTS batch.

This is NOT a general theorem prover or independent academic approval.
Hard findings stop TTS, generate source-bound revision instructions, and
retain immutable input hashes. Other math claims remain for independent review.

Avoid silently replacing original teaching files. The caller can request a
verified revision through the bounded math_qa_repair_flow orchestration.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

_BLOCKS=re.compile(r"(?m)^\*\*Slide\s+(\d+)\s+\[[^\]\r\n]+\]:")
_RULE_VERSION="general-semantic-domain-sign-v1"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _chunks(script: str) -> list[tuple[int,str]]:
    if type(script) is not str or not script.strip() or len(script)>1_000_000:
        raise ValueError("Missing or unbounded narration script")
    starts=list(_BLOCKS.finditer(script))
    if not starts:
        return [(1,script.strip())]
    if [int(m.group(1)) for m in starts]!=list(range(1,len(starts)+1)):
        raise ValueError("Narration must contain consecutive slide blocks")
    return [(int(m.group(1)),script[m.end():(starts[i+1].start() if i+1<len(starts) else len(script))].strip().strip("*").strip())
            for i,m in enumerate(starts)]


def _detect(slide: int, body: str) -> list[dict]:
    """Conservative *scientific risk*, not regex-based mathematical judgment."""
    low=re.sub(r"\s+"," ",body.casefold())
    lines=re.split(r"(?<=[.!?])\s+",low)
    found=[]
    def add(rule:str,matched:str,reason:str,repair:str,example:dict|None=None):
        found.append({"slide":slide,"rule":rule,"severity":"blocking",
                      "trigger":matched,"reason":reason,
                      "revision_guidance":repair,
                      "exact_counterexample":example,
                      "academic_semantics_approved":False})
    triangle=bool(re.search(r"\b(triangle|triangles|hypotenuse|adjacent|opposite)\b",low))
    signed=bool(re.search(r"\b(tangent|tan(?:gent)?\s+u|sine|sin(?:e)?\s+u)\b",low))
    # Assess the domain-sensitive assertion locally rather than passing if
    # *another* sentence somewhere mentions a reference angle.
    for sentence in lines:
        if (triangle and signed
                and re.search(r"\bacute angle\s+(?:u|theta|θ)\b",sentence)
                and not re.search(r"\b(reference angle|positive reference angle|only when|provided|restricted to|if)\b",sentence)):
            add("signed_angle_not_always_acute",sentence.strip(),
                "A signed trigonometric substitution may use negative angles; a physical triangle has an unsigned reference angle.",
                "Describe the positive reference angle and show signed-domain counterexamples. State the selected angle interval.",
                {"parameter":"a=2","angle":"u=-pi/4","substitution":"x=a tan(u)","x":"-2"})
        if triangle and signed and re.search(
                r"\bx\s+and\s+a\s+(?:represent|are)\s+the\s+opposite\s+and\s+adjacent\s+(?:legs|sides)\b",sentence):
            add("signed_variable_as_side_length",sentence.strip(),
                "For negative x, the geometric side length is |x|, not x.",
                "Use the absolute value of x as side length and keep signed trig ratios separately.",
                {"parameter":"a=2","angle":"u=-pi/4","substitution":"x=a tan(u)","x":"-2"})
        if (triangle and re.search(r"\bsine\b|\bsin\s+u\b",low)
                and re.search(r"\bx\s+is\s+the\s+opposite\s+(?:leg|side)\b",sentence)):
            add("signed_opposite_sine_length",sentence.strip(),
                "A sine substitution can have x negative; side lengths cannot.",
                "Use side length |x|, and state the principal arcsine domain.",
                {"parameter":"a=2","angle":"u=-pi/6","substitution":"x=a sin(u)","x":"-1"})
        if (triangle and re.search(r"\bsecant\b",low)
                and re.search(r"\bhypotenuse\s+is\s+x\b",sentence)
                and not re.search(r"\b(positive|x\s*(?:at least|>=|greater|positive)|x\s+over\s+a\s+at\s+least)\b",low)):
            add("unsigned_secant_hypotenuse",sentence.strip(),
                "A hypotenuse is nonnegative; x=a sec(u) may have negative x unless the positive branch is declared.",
                "State a>0 and x>=a (or use |x| for a separately justified negative branch).")
        # sqrt(4) = 2 is NOT the sign-sensitive identity sqrt(z²)=|z|.
        # Require an explicitly squared nonconstant expression OR a bounded
        # trigonometric radical-elimination assertion from the same slide.
        squared_variable=bool(re.search(
            r"\b(?:[a-z]|variable|quantity|sine|cosine|secant|tangent|sin|cos|sec|tan)\s+squared\b",
            sentence))
        trig_root_shortcut=bool(
            re.search(r"\b(?:taking|take)\s+the\s+square\s+root\b",sentence)
            and re.search(r"\b(?:eliminates?|removes?)\s+the\s+radical\b",sentence)
            and re.search(r"\b(?:tangent|sine|secant|trigonometr)\b",low))
        if (re.search(r"\b(?:square root|principal root|radical)\b.{0,120}?\b(?:eliminates? the radical|removes? the radical|simplifies? to|equals?)\b",sentence)
                and (squared_variable or trig_root_shortcut)
                and not re.search(r"\b(absolute value|nonnegative|non-negative|on the restricted|positive|domain|provided|assuming)\b",sentence)):
            add("unchecked_principal_root_sign",sentence.strip(),
                "sqrt(z squared) = |z|, not z for arbitrary real z.",
                "Supply the sign/branch domain, write the absolute value, and only simplify when z>=0.")
        if (re.search(r"\b(cancel(?:s|ling|lation|led)?|divide(?:s|d)?(?:\s+both\s+sides)?\s+by)\b",sentence)
                and re.search(r"\b(denominator|factor|variable|x)\b",sentence)
                and not re.search(r"\b(nonzero|non-zero|not zero|excluding zero|x\s*≠\s*0|x\s*!=\s*0)\b",sentence)):
            # Only flag explicit cancellation of a variable/factor; generic
            # "factor two cancels" is not an unsafe domain claim.
            if re.search(r"\b(cancel(?:s|ling|led)?\s+(?:the\s+)?(?:x|variable|common factor)|divide(?:s|d)?\s+(?:both sides\s+)?by\s+x)\b",sentence):
                add("division_by_possible_zero",sentence.strip(),
                    "Cancellation/division of a variable requires a nonzero restriction.",
                    "State and independently check a nonzero denominator condition, or use a case split.")
    return found


def inspect_math_semantics(script: str, *,source_sha256:str|None=None)->dict:
    if source_sha256 is not None and (
            type(source_sha256) is not str
            or re.fullmatch(r"[0-9a-f]{64}",source_sha256) is None):
        raise ValueError("Source hash must be an exact SHA-256")
    chunks=_chunks(script)
    findings=[]
    for slide,body in chunks:
        if not body: raise ValueError("Empty narration block")
        findings.extend(_detect(slide,body))
    # Do not call a script mathematically true just because selected hazards
    # were not recognized. Independent source/math review still required.
    blocking=len(findings)
    return {"schema_version":1,"ruleset":_RULE_VERSION,
            "script_sha256":_sha(script),"source_sha256":source_sha256,
            "slide_count":len(chunks),"blocking_count":blocking,
            "status":("MATH_DOMAIN_REPAIR_REQUIRED" if blocking
                      else "NO_KNOWN_DOMAIN_SIGN_HAZARDS_IN_LIMITED_RULESET"),
            "findings":findings,
            "all_mathematics_verified":False,
            "independent_source_math_ai_review_approved":False,
            "automatic_tts_authorized":False,
            "student_publication_authorized":False}


def repair_prompt(report:dict,*,source_file_name:str="source.pdf")->dict:
    if (type(report) is not dict or report.get("schema_version")!=1
            or report.get("ruleset")!=_RULE_VERSION
            or type(report.get("script_sha256")) is not str):
        raise ValueError("Expected genuine mathematical QA report")
    lines=["Repair only the flagged source-grounded mathematical claims.",
           "Treat original textbook, on-page figure labels and full angle/domain conditions as authoritative evidence.",
           "For signed trigonometric substitutions, distinguish variable signs from unsigned reference triangle side lengths.",
           "Preserve exact slide count and all unaffected sentences and lesson order.",
           "For radicals, prove sqrt(z^2)=|z| and supply nonnegative branch conditions before dropping absolute values.",
           "For division and cancellation, inspect zero/excluded values.",
           "If source evidence does not justify a safe correction, mark UNRESOLVED and do not invent a theorem or quotation.",
           "Return a full corrected script in the identical **Slide N [time sec]: grammar and no other text.",
           "A candidate must be locally re-audited, independently source-reviewed, and checked against the original source before TTS.",
           "Source attachment: "+source_file_name]
    for x in report.get("findings",[]):
        lines.append(f"Slide {x['slide']}: {x['rule']}: {x['revision_guidance']}")
    return {"status":"SOURCE_BOUND_MATH_CORRECTION_PROMPT_NOT_SENT",
            "script_sha256":report["script_sha256"],
            "source_sha256":report.get("source_sha256"),
            "instructions":"\n".join(lines),
            "blocking_findings":report["blocking_count"],
            "max_repair_attempts":3,
            "model_web_dispatch_performed":False,
            "no_silent_source_or_media_replacement":True}


def main(argv=None)->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--script",required=True,type=Path)
    ap.add_argument("--source-pdf",type=Path)
    ap.add_argument("--report",required=True,type=Path)
    ap.add_argument("--repair-prompt",type=Path)
    ap.add_argument("--strict",action="store_true")
    a=ap.parse_args(argv)
    before=a.script.read_bytes()
    source_hash=None
    if a.source_pdf:
        if not a.source_pdf.is_file(): raise ValueError("Missing original source PDF")
        source_hash=hashlib.sha256(a.source_pdf.read_bytes()).hexdigest()
    report=inspect_math_semantics(before.decode("utf-8-sig"),source_sha256=source_hash)
    if a.report.exists(): raise FileExistsError("Never overwrite math semantic receipt")
    with a.report.open("x",encoding="utf8") as stream:
        json.dump(report,stream,indent=2,ensure_ascii=False);stream.write("\n")
    if a.repair_prompt:
        if a.repair_prompt.exists():raise FileExistsError("Never overwrite repair prompt")
        with a.repair_prompt.open("x",encoding="utf8") as stream:
            json.dump(repair_prompt(report),stream,indent=2,ensure_ascii=False);stream.write("\n")
    if a.script.read_bytes()!=before:
        raise RuntimeError("Script changed during math semantics QA")
    print(json.dumps({"status":report["status"],
                      "blocking":report["blocking_count"],
                      "script_sha256":report["script_sha256"]}))
    return 2 if a.strict and report["blocking_count"] else 0

if __name__=="__main__":
    raise SystemExit(main())
