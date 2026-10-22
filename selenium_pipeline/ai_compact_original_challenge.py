"""Bounded textbook PDF excerpt for a separately requested AI challenge pass.

Real original PDF pages, slide text and source hashes, NOT merely the first
model's review. Text-only excerpts are not sufficient for unseen figure
semantics: preserve unresolved figure cases for multimodal academic QA.
"""
from __future__ import annotations
import json
from pathlib import Path
import pymupdf
from .figure_source_identity import require,_sha
from .ai_academic_review_queue import _check_queue,execute_one_review
from .ai_academic_web_review import build_review_job
from .ai_academic_review_consensus import _independently_check_saved_pass
from .series_gemini import _browser_request

def write_bounded_challenge_evidence(*,queue_root:Path,folder:Path,
                                     slide:int,output:Path)->dict:
    queue_root,folder,output=[Path(p).absolute() for p in (queue_root,folder,output)]
    _check_queue(queue_root=queue_root,folder=folder,slide=slide,mode="INDEPENDENT_CHALLENGE")
    require(output.parent.is_dir() and not output.exists() and
            not output.is_relative_to(folder) and output.suffix.lower()==".txt",
            "Original figure/text snippets require new independent text file")
    j=build_review_job(folder=folder,slide_numbers=[slide])
    first=json.loads((queue_root/f"slide_{slide:03d}_initial_review.json").read_text(encoding="utf8"))
    prior=_independently_check_saved_pass(folder=folder,job=j,record=first,
                                          mode="INITIAL_REVIEW")
    page_ids=sorted({r["source_page"] for r in prior
                     if type(r.get("source_page")) is int})
    require(1<=len(page_ids)<=4,"Original textbook page evidence missing or unbounded")
    evidence=[f"ORIGINAL SOURCE SHA256 {j['source_sha256']}",
              f"ORIGINAL SLIDE SHA256 {j['slides_sha256']}",
              f"ORIGINAL SCRIPT SHA256 {j['script_sha256']}",
              "INDEPENDENT SECOND REVIEW: challenge mathematical truth and source support.",
              "This text was extracted programmatically from the actual original PDFs;",
              "visible PDF figures/equations inaccessible to text extraction MUST be marked UNRESOLVED."]
    with pymupdf.open(folder/"source.pdf") as book,pymupdf.open(folder/"slides.pdf") as deck:
        for pg in page_ids:
            require(1<=pg<=len(book),"Source quote references nonexistent physical book page")
            txt=book[pg-1].get_text(sort=True)
            require(txt.strip(),"Source page has no extractable mathematical text")
            evidence.append(f"\nORIGINAL TEXTBOOK PDF PHYSICAL PAGE {pg}\n"+txt[:12000])
        page=deck[slide-1]
        evidence.append(f"\nORIGINAL SLIDE PDF PHYSICAL PAGE {slide}\n"+page.get_text(sort=True)[:12000])
    for unit in j["slides"][0]["utterances"]:
        evidence.append("\nEXACT ORIGINAL SPEECH "+unit["id"]+" SHA "+unit["spoken_sha256"]
                        +"\n"+unit["spoken_text"])
    for target in j["slides"][0]["visual_targets"]:
        evidence.append("\nACTUAL SLIDE TARGET "+target["id"]+" RECT "+
                        json.dumps(target["bbox_pdf_pt"])+"\n"+
                        str(target["visible_text"])[:900])
    require(all(_sha(folder/k)==j[v] for k,v in
                (("source.pdf","source_sha256"),("slides.pdf","slides_sha256"),
                 ("script.txt","script_sha256"))),
            "Original educational source changed during PDF excerpt extraction")
    full="\n".join(evidence)
    require(len(full)<=65000,"Compact original source excerpt unbounded")
    output.write_text(full,encoding="utf8")
    return {"status":"ORIGINAL_PDF_VERIFIED_TEXT_ONLY_CHALLENGE_EVIDENCE",
            "slide":slide,"original_utterance_count":j["utterance_count"],
            "original_book_pages":page_ids,"excerpt_sha256":_sha(output),
            "image_only_figure_semantics_verified":False,
            "student_publication_authorized":False}

def execute_compact_original_challenge(*,queue_root:Path,folder:Path,
                                       slide:int,attempt:int,
                                       excerpt:Path,transport=None)->dict:
    # Caller has explicitly inspected prior quarantine and selected attempt.
    context=write_bounded_challenge_evidence(
        queue_root=queue_root,folder=folder,slide=slide,output=excerpt)
    def call(original_prompt,original_files):
        intro=("The attachment is a source-hash-bound extract from the ORIGINAL PDF "
               "and original slide. Challenge mathematics and exact slide target "
               "using only the attachment, cite physical textbook PDF page and "
               "verbatim original quote. If visual equation is not discernible "
               "from text, mark UNRESOLVED. Provide EXACT JSON. "
               "Original job/schema follows:\n")
        service=transport or (lambda prompt,files:_browser_request(
            prompt,files,port=9222,wait_cap_s=240,min_chars=80))
        return service(intro+original_prompt,[Path(excerpt)])
    r=execute_one_review(queue_root=queue_root,folder=folder,slide=slide,
                         mode="INDEPENDENT_CHALLENGE",attempt=attempt,transport=call)
    return {**r,"source_excerpt_sha256":context["excerpt_sha256"],
            "second_pass_uses_text_only_source_evidence":True,
            "figure_math_semantics_without_visual_qa_verified":False}
