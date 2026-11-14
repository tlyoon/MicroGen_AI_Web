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
# A single physical line or adjacent pair cannot cite a multi-step
# explanation that crosses three or more textbook lines. Longer quotes
# remain *alternatives*, not mathematical proof or automatic approval.
_MAX_PARAGRAPH_QUOTE_CHARS = 460
_MAX_CONTIGUOUS_QUOTE_LINES = 5
_MAX_EXPANDED_LINE_WINDOWS = 2600


def _section_scope_first_page(page, source: Path) -> float | None:
    """Ignore preceding-section carryover before a witnessed target heading.

    Chapter extracts often start half way through a *previous* section on
    page one. The source folder's numeric subchapter identity is advisory:
    filter only when an exact physical section heading matches it. The PDF
    and heading retain their original SHA, no OCR or inferred math.
    """
    label = source.parent.name.strip()
    if not re.fullmatch(r"\d{1,2}\.\d{1,3}", label):
        return None
    headings = []
    for block in page.get_text("blocks"):
        if len(block) < 5 or not isinstance(block[4], str):
            continue
        value = " ".join(block[4].split())
        if (20 <= len(value) <= 120
                and re.match(re.escape(label) + r"\s+[A-Za-z]", value)
                and not re.match(r"^\d+\.\d+\s+Figure\b", value)
                and float(block[1]) >= 45):
            headings.append(float(block[1]))
    # Multiple apparent headings are ambiguous. Never guess the boundary.
    return headings[0] if len(headings) == 1 else None


def _publisher_navigation(quote: str) -> bool:
    """Do not rank textbook website/assessment-navigation as physics evidence."""
    q = quote.lower()
    return any(x in q for x in (
        "additional assessment items",
        "see the preface for an explanation of the icons",
        "go to www.",
        "for online homework",
    ))


def _source_model_sections(source: Path, expected_sha256: str) -> dict[int, tuple]:
    """Physically witness ordered numbered subsection headings in original PDF.

    Model labels are a retrieval SCOPE, never physics semantics. A slide with
    one unambiguous title 'Model N: ...' can search inside that numbered source
    section, rather than unrelated exercises / other regimes. Ambiguous or
    missing markers disable scope filtering; they cannot create false proof.
    """
    markers=[]
    with pymupdf.open(source) as pdf:
        for page_number, page in enumerate(pdf,1):
            for block in page.get_text("blocks"):
                if len(block)<5 or not isinstance(block[4],str):
                    continue
                clean=" ".join(block[4].split())
                m=re.match(r"(?i)^model\s+(\d{1,2})\s*:",clean)
                if m and 20 <= len(clean) <= 1400:
                    markers.append((int(m.group(1)),page_number,
                                    float(block[1])))
        last=len(pdf)+1
    require(_sha(source)==expected_sha256,
            "Original source changed while mapping physical subheadings")
    if (len(markers)<2
            or len({x[0] for x in markers})!=len(markers)
            or markers!=sorted(markers,key=lambda x:(x[1],x[2]))
            or [x[0] for x in markers]!=list(range(
                markers[0][0],markers[0][0]+len(markers)))):
        return {}  # no reliable subsection boundary inferred
    result={}
    for i,(number,first_page,first_y) in enumerate(markers):
        if i+1<len(markers):
            _n,stop_page,stop_y=markers[i+1]
        else:
            stop_page,stop_y=last,0.0
        result[number]=(first_page,first_y,stop_page,stop_y)
    return result


def _source_example_sections(source: Path, expected_sha256: str) -> dict[tuple, tuple]:
    """Restrict numbered worked/conceptual examples by actual PDF headings.

    An Example 6.8 slide must never cite a nearby Example 6.9 solution merely
    because both mention terminal speed. Scan only heading starts, not figure
    captions, and enable boundaries only for unambiguous consecutive labels.
    """
    markers=[]
    with pymupdf.open(source) as pdf:
        total=len(pdf)
        for physical_page,page in enumerate(pdf,1):
            for block in page.get_text("blocks"):
                if len(block)<5 or not isinstance(block[4],str):
                    continue
                value=" ".join(block[4].split())
                match=re.match(
                    r"(?i)^(?:conceptual\s+)?example\s+(\d{1,2})\.(\d{1,3})\s+",
                    value)
                if match and 20<=len(value)<=1400:
                    markers.append(((int(match.group(1)),int(match.group(2))),
                                    physical_page,float(block[1])))
    require(_sha(source)==expected_sha256,
            "Source changed while extracting physical numbered examples")
    if (len(markers)<2
            or len({x[0] for x in markers})!=len(markers)
            or markers!=sorted(markers,key=lambda x:(x[1],x[2]))
            or any(current[0][0]!=following[0][0]
                   or current[0][1]+1!=following[0][1]
                   for current,following in zip(markers,markers[1:]))):
        return {}
    results={}
    for i,(key,page,y) in enumerate(markers):
        stop=(markers[i+1][1],markers[i+1][2]
              ) if i+1<len(markers) else (total+1,0.)
        results[key]=(page,y,*stop)
    return results


