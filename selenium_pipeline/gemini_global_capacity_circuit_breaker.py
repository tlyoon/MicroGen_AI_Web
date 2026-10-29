"""Offline capacity circuit breaker across multiple Gemini jobs."""
from __future__ import annotations
def capacity_circuit_state(*,terminal_receipts:list[dict],
                           now:float,window_s:int=3600,
                           threshold:int=3,cooldown_s:int=1800)->dict:
 if (type(terminal_receipts) is not list or len(terminal_receipts)>10000
     or type(now) not in (int,float) or type(window_s) is not int
     or not 60<=window_s<=86400 or threshold<2 or cooldown_s<300):
  raise ValueError("Bounded capacity observation required")
 recent=[]
 for item in terminal_receipts:
  if type(item) is not dict:raise ValueError("Untrusted capacity evidence")
  t=item.get("verified_terminal_utc")
  if (type(t) not in (int,float) or t>now or
      item.get("same_owned_session_verified") is not True):
   continue
  if now-window_s<=t<=now and item.get("category") in (
      "SERVER_BUSY_429","SERVER_UNAVAILABLE_503"):
   recent.append(item)
 latest=max((x["verified_terminal_utc"] for x in recent),default=None)
 blocked=len(recent)>=threshold and now<latest+cooldown_s
 return {"status":"OPEN_CAPACITY_COOLDOWN" if blocked else "CLOSED_NO_CAPACITY_STOP",
         "verified_capacity_failures_in_window":len(recent),
         "next_global_eligible_utc":latest+cooldown_s if blocked else None,
         "model_dispatch_authorized":False,
         "student_publication_authorized":False}
