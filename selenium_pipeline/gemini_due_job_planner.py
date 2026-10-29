"""Pure read-only scheduler planner; no browser, clocks or task installation."""
from pathlib import Path
from .gemini_review_backoff_checkpoint import inspect
def plan_due_retry_jobs(*,items:list[tuple[Path,Path]],now:float,
                        budget:int=1)->dict:
 if (type(items) is not list or type(budget) is not int or
     budget!=1 or type(now) not in (int,float) or not 0<=now<=1e11):
  raise ValueError("Single bounded local retry inspection required")
 rows=[];seen=set()
 for cp,original_folder in items:
  cp=Path(cp).absolute()
  if cp in seen:raise ValueError("Duplicate checkpoint in one worker tick")
  seen.add(cp)
  report=inspect(checkpoint=cp,original_folder=Path(original_folder),now=now)
  rows.append({"checkpoint":str(cp),"status":report["status"],
               "eligible":report["eligible_for_single_authorized_dispatch"],
               "due":report["next_due_unix_utc"]})
 due=sorted((x for x in rows if x["eligible"]),
            key=lambda x:(x["due"],x["checkpoint"]))
 # Never mutate or claim. This is a planner, not an attempt permission grant.
 return {"status":"READ_ONLY_GEMINI_DUE_PLAN","total":len(rows),
         "ready_count":len(due),"selected":due[:1],
         "mutation_performed":False,"model_request_sent":False,
         "student_publication_authorized":False}
