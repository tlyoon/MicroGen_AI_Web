"""Conservative ZERO-MODEL rich-element alignment fallback for Gemini outages.

Operates ONLY on frozen publisher/source-author/script SHA worklists already
accepted by rich_element_mapping_checkpoint. It chooses source-quoted visible
prose when a single author PDF text block has distinct lexical support and
the ORIGINAL textbook contains the same substantive words. Any mathematics,
figure semantics, unknown source quote, low margin or model-free guess remains
unresolved. Never synthesizes PCM, rechecks an accepted image identity, or
claims scholarly/student approval.

Output uses the SAME strict response schema as rich_element_model_alignment,
so a future Gemini/ChatGPT proposal can fill ONLY unverified utterances while
already physically accepted text links remain intact and hash-reused.
"""

from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

from .rich_element_model_alignment import (
    RichMappingError, require, request_for_slide, assess_response,
    normalized, trig_families, stable_hash)
from .scene_candidate_authoring import terms


ALGEBRA = re.compile(
    r"[=+√∫≤≥θπ±^]|"
    r"\b(?:sine|cosine|tangent|secant|arcsine|arccosine|"
    r"arctangent|arcsecant|square root|squared|minus|plus|"
    r"negative|integral|divided|theta|pi|domain|inverse|"
    r"derivative|ratio|absolute value|larger than|less than)\b",
    flags=re.IGNORECASE,
)
VISUAL_SEMANTIC = re.compile(
    r"\b(?:figure|graph|diagram|plot|triangle|panels?|"
    r"image|curve|axes|vertical|horizontal)\b", re.IGNORECASE)


def _terms(value: str) -> set[str]:
    return set(terms(value))


def overlap(a: str, b: str) -> float:
    """Symmetric bounded lexical source hint, NEVER standalone math proof."""
    left,right=_terms(a),_terms(b)
    if not left or not right:
        return 0.
    return round(2*len(left & right)/max(1,len(left)+len(right)),5)


def _source_spans(original_text: str):
    # Retain original exact characters, including newlines. Split only into
    # contiguous unmodified source-page fragments, not paraphrased sentences.
    lines=original_text.splitlines(keepends=True)
    seen=set()
    for index in range(len(lines)):
        for count in (1,2,3,4):
            raw="".join(lines[index:index+count]).strip()
            if 12<=len(raw)<=240 and raw not in seen:
                seen.add(raw)
                yield raw
    for expression in re.split(r"(?<=[.!?])\s+",original_text):
        expression=expression.strip()
        if 12<=len(expression)<=240 and expression not in seen:
            seen.add(expression)
            yield expression


def _best_original_quote(speech: str, visible: str, pages: list[dict]) -> tuple:
    possibilities=[]
    for entry in pages:
        number=entry["source_page"]
        full=entry["original_page_text"]
        for literal in _source_spans(full):
            quote_score=min(overlap(literal,speech),
                            overlap(literal,visible))
            if len(_terms(literal)&_terms(speech))<2 or \
               len(_terms(literal)&_terms(visible))<2:
                continue
            if quote_score>=.32:
                possibilities.append((quote_score,number,literal))
    possibilities.sort(key=lambda x:(-x[0],x[1],len(x[2])))
    if not possibilities:
        return None,None,0.
    score,page,quote=possibilities[0]
    return page,quote,score


def propose_safe_text_slide(request: dict) -> dict:
    require(request.get("status")==
            "SOURCEBOUND_RICH_ELEMENT_AI_PROPOSAL_INPUT_REVIEW_ONLY",
            "Not an immutable original publisher and author source request")
    targets=request["visible_targets"]
    associations=[]
    for unit in request["original_utterances"]:
        text=unit["verbatim_text"]
        candidates=[]
        if not ALGEBRA.search(text) and not VISUAL_SEMANTIC.search(text):
            for target in targets:
                visible=target["visible_text"]
                if (target["kind"]!="text_block"
                        or target.get("figure_panel_review_required")
                        or not visible.strip()
                        or ALGEBRA.search(visible)
                        or VISUAL_SEMANTIC.search(visible)
                        or trig_families(visible)):
                    continue
                matching=overlap(text,visible)
                if matching<.50 or len(_terms(text)&_terms(visible))<3:
                    continue
                page,quote,source_score=_best_original_quote(
                    text,visible,request["source_page_excerpts"])
                if quote is None:
                    continue
                # Require separate support from original source AND author,
                # not just similarity between two copied slide passages.
                combined=round(.65*matching+.35*source_score,5)
                candidates.append((combined,target["target_id"],
                                   page,quote,matching,source_score))
        candidates.sort(key=lambda x:(-x[0],x[1]))
        top=candidates[0] if candidates else None
        runner_up=candidates[1][0] if len(candidates)>1 else 0.
        if top and top[0]>=.58 and top[0]-runner_up>=.19 and top[5]>=.35:
            proposed={
                "utterance_id":unit["utterance_id"],
                "target_id":top[1],
                "source_page":top[2],
                "source_quote":top[3],
                "reason":"Deterministic source+author prose lexical corroboration "
                         f"score={top[0]:.3f}; no math/figure semantics claimed",
                "needs_review":False,
            }
        else:
            proposed={
                "utterance_id":unit["utterance_id"],
                "target_id":None,
                "source_page":None,
                "source_quote":None,
                "reason":"Independent physical source-prose support missing, "
                         "formula/figure present, or multiple competing targets",
                "needs_review":True,
            }
        associations.append(proposed)
    return {
        "slide":request["slide"],
        "request_sha256":request["request_sha256"],
        "producer":"DETERMINISTIC_SOURCE_PDF_SAFE_PROSE_FALLBACK_V1",
        "associations":associations,
        "audio_generation_authorized":False,
        "student_publication_authorized":False,
    }


