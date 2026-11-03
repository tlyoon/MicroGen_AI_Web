"""Read-only Gemini/ChatGPT browser readiness and safe provider selection.

Inspects ONLY existing local Chrome DevTools UI sessions on the authorized
Windows machine. Never launches Chrome, logs in, submits prompts, opens tabs
or treats a guest textarea as an authenticated ChatGPT session.

Provider choice is allowed only BEFORE a first model submission. If an earlier
submission may be in flight, reconcile it; never auto-resend on another service.
"""
from __future__ import annotations
import argparse
import json
from urllib.request import urlopen

class ProviderNotReady(RuntimeError):
    pass

DEFAULT_PORTS={"gemini":9222,"chatgpt":9223}

def require(ok:bool,message:str)->None:
    if not ok:raise ProviderNotReady(message)

def inspect_provider(provider:str,port:int|None=None, *,
                     browser_factory=None,endpoint=None)->dict:
    require(provider in DEFAULT_PORTS,"Provider must be Gemini or ChatGPT")
    port=DEFAULT_PORTS[provider] if port is None else port
    require(type(port) is int and 9222<=port<=9323,
            "Only configured native Windows Chrome debug ports")
    outcome={
        "schema_version":1,
        "provider":provider,
        "debug_port":port,
        "status":"BROWSER_UNAVAILABLE",
        "authenticated_ui_ready":False,
        "source_originals_modified":False,
        "model_submission_performed":False,
        "paid_tts_authorized":False,
        "student_publication_authorized":False,
    }
    try:
        if endpoint is None:
            with urlopen(f"http://127.0.0.1:{port}/json/version",
                         timeout=2) as stream:
                info=json.loads(stream.read().decode("utf8"))
        else:
            info=endpoint(port)
        if "Chrome" not in info.get("Browser","") or not info.get(
                "webSocketDebuggerUrl",""):
            outcome["status"]="NON_CHROME_OR_NO_DEBUGGER"
            return outcome
    except (OSError,ValueError,TypeError):
        return outcome
    try:
        if browser_factory is None:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            opts=Options()
            opts.add_experimental_option(
                "debuggerAddress",f"127.0.0.1:{port}")
            driver=webdriver.Chrome(options=opts)
        else:
            driver=browser_factory(port)
    except Exception:
        outcome["status"]="CHROME_ATTACH_FAILED"
        return outcome
    try:
        seen=False
        unauthenticated=False
        for handle in list(driver.window_handles):
            try:
                driver.switch_to.window(handle)
                uri=str(driver.current_url)
                prefix=("https://gemini.google.com/" if provider=="gemini"
                        else "https://chatgpt.com/")
                if not uri.startswith(prefix):
                    continue
                seen=True
                def visible(selector):
                    return any(x.is_displayed() for x in driver.find_elements(
                        "css selector",selector))
                if provider=="gemini":
                    ok=visible('button[aria-label^="Open mode picker"]')
                    login=visible('button[aria-label="Sign in"]')
                else:
                    # Guest composer textareas are not authenticated.
                    login=visible("button[data-testid='login-button']")
                    login=login or any(
                        (x.text or "").strip().casefold() in
                            {"log in","sign up for free","sign up"}
                        for x in driver.find_elements("css selector","button")
                        if x.is_displayed())
                    ok=(visible("#prompt-textarea")
                        or visible('[data-testid="composer-text-input"]')
                        or visible('div[contenteditable="true"][role="textbox"]'))
                if ok and not login:
                    outcome["status"]="AUTHENTICATED_COMPOSER_READY"
                    outcome["authenticated_ui_ready"]=True
                    break
                if login:
                    unauthenticated=True
            except Exception:
                continue
        if not outcome["authenticated_ui_ready"]:
            outcome["status"]=("LOGIN_REQUIRED" if unauthenticated else
                "COMPOSER_NOT_READY" if seen else
                "NO_AUTHENTICATED_PROVIDER_TAB")
    finally:
        # Existing USER Chrome sessions must remain open.
        # Detach ChromeDriver service only; never quit/close/navigate tabs.
        try:
            if browser_factory is None:
                driver.service.stop()
        except Exception:
            pass
    return outcome

def choose_provider(statuses:list[dict],*,model_submission_uncertain:bool=False)->dict:
    require(type(statuses) is list and statuses
            and all(type(x) is dict for x in statuses),
            "Bounded genuine provider readiness required")
    result={
        "status":"PROVIDER_UNAVAILABLE_NO_MODEL_SUBMISSION",
        "chosen_provider":None,
        "student_publication_authorized":False,
        "paid_tts_authorized":False,
        "automatic_duplicate_submission_authorized":False,
    }
    if model_submission_uncertain:
        result["status"]="RECONCILE_EXISTING_PROVIDER_BEFORE_FALLBACK"
        return result
    by_name={x.get("provider"):x for x in statuses}
    require(len(by_name)==len(statuses)
            and set(by_name).issubset(DEFAULT_PORTS),
            "Unexpected/duplicate provider readiness")
    for name in ("gemini","chatgpt"):
        if (name in by_name and
                by_name[name].get("status")=="AUTHENTICATED_COMPOSER_READY"
                and by_name[name].get("authenticated_ui_ready") is True
                and by_name[name].get("model_submission_performed") is False):
            result["status"]="READY_TO_CLAIM_ONE_UNSENT_MODEL_JOB"
            result["chosen_provider"]=name
            break
    return result

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gemini-port",type=int,default=9222)
    ap.add_argument("--chatgpt-port",type=int,default=9223)
    args=ap.parse_args(argv)
    rows=[inspect_provider("gemini",args.gemini_port),
          inspect_provider("chatgpt",args.chatgpt_port)]
    print(json.dumps({"providers":rows,"decision":choose_provider(rows)},
                     indent=2))
if __name__=="__main__":
    main()
