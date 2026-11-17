"""One-time source-bound offline QA work while Gemini PDF service is blocked.

This is a real independently eligible DEV/QA activity, not a workaround for
two independent scientific model reviews. It prepares original PDF geometry,
verifiable citation candidates for the next untouched slide, and per-utterance
slide-element inventory WITHOUT any provider Send, TTS, or publisher mutation.

Records are SHA-locked, atomic, idempotent and outside the original source
tree. A corrupt prior record fails closed, never silently resetting history.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re

from .evidence_reuse_contract import file_sha256

VERSION = 1
STATUS = "G2_OFFLINE_SOURCE_READINESS_RECORDED_NO_SCIENTIFIC_APPROVAL"
MAX_RECEIPT_BYTES = 80_000


def require(ok, detail: str) -> None:
    if not ok:
        raise ValueError(detail)


def _sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _source_identifiers(folder: Path, queue_root: Path) -> dict:
    # Reuse the production queue/source validator, not a new input policy.
    from .windows_g2_autonomous_qa_supervisor import _is_verified_folder
    _, originals = _is_verified_folder(folder, queue_root)
    queue_file = queue_root / "queue.json"
    require(queue_file.is_file() and not queue_file.is_symlink(),
            "Missing immutable academic queue")
    # An unchanged textbook is NOT enough for cache reuse when the audit's
    # ranker/citation/visual/science verification algorithms are revised.
    # Recompute its source-bound proof under a new implementation digest.
    code_root=Path(__file__).resolve().parent
    modules=(
        "g2_offline_source_readiness.py",
        "incremental_element_candidate_map.py",
        "element_plan_autodraft.py",
        "academic_visual_preflight.py",
        "source_verified_quote_candidates.py",
        "ai_academic_review_consensus.py",
        "recovery_registry.py",
        "recovery_registry_v1.json",
        "physical_fraction_review_targets.py",
        "fraction_pdf_context_review.py",
    )
    signatures={}
    for name in modules:
        code=code_root/name
        require(code.is_file() and not code.is_symlink(),
                "Source QA algorithm not available for versioned verification")
        signatures[name]=file_sha256(code)
    return {**originals,"queue.json":file_sha256(queue_file),
            "audit_implementation_sha256":_sha_bytes(json.dumps(
                signatures,sort_keys=True,separators=(",", ":")
            ).encode("utf8"))}


def _receipt_path(folder: Path, queue_root: Path, work_root: Path,
                  ids: dict) -> Path:
    require(folder.is_dir() and not folder.is_symlink()
            and queue_root.is_dir() and not queue_root.is_symlink()
            and work_root.is_dir() and not work_root.is_symlink()
            and not work_root.is_relative_to(folder)
            and not queue_root.is_relative_to(folder),
            "Independent QA must never edit original source tree")
    for name in ("source.pdf", "slides.pdf", "script.txt", "queue.json",
                 "audit_implementation_sha256"):
        require(re.fullmatch(r"[0-9a-f]{64}", ids.get(name, "")) is not None,
                "Source provenance incomplete")
    key=_sha_bytes(json.dumps({
        "folder": str(folder), "queue_root": str(queue_root),
        "ids": ids, "version": VERSION
    }, sort_keys=True, separators=(",", ":")).encode("utf8"))
    root=work_root / "g2_offline_source_readiness_v1"
    require(not root.is_symlink(), "No linked offline evidence directory")
    return root / (key + ".json")


def _verify_record(path: Path, original: dict, expected_slide: int) -> dict:
    require(path.is_file() and not path.is_symlink()
            and 0 < path.stat().st_size <= MAX_RECEIPT_BYTES,
            "Missing/linked/oversized source-bound offline QA record")
    report=json.loads(path.read_text(encoding="utf8"))
    from .fraction_pdf_context_review import verify_saved_context_packet
    require(type(report) is dict
            and report.get("schema_version")==VERSION
            and report.get("status")==STATUS
            and report.get("source_identifiers")==original
            and report.get("next_unattempted_slide")==expected_slide
            and type(report.get("slide_inventory")) is list
            and len(report["slide_inventory"]) == report.get("slide_count")
            and sum(x["utterance_count"] for x in report["slide_inventory"])
                == report.get("original_utterance_count")
            and report.get("independent_scientific_consensus_granted") is False
            and report.get("academic_approval") is False
            and report.get("new_model_requests")==0
            and report.get("paid_tts_calls")==0
            and report.get("student_publication_authorized") is False
            and report.get("unranked_visual_review_worklist_status")==
                "ORIGINAL_PDF_PHYSICAL_OPTIONS_UNASSIGNED_REVIEW_REQUIRED"
            and type(report.get("unranked_visual_review_worklist")) is list
            and len(report["unranked_visual_review_worklist"])==
                report.get("unranked_visual_review_count")
            and len(report["unranked_visual_review_worklist"])==sum(
                r.get("utterances_without_ranked_targets",0)
                for r in report["slide_inventory"])
            and all(type(x) is dict
                    and x.get("selected_target_id") is None
                    and x.get("source_semantics_approved") is False
                    and x.get("paid_tts_authorized") is False
                    and x.get("model_review_required") is True
                    for x in report["unranked_visual_review_worklist"])
            and type(report.get("ambiguous_fraction_review_worklist")) is list
            and len(report["ambiguous_fraction_review_worklist"])==
                report.get("ambiguous_fraction_review_count")
            and all(type(x) is dict
                    and x.get("selected_target_id") is None
                    and x.get("source_semantics_approved") is False
                    and x.get("paid_tts_authorized") is False
                    and x.get("independent_semantic_choice_required") is True
                    and type(x.get("source_review_target_choices")) is list
                    and len(x["source_review_target_choices"])==2
                    and verify_saved_context_packet(
                        x.get("physically_witnessed_review_contexts"),
                        x["source_review_target_choices"])
                    for x in report["ambiguous_fraction_review_worklist"]),
            "Source-bound offline QA may not be forged or promoted")
    return report


def inspect_and_checkpoint(*, folder: Path, queue_root: Path,
                           work_root: Path, next_slide: int,
                           execute: bool = True) -> dict:
    folder,queue_root,work_root=(
        Path(p).absolute() for p in (folder,queue_root,work_root))
    require(type(next_slide) is int and 1 <= next_slide <= 200
            and type(execute) is bool,
            "Source-bound forward offline QA must have a next slide")
    ids=_source_identifiers(folder,queue_root)
    path=_receipt_path(folder,queue_root,work_root,ids)
    # A process death after fsynced temp write but before atomic promotion
    # is read-only recoverable; no source/model/provider work is replayed.
    torn=path.with_name(path.name+".incomplete")
    require(not torn.is_symlink(),"Linked interrupted offline audit")
    if not path.exists() and torn.exists():
        _verify_record(torn,ids,next_slide)
        require(_source_identifiers(folder,queue_root)==ids,
                "Original content changed during torn checkpoint recovery")
        os.replace(torn,path)
    if path.exists() or path.is_symlink():
        stored=_verify_record(path,ids,next_slide)
        require(_source_identifiers(folder,queue_root)==ids,
                "Source changed during offline-record inspection")
        return {
            "status":"G2_OFFLINE_READINESS_REUSED_NO_NEW_WORK",
            "offline_evidence_path":str(path),
            "offline_evidence_sha256":file_sha256(path),
            "original_utterance_count":stored["original_utterance_count"],
            "slide_count":stored["slide_count"],
            "original_two_pass_accepted":stored["original_two_pass_accepted"],
            "original_pending_or_disputed":stored["original_pending_or_disputed"],
            "unranked_visual_review_count":stored["unranked_visual_review_count"],
            "ambiguous_fraction_review_count":stored["ambiguous_fraction_review_count"],
            "verified_source_citation_candidate_count_for_next_slide":
                stored["verified_source_citation_candidate_count_for_next_slide"],
            "new_model_requests":0,
            "scientific_approval":False,
            "student_publication_authorized":False,
        }
    if not execute:
        return {
            "status":"G2_OFFLINE_READINESS_POSSIBLE_NO_DISPATCH",
            "original_source_sha256":ids["source.pdf"],
            "new_model_requests":0,
            "scientific_approval":False,
            "student_publication_authorized":False,
        }

    from .incremental_element_candidate_map import candidate_map
    from .incremental_lecture_sync_queue import inspect_pre_tts_folder
    from .academic_visual_preflight import inspect as inspect_visual
    from .ai_academic_web_review import build_review_job
    from .ai_academic_review_consensus import reconcile_actual_review_queue

    # Match the existing real academic selector when some WAVs already
    # exist; this audit itself never creates or approves any paid WAV.
    map_all=(candidate_map(folder=folder)
             if any(folder.glob("slide*.wav"))
             else candidate_map(folder=folder,
                                queue=inspect_pre_tts_folder(folder)))
    require(map_all.get("status") ==
            "PER_UTTERANCE_SLIDE_ELEMENT_CANDIDATES_REVIEW_REQUIRED"
            and map_all.get("source_sha256")==ids["source.pdf"]
            and map_all.get("slides_sha256")==ids["slides.pdf"]
            and map_all.get("script_sha256")==ids["script.txt"]
            and 1<=map_all.get("slide_count",0)<=200
            and 1<=map_all.get("utterance_count",0)<=1000,
            "Offline visual inventory did not match original lecture")
    require(next_slide <= map_all["slide_count"],
            "Next original slide outside physical PDF")

    job=build_review_job(folder=folder,slide_numbers=[next_slide])
    citation_packet=job["verified_source_quote_candidates_v1"]
    require(citation_packet.get("status") ==
            "PHYSICALLY_WITNESSED_SOURCE_CITATIONS_V1"
            and citation_packet.get("source_sha256")==ids["source.pdf"]
            and len(citation_packet.get("utterances",[]))==
                job["utterance_count"],
            "Original PDF quote packet not physically verified")
    quotes=sum(len(x["allowed_citations"])
               for x in citation_packet["utterances"])
    with_citations=sum(bool(x["allowed_citations"])
                       for x in citation_packet["utterances"])

    geometry=inspect_visual(folder/"slides.pdf")
    require(geometry.get("pdf_sha256")==ids["slides.pdf"]
            and geometry.get("pages")==map_all["slide_count"]
            and geometry.get("mathematical_correctness_verified") is False,
            "PDF geometry audit cannot prove scientific semantics")
    consensus=reconcile_actual_review_queue(
        queue_root=queue_root,folder=folder)
    require(consensus.get("status")==
            "INDEPENDENTLY_REVALIDATED_AI_SOURCE_MATH_AGREEMENT_QUEUE"
            and consensus["original_utterances"]==
                map_all["utterance_count"]
            and len(consensus["accepted_ai_evidence"])+
                consensus["pending_or_disputed"]==
                map_all["utterance_count"],
            "No independent original two-pass consensus revalidation")

    # Additional independent task when no original Gemini PDF-response is
    # available: prepare the exact source-bound ambiguous-visual worklist for
    # later model/physics review, without assigning even one visual target.
    # Physical targets are offered as observations, never a selected match.
    unresolved=[]
    ambiguous=[]
    inventory=[]
    for i,row in enumerate(map_all["slides"],start=1):
        require(row["slide"]==i,
                "Out-of-order physical source slide identity")
        units=row["original_utterance_candidates"]
        source_targets={
            item.get("draft_element_id"):item
            for item in row["candidate_visual_targets"]}
        for unit in units:
            ranked=unit["candidate_visual_targets"]
            if len(ranked)>=2:
                first,second=ranked[:2]
                a=source_targets.get(first.get("target_id")) or {}
                b=source_targets.get(second.get("target_id")) or {}
                if (a.get("kind")==b.get("kind")=="math_fraction_review"
                        and first.get("ranking_hint",0)>=.8
                        and second.get("ranking_hint",0)>=.8
                        and abs(first["ranking_hint"]-
                                second["ranking_hint"])<=.05):
                    # Preserve exact original-PDF line/bbox context for
                    # EACH repeated literal fraction. This is more useful
                    # to the independent Gemini reviewer than equal .90
                    # scores, but is NOT an automatic target decision.
                    from .fraction_pdf_context_review import (
                        physically_witnessed_fraction_context)
                    options=physically_witnessed_fraction_context(
                        slides_pdf=folder/"slides.pdf",slide=i,
                        choices=[a,b])
                    ambiguous.append({
                        "physically_witnessed_review_contexts":options,
                        "slide":i,
                        "utterance_id":unit.get("utterance_id"),
                        "utterance_sha256":unit.get("original_text_sha256"),
                        "source_review_target_choices":[
                            first["target_id"],second["target_id"]],
                        "reason":"MULTIPLE_PHYSICALLY_VALID_FRACTIONS_EQUIVALENT_RANKING",
                        "selected_target_id":None,
                        "independent_semantic_choice_required":True,
                        "source_semantics_approved":False,
                        "paid_tts_authorized":False,
                    })
            if unit["candidate_visual_targets"]:
                continue
            snippet=str(unit.get("original_text",""))
            has_math=bool(re.search(
                r"\b(?:half|fraction|squared|power|exponent|denominator)\b",
                snippet,re.I))
            targets=[]
            for target in row["candidate_visual_targets"][:24]:
                tid=target.get("draft_element_id")
                bbox=target.get("bbox_pdf_pt")
                if type(tid) is not str or type(bbox) is not list:
                    continue
                require(len(bbox)==4 and all(type(v) in (int,float)
                        for v in bbox),
                        "Unverified physical target geometry in review worklist")
                targets.append({
                    "target_id":tid,"kind":target.get("kind"),
                    "bbox_pdf_pt":bbox,
                    "visible_text_sha256":_sha_bytes(
                        str(target.get("visible_text","")).encode("utf8"))
                })
            unresolved.append({
                "slide":i,
                "utterance_id":unit.get("utterance_id"),
                "utterance_sha256":unit.get("original_text_sha256"),
                "exact_original_spoken_text":snippet[:400],
                "reason":("FRACTION_OR_MATH_LAYOUT_REQUIRES_INDEPENDENT_REVIEW"
                          if has_math else
                          "SEMANTIC_PARAPHRASE_REQUIRES_INDEPENDENT_REVIEW"),
                "physically_witnessed_slide_targets_not_assigned":targets,
                "selected_target_id":None,
                "source_semantics_approved":False,
                "model_review_required":True,
                "paid_tts_authorized":False,
            })
        inventory.append({
            "slide":i,
            "utterance_count":len(units),
            "physical_visual_target_count":len(row["candidate_visual_targets"]),
            "utterances_without_ranked_targets":sum(
                not x["candidate_visual_targets"] for x in units),
            "physical_image_whole_target_count":sum(
                x["kind"]=="image_whole"
                for x in row["candidate_visual_targets"]),
            "technical_geometry_review_findings":
                len(geometry["details"][i-1]["findings"]),
            "source_science_approved":False,
        })
    report={
        "schema_version":VERSION,"status":STATUS,
        "source_identifiers":ids,"slide_count":map_all["slide_count"],
        "original_utterance_count":map_all["utterance_count"],
        "next_unattempted_slide":next_slide,
        "next_slide_utterances":job["utterance_count"],
        "verified_source_citation_candidate_count_for_next_slide":quotes,
        "next_slide_utterances_with_at_least_one_citation_candidate":
            with_citations,
        "next_slide_quote_packet_sha256":_sha_bytes(
            json.dumps(citation_packet,sort_keys=True,ensure_ascii=False,
                       separators=(",", ":")).encode("utf8")),
        "technical_geometry_blocker_count":geometry["blocker_count"],
        "technical_geometry_review_findings":geometry["findings_total"],
        "slide_inventory":inventory,
        "unranked_visual_review_worklist_status":
            "ORIGINAL_PDF_PHYSICAL_OPTIONS_UNASSIGNED_REVIEW_REQUIRED",
        "unranked_visual_review_worklist":unresolved,
        "unranked_visual_review_count":len(unresolved),
        "ambiguous_fraction_review_worklist":ambiguous,
        "ambiguous_fraction_review_count":len(ambiguous),
        "original_two_pass_accepted":len(consensus["accepted_ai_evidence"]),
        "original_pending_or_disputed":consensus["pending_or_disputed"],
        "independent_scientific_consensus_granted":False,
        "figure_semantics_verified":False,
        "academic_approval":False,"new_model_requests":0,
        "paid_tts_calls":0,"student_publication_authorized":False,
        "original_provider_failure_still_blocks_source_review":True,
    }
    require(_source_identifiers(folder,queue_root)==ids,
            "Source/queue changed during complete original QA inventory")
    raw=(json.dumps(report,sort_keys=True,ensure_ascii=False,indent=2)
         +"\n").encode("utf8")
    require(0<len(raw)<=MAX_RECEIPT_BYTES,"Unbounded offline QA evidence")
    path.parent.mkdir(exist_ok=True)
    require(not path.parent.is_symlink(),
            "Cannot write source QA through linked checkpoint directory")
    # Exclusive temp + fsync + atomic replace; never overwrite an existing
    # immutable content-addressed checkpoint from another process.
    temp=path.with_name(path.name + ".incomplete")
    require(not path.exists() and not temp.exists() and not temp.is_symlink(),
            "Existing or interrupted offline checkpoint needs reconciliation")
    with temp.open("xb") as output:
        output.write(raw);output.flush();os.fsync(output.fileno())
    require(not path.exists(),"Concurrent offline QA checkpoint collision")
    os.replace(temp,path)
    _verify_record(path,ids,next_slide)
    return {
        "status":"G2_OFFLINE_READINESS_COMPLETED_NO_GEMINI_SEND",
        "offline_evidence_path":str(path),
        "offline_evidence_sha256":file_sha256(path),
        "original_utterance_count":map_all["utterance_count"],
        "slide_count":map_all["slide_count"],
        "original_two_pass_accepted":len(consensus["accepted_ai_evidence"]),
        "original_pending_or_disputed":consensus["pending_or_disputed"],
        "unranked_visual_review_count":len(unresolved),
        "ambiguous_fraction_review_count":len(ambiguous),
        "verified_source_citation_candidate_count_for_next_slide":quotes,
        "technical_geometry_blocker_count":geometry["blocker_count"],
        "new_model_requests":0,"scientific_approval":False,
        "student_publication_authorized":False,
    }
