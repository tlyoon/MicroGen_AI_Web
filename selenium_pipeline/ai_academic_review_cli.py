"""Command-line real Gemini review queue: explicit retry, real prior receipt import.

No private credentials, saved model text from unrelated browser tabs, or
original PDF edits. Never equate AI review with human approval or publication.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from .figure_source_identity import require,_sha
from .ai_academic_web_review import build_review_job
from .pdf_text_source_span_witness import prove_source_quote_occurrence
from .ai_academic_review_queue import execute_one_review,summarize_queue,_check_queue,_receipt_name

def import_prior_source_verified_pass(*,queue_root:Path,folder:Path,
                                      slide:int,prior:Path)->dict:
    queue_root,folder,prior=[Path(x).absolute() for x in (queue_root,folder,prior)]
    state=_check_queue(queue_root=queue_root,folder=folder,slide=slide,mode="INITIAL_REVIEW")
    output=queue_root/_receipt_name(slide,"INITIAL_REVIEW")
    require(not output.exists() and prior.is_file() and not prior.is_symlink()
            and not prior.is_relative_to(folder) and prior!=output,
            "Import cannot change historical source or replace existing AI review")
    current=build_review_job(folder=folder,slide_numbers=[slide])
    report=json.loads(prior.read_text(encoding="utf8"))
    require(report.get("status")=="SOURCE_WITNESSED_AI_MATH_REVIEW_ONE_PASS"
            and report.get("mode")=="INITIAL_REVIEW"
            and type(report.get("rows")) is list
            and len(report["rows"])==current["utterance_count"]
            and report.get("review_count")==current["utterance_count"]
            and report.get("academic_mathematics_independently_verified") is False
            and report.get("student_publication_authorized") is False,
            "Prior Gemini first pass provenance incomplete")
    targets={s["slide"]:{t["id"]:t for t in s["visual_targets"]}
             for s in current["slides"]}
    utterances=[u for s in current["slides"] for u in s["utterances"]]
    for u,row in zip(utterances,report["rows"]):
        require(row.get("utterance_id")==u["id"] and
                row.get("spoken_sha256")==u["spoken_sha256"] and
                row.get("verdict") in ("SUPPORTED","INCORRECT","UNRESOLVED") and
                type(row.get("math_explanation")) is str and
                len(row["math_explanation"].strip())>=25,
                "Cannot import incorrect original narration or missing reason")
        selected=row.get("target_id")
        if selected is not None:
            require(selected in targets[slide]
                    and row.get("text_target_pdf_bbox_pt")==targets[slide][selected]["bbox_pdf_pt"],
                    "Old AI element mapping is stale or fabricated")
        if row.get("exact_textbook_quote_verified"):
            prove_source_quote_occurrence(
                source_pdf=folder/"source.pdf",expected_sha256=current["source_sha256"],
                page_number=row.get("source_page"),
                verbatim_quote=row.get("verbatim_source_quote"))
        if row["verdict"]=="SUPPORTED":
            require(selected is not None and row.get("exact_textbook_quote_verified") is True,
                    "Supported source must have genuine PDF quote and target")
    require(all(_sha(folder/name)==current[key] for name,key in
                (("source.pdf","source_sha256"),("slides.pdf","slides_sha256"),
                 ("script.txt","script_sha256"))),
            "Originals changed during review migration")
    with output.open("x",encoding="utf8") as out:
        json.dump(report,out,indent=2,ensure_ascii=False);out.write("\n")
    return {"status":"VALIDATED_PREVIOUS_ORIGINAL_GEMINI_REVIEW_IMPORTED",
            "slide":slide,"utterances":len(utterances),
            "new_immutable_receipt_sha256":_sha(output),
            "academic_second_pass_completed":False,
            "student_publication_authorized":False}

def main(argv=None):
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("--folder",required=True,type=Path)
    a.add_argument("--queue-root",required=True,type=Path)
    a.add_argument("--status",action="store_true")
    a.add_argument("--slide",type=int)
    a.add_argument("--mode",default="INITIAL_REVIEW",
                   choices=["INITIAL_REVIEW","INDEPENDENT_CHALLENGE"])
    a.add_argument("--attempt",type=int,default=1)
    a.add_argument("--import-prior-first-pass",type=Path)
    a.add_argument("--execute-gemini-web",action="store_true")
    args=a.parse_args(argv)
    if args.status:
        result=summarize_queue(queue_root=args.queue_root,folder=args.folder)
    elif args.import_prior_first_pass is not None:
        result=import_prior_source_verified_pass(queue_root=args.queue_root,
            folder=args.folder,slide=args.slide,prior=args.import_prior_first_pass)
    else:
        require(args.execute_gemini_web,
                "Explicit Gemini-web invocation required; queue status is read-only")
        result=execute_one_review(queue_root=args.queue_root,folder=args.folder,
            slide=args.slide,mode=args.mode,attempt=args.attempt)
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return 0 if result["status"]!="FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED" else 2

if __name__=="__main__":
    raise SystemExit(main())
