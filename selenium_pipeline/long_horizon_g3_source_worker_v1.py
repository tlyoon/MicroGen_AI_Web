"""Long-horizon G3 physical-source continuation with independent per-section holds.

Runs only the established, immutable publisher-PDF quotation witness.  This
worker NEVER talks to a model or TTS service, changes source inputs, approves
physics, synthesizes audio, edits MP4, or publishes students' content.
Work can safely restart after killed processes: recompute remaining work from
the original SHA-bound unit receipts, never from possibly interrupted summary.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .figure_source_identity import _sha,require
from .g3_source_quote_bounded_continuation_v1 import continue_quotes
from .three_pc_worker import LocalInstanceLock
from .recovery_registry import lookup_mechanism

KIND="long_horizon_g3_source_continuation"
SIGNATURE="G2_MODEL_SEND_HELD_G3_SOURCE_WORK_MUST_AUTONOMOUSLY_CONTINUE"
MECHANISM="RESUME_INDEPENDENT_G3_SOURCE_ONLY_SCOPES_WITH_IMMUTABLE_CHECKPOINTS"
STATUS="G3_LONG_HORIZON_SOURCE_ONLY_IN_PROGRESS_NO_APPROVAL"
DONE="G3_LONG_HORIZON_SOURCE_SCOPES_FULLY_STAGED_NOT_SCIENTIFICALLY_ACCEPTED"
MAX_ROUNDS=64


def _read(path:Path)->dict:
    require(path.is_file() and not path.is_symlink()
            and 0<path.stat().st_size<1_000_000,"Untrusted historical G3 report")
    value=json.loads(path.read_text(encoding="utf8"))
    require(type(value) is dict,"Historical G3 report is malformed")
    return value


def _save(path:Path,payload:dict)->None:
    require(not path.is_symlink(),"No redirected G3 progress receipt")
    path.parent.mkdir(parents=True,exist_ok=True)
    data=(json.dumps(payload,sort_keys=True,indent=2,ensure_ascii=False,
                     allow_nan=False)+"\n").encode("utf8")
    tmp=path.with_name(path.name+".pending")
    require(not tmp.is_symlink(),"No redirected G3 pending receipt")
    with tmp.open("wb") as file:
        file.write(data)
        file.flush()
        os.fsync(file.fileno())
    os.replace(tmp,path)


def _spec_one(*,row:dict,archive_root:Path,state_root:Path)->dict:
    require(type(row) is dict,"Malformed original G3 subsection")
    mapping={"Serway_8_2":"8_2","Serway_8_3":"8_3"}
    section=row.get("section")
    require(section in mapping,"Unexpected G3 subsection")
    source=archive_root/mapping[section]
    draft=row["element_mapping_source_review"]
    prior=row["publisher_quote_mapping_recovery"]
    total=prior["original_ambiguous_utterance_count"]
    require(type(total) is int and 0<total<=1000
            and draft["status"]=="G3_ORIGINAL_SOURCE_ELEMENT_MAPPING_REVIEW_STAGED_NO_TTS"
            and prior["status"]=="G3_SOURCE_PHYSICAL_CONTEXT_INCREMENTALLY_STAGED_NO_APPROVAL"
            and prior["source_scientific_QA_complete"] is False
            and prior["student_publication_authorized"] is False,
            "G3 original source-only receipt cannot approve physics")
    hashes={name:draft[name.replace(".pdf","").replace(".txt","")+"_sha256"]
            for name in ("source.pdf","slides.pdf","script.txt")}
    # The primary Google Drive 8.3 output changed after this report;
    # only the preserved original archivally matched bytes are allowed.
    require(source.is_dir() and not source.is_symlink()
            and all((source/name).is_file() and not (source/name).is_symlink()
                    and _sha(source/name)==sha
                    for name,sha in hashes.items()),
            "Original archived source/slide/script hash drift; HOLD THIS section")
    receipt=Path(draft["draft_receipt"]).absolute()
    require(receipt.is_file() and not receipt.is_symlink()
            and receipt.is_relative_to(state_root/
                "g3_original_element_review_drafts_v1"/section),
            "Original element draft is outside owned immutable G3 state")
    return {"section":section,"source_folder":source,
            "draft_receipt":receipt,"source_hashes":hashes,"total":total}


def run(*,original_report:Path,archive_root:Path,state_root:Path,
        report_root:Path,max_rounds:int=MAX_ROUNDS,
        continuation_fn=None)->dict:
    require(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
            "Independent long-horizon source-repair handler not registered")
    require(type(max_rounds) is int and 1<=max_rounds<=MAX_ROUNDS,
            "Unbounded original source worker run")
    original_report,archive_root,state_root,report_root=map(
        lambda p:Path(p).absolute(),
        (original_report,archive_root,state_root,report_root))
    require(archive_root.is_dir() and state_root.is_dir()
            and not archive_root.is_symlink() and not state_root.is_symlink()
            and not report_root.is_symlink()
            and not report_root.is_relative_to(archive_root)
            and not report_root.is_relative_to(state_root),
            "G3 source worker must not overwrite source or unit checkpoint")
    resume=continuation_fn or continue_quotes
    report_root.mkdir(parents=True,exist_ok=True)
    with LocalInstanceLock("g3_long_horizon_physical_source",report_root):
        # A broken section should not prevent source work on the other one.
        # But a malformed entire original manifest is not runnable at all.
        original=_read(original_report)
        sections=original.get("source_bound_actual_highlight_recovery")
        require(type(sections) is list and len(sections)==2,
                "Two original G3 evidence sections are required")
        names={"Serway_8_2":"8_2","Serway_8_3":"8_3"}
        require({s.get("section") for s in sections if type(s) is dict}==set(names),
                "G3 section set changed")
        current={};closed=set();held=set();counts={n:0 for n in names}
        rounds=0
        for _ in range(max_rounds):
            progressed=False
            for section in sorted(names):
                if section in closed or section in held:
                    continue
                try:
                    row=next(x for x in sections if x["section"]==section)
                    # Verify each section independently so one changed input
                    # can never prevent unrelated original PDF work.
                    spec=_spec_one(row=row,archive_root=archive_root,
                                   state_root=state_root)
                    result=resume(
                        source_folder=spec["source_folder"],
                        state_root=state_root,section=section,
                        draft_receipt=spec["draft_receipt"],
                        source_hashes=spec["source_hashes"],
                        expected_remaining=spec["total"],
                        max_batches=1,resume_from_saved=True)
                    require(result["status"]==
                            "G3_BOUNDED_SOURCE_PHYSICAL_QUOTE_CONTINUATION_NO_APPROVAL"
                            and result["student_publication_authorized"] is False
                            and result["source_scientific_QA_complete"] is False
                            and result["new_browser_sends"]==0
                            and result["new_paid_gemini_API_calls"]==0,
                            "Long-horizon worker cannot fabricate acceptance or model Sends")
                    remaining=result["remaining_unprocessed_ambiguous_tasks"]
                    new=result["new_source_quote_tasks_staged"]
                    recovered=result["prior_unfinalized_scopes_recovered"]
                    require(type(new) is int and 0<=new<=2
                            and type(recovered) is int and recovered>=0
                            and type(remaining) is int and remaining>=0
                            and new+recovered+remaining==spec["total"],
                            "Saved physical G3 source scopes do not reconcile")
                    current[section]={"status":"SOURCE_SCOPE_COMPLETE" if remaining==0 else
                                       "SOURCE_SCOPE_PENDING",
                                      "remaining":remaining,"total":spec["total"],
                                      "recovered_existing":recovered,
                                      "new_this_round":new,
                                      "student_publication_authorized":False}
                    counts[section]+=new
                    if remaining==0:
                        closed.add(section)
                    elif new==0:
                        held.add(section)
                        current[section]["status"]="NO_SOURCE_PROGRESS_HOLD"
                    else:
                        progressed=True
                except Exception as err:
                    current[section]={"status":"SOURCE_SCOPE_HELD",
                                      "error_class":type(err).__name__,
                                      "remaining":None,
                                      "student_publication_authorized":False}
                    held.add(section)
            rounds+=1
            result={"schema_version":1,
                    "status":DONE if closed==set(names) else STATUS,
                    "source_only_completed":closed==set(names),
                    "source_sections":current,
                    "new_source_scopes_in_this_run":counts,
                    "rounds_completed":rounds,
                    "held_sections":sorted(held),
                    "original_source_report_sha256":_sha(original_report),
                    "new_browser_sends":0,"new_paid_gemini_API_calls":0,
                    "source_scientific_QA_complete":False,
                    "independent_acoustic_QA_complete":False,
                    "independent_video_highlight_QA_complete":False,
                    "student_publication_authorized":False}
            _save(report_root/"g3_long_horizon_progress.json",result)
            if closed==set(names) or not progressed:
                break
        return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-report",type=Path,required=True)
    parser.add_argument("--archive-root",type=Path,required=True)
    parser.add_argument("--state-root",type=Path,required=True)
    parser.add_argument("--report-root",type=Path,required=True)
    parser.add_argument("--max-rounds",type=int,default=MAX_ROUNDS)
    args=parser.parse_args(argv)
    result=run(original_report=args.original_report,
               archive_root=args.archive_root,state_root=args.state_root,
               report_root=args.report_root,max_rounds=args.max_rounds)
    print(json.dumps(result,indent=2))
    return 0 if result["source_only_completed"] else 2

if __name__=="__main__":
    raise SystemExit(main())

