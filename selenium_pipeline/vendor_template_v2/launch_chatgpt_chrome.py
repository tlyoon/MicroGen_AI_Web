# -*- coding: utf-8 -*-
# MicroGen_AI Educational Automation Package
# (c) 2025 Dr. Yoon Tiem Leong, School of Physics, Universiti Sains Malaysia.
# This file is part of the MicroGen_AI package.
# Licensed under the MIT License (see LICENSE file in the project root).
# You may not use this file except in compliance with the License.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

import os
import sys
import time
import json
import socket
import subprocess
import urllib.request
from pathlib import Path
import importlib

DEBUG_PORT = int(os.getenv("CHATGPT_DEBUG_PORT", os.getenv("CHATGPT_DEVTOOLS_PORT", "9222")))
CHATGPT_URL = os.getenv("CHATGPT_URL", "https://chatgpt.com/")
KEEPALIVE_PROMPT = "Keep alive while waiting for my prompt"

PATH_A = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PATH_B = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

if os.path.exists(PATH_A):
    CHROME_EXE = PATH_A
elif os.path.exists(PATH_B):
    CHROME_EXE = PATH_B
else:
    CHROME_EXE = os.getenv("CHROME_EXE", PATH_A)

hostname = socket.gethostname().replace(" ", "_")
local_appdata = os.getenv("LOCALAPPDATA", r"C:\Users\Public\AppData\Local")
AUTOMATION_USER_DATA_DIR = os.path.join(local_appdata, f"chatgpt_automation_{hostname}")

LOGIN_WAIT_SECONDS = 10
PORT_WAIT_SECONDS = 15
DEVTOOLS_WAIT_SECONDS = 15


def port_in_use(port: int) -> bool:
    s = socket.socket()
    try:
        s.settimeout(0.5)
        s.connect(("127.0.0.1", port))
        return True
    except Exception:
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass


def wait_for_port(port: int, timeout: int = PORT_WAIT_SECONDS) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        if port_in_use(port):
            return True
        time.sleep(0.25)
    return False


def fetch_json(url: str, timeout: float = 2.0):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def wait_for_devtools_ready(port: int, timeout: int = DEVTOOLS_WAIT_SECONDS) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            info = fetch_json(f"http://127.0.0.1:{port}/json/version", timeout=2.0)
            browser = str(info.get("Browser", ""))
            ws_url = str(info.get("webSocketDebuggerUrl", ""))
            if "Chrome" in browser and ws_url:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def import_real_selenium():
    script_dir = str(Path(__file__).resolve().parent)
    cwd = str(Path.cwd().resolve())
    removed = []

    for p in [script_dir, cwd, ""]:
        while p in sys.path:
            sys.path.remove(p)
            removed.append(p)

    try:
        webdriver_mod = importlib.import_module("selenium.webdriver")
        by_mod = importlib.import_module("selenium.webdriver.common.by")
        keys_mod = importlib.import_module("selenium.webdriver.common.keys")
        options_mod = importlib.import_module("selenium.webdriver.chrome.options")
        service_mod = importlib.import_module("selenium.webdriver.chrome.service")
    finally:
        for p in reversed(removed):
            sys.path.insert(0, p)

    return webdriver_mod, by_mod, keys_mod, options_mod, service_mod


