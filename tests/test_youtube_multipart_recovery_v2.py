"""One-to-many YouTube, DOCX readback, hashes, and non-replayed deletion."""
from io import BytesIO
from pathlib import Path
import pytest
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT

from selenium_pipeline.youtube_multipart_recovery_v2 import (
 ordered_narrated_parts, full_replacement_plan, sha256_bytes,
 verify_remote_docx_links, verify_remote_pdf, require_replacement_playlist,
 require_complete_predelete, deletion_transition
)
from selenium_pipeline.youtube_publication_recovery import PublicationRecoveryBlocked

ROOT=Path(r"G:\My Drive\Serway\Serway_8_14\11")


@pytest.mark.skipif(not ROOT.is_dir(),reason="Live Chapter 11 DriveFS not mounted here")
@pytest.mark.parametrize("section,total",[
 ("11.1",2),("11.2",3),("11.3",2),("11.4",3),("11.5",1)])
def test_real_ch11_source_qa_and_manifest_shas(section,total):
    parts=ordered_narrated_parts(ROOT/section,explicit_skip_highlight_qa=True)
    assert len(parts)==total
    assert [x["part_number"] for x in parts]==list(range(1,total+1))
    assert all(0<x["duration_seconds"]<600 for x in parts)
    assert parts[0]["filename"]=="slides.mp4"


@pytest.mark.skipif(not ROOT.is_dir(),reason="Live Chapter 11 DriveFS not mounted here")
def test_scoped_technical_completion_cannot_be_full_g3():
    with pytest.raises(PublicationRecoveryBlocked,match="HIGHLIGHT_QA_NOT_ACCEPTED"):
        ordered_narrated_parts(ROOT/"11.1",explicit_skip_highlight_qa=False)


def test_dynamic_many_to_many_planner_orders_all_parts():
    parts=[
        {"part_number":i,"parts_total":3,
         "filename":"slides.mp4" if i==1 else f"slides_part{i:02d}.mp4",
         "sha256":str(i)*64}
        for i in range(1,4)]
    out=full_replacement_plan("11.4",["oldvideo001","oldvideo002"],
                              "Angular Momentum",parts)
    assert len(out)==3
    assert out[0]["title"].endswith("(Part 1 of 3)")
    assert out[2]["title"].endswith("(Part 3 of 3)")
    assert all(v["old_video_ids"]==["oldvideo001","oldvideo002"] for v in out)
    assert all(v["new_video_id"] is None for v in out)


def test_planner_rejects_partial_parts_and_unsafe_titles():
    with pytest.raises(PublicationRecoveryBlocked,match="PARTS_NOT_CONTIGUOUS"):
        full_replacement_plan("11.1",["oldvideo001"],"Title",[
          {"part_number":1,"parts_total":3,"filename":"slides.mp4","sha256":"1"*64}])
    with pytest.raises(PublicationRecoveryBlocked,match="TITLE_EXCEEDS"):
        full_replacement_plan("11.1",["oldvideo001"],"x"*120,[
          {"part_number":1,"parts_total":1,"filename":"slides.mp4","sha256":"1"*64}])


def _link(cell,label,url):
    paragraph=cell.paragraphs[0]
    rid=paragraph.part.relate_to(url,RT.HYPERLINK,is_external=True)
    h=OxmlElement("w:hyperlink");h.set(qn("r:id"),rid)
    run=OxmlElement("w:r");t=OxmlElement("w:t")
    t.text=label;run.append(t);h.append(run);paragraph._p.append(h)


def _doc():
    d=Document();table=d.add_table(rows=3,cols=5)
    for row,section,links in [
       (0,"11.1",["new1","new2"]),
       (1,"11.2",["new3","new4","new5"])]:
        c=table.rows[row].cells
        c[1].text=section
        for i,video in enumerate(links,1):
            _link(c[3],f"Part {i}",f"https://youtu.be/{video}")
        _link(c[4],"PDF","https://drive.google.com/"+section)
    other=table.rows[2].cells
    other[1].text="12.1";_link(other[3],"Old","https://youtu.be/other")
    b=BytesIO();d.save(b);return b.getvalue()


def test_exact_original_remote_docx_link_readback_verification():
    payload=_doc()
    result=verify_remote_docx_links(payload,{
        "11.1":["https://youtu.be/new1","https://youtu.be/new2"],
        "11.2":["https://youtu.be/new3","https://youtu.be/new4","https://youtu.be/new5"]
    },previous_video_ids=["old1","old2"],
       expected_sha256=sha256_bytes(payload),
       pdf_links={"11.1":"https://drive.google.com/11.1",
                  "11.2":"https://drive.google.com/11.2"})
    assert result["subsections"]==2
    assert result["hyperlinks"]==5


