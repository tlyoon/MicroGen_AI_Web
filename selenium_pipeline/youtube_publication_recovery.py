"""Safe, testable guards for YouTube publication and Office DOCX synchronization.

The caller must obtain the authoritative DOCX bytes directly from Drive,
upload the patched bytes via files.update to the SAME file ID, and verify the
remote readback before retiring videos. No network or destructive calls here.
"""
from __future__ import annotations
import copy, hashlib, io, zipfile
from collections.abc import Callable, Mapping, Sequence

class PublicationRecoveryBlocked(RuntimeError):
    pass

def require_fresh_drive_mount(mounted: bytes, authoritative: bytes) -> None:
    if hashlib.sha256(mounted).digest() != hashlib.sha256(authoritative).digest():
        raise PublicationRecoveryBlocked("DRIVEFS_STALE_DOCX_USE_REMOTE_FILES_UPDATE")

def wait_for_youtube_public(
    video_ids: Sequence[str],
    fetch: Callable[[list[str]], Mapping[str, Mapping[str, str]]],
    *, attempts: int = 5, wait: Callable[[], None] = lambda: None
) -> None:
    """Only repeat READBACK after a successful update; never resend mutation."""
    ids=list(video_ids)
    if not ids or len(set(ids))!=len(ids) or attempts<1:
        raise ValueError("Unique video IDs and positive attempts required")
    for index in range(attempts):
        current=fetch(ids)
        if all(v in current and current[v].get("privacyStatus")=="public"
               and current[v].get("uploadStatus")=="processed"
               and current[v].get("processingStatus","succeeded")=="succeeded"
               for v in ids):
            return
        if index+1<attempts: wait()
    raise PublicationRecoveryBlocked("YOUTUBE_VISIBILITY_READBACK_STALE_OR_NOT_READY")

def safe_retirement_ids(
    *, old_ids: Sequence[str], new_ids: Sequence[str], playlist_ids: Sequence[str],
    document_urls: Sequence[str], publicly_processed_ids: Sequence[str],
    pdf_verified: bool, remote_doc_verified: bool,
    out_of_scope_before: Sequence[str], out_of_scope_after: Sequence[str]
) -> tuple[str,...]:
    old,new=tuple(old_ids),tuple(new_ids)
    if not old or not new or len(set(old))!=len(old) or len(set(new))!=len(new) or set(old)&set(new):
        raise PublicationRecoveryBlocked("INVALID_REPLACEMENT_SET")
    if not pdf_verified or not remote_doc_verified:
        raise PublicationRecoveryBlocked("DOCUMENT_OR_PDF_GATE_FAILED")
    if not set(new).issubset(playlist_ids) or not set(new).issubset(publicly_processed_ids):
        raise PublicationRecoveryBlocked("UNPUBLISHED_OR_INCOMPLETE_REPLACEMENT")
    if list(document_urls)!=["https://youtu.be/"+v for v in new]:
        raise PublicationRecoveryBlocked("DOCUMENT_LINK_SET_MISMATCH")
    if list(out_of_scope_before)!=list(out_of_scope_after):
        raise PublicationRecoveryBlocked("OUT_OF_SCOPE_ORDER_CHANGED")
    return old

def orphan_item_ids(
    old_ids: Sequence[str], confirmed_deleted: Sequence[str],
    playlist_items: Sequence[Mapping[str,str]]
) -> tuple[str,...]:
    old,confirmed=set(old_ids),set(confirmed_deleted)
    result=[]
    for item in playlist_items:
        if item.get("video_id") in old:
            if item["video_id"] not in confirmed or not item.get("playlist_item_id"):
                raise PublicationRecoveryBlocked("ORPHAN_REMOVAL_NOT_VERIFIED_SAFE")
            result.append(item["playlist_item_id"])
    return tuple(result)

