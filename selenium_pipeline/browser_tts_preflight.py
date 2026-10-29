"""Read-only Google AI Studio browser TTS capability preflight.

Does not generate speech, submit prompts, select an API key, download
model weights, import Whisper, access private lecture data or bill an API.
A page that merely advertises TTS is NOT evidence of downloadable audio.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

SURFACE="https://aistudio.google.com/generate-speech"
# The official model documentation routes this link to AI Studio; the UI
# may drop its query parameter. A deep link is NEVER selection evidence.
OFFICIAL_MODEL_LINK="https://aistudio.google.com/?model=gemini-3.8-flash-lite-tts"
ENTRYPOINTS=frozenset(("speech_ui","official_model_link"))
MODELS=frozenset({"gemini-3.8-flash-lite-tts","gemini-3.8-flash-tts"})


class BrowserTTSBlocked(RuntimeError):
    pass


def digest(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()


def local_configuration_presence(environ:dict[str,str]|None=None)->dict:
    """Inspect ONLY directory/file existence, never credential values.

    Local settings and authenticated Chrome profiles are separate from a
    Google AI Studio page displaying "No API key selected". They are not
    proofs that browser voice generation is usable or cost-free.
    """
    env=os.environ if environ is None else environ
    raw=str(env.get("LOCALAPPDATA","")).strip()
    base=Path(raw).expanduser() if raw else None
    if base is None or not base.is_dir():
        return {
            "local_microvid_config_present":False,
            "local_google_cloud_credential_file_present":False,
            "local_drive_oauth_config_present":False,
            "local_persistent_gemini_profile_present":False,
            "local_chrome_profile_present":False,
            "local_credential_contents_read":False,
            "local_credentials_not_browser_key_selection":True,
        }
    microvid=base/"Microvid"
    return {
        "local_microvid_config_present":(microvid/".env").is_file(),
        "local_google_cloud_credential_file_present":
            (microvid/"google_cloud_credentials.json").is_file(),
        "local_drive_oauth_config_present":
            (microvid/"drive-oauth-client.json").is_file(),
        "local_persistent_gemini_profile_present":
            any(p.is_dir() for p in base.glob("gemini_automation_*")),
        "local_chrome_profile_present":
            (base/"Google"/"Chrome"/"User Data").is_dir(),
        "local_credential_contents_read":False,
        "local_credentials_not_browser_key_selection":True,
    }


def validate_request(*, requested_model:str, requested_voice:str)->None:
    """Fail before attaching Chrome or creating a receipt on invalid intent."""
    if requested_model not in MODELS:
        raise ValueError("Unapproved Gemini TTS model")
    if not isinstance(requested_voice,str) or not re.fullmatch(
            r"[A-Za-z][A-Za-z0-9_-]{1,30}",requested_voice):
        raise ValueError("Invalid voice")


def validate_entrypoint(entrypoint:str, requested_model:str)->None:
    if entrypoint not in ENTRYPOINTS:
        raise ValueError("Unapproved browser TTS entrypoint")
    if entrypoint=="official_model_link" and requested_model!="gemini-3.8-flash-lite-tts":
        raise ValueError("Official Flash-Lite model link requires exact Flash-Lite request")


def evaluate(snapshot:dict, *, requested_model:str,
             requested_voice:str)->dict:
    """Conservative summary of UI support. No dynamic JavaScript calls."""
    validate_request(requested_model=requested_model,
                     requested_voice=requested_voice)
    url=str(snapshot.get("url") or "")
    parsed=urlsplit(url)
    if (parsed.scheme!="https" or parsed.netloc!="aistudio.google.com"
            or parsed.path.rstrip("/")!="/generate-speech"):
        raise BrowserTTSBlocked("Wrong site: not the Google AI Studio speech GUI")
    labels=[str(x) for x in snapshot.get("control_labels",[])]
    body=str(snapshot.get("body",""))
    evidence=" ".join(labels)+" "+body
    actual_ids=sorted(set(re.findall(r"gemini-3\.8-flash(?:-lite)?-tts\b",
                                   evidence,flags=re.I)))
    no_key=any("no api key selected" in x.lower() for x in labels)
    editor_present=bool(snapshot.get("editable_count",0))
    # A composer field is not enough to prove voice, downloaded WAVs,
    # billing-free status, or the exact model generation semantics.
    result={
       "schema_version":1,
       "status":"BROWSER_TTS_GENERATION_UNVERIFIED",
       "provider":"google_ai_studio_browser_ui",
       "observed_surface":SURFACE,
       "source_content_uploaded":False,
       "requested_model":requested_model,
       "requested_voice":requested_voice,
       "official_model_link_requested":bool(snapshot.get("official_model_link_requested",False)),
       "official_link_query_retained":bool(snapshot.get("official_link_query_retained",False)),
       "official_link_is_selection_proof":False,
       "visible_model_ids":actual_ids,
       "exact_model_visible":requested_model in actual_ids,
       "selected_model_verified":False,
       "selected_voice_verified":False,
       "voice_visible":bool(re.search(r"\b"+re.escape(requested_voice)+r"\b",
                                       evidence,flags=re.I)),
       "no_api_key_selected_visible":no_key,
       "speech_editor_available":editor_present,
       "downloadable_wav_verified":False,
       "billing_free_generation_verified":False,
       "submitted_generation_request":False,
       "api_called_by_microgen":False,
       "usable_for_automatic_element_tts":False,
       "source_audio_or_slides_modified":False,
       "requires_independent_browser_audio_proof":True,
       "human_academic_approval":False,
       "student_publication":False,
    }
    reasons=[]
    if not result["exact_model_visible"]:
        reasons.append("requested_model_not_visible_as_exact_model")
    if not result["voice_visible"]:
        reasons.append("requested_voice_not_confirmed")
    if no_key:reasons.append("no_api_key_selected")
    if not editor_present:reasons.append("speech_editor_not_available")
    reasons.extend(("selected_model_not_verified",
                    "selected_voice_not_verified",
                    "downloadable_wav_not_verified",
                    "billing_free_generation_not_verified"))
    result["blockers"]=reasons
    return result


def browser_snapshot(*, port:int=9222, timeout_s:int=25,
                     entrypoint:str="speech_ui")->dict:
    """Only open/close an owned tab; never click Run or add a key."""
    validate_entrypoint(entrypoint,"gemini-3.8-flash-lite-tts")
    if not 1<=port<=65535 or not 8<=timeout_s<=60:
        raise ValueError("Invalid bounded Chrome settings")
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
    except ImportError as exc:
        raise BrowserTTSBlocked("selenium_python_dependency_unavailable") from exc
    from .three_pc_worker import LocalInstanceLock
    opts=Options()
    opts.add_experimental_option("debuggerAddress",f"127.0.0.1:{port}")
    cache=Path(os.environ.get("LOCALAPPDATA") or Path.home()/".cache")
    with LocalInstanceLock(f"gemini_port_{port}",
                           cache/"Microvid"/"browser_locks"):
        try:
            driver=webdriver.Chrome(options=opts)
        except Exception as exc:
            raise BrowserTTSBlocked("authenticated_chrome_debugger_unavailable") from exc
        prior=driver.current_window_handle
        owned=None
        try:
            driver.switch_to.new_window("tab")
            owned=driver.current_window_handle
            driver.get(SURFACE if entrypoint=="speech_ui" else OFFICIAL_MODEL_LINK)
            deadline=time.monotonic()+timeout_s
            model_seen=False
            while time.monotonic()<deadline:
                try:
                    model_seen="gemini-3.8-flash" in (
                        driver.find_element(By.TAG_NAME,"body").text.lower())
                except Exception:
                    model_seen=False
                if model_seen:break
                time.sleep(.5)
            controls=[]
            for item in driver.find_elements(By.CSS_SELECTOR,
                "button,[role='button'],[role='combobox']"):
                try:
                    if not item.is_displayed():continue
                    title=(item.get_attribute("aria-label") or
                           item.get_attribute("title") or item.text or "")
                    if title:controls.append(title[:180])
                except Exception:pass
            # Only allowlist relevant UI terms. Do NOT capture account
            # identity, conversations, tokens, private file names or email.
            model_labels=[x for x in controls if "gemini-3.8-flash" in x.lower()]
            key_labels=[x for x in controls if "no api key selected" in x.lower()]
            editor_count=sum(1 for e in driver.find_elements(
                By.CSS_SELECTOR,"textarea,[contenteditable='true']") if e.is_displayed())
            final_url=urlsplit(driver.current_url)
            # Do not record arbitrary URL queries: they can contain session
            # state. Record only a boolean for the official model parameter.
            query_matches=(final_url.scheme=="https"
                and final_url.netloc=="aistudio.google.com"
                and parse_qs(final_url.query).get("model")
                ==["gemini-3.8-flash-lite-tts"])
            return {"url":driver.current_url.partition("?")[0],
                    "control_labels":model_labels+key_labels,
                    "body":"", "editable_count":editor_count,
                    "official_model_link_requested":entrypoint=="official_model_link",
                    "official_link_query_retained":query_matches}
        finally:
            try:
                if owned:
                    driver.switch_to.window(owned)
                    driver.close()
                driver.switch_to.window(prior)
            except Exception:pass
            try:driver.quit()
            except Exception:pass


def preflight(*,requested_model:str,requested_voice:str,output:Path,
              transport=None,port:int=9222,timeout_s:int=25,
              entrypoint:str="speech_ui",
              source_root:Path|None=None,
              local_environ:dict[str,str]|None=None)->dict:
    validate_request(requested_model=requested_model,
                     requested_voice=requested_voice)
    validate_entrypoint(entrypoint,requested_model)
    proposed=Path(output)
    if proposed.is_symlink():
        raise ValueError("Preflight receipt must be a new isolated file")
    output=proposed.resolve()
    if output.exists() or not output.parent.is_dir():
        raise ValueError("Preflight receipt must be a new isolated file")
    if source_root is not None and output.is_relative_to(Path(source_root).resolve()):
        raise ValueError("Never create a browser probe inside the textbook source")
    try:
        snapshot=(transport or browser_snapshot)(port=port,timeout_s=timeout_s,
                                                  entrypoint=entrypoint)
    except BrowserTTSBlocked as exc:
        reason=str(exc)
        if reason not in ("selenium_python_dependency_unavailable",
                          "authenticated_chrome_debugger_unavailable",
                          "browser_ui_unavailable"):
            reason="browser_ui_unavailable"
        # Unlike a capability probe, an environment failure cannot attest
        # which model/voice/key is selected. Never invent UI observations.
        report={
            "schema_version":1,
            "status":"BROWSER_TTS_PREFLIGHT_UNAVAILABLE",
            "provider":"google_ai_studio_browser_ui",
            "requested_model":requested_model,
            "requested_voice":requested_voice,
            "official_model_link_requested":entrypoint=="official_model_link",
            "official_link_query_retained":False,
            "official_link_is_selection_proof":False,
            "observed_surface":None,
            "visible_model_ids":[],
            "exact_model_visible":False,
            "selected_model_verified":False,
            "selected_voice_verified":False,
            "voice_visible":False,
            "no_api_key_selected_visible":False,
            "speech_editor_available":False,
            "downloadable_wav_verified":False,
            "billing_free_generation_verified":False,
            "submitted_generation_request":False,
            "api_called_by_microgen":False,
            "usable_for_automatic_element_tts":False,
            "source_content_uploaded":False,
            "source_audio_or_slides_modified":False,
            "requires_independent_browser_audio_proof":True,
            "human_academic_approval":False,
            "student_publication":False,
            "blockers":[reason],
        }
    else:
        report=evaluate(snapshot,requested_model=requested_model,
                        requested_voice=requested_voice)
    # Presence-only local configuration evidence. Do not infer browser
    # billing, model availability, key selection, or an authorized API call.
    report.update(local_configuration_presence(local_environ))
    with output.open("x",encoding="utf8") as f:
        json.dump(report,f,indent=2,sort_keys=True)
        f.write("\n")
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model",default="gemini-3.8-flash-lite-tts",choices=sorted(MODELS))
    p.add_argument("--voice",default="Kore")
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--source-root",type=Path,
                   help="Optional protected textbook root (never store receipts here)")
    p.add_argument("--port",type=int,default=9222)
    p.add_argument("--timeout",type=int,default=25)
    p.add_argument("--check-official-model-link",action="store_true",
                   help="Read-only official Flash-Lite deep link, never selects a model")
    a=p.parse_args(argv)
    report=preflight(requested_model=a.model,requested_voice=a.voice,
                     output=a.output,port=a.port,timeout_s=a.timeout,
                     entrypoint=("official_model_link" if a.check_official_model_link
                                 else "speech_ui"),
                     source_root=a.source_root)
    print(json.dumps(report,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
