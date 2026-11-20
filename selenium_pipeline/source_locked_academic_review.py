"""Strict source-locked academic review *input and response* contracts.

This does not dispatch to Gemini; run_web_review may opt in with a genuine
original five-utterance evidence packet. Only quotations previously physically
verified in source.pdf may be repeated by a model, or it must say UNRESOLVED.
"""
from __future__ import annotations

from .figure_source_identity import require

import hashlib,json,re

# Exact independently source-registered review regions on immutable original
# Thomas8.4 Slide4. Figure strips and a multi-text radical union are NOT
# ordinary element IDs from the PDF text candidate list.
_ORIGINAL_SLIDE4_REVIEW_TARGETS=(
    ("s004.text.002",(10.909,57.794,339.762,82.252)),
    ("s004.figure82.strip.001",(48.421,91.9534,126.4618,179.099)),
    ("s004.figure82.strip.002",(126.4618,91.9534,208.4046,179.099)),
    ("s004.figure82.strip.003",(208.4046,91.9534,314.4101,179.099)),
    ("s004.text.003-through-s004.text.006",(32.727,186.691,126.5,240.062)),
)

def recover_rendered_json_format_only(raw:str)->dict:
    """Fix embedded string whitespace only; never repair scientific content."""
    require(type(raw) is str and len(raw)<=12000,
            "Too large or missing Gemini response: no JSON rescue")
    content=raw.strip()
    if content.startswith("Gemini said\n\n"):
        content=content[len("Gemini said\n\n"):].strip()
    require(content.startswith("{") and content.endswith("}"),
            "Source reply is not one complete JSON document")
    fixed=[]
    inside=False
    escaped=False
    for character in content:
        if inside:
            if escaped:
                fixed.append(character)
                escaped=False
            elif character=="\\":
                fixed.append(character)
                escaped=True
            elif character=='"':
                fixed.append(character)
                inside=False
            elif character in ("\n","\r","\t"):
                fixed.append({"\n":"\\n","\r":"\\r","\t":"\\t"}[character])
            else:
                fixed.append(character)
        else:
            fixed.append(character)
            if character=='"':
                inside=True
    require(not inside and not escaped,
            "Incomplete quoted source review content")
    restored=json.loads("".join(fixed))
    require(type(restored) is dict and
            restored.get("status")=="ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE",
            "Recovered text is not a source-review JSON object")
    return restored


def assert_original_slide4_source_packet(*,job:dict,packet:dict)->list:
    require(type(job) is dict and type(packet) is dict
            and packet.get("status")=="FIVE_ORIGINAL_SLIDE4_SOURCE_QUOTE_PACKET_REVIEW_ONLY"
            and packet.get("original_utterance_count")==job.get("utterance_count")==5
            and len(job.get("slides",[]))==1
            and job["slides"][0]["slide"]==4
            and all(packet.get("original_"+name+"_sha256")==job.get(name+"_sha256")
                    for name in ("source","slides","script"))
            and packet.get("source_math_semantically_approved_utterances")==0
            and packet.get("source_radical_operator_academically_verified") is False
            and packet.get("independent_two_pass_review_approved") is False
            and packet.get("student_publication_authorized") is False,
            "Original five-unit quotation packet cannot be stale or approved")
    rows=packet.get("original_utterance_evidence")
    original=job["slides"][0]["utterances"]
    require(type(rows) is list and len(rows)==5,
            "Five immutable original quote sets required")
    for i,(p,u) in enumerate(zip(rows,original)):
        require(type(p) is dict
                and p.get("original_utterance_id")==u.get("id")
                and p.get("spoken_sha256")==u.get("spoken_sha256")
                and p.get("exact_original_spoken_text")==u.get("spoken_text")
                and p.get("review_target_id")==_ORIGINAL_SLIDE4_REVIEW_TARGETS[i][0]
                and type(p.get("review_target_bbox_pdf_pt")) in (list,tuple)
                and tuple(p["review_target_bbox_pdf_pt"])==_ORIGINAL_SLIDE4_REVIEW_TARGETS[i][1]
                and p.get("exact_source_quote_count")==2
                and type(p.get("source_evidence")) is list
                and len(p["source_evidence"])==2
                and p.get("evidence_is_semantic_math_approval") is False
                and p.get("original_radical_glyph_reliably_decoded") is False
                and p.get("review_disposition")=="AWAIT_INDEPENDENT_SOURCE_MATH_REVIEW",
                "Source review packet is not exact original five narrations")
        for q in p["source_evidence"]:
            require(type(q.get("source_physical_page")) is int
                    and q["source_physical_page"]>=1
                    and type(q.get("exact_extracted_pdf_quote")) is str
                    and len(q["exact_extracted_pdf_quote"])>=8
                    and type(q.get("source_quote_sha256")) is str
                    and q["source_quote_sha256"] == hashlib.sha256(
                        re.sub(r"\\s+"," ",q["exact_extracted_pdf_quote"]).strip().encode()
                    ).hexdigest()
                    and q.get("original_pdf_spatial_coherence_verified") is True,
                    "Unverified source passage injected")
        require(p.get("evidence_kind")==(
            "INTRO_REFERENCE_TRIANGLES","TANGENT_SQUARED_IDENTITY",
            "SINE_SQUARED_IDENTITY","SECANT_SQUARED_IDENTITY",
            "ROOT_ABSOLUTE_VALUES_CONTEXT_ONLY")[i],
            "Source quote evidence category switched")
    return rows