def patch_authoritative_docx(
    source: bytes,
    replacements: Mapping[str, Sequence[str]],
    expected_existing: Mapping[str, Sequence[str]],
    *, section_column: int=1, video_column: int=3
) -> bytes:
    """Modify only selected video-link cells, preserving ZIP non-XML members.

    Supports one-to-N and M-to-N links, and is idempotent if already updated.
    Does NOT edit DriveFS in place or weaken concurrency/readback requirements.
    """
    from lxml import etree as E
    if not replacements or set(replacements)!=set(expected_existing):
        raise PublicationRecoveryBlocked("REPLACEMENT_SECTIONS_INVALID")
    W="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    R="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    P="http://schemas.openxmlformats.org/package/2006/relationships"
    NS={"w":W}
    def q(n,t):return "{"+n+"}"+t
    def text(node):return "".join((t.text or "") for t in node.findall(".//w:t",NS)).strip()
    with zipfile.ZipFile(io.BytesIO(source)) as z:
        if z.testzip():raise PublicationRecoveryBlocked("DOCX_SOURCE_INVALID")
        infos=z.infolist()
        members={i.filename:z.read(i.filename) for i in infos}
    doc=E.fromstring(members["word/document.xml"])
    rel=E.fromstring(members["word/_rels/document.xml.rels"])
    relmap={r.get("Id"):r for r in rel}
    used=set(relmap)
    nextid=1
    seen=set()
    modified=False
    for row in doc.findall(".//w:tr",NS):
        cells=row.findall("w:tc",NS)
        if len(cells)<=max(section_column,video_column):continue
        section=text(cells[section_column])
        if section not in replacements:continue
        if section in seen:raise PublicationRecoveryBlocked("DUPLICATE_DOCUMENT_SECTION")
        seen.add(section)
        target=cells[video_column]
        links=target.findall(".//w:hyperlink",NS)
        urls=[relmap[h.get(q(R,"id"))].get("Target") if h.get(q(R,"id")) in relmap else None for h in links]
        desired=list(replacements[section])
        labels=[text(h) for h in links]
        if not desired or not all(x.startswith("https://youtu.be/") for x in desired):
            raise PublicationRecoveryBlocked("BAD_YOUTUBE_URLS")
        if urls==desired and labels==[f"Part {n+1}" for n in range(len(desired))]:
            continue
        if urls!=list(expected_existing[section]) or not links:
            raise PublicationRecoveryBlocked("UNEXPECTED_CONCURRENT_OR_UNRECONCILED_LINKS")
        if len({id(h.getparent()) for h in links})!=1:
            raise PublicationRecoveryBlocked("MULTIPLE_VIDEO_PARAGRAPHS")
        if text(target)!=" | ".join(labels):
            raise PublicationRecoveryBlocked("VIDEO_CELL_HAS_UNEXPECTED_TEXT")
        base=copy.deepcopy(links[0])
        if len(base.findall(".//w:t",NS))!=1:
            raise PublicationRecoveryBlocked("UNKNOWN_HYPERLINK_STYLE")
        parent=links[0].getparent()
        place=parent.index(links[0])
        for child in list(parent):
            if child in links or (child.tag==q(W,"r") and text(child)=="|"):
                parent.remove(child)
        for i,url in enumerate(desired):
            while f"rId{nextid}" in used:nextid+=1
            rid=f"rId{nextid}";used.add(rid);nextid+=1
            relationship=E.SubElement(rel,q(P,"Relationship"))
            relationship.set("Id",rid)
            relationship.set("Type",P+"/hyperlink")
            relationship.set("Target",url)
            relationship.set("TargetMode","External")
            if i:
                sep=E.Element(q(W,"r"))
                t=E.SubElement(sep,q(W,"t"))
                t.set("{http://www.w3.org/XML/1998/namespace}space","preserve")
                t.text=" | "
                parent.insert(place,sep);place+=1
            h=copy.deepcopy(base)
            h.set(q(R,"id"),rid)
            h.findall(".//w:t",NS)[0].text=f"Part {i+1}"
            parent.insert(place,h);place+=1
        modified=True
    if seen!=set(replacements):
        raise PublicationRecoveryBlocked("MISSING_DOCUMENT_SECTION")
    if not modified:return source
    members["word/document.xml"]=E.tostring(doc,encoding="UTF-8",xml_declaration=True)
    members["word/_rels/document.xml.rels"]=E.tostring(rel,encoding="UTF-8",xml_declaration=True)
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w") as z:
        for info in infos:z.writestr(info,members[info.filename])
    with zipfile.ZipFile(io.BytesIO(out.getvalue())) as z:
        if z.testzip():raise PublicationRecoveryBlocked("PATCHED_DOCX_DAMAGED")
    return out.getvalue()