def _slide_example_title(slide: dict) -> tuple[int,int] | None:
    """Only the actual title PDF text bbox may claim the numbered example."""
    labels=[]
    for row in slide.get("visual_targets",[]):
        if (type(row) is not dict
                or type(row.get("visible_text")) is not str
                or type(row.get("bbox_pdf_pt")) is not list
                or len(row["bbox_pdf_pt"])!=4
                or not 6<=row["bbox_pdf_pt"][1]<=46):
            continue
        name=" ".join(row["visible_text"].split())
        match=re.match(
            r"(?i)^(?:conceptual\s+)?example\s+(\d{1,2})\.(\d{1,3})\s*:",
            name)
        if match:
            labels.append((int(match.group(1)),int(match.group(2))))
    return labels[0] if len(labels)==1 else None


def _slide_model_title(slide: dict) -> int | None:
    """Only a physical slide HEADER matching a model label constrains search."""
    headings=[]
    for row in slide.get("visual_targets",[]):
        if (type(row) is not dict
                or type(row.get("visible_text")) is not str
                or type(row.get("bbox_pdf_pt")) is not list
                or len(row["bbox_pdf_pt"])!=4):
            continue
        bbox=row["bbox_pdf_pt"]
        if not (6 <= bbox[1] <= 46):
            continue
        m=re.match(r"(?i)^model\s+(\d{1,2})\s*:",
                   " ".join(row["visible_text"].split()))
        if m:
            headings.append(int(m.group(1)))
    return headings[0] if len(headings)==1 else None


def _within_physical_model_scope(page: int, bbox: tuple,
                                 scope: tuple) -> bool:
    start_page,start_y,end_page,end_y=scope
    if not (start_page<=page<=end_page):
        return False
    if page==start_page and bbox[1]<start_y-1.0:
        return False
    if page==end_page and bbox[3]>end_y+1.0:
        return False
    return True


def _retrieval_lexeme(word: str) -> str:
    """Regular English inflections for SEARCH RANKING ONLY, not citation truth.

    A lecture may ask about 'terminal speeds and time constants' while the
    source describes 'terminal speed' and 'time constant'. Exact-match
    retrieval otherwise prefers an irrelevant table about 'speeds'. Preserve
    negation, operators, scientific sign/domain words, and every literal
    quoted byte: this function is never used in source proof or AI grading.
    """
    if word.endswith("ies") and len(word) >= 6:
        return word[:-3] + "y"  # velocities -> velocity
    if word.endswith("sses") and len(word) >= 6:
        return word[:-2]       # masses -> mass
    if (word.endswith("s") and len(word) >= 5
            and not word.endswith(("ss", "us", "is"))):
        return word[:-1]       # speeds, constants, spheres
    return word


def _search_words(text: str) -> list[str]:
    return [_retrieval_lexeme(w)
            for w in re.findall(r"[A-Za-z]{4,}", text.casefold())
            if w not in _STOP]


def _content_pairs(text: str) -> set[tuple[str,str]]:
    """Conservative inflected phrase SEARCH signals, never physics proof."""
    tokens=_search_words(text)
    return set(zip(tokens,tokens[1:]))


def _same_physical_quote_region(a: tuple, b: tuple) -> bool:
    """Avoid wasting both source slots on overlapping slices of one paragraph."""
    if a[0]!=b[0]:
        return False
    x0,y0,x1,y1=a[1]
    p0,q0,p1,q1=b[1]
    intersection=max(0,min(x1,p1)-max(x0,p0))*max(
        0,min(y1,q1)-max(y0,q0))
    area_a=(x1-x0)*(y1-y0)
    area_b=(p1-p0)*(q1-q0)
    return bool(area_a>0 and area_b>0 and
                intersection / min(area_a,area_b) >= .55)