def review_quote_whitelist(*,job:dict,packet:dict)->list:
    rows=assert_original_slide4_source_packet(job=job,packet=packet)
    return [{"utterance_id":r["original_utterance_id"],
             "spoken_sha256":r["spoken_sha256"],
             "source_verified_target_id":r["review_target_id"],
             "source_verified_target_bbox_pdf_pt":r["review_target_bbox_pdf_pt"],
             "source_evidence_kind":r["evidence_kind"],
             "allowed_citations":[{"source_page":q["source_physical_page"],
                       "verbatim_source_quote":q["exact_extracted_pdf_quote"],
                       "preverified_quote_sha256":q["source_quote_sha256"]}
                         for q in r["source_evidence"]]}
            for r in rows]


def require_quote_locked_model_reply(*,job:dict,packet:dict,response:dict)->None:
    rows=assert_original_slide4_source_packet(job=job,packet=packet)
    supplied=response.get("rows") if type(response) is dict else None
    require(type(supplied) is list and len(supplied)==5,
            "Five complete AI decisions required; partial outputs cannot pass")
    allowed_targets={x["id"] for x in job["slides"][0]["visual_targets"]}
    for i,(entry,model) in enumerate(zip(rows,supplied)):
        require(type(model) is dict
                and model.get("utterance_id")==entry["original_utterance_id"]
                and model.get("spoken_sha256")==entry["spoken_sha256"]
                and model.get("verdict") in ("SUPPORTED","INCORRECT","UNRESOLVED"),
                "AI response changed narrator, SHA, ordering or verdict")
        value=(model.get("source_page"),model.get("verbatim_source_quote"))
        accepted={(q["source_physical_page"],q["exact_extracted_pdf_quote"])
                  for q in entry["source_evidence"]}
        require((value==(None,None) or
                 (type(value[0]) is int and type(value[1]) is str
                  and value in accepted)),
                "Model cited a made-up, out-of-scope or cross-unit source quotation")
        selected=model.get("target_id")
        require(selected is None or
                (type(selected) is str and selected==entry["review_target_id"]),
                "Model selected a target not source-bound to this exact utterance")
        if model["verdict"] in ("SUPPORTED","INCORRECT"):
            require(value in accepted and selected is not None,
                    "Definitive judgment requires a permitted source quote and original slide target")
        if i==4:
            # The original radical absolute-value math glyph is poorly
            # extracted. Neither context text nor squared identity proves
            # narrated principal root semantics; require further source QA.
            require(model["verdict"]=="UNRESOLVED",
                    "Principal-root claim cannot be certified by lossy PDF text")
        require(type(model.get("math_explanation")) is str
                and len(model["math_explanation"].strip())>=25,
                "Require substantive reasoning even when unresolved")
