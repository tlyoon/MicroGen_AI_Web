"""HP Serway 1-7 long-horizon generation supervisor v2 (source-hash pinned).

Runs the whole Selenium -> slide -> narration -> approved paid TTS ->
approved paid Gemini 3.8 Flash audio QA -> MP4 pipeline in the authentic HP
Chrome session. All originals are preserved. Never blindly replays an
uncertain Gemini Send. A repeated Windows task tick resumes a safe checkpoint.
"""
from __future__ import annotations
import collections,datetime,hashlib,json,msvcrt,os,re,subprocess,sys,time,traceback
from pathlib import Path
from typing import Any
ROOT=Path(r"G:\My Drive\Serway\Serway_1_7")
COORD=ROOT/".microgen_ch1_7_coordination"
REPO=Path(__file__).resolve().parent.parent  # CI-merged source, not a private stale runtime clone
PYTHON=Path(r"C:\Users\tlyoo\miniforge3\envs\microgen_ai\python.exe")
STATE=COORD/"autonomous_hp_full_pipeline_v2.json"
PIN_RECORD=COORD/"verified_runtime_pin_v2.json"
LOCK=Path(r"C:\Users\tlyoo\AppData\Local\Microvid\ch1_7_v2_supervisor.lock")
LOGDIR=COORD/"v2_full_pipeline_logs"
MAX_JOB_SECONDS=3*60*60
RETRY_SAFE_MINUTES=20
TTS_MODEL="gemini-3.8-flash-lite-tts"
QA_MODEL="gemini-3.8-flash"
TASK="MicroGen_Serway_Ch1_7_HP_20261127"
def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def digest(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
def atom(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True)
 t=p.with_name("."+p.name+".pending")
 with t.open("w",encoding="utf8") as f:
  json.dump(obj,f,indent=2,ensure_ascii=False)
  f.write("\n");f.flush();os.fsync(f.fileno())
 os.replace(t,p)
def sources():
 found=[]
 for c in range(1,8):
  for p in sorted((ROOT/str(c)).iterdir()):
   if p.is_dir() and re.fullmatch(r"\d+\.\d+",p.name):
    f=p/"source.pdf"
    if not f.is_file():raise RuntimeError("MISSING_IMMUTABLE_SOURCE_"+p.name)
    found.append((p.name,digest(f)))
 if len(found)!=46 or len({x[0] for x in found})!=46:
  raise RuntimeError("EXPECTED_EXACTLY_46_SERWAY_SUBCHAPTER_SOURCES")
 return found
def gitpin():
 o=json.loads(PIN_RECORD.read_text("utf8"))
 if o.get("repo")!=str(REPO) or not re.fullmatch("[a-f0-9]{40}",str(o.get("sha",""))):
  raise RuntimeError("INVALID_VERIFIED_RUNTIME_PIN")
 p=subprocess.run(["git","rev-parse","HEAD"],cwd=REPO,capture_output=True,text=True,timeout=30)
 if p.returncode or p.stdout.strip()!=o["sha"]:
  raise RuntimeError("UNVERIFIED_REPO_REVISION_NO_GENERATION")
 return o["sha"]
def media_complete(folder):
 from selenium_pipeline.youtube_multipart_recovery_v2 import ordered_narrated_parts
 from selenium_pipeline.cleanup import completed_lecture
 if not (folder/"lecture_parts_manifest.json").is_file():
  return None
 if not completed_lecture(folder/"source.pdf"):
  return None
 parts=ordered_narrated_parts(folder,explicit_skip_highlight_qa=True)
 if not parts: return None
 return [{"filename":x["filename"],"sha256":x["sha256"],
          "duration_seconds":x["duration_seconds"]} for x in parts]
def safe_retry(error):
 return ("PRE_SEND_" in error and "NO_SEND" in error) or (
  "SOURCE_FIGURE_" in error and
  ("NO_SEND" in error or "BOUND" in error or "CROPS" in error))
def external_uncertain(error):
 return any(x in error.upper() for x in (
  "UNCERTAIN_RESULT","REQUEST_OUTCOME_UNCERTAIN",
  "DO_NOT_REPLAY","INFLIGHT_UNCERTAIN","TIMEOUT_OUTCOME_UNCERTAIN",
  "SINGLE_PROVIDER_SEND_UNCERTAIN","UNKNOWN_PROVIDER_OUTCOME"))
def bootstrap(srcs,pin):
 if STATE.exists():
  v=json.loads(STATE.read_text("utf8"))
  assert v.get("schema")=="serway_hp_full_pipeline_v2"
  assert [x[0] for x in srcs]==v["ordered_subchapters"]
  for k,h in srcs:
   assert v["jobs"][k]["source_sha256"]==h, "SOURCE_PDF_CHANGED_"+k
  return v
 prev=COORD/"autonomous_hp_generation_state.json"
 prevobj=json.loads(prev.read_text("utf8")) if prev.is_file() else None
 v={"schema":"serway_hp_full_pipeline_v2","created_utc":utc(),
    "source_root":str(ROOT),"code_sha":pin,
    "required_stages":["figures","slides","narration","script_qa","tts","tts_qa","video"],
    "standing_audio_qa_model":QA_MODEL,"state":"AUDIT",
    "ordered_subchapters":[k for k,h in srcs],"jobs":{},
    "current":None,"publication_queue":[]}
 for k,h in srcs:
  previous=prevobj["jobs"].get(k,{}) if prevobj else {}
  # Historical Chapter 1-7 failures were all before the provider Send.
  # Reject any other historical failure instead of a blind retry.
  logs=[str(x.get("last_error_tail","")) for x in [previous]]
  historical_safe=previous.get("status")=="BLOCKED_PASS2" and all(
      "PRE_SEND_MODEL_FALLBACK_NOT_AUTHORIZED_WITHOUT_EXACT_MENU_EVIDENCE" in s for s in logs)
  status=("PENDING" if not previous or historical_safe or
          previous.get("status")=="TTS_VERIFIED" else "QUARANTINED_HISTORICAL_UNKNOWN")
  v["jobs"][k]={"source_sha256":h,"status":status,
                "historical_status":previous.get("status"),
                "attempts":[],"last_error":None,"retry_after_utc":None}
 atom(STATE,v)
 return v
def persist(v):
 v["updated_utc"]=utc()
 statuses=collections.Counter(job["status"] for job in v["jobs"].values())
 v["summary"]={"total":46,"verified_videos":statuses["VIDEO_VERIFIED"],
              "pending":statuses["PENDING"],"blocked":sum(n for s,n in statuses.items()
                 if s.startswith("BLOCKED") or s.startswith("QUARANTINED")),
              "running":v["current"],"counts":dict(statuses)}
 atom(STATE,v)
 print("CHECKPOINT",v["state"],v["summary"],flush=True)
def reconcile(v,srcs):
 sys.path.insert(0,str(REPO))
 for k,h in srcs:
  folder=ROOT/k.split(".")[0]/k
  entry=v["jobs"][k]
  # Only a previously ACKNOWLEDGED figure-mapping response that was rejected
  # during a post-Send duplicate-figure publication collision may be resumed
  # via the distinct new SHA-verified SOURCE-ONLY v3 figure route. It must
  # never repeat that old page-model Send. Constrain by section, source hash,
  # exact historical log, current protected source registry, and source
  # pixel+caption figure verification. Other uncertain outcomes stay parked.
  if (k=="1.2" and entry["status"]=="QUARANTINED_MANUAL_RECONCILIATION"
       and entry["source_sha256"]==
        "814ce3e174b730271b04bbec4284bb4a15930d5026a2fcbb5148e0cf5ec018cb"
       and entry["attempts"] and
       entry["attempts"][-1].get("code_sha")!=gitpin()):
   from selenium_pipeline.source_bound_v3_repair import registered_and_complete
   from selenium_pipeline.source_caption_figure_chain_v1 import verify_figure_crops
   oldlog=folder/".microgen_work"/"microgen_figures.log"
   original=Path(entry["attempts"][-1]["log"])
   try:
    hist=oldlog.read_text("utf8",errors="replace")
    parent=original.read_text("utf8",errors="replace")
    covered=registered_and_complete(folder/"source.pdf")
    crop=(verify_figure_crops(folder/".microgen_work")
          if covered else {})
    source_match=(
      covered and crop.get("status")=="ALL_PRINTED_SOURCE_FIGURE_CROPS_VERIFIED"
      and crop.get("figure_count")==4)
    mapped=(
      "Mapping response confirmed" in hist
      and "existing_figure_conflicts_with_new_crop" in hist
      and "map_and_rename_selenium_v8.py" in parent)
    if source_match and mapped:
     entry["status"]="BLOCKED_SOURCE"
     entry["safe_no_send_reconciliation"]={
       "at_utc":utc(),"old_model_response":"ACKNOWLEDGED_AND_NOT_REPLAYED",
       "old_map_failure":"POST_SEND_FIGURE_COLLISION",
       "new_handler":"SOURCE_SHA_PINNED_V3_CROPS_NO_LEGACY_MAPPING_SEND",
       "old_repo_sha":entry["attempts"][-1]["code_sha"],
       "new_verified_repo_sha":gitpin()}
     print("RECONCILED_SAFE_SOURCE_ONLY_V3_NO_OLD_GEMINI_REPLAY",k,flush=True)
   except (OSError,ValueError,KeyError) as exc:
    print("PRESERVED_UNCERTAIN_MAP_HISTORY",k,type(exc).__name__,flush=True)
  # A second specific historical case: Section 1.6 reached the exact
  # owned Neon Medium picker but all three slide attempts terminated at
  # the pre-Send thinking-selector boundary. The original model was never
  # submitted. Revalidate the immutable original log before a bounded retry
  # under a NEW certified code revision. Never generalize this exemption
  # to a captured or uncertain Gemini response.
  if (k=="1.6" and entry["status"]=="QUARANTINED_MANUAL_RECONCILIATION"
      and len(entry["attempts"])==1
      and entry["attempts"][-1].get("code_sha")!=gitpin()):
   oldslide=folder/".microgen_work"/"microgen_slides.log"
   parent=Path(entry["attempts"][-1]["log"])
   try:
    detail=oldslide.read_text("utf8",errors="replace")
    ancestor=parent.read_text("utf8",errors="replace")
    count=detail.count("VERIFIED_PRE_SEND_FAILURE")
    no_provider_send=not any(marker in detail for marker in (
       "Gemini submission registered","Gemini wait:","response_captured",
       "Gemini response received","PROVIDER_SEND_ACCEPTED"))
    stages=(
      "OWNED_MEDIUM_THINKING_SELECTION" in detail and
      "Failed to produce a valid Beamer slide stack after all attempts" in detail
      and "gen_slides_selenium_v11.py" in ancestor)
    if count==3 and no_provider_send and stages:
     entry["status"]="BLOCKED_PRE_SEND"
     entry["retry_after_utc"]=None
     entry["safe_no_send_reconciliation"]={
       "at_utc":utc(),"evidence":"3/3 explicitly VERIFIED_PRE_SEND_FAILURE",
       "source_stage":"slides","failure":"OWNED_MEDIUM_THINKING_SELECTION",
       "no_model_send":True,"old_repo_sha":entry["attempts"][-1]["code_sha"],
       "new_repo_sha":gitpin()}
     print("RECONCILED_SAFE_PRE_SEND_NEON_MEDIUM_PICKER",k,flush=True)
   except (OSError,ValueError,KeyError) as exc:
    print("PRESERVE_UNRECONCILED_1_6",type(exc).__name__,flush=True)
  try: parts=media_complete(folder)
  except (OSError,ValueError,RuntimeError) as e:
   entry["media_audit_error"]=type(e).__name__+":"+str(e)[:300]
   parts=None
  if parts:
   entry["status"]="VIDEO_VERIFIED"
   entry["accepted_parts"]=parts
   entry["video_verified_utc"]=utc()
  elif entry["status"]=="RUNNING":
   entry["status"]="QUARANTINED_INTERRUPTED_OR_EXTERNAL_OUTCOME"
   entry["last_error"]="Prior process ended without verified completion; reconcile provider ledger and original checkpoint before retry"
  elif entry["status"]=="VIDEO_VERIFIED":
   entry["status"]="QUARANTINED_PREVIOUS_MEDIA_CHANGED"
   entry["last_error"]="Previously accepted part missing or changed"
 v["current"]=None
 v["publication_queue"]=[k for k in v["ordered_subchapters"]
  if v["jobs"][k]["status"]=="VIDEO_VERIFIED"]
 persist(v)
def evaluate(entry,pin):
 if entry["status"]=="VIDEO_VERIFIED":return False
 if entry["status"]=="QUARANTINED_INTERRUPTED_OR_EXTERNAL_OUTCOME":return False
 if entry["status"].startswith("QUARANTINED"):return False
 tries=entry["attempts"]
 if not tries:return True
 last=tries[-1]
 if last.get("code_sha")!=pin and entry["status"]=="BLOCKED_SOURCE":
  return True
 if entry["status"] not in ("BLOCKED_PRE_SEND","BLOCKED_SOURCE","PENDING"):
  return False
 if entry["status"]=="BLOCKED_SOURCE":
  # A repeated source-only crop without a new source-specific recovery
  # registry revision adds no evidence and just loops forever.
  return False
 if entry["status"]=="BLOCKED_PRE_SEND" and len(tries)>=3:
  # One retry per *different* verified merged repair revision only, after
  # reading the exact historical no-Send failure log and source SHA.
  from selenium_pipeline.safe_presend_retry_v1 import verified_new_code_presend_retry
  return verified_new_code_presend_retry(entry,pin,LOGDIR)
 if entry.get("retry_after_utc"):
  return utc()>=entry["retry_after_utc"]
 return True
def run_sub(v,k,pin):
 f=ROOT/k.split(".")[0]/k
 entry=v["jobs"][k]
 n=len(entry["attempts"])+1
 log=LOGDIR/f"{k}_v2_attempt{n}.log"
 args=[str(PYTHON),"-X","utf8","-u","-m","selenium_pipeline",
   "--source-root",str(ROOT),"--subchapter",k,
   "--communication-mode","selenium",
   "--tts-model",TTS_MODEL,"--tts-qa-model",QA_MODEL,
   "--tts-qa-threshold","99","--through-stage","video"]
 env=dict(os.environ)
 env["MICROGEN_COMMUNICATION_MODE"]="selenium"
 env["PYTHONUNBUFFERED"]="1"
 env["PYTHONNOUSERSITE"]="1"
 record={"attempt":n,"code_sha":pin,"started_utc":utc(),
   "source_sha256":entry["source_sha256"],"log":str(log),"state":"DISPATCHING"}
 entry["attempts"].append(record)
 entry["status"]="RUNNING";v["current"]=k;v["state"]="GENERATION_RUNNING";persist(v)
 with log.open("x",encoding="utf8",errors="replace") as output:
  output.write(" ".join(args)+"\n");output.flush()
  proc=subprocess.Popen(args,stdin=subprocess.DEVNULL,
                        stdout=output,stderr=subprocess.STDOUT,
                        cwd=REPO,env=env)
  record["pid"]=proc.pid;record["state"]="IN_PROGRESS";persist(v)
  try:
   rc=proc.wait(timeout=MAX_JOB_SECONDS)
  except subprocess.TimeoutExpired:
   proc.terminate()
   try: proc.wait(timeout=25)
   except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=10)
   record["state"]="TIMEOUT_OUTCOME_UNCERTAIN"
   rc=None
 record["ended_utc"]=utc();record["returncode"]=rc
 data=log.read_text("utf8",errors="replace")
 tail="\n".join(data.splitlines()[-60:])
 entry["last_error"]=tail[-4000:] if rc else None
 if rc==0:
  try:
   parts=media_complete(f)
   if parts:
    entry["accepted_parts"]=parts
    entry["status"]="VIDEO_VERIFIED"
    entry["video_verified_utc"]=utc()
    record["state"]="VERIFIED_VIDEO_COMPLETED"
   else:
    entry["status"]="QUARANTINED_MEDIA_COMPLETION_MISMATCH"
    record["state"]="UNVERIFIED_EXIT_ZERO"
  except Exception as e:
   entry["status"]="QUARANTINED_MEDIA_AUDIT_ERROR"
   entry["last_error"]=str(e)
   record["state"]="MEDIA_AUDIT_FAILED"
 elif record["state"]=="TIMEOUT_OUTCOME_UNCERTAIN" or external_uncertain(tail):
  entry["status"]="QUARANTINED_EXTERNAL_OUTCOME_UNCERTAIN"
 elif "PRE_SEND_" in tail and "NO_SEND" in tail:
  entry["status"]="BLOCKED_PRE_SEND"
  entry["retry_after_utc"]=(
    datetime.datetime.now(datetime.timezone.utc)+
    datetime.timedelta(minutes=RETRY_SAFE_MINUTES)).isoformat()
 elif ("SOURCE_FIGURE_" in tail and "FigureChainError" in tail):
  entry["status"]="BLOCKED_SOURCE"
 else:
  entry["status"]="QUARANTINED_MANUAL_RECONCILIATION"
  record["state"]="FAILED_NOT_SAFE_TO_REPLAY"
 v["current"]=None
 v["state"]="AUDIT_AFTER_ATTEMPT";persist(v)