def test_docx_readback_detects_stale_rev_wrong_links_and_pdf():
    payload=_doc()
    args={
        "replacements":{"11.1":["https://youtu.be/new1","https://youtu.be/new2"],
                         "11.2":["https://youtu.be/new3","https://youtu.be/new4","https://youtu.be/new5"]},
        "previous_video_ids":["old1","old2"],
        "expected_sha256":sha256_bytes(payload)
    }
    with pytest.raises(PublicationRecoveryBlocked,match="SHA"):
        verify_remote_docx_links(payload,**{**args,"expected_sha256":"0"*64})
    with pytest.raises(PublicationRecoveryBlocked,match="PART_LINKS"):
        verify_remote_docx_links(payload,**{**args,
          "replacements":{**args["replacements"],"11.1":["https://youtu.be/new2","https://youtu.be/new1"]}})
    with pytest.raises(PublicationRecoveryBlocked,match="PDF_LINK_CHANGED"):
        verify_remote_docx_links(payload,**args,pdf_links={
          "11.1":"https://drive.google.com/not-the-original",
          "11.2":"https://drive.google.com/11.2"})


def test_remote_pdf_requires_same_accepted_bytes():
    accepted=b"%PDF-1.5\nexample bytes"
    verify_remote_pdf(accepted,sha256_bytes(accepted))
    with pytest.raises(PublicationRecoveryBlocked,match="PDF_DOES_NOT_MATCH"):
        verify_remote_pdf(accepted,sha256_bytes(b"another PDF"))
    with pytest.raises(PublicationRecoveryBlocked,match="NOT_PDF"):
        verify_remote_pdf(b"Not PDF",sha256_bytes(b"Not PDF"))


def test_playlist_insertion_then_retirement_preserves_other_videos():
    before=["u1","u2","old1","old2","u3"]
    prepared=["u1","u2","new1","new2","new3","old1","old2","u3"]
    out=require_replacement_playlist(original_order=before,
        current_order=prepared,old_ids=["old1","old2"],
        new_ids=["new1","new2","new3"],start_position=2,
        old_videos_deleted=False)
    assert out["playlist_count"]==8
    completed=["u1","u2","new1","new2","new3","u3"]
    out=require_replacement_playlist(original_order=before,
        current_order=completed,old_ids=["old1","old2"],
        new_ids=["new1","new2","new3"],start_position=2,
        old_videos_deleted=True)
    assert out["playlist_count"]==6
    with pytest.raises(PublicationRecoveryBlocked,match="OUT_OF_SCOPE"):
        require_replacement_playlist(original_order=before,
            current_order=["u2","u1","new1","new2","new3","u3"],
            old_ids=["old1","old2"],new_ids=["new1","new2","new3"],
            start_position=2,old_videos_deleted=True)


def test_deletion_state_machine_never_replays_uncertain_mutation():
    assert deletion_transition(None,remote_video_exists=True)=="ISSUE_FIRST_DELETE_ONLY"
    assert deletion_transition("DELETE_REQUEST_ACCEPTED",remote_video_exists=True)=="READBACK_ONLY_NEVER_REISSUE_DELETE"
    assert deletion_transition("DELETE_OUTCOME_UNCERTAIN_NOT_REPLAYED",remote_video_exists=True)=="READBACK_ONLY_NEVER_REISSUE_DELETE"
    assert deletion_transition("DELETE_REQUEST_ACCEPTED",remote_video_exists=False)=="VIDEO_ABSENT_VERIFIED"
    with pytest.raises(PublicationRecoveryBlocked,match="CONTRADICTED"):
        deletion_transition("VIDEO_ABSENT_VERIFIED",remote_video_exists=True)


def test_predelete_complete_requires_remote_document_and_all_pdf_hashes():
    kw=dict(old_ids=["old1"],new_ids=["new1","new2"],
        publicly_processed_ids=["new1","new2"],
        playlist_ids=["new1","new2","old1"],
        document_urls=["https://youtu.be/new1","https://youtu.be/new2"],
        remote_pdf_shas={"11.1":"sha-A"},
        accepted_pdf_shas={"11.1":"sha-A"},
        remote_doc_verified=True,out_of_scope_before=["u"],out_of_scope_after=["u"])
    assert require_complete_predelete(**kw)==("old1",)
    with pytest.raises(PublicationRecoveryBlocked,match="PDF_HASH"):
        require_complete_predelete(**{**kw,"remote_pdf_shas":{"11.1":"different"}})
    with pytest.raises(PublicationRecoveryBlocked,match="DOCUMENT_OR_PDF"):
        require_complete_predelete(**{**kw,"remote_doc_verified":False})
    with pytest.raises(PublicationRecoveryBlocked,match="INCOMPLETE"):
        require_complete_predelete(**{**kw,"publicly_processed_ids":["new1"]})


def test_executable_recovery_registry_contains_source_bound_youtube_repair():
    from selenium_pipeline.recovery_registry import load_registry, lookup_mechanism
    reg=load_registry()
    matching=[entry for entry in reg["entries"]
              if entry["match_type"]=="youtube_multipart_publication"]
    assert len(matching)==1
    assert matching[0]["enabled"] is True
    assert lookup_mechanism(
        "youtube_multipart_publication",
        "ONE_OLD_YOUTUBE_VIDEO_SUPERSEDED_BY_MULTIPLE_VERIFIED_MP4_PARTS"
    )=="SOURCE_QA_PART_HASH_DOCX_REMOTE_PDF_PLAYLIST_TWO_PHASE_RETIREMENT"
