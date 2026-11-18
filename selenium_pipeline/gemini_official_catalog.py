"""Official *Gemini Apps* catalog discovery for owned Selenium routing.

Gemini API endpoint existence is NOT evidence a model is selectable in
gemini.google.com. Only Google's Gemini Apps Help may authorize a newly
named UI family; a live accessible option must independently confirm it.
Fetches only exact official URLs with bounded timeout and maintains a
content-addressed, atomic local cache. Never sends data to a provider.
"""
from __future__ import annotations

from datetime import datetime,timezone,timedelta
from hashlib import sha256
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import urllib.request
from urllib.parse import urlparse

HELP_URL="https://support.google.com/gemini/answer/18648722?hl=en"
API_URL="https://ai.google.dev/gemini-api/docs/models"
CACHE_TTL_HOURS=24
STALE_LIMIT_DAYS=7

# Capability classes are local task-routing policy, not Google benchmark
# measurements. In particular, the API endpoints are not UI entitlements.
MODEL_TIERS={
    "flash-lite":1,"hydrogen":2,"flash":2,
    "hydrogen-thinking":3,"pro":3,"argon":4,"carbon":5,
}
# Full label patterns anchor to one model name, not to menu descriptions.
MODEL_PATTERNS={
    "hydrogen-thinking":r"\b\d+(?:\.\d+)?\s+Hydrogen\s+Thinking\b",
    "hydrogen":r"\b\d+(?:\.\d+)?\s+Hydrogen\b(?!\s+Thinking)",
    "argon":r"\b(?:Gemini\s+)?\d+(?:\.\d+)?\s+Argon\b",
    "carbon":r"\b(?:Gemini\s+)?\d+(?:\.\d+)?\s+Carbon\b",
    "pro":r"\b(?:Gemini\s+)?(?:\d+(?:\.\d+)?\s+)?Pro\b",
    "flash":r"\b(?:Gemini\s+)?(?:\d+(?:\.\d+)?\s+)?Flash\b(?![\s-]*Lite)",
    "flash-lite":r"\bFlash[\s-]*Lite\b",
}
# Legacy known families remain in their existing strict selector when
# official access is transiently unavailable. NEVER authorize unknown model
# families by these fixed defaults.
LEGACY=frozenset(("flash","flash-lite","pro"))

class CatalogUnavailable(RuntimeError):
    pass

class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[]
        self.ignored=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","svg","noscript"):
            self.ignored+=1
        if tag in ("p","div","h1","h2","h3","li","td","tr","br"):
            self.parts.append(" ")
    def handle_endtag(self,tag):
        if tag in ("script","style","svg","noscript"):
            self.ignored=max(0,self.ignored-1)
        self.parts.append(" ")
    def handle_data(self,data):
        if not self.ignored:self.parts.append(data)

def _path():
    root=Path(os.getenv("LOCALAPPDATA") or Path.home()/".cache")
    return root/"MicroGen_AI_Web_Checkpoints"/"gemini_official_app_model_catalog_v1.json"

def _fetch(url,*,timeout=9):
    if url not in (HELP_URL,API_URL):raise CatalogUnavailable("Non-Google catalog URL")
    request=urllib.request.Request(url,headers={
        "User-Agent":"Mozilla/5.0 (compatible; MicroGenModelCatalog/1.0)",
        "Accept":"text/html"})
    with urllib.request.urlopen(request,timeout=timeout) as reply:
        final=urlparse(reply.geturl())
        if final.scheme!="https" or final.hostname!=urlparse(url).hostname:
            raise CatalogUnavailable("Redirect off approved official host")
        html=reply.read(2_600_001)
    if len(html)>2_600_000 or len(html)<500:
        raise CatalogUnavailable("Unexpected official catalog size")
    result=_Text()
    result.feed(html.decode("utf8",errors="replace"))
    plain=" ".join(" ".join(result.parts).split())
    if len(plain)<200:raise CatalogUnavailable("Official catalog empty")
    return plain,sha256(html).hexdigest()

def _now():
    return datetime.now(timezone.utc)

def _read_cached(path):
    if not path.is_file() or path.is_symlink() or path.stat().st_size>30_000:
        return None
    try:
        x=json.loads(path.read_text("utf8"))
        if (x["schema_version"]!=1 or x["app_url"]!=HELP_URL
                or not isinstance(x["verified_app_families"],list)
                or any(v not in MODEL_TIERS for v in x["verified_app_families"])
                or len(x["help_sha256"])!=64):
            return None
        born=datetime.fromisoformat(x["refreshed_at"])
        if born.tzinfo is None or born>_now()+timedelta(minutes=3):
            return None
        return x,born
    except (ValueError,KeyError,TypeError,OSError):
        return None

def official_ui_catalog(*,force=False,cache_path=None,fetch=None):
    """Fresh official help, or bounded stale official cache on network outage.

    Returns only verified family/URL/time/evidence. Never treats the API
    catalog as the browser's currently available model menu.
    """
    path=Path(cache_path) if cache_path else _path()
    cached=_read_cached(path)
    if cached and not force and _now()-cached[1]<timedelta(hours=CACHE_TTL_HOURS):
        return dict(cached[0],source_state="FRESH_VERIFIED_CACHE")
    fetcher=_fetch if fetch is None else fetch
    try:
        helptext,help_sha=fetcher(HELP_URL)
        if len(help_sha)!=64 or len(helptext)<200:
            raise CatalogUnavailable("Invalid app help evidence")
        model_names=[]
        for name,pattern in MODEL_PATTERNS.items():
            if re.search(pattern,helptext,flags=re.I):
                model_names.append(name)
        # The public document must contain an explicit Gemini Apps model
        # section. Otherwise an unrelated Google help redirect could create
        # false classifications.
        if ("Gemini" not in helptext or "model" not in helptext.casefold()
                or not {"hydrogen","flash-lite","pro"}.intersection(model_names)):
            raise CatalogUnavailable("No verifiable Gemini Apps model list")
        # API doc consulted for freshness/context only, not for UI authority.
        api_sha=None
        try:
            _,api_sha=fetcher(API_URL)
        except (OSError,TimeoutError,ValueError,CatalogUnavailable):
            pass
        output={
            "schema_version":1,"refreshed_at":_now().isoformat(),
            "app_url":HELP_URL,"help_sha256":help_sha,
            "api_url":API_URL,"api_sha256":api_sha,
            "verified_app_families":sorted(set(model_names)),
            "source_state":"FRESH_OFFICIAL_HELP",
        }
        path.parent.mkdir(parents=True,exist_ok=True)
        if path.is_symlink():
            raise CatalogUnavailable("Unsafe model catalog cache path")
        temp=path.with_suffix(".new")
        if temp.exists():raise CatalogUnavailable("Concurrent catalog refresh")
        with temp.open("x",encoding="utf8") as handle:
            json.dump({k:v for k,v in output.items() if k!="source_state"},
                      handle,sort_keys=True,indent=2)
            handle.flush();os.fsync(handle.fileno())
        os.replace(temp,path)
        return output
    except (OSError,TimeoutError,ValueError,CatalogUnavailable):
        if cached and _now()-cached[1]<=timedelta(days=STALE_LIMIT_DAYS):
            return dict(cached[0],source_state="BOUNDED_STALE_VERIFIED_CACHE")
        raise CatalogUnavailable("Official Gemini Apps catalog unavailable; unknown UI models forbidden")
