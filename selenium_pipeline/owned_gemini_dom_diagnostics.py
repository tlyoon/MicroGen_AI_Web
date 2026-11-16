"""Privacy-safe same-owned-Gemini-tab DOM provenance for failed responses.

No prompt, response text, URL, screenshots, token, HTML or other-tab data is
captured. The diagnostic is read-only and cannot establish Gemini backend
health or grant permission to resend an already claimed source request.
"""
from __future__ import annotations


# Use only count/length metadata; never return node text or HTML. Existence
# of a semantic assistant node is an investigative hint, not source authority.
_OWNED_RESPONSE_METADATA_JS = """
const visible = e => Boolean(e) && Boolean(
  e.offsetWidth || e.offsetHeight || e.getClientRects().length);
const model = [...document.querySelectorAll('model-response')];
const shown = model.filter(visible);
const assistant = [...document.querySelectorAll(
  '[data-message-author-role="assistant"],[data-author-role="model"],[role="article"][data-role="model"]'
)].filter(visible);
const nodes = shown.flatMap(e => [...e.querySelectorAll(
  'message-content .markdown, .model-response-text .markdown, .markdown'
)].filter(visible));
const last = nodes.length ? nodes[nodes.length - 1]
           : shown.length ? shown[shown.length - 1] : null;
const stop = [...document.querySelectorAll('button')].filter(
  e => visible(e) && /stop/i.test(e.getAttribute('aria-label') || ''));
const count = x => Math.min(9999, Number(x) || 0);
return {
  model_response_nodes: count(model.length),
  visible_model_response_nodes: count(shown.length),
  visible_model_markdown_nodes: count(nodes.length),
  visible_assistant_semantic_nodes: count(assistant.length),
  model_answer_text_length: count(last
      ? String(last.innerText || last.textContent || '').length : 0),
  visible_stop_controls: count(stop.length)
};
"""

_KEYS = (
    "model_response_nodes", "visible_model_response_nodes",
    "visible_model_markdown_nodes", "visible_assistant_semantic_nodes",
    "model_answer_text_length", "visible_stop_controls",
)
_STATUSES = frozenset({
    "OWNED_DOM_UNAVAILABLE", "OWNED_DOM_NOT_GEMINI",
    "OWNED_DOM_ROUTE_MISMATCH", "OWNED_DOM_MODEL_ELEMENTS_ABSENT",
    "OWNED_DOM_ALTERNATE_ASSISTANT_PRESENT",
    "OWNED_DOM_MODEL_ELEMENTS_EMPTY", "OWNED_DOM_MODEL_TEXT_PRESENT",
})


def _empty(status: str) -> dict:
    return {"schema_version": 1, "status": status,
            **{k: 0 for k in _KEYS},
            "provider_outage_proven": False,
            "selector_defect_proven": False,
            "academic_approval": False,
            "retry_authorized": False}


def sanitize_dom_diagnostic(obj) -> dict:
    """Allowlist serialization; discard arbitrary browser or test input."""
    if type(obj) is not dict or obj.get("status") not in _STATUSES:
        return _empty("OWNED_DOM_UNAVAILABLE")
    if obj.get("schema_version") != 1:
        return _empty("OWNED_DOM_UNAVAILABLE")
    if not all(type(obj.get(k)) is int and 0 <= obj[k] <= 9999 for k in _KEYS):
        return _empty("OWNED_DOM_UNAVAILABLE")
    return {"schema_version": 1, "status": obj["status"],
            **{k: obj[k] for k in _KEYS},
            "provider_outage_proven": False,
            "selector_defect_proven": False,
            "academic_approval": False,
            "retry_authorized": False}


def observe_owned_dom_metadata(driver, owned_handle: str | None, *,
                               expected_url: str | None = None) -> dict:
    """Inspect only an independently owned, current, optionally route-locked tab.

    IMPORTANT: a URL or valid structured reply from another Gemini chat
    cannot validate this original uncertain Send.
    """
    if not owned_handle or driver is None:
        return _empty("OWNED_DOM_UNAVAILABLE")
    # The diagnostic itself is a versioned, code-reviewed, *read-only*
    # recovery handler. If its registry entry has been retired or changed,
    # keep the normal quarantine but collect no unverified DOM metadata.
    try:
        from .recovery_registry import lookup_mechanism
        registered = lookup_mechanism(
            "owned_transport_diagnostic",
            "OWNED_POST_SEND_RESPONSE_MISSING")
        if registered != "READONLY_SAME_TAB_RESPONSE_DOM_METADATA_NO_RETRY":
            return _empty("OWNED_DOM_UNAVAILABLE")
    except (ValueError, OSError):
        return _empty("OWNED_DOM_UNAVAILABLE")
    try:
        if driver.current_window_handle != owned_handle:
            return _empty("OWNED_DOM_UNAVAILABLE")
        url = str(driver.current_url)
        if not url.startswith("https://gemini.google.com/"):
            return _empty("OWNED_DOM_NOT_GEMINI")
        if (expected_url is not None and
                url.split("?", 1)[0].split("#", 1)[0] != expected_url):
            return _empty("OWNED_DOM_ROUTE_MISMATCH")
        info = driver.execute_script(_OWNED_RESPONSE_METADATA_JS)
        if type(info) is not dict or not all(
                type(info.get(k)) is int and 0 <= info[k] <= 9999
                for k in _KEYS):
            return _empty("OWNED_DOM_UNAVAILABLE")
        if info["visible_model_response_nodes"] == 0:
            status = ("OWNED_DOM_ALTERNATE_ASSISTANT_PRESENT"
                      if info["visible_assistant_semantic_nodes"] > 0 else
                      "OWNED_DOM_MODEL_ELEMENTS_ABSENT")
        elif info["model_answer_text_length"] == 0:
            status = "OWNED_DOM_MODEL_ELEMENTS_EMPTY"
        else:
            status = "OWNED_DOM_MODEL_TEXT_PRESENT"
        return sanitize_dom_diagnostic({
            "schema_version": 1, "status": status, **info})
    except Exception:
        return _empty("OWNED_DOM_UNAVAILABLE")
