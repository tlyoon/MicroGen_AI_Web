"""Stage-scoped recovery for a removed Gemini Flash academic-review family.

This is NOT a model equivalence claim. The independent source-review stage
may use the already supported Pro family, with an exact owned-tab Medium
verification, only when BOTH authorized Flash sessions lack Flash. The
normal figure/slides/narration stage model policies remain unchanged.

This is a PROCESS-ISOLATED entry point. The selected UI family is inherited
by the existing academic review worker through the process environment;
source claims, Send boundaries, strict citation validation and no-resend
are still enforced by source_review_autonomous_campaign.run.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .academic_gemini_presend_preflight import (
    AcademicGeminiPreSendBlocked, select_ready_existing_session,
)
from .gemini_model import configured_ui_mode

RECEIPT_NAME = "academic_model_route_v1.json"
MISSING_FAMILY = "GEMINI_REQUESTED_MODEL_FAMILY_UNAVAILABLE"


class AcademicReviewRouteError(ValueError):
    pass


def _new_verified_receipt(root: Path, receipt: dict) -> None:
    """Never silently change a previously selected model/port for this root."""
    output = root / RECEIPT_NAME
    if output.is_symlink():
        raise AcademicReviewRouteError("Unsafe academic model-route evidence")
    encoded = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if output.exists():
        if output.read_text(encoding="utf8") != encoded:
            raise AcademicReviewRouteError("Existing source-bound review route differs")
        return
    with output.open("x", encoding="utf8") as file:
        file.write(encoded)


def run(*, plan_path: Path, root: Path, max_jobs: int = 1,
        chrome_port: int = 9222, only_positions: set[int] | None = None,
        campaign=None, inspect_ready=None, health_probe=None) -> dict:
    """Preflight exact Flash, recover to exactly verified Pro, then dispatch.

    No source claim may be created before an exact owned-tab model/Thinking
    gate passes. Generic login/timeout/editor failures do not authorize Pro.
    Every source job still passes the original global no-resend claim ledger.
    """
    from .source_review_autonomous_campaign import run as real_campaign
    campaign = real_campaign if campaign is None else campaign
    inspect_ready = (select_ready_existing_session if inspect_ready is None
                     else inspect_ready)
    plan_path = Path(plan_path).absolute()
    root = Path(root).absolute()
    if (not root.is_dir() or root.is_symlink() or not plan_path.is_file()
            or plan_path.is_symlink()
            or not isinstance(chrome_port, int) or type(max_jobs) is not int
            or not 0 <= max_jobs <= 6):
        raise AcademicReviewRouteError("Invalid independent G2 source-review paths/budget")
    plan = json.loads(plan_path.read_text(encoding="utf8"))
    source_sha = plan.get("source_sha256")
    if (not isinstance(source_sha, str) or len(source_sha) != 64
            or any(x not in "0123456789abcdef" for x in source_sha)):
        raise AcademicReviewRouteError("Missing source SHA on review plan")
    if max_jobs == 0:
        return {"status": "NO_MODEL_DISPATCH_BUDGET", "new_requests_attempted": 0,
                "jobs_completed": [], "jobs_not_rerun": [],
                "G2_approved": False, "student_publication_authorized": False}
    # The global no-resend inventory is authoritative BEFORE model preflight.
    # On older V1/V2 plans, check even one/two-unit source jobs: they, too,
    # may contain an obsolete frozen quotation packet. Version 3 is already
    # rebound to current source PDF evidence and its own prompt SHA.
    # A completely consumed source review should exit without opening Gemini
    # or rebuilding one previously claimed utterance.
    needs_quote_refresh=bool(
        campaign is real_campaign and
        plan.get("source_microbatch_revision") != 3)
    if needs_quote_refresh:
        from .academic_source_microbatch import unclaimed_microbatch_plan
        unsent=unclaimed_microbatch_plan(
            original_plan=plan_path,checkpoint_parent=root.parent)
        if not unsent["jobs"]:
            return {
                "status":"ALL_ORIGINAL_SOURCE_REVIEW_UNITS_ALREADY_CLAIMED_NO_SEND",
                "source_sha256":source_sha,
                "previous_consumed_units_excluded":
                    unsent["previous_consumed_units_excluded"],
                "remaining_original_unclaimed_units":0,
                "new_requests_attempted":0,
                "jobs_completed":[],"jobs_not_rerun":[],
                "G2_approved":False,"student_publication_authorized":False,
            }
    original = os.environ.get("MICROGEN_GEMINI_UI_MODE")
    original_model_id = os.environ.get("MICROGEN_LLM_MODEL")
    requested = configured_ui_mode()
    chosen = requested
    reason = "CONTRACT_REQUESTED_FAMILY_AVAILABLE"
    prior_route = root / RECEIPT_NAME
    try:
        if prior_route.exists():
            # A certified no-Send request may resume the SAME owned source
            # claim. Reuse its exact selected family instead of wasting two
            # fresh failed Flash account probes on every resumed invocation.
            # The actual model/Medium must still be re-observed before Send.
            if prior_route.is_symlink():
                raise AcademicReviewRouteError("Unsafe existing route receipt")
            prior = json.loads(prior_route.read_text(encoding="utf8"))
            if (prior.get("schema_version") != 1 or
                    prior.get("source_sha256") != source_sha or
                    prior.get("requested_model_family") != requested or
                    prior.get("selected_academic_model_family") not in ("flash","pro") or
                    prior.get("selected_thinking_level") != "medium" or
                    prior.get("G2_approved") is not False or
                    prior.get("model_family_equivalence_asserted") is not False or
                    type(prior.get("selected_chrome_port")) is not int):
                raise AcademicReviewRouteError("Untrusted source model-route checkpoint")
            chosen = prior["selected_academic_model_family"]
            reason = prior["route_reason"]
            # Existing no-reply evidence suppresses NEW academic Sends before
            # even opening the browser. A source-sized model response is not
            # proved healthy by merely finding its authenticated composer.
            from .academic_review_transport_circuit import inspect as health
            gate=health(checkpoint_parent=root.parent,
                        source_sha=source_sha,family=chosen)
            if (not gate["automatic_new_academic_model_send_allowed"]
                    and not gate.get("source_free_health_probe_due")):
                # A cooldown that has not expired is a safe, fully
                # automatic zero-Send stop. Once due, continue ONLY to
                # a verified *source-free* requalification, never straight
                # to a new original-PDF claim.
                return {"status":gate["status"],
                        "new_requests_attempted":0,
                        "jobs_completed":[],
                        "jobs_not_rerun":[],
                        "academic_transport_health":gate,
                        "G2_approved":False,
                        "student_publication_authorized":False}
            os.environ["MICROGEN_GEMINI_UI_MODE"] = chosen
            if chosen == "pro" and requested == "flash":
                os.environ["MICROGEN_LLM_MODEL"] = "gemini-3.1-pro"
            ready = inspect_ready(primary_port=prior["selected_chrome_port"])
        else:
            try:
                ready = inspect_ready(primary_port=chrome_port)
            except AcademicGeminiPreSendBlocked as failure:
                if (requested != "flash" or
                        failure.failure_phase != MISSING_FAMILY):
                    raise
                # Scoped source-review fallback ONLY; original lecture
                # generations retain their exact stage-model contract.
                os.environ["MICROGEN_GEMINI_UI_MODE"] = "pro"
                os.environ["MICROGEN_LLM_MODEL"] = "gemini-3.1-pro"
                chosen = "pro"
                reason = "FLASH_MISSING_ON_BOTH_AUTHORIZED_SESSIONS_PRO_MEDIUM"
                ready = inspect_ready(primary_port=chrome_port)
        if (ready.get("status") !=
                "EXACT_OWNED_GEMINI_MODEL_AND_THINKING_READY_NO_SEND"
                or ready.get("model_family") != chosen
                or ready.get("thinking_level") != "medium"
                or type(ready.get("verified_port")) is not int
                or ready.get("gemini_requests_submitted") != 0):
            raise AcademicReviewRouteError(
                "Exact selected academic model and Medium evidence not proven")
        from .academic_review_transport_circuit import inspect as health
        gate=health(checkpoint_parent=root.parent,
                    source_sha=source_sha,family=chosen)
        source_free_probe=None
        if (not gate["automatic_new_academic_model_send_allowed"]
                and gate.get("source_free_health_probe_due")):
            # Automatic normal-pipeline recovery after a real response
            # outage: probe ONE distinct, source-free, SHA-claimed Gemini
            # request on the independently verified SAME model+Medium
            # route. Do not burn any remaining original utterance claims
            # unless the resulting reply itself is trustworthy.
            from .academic_provider_requalification import probe_once
            try:
                source_free_probe=(health_probe or probe_once)(
                    checkpoint_parent=root.parent,source_sha=source_sha,
                    family=chosen,chrome_port=ready["verified_port"])
            except Exception as exc:
                return {
                    "status":"ACADEMIC_SOURCE_FREE_HEALTH_LOCAL_ERROR_NO_SOURCE_SEND",
                    "health_error_class":type(exc).__name__,
                    "new_requests_attempted":0,
                    "jobs_completed":[],"jobs_not_rerun":[],
                    "academic_transport_health":gate,
                    "G2_approved":False,
                    "student_publication_authorized":False,
                }
            gate=health(checkpoint_parent=root.parent,
                        source_sha=source_sha,family=chosen)
        if not gate["automatic_new_academic_model_send_allowed"]:
            return {"status":gate["status"],
                    "new_requests_attempted":0,
                    "jobs_completed":[],
                    "jobs_not_rerun":[],
                    "academic_transport_health":gate,
                    "academic_source_free_probe":source_free_probe,
                    "G2_approved":False,
                    "student_publication_authorized":False}
        receipt = {
            "schema_version": 1,
            "source_sha256": source_sha,
            "requested_model_family": requested,
            "selected_academic_model_family": chosen,
            "selected_thinking_level": "medium",
            "selected_chrome_port": ready["verified_port"],
            "route_reason": reason,
            "model_family_equivalence_asserted": False,
            "academic_model_sends_during_route": 0,
            "academic_approval": False,
            "element_tts_authorized": False,
            "G2_approved": False,
            "student_publication_authorized": False,
        }
        _new_verified_receipt(root, receipt)
        dispatch_plan=plan_path
        dispatch_root=root
        source_microbatch=None
        if needs_quote_refresh:
            # A short (<=2 units) original plan is NOT exempt from stale
            # quotation recovery. The current shared source extractor must
            # run for every unsent, original plan before a model Send.
            # Already-verified v3 plans retain their exact immutable prompt.

            from .academic_source_microbatch import ensure_microbatch_dispatch
            dispatch_plan,dispatch_root,source_microbatch=ensure_microbatch_dispatch(
                original_plan=plan_path,requested_root=root)
            # New short-job numbering belongs to the derived plan. An old
            # --only-job selector refers to the OLD uncut source job and
            # must NEVER silently select an unrelated short review unit.
            if only_positions is not None:
                return {**{
                    "status":"MICROBATCH_PLAN_READY_SELECT_NEW_JOB_INDEX",
                    "G2_approved":False,
                    "student_publication_authorized":False,
                    "new_requests_attempted":0,
                    "jobs_completed":[],
                    "microbatch_plan":str(dispatch_plan),
                    "microbatch_root":str(dispatch_root),
                    "remaining_unclaimed":source_microbatch[
                        "remaining_original_unclaimed_units"],
                },"academic_model_route":receipt}
        # One short synthetic success establishes only that the model can
        # return an attributable small answer; it does NOT prove source-
        # sized academic review health. Limit the first resumed campaign to
        # one distinct original source job, even if --max-new-jobs was 6.
        recovered_route=bool(
            gate.get("independent_source_free_reply_reverified"))
        # The proof may have been created in a prior invocation (or by
        # the source-free normal diagnostic). Keep the one-original-job cap
        # for every invocation of the requalified model, not just the
        # exact call that first generated the short canary.
        bounded_source_jobs=min(max_jobs,1) if recovered_route else max_jobs
        outcome = campaign(plan_path=dispatch_plan, root=dispatch_root,
                           max_jobs=bounded_source_jobs,
                           chrome_port=ready["verified_port"],
                           only_positions=only_positions)
        # A failed source-owned claim is preserved as a SHA-locked transport
        # health witness. Never infer an actual provider outage or retry the
        # consumed original utterances. Two distinct failures cause a finite
        # source+model-specific halt on subsequent ordinary invocations.
        failed=[x for x in outcome.get("jobs_not_rerun",[])
                if x.get("status")=="TRANSPORT_OR_VALIDATION_BLOCKED_NO_RETRY"]
        if failed:
            from .academic_review_transport_circuit import (
                record_original_failure, inspect as inspect_health)
            for item in failed:
                checkpoint=dispatch_root/("job_%02d_checkpoint" % item["job"])
                record_original_failure(
                    checkpoint=checkpoint,
                    route_receipt=root/RECEIPT_NAME,
                    checkpoint_parent=root.parent)
            gate=inspect_health(checkpoint_parent=root.parent,
                                source_sha=source_sha,family=chosen)
        # This wrapper cannot promote any substantive review finding.
        if outcome.get("G2_approved") is True:
            raise AcademicReviewRouteError(
                "Source-review transport cannot independently approve G2")
        extra={"academic_model_route":receipt,
               "academic_transport_health":gate,
               "bounded_original_source_jobs_budget":bounded_source_jobs}
        if source_free_probe is not None:
            # A synthetic health reply is NOT source academic approval.
            # Include its immutable evidence in the ordinary campaign report
            # for the next cross-session stage-health audit.
            extra["academic_source_free_probe"]=source_free_probe
        if source_microbatch is not None:
            extra["academic_microbatch"]={
                "plan_path":str(dispatch_plan),
                "root":str(dispatch_root),
                "prior_original_units_not_resent":source_microbatch[
                    "previous_consumed_units_excluded"],
                "remaining_before_dispatch":source_microbatch[
                    "remaining_original_unclaimed_units"],
                "G2_approved":False}
        return {**outcome,**extra}
    finally:
        if original is None:
            os.environ.pop("MICROGEN_GEMINI_UI_MODE", None)
        else:
            os.environ["MICROGEN_GEMINI_UI_MODE"] = original
        if original_model_id is None:
            os.environ.pop("MICROGEN_LLM_MODEL", None)
        else:
            os.environ["MICROGEN_LLM_MODEL"] = original_model_id


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--checkpoint-root", type=Path, required=True)
    parser.add_argument("--max-new-jobs", type=int, default=1)
    parser.add_argument("--chrome-port", type=int, default=9222)
    parser.add_argument("--only-job", type=int, action="append")
    args = parser.parse_args(argv)
    from .academic_provider_requalification import AcademicProbeError
    from .academic_review_transport_circuit import AcademicTransportCircuitError
    try:
        result = run(
            plan_path=args.plan, root=args.checkpoint_root,
            max_jobs=args.max_new_jobs, chrome_port=args.chrome_port,
            only_positions=set(args.only_job) if args.only_job else None)
    except (AcademicGeminiPreSendBlocked, AcademicReviewRouteError,
            AcademicProbeError, AcademicTransportCircuitError) as exc:
        # No arbitrary browser exception text, source document content,
        # account identity or prompt is emitted.
        result = {
            "status": "ACADEMIC_TRANSPORT_PREFLIGHT_BLOCKED_NO_SEND",
            "reason": (getattr(exc, "failure_phase", None)
                       or type(exc).__name__),
            "new_requests_attempted": 0, "G2_approved": False,
            "student_publication_authorized": False,
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    # A safely deferred health gate MUST NOT exit 0: a parent workflow may
    # otherwise mistake "no model Send" for "review stage completed".
    # This classification is distinct from a planned zero dispatch budget
    # or a successfully prepared immutable short-batch plan.
    if result.get("status") in {
        "ACADEMIC_GEMINI_SOURCE_FREE_REQUALIFICATION_REQUIRED",
        "ACADEMIC_GEMINI_RESPONSES_TEMPORARILY_SUSPENDED",
        "ACADEMIC_SOURCE_FREE_HEALTH_LOCAL_ERROR_NO_SOURCE_SEND",
    }:
        return 2
    # A failed once-claimed review is a nonzero orchestration result, NEVER
    # a positive scientific G2 acceptance or reason for a duplicate Send.
    return int(result.get("G2_approved") is False and
               not result.get("jobs_completed") and
               result.get("new_requests_attempted",0)>0)


if __name__ == "__main__":
    raise SystemExit(main())