def run_once():
 if not REPO.is_dir() or not PYTHON.is_file():
  raise RuntimeError("MISSING_REQUIRED_WINDOWS_RUNNER")
 pin=gitpin()
 srcs=sources()
 v=bootstrap(srcs,pin)
 reconcile(v,srcs)
 LOGDIR.mkdir(exist_ok=True)
 for k,h in srcs:
  e=v["jobs"][k]
  if evaluate(e,pin):
   run_sub(v,k,pin)
   # Continue with next independently eligible source, even after
   # one deterministic local failure; never throw away safe progress.
 v["state"]=("ALL_46_VIDEOS_VERIFIED_PUBLICATION_PENDING" if
   all(e["status"]=="VIDEO_VERIFIED" for e in v["jobs"].values()) else
   "AWAITING_SAFE_RETRY_OR_VERIFIED_CODE_REPAIR")
 persist(v)
 print("HANDOFF",v["state"],"VIDEO_VERIFIED",v["summary"]["verified_videos"],
       "NEXT_PUBLICATION_QUEUE",v["publication_queue"],flush=True)
def main():
 COORD.mkdir(parents=True,exist_ok=True)
 with LOCK.open("a+b") as fd:
  fd.seek(0)
  if fd.read(1)==b"":
   fd.seek(0);fd.write(b".");fd.flush()
  try:
   fd.seek(0);msvcrt.locking(fd.fileno(),msvcrt.LK_NBLCK,1)
  except OSError:
   print("ALREADY_RUNNING_SAFE_EXIT",flush=True)
   return 0
  try:run_once()
  finally:
   fd.seek(0);msvcrt.locking(fd.fileno(),msvcrt.LK_UNLCK,1)
 return 0
if __name__=="__main__":
 try:raise SystemExit(main())
 except BaseException as e:
  print("SUPERVISOR_ERROR",type(e).__name__,str(e),flush=True)
  traceback.print_exc()
  raise
