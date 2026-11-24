"""Cross-campaign source-scoped post-Send browser-health invalidation.

A prior synthetic Neon/High health probe cannot justify more genuine
source-science Sends AFTER an independently owned Gemini Send became
SUBMITTED_OR_UNCERTAIN with no attributable model response. Require fresh
source-free model-health proof after that incident; daily claimed health
cannot be replayed or refreshed by relabeling an old receipt. Other
textbook sections' unrelated provider evidence remain independent.
"""
from __future__ import annotations

from pathlib import Path

from .academic_review_checkpoint import _load
from .g3_semantic_source_repair_v1 import _read,need
from .recovery_registry import lookup_mechanism

KIND="g3_post_send_health_invalidation"
SIGNATURE="G3_REGISTERED_SOURCE_SCIENCE_SEND_FAILED_AFTER_PREVIOUS_NEON_HEALTH"
MECHANISM="INVALIDATE_STALE_SOURCE_HEALTH_AND_REQUIRE_NEW_OWNED_HEALTH_PROOF"
MAX_TASKS_PER_SECTION=128
TASKS=(
    ("g3_distinct_semantic_science_tasks_v1",
     "g3_distinct_semantic_science_reviews_v1",
     "science_review_job"),
    ("g3_distinct_example_context_tasks_v1",
     "g3_distinct_example_context_reviews_v1",
     "review_job"),
    ("g3_prepass_source_gap_repair_v2",
     "g3_prepass_source_science_reviews_v1",
     "new_scientific_source_review_job"),
)
_UNCERTAIN={
    "SUBMITTED_OR_UNCERTAIN","NO_RESPONSE_UNRESOLVED",
    "LEGACY_SENT_NO_RESPONSE",
}


def latest_unresolved_incident(*,state_root:Path,section:str,
                               source_sha256:str)->float:
    need(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
         "Source-specific browser-health incident recovery not registered")
    root=Path(state_root).absolute()
    need(root.is_dir() and not root.is_symlink()
         and type(section) is str and section.startswith("Serway_")
         and len(source_sha256)==64
         and all(c in "0123456789abcdef" for c in source_sha256),
         "Missing original textbook identity for source browser health")
    last=0.0
    for task_dir,review_dir,job_field in TASKS:
        home=root/task_dir/section
        if not home.exists():
            continue
        need(home.is_dir() and not home.is_symlink(),
             "Unsafe source-owned task inventory")
        files=sorted(home.glob("*.json"))
        need(len(files)<=MAX_TASKS_PER_SECTION,
             "Unbounded original source-science task inventory")
        for file in files:
            task=_read(file)
            job=task.get(job_field)
            if job is None:
                continue
            need(type(job) is dict and job.get("source_sha256")==source_sha256,
                 "Original G3 science task changed source identity")
            scope=task.get("scope_sha256")
            need(type(scope) is str and len(scope)==64
                 and all(c in "0123456789abcdef" for c in scope),
                 "Original source review scope modified")
            prior=root/review_dir/scope
            if not prior.exists():
                continue
            need(prior.is_dir() and not prior.is_symlink(),
                 "Unsafe previous source-science reviewer owner")
            for phase in ("initial_request","challenge_request"):
                checkpoint=prior/phase
                if not checkpoint.exists():
                    continue
                need(checkpoint.is_dir() and not checkpoint.is_symlink(),
                     "Corrupted prior academic review claim")
                state=checkpoint/"request_state.json"
                if not state.is_file() or state.is_symlink():
                    # Treat broken/torn state as an incident, not as health.
                    last=max(last,checkpoint.stat().st_mtime)
                    continue
                record=_load(checkpoint)
                if record["status"] in _UNCERTAIN and not (
                    checkpoint/"model_response_identity.json").is_file():
                    last=max(last,state.stat().st_mtime)
    return last


def receipt_is_fresher(*,receipt:dict|None,incident_unix:float)->bool:
    if not isinstance(receipt,dict):
        return False
    return bool(
        receipt.get("fresh_neon_high_source_free_health") is True
        and receipt.get("status")=="G3_SOURCE_FREE_NEON_HIGH_HEALTH_VERIFIED"
        and type(receipt.get("observed_unix")) in (int,float)
        and receipt["observed_unix"]>incident_unix)