def _numeric_tokens(text: str) -> set[str]:
    """Only conservative literal numeric tokens; no spoken-number conversion."""
    return {n for n in re.findall(
        r"(?<![a-zA-Z0-9])\d+(?:\.\d+)?(?![a-zA-Z0-9])", text)
        if len(n) >= 2 or "." in n}


def _terms(text: str) -> set[str]:
    # These are *retrieval* lexemes only. The original, unchanged exact
    # publisher text, geometry and SHA are checked independently afterwards.
    return set(_search_words(text))


@lru_cache(maxsize=8)
def _line_catalog(source_path: str, expected_sha256: str) -> tuple:
    """Untrusted text lines; each chosen quote is verified before publication."""
    source = Path(source_path)
    require(source.is_file() and not source.is_symlink() and
            _sha(source) == expected_sha256,
            "Source identity drift before building academic citation packet")
    lines = []
    expanded = []
    with pymupdf.open(source) as pdf:
        require(1 <= len(pdf) <= _MAX_PAGES,
                "Citation extraction requires bounded source PDF; do not guess")
        for physical_page, page in enumerate(pdf, 1):
            # Preserve actual section scope when the extracted PDF begins
            # with carryover text from the preceding textbook subchapter.
            # A different folder layout or ambiguous title fails OPEN as
            # a retrieval filter, never as mathematical/academic approval.
            first_section_y = (
                _section_scope_first_page(page, source)
                if physical_page == 1 else None)
            groups = defaultdict(list)
            for word in page.get_text("words", sort=True):
                if (first_section_y is not None
                        and float(word[3]) < first_section_y - 1.0):
                    continue
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
                    if (8 <= len(quote) <= _MAX_QUOTE_CHARS
                            and _terms(quote) and not _publisher_navigation(quote)):
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
            # A scientifically relevant equation explanation often crosses
            # two physical source lines. Include strictly consecutive lines
            # from ONE original PDF text block as review-only candidates.
            # The independent spatial/word witness below still decides which
            # of these exact physical sequences really constitute a quote.
            by_block = defaultdict(list)
            for (block_id, line_id), words in sorted(groups.items()):
                if 1 <= len(words) <= 30:
                    by_block[block_id].append((line_id, words))
            for rows in by_block.values():
                for start in range(len(rows)):
                    current = []
                    for offset in range(_MAX_CONTIGUOUS_QUOTE_LINES):
                        j = start + offset
                        if j >= len(rows):
                            break
                        line_id, words = rows[j]
                        if (not words or (offset and (
                                rows[j-1][0] + 1 != line_id
                                or abs(float(words[0][1]) -
                                       float(rows[j-1][1][0][1])) > 28
                                or abs(float(words[0][0]) -
                                       float(rows[j-1][1][0][0])) > 90))):
                            break
                        current.extend(words)
                        if offset == 0:
                            continue  # Single physical lines are above.
                        quote = " ".join(str(w[4]) for w in current)
                        limit = (_MAX_QUOTE_CHARS if offset == 1
                                 else _MAX_PARAGRAPH_QUOTE_CHARS)
                        if len(quote) > limit:
                            break
                        if (not (20 <= len(quote) and _terms(quote))
                                or _publisher_navigation(quote)):
                            continue
                        bbox = (round(min(w[0] for w in current), 3),
                                round(min(w[1] for w in current), 3),
                                round(max(w[2] for w in current), 3),
                                round(max(w[3] for w in current), 3))
                        if len(expanded) >= _MAX_EXPANDED_LINE_WINDOWS:
                            break
                        expanded.append((physical_page, quote,
                                         frozenset(_terms(quote)), bbox))
    require(_sha(source) == expected_sha256,
            "Academic source PDF changed during quote candidate scan")
    return tuple(lines + expanded)


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
    # Exact physical numbered headings, not utterance similarity, determine
    # whether a slide's model subsection has an unambiguous source window.
    model_scopes = _source_model_sections(source, original_sha)
    example_scopes = _source_example_sections(source, original_sha)
    counts = Counter(term for _page, _quote, terms, _bbox in catalogue
                     for term in terms)
    numeric_counts = Counter(number for _page, quote, _terms_found, _bbox
                             in catalogue for number in _numeric_tokens(quote))
    selected = []
    cached_proofs = {}
    for slide in job["slides"]:
        model_number = _slide_model_title(slide)
        example_number = _slide_example_title(slide)
        # A physically witnessed exact Example 6.8 heading takes priority
        # over a broad model subsection. Unmatched/ambiguous headings fall
        # back to existing conservative full-PDF quote retrieval.
        source_scope = (example_scopes.get(example_number)
                        if example_number is not None
                        else model_scopes.get(model_number))
        visible_by_id = {target["id"]: target.get("visible_text", "")
                         for target in slide.get("visual_targets", [])
                         if type(target) is dict and type(target.get("id")) is str}
        for unit in slide["utterances"]:
            original_terms = _terms(unit["spoken_text"])
            # The physically rendered slide can retain numerals (e.g.
            # 980, 0.900, 75) that speech renders as words. Treat these as
            # SEARCH HINTS only, never an approved numeric equivalence.
            visible = " ".join(visible_by_id.get(t, "")
                               for t in unit.get("ranked_candidates", [])[:3])
            visible_terms = _terms(visible)
            numeric_query = _numeric_tokens(visible) | _numeric_tokens(
                unit["spoken_text"])
            # Longer scientific reasoning needs *coverage of the actual
            # spoken claim*, not just one rare word or a nearby equation
            # number. Search rewards exact ordered content phrases but never
            # equates lexical overlap with scientific truth.
            spoken_pairs = _content_pairs(unit["spoken_text"])
            ranked = []
            for page, quote, terms, physical_bbox in catalogue:
                if (source_scope is not None
                        and not _within_physical_model_scope(
                            page, physical_bbox, source_scope)):
                    continue
                intersection = original_terms & terms
                visible_hits = visible_terms & terms
                numbers = numeric_query & _numeric_tokens(quote)
                if not (intersection or visible_hits or numbers):
                    continue
                # Exact phrase overlap plus claim coverage dominate generic
                # frequency/numeric hints. Source page model scope is a
                # physical chapter-heading boundary, not an academic verdict.
                lexical_coverage = len(intersection) / max(1,len(original_terms))
                ordered_coverage = len(
                    spoken_pairs & _content_pairs(quote)) / max(1,len(spoken_pairs))
                score = (
                    5.0 * lexical_coverage + 3.0 * ordered_coverage
                    + .20 * sum(1.0/(1.0+counts[t]) for t in intersection)
                    + .18 * sum(1.0/(1.0+counts[t]) for t in visible_hits)
                    + .12 * sum(1.0/(1.0+numeric_counts[n]) for n in numbers)
                )
                ranked.append((score, len(intersection) + len(visible_hits)
                               + len(numbers), page, quote, physical_bbox))
            ranked.sort(key=lambda t: (-t[0], -t[1], t[2], t[3]))
            choices = []
            seen = set()
            used_regions = []
            # Prefer two distinct physical derivation regions. When the
            # source contains only ONE pertinent region, retain its exact
            # shorter/subspan variant as a fallback for independent reviewers
            # (without inventing a second page or pretending it is proof).
            for prefer_new_region in (True, False):
                for _score, _n, page, quote, physical_bbox in ranked[:100]:
                    pair = (page, quote)
                    if pair in seen:
                        continue
                    if prefer_new_region and any(
                            _same_physical_quote_region(
                                (page,physical_bbox),previous)
                            for previous in used_regions):
                        continue
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
                    seen.add(pair)
                    choices.append({
                        "source_page": page,
                        "verbatim_source_quote": quote,
                        "quote_sha256": cached_proofs[pair]["quote_sha256"],
                        "source_text_bbox_pdf_pt": list(physical_bbox),
                    })
                    used_regions.append((page,physical_bbox))
                    if len(choices) >= _MAX_CANDIDATES_PER_UTTERANCE:
                        break
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
    # Large batches must not become unreviewable merely because the
    # evidence finder located longer, better source passages. Preserve one
    # physically witnessed candidate for every utterance where available;
    # remove the most expensive *second* citation deterministically until
    # the existing bounded Gemini prompt contract is satisfied.
    def packet_chars() -> int:
        return len(json.dumps(payload, ensure_ascii=False))
    while packet_chars() > 13000:
        optional = [(len(c["verbatim_source_quote"]), i)
                    for i, row in enumerate(selected)
                    for c in row["allowed_citations"][1:]]
        require(bool(optional),
                "At least one source citation per utterance exceeds bounded prompt")
        _size, index = max(optional)
        selected[index]["allowed_citations"].pop()
    require(packet_chars() <= 13000,
            "Source citation packet size remains invalid")
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
