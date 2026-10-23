"""Dell-115 safe one-shot Gemini browser health check for ONE approved window.

Dry-read-only by default. Does not attempt academic review or TTS.
Use --allow-one-browser-canary only after a distinct user-approved scope.
"""
import argparse,json
from pathlib import Path
from .scoped_original_math_review_window import inspect_window
from .one_shot_gemini_source_health_probe import run_one_health_probe

def main(argv=None):
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument("--window-root",required=True,type=Path)
 ap.add_argument("--allow-one-browser-canary",action="store_true")
 args=ap.parse_args(argv)
 if not args.allow_one_browser_canary:
  status=inspect_window(window_root=args.window_root)
  print(json.dumps({"mode":"READ_ONLY_NO_GEMINI_TRAFFIC",**status},
                   sort_keys=True,indent=2))
  return 0
 def verified_text_transport(prompt):
  # Vendor bridge owns one browser tab and strict model-only capture.
  # On any uncertain timeout this callback throws and this diagnostic
  # receipt remains UNHEALTHY; original mathematics is NOT retried.
  from .series_gemini import _browser_request
  text=_browser_request(prompt,[],port=9222,wait_cap_s=75,min_chars=8)
  return {"raw":text,"same_owned_gemini_session":True,
          "model_stopped_generating":True}
 result=run_one_health_probe(window_root=args.window_root,
                             transport=verified_text_transport)
 print(json.dumps(result,sort_keys=True,indent=2))
 return 0

if __name__=="__main__":
 raise SystemExit(main())
