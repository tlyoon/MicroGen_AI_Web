"""Quarantine incomplete Gemini responses before browser-tab teardown.

Only the final visible model-response of the owned Gemini tab is sampled.
Never capture user prompt text, other browser tabs, credentials or screenshots.
Quarantined text is UNTRUSTED and must not be used as scientific approval.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets

MAX_CAPTURE_CHARS = 1_800_000

_LATEST_MODEL_ONLY = """
const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
const response = [...document.querySelectorAll('model-response')].filter(visible);
const element = response.length ? response[response.length - 1] : null;
const text = element ? (element.innerText || element.textContent || '') : '';
const generating = [...document.querySelectorAll('button')].some(
    b => visible(b) && /stop/i.test((b.getAttribute('aria-label') || ''))
);
return {text: String(text).slice(0, 1800000), generating: generating};
"""


def latest_owned_response(driver, owned_handle: str | None) -> dict:
    """Get latest model reply only, provided the browser owns this tab.

    If the owned handle is unknown, navigation changed, or DOM inspection fails,
    report no text rather than risking retrieval of unrelated chats.
    """
    empty = {"text": "", "generating": False, "capture_status": "unavailable"}
    if not owned_handle:
        return empty
    try:
        if driver.current_window_handle != owned_handle:
            return empty
        if not str(driver.current_url).startswith("https://gemini.google.com/"):
            return empty
        result = driver.execute_script(_LATEST_MODEL_ONLY)
        if not isinstance(result, dict):
            return empty
        txt = result.get("text")
        if not isinstance(txt, str):
            return empty
        return {
            "text": txt[:MAX_CAPTURE_CHARS],
            "generating": bool(result.get("generating")),
            "capture_status": "visible_model_response" if txt.strip() else "empty_model_response",
        }
    except Exception:
        return empty


def response_snapshot_with_scoped_copy(
    driver, owned_handle: str | None, *, copy_response=None,
) -> dict:
    """Prefer the longer vendor-verified response over a short DOM placeholder.

    The callback MUST be the vendor's response-scoped Copy helper, which
    validates response attribution. Never use a general clipboard paste
    or scan arbitrary page text.
    """
    snapshot = latest_owned_response(driver, owned_handle)
    if not owned_handle:
        return snapshot
    try:
        # Refuse Copy if user navigated away or our owned tab changed.
        if driver.current_window_handle != owned_handle:
            return snapshot
        if not str(driver.current_url).startswith("https://gemini.google.com/"):
            return snapshot
    except Exception:
        return snapshot
    if len(snapshot["text"].strip()) >= 120 or not callable(copy_response):
        return snapshot
    try:
        copied = copy_response(driver)
    except Exception:
        return snapshot
    if isinstance(copied, str) and len(copied.strip()) > max(
        len(snapshot["text"].strip()), 60
    ):
        return {
            "text": copied[:MAX_CAPTURE_CHARS],
            "generating": snapshot["generating"],
            "capture_status": "vendor_verified_response_copy",
        }
    return snapshot


def poll_existing_owned_response(
    read_snapshot, *, accept_fn, wait_s=45, poll_s=3,
    clock=None, sleep=None,
) -> tuple[str | None, dict]:
    """Observe ONLY the already submitted owned-tab response after strict capture fails.

    No prompt resend, tab creation, model switch, or browser-side click occurs
    here. In-progress replies are never accepted; once generation stops,
    complete schema-acceptable text may be returned for normal downstream
    source-validation. A changed/unowned tab fails closed.
    """
    import time
    if (not callable(read_snapshot) or not callable(accept_fn)
            or not isinstance(wait_s, (int, float)) or not 1 <= wait_s <= 90
            or not isinstance(poll_s, (int, float)) or not 0 < poll_s <= 10):
        raise ValueError("Bounded owned-response observation required")
    clock = clock or time.monotonic
    sleep = sleep or time.sleep
    deadline = clock() + wait_s
    last = {"text": "", "generating": False, "capture_status": "unavailable"}
    while True:
        current = read_snapshot()
        if not isinstance(current, dict):
            return None, last
        last = current
        if current.get("capture_status") not in (
                "visible_model_response", "empty_model_response",
                "vendor_verified_response_copy"):
            return None, last
        if not current.get("generating"):
            raw = current.get("text")
            if isinstance(raw, str) and raw.strip() and accept_fn(raw):
                return raw, last
            # A short model DOM placeholder can say "Gemini said" even
            # while the normal Stop control is absent. Keep observing the
            # *same* owned tab for the bounded grace; never submit again.
            # This is NOT evidence of a complete provider response.
        remaining = deadline - clock()
        if remaining <= 0:
            return None, last
        sleep(min(poll_s, remaining))



_SEND_METADATA_ONLY_JS = """
const editor=document.querySelector('[role="textbox"][contenteditable="true"]');
const buttons=[...document.querySelectorAll('button[aria-label="Send message"]')];
let visible=0;
for(const button of buttons){
  let e=button, hidden=false;
  while(e && e.nodeType===1){
    const style=getComputedStyle(e);
    if(style.display==='none'||style.visibility==='hidden'||
       Number(style.opacity)<=0.01){hidden=true;break;}
    e=e.parentElement;
  }
  if(!hidden)visible++;
}
return {doc_visible:document.visibilityState==='visible',
        composer_present:Boolean((editor?.innerText||'').trim()),
        send_count:buttons.length,visible_send_count:visible};
