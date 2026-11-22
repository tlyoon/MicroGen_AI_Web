"""Source-pinned 1-to-N / M-to-N YouTube and Office DOCX publication recovery.

Safe, provider-independent primitives for the existing authorized YouTube/
Google Drive publication workflow. No OAuth, network or destructive operation
is performed here. Never declare full G3/highlight acceptance from narrated
MP4 technical QA alone. Every outside operation must provide readback proof.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
import re
import zipfile
import io
from lxml import etree as ET

from .youtube_publication_recovery import PublicationRecoveryBlocked, safe_retirement_ids


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise PublicationRecoveryBlocked(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1048576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding="utf8"))
    _need(type(obj) is dict, "INVALID_SOURCE_ACCEPTANCE_JSON")
    return obj


def ordered_narrated_parts(folder: Path, *, explicit_skip_highlight_qa: bool) -> list[dict]:
    """Honor exactly the accepted manifest, never invent part count or join.

    A narrated-video-only run is permitted ONLY with an explicit caller scope.
    It neither certifies synchronized visual highlights nor writes a general
    G3 completion receipt. Existing 11.2/11.4 historical video-length control
    may retain its original completion receipts.
    """
    folder = Path(folder)
    _need(folder.is_dir(), "SOURCE_SUBSECTION_NOT_FOUND")
    _need((folder / "source.pdf").is_file()
          and (folder / "slides.pdf").is_file()
          and (folder / "script.txt").is_file(),
          "MISSING_SOURCE_LECTURE_CHAIN")
    manifest_file = next((folder / name for name in
         ("lecture_parts_manifest.json", "slides_parts_manifest.json")
         if (folder / name).is_file()), None)
    _need(manifest_file is not None, "AUTHORITATIVE_VIDEO_PART_MANIFEST_MISSING")
    manifest = _read_json(manifest_file)
    qa = _read_json(folder / "tts_fidelity_report.json")
    summary = qa.get("summary", {})
    _need(type(summary.get("slides")) is int and summary["slides"] > 0
          and summary.get("passed") == summary["slides"]
          and summary.get("blocking_failures") == 0
          and summary.get("review") == 0,
          "ACOUSTIC_QA_NOT_ACCEPTED")
    _need(manifest.get("source_sha256") == sha256_file(folder / "source.pdf"),
          "MANIFEST_ORIGINAL_SOURCE_HASH_CHANGED")
    parts = manifest.get("parts")
    _need(type(parts) is list and 1 <= len(parts) <= 100
          and manifest.get("total_parts", len(parts)) == len(parts),
          "MANIFEST_PARTS_MISSING_OR_INCOMPLETE")

    technical = manifest.get("technical_only") is True or (
        manifest.get("independent_visual_highlight_acceptance") in
        ("not_proven", "not_performed_user_skipped"))
    technical = technical or manifest.get("status") == "technical_length_control_passed"
    if technical:
        _need(explicit_skip_highlight_qa, "HIGHLIGHT_QA_NOT_ACCEPTED")
    else:
        # Don't convert an unknown manifest into full visual QA approval.
        _need(explicit_skip_highlight_qa or
              manifest.get("independent_visual_highlight_acceptance") is True,
              "VISUAL_HIGHLIGHT_ACCEPTANCE_NOT_PROVEN")
    for name in ("slides.pdf", "script.txt"):
        _need((folder / name).stat().st_size > 256, "EMPTY_LECTURE_ASSET")

    result = []
    for index, entry in enumerate(parts, start=1):
        _need(type(entry) is dict, "INVALID_MANIFEST_ENTRY")
        file_name = entry.get("filename", entry.get("file", entry.get("name")))
        # Stable and bounded names, never path traversal.
        _need(type(file_name) is str and bool(re.fullmatch(
           r"slides(?:_part\d{2})?\.mp4", file_name)), "UNSAFE_VIDEO_FILENAME")
        file = folder / file_name
        _need(file.is_file() and not file.is_symlink()
              and file.stat().st_size >= 100000, "MISSING_OR_TOO_SMALL_VIDEO")
        _need(sha256_file(file) == entry.get("sha256"),
              "VIDEO_HASH_MISMATCH")
        seconds = entry.get("duration_seconds", entry.get("seconds"))
        _need(type(seconds) in (float, int) and 0 < seconds < 600,
              "VIDEO_DURATION_OUTSIDE_SIX_HUNDRED_SECONDS")
        result.append({
            "part_number": index,
            "parts_total": len(parts),
            "filename": file_name,
            "sha256": entry["sha256"],
            "duration_seconds": seconds,
            "bytes": file.stat().st_size,
        })
    names = [x["filename"] for x in result]
    _need(len(names) == len(set(names)), "DUPLICATE_VIDEO_PART_FILENAME")
    # Both the established slides.mp4 + part02, and zero/one-based partXX
    # naming schemes exist. Ordering comes from the authoritative manifest.
    if names[0] == "slides.mp4":
        expected = ["slides.mp4"] + [
            f"slides_part{i:02d}.mp4" for i in range(2, len(names)+1)]
        _need(names == expected, "MIXED_OR_MISORDERED_VIDEO_PART_NAMES")
    else:
        suffixes = [int(re.fullmatch(r"slides_part(\d{2})\.mp4",name).group(1))
                    if re.fullmatch(r"slides_part(\d{2})\.mp4",name)
                    else -999 for name in names]
        _need(suffixes == list(range(suffixes[0], suffixes[0]+len(suffixes)))
              and suffixes[0] in (0,1),
              "NONCONTIGUOUS_OR_UNRECOGNIZED_PART_NUMBERING")
    if explicit_skip_highlight_qa:
        # An explicit technical-only acceptance receipt is required for newly
        # completed slides, even when a video has a decodable file container.
        narrow = folder / ".microgen_narrated_video_chain.json"
        if narrow.is_file():
            report = _read_json(narrow)
            _need(report.get("full_g3_release_accepted") is False and
                  report.get("independent_visual_highlight_acceptance") == "not_performed"
                  and report.get("original_source_pdf_sha256") ==
                  manifest["source_sha256"] and
                  report.get("slides_pdf_sha256") == sha256_file(folder/"slides.pdf") and
                  report.get("script_txt_sha256") == sha256_file(folder/"script.txt") and
                  report.get("tts_qa_report_sha256") ==
                  sha256_file(folder/"tts_fidelity_report.json") and
                  [(x.get("filename"),x.get("sha256")) for x in report.get("video_parts",[])] ==
                  [(x["filename"],x["sha256"]) for x in result],
                  "NARRATED_TECHNICAL_RECEIPT_STALE")
        else:
            legacy = _read_json(folder / ".microgen_completion.json")
            _need(legacy.get("source_sha256") == manifest["source_sha256"],
                  "LEGACY_VIDEO_RECEIPT_STALE")
    return result


def full_replacement_plan(
    subsection: str, old_ids: Sequence[str], title: str,
    parts: Sequence[Mapping[str, object]],
) -> list[dict]:
    """Create complete N-part replacement intents for M superseded videos."""
    _need(bool(re.fullmatch(r"\d{1,2}\.\d{1,2}", subsection)),
          "INVALID_SUBSECTION_KEY")
    _need(bool(old_ids) and len(set(old_ids)) == len(old_ids)
          and all(re.fullmatch(r"[\w-]{11}", v) for v in old_ids),
          "INVALID_OLD_VIDEO_SET")
    _need(bool(parts) and all(p.get("parts_total") == len(parts) and
          p.get("part_number") == i
          for i,p in enumerate(parts,start=1)), "PARTS_NOT_CONTIGUOUS")
    titles = [(f"{subsection} {title} (Part {i} of {len(parts)})"
                if len(parts)>1 else f"{subsection} {title}")
              for i in range(1,len(parts)+1)]
    _need(all(len(t)<=100 for t in titles), "YOUTUBE_TITLE_EXCEEDS_LIMIT")
    return [{
        "subsection":subsection, "old_video_ids":list(old_ids),
        "display_part":i, "part_count":len(parts), "title":titles[i-1],
        "source_filename":p["filename"], "source_sha256":p["sha256"],
        "new_video_id":None, "publication_state":"PREPARED"
    } for i,p in enumerate(parts,start=1)]


def verify_remote_docx_links(
    raw: bytes,
    replacements: Mapping[str, Sequence[str]],
    *, previous_video_ids: Sequence[str],
    expected_sha256: str,
    pdf_links: Mapping[str, str] | None = None,
) -> dict:
    """Verify exact remote DOCX bytes and active hyperlink relationships.

    Call ONLY on bytes fetched from the exact original Google Drive file ID.
    A stale DriveFS-mounted copy is not proof of remote commit. The caller
    must independently assert the fetched Drive ID before passing bytes.
    """
    _need(sha256_bytes(raw) == expected_sha256,
          "REMOTE_DOCX_SHA_NOT_CURRENT_COMMITTED_REVISION")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        _need(z.testzip() is None, "REMOTE_DOCX_ZIP_CRC_FAILED")
        body = ET.fromstring(z.read("word/document.xml"))
        rel = ET.fromstring(z.read("word/_rels/document.xml.rels"))
    W="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    R="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    NS={"w":W}
    rels={e.get("Id"):e.get("Target") for e in rel}
    seen=set()
    active=[]
    for row in body.findall(".//w:tr",NS):
        cells=row.findall("w:tc",NS)
        if len(cells)<5:continue
        subsection = "".join(t.text or "" for t in cells[1].findall(".//w:t",NS)).strip()
        for h in row.findall(".//w:hyperlink",NS):
            active.append(rels.get(h.get("{"+R+"}id")))
        if subsection not in replacements:continue
        _need(subsection not in seen, "DUPLICATE_DOCX_SUBSECTION_ROW")
        seen.add(subsection)
        links = cells[3].findall(".//w:hyperlink",NS)
        urls = [rels.get(h.get("{"+R+"}id")) for h in links]
        labels = ["".join(t.text or "" for t in h.findall(".//w:t",NS)) for h in links]
        expected = list(replacements[subsection])
        _need(bool(expected) and urls==expected and
              labels == [f"Part {i}" for i in range(1,len(expected)+1)],
              "REMOTE_DOCX_VIDEO_PART_LINKS_WRONG")
        if pdf_links is not None:
            pdf = cells[4].findall(".//w:hyperlink",NS)
            _need(len(pdf)==1 and rels.get(pdf[0].get("{"+R+"}id")) ==
                  pdf_links[subsection],
                  "REMOTE_DOCX_PDF_LINK_CHANGED")
    _need(seen==set(replacements),"MISSING_REMOTE_DOCX_SUBSECTION")
    for video in previous_video_ids:
        _need(not any(x in (f"https://youtu.be/{video}",
                            f"https://www.youtube.com/watch?v={video}")
                      for x in active),
              "ACTIVE_DOCUMENT_STILL_LINKS_SUPERSEDED_VIDEO")
    return {"remote_sha256":expected_sha256,"subsections":len(seen),
            "hyperlinks":sum(len(x) for x in replacements.values()),
            "all_previous_video_links_absent":True}


def verify_remote_pdf(remote_pdf_bytes: bytes, expected_local_sha256: str) -> None:
    _need(sha256_bytes(remote_pdf_bytes)==expected_local_sha256,
          "REMOTE_LINKED_PDF_DOES_NOT_MATCH_ACCEPTED_SLIDES")
    _need(remote_pdf_bytes.startswith(b"%PDF-"),
          "REMOTE_LINKED_ASSET_NOT_PDF")


def require_replacement_playlist(
    *, original_order: Sequence[str], current_order: Sequence[str],
    old_ids: Sequence[str], new_ids: Sequence[str],
    start_position: int, old_videos_deleted: bool,
) -> dict:
    """Allow only intended insertion and retirement; preserve other video order."""
    baseline=list(original_order);live=list(current_order)
    old=set(old_ids);new=set(new_ids)
    _need(len(old)==len(old_ids) and len(new)==len(new_ids)
          and len(new)>0 and not old & new, "INVALID_VIDEO_ID_SETS")
    _need(start_position>=0 and len(baseline)==len(set(baseline))
          and len(live)==len(set(live)), "INVALID_PLAYLIST_IDENTITIES")
    _need(live[start_position:start_position+len(new_ids)]==list(new_ids),
          "REPLACEMENT_PART_ORDER_CHANGED")
    if old_videos_deleted:
        _need(not old.intersection(live), "SUPERSEDED_PLAYLIST_VIDEO_REMAINS")
    else:
        _need(old.issubset(live), "ORIGINAL_VIDEO_MISSING_BEFORE_RETIREMENT")
    expected_others=[v for v in baseline if v not in old]
    current_others=[v for v in live if v not in old|new]
    _need(current_others==expected_others, "OUT_OF_SCOPE_PLAYLIST_ORDER_CHANGED")
    _need(len(live)==len(baseline)+len(new_ids)-
          (len(old_ids) if old_videos_deleted else 0),
          "UNEXPECTED_PLAYLIST_COUNT")
    return {"new_positions":list(range(start_position,start_position+len(new_ids))),
            "playlist_count":len(live),"out_of_scope_order_preserved":True}


def require_complete_predelete(
    *, old_ids: Sequence[str], new_ids: Sequence[str],
    publicly_processed_ids: Sequence[str],
    playlist_ids: Sequence[str], document_urls: Sequence[str],
    remote_pdf_shas: Mapping[str,str], accepted_pdf_shas: Mapping[str,str],
    remote_doc_verified: bool,
    out_of_scope_before: Sequence[str], out_of_scope_after: Sequence[str],
) -> tuple[str, ...]:
    _need(bool(remote_pdf_shas)
          and remote_pdf_shas==accepted_pdf_shas,
          "REMOTE_PDF_HASH_SET_NOT_VERIFIED")
    return safe_retirement_ids(
        old_ids=old_ids,new_ids=new_ids,playlist_ids=playlist_ids,
        document_urls=document_urls,
        publicly_processed_ids=publicly_processed_ids,
        pdf_verified=True,remote_doc_verified=remote_doc_verified,
        out_of_scope_before=out_of_scope_before,
        out_of_scope_after=out_of_scope_after)


def deletion_transition(action_state: str | None, *, remote_video_exists: bool) -> str:
    """Disambiguation policy for irreversible YouTube delete calls.

    Caller may SEND exactly one new delete only on action_state==None and
    verified original existence. Once a request is acknowledged or ambiguous,
    reconciliation must use reads only; it must not reissue DELETE.
    """
    if not remote_video_exists:
        return "VIDEO_ABSENT_VERIFIED"
    if action_state is None:
        return "ISSUE_FIRST_DELETE_ONLY"
    if action_state in ("DELETE_REQUEST_ACCEPTED","DELETE_ACCEPTED_AWAITING_ABSENCE",
                        "DELETE_OUTCOME_UNCERTAIN_NOT_REPLAYED"):
        return "READBACK_ONLY_NEVER_REISSUE_DELETE"
    if action_state == "VIDEO_ABSENT_VERIFIED":
        raise PublicationRecoveryBlocked("PREVIOUS_ABSENCE_RECEIPT_CONTRADICTED")
    raise PublicationRecoveryBlocked("UNRECOGNIZED_DELETION_STATE")
