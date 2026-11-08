"""Source-verified, read-only citation candidates for every academic review.

Candidates are genuine, spatially coherent quotes from the ORIGINAL PDF.
They are *not* academic proof or approval, and a model may select a quote only
for the exact original utterance whose candidate list contains it.
No model requests, file mutations, OCR, semantic rewriting or user intervention.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from functools import lru_cache
import json
from pathlib import Path
import re

import pymupdf

from .figure_source_identity import _sha, require
from .pdf_text_source_span_witness import prove_source_quote_occurrence

_STOP = frozenset(
    "about above after again along also among another around because before "
    "being below between could does during each every from have into itself "
    "more other over only same should some such than that their them there "
    "these this those through under until using very what when where which "
    "while with would your will then finally example examples first second "
    "third many often also next begin beginning means".split()
)
_MAX_PAGES = 24
_MAX_WORD_LINES = 1200
_MAX_CANDIDATES_PER_UTTERANCE = 2
_MAX_QUOTE_CHARS = 200


def _terms(text: str) -> set[str]:
    return {
        t for t in re.findall(r"[a-zA-Z]{4,}", text.lower())
        if t not in _STOP
    }


@lru_cache(maxsize=8)
def _line_catalog(source_path: str, expected_sha256: str) -> tuple:
    """Untrusted text lines; each chosen quote is verified before publication."""
    source = Path(source_path)
    require(source.is_file() and not source.is_symlink() and
            _sha(source) == expected_sha256,
            "Source identity drift before building academic citation packet")
    lines = []
    with pymupdf.open(source) as pdf:
        require(1 <= len(pdf) <= _MAX_PAGES,
                "Citation extraction requires bounded source PDF; do not guess")
        for physical_page, page in enumerate(pdf, 1):
            groups = defaultdict(list)
            for word in page.get_text("words", sort=True):
                groups[(word[5], word[6])].append(word)
            for words in groups.values():
                if not 2 <= len(words) <= 30:
                    continue
                # Preserve independently valid shorter quotations on compact
                # physical lines. A legitimate independent challenger may
                # quote "visible equation" where the first reviewer cited
                # "A visible equation"; historical two-pass consensus permits
                # both only if each is exactly witnessed by the original PDF.
                alternatives = [words]
                if (3 <= len(words) <= 6
                    and (len(str(words[0][4]).strip(".,:;()")) < 4
                         or str(words[0][4]).lower().strip(".,:;()") in _STOP)):
                    alternatives.append(words[1:])
                for option in alternatives:
                    quote = " ".join(str(word[4]) for word in option)
                    if 8 <= len(quote) <= _MAX_QUOTE_CHARS and _terms(quote):
                        physical_bbox = (
                            round(min(word[0] for word in option), 3),
                            round(min(word[1] for word in option), 3),
                            round(max(word[2] for word in option), 3),
                            round(max(word[3] for word in option), 3),
                        )
                        lines.append((physical_page, quote,
                                      frozenset(_terms(quote)), physical_bbox))
                    require(len(lines) <= _MAX_WORD_LINES,
                            "Unbounded source PDF quote lines; fail before model Send")
    require(_sha(source) == expected_sha256,
            "Academic source PDF changed during quote candidate scan")
    return tuple(lines)


def build_verified_source_candidates(*, folder: Path, job: dict) -> dict:
    """Bound candidate *identities* to the source+slides+script+utterances."""
    folder = Path(folder).absolute()
    source = folder / "source.pdf"
    require(folder.is_dir() and not folder.is_symlink()
            and type(job) is dict
            and type(job.get("slides")) is list
            and len(job["slides"]) <= 4,
            "Only bounded original academic review jobs may have quote lists")
    original_sha = job["source_sha256"]
    for file, field in (("source.pdf", "source_sha256"),
                        ("slides.pdf", "slides_sha256"),
                        ("script.txt", "script_sha256")):
        require(_sha(folder / file) == job[field],
                "Original PDF/slide/narration hash changed before quote packet")

    catalogue = _line_catalog(str(source), original_sha)
    counts = Counter(term for _page, _quote, terms, _bbox in catalogue
                     for term in terms)
    selected = []
    cached_proofs = {}
    for slide in job["slides"]:
        for unit in slide["utterances"]:
            original_terms = _terms(unit["spoken_text"])
            ranked = []
            for page, quote, terms, physical_bbox in catalogue:
                intersection = original_terms & terms
                if not intersection:
                    continue
                # Avoid first-page/early-line bias and repeated generic words:
                # rare matching terms score higher, but none constitutes proof.
                score = sum(1.0 / (1.0 + counts[t]) for t in intersection)
                ranked.append((score, len(intersection), page,
                               quote, physical_bbox))
            ranked.sort(key=lambda t: (-t[0], -t[1], t[2], t[3]))
            choices = []
            seen = set()
            for _score, _n, page, quote, physical_bbox in ranked[:30]:
                pair = (page, quote)
                if pair in seen:
                    continue
                seen.add(pair)
                if pair not in cached_proofs:
                    try:
                        proof = prove_source_quote_occurrence(
                            source_pdf=source,
                            expected_sha256=original_sha,
                            page_number=page,
                            verbatim_quote=quote)
                    except (ValueError, RuntimeError, OSError):
                        proof = None
                    cached_proofs[pair] = proof
                if cached_proofs[pair] is None:
                    continue
                choices.append({
                    "source_page": page,
                    "verbatim_source_quote": quote,
                    "quote_sha256": cached_proofs[pair]["quote_sha256"],
                    "source_text_bbox_pdf_pt": list(physical_bbox),
                })
                if len(choices) >= _MAX_CANDIDATES_PER_UTTERANCE:
                    break
            selected.append({
                "utterance_id": unit["id"],
                "spoken_sha256": unit["spoken_sha256"],
                "allowed_citations": choices,
            })

    for file, field in (("source.pdf", "source_sha256"),
                        ("slides.pdf", "slides_sha256"),
                        ("script.txt", "script_sha256")):
        require(_sha(folder / file) == job[field],
                "Original source changed during academic citation preparation")
    payload = {
        "status": "PHYSICALLY_WITNESSED_SOURCE_CITATIONS_V1",
        "source_sha256": job["source_sha256"],
        "slides_sha256": job["slides_sha256"],
        "script_sha256": job["script_sha256"],
        "utterances": selected,
        "citations_are_scientific_proof": False,
        "all_mathematics_verified": False,
        "student_publication_authorized": False,
    }
    require(len(json.dumps(payload, ensure_ascii=False)) <= 13000,
            "Too many source citation candidates for bounded academic prompt")
    return payload


def verify_witnessed_candidate(*, job: dict, utterance: dict,
                               guess: dict, source_pdf: Path) -> bool:
    """Never accept a model-created or cross-utterance quotation as verified."""
    packet = job.get("verified_source_quote_candidates_v1")
    if packet is None:
        return False  # compatibility with trusted legacy fixtures only
    require(packet.get("status") == "PHYSICALLY_WITNESSED_SOURCE_CITATIONS_V1"
            and all(packet.get(name + "_sha256") == job[name + "_sha256"]
                    for name in ("source", "slides", "script")),
            "Stale or altered source quote packet")
    entry = next(
        (x for x in packet["utterances"]
         if x["utterance_id"] == utterance["id"]), None)
    require(entry is not None
            and entry.get("spoken_sha256") == utterance["spoken_sha256"],
            "Source quote candidates not bound to original spoken utterance")
    page, quote = guess.get("source_page"), guess.get("verbatim_source_quote")
    if page is None and quote is None:
        return False
    require(any(
        x["source_page"] == page and x["verbatim_source_quote"] == quote
        for x in entry["allowed_citations"]),
        "Model supplied an unverified or cross-utterance source quotation")
    proof = prove_source_quote_occurrence(
        source_pdf=source_pdf, expected_sha256=job["source_sha256"],
        page_number=page, verbatim_quote=quote)
    expected = next(
        x["quote_sha256"] for x in entry["allowed_citations"]
        if x["source_page"] == page and x["verbatim_source_quote"] == quote)
    require(proof["quote_sha256"] == expected,
            "Citation proof differs from original independently verified candidate")
    return True
