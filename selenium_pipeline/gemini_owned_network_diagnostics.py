"""Passive resource-timing evidence from the exact owned Gemini browser tab.

This does NOT intercept traffic, reveal URLs, read response bodies, infer
provider outage, authorize a new model Send, or query another tab. Resource
timings alone cannot prove a PDF-bearing request was delivered to Gemini.
"""
from __future__ import annotations

MAX_COUNT=9999
_MECHANISM="READONLY_SAME_TAB_RESOURCE_TIMING_METADATA_NO_RETRY"
_SIGNATURE="OWNED_POST_SEND_RESOURCE_TIMING_MISSING"

# The only browser JS executed here is read-only. URL parsing is local to the
# browser and NO URL, path, query, host, credential, token or response text is
# returned to the Python process.
_RESOURCE_TIMING_JS=r"""
const n=x=>Math.min(9999, Math.max(0, Math.trunc(Number(x)||0)));
const timing=performance.getEntriesByType('resource');
const start=Number(arguments[0])||0;
const after=timing.filter(e=>e.startTime>start);
const counts={all_new_resources:n(after.length),same_origin_new_resources:0,
 gemini_api_new_resources:0,other_google_new_resources:0,
 fetch_xhr_new_resources:0,http_4xx_new_resources:0,
 http_5xx_new_resources:0,unknown_http_status_new_resources:0};
const origin=location.hostname.toLowerCase();
for(const e of after){
  let hostname='';
  try{hostname=new URL(e.name,location.href).hostname.toLowerCase();}catch(_){}
  if(hostname===origin)counts.same_origin_new_resources++;
  else if(hostname==='generativelanguage.googleapis.com' ||
          hostname==='alkalimakersuite-pa.clients6.google.com')
    counts.gemini_api_new_resources++;
  else if(hostname.endsWith('.google.com') ||
          hostname.endsWith('.googleapis.com'))counts.other_google_new_resources++;
  if(['fetch','xmlhttprequest'].includes(String(e.initiatorType).toLowerCase()))
    counts.fetch_xhr_new_resources++;
  const s=Number(e.responseStatus)||0;
  if(s>=400&&s<500)counts.http_4xx_new_resources++;
  if(s>=500&&s<600)counts.http_5xx_new_resources++;
  if(s===0)counts.unknown_http_status_new_resources++;
}
return {document_epoch_ms:Math.trunc(performance.timeOrigin),
        resource_entry_count:n(timing.length),
        latest_start_ms:Math.max(0, ...timing.slice(-25).map(e=>e.startTime)),
        ...counts};
"""

_COUNTERS=("all_new_resources","same_origin_new_resources",
           "gemini_api_new_resources","other_google_new_resources",
           "fetch_xhr_new_resources","http_4xx_new_resources",
           "http_5xx_new_resources","unknown_http_status_new_resources")
_STATUSES=frozenset(("OWNED_NETWORK_UNAVAILABLE","OWNED_NETWORK_NOT_GEMINI",
                     "OWNED_NETWORK_ROUTE_MISMATCH",
                     "OWNED_NETWORK_NO_BASELINE",
                     "OWNED_NETWORK_DOCUMENT_REPLACED",
                     "OWNED_NETWORK_RESOURCE_TIMING_OBSERVED",
                     "OWNED_NETWORK_NO_NEW_RESOURCE_TIMING"))


def _empty(status):
    return {"schema_version":1,"status":status,
            **{k:0 for k in _COUNTERS},
            "provider_outage_proven":False,
            "selector_defect_proven":False,
            "model_response_verified":False,
            "retry_authorized":False}


def sanitize_network_diagnostic(info):
    if (type(info) is not dict or info.get("schema_version")!=1
            or info.get("status") not in _STATUSES
            or not all(type(info.get(k)) is int and 0<=info[k]<=MAX_COUNT
                       for k in _COUNTERS)):
        return _empty("OWNED_NETWORK_UNAVAILABLE")
    return {"schema_version":1,"status":info["status"],
            **{k:info[k] for k in _COUNTERS},
            "provider_outage_proven":False,
            "selector_defect_proven":False,
            "model_response_verified":False,
            "retry_authorized":False}


def _owned(driver,handle,expected_url):
    try:
        if not handle or driver is None or driver.current_window_handle!=handle:
            return "OWNED_NETWORK_UNAVAILABLE"
        url=str(driver.current_url)
        if not url.startswith("https://gemini.google.com/"):
            return "OWNED_NETWORK_NOT_GEMINI"
        if expected_url is not None and (
            url.split("?",1)[0].split("#",1)[0] != expected_url):
            return "OWNED_NETWORK_ROUTE_MISMATCH"
        return None
    except Exception:
        return "OWNED_NETWORK_UNAVAILABLE"


def _registered():
    try:
        from .recovery_registry import lookup_mechanism
        return lookup_mechanism("owned_transport_diagnostic",_SIGNATURE)==_MECHANISM
    except (ValueError,OSError):
        return False


def arm_owned_network_baseline(driver,owned_handle):
    """Read timing BEFORE the one approved Send; no browser/network mutation."""
    if _owned(driver,owned_handle,None) is not None or not _registered():
        return None
    try:
        raw=driver.execute_script(_RESOURCE_TIMING_JS, 1.0e18)
        if (type(raw) is not dict
                or type(raw.get("document_epoch_ms")) is not int
                or raw["document_epoch_ms"]<=0
                or type(raw.get("latest_start_ms")) not in (int,float)
                or raw["latest_start_ms"]<0):
            return None
        return {"document_epoch_ms":raw["document_epoch_ms"],
                "latest_start_ms":float(raw["latest_start_ms"])}
    except Exception:
        return None


def observe_owned_network_timing(driver,owned_handle,*,baseline,
                                 expected_url=None):
    """No-Send inspect immediately after response failure in SAME owned tab."""
    blocked=_owned(driver,owned_handle,expected_url)
    if blocked is not None:
        return _empty(blocked)
    if not _registered():
        return _empty("OWNED_NETWORK_UNAVAILABLE")
    if (type(baseline) is not dict
            or type(baseline.get("document_epoch_ms")) is not int
            or type(baseline.get("latest_start_ms")) is not float
            or baseline["latest_start_ms"]<0):
        return _empty("OWNED_NETWORK_NO_BASELINE")
    try:
        raw=driver.execute_script(_RESOURCE_TIMING_JS,
                                  baseline["latest_start_ms"])
        if (type(raw) is not dict
                or type(raw.get("document_epoch_ms")) is not int
                or any(type(raw.get(k)) is not int
                       or not 0<=raw[k]<=MAX_COUNT for k in _COUNTERS)):
            return _empty("OWNED_NETWORK_UNAVAILABLE")
        if raw["document_epoch_ms"]!=baseline["document_epoch_ms"]:
            return _empty("OWNED_NETWORK_DOCUMENT_REPLACED")
        status=("OWNED_NETWORK_RESOURCE_TIMING_OBSERVED"
                if raw["all_new_resources"]>0 else
                "OWNED_NETWORK_NO_NEW_RESOURCE_TIMING")
        return sanitize_network_diagnostic(
            {"schema_version":1,"status":status,
             **{k:raw[k] for k in _COUNTERS}})
    except Exception:
        return _empty("OWNED_NETWORK_UNAVAILABLE")
