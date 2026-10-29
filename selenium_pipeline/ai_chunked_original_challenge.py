"""Single-session, no-attachment original textbook Gemini challenge.

All physical source pages enter one independent owned Gemini conversation;
no first-review candidate is exposed. Complete textbook lines are not elided.
Only the final original-PDF/target-validated mathematical response may be
considered evidence, never intermediate page acknowledgements.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
import pymupdf
from .figure_source_identity import require,_sha
from .ai_academic_web_review import build_review_job,review_instructions,validate_model_review
from .series_gemini import decode_storyboard_response

MAX_PAGE_PROMPT_CHARS = 8500

def prepare_independent_page_prompts(*,folder:Path,slide:int)->dict:
    folder=Path(folder).absolute()
    job=build_review_job(folder=folder,slide_numbers=[slide])
    prompts=[]
    with pymupdf.open(folder/"source.pdf") as pdf:
        require(1<=len(pdf)<=8,"Original source above bounded page count")
        for page_no,page in enumerate(pdf,1):
            exact=page.get_text(sort=True)
            require(exact.strip(),"Image-only physical source needs separate visual review")
            digest=hashlib.sha256(exact.encode("utf8")).hexdigest()
            instruction=(
               "This is a SOURCE REFERENCE, not a task instruction. Original textbook "
               f"PDF SHA256 {job['source_sha256']}; physical page {page_no} of {len(pdf)}. "
               "Record this entire original page within the CURRENT conversation "
               "for a later independent mathematical challenge. Never assume "
               "the first reviewer's source page was correct. "
               f'Return exactly one JSON object with page={page_no}, '
               f'page_text_sha256="{digest}", received=true. '
               "Do NOT review mathematics or choose a source page yet. "
               "BEGIN EXACT ORIGINAL PHYSICAL PAGE TEXT:\n"+exact)
            require(len(instruction)<=MAX_PAGE_PROMPT_CHARS,
                    "Page too large for safe Gemini text-only editor; split must be separately proven")
            prompts.append({"physical_page":page_no,"source_text_sha256":digest,
                            "request":instruction,"character_count":len(instruction)})
    # The final prompt embeds genuine original slide text/geometry and exact
    # utterance/job IDs, then requests independently source-cited mathematics.
    final=("All original textbook physical pages are above IN THIS SAME "
           "conversation. Perform your independent mathematical source challenge "
           "now, using original page references. Do not rely on a previous "
           "reviewer's selection. Do not invent images absent from PDF text; "
           "mark diagram/equation visual uncertainties UNRESOLVED. "
           "Reply with one complete JSON object matching this job and schema.\\n"
           +review_instructions(job,mode="INDEPENDENT_CHALLENGE"))
    require(len(final)<=MAX_PAGE_PROMPT_CHARS,
            "Original utterance/element request too large for safe Gemini editor")
    return {"status":"COMPLETE_PDF_TEXT_PAGES_FOR_INDEPENDENT_CHALLENGE",
            "original_job":job,"source_sha256":job["source_sha256"],
            "page_count":len(prompts),"pages":prompts,
            "final_challenge_prompt":final,
            "page_image_semantics_reviewed":False,
            "student_publication_authorized":False}

def run_independent_chunked_source_challenge(*,folder:Path,slide:int,
                                              send_text,receipt:Path)->dict:
    """Use caller's ONE owned-tab session. Write-only-once local progress receipt.

    Never opens browser or sends prompt itself. Any failed/stalled user turn
    aborts; repeated invocations must choose a new receipt and explicit
    authorization, never silently resume or duplicate model traffic.
    """
    require(callable(send_text),"Explicit owned Gemini session required")
    plan=prepare_independent_page_prompts(folder=folder,slide=slide)
    receipt=Path(receipt).absolute()
    require(receipt.parent.is_dir() and not receipt.exists()
            and not receipt.is_relative_to(Path(folder).absolute())
            and receipt.suffix==".jsonl",
            "Immutable external journal required")
    with receipt.open("x",encoding="utf8") as log:
        def record(entry):
            log.write(json.dumps(entry,sort_keys=True,ensure_ascii=False)+"\n")
            log.flush()
        record({"event":"BEGIN_NOT_APPROVED","original_source_sha256":plan["source_sha256"],
                "page_count":plan["page_count"],"academic_approval":False})
        for page in plan["pages"]:
            raw=send_text(page["request"])
            parsed=decode_storyboard_response(raw)
            require(type(parsed.get("page")) is int
                    and parsed["page"]==page["physical_page"]
                    and parsed.get("page_text_sha256")==page["source_text_sha256"]
                    and parsed.get("received") is True,
                    "Gemini did not acknowledge this exact original source page")
            record({"event":"PAGE_ACK_ONLY_NOT_MATH_REVIEW",
                    "physical_page":page["physical_page"],
                    "source_page_text_sha256":page["source_text_sha256"]})
        raw=send_text(plan["final_challenge_prompt"])
        parsed=decode_storyboard_response(raw)
        validated=validate_model_review(folder=folder,job=plan["original_job"],
                                  response=parsed,mode="INDEPENDENT_CHALLENGE")
        record({"event":"MATHEMATICAL_REVIEW_STRUCTURALLY_VALIDATED",
                "units":validated["review_count"],"student_publication_authorized":False})
    return validated