def fully_audited_slide(*,source_folder:Path,checkpoint:Path,slide:int)->tuple[dict,dict]:
    request=request_for_slide(source_folder=source_folder,
                              checkpoint=checkpoint,slide_number=slide)
    proposal=propose_safe_text_slide(request)
    # Independently re-run ALL model-contract source, geometry and math
    # guards even for deterministic proposed matches.
    audit=assess_response(source_folder=source_folder,
             checkpoint=checkpoint,slide_number=slide,proposed=proposal)
    for choice,entry in zip(proposal["associations"],audit["entries"]):
        if choice["target_id"] is not None and not entry[
              "source_and_visible_text_anchors_independently_verified"]:
            choice.update({
                "target_id":None,"source_page":None,"source_quote":None,
                "needs_review":True,
                "reason":"Independent source/author verifier rejected "
                         "the lexical candidate: "+
                         ", ".join(entry[
                             "remaining_independent_scientific_review_reasons"])[:300],
            })
    audit=assess_response(source_folder=source_folder,
            checkpoint=checkpoint,slide_number=slide,proposed=proposal)
    require(all((x["target_id"] is None)==
                bool(entry["remaining_independent_scientific_review_reasons"])
                for x,entry in zip(proposal["associations"],audit["entries"])),
            "Unreviewed source mathematics/figure entered accepted text fallback")
    return proposal,audit


def stage_section(*,source_folder:Path,checkpoint:Path,destination:Path)->dict:
    from .rich_element_model_alignment import load_accepted_checkpoint
    meta,draft=load_accepted_checkpoint(folder=source_folder,checkpoint=checkpoint)
    destination=Path(destination).absolute()
    require(destination.parent.is_dir() and not destination.exists()
            and not destination.is_relative_to(Path(source_folder).absolute()),
            "New external original SHA-bound response folder required")
    # Precompute all before creating any output. A source/model exception
    # cannot leave an apparently completed half-accepted section.
    completed=[]
    for slide in range(1,meta["slide_count"]+1):
        response,audit=fully_audited_slide(
            source_folder=source_folder,checkpoint=checkpoint,slide=slide)
        completed.append((response,audit))
    # Reverify frozen physical originals and cached source worklist.
    load_accepted_checkpoint(folder=source_folder,checkpoint=checkpoint)
    destination.mkdir()
    refs={}
    for row,audit in completed:
        name=f"slide_{row['slide']:03d}.json"
        file=destination/name
        with file.open("x",encoding="utf8") as stream:
            json.dump(row,stream,indent=2,ensure_ascii=False)
            stream.write("\n")
        refs[name]=stable_hash(row)
    summary={
        "schema_version":1,
        "status":"DETERMINISTIC_SOURCE_GROUNDED_SAFE_PROSE_CANDIDATES_REVIEW_ONLY",
        "source_inputs_sha256":meta["source_inputs_sha256"],
        "original_slide_count":meta["slide_count"],
        "original_utterances":sum(x["utterances_total"] for _,x in completed),
        "machine_verified_safe_prose_links":sum(
            x["text_source_and_author_anchors_passed"] for _,x in completed),
        "unresolved_original_math_figure_or_ambiguous_utterances":sum(
            x["remaining_review_items"] for _,x in completed),
        "each_slide_response_stable_sha256":refs,
        "existing_original_analysis_reused":True,
        "model_provider_invoked":False,
        "paid_tts_authorized":False,
        "student_publication_authorized":False,
    }
    with (destination/"SAFE_PROSE_FALLBACK_MANIFEST.json").open(
            "x",encoding="utf8") as stream:
        json.dump(summary,stream,indent=2,ensure_ascii=False)
        stream.write("\n")
    return summary


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-folder",type=Path,required=True)
    ap.add_argument("--checkpoint",type=Path,required=True)
    ap.add_argument("--out-dir",type=Path,required=True)
    args=ap.parse_args(argv)
    summary=stage_section(source_folder=args.source_folder,
          checkpoint=args.checkpoint,destination=args.out_dir)
    print(json.dumps({k:summary[k] for k in (
        "status","original_slide_count","original_utterances",
        "machine_verified_safe_prose_links",
        "unresolved_original_math_figure_or_ambiguous_utterances",
        "model_provider_invoked","paid_tts_authorized")}))
if __name__=="__main__":
    main()
