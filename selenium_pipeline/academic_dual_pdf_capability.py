"""One-shot synthetic dual-PDF Gemini transport qualification after TWO lost reviews.

A short, text-only canary is insufficient evidence that the same browser,
model and source-upload transport can answer a two-PDF academic prompt.
This probe uploads only two GENERATED, NON-SOURCE PDF documents with hidden
tokens, requires the model to read both, validates an owned one-Send reply,
and preserves its exclusive claim across process restarts. It cannot approve
scientific evidence, audio, release or the original uncertain requests.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time

from .academic_provider_requalification import _REGISTERED
from .figure_source_identity import require

ROOT = ".microgen_g2_dual_pdf_capability_v1"
MAX_PROBES_PER_DAY_PER_SOURCE = 1
MAX_RECEIPT_BYTES = 8000


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _load(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink()
            and 0 < path.stat().st_size <= MAX_RECEIPT_BYTES,
            "Missing/linked/invalid Gemini dual PDF capability evidence")
    obj = json.loads(path.read_text(encoding="utf8"))
    require(type(obj) is dict and obj.get("schema_version") == 1,
            "Invalid Gemini PDF capability receipt schema")
    return obj


def _new(path: Path, obj: dict) -> None:
    require(not path.exists() and not path.is_symlink(),
            "Never overwrite a claimed Gemini diagnostic Send")
    with path.open("x", encoding="utf8") as file:
        json.dump(obj, file, sort_keys=True, indent=2)
        file.write("\n")
        file.flush()
        os.fsync(file.fileno())


def _values(source_sha: str, family: str, incident: str) -> tuple[str, str, str]:
    salt = f"MicroGen-Dual-PDF-Source-Free-v1|{source_sha}|{family}|{incident}"
    nonce = _sha((salt + "|nonce").encode("ascii"))[:18]
    a = _sha((salt + "|attachment-A").encode("ascii"))[:18].upper()
    b = _sha((salt + "|attachment-B").encode("ascii"))[:18].upper()
    return nonce, a, b


def _request(nonce: str) -> str:
    return (
        "MicroGen source-free Gemini PDF-reading transport test. This is NOT "
        "an academic textbook request and contains NO user source material. "
        "Read BOTH attached synthetic one-page PDF files. Each PDF has a "
        "different line beginning with PDF_CODE: . Read the code from the "
        "file named SyntheticA.pdf into field a and from SyntheticB.pdf into "
        "field b. No speculation: if you cannot read both PDFs reply with "
        "an error, which will NOT pass this test. Return ONLY one JSON object "
        'with exactly these three keys: {"probe":"' + nonce +
        '","a":"<code from SyntheticA.pdf>","b":"<code from SyntheticB.pdf>"}. '
        "No markdown fences, no explanations, no other content."
    )


def _exact(raw: str, expected: dict) -> bool:
    if type(raw) is not str or not 15 <= len(raw) <= 1024:
        return False
    def unique(pairs):
        obj = {}
        for k, v in pairs:
            if k in obj:
                raise ValueError("Duplicate response JSON key")
            obj[k] = v
        return obj
    try:
        return json.loads(raw.strip(), object_pairs_hook=unique) == expected
    except (ValueError, TypeError, UnicodeError):
        return False


def _verify_unsafe_source_claims(*, queue_root: Path, source_sha: str,
                                  prior_slides: list[int],
                                  family: str) -> tuple[str, float]:
    q = Path(queue_root).absolute()
    require(q.is_dir() and not q.is_symlink()
            and re.fullmatch(r"[0-9a-f]{64}", source_sha) is not None
            and family in ("flash", "pro")
            and type(prior_slides) is list
            and 2 <= len(prior_slides) <= 100
            and all(type(x) is int and 1 <= x <= 200 for x in prior_slides)
            and prior_slides == sorted(set(prior_slides)),
            "PDF probe only applies to two distinct source-bound unresolved Sends")
    verified = []
    for slide in prior_slides[-2:]:
        cp = q / f"slide_{slide:03d}_initial_review_attempt_01_request"
        state_path = cp / "request_state.json"
        sent = cp / "dispatch_attempted.claim"
        require(cp.is_dir() and not cp.is_symlink()
                and state_path.is_file() and not state_path.is_symlink()
                and sent.is_file() and not sent.is_symlink()
                and not (cp / "model_response_identity.json").exists(),
                "Source Send has no unambiguous immutable one-Send claim")
        state = json.loads(state_path.read_text(encoding="utf8"))
        fingerprint = state.get("request_fingerprint")
        require(state.get("source_sha256") == source_sha
                and state.get("status") in {
                    "SUBMITTED_OR_UNCERTAIN", "NO_RESPONSE_UNRESOLVED",
                    "LEGACY_SENT_NO_RESPONSE"}
                and state.get("submission_may_have_occurred") is True
                and state.get("can_auto_retry") is False
                and state.get("student_publication_authorized") is False
                and type(fingerprint) is str
                and re.fullmatch(r"[0-9a-f]{64}", fingerprint) is not None
                and sent.read_text(encoding="utf8").strip() == fingerprint,
                "Unrelated, possibly replayable or foreign scientific request")
        verified.append((slide, fingerprint, state_path.stat().st_mtime))
    incident_raw = json.dumps(
        {"source_sha": source_sha, "family": family,
         "original_claims": [[i, f] for i, f, _ in verified]},
        sort_keys=True, separators=(",", ":")).encode("ascii")
    return _sha(incident_raw), max(x[2] for x in verified)


def _home(*, checkpoint_parent: Path, source_sha: str,
          family: str, incident: str) -> Path:
    root = Path(checkpoint_parent).absolute()
    require(root.is_dir() and not root.is_symlink()
            and re.fullmatch(r"[0-9a-f]{64}", source_sha)
            and re.fullmatch(r"[0-9a-f]{64}", incident)
            and family in ("flash", "pro"),
            "PDF capability must use exact safe source/model checkpoint scope")
    child = root / ROOT / source_sha / family / incident
    require(not any(p.is_symlink() for p in (
        root / ROOT, root / ROOT / source_sha,
        root / ROOT / source_sha / family, child)),
        "Linked PDF capability receipt directory")
    return child


def _expected(source_sha: str, family: str, incident: str) -> dict:
    nonce, a, b = _values(source_sha, family, incident)
    return {"probe": nonce, "a": a, "b": b}


def _verify_saved(slot: Path, source_sha: str, family: str,
                  incident: str, after: float, now: float) -> dict | None:
    claim_path = slot / "claim.json"
    result_path = slot / "result.json"
    if not claim_path.exists():
        return None
    c = _load(claim_path)
    require(c.get("source_sha256") == source_sha
            and c.get("model_family") == family
            and c.get("incident_sha256") == incident
            and c.get("last_uncertain_claim_unix") == after
            and c.get("original_source_uploaded") is False
            and c.get("two_synthetic_pdf_attachments") is True
            and c.get("one_send_only") is True,
            "Original incident and PDF capability claim do not match")
    if not result_path.exists():
        return {"status": "PRIOR_SYNTHETIC_PDF_SEND_UNCERTAIN_NO_RESEND",
                "new_provider_requests": 0, "new_source_review_send_allowed": False}
    r = _load(result_path)
    require(r.get("claim_sha256") == _sha(claim_path.read_bytes())
            and r.get("source_sha256") == source_sha
            and r.get("model_family") == family
            and r.get("incident_sha256") == incident
            and type(r.get("observed_unix")) in (int, float)
            and c["last_uncertain_claim_unix"] < r["observed_unix"] <= now + 3
            and r.get("original_source_uploaded") is False
            and r.get("academic_approval") is False
            and r.get("paid_operations_authorized") is False,
            "PDF capability result is unrelated, stale, future or unsafe")
    if r.get("status") == "DUAL_SYNTHETIC_PDF_RESPONSE_VERIFIED":
        expected = _expected(source_sha, family, incident)
        require(r.get("gemini_new_user_turn_verified") is True
                and r.get("send_registration_status") in _REGISTERED
                and r.get("model_response_json") == expected,
                "Saved synthetic dual-PDF model response is not attributable")
        return {**r, "new_provider_requests": 0,
                "new_source_review_send_allowed": True}
    require(r.get("status") == "DUAL_SYNTHETIC_PDF_RESPONSE_UNVERIFIED"
            and r.get("model_response_json") is None
            and r.get("gemini_new_user_turn_verified") is False,
            "Synthetic two-PDF probe cannot silently assert verification")
    return {**r, "new_provider_requests": 0,
            "new_source_review_send_allowed": False}


def qualifying_proof(*, queue_root: Path, checkpoint_parent: Path,
                     source_sha: str, prior_slides: list[int],
                     family: str, now: float | None = None) -> dict | None:
    instant = float(time.time() if now is None else now)
    incident, after = _verify_unsafe_source_claims(
        queue_root=queue_root, source_sha=source_sha,
        prior_slides=prior_slides, family=family)
    slot = _home(checkpoint_parent=checkpoint_parent,
                 source_sha=source_sha, family=family, incident=incident)
    proof = _verify_saved(slot, source_sha, family, incident, after, instant)
    if proof and proof.get("new_source_review_send_allowed") is True:
        return proof
    # A consumed unsuccessful v1 request is immutable. A distinct, separately
    # claimed v2 transport test is eligible only after registered primary
    # profile repair, with exact old incident/result identity checked by v2.
    if proof is not None and family == "pro":
        from .academic_dual_pdf_profile_repair_v2 import qualifying_proof as v2_proof
        return v2_proof(queue_root=queue_root, checkpoint_parent=checkpoint_parent,
                        source_sha=source_sha, prior_slides=prior_slides,
                        family=family, now=now)
    return None


def existing_outcome(*, queue_root: Path, checkpoint_parent: Path,
                     source_sha: str, prior_slides: list[int],
                     family: str, now: float | None = None) -> dict | None:
    """Read-only: distinguish unattempted PDF probe from an already consumed one.

    Do not create new recovery stages or provider calls merely because a prior
    synthetic Gemini Send returned no attributable response.
    """
    instant = float(time.time() if now is None else now)
    incident, after = _verify_unsafe_source_claims(
        queue_root=queue_root,source_sha=source_sha,
        prior_slides=prior_slides,family=family)
    slot=_home(checkpoint_parent=checkpoint_parent,
               source_sha=source_sha,family=family,incident=incident)
    return _verify_saved(slot,source_sha,family,incident,after,instant)


def _create_pdf(path: Path, code: str, label: str) -> str:
    """Build a valid, deterministic single-page PDF using only Python stdlib.

    The CI Windows runner intentionally has no ReportLab installation.
    This limited generator contains no arbitrary user text or PDF parser:
    code and label are fixed safe ASCII, and the cross-reference offsets are
    computed on the exact bytes written. An external PDF reader must still
    confirm that the hidden code can be extracted from each attachment.
    """
    require(not path.exists() and not path.is_symlink()
            and re.fullmatch(r"[0-9A-F]{18}", code) is not None
            and label in ("A", "B"), "Unsafe synthetic PDF parameters")
    content = (
        "BT /F1 17 Tf 65 700 Td "
        "(MicroGen synthetic diagnostic file " + label + ") Tj ET\n"
        "BT /F1 14 Tf 65 650 Td (PDF_CODE: " + code + ") Tj ET\n"
        "BT /F1 12 Tf 65 620 Td "
        "(No user or textbook source material.) Tj ET\n"
    ).encode("ascii")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
         b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        (b"<< /Length " + str(len(content)).encode("ascii") +
         b" >>\nstream\n" + content + b"endstream"),
    ]
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for idx, body in enumerate(objs, start=1):
        offsets.append(len(pdf))
        pdf.extend(str(idx).encode("ascii") + b" 0 obj\n" +
                   body + b"\nendobj\n")
    cross_ref_start = len(pdf)
    pdf.extend(b"xref\n0 6\n0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend((b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n" +
                str(cross_ref_start).encode("ascii") + b"\n%%EOF\n"))
    raw = bytes(pdf)
    require(raw.startswith(b"%PDF-1.4") and 200 < len(raw) < 20000,
            "Synthetic PDF malformed")
    with path.open("xb") as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())
    return _sha(raw)


PRESEND_SIGNATURE = "V1_DUAL_PDF_CLAIM_BURNED_ON_RETIRED_GEMINI_MODEL"
PRESEND_MECHANISM = "REQUIRE_EXACT_OWNED_MODEL_THINKING_BEFORE_V1_SYNTHETIC_CLAIM"


def _production_probe_presend_ready(family: str) -> dict:
    """Zero Send and zero original source upload BEFORE a unique diagnostic claim.

    Reuse the same owned-tab academic model and Medium Thinking verifier as
    the already-repaired v2 probe. The actual v1 browser transport uses 9222,
    so a verified alternate account never licenses a Send on the primary.
    """
    from .recovery_registry import lookup_mechanism
    require(lookup_mechanism("presend_capability_repair",
                             PRESEND_SIGNATURE) == PRESEND_MECHANISM,
            "V1 Gemini synthetic PDF pre-claim recovery disabled")
    from .academic_queue_fresh_send_health import _full_family_scope
    from .academic_gemini_presend_preflight import (
        select_ready_existing_session, AcademicGeminiPreSendBlocked)
    try:
        with _full_family_scope(family):
            result = select_ready_existing_session(
                primary_port=9222, allow_active_alternate=False)
    except AcademicGeminiPreSendBlocked as error:
        return {"status": "V1_SYNTHETIC_PDF_PRESEND_UNAVAILABLE_NO_CLAIM",
                "failure_phase": error.failure_phase,
                "new_provider_requests": 0,
                "new_source_review_send_allowed": False}
    except Exception:
        # Do not leak model screenshots, account labels, prompts or credentials.
        return {"status": "V1_SYNTHETIC_PDF_PRESEND_UNAVAILABLE_NO_CLAIM",
                "failure_phase": "PRESEND_VERIFICATION_FAILED",
                "new_provider_requests": 0,
                "new_source_review_send_allowed": False}
    passed = (
        isinstance(result, dict)
        and result.get("verified_port") == 9222
        and result.get("model_family") == family
        and result.get("thinking_level") == "medium"
        and result.get("gemini_requests_submitted") == 0
        and result.get("files_uploaded") == 0
        and result.get("model_prompt_typed") is False
        and result.get("student_publication_authorized") is False
        and result.get("G2_approved") is False
    )
    return {
        "status": ("EXACT_SYNTHETIC_PDF_MODEL_PRESEND_VERIFIED_NO_SEND"
                   if passed else "V1_SYNTHETIC_PDF_PRESEND_UNAVAILABLE_NO_CLAIM"),
        "failure_phase": (None if passed else "PRESEND_EVIDENCE_MISMATCH"),
        "new_provider_requests": 0,
        "new_source_review_send_allowed": False,
    }


def probe_once(*, queue_root: Path, checkpoint_parent: Path,
               source_sha: str, prior_slides: list[int], family: str,
               now: float | None = None, transport=None) -> dict:
    """One new, provenance-bound, synthetic PDF Send; repeat calls only inspect."""
    instant = float(time.time() if now is None else now)
    incident, after = _verify_unsafe_source_claims(
        queue_root=queue_root, source_sha=source_sha,
        prior_slides=prior_slides, family=family)
    require(after < instant and 0 < instant < 4102444800,
            "Cannot probe against a future/unverified original review claim")
    slot = _home(checkpoint_parent=checkpoint_parent,
                 source_sha=source_sha, family=family, incident=incident)
    prior = _verify_saved(slot, source_sha, family, incident, after, instant)
    if prior is not None:
        return prior
    root = slot.parent
    day = datetime.fromtimestamp(instant, timezone.utc).strftime("%Y%m%d")
    if root.exists():
        claims = list(root.glob("*/claim.json"))
        require(len(claims) <= 20, "Unbounded synthetic probe claims")
        today = sum(_load(path).get("utc_day") == day for path in claims)
        if today >= MAX_PROBES_PER_DAY_PER_SOURCE:
            return {"status": "SYNTHETIC_PDF_DAILY_BUDGET_EXHAUSTED",
                    "new_provider_requests": 0,
                    "new_source_review_send_allowed": False}
    require(not slot.exists() and not slot.is_symlink(),
            "Synthetic probe claim must never overwrite a prior incident")
    if transport is None:
        presend = _production_probe_presend_ready(family)
        if presend["status"] != (
                "EXACT_SYNTHETIC_PDF_MODEL_PRESEND_VERIFIED_NO_SEND"):
            # Crucial: no slot, PDFs, intent, Send claim, daily-budget usage
            # or source upload is created when the requested family is gone.
            return presend
    slot.mkdir(parents=True)
    expected = _expected(source_sha, family, incident)
    a = slot / "SyntheticA.pdf"
    b = slot / "SyntheticB.pdf"
    a_sha = _create_pdf(a, expected["a"], "A")
    b_sha = _create_pdf(b, expected["b"], "B")
    prompt = _request(expected["probe"])
    require(expected["a"] not in prompt and expected["b"] not in prompt
            and len(prompt) <= 1500, "Synthetic source markers leaked into prompt")
    claim = {"schema_version": 1, "source_sha256": source_sha,
             "model_family": family, "incident_sha256": incident,
             "utc_day": day, "claimed_unix": instant,
             "last_uncertain_claim_unix": after,
             "prompt_sha256": _sha(prompt.encode("utf8")),
             "pdf_a_sha256": a_sha, "pdf_b_sha256": b_sha,
             "original_source_uploaded": False,
             "two_synthetic_pdf_attachments": True, "one_send_only": True}
    _new(slot / "claim.json", claim)
    registered = None
    valid = False
    error_type = None
    try:
        if transport is None:
            from .academic_queue_fresh_send_health import _full_family_scope
            from .series_gemini import _browser_request
            with _full_family_scope(family):
                response = _browser_request(
                    prompt, [a, b], port=9222, wait_cap_s=160,
                    min_chars=20, accept_fn=lambda raw:_exact(raw, expected))
        else:
            response = transport(prompt, [a, b])
        from .series_gemini import OwnedGeminiResponse
        valid = (isinstance(response, OwnedGeminiResponse)
                 and response.gemini_new_user_turn_verified is True
                 and response.gemini_send_registration_status in _REGISTERED
                 and _exact(str(response), expected))
        if valid:
            registered = response.gemini_send_registration_status
    except Exception as exc:
        error_type = type(exc).__name__
    observed = float(time.time() if now is None else instant + 0.01)
    receipt = {"schema_version": 1, "claim_sha256":
               _sha((slot / "claim.json").read_bytes()),
               "source_sha256": source_sha, "model_family": family,
               "incident_sha256": incident, "observed_unix": observed,
               "status": ("DUAL_SYNTHETIC_PDF_RESPONSE_VERIFIED" if valid
                          else "DUAL_SYNTHETIC_PDF_RESPONSE_UNVERIFIED"),
               "send_registration_status": registered,
               "gemini_new_user_turn_verified": valid,
               "model_response_json": expected if valid else None,
               "error_type": error_type, "original_source_uploaded": False,
               "academic_approval": False, "paid_operations_authorized": False}
    _new(slot / "result.json", receipt)
    saved = _verify_saved(slot, source_sha, family, incident, after,
                          max(instant + 1, observed))
    return {**saved, "new_provider_requests": 1} if saved else {
        "status": "DUAL_SYNTHETIC_PDF_RESPONSE_UNVERIFIED",
        "new_provider_requests": 1, "new_source_review_send_allowed": False}
