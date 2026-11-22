from io import BytesIO
import pytest
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from selenium_pipeline.youtube_publication_recovery import (
    PublicationRecoveryBlocked,require_fresh_drive_mount,wait_for_youtube_public,
    safe_retirement_ids,orphan_item_ids,patch_authoritative_docx)

def link(cell,label,url):
    p=cell.paragraphs[0];rid=p.part.relate_to(url,RT.HYPERLINK,is_external=True)
    h=OxmlElement("w:hyperlink");h.set(qn("r:id"),rid)
    run=OxmlElement("w:r");t=OxmlElement("w:t");t.text=label;run.append(t);h.append(run);p._p.append(h)

def docx():
    d=Document();t=d.add_table(rows=3,cols=5)
    for j,(s,video) in enumerate([("9.1","nine"),("10.5","old5"),("10.6","old6")]):
        c=t.rows[j].cells;c[1].text=s;link(c[3],"Link","https://youtu.be/"+video)
        link(c[4],"PDF","https://drive.google.com/"+s)
    b=BytesIO();d.save(b);return b.getvalue()

def test_docx_repair_preserves_others_and_idempotent():
    data=docx()
    desired={"10.5":["https://youtu.be/new51","https://youtu.be/new52"],
             "10.6":["https://youtu.be/new61","https://youtu.be/new62","https://youtu.be/new63"]}
    old={"10.5":["https://youtu.be/old5"],"10.6":["https://youtu.be/old6"]}
    updated=patch_authoritative_docx(data,desired,old)
    t=Document(BytesIO(updated)).tables[0]
    assert t.rows[0].cells[3].text=="Link"
    assert t.rows[1].cells[3].text=="Part 1 | Part 2"
    assert t.rows[2].cells[3].text=="Part 1 | Part 2 | Part 3"
    assert t.rows[2].cells[4].text=="PDF"
    assert patch_authoritative_docx(updated,desired,old)==updated

def test_stale_mount_prevented():
    with pytest.raises(PublicationRecoveryBlocked,match="DRIVEFS_STALE"):
        require_fresh_drive_mount(b"old",b"new")

def test_youtube_readback_recovery_without_resending_update():
    responses=[{"v":{"privacyStatus":"unlisted","uploadStatus":"processed"}},
               {"v":{"privacyStatus":"public","uploadStatus":"processed"}}]
    polls=[]
    def fetch(ids):
        polls.append(ids);return responses.pop(0)
    wait_for_youtube_public(["v"],fetch)
    assert len(polls)==2
    with pytest.raises(PublicationRecoveryBlocked):
        wait_for_youtube_public(["v"],lambda ids:{},attempts=2)

def test_retirement_and_orphan_proof():
    kw=dict(old_ids=["old"],new_ids=["new1","new2"],playlist_ids=["new1","new2","old"],
            document_urls=["https://youtu.be/new1","https://youtu.be/new2"],
            publicly_processed_ids=["new1","new2"],pdf_verified=True,
            remote_doc_verified=True,out_of_scope_before=["other"],
            out_of_scope_after=["other"])
    assert safe_retirement_ids(**kw)==("old",)
    with pytest.raises(PublicationRecoveryBlocked):
        safe_retirement_ids(**{**kw,"pdf_verified":False})
    with pytest.raises(PublicationRecoveryBlocked):
        safe_retirement_ids(**{**kw,"document_urls":["https://youtu.be/old"]})
    entries=[{"video_id":"old","playlist_item_id":"orphan"},
             {"video_id":"new","playlist_item_id":"keep"}]
    assert orphan_item_ids(["old"],["old"],entries)==("orphan",)
    with pytest.raises(PublicationRecoveryBlocked):
        orphan_item_ids(["old"],[],entries)
