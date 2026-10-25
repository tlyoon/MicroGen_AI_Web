"""Real original-PDF Gemini-web academic-review jobs; no model/API billing.

A first-pass AI assessment is source-cited evidence, not proof or student
release authorization. Browser requests are explicit, isolated and read-only
with respect to the original Thomas files.
"""
from __future__ import annotations
import argparse,json,re
from pathlib import Path
from .figure_source_identity import require,_sha
from .incremental_element_candidate_map import candidate_map
from .pdf_text_source_span_witness import prove_source_quote_occurrence
from .series_gemini import decode_storyboard_response,_browser_request
from .source_locked_academic_review import (review_quote_whitelist,
    require_quote_locked_model_reply,recover_rendered_json_format_only)

def build_review_job(*,folder:Path,slide_numbers:list[int])->dict:
    folder=Path(folder).absolute()
    require(folder.is_dir() and not folder.is_symlink()
            and type(slide_numbers) is list and len(slide_numbers)>0
            and len(slide_numbers)<=4 and all(type(s) is int for s in slide_numbers)
            and slide_numbers==sorted(set(slide_numbers)),
            "Small bounded original slide range required")
    full=candidate_map(folder=folder)
    require(max(slide_numbers)<=full["slide_count"],"Slide outside genuine source PDF")
    slides=[]
    for i in slide_numbers:
        s=full["slides"][i-1]
        slides.append({"slide":i,
          "visual_targets":[{"id":x["draft_element_id"],"bbox_pdf_pt":x["bbox_pdf_pt"],
                             "visible_text":x["visible_text"][:650],
                             "kind":x["kind"]} for x in s["candidate_visual_targets"]],
          "utterances":[{"id":u["utterance_id"],"spoken_text":u["original_text"],
                         "spoken_sha256":u["original_text_sha256"],
                         "ranked_candidates":[v["target_id"] for v in u["candidate_visual_targets"]]}
                        for u in s["original_utterance_candidates"]]})
    return {"status":"SOURCE_BOUND_AI_REVIEW_REQUEST_NOT_DISPATCHED",
            "original_folder":str(folder),
            "source_sha256":full["source_sha256"],
            "slides_sha256":full["slides_sha256"],
            "script_sha256":full["script_sha256"],
            "selected_original_slides":slide_numbers,
            "utterance_count":sum(len(s["utterances"]) for s in slides),
            "slides":slides,"academic_approval":False,
            "student_publication_authorized":False}

def review_instructions(job:dict,*,mode:str,verified_source_evidence:dict|None=None)->str:
    require(mode in ("INITIAL_REVIEW","INDEPENDENT_CHALLENGE"),"Two distinct review passes only")
    # The original Thomas8.4 Slide4 pilot previously produced 5/5 fabricated
    # textbook citations. Fail BEFORE provider send if a caller omits its
    # independently source-witnessed quotation whitelist.
    if (job.get("source_sha256") ==
        "b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068"
        and job.get("selected_original_slides")==[4]):
        require(verified_source_evidence is not None,
            "Original Thomas8.4 Slide4 review must use verified source quote packet")
    spec={"task":mode,"response_schema":{
            "status":"ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE",
            "rows":[{"utterance_id":"one exact supplied ID",
              "spoken_sha256":"exact supplied SHA",
              "target_id":"one supplied visible target ID or null",
              "source_page":"integer physical source PDF page or null",
              "verbatim_source_quote":"verbatim extract from source PDF or null",
              "verdict":"SUPPORTED or INCORRECT or UNRESOLVED",
              "math_explanation":"concrete reasoning, errors, equations and alternative interpretations"}]}}
    locked=(
        {"verified_source_quote_whitelist":review_quote_whitelist(
            job=job,packet=verified_source_evidence),
         "review_rules":"Cite ONLY an exact page and verbatim quotation from the matching listed utterance; no created quotations or citation paraphrases. Mark UNRESOLVED when the passages do not establish a claim. For the principal-root and absolute-value final utterance, use UNRESOLVED until independently verified original PDF math glyphs are available. Context-only source text is not proof."}
        if verified_source_evidence is not None else {})
    return ("Examine the attached ORIGINAL source.pdf AND slides.pdf; no fabricated PDF page or "
            "math claims. Match the exact original narration to a precise visible slide element; "
            "check mathematical truth and source derivation. For diagrams/equations not captured "
            "as text, leave target null and explain needed visual geometry. Do not guess. "
            "Give a verbatim source quote on the actual 1-indexed PDF page; "
            "if uncertain use null and UNRESOLVED. Independently challenge the claim "
            "on challenge pass; do not assume prior acceptance. Use only listed target IDs. "
            "Respond with one complete JSON object, no Markdown. Requested job and schema:\n"+
            json.dumps({"job":job,"schema":spec,**locked},ensure_ascii=False))