"""

def await_owned_gemini_send_visible(driver, owned_handle: str | None, *,
                                     wait_s: float=10, poll_s: float=0.5,
                                     clock=None, sleep=None) -> bool:
    """Observe ordinary Send visibility after Quill updates; NEVER force click.

    No content or other-tab data is read. Fail closed on changed browser ownership,
    unexpected page or no normal visible Send control. This does not submit.
    """
    import time
    if (not owned_handle or not 0<=wait_s<=20 or not 0<poll_s<=5):
        return False
    clock=clock or time.monotonic
    sleep=sleep or time.sleep
    deadline=clock()+wait_s
    while True:
        try:
            if (driver.current_window_handle!=owned_handle or
                not driver.current_url.startswith("https://gemini.google.com/")):
                return False
            state=driver.execute_script(_SEND_METADATA_ONLY_JS)
            if not isinstance(state,dict) or not state.get("doc_visible"):
                return False
            if (state.get("composer_present") is True and
                type(state.get("visible_send_count")) is int and
                state["visible_send_count"]>0):
                return True
            if not state.get("composer_present") or not state.get("send_count"):
                return False
        except Exception:
            return False
        remaining=deadline-clock()
        if remaining<=0:return False
        sleep(min(poll_s,remaining))


def default_quarantine_dir() -> Path:
    """A per-user local directory, never the textbook or cloned repo."""
    return Path(os.getenv("LOCALAPPDATA") or (Path.home() / ".cache")) / "Microvid" / "gemini_quarantine"


def quarantine_snapshot(snapshot: dict, *, directory: Path | None = None,
                        reason: str = "incomplete_json") -> dict:
    """Write no-overwrite untrusted text and hash-bound metadata for review.

    The files live only in a local user-owned directory. No automatic re-prompt,
    cleanup, publication, or approval occurs. Keep evidence on timeout even if
    the visible answer is empty; metadata accurately records that condition.
    """
    root = (directory or default_quarantine_dir()).expanduser().resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not root.is_dir():
        raise OSError("Recovery quarantine is not a directory")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    identifier = f"gemini_{stamp}_{secrets.token_hex(6)}"
    raw_path = root / f"{identifier}.raw.txt"
    meta_path = root / f"{identifier}.meta.json"
    raw = snapshot.get("text", "")
    if not isinstance(raw, str):
        raw = ""
    raw = raw[:MAX_CAPTURE_CHARS]
    payload = raw.encode("utf-8")
    sha = hashlib.sha256(payload).hexdigest()
    meta = {
        "schema_version": 1,
        "status": "incomplete_untrusted",
        "reason": str(reason)[:128],
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "capture_status": str(snapshot.get("capture_status", "unavailable"))[:64],
        "generation_active_at_capture": bool(snapshot.get("generating")),
        "model_response_chars": len(raw),
        "raw_sha256": sha,
        "raw_filename": raw_path.name,
        "not_scientifically_reviewed": True,
    }
    with raw_path.open("xb") as stream:
        stream.write(payload)
    with meta_path.open("x", encoding="utf-8") as stream:
        json.dump(meta, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    if os.name != "nt":
        raw_path.chmod(0o600)
        meta_path.chmod(0o600)
    return {"raw_path": raw_path, "meta_path": meta_path, **meta}


def read_quarantined_response(raw_file: Path) -> str:
    """Recover only a complete reply whose stored bytes match its receipt.

    A valid hash proves local file integrity, not the accuracy or completeness
    of Gemini's answer. Strict JSON and source/storyboard gates apply downstream.
    """
    raw_file = Path(raw_file)
    if raw_file.suffix != ".txt" or not raw_file.name.endswith(".raw.txt"):
        raise ValueError("Expected a .raw.txt quarantine artifact")
    meta_path = raw_file.with_name(raw_file.name[:-8] + ".meta.json")
    if not raw_file.is_file() or not meta_path.is_file():
        raise ValueError("Missing quarantine payload or metadata")
    if raw_file.stat().st_size > MAX_CAPTURE_CHARS * 4:
        raise ValueError("Oversized quarantine artifact")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if (meta.get("schema_version") != 1
            or meta.get("status") != "incomplete_untrusted"
            or meta.get("raw_filename") != raw_file.name):
        raise ValueError("Quarantine metadata is not trusted for recovery")
    payload = raw_file.read_bytes()
    if hashlib.sha256(payload).hexdigest() != meta.get("raw_sha256"):
        raise ValueError("Quarantine payload changed after capture")
    text = payload.decode("utf-8")
    if len(text) != meta.get("model_response_chars"):
        raise ValueError("Quarantine text length mismatch")
    return text
