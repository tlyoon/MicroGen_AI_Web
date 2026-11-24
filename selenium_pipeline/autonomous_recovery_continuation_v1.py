"""Finite, restart-aware recovery and automatic continuation for MicroGen G2.

The central controller resolves *registered* known failures via actual
production mechanisms, never synthesized review text or arbitrary registry
code. The first certified action family is distinct, one-utterance G2 source
review. Other stages remain closed until independently implemented and tested.

One shared G2 owner lock, a source-bound immutable campaign, SHA-chained
pre-Send reservation journal, and the underlying one-Send academic claims
ensure that interrupted execution cannot duplicate an uncertain Send.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time

from .ai_academic_review_consensus import reconcile_actual_review_queue
from .ai_academic_web_review import build_review_job
from .academic_provider_requalification import (
    ROOT as HEALTH_ROOT, latest_success, probe_once, verify_result)
from .figure_source_identity import _sha, require
from .g2_distinct_focused_source_review_v1 import (
    plan, run_one, _health_ok, _digest as _scope_digest, FOCUS_KIND,
    _last_original_gemini_quarantine_mtime, REVIEW_ROOT_NAME)
from .g2_distinct_focused_challenge_v1 import challenge_once
from .g2_focused_source_consensus_bridge_v1 import reconcile
from .recovery_registry import lookup_mechanism
from .three_pc_worker import LocalInstanceLock

KIND = "autonomous_recovery_continuation"
SIGNATURE = "G2_VERIFIED_FOCUSED_REVIEW_SHOULD_AUTOMATICALLY_ADVANCE"
MECHANISM = "RESERVE_FINITE_SOURCE_BOUND_WORK_RECOVER_CHECKPOINT_AND_FORWARD"
RUN_STATUS = "SOURCE_BOUND_AUTOFORWARD_CAMPAIGN_V1"
EVENT_STATUS = "G2_APPEND_ONLY_RECOVERY_EVENT_V1"
MAX_SENDS = 6
MAX_EVENTS = 96
_CAMPAIGN = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{2,63}\Z")
_SHA = re.compile(r"[a-f0-9]{64}\Z")


def _json(data: dict) -> bytes:
    return (json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False)
            + "\n").encode("utf8")


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_path(p: Path) -> Path:
    p = Path(p).absolute()
    require(not p.is_symlink(), "Linked checkpoint or source folder")
    return p


def _read_json(path: Path, *, limit: int = 40000) -> dict:
    require(path.is_file() and not path.is_symlink()
            and 0 < path.stat().st_size <= limit,
            "Missing, linked or unbounded recovery receipt")
    value = json.loads(path.read_text("utf8"))
    require(type(value) is dict, "Invalid recovery checkpoint schema")
    return value


def _write_once(path: Path, data: dict) -> None:
    """Atomic, restart-recoverable before-Send event publication."""
    body = _json(data)
    stage = path.with_suffix(".stage")
    require(not path.is_symlink() and not stage.is_symlink(),
            "Redirected recovery event")
    if path.exists():
        require(path.read_bytes() == body,
                "Existing immutable recovery event changed")
        return
    if stage.exists():
        require(stage.is_file() and stage.read_bytes() == body,
                "Previous interrupted recovery reservation inconsistent")
    else:
        with stage.open("xb") as f:
            f.write(body)
            f.flush()
            os.fsync(f.fileno())
    os.replace(stage, path)


def _event_core(kind: str, *, index: int, previous: str,
                scope: str, phase: str, detail: str) -> dict:
    require(kind in ("RESERVE","RESULT","HOLD","OFFLINE_RECOVERY")
            and type(index) is int and 1 <= index <= MAX_EVENTS
            and type(previous) is str and _SHA.fullmatch(previous)
            and type(scope) is str and len(scope) <= 120
            and type(phase) is str and phase in
                ("HEALTH","INITIAL","CHALLENGE","RECONCILE","SELECTION")
            and type(detail) is str and len(detail) <= 125,
            "Invalid finite recovery event")
    row = {"status":EVENT_STATUS, "event_index":index,
           "previous_sha256":previous, "type":kind,
           "scope":scope, "phase":phase, "detail":detail}
    row["event_sha256"] = _digest(_json(row))
    return row


def _load_events(root: Path, first_sha: str) -> list[dict]:
    require(root.is_dir() and not root.is_symlink(),
            "Recovery campaign journal is unavailable")
    entries = list(root.glob("event_*.json")) + list(root.glob("event_*.stage"))
    require(len(entries) <= MAX_EVENTS * 2
            and all(x.is_file() and not x.is_symlink() for x in entries),
            "Unbounded, redirected or damaged recovery journal")
    ordered: list[dict] = []
    previous = first_sha
    n = 1
    while True:
        if n > MAX_EVENTS:
            require(not any(x.name.startswith("event_") for x in
                            entries if x.name not in {
                                f"event_{k:03d}.json" for k in range(1,n)}),
                    "Recovery event limit exceeded")
            break
        target = root / f"event_{n:03d}.json"
        stage = root / f"event_{n:03d}.stage"
        if not target.exists() and not stage.exists():
            break
        obj = _read_json(target if target.exists() else stage)
        expected = _event_core(
            obj.get("type"), index=n, previous=previous,
            scope=obj.get("scope"), phase=obj.get("phase"),
            detail=obj.get("detail"))
        require(obj == expected and
                (not target.exists() or not stage.exists()
                 or target.read_bytes() == stage.read_bytes()),
                "Recovery journal chain or interrupted stage corrupt")
        _write_once(target, expected)
        if stage.exists():
            # The final event already survived a crash after os.replace;
            # remove only its byte-identical uncommitted staging duplicate.
            require(target.read_bytes()==stage.read_bytes(),
                    "Recovery stage disagrees with committed reservation")
            stage.unlink()
        ordered.append(expected)
        previous = obj["event_sha256"]
        n += 1
    remaining = list(root.glob("event_*.json")) + list(root.glob("event_*.stage"))
    require(len(remaining) == len(ordered)
            and all(x.name == f"event_{i:03d}.json"
                    for i,x in enumerate(sorted(remaining),1)),
            "Non-contiguous or unrecognized recovery event")
    return ordered


def _append(root: Path, header: dict, events: list[dict], kind: str,
            *, scope: str, phase: str, detail: str) -> list[dict]:
    require(len(events) < MAX_EVENTS, "Bounded recovery journal exhausted")
    previous = (events[-1]["event_sha256"] if events
                else _digest(_json(header)))
    record = _event_core(kind, index=len(events)+1, previous=previous,
                         scope=scope, phase=phase, detail=detail)
    _write_once(root/f"event_{len(events)+1:03d}.json", record)
    return [*events, record]


def _campaign(*, root: Path, campaign_id: str, source_sha: str,
              queue_sha: str, max_sends: int) -> tuple[Path, dict, list[dict]]:
    require(type(campaign_id) is str and _CAMPAIGN.fullmatch(campaign_id)
            and type(max_sends) is int and 0 <= max_sends <= MAX_SENDS
            and _SHA.fullmatch(source_sha) and _SHA.fullmatch(queue_sha),
            "Finite source-bound campaign identity required")
    root = _safe_path(root)
    root.mkdir(parents=True, exist_ok=True)
    require(root.is_dir() and not root.is_symlink(),
            "Invalid autonomous recovery checkpoint root")
    home = root / campaign_id
    home.mkdir(exist_ok=True)
    require(home.is_dir() and not home.is_symlink(),
            "Unsafe original campaign scope")
    header = {
        "status": RUN_STATUS, "schema_version": 1,
        "campaign_id": campaign_id,
        "source_sha256": source_sha, "queue_sha256": queue_sha,
        "max_possible_model_sends": max_sends,
        "automatic_api_fallback_authorized": False,
        "historic_request_replay_authorized": False,
        "student_publication_authorized": False,
    }
    _write_once(home/"campaign.json", header)
    events = _load_events(home, _digest(_json(header)))
    return home, header, events


@contextmanager
def _owned_neon_high():
    old = {k: os.environ.get(k) for k in (
        "MICROGEN_GEMINI_UI_MODE", "MICROGEN_GEMINI_THINKING_LEVEL",
        "MICROGEN_ACTIVE_GENERATION_STAGE")}
    try:
        os.environ.update({
            "MICROGEN_GEMINI_UI_MODE": "pro",
            "MICROGEN_GEMINI_THINKING_LEVEL": "high",
            "MICROGEN_ACTIVE_GENERATION_STAGE": "academic_review"})
        yield
    finally:
        for k, value in old.items():
            if value is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = value


def _health(*, queue_root: Path, source_sha: str,
            old_claim: Path, now: float) -> Path | None:
    after = max(old_claim.stat().st_mtime,
                _last_original_gemini_quarantine_mtime())
    receipt = latest_success(
        checkpoint_parent=queue_root.parent,
        source_sha=source_sha, family="neon",
        after_unix=after, now=now)
    if receipt is None or now-receipt["observed_unix"] > 21600:
        return None
    path = (queue_root.parent/HEALTH_ROOT/source_sha/"neon"/
            receipt["utc_day"]/"result.json")
    _health_ok(health_result=path, queue_root=queue_root,
               source_sha=source_sha, old_claim=old_claim, family="neon")
    return path


def _choose(*, folder: Path, queue_root: Path,
            eligible: set[str], skipped: set[str]) -> dict | None:
    """Prefer existing half-completed source claims; never relabel old Sends."""
    original = _read_json(queue_root/"queue.json", limit=500000)
    require(original.get("status") == "IMMUTABLE_ORIGINAL_GEMINI_AI_REVIEW_QUEUE"
            and original.get("original_source_folder") == str(folder)
            and original.get("student_publication_authorized") is False,
            "Original immutable review queue is no longer trustworthy")
    pending = []
    for row in original["slide_jobs"]:
        slide = row["slide"]
        old = queue_root/f"slide_{slide:03d}_initial_review_attempt_01_request"
        if not old.is_dir() or (old/"model_response_untrusted.txt").exists():
            continue
        claim = old/"dispatch_attempted.claim"
        require(claim.is_file() and not claim.is_symlink(),
                "Missing immutable original possible-Send claim")
        claim_sha = _sha(claim)
        # Parse a source slide ONCE. Reconstruct each potential scope using
        # the already verified production scope identity formula; only the
        # one selected candidate must undergo the expensive physical quote
        # and slide-target source verification in plan().
        job = build_review_job(folder=folder, slide_numbers=[slide])
        require(job["source_sha256"] == row["original_source_sha256"]
                and job["slides_sha256"] == row["original_slides_sha256"]
                and job["script_sha256"] == row["original_script_sha256"],
                "Original source/slide/script changed before source selection")
        for unit in job["slides"][0]["utterances"]:
            uid = unit["id"]
            if uid not in eligible or uid in skipped:
                continue
            scope_sha = _scope_digest({
                "kind":FOCUS_KIND,
                "source_sha256":job["source_sha256"],
                "slides_sha256":job["slides_sha256"],
                "script_sha256":job["script_sha256"],
                "slide":slide,
                "utterance_id":uid,
                "historic_original_claim_sha256":claim_sha})
            scope = queue_root.parent/REVIEW_ROOT_NAME/scope_sha
            require(not scope.is_symlink(), "Redirected focused review scope")
            if (scope/"two_pass_evidence.json").exists():
                continue
            initial, challenge = scope/"initial_request",scope/"challenge_request"
            if challenge.exists():
                require(challenge.is_dir() and not challenge.is_symlink(),
                        "Tampered challenge checkpoint")
                phase = ("RECONCILE" if
                         (challenge/"model_response_untrusted.txt").is_file()
                         else "HOLD_UNCERTAIN")
                priority = 0 if phase == "RECONCILE" else 4
            elif initial.exists():
                require(initial.is_dir() and not initial.is_symlink(),
                        "Tampered initial checkpoint")
                phase = ("CHALLENGE" if
                         (initial/"model_response_untrusted.txt").is_file()
                         else "HOLD_UNCERTAIN")
                priority = 1 if phase == "CHALLENGE" else 4
            else:
                phase, priority = "INITIAL", 2
            pending.append((priority,slide,uid,phase,scope_sha,scope))
    if not pending:
        return None
    # A NEW focused request with an unresolved possible Send triggers a
    # source-review circuit breaker. Do not choose another clean unit simply
    # because it sorts ahead of the uncertain one.
    uncertain = [row for row in pending if row[3] == "HOLD_UNCERTAIN"]
    _,slide,uid,phase,scope_sha,scope = min(
        uncertain or pending,key=lambda x:(x[0],x[1],x[2]))
    item = plan(folder=folder,queue_root=queue_root,
                slide=slide,utterance_id=uid)
    require(item["scope_sha256"]==scope_sha,
            "Source-scoped task identity differs from original claim")
    return {"slide":slide,"utterance_id":uid,"phase":phase,
            "item":item,"scope":scope}


def _possible_sends(events: list[dict]) -> int:
    return sum(e["type"]=="RESERVE" and e["phase"] in (
        "HEALTH","INITIAL","CHALLENGE") for e in events)


def _reservation(events: list[dict], scope: str, phase: str) -> bool:
    return any(e["type"]=="RESERVE" and e["scope"]==scope
               and e["phase"]==phase for e in events)


def run_campaign(*, folder: Path, queue_root: Path, work_root: Path,
                 campaign_id: str, max_possible_sends: int,
                 execute: bool = False,
                 auto_health: bool = False,
                 max_actions: int = 12,
                 stage_source_only: bool = False,
                 initial_runner=None, challenge_runner=None,
                 health_probe=None,
                 source_consensus=None, consensus_bridge=None) -> dict:
    """One finite foreground run; restart with same campaign ID and budget.

    Existing saved review checkpoints are revalidated before any continuation.
    A pre-Send RESERVED event always consumes budget—even when the process
    crashes and it is not known whether the external provider received it.
    """
    require(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
            "Autonomous recovery handler not in executable registry")
    require(type(execute) is bool and type(auto_health) is bool
            and type(stage_source_only) is bool
            and type(max_actions) is int and 1<=max_actions<=24,
            "Unsafe autonomous continuation contract")
    folder,queue_root,work_root = map(_safe_path, (
        folder,queue_root,work_root))
    require(folder.is_dir() and queue_root.is_dir() and work_root.is_dir()
            and work_root == queue_root
            and not work_root.is_relative_to(folder)
            and not queue_root.is_relative_to(folder),
            "Use the existing G2 queue's ONE common supervisor lock root")
    original_file = queue_root/"queue.json"
    old = _read_json(original_file, limit=500000)
    require(old.get("original_source_folder")==str(folder)
            and old.get("expected_utterances",0)>1,
            "Wrong textbook queue or empty original source")
    hash_source = _sha(folder/"source.pdf")
    queue_sha = _sha(original_file)
    lock_name = "g2_qa_"+hashlib.sha256(
        str(queue_root).encode("utf8")).hexdigest()[:20]
    with LocalInstanceLock(lock_name,
                           work_root/".microgen_g2_supervisor_locks"):
        home,header,events = _campaign(
            root=work_root/"autonomous_recovery_continuation_v1",
            campaign_id=campaign_id, source_sha=hash_source,
            queue_sha=queue_sha, max_sends=max_possible_sends)
        runner1 = initial_runner or run_one
        runner2 = challenge_runner or challenge_once
        reader = source_consensus or reconcile_actual_review_queue
        bridge = consensus_bridge or reconcile
        initial_original = reader(folder=folder,queue_root=queue_root)
        verified = bridge(folder=folder,queue_root=queue_root,
                          original_consensus=initial_original)
        require(verified.get("status")==
                    "G2_ORIGINAL_AND_FOCUSED_SOURCE_AI_EVIDENCE_RECONCILED_NO_RELEASE"
                and verified.get("original_total_utterances")==
                    old["expected_utterances"]
                and verified.get("new_provider_requests")==0
                and verified.get("student_publication_authorized") is False,
                "Source scientific acceptance not independently reverified")
        total = verified["combined_source_AI_agreements"]
        accepted = {x["utterance_id"] for x in
                    initial_original["accepted_ai_evidence"]}
        accepted.update(verified["new_focused_utterance_ids"])
        unresolved = {x["utterance_id"] for x in
                      initial_original["unresolved"]}
        eligible = unresolved-accepted
        blocked = set()
        work_done = []
        status = "NO_ELIGIBLE_NEW_SOURCE_REVIEW"
        for _ in range(max_actions):
            selection = _choose(
                folder=folder,queue_root=queue_root,
                eligible=eligible,skipped=blocked)
            if selection is None:
                break
            uid,phase,item,scope = (
                selection["utterance_id"],selection["phase"],
                selection["item"],selection["scope"])
            slot = item["scope_sha256"]
            old_claim = (queue_root/
                         f"slide_{selection['slide']:03d}_initial_review_attempt_01_request"/
                         "dispatch_attempted.claim")
            if phase=="HOLD_UNCERTAIN":
                status="HOLD_UNCERTAIN_NEW_REVIEW_NO_REPLAY"
                blocked.add(uid)
                work_done.append({"unit":uid,"phase":phase,
                                  "new_provider_requests":0})
                if stage_source_only and not execute:
                    # Source-only planning may inspect a DIFFERENT task;
                    # the historic held task is still never dispatched.
                    continue
                # Model egress remains stopped by an uncertain new Send.
                break
            if phase=="RECONCILE":
                try:
                    existing = runner2(
                        folder=folder,queue_root=queue_root,
                        slide=selection["slide"],utterance_id=uid,
                        health_result=Path("NO_BROWSER_NEEDED_FOR_SAVED_REPLY"),
                        family="neon")
                    work_done.append({"unit":uid,"phase":phase,
                                      "status":existing["status"],
                                      "new_provider_requests":0})
                    status="RECOVERED_INDEPENDENT_SOURCE_REVIEW"
                except Exception as exc:
                    status="SOURCE_REVIEW_RECONCILIATION_BLOCKED"
                    work_done.append({"unit":uid,"phase":phase,
                                      "error_class":type(exc).__name__})
                    break
                blocked.add(uid)
                continue
            # New source-focused tasks must not target a slide heading
            # simply because it appears first in original PDF element order.
            # Physically witness and quarantine mismatched targets BEFORE
            # any health probe or possible Gemini model Send.
            selected_target=item["job"]["slides"][0]["visual_targets"][0]["id"]
            ranked=item["job"]["slides"][0]["utterances"][0][
                "ranked_candidates"]
            require(bool(ranked),"Focused original narration has no ranked target")
            source_preflight=None
            if ((not execute and stage_source_only)
                    or (execute and selected_target!=ranked[0])):
                from .g2_focused_source_target_preflight_v1 import stage
                source_preflight=stage(
                    folder=folder,queue_root=queue_root,item=item)
                require(source_preflight["new_browser_sends"]==0
                        and source_preflight["new_paid_gemini_API_calls"]==0
                        and source_preflight["student_publication_authorized"] is False,
                        "Source-target preflight must not bypass G2 QA")
            if (source_preflight is not None and
                    source_preflight["status"]==
                    "G2_FOCUSED_RENDERED_TARGET_RANK_MISMATCH_NO_SEND"):
                from .g2_ranked_source_review_candidate_v2 import (
                    stage as stage_ranked_v2)
                candidate_v2=stage_ranked_v2(
                    folder=folder,queue_root=queue_root,item=item,
                    source_preflight=source_preflight)
                require(candidate_v2["new_browser_sends"]==0
                        and candidate_v2["paid_gemini_API_calls"]==0
                        and candidate_v2["new_review_send_authorized"] is False
                        and candidate_v2["student_publication_authorized"] is False,
                        "New ranked review input must not bypass academic QA")
                status="G2_RANKED_SOURCE_CANDIDATE_STAGED_NO_SEND"
                work_done.append({"unit":uid,"phase":phase,
                    "source_target_audit":source_preflight,
                    "ranked_source_review_candidate":candidate_v2,
                    "new_provider_requests":0})
                blocked.add(uid)
                continue
            if not execute:
                status="NEXT_ELIGIBLE_SOURCE_REVIEW_AWAITS_EXECUTION"
                work_done.append({"unit":uid,"phase":phase,
                                  "new_provider_requests":0,
                                  "source_target_audit":source_preflight})
                if stage_source_only:
                    blocked.add(uid)
                    continue
                break
            if _possible_sends(events) >= max_possible_sends:
                status="FINITE_CAMPAIGN_SEND_BUDGET_EXHAUSTED"
                work_done.append({"unit":uid,"phase":phase,
                                  "new_provider_requests":0})
                break
            if _reservation(events,slot,phase):
                # One reservation may have reached Gemini. Never claim an
                # unknown past Send is safely repeatable.
                status="PERSISTED_RESERVATION_NO_REPLAY"
                blocked.add(uid)
                break
            now=time.time()
            health_path = _health(queue_root=queue_root,
                                  source_sha=hash_source,
                                  old_claim=old_claim,now=now)
            if health_path is None:
                if not auto_health:
                    status="FRESH_SOURCE_FREE_NEON_HEALTH_REQUIRED_NO_SEND"
                    work_done.append({"unit":uid,"phase":phase,
                                      "new_provider_requests":0})
                    break
                health_scope="health:"+datetime.fromtimestamp(
                    now,timezone.utc).strftime("%Y%m%d")
                if (_reservation(events,health_scope,"HEALTH") or
                        _possible_sends(events)>=max_possible_sends):
                    status="SOURCE_FREE_HEALTH_ALREADY_CLAIMED_NO_REPLAY"
                    break
                events = _append(home,header,events,"RESERVE",
                                 scope=health_scope,phase="HEALTH",
                                 detail="ONE_SOURCE_FREE_NEON_HIGH_HEALTH_ATTEMPT")
                try:
                    with _owned_neon_high():
                        observation = (health_probe or probe_once)(
                            checkpoint_parent=queue_root.parent,
                            queue_root=queue_root,source_sha=hash_source,
                            family="neon",chrome_port=9222)
                    events = _append(
                        home,header,events,"RESULT",
                        scope=health_scope,phase="HEALTH",
                        detail=str(observation.get("status","UNKNOWN"))[:125])
                    health_path = _health(
                        queue_root=queue_root,source_sha=hash_source,
                        old_claim=old_claim,now=time.time())
                except Exception as exc:
                    status="SOURCE_FREE_HEALTH_BLOCKED_NO_PROVIDER_RETRY"
                    work_done.append({"unit":uid,"phase":"HEALTH",
                                      "error_class":type(exc).__name__})
                    break
                if health_path is None:
                    status="SOURCE_FREE_HEALTH_UNVERIFIED_NO_REVIEW"
                    break
                # Health itself is a possible provider Send. A one-Send
                # campaign cannot spend one on health AND another on science.
                if _possible_sends(events) >= max_possible_sends:
                    status="FINITE_CAMPAIGN_SEND_BUDGET_EXHAUSTED_AFTER_HEALTH"
                    break
            # A durable reservation is written BEFORE invoking any code which
            # may click Gemini Send; restarting the same campaign cannot
            # increase the possible number of external Sends.
            events = _append(home,header,events,"RESERVE",
                             scope=slot,phase=phase,
                             detail=uid)
            try:
                if phase=="INITIAL":
                    result = runner1(
                        folder=folder,queue_root=queue_root,
                        slide=selection["slide"],utterance_id=uid,
                        health_result=health_path,family="neon")
                    require(result.get("status")==
                                "FOCUSED_NEW_REVIEW_ONE_PASS_UNAPPROVED"
                            and result.get("new_original_slide_consensus_count")==0
                            and result.get("student_publication_authorized") is False,
                            "Unverified one-pass automatic source result")
                else:
                    result = runner2(
                        folder=folder,queue_root=queue_root,
                        slide=selection["slide"],utterance_id=uid,
                        health_result=health_path,family="neon")
                    require(result.get("status") in (
                        "FOCUSED_TWO_PASS_SOURCE_AI_AGREEMENT_UNAPPROVED",
                        "FOCUSED_TWO_PASS_DISPUTED_NO_PROMOTION")
                        and result.get("original_g2_segments_promoted")==0
                        and result.get("student_publication_authorized") is False,
                        "Unverified two-pass scientific outcome")
                events = _append(home,header,events,"RESULT",
                                 scope=slot,phase=phase,
                                 detail=result["status"])
                status="ADVANCED_ONE_SOURCE_REVIEW_STAGE"
                work_done.append({"unit":uid,"phase":phase,
                                  "status":result["status"],
                                  "possible_provider_send_reserved":True})
                if phase=="CHALLENGE":
                    blocked.add(uid)
            except Exception as exc:
                status="SOURCE_REVIEW_FAILED_OR_UNCERTAIN_NO_REPLAY"
                work_done.append({"unit":uid,"phase":phase,
                                  "error_class":type(exc).__name__,
                                  "possible_provider_send_reserved":True})
                events = _append(
                    home,header,events,"HOLD",scope=slot,phase=phase,
                    detail=type(exc).__name__[:125])
                break
        # No new source/audio QA approval is asserted by this campaign.
        # When there was no new or recovered academic result, keep the
        # already independently verified source consensus from the start
        # of this locked cycle. Avoid a needless second 85-unit PDF parse.
        changed_review_evidence = any(
            row.get("phase")=="RECONCILE"
            or row.get("status") in (
                "FOCUSED_NEW_REVIEW_ONE_PASS_UNAPPROVED",
                "FOCUSED_TWO_PASS_SOURCE_AI_AGREEMENT_UNAPPROVED",
                "FOCUSED_TWO_PASS_DISPUTED_NO_PROMOTION")
            for row in work_done)
        if changed_review_evidence:
            final_original = reader(folder=folder,queue_root=queue_root)
            final = bridge(folder=folder,queue_root=queue_root,
                           original_consensus=final_original)
        else:
            final = verified
        require(final.get("original_total_utterances")==old["expected_utterances"]
                and final.get("combined_source_AI_agreements",0)>=total
                and final.get("new_provider_requests")==0
                and final.get("student_publication_authorized") is False
                and _sha(original_file)==queue_sha
                and _sha(folder/"source.pdf")==hash_source,
                "Source, original queue or academic acceptance drift")
        return {
            "status":status,
            "campaign_id":campaign_id,
            "campaign_checkpoint":str(home/"campaign.json"),
            "recovery_registry_handler":MECHANISM,
            "possible_provider_sends_reserved":_possible_sends(events),
            "max_possible_provider_sends":max_possible_sends,
            "remaining_possible_send_budget":max_possible_sends-_possible_sends(events),
            "stages":work_done,
            "original_source_AI_agreements":final["original_two_pass_source_AI_agreements"],
            "reconciled_source_AI_agreements":final["combined_source_AI_agreements"],
            "pending_source_AI_review":final["pending_or_disputed_source_AI"],
            "source_sha256":hash_source,
            "new_paid_gemini_api_calls":0,
            "original_historical_requests_replayed":False,
            "independent_acoustic_QA_complete":False,
            "full_G2_acceptance_claimed":False,
            "full_G3_acceptance_claimed":False,
            "student_publication_authorized":False,
        }


def main(argv: list[str] | None = None) -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",type=Path,required=True)
    p.add_argument("--queue-root",type=Path,required=True)
    p.add_argument("--work-root",type=Path,required=True)
    p.add_argument("--campaign-id",required=True)
    p.add_argument("--max-possible-sends",type=int,default=0)
    p.add_argument("--max-actions",type=int,default=12)
    p.add_argument("--execute",action="store_true")
    p.add_argument("--auto-health",action="store_true")
    p.add_argument("--stage-source-only",action="store_true")
    args=p.parse_args(argv)
    result=run_campaign(
        folder=args.folder,queue_root=args.queue_root,work_root=args.work_root,
        campaign_id=args.campaign_id,
        max_possible_sends=args.max_possible_sends,
        max_actions=args.max_actions,execute=args.execute,
        auto_health=args.auto_health,
        stage_source_only=args.stage_source_only)
    print(json.dumps(result,sort_keys=True,indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