def validate_model_review(*,folder:Path,job:dict,response:dict,mode:str,
                          verified_source_evidence:dict|None=None)->dict:
    folder=Path(folder).absolute()
    require(type(response) is dict
            and response.get("status")=="ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE"
            and type(response.get("rows")) is list
            and len(response["rows"])==job["utterance_count"],"Incomplete model review JSON")
    if verified_source_evidence is not None:
        require_quote_locked_model_reply(job=job,packet=verified_source_evidence,
                                         response=response)
    for file,field in (("source.pdf","source_sha256"),("slides.pdf","slides_sha256"),
                       ("script.txt","script_sha256")):
        require(_sha(folder/file)==job[field],"Original source changed during AI review")
    originals=[u for s in job["slides"] for u in s["utterances"]]
    target={s["slide"]:{x["id"]:x for x in s["visual_targets"]} for s in job["slides"]}
    results=[]
    for original,guess in zip(originals,response["rows"]):
        require(type(guess) is dict
                and guess.get("utterance_id")==original["id"]
                and guess.get("spoken_sha256")==original["spoken_sha256"]
                and guess.get("verdict") in ("SUPPORTED","INCORRECT","UNRESOLVED")
                and type(guess.get("math_explanation")) is str
                and len(guess["math_explanation"].strip())>=25,
                "AI omitted/altered an original narrated unit or mathematics rationale")
        slide=int(original["id"][1:4])
        selected=guess.get("target_id")
        if selected is not None:
            require(type(selected) is str and selected in target[slide],
                    "Model hallucinated slide target identity")
        cited=False
        if guess.get("source_page") is not None or guess.get("verbatim_source_quote") is not None:
            prove_source_quote_occurrence(
                source_pdf=folder/"source.pdf",expected_sha256=job["source_sha256"],
                page_number=guess.get("source_page"),
                verbatim_quote=guess.get("verbatim_source_quote"))
            cited=True
        if guess["verdict"]=="SUPPORTED":
            require(selected is not None and cited,"Math support needs a real target and source quote")
        results.append({"utterance_id":original["id"],"spoken_sha256":original["spoken_sha256"],
                        "target_id":selected,"source_page":guess.get("source_page"),
                        "verbatim_source_quote":guess.get("verbatim_source_quote"),
                        "verdict":guess["verdict"],"math_explanation":guess["math_explanation"],
                        "exact_textbook_quote_verified":cited,
                        "text_target_pdf_bbox_pt":target[slide][selected]["bbox_pdf_pt"] if selected else None})
    return {"status":"SOURCE_WITNESSED_AI_MATH_REVIEW_ONE_PASS",
            "mode":mode,"rows":results,"review_count":len(results),
            "ai_review_is_human_attestation":False,
            "academic_mathematics_independently_verified":False,
            "tts_authorized":False,"student_publication_authorized":False}

def run_web_review(*,folder:Path,job:dict,mode:str,
                   chrome_port:int=9222,wait_cap_s:int=240,transport=None,
                   response_observer=None,verified_source_evidence:dict|None=None)->dict:
    require(chrome_port in range(1,65536) and 60<=wait_cap_s<=600,
            "Browser request must be bounded")
    call=transport or (lambda prompt,files:_browser_request(
        prompt,files,port=chrome_port,wait_cap_s=wait_cap_s,min_chars=80))
    raw=call(review_instructions(job,mode=mode,
                       verified_source_evidence=verified_source_evidence),
             [Path(folder)/"source.pdf",Path(folder)/"slides.pdf"])
    # This callback establishes only that the owned transport returned a
    # response. Never persist the private model text in public receipts.
    if callable(response_observer):
        response_observer(raw)
    try:
        decoded=decode_storyboard_response(raw)
    except (ValueError,RuntimeError,json.JSONDecodeError):
        if verified_source_evidence is None:
            raise
        # Formatting-only rescue is never citation or math approval;
        # downstream locked source validator must still reject bad claims.
        decoded=recover_rendered_json_format_only(raw)
    return validate_model_review(folder=folder,job=job,
             response=decoded,mode=mode,
             verified_source_evidence=verified_source_evidence)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",type=Path,required=True)
    p.add_argument("--slides",type=int,nargs="+",required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--run-gemini-web",action="store_true")
    p.add_argument("--review-mode",choices=["INITIAL_REVIEW","INDEPENDENT_CHALLENGE"],
                   default="INITIAL_REVIEW")
    a=p.parse_args(argv)
    require(a.out.parent.is_dir() and not a.out.exists()
            and not a.out.absolute().is_relative_to(a.folder.absolute()),
            "New review receipts must remain outside original textbook folders")
    job=build_review_job(folder=a.folder,slide_numbers=a.slides)
    result=run_web_review(folder=a.folder,job=job,mode=a.review_mode) if a.run_gemini_web else job
    with a.out.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps({"status":result["status"],"utterances":job["utterance_count"],
                      "out":str(a.out)},indent=2))
if __name__=="__main__":main()