def launch_chrome_debug():
    if port_in_use(DEBUG_PORT):
        print(f"[INFO] Debug port {DEBUG_PORT} already active; using existing Chrome.")
        if not wait_for_devtools_ready(DEBUG_PORT, timeout=DEVTOOLS_WAIT_SECONDS):
            raise RuntimeError(
                f"Port {DEBUG_PORT} is open but DevTools endpoint is not responding.\n"
                f"Close stale Chrome/debug sessions and retry, or use another port via CHATGPT_DEBUG_PORT."
            )
        return

    if not os.path.exists(CHROME_EXE):
        raise RuntimeError(
            f"Chrome not found at: {CHROME_EXE}\n"
            f"Set environment variable CHROME_EXE to your correct chrome.exe path."
        )

    Path(AUTOMATION_USER_DATA_DIR).mkdir(parents=True, exist_ok=True)

    args = [
        CHROME_EXE,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={AUTOMATION_USER_DATA_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        CHATGPT_URL,
    ]

    print("[INFO] Launching Chrome with remote debugging for ChatGPT...")
    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print(f"[INFO] Waiting for debug port {DEBUG_PORT} to open...")
    if not wait_for_port(DEBUG_PORT, timeout=PORT_WAIT_SECONDS):
        raise RuntimeError(
            f"Chrome did not open 127.0.0.1:{DEBUG_PORT} within {PORT_WAIT_SECONDS}s.\n"
            f"Most common causes:\n"
            f"  - Another Chrome instance is locking the same profile\n"
            f"  - Security policy blocks remote debugging\n"
            f"  - Wrong Chrome executable path\n"
            f"Fix:\n"
            f"  - Close all Chrome windows and try again\n"
            f"  - Or set CHROME_EXE manually\n"
            f"  - Or set CHATGPT_DEBUG_PORT to another port"
        )

    print("[INFO] Waiting for DevTools endpoint to become ready...")
    if not wait_for_devtools_ready(DEBUG_PORT, timeout=DEVTOOLS_WAIT_SECONDS):
        raise RuntimeError(
            f"Port {DEBUG_PORT} opened, but Chrome DevTools endpoint is not ready.\n"
            f"This often means a stale/incompatible debugging session."
        )


def list_debug_targets(port: int):
    try:
        return fetch_json(f"http://127.0.0.1:{port}/json", timeout=2.0)
    except Exception:
        return []


def find_interactable_composer(driver, By, login_wait_seconds):
    candidate_selectors = [
        (By.CSS_SELECTOR, "textarea#prompt-textarea"),
        (By.CSS_SELECTOR, "textarea[data-testid='composer-text-input']"),
        (By.CSS_SELECTOR, "div#prompt-textarea[contenteditable='true']"),
        (By.CSS_SELECTOR, "div[contenteditable='true'][role='textbox']"),
        (By.CSS_SELECTOR, "div[contenteditable='true']"),
        (By.CSS_SELECTOR, "textarea"),
    ]

    t0 = time.time()
    last_error = None

    while time.time() - t0 < login_wait_seconds:
        for by, sel in candidate_selectors:
            try:
                elems = driver.find_elements(by, sel)
            except Exception as e:
                last_error = e
                continue

            for el in elems:
                try:
                    if not el.is_displayed():
                        continue
                except Exception:
                    continue

                try:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                except Exception:
                    pass

                try:
                    driver.execute_script("arguments[0].focus();", el)
                except Exception:
                    pass

                try:
                    if el.is_enabled():
                        return el
                except Exception:
                    return el

        time.sleep(1.0)

    if last_error:
        print(f"[DEBUG] Last composer detection error: {last_error}")
    return None


def send_keepalive_to_composer(driver, composer, Keys):
    try:
        js_typing_script = """
        let el = arguments[0];
        let textToType = arguments[1];

        if (!el || !document.contains(el)) {
            el = document.querySelector('textarea#prompt-textarea') ||
                 document.querySelector("textarea[data-testid='composer-text-input']") ||
                 document.querySelector("div#prompt-textarea[contenteditable='true']") ||
                 document.querySelector("div[contenteditable='true'][role='textbox']") ||
                 document.querySelector("div[contenteditable='true']") ||
                 document.querySelector('textarea');
        }

        if (!el) return false;

        el.focus();

        try {
            if ('value' in el) {
                el.value = textToType;
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                return true;
            }
        } catch (e) {}

        try {
            el.textContent = textToType;
            el.dispatchEvent(new InputEvent('input', {
                bubbles: true,
                data: textToType,
                inputType: 'insertText'
            }));
            return true;
        } catch (e) {}

        return false;
        """

        success = driver.execute_script(js_typing_script, composer, KEEPALIVE_PROMPT)

        if not success:
            print("[WARN] JS could not find an active ChatGPT composer to type into.")
            return False

        time.sleep(0.8)

        try:
            send_btns = driver.find_elements("css selector", "button[data-testid='send-button']")
            for btn in reversed(send_btns[-3:]):
                try:
                    if btn.is_displayed() and btn.is_enabled():
                        btn.click()
                        return True
                except Exception:
                    pass
        except Exception:
            pass

        try:
            active_el = driver.switch_to.active_element
            active_el.send_keys(Keys.ENTER)
            return True
        except Exception:
            pass

        try:
            composer.send_keys(Keys.ENTER)
            return True
        except Exception:
            pass

        print("[WARN] Text inserted, but Enter submission failed.")
        return False

    except Exception as e:
        print(f"[DEBUG] Error during ChatGPT keepalive send: {e}")
        return False


def attach_driver(webdriver, Service, options):
    try:
        service = Service()
        driver = webdriver(service=service, options=options)
        print("[INFO] Selenium attached successfully.")
        return driver
    except Exception as e:
        raise RuntimeError(
            f"Selenium failed to attach: {type(e).__name__}: {e}\n"
            f"Likely causes:\n"
            f"  - Chrome / ChromeDriver / Selenium mismatch\n"
            f"  - Stale debug session on port {DEBUG_PORT}\n"
            f"  - Security software interference\n"
            f"  - Broken local Selenium install"
        ) from e


def main():
    launch_chrome_debug()

    webdriver_mod, by_mod, keys_mod, options_mod, service_mod = import_real_selenium()
    webdriver = webdriver_mod.Chrome
    By = by_mod.By
    Keys = keys_mod.Keys
    Options = options_mod.Options
    Service = service_mod.Service

    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{DEBUG_PORT}")

    print("[INFO] Attaching Selenium to Chrome debugging session...")
    driver = None

    try:
        targets = list_debug_targets(DEBUG_PORT)
        if targets:
            print(f"[INFO] DevTools target count: {len(targets)}")
        else:
            print("[WARN] No DevTools targets listed yet; continuing anyway.")

        driver = attach_driver(webdriver=webdriver, Service=Service, options=opts)

        try:
            driver.set_page_load_timeout(10)
        except Exception:
            pass

        driver.get(CHATGPT_URL)

        print("[INFO] Waiting for ChatGPT composer (login detection)...")
        composer = find_interactable_composer(
            driver=driver,
            By=By,
            login_wait_seconds=LOGIN_WAIT_SECONDS,
        )

        if composer is None:
            print("[WARN] ChatGPT composer not detected or not interactable.")
            print("[WARN] If ChatGPT is on login screen, please log in manually in this automation Chrome, then re-run.")
            return

        ok = send_keepalive_to_composer(driver, composer, Keys)
        if not ok:
            print("[WARN] Composer detected, but keepalive typing/submission failed.")
            print("[WARN] ChatGPT may still be loading, or an overlay may be blocking input.")
            return

        print("[OK] Keepalive prompt submitted. Leave Chrome open.")
        print("Now run gen_problem_sets_selenium_v11.py with --provider chatgpt to attach to this same Chrome session.")

    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    main()
