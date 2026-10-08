from __future__ import annotations

import subprocess
import pathlib
import time
import importlib.util
import re
from typing import Optional, Tuple


# ---------------- Logging ----------------

def log(msg: str, level: str = "INFO"):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)


def timed_call(label: str, fn, *args, **kwargs):
    t0 = time.perf_counter()
    try:
        return fn(*args, **kwargs)
    finally:
        dt = time.perf_counter() - t0
        log(f"[timing] {label}: {dt:.3f}s", "INFO")


def _ts_now() -> float:
    return time.perf_counter()


def _fmt_dt(dt: float) -> str:
    return f"{dt:.3f}s"


def log_timing(stage: str, started_at: float, detail: str = "", level: str = "INFO") -> None:
    msg = f"[TIMING] {stage}: {_fmt_dt(_ts_now() - started_at)}"
    if detail:
        msg += f" | {detail}"
    log(msg, level)


# ---------------- File I/O helpers ----------------

def write_utf8_text(path: pathlib.Path, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def read_utf8_text(path: pathlib.Path) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


# ---------------- Tunables ----------------

PDFLATEX_TIMEOUT = 240

UPLOAD_SETTLE_TIMEOUT = 4.0
UPLOAD_SETTLE_QUIET = 0.20
UPLOAD_SETTLE_POLL = 0.08

CLEAR_COMPOSER_SLEEP = 0.02
STOP_CLICK_SLEEP = 0.08
SEND_CLICK_SLEEP = 0.05

INJECT_VERIFY_TIMEOUT = 0.30
INJECT_VERIFY_POLL = 0.02

LEAVE_COMPOSER_TIMEOUT = 1.8
LEAVE_COMPOSER_POLL = 0.05

RETRY_SLEEP_SHORT = 0.12
RETRY_SLEEP_MED = 0.10

GENERATION_POLL = 0.35
DOM_FALLBACK_MAX_WAIT = 45
DOM_FALLBACK_POLL = 0.5
FINAL_CLIPBOARD_RETRY_WAIT = 20

EARLY_LATEX_WAIT = 45
EARLY_LATEX_POLL = 0.35

GEMINI_REPAIR_ROUNDS = 2
COMPILE_ERROR_EXCERPT_LINES = 60
MAX_SOURCE_CHARS_FOR_PROMPT = 14000


# ---------------- Compile helpers ----------------

def pdflatex_run(tex_path: pathlib.Path) -> Tuple[bool, str]:
    try:
        cmd = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name]
        proc = subprocess.run(
            cmd,
            cwd=str(tex_path.parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=PDFLATEX_TIMEOUT,
        )
        out = proc.stdout or ""
        write_utf8_text(tex_path.with_suffix(".compile.log"), out)
        return proc.returncode == 0, out
    except Exception as e:
        msg = f"pdflatex test failed: {e}"
        log(msg, "ERR")
        return False, msg


def pdflatex_compiles(tex_path: pathlib.Path) -> bool:
    ok, _ = pdflatex_run(tex_path)
    return ok


def extract_compile_error_excerpt(log_text: str, max_lines: int = COMPILE_ERROR_EXCERPT_LINES) -> str:
    if not log_text:
        return ""

    lines = log_text.splitlines()

    bang_idx = None
    for i, line in enumerate(lines):
        if line.lstrip().startswith("!"):
            bang_idx = i
            break

    if bang_idx is not None:
        start = max(0, bang_idx - 8)
        end = min(len(lines), bang_idx + max_lines)
        excerpt = "\n".join(lines[start:end]).strip()
        return excerpt[:6000]

    tail = "\n".join(lines[-max_lines:]).strip()
    return tail[:6000]


# ---------------- Gemini Selenium loader ----------------

def _load_local_gemini_selenium_module():
    import sys

    here = pathlib.Path(__file__).resolve().parent
    mod_path = here / "selenium.py"

    if not mod_path.exists():
        raise FileNotFoundError(f"selenium.py not found: {mod_path}")

    spec = importlib.util.spec_from_file_location("gemini_selenium_local", str(mod_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not create import spec for: {mod_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


# ---------------- File rename helpers ----------------

def _unique_rename(src: pathlib.Path, new_name: str) -> pathlib.Path:
    dst = src.with_name(new_name)
    if dst.exists():
        stamp = time.strftime("%Y%m%d_%H%M%S")
        dst = dst.with_name(f"{dst.stem}_{stamp}{dst.suffix}")
    src.rename(dst)
    return dst


# ---------------- Local LaTeX sanitation / deterministic fixes ----------------

SMART_MAP = str.maketrans({
    "\u201c": '"', "\u201d": '"',
    "\u2018": "'", "\u2019": "'",
    "\u2013": "-", "\u2014": "-", "\u2212": "-",
    "\u00a0": " ",
})

CODEFENCE_RE = re.compile(r"```(?:latex|tex)?\s*([\s\S]*?)```", re.IGNORECASE)
FULL_DOC_RE = re.compile(r"(\\documentclass.*?\\end\{document\})", re.DOTALL)


def _looks_like_full_latex_document(text: str) -> bool:
    if not text:
        return False
    s = text.strip()
    return ("\\documentclass" in s) and ("\\begin{document}" in s) and ("\\end{document}" in s)


def _extract_full_latex_document(text: str) -> Optional[str]:
    if not text:
        return None

    s = text.strip()
    fenced = CODEFENCE_RE.search(s)
    if fenced:
        s = fenced.group(1).strip()

    m = FULL_DOC_RE.search(s)
    if m:
        return m.group(1).strip()

    if _looks_like_full_latex_document(s):
        return s

    return None


def _normalize_tex_text(text: str) -> str:
    s = text or ""
    s = s.translate(SMART_MAP)

    fenced = CODEFENCE_RE.search(s)
    if fenced:
        s = fenced.group(1).strip()

    doc = _extract_full_latex_document(s)
    if doc:
        s = doc

    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"[^\x09\x0A\x0D\x20-\x7E\u00A0-\uFFFF]", "", s)
    return s.strip() + "\n"


def _fix_itemize_with_enumerate_labels(text: str) -> str:
    block_pat = re.compile(r"\\begin\{itemize\}(\[[^\]]*\])(?P<body>.*?)\\end\{itemize\}", re.DOTALL)

    def block_repl(m):
        opts = m.group(1) or ""
        body = m.group("body")
        if re.search(r"\\(?:alph|Alph|arabic|roman|Roman)\*", opts):
            return f"\\begin{{enumerate}}{opts}{body}\\end{{enumerate}}"
        return m.group(0)

    return block_pat.sub(block_repl, text)


def _fix_dangling_quotes_and_fences(text: str) -> str:
    s = text
    s = re.sub(r"^\s*```.*?$", "", s, flags=re.MULTILINE)
    s = re.sub(r"^\s*~~~.*?$", "", s, flags=re.MULTILINE)
    return s


def _ensure_document_end(text: str) -> str:
    s = text
    if "\\begin{document}" in s and "\\end{document}" not in s:
        s = s.rstrip() + "\n\n\\end{document}\n"
    s = re.sub(r"(\\end\{document\})(?:\s*\\end\{document\})+", r"\1", s, flags=re.DOTALL)
    return s


def _fix_common_latex_issues(text: str) -> str:
    s = _normalize_tex_text(text)
    s = _fix_dangling_quotes_and_fences(s)
    s = _fix_itemize_with_enumerate_labels(s)

    s = re.sub(r"(?<!\\)\\'([A-Za-z])", r"'\1", s)

    s = _ensure_document_end(s)
    return s


def try_local_repair(tex_path: pathlib.Path) -> Tuple[bool, Optional[pathlib.Path], str]:
    original = read_utf8_text(tex_path)
    fixed = _fix_common_latex_issues(original)

    if fixed == original:
        ok, log_text = pdflatex_run(tex_path)
        return ok, None, log_text

    local_fixed = tex_path.with_name(tex_path.stem + "_localfixed.tex")
    write_utf8_text(local_fixed, fixed)

    ok, log_text = pdflatex_run(local_fixed)
    return ok, local_fixed, log_text


# ---------------- Thick Gemini UI guards ----------------

def _fast_find_prompt_editable(client):
    if client.driver is None:
        return None

    cache = getattr(client, "_fix_prompt_cache", None)
    if cache is not None:
        try:
            if cache.is_displayed():
                return cache
        except Exception:
            pass

    selectors = [
        ('css selector', 'div[aria-label="Enter a prompt here"] [contenteditable="true"]'),
        ('css selector', '[contenteditable="true"][role="textbox"]'),
        ('css selector', 'div[role="textbox"][contenteditable="true"]'),
        ('css selector', 'textarea'),
        ('css selector', 'div[aria-label="Enter a prompt here"]'),
    ]

    for by, sel in selectors:
        try:
            els = client.driver.find_elements(by, sel)
        except Exception:
            els = []
        for el in reversed(els):
            try:
                if el.is_displayed():
                    setattr(client, "_fix_prompt_cache", el)
                    return el
            except Exception:
                pass

    try:
        el = client.driver.execute_script(
            """
            const sels = [
              'div[aria-label="Enter a prompt here"] [contenteditable="true"]',
              '[contenteditable="true"][role="textbox"]',
              'div[role="textbox"][contenteditable="true"]',
              'textarea',
              'div[aria-label="Enter a prompt here"]'
            ];
            const isVisible = (el) => {
              if (!el) return false;
              const cs = getComputedStyle(el);
              const r = el.getBoundingClientRect();
              return cs.display !== 'none' && cs.visibility !== 'hidden' && r.width > 0 && r.height > 0;
            };
            for (const sel of sels) {
              const nodes = Array.from(document.querySelectorAll(sel));
              for (const el of nodes) {
                if (isVisible(el)) return el;
              }
            }
            return null;
            """
        )
        if el is not None:
            setattr(client, "_fix_prompt_cache", el)
            return el
    except Exception:
        pass

    return None


def clear_composer(client) -> None:
    if client.driver is None:
        return

    try:
        ed = _fast_find_prompt_editable(client)
    except Exception:
        return

    try:
        client.driver.execute_script(
            """
            const el = arguments[0];
            if (!el) return;
            el.focus();

            const clearOne = (node) => {
                if (!node) return;
                try { if ('value' in node) node.value = ''; } catch (e) {}
                try { node.innerHTML = ''; } catch (e) {}
                try { node.textContent = ''; } catch (e) {}
                try { node.innerText = ''; } catch (e) {}
                try { node.dispatchEvent(new Event('input', {bubbles: true})); } catch (e) {}
                try { node.dispatchEvent(new Event('change', {bubbles: true})); } catch (e) {}
            };

            clearOne(el);
            try {
                el.querySelectorAll('[contenteditable="true"], div[role="textbox"], textarea, p, span')
                  .forEach(clearOne);
            } catch (e) {}
            """,
            ed,
        )
    except Exception:
        pass

    time.sleep(CLEAR_COMPOSER_SLEEP)


def _page_text_lower(driver) -> str:
    try:
        txt = driver.execute_script("return (document.body && document.body.innerText) || '';")
    except Exception:
        txt = ""
    return re.sub(r"\s+", " ", (txt or "")).strip().lower()


def _count_visible_matches(driver, selectors) -> int:
    total = 0
    for sel in selectors:
        try:
            els = driver.find_elements("css selector", sel)
            total += sum(1 for e in els if e.is_displayed())
        except Exception:
            pass
    return total


def _attachment_probe(driver) -> tuple[int, list[str]]:
    strict_selectors = [
        "[aria-label*='Remove file']",
        "[aria-label*='Remove attachment']",
        "[aria-label^='Remove '][role='button']",
        "button[aria-label*='Remove file']",
        "button[aria-label*='Remove attachment']",
    ]

    count = 0
    names = []

    try:
        info = driver.execute_script(
            """
            const sels = arguments[0];
            const isVisible = (el) => {
                if (!el) return false;
                const cs = getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return cs.display !== 'none' &&
                       cs.visibility !== 'hidden' &&
                       rect.width > 0 &&
                       rect.height > 0;
            };

            const out = [];
            const seen = new Set();

            for (const sel of sels) {
                for (const el of document.querySelectorAll(sel)) {
                    if (!isVisible(el)) continue;
                    const key = (el.outerHTML || '').slice(0, 180) + '|' + (el.getAttribute('aria-label') || '');
                    if (seen.has(key)) continue;
                    seen.add(key);

                    const aria = (el.getAttribute('aria-label') || '').trim();
                    let name = aria.replace(/^Remove\\s+/i, '').trim();
                    if (/\\.(png|jpg|jpeg|pdf|docx?|tex|txt)$/i.test(name)) {
                        out.push(name);
                    } else {
                        out.push('');
                    }
                }
            }
            return out;
            """,
            strict_selectors,
        ) or []
        count = len(info)
        names = [x.strip().lower() for x in info if isinstance(x, str) and x.strip()]
    except Exception:
        count = _count_visible_matches(driver, strict_selectors)
        names = []

    return count, names


def get_visible_attachment_count(driver) -> int:
    count, _ = _attachment_probe(driver)
    return count


def get_latest_response_text(driver) -> str:
    selectors = [
        "message-content",
        "div[role='article']",
        "div[class*='response']",
        "div[class*='model']",
    ]
    for sel in selectors:
        try:
            els = driver.find_elements("css selector", sel)
        except Exception:
            els = []
        if not els:
            continue
        for el in reversed(els[-4:]):
            try:
                txt = (el.get_attribute("innerText") or el.text or "").strip()
            except Exception:
                txt = ""
            if len(txt) >= 10:
                return txt
    return ""


def wait_for_upload_to_settle(
    client,
    expected_names=None,
    timeout: float = UPLOAD_SETTLE_TIMEOUT,
    quiet_window: float = UPLOAD_SETTLE_QUIET,
    poll: float = UPLOAD_SETTLE_POLL,
    baseline_attachment_count: int = 0,
    min_new_attachments: int = 0,
) -> bool:
    t_wait = _ts_now()
    if client.driver is None:
        log_timing("upload settle skipped", t_wait, "driver unavailable", level="WARN")
        return False

    expected_names = [str(x).strip().lower() for x in (expected_names or []) if str(x).strip()]

    busy_selectors = [
        "[role='progressbar']",
        "mat-progress-bar",
        ".upload-progress",
        "[aria-label*='Uploading']",
        "[aria-label*='uploading']",
        "[aria-label*='Processing']",
        "[aria-label*='processing']",
        "[class*='progress']",
        "[class*='uploading']",
    ]

    good_since = None
    last_signature = None
    last_detail = ""

    while _ts_now() - t_wait < timeout:
        page_txt = _page_text_lower(client.driver)

        busy_count = _count_visible_matches(client.driver, busy_selectors)
        busy_text = any(tok in page_txt for tok in ["uploading", "processing", "preparing"])

        composer_ready = False
        try:
            ed = _fast_find_prompt_editable(client)
            composer_ready = ed is not None
        except Exception:
            composer_ready = False

        attachment_count, attachment_names = _attachment_probe(client.driver)
        new_attachments = max(0, attachment_count - baseline_attachment_count)

        names_seen = 0
        if expected_names:
            page_name_hits = sum(1 for name in expected_names if name in page_txt)
            chip_name_hits = sum(1 for name in expected_names if name in attachment_names)
            names_seen = max(page_name_hits, chip_name_hits)

        names_ready = bool(expected_names) and (names_seen >= len(expected_names))
        attachment_ready = (min_new_attachments > 0) and (new_attachments >= min_new_attachments)
        send_ready = get_safe_send_button(client) is not None

        files_ready = names_ready or attachment_ready or (attachment_count > baseline_attachment_count)

        signature = (busy_count, busy_text, attachment_count, names_seen, send_ready, composer_ready)
        stable_now = (busy_count == 0) and (not busy_text) and composer_ready and files_ready and send_ready

        last_detail = (
            f"names_seen={names_seen}/{len(expected_names) if expected_names else 0}, "
            f"attachment_count={attachment_count}, baseline_attachment_count={baseline_attachment_count}, "
            f"new_attachments={new_attachments}, composer_ready={composer_ready}, send_ready={send_ready}, "
            f"busy_count={busy_count}, busy_text={busy_text}"
        )

        if stable_now and signature == last_signature:
            if good_since is None:
                good_since = _ts_now()
            elif _ts_now() - good_since >= quiet_window:
                log_timing("upload settle confirmed", t_wait, last_detail)
                return True
        else:
            good_since = None

        last_signature = signature
        time.sleep(poll)

    log_timing("upload settle timeout", t_wait, last_detail, level="WARN")
    return False


def stop_generation_if_present(client) -> bool:
    if client.driver is None:
        return False

    selectors = [
        "//button[contains(@aria-label,'Stop')]",
        "//button[contains(@title,'Stop')]",
        "//button[.//span[contains(normalize-space(.),'Stop')]]",
    ]

    for sel in selectors:
        try:
            btns = client.driver.find_elements("xpath", sel)
        except Exception:
            btns = []

        for btn in reversed(btns[-4:]):
            try:
                if btn.is_displayed() and btn.is_enabled():
                    try:
                        client.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                    except Exception:
                        pass
                    try:
                        btn.click()
                    except Exception:
                        client.driver.execute_script("arguments[0].click();", btn)
                    time.sleep(STOP_CLICK_SLEEP)
                    return True
            except Exception:
                pass

    return False


def get_composer_text(client) -> str:
    if client.driver is None:
        return ""

    try:
        ed = _fast_find_prompt_editable(client)
    except Exception:
        return ""

    try:
        txt = client.driver.execute_script(
            """
            const root = arguments[0];
            if (!root) return "";

            const vals = [];
            const harvest = (node) => {
                if (!node) return;
                try {
                    if ('value' in node && node.value && String(node.value).trim()) {
                        vals.push(String(node.value).trim());
                    }
                } catch (e) {}
                try {
                    if (node.innerText && String(node.innerText).trim()) {
                        vals.push(String(node.innerText).trim());
                    }
                } catch (e) {}
                try {
                    if (node.textContent && String(node.textContent).trim()) {
                        vals.push(String(node.textContent).trim());
                    }
                } catch (e) {}
            };

            harvest(root);
            try {
                root.querySelectorAll('[contenteditable="true"], div[role="textbox"], textarea, p, span')
                    .forEach(harvest);
            } catch (e) {}

            vals.sort((a, b) => b.length - a.length);
            return vals.length ? vals[0] : "";
            """,
            ed,
        )
        return (txt or "").strip()
    except Exception:
        return ""


def prompt_verified_in_composer(client, prompt_text: str) -> bool:
    current = " ".join(get_composer_text(client).split())
    if not current:
        return False

    prompt_norm = " ".join(prompt_text.split())
    probe = prompt_norm[:60].strip()
    if probe and probe in current:
        return True

    lead = prompt_norm[:220]
    tokens = [
        tok for tok in re.findall(r"[A-Za-z0-9_.:/\\\\-]{4,}", lead)
        if tok.lower() not in {"your", "with", "that", "this", "have", "from", "only", "must"}
    ]
    hits = sum(1 for tok in tokens[:12] if tok in current)

    return len(current) >= 40 and hits >= 3


def inject_prompt_text(client, text: str, verify_timeout: float = INJECT_VERIFY_TIMEOUT, poll: float = INJECT_VERIFY_POLL) -> bool:
    t_inject = _ts_now()
    if client.driver is None:
        log_timing("prompt inject skipped", t_inject, "driver unavailable", level="WARN")
        return False

    try:
        ed = _fast_find_prompt_editable(client)
    except Exception:
        return False

    try:
        ok = client.driver.execute_script(
            """
            const root = arguments[0];
            const txt  = arguments[1];
            if (!root) return false;

            const targets = [root];
            try {
                root.querySelectorAll('[contenteditable="true"], div[role="textbox"], textarea')
                    .forEach(x => targets.push(x));
            } catch (e) {}

            const uniq = [];
            const seen = new Set();
            for (const t of targets) {
                if (t && !seen.has(t)) {
                    seen.add(t);
                    uniq.push(t);
                }
            }

            const fill = (el) => {
                try { el.focus(); } catch (e) {}

                try {
                    if ('value' in el) {
                        el.value = txt;
                        el.dispatchEvent(new Event('input', {bubbles: true}));
                        el.dispatchEvent(new Event('change', {bubbles: true}));
                        return true;
                    }
                } catch (e) {}

                try { el.innerHTML = ''; } catch (e) {}
                try { el.textContent = txt; } catch (e) {}
                try {
                    el.dispatchEvent(new InputEvent('input', {
                        bubbles: true,
                        inputType: 'insertText',
                        data: txt
                    }));
                } catch (e) {
                    try { el.dispatchEvent(new Event('input', {bubbles: true})); } catch (ee) {}
                }
                try { el.dispatchEvent(new Event('change', {bubbles: true})); } catch (e) {}
                return true;
            };

            for (const el of uniq) {
                if (fill(el)) return true;
            }
            return false;
            """,
            ed,
            text,
        )

        if not ok:
            log_timing("prompt inject js", t_inject, "js fill returned false", level="WARN")
            return False

        log_timing("prompt inject js", t_inject, "js fill completed")
        t0 = _ts_now()
        while _ts_now() - t0 < verify_timeout:
            if prompt_verified_in_composer(client, text):
                log_timing("prompt verify after inject", t0, "prompt confirmed in composer")
                return True
            time.sleep(poll)

        verified = prompt_verified_in_composer(client, text)
        log_timing("prompt verify after inject", t0, f"verified={verified}", level=("INFO" if verified else "WARN"))
        return verified

    except Exception as e:
        log_timing("prompt inject exception", t_inject, repr(e), level="WARN")
        return False


def get_safe_send_button(client):
    if client.driver is None:
        return None

    stop_selectors = [
        "//button[contains(@aria-label,'Stop')]",
        "//button[contains(@title,'Stop')]",
        "//button[.//span[contains(normalize-space(.),'Stop')]]",
    ]
    for sel in stop_selectors:
        try:
            btns = client.driver.find_elements("xpath", sel)
        except Exception:
            btns = []
        for b in btns[-3:]:
            try:
                if b.is_displayed() and b.is_enabled():
                    return None
            except Exception:
                pass

    send_selectors = [
        '//button[@aria-label="Send message"]',
        '//button[contains(@aria-label,"Send")]',
        '//button[contains(@aria-label,"Ask")]',
        '//button[.//span[contains(normalize-space(.),"Send")]]',
        '//button[.//span[contains(normalize-space(.),"Ask")]]',
    ]
    for sel in send_selectors:
        try:
            btns = client.driver.find_elements("xpath", sel)
        except Exception:
            btns = []
        for b in reversed(btns[-4:]):
            try:
                if b.is_displayed() and b.is_enabled():
                    return b
            except Exception:
                pass

    return None


def wait_until_send_actionable(
    client,
    prompt_text: str = "",
    timeout: float = 8.0,
    poll: float = 0.04,
    stable_rounds: int = 1,
) -> bool:
    if client.driver is None:
        return False

    prompt_probe = " ".join((prompt_text or "").split())[:80].strip()
    t0 = _ts_now()
    stable = 0
    last_status = {}

    while _ts_now() - t0 < timeout:
        try:
            status = client.driver.execute_script(
                """
                const probe = arguments[0] || "";
                const norm = (s) => String(s || "").replace(/\\s+/g, " ").trim();

                const isVisible = (el) => {
                    if (!el) return false;
                    const cs = getComputedStyle(el);
                    const r = el.getBoundingClientRect();
                    return cs.display !== "none" &&
                           cs.visibility !== "hidden" &&
                           r.width > 0 && r.height > 0;
                };

                const bodyText = norm((document.body && document.body.innerText) || "").toLowerCase();

                let busyCount = 0;
                const busySelectors = [
                    "[role='progressbar']",
                    "mat-progress-bar",
                    ".upload-progress",
                    "[aria-label*='Uploading']",
                    "[aria-label*='uploading']",
                    "[aria-label*='Processing']",
                    "[aria-label*='processing']",
                    "[class*='progress']",
                    "[class*='uploading']",
                ];
                for (const sel of busySelectors) {
                    try {
                        for (const el of document.querySelectorAll(sel)) {
                            if (isVisible(el)) busyCount += 1;
                        }
                    } catch (e) {}
                }

                let composerText = "";
                const composerSelectors = [
                    'div[aria-label="Enter a prompt here"] [contenteditable="true"]',
                    'div[aria-label="Enter a prompt here"]',
                    '[contenteditable="true"][role="textbox"]',
                    'div[role="textbox"][contenteditable="true"]',
                    'textarea',
                ];
                for (const sel of composerSelectors) {
                    try {
                        const nodes = Array.from(document.querySelectorAll(sel));
                        for (const el of nodes) {
                            if (!isVisible(el)) continue;
                            const vals = [el.value, el.innerText, el.textContent].map(norm).filter(Boolean);
                            if (vals.length) {
                                vals.sort((a,b) => b.length - a.length);
                                composerText = vals[0];
                                break;
                            }
                        }
                    } catch (e) {}
                    if (composerText) break;
                }

                let sendEnabled = false;
                const sendX = [
                    "//button[@aria-label='Send message']",
                    "//button[contains(@aria-label,'Send')]",
                    "//button[contains(@aria-label,'Ask')]",
                    "//button[.//span[contains(normalize-space(.),'Send')]]",
                    "//button[.//span[contains(normalize-space(.),'Ask')]]",
                ];
                const stopX = [
                    "//button[contains(@aria-label,'Stop')]",
                    "//button[contains(@title,'Stop')]",
                    "//button[.//span[contains(normalize-space(.),'Stop')]]",
                ];

                const hasVisibleEnabled = (xps) => {
                    for (const xp of xps) {
                        try {
                            const it = document.evaluate(xp, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                            for (let i = 0; i < it.snapshotLength; i++) {
                                const el = it.snapshotItem(i);
                                if (isVisible(el) && !el.disabled && el.getAttribute("aria-disabled") !== "true") {
                                    return true;
                                }
                            }
                        } catch (e) {}
                    }
                    return false;
                };

                const stopVisible = hasVisibleEnabled(stopX);
                if (!stopVisible) {
                    sendEnabled = hasVisibleEnabled(sendX);
                }

                const probeOk = !probe || composerText.includes(probe);
                const busyText = ["uploading", "processing", "preparing"].some(tok => bodyText.includes(tok));

                return {
                    prompt_ok: probeOk,
                    send_ready: sendEnabled,
                    busy_count: busyCount,
                    busy_text: busyText,
                    composer_text: composerText.slice(0, 120),
                };
                """,
                prompt_probe,
            ) or {}
        except Exception:
            status = {}

        last_status = status or {}
        prompt_ok = bool(status.get("prompt_ok"))
        send_ready = bool(status.get("send_ready"))
        busy_count = int(status.get("busy_count", 0) or 0)
        busy_text = bool(status.get("busy_text"))

        if prompt_ok and send_ready and busy_count == 0 and not busy_text:
            stable += 1
            if stable >= stable_rounds:
                log_timing("send actionable wait", t0, f"stable_rounds={stable_rounds}, composer={status.get('composer_text','')[:80]}")
                return True
        else:
            stable = 0

        time.sleep(poll)

    detail = (
        f"prompt_ok={bool(last_status.get('prompt_ok'))}, send_ready={bool(last_status.get('send_ready'))}, "
        f"busy_count={int(last_status.get('busy_count', 0) or 0)}, busy_text={bool(last_status.get('busy_text'))}, "
        f"composer={str(last_status.get('composer_text', ''))[:80]}"
    )
    log_timing("send actionable wait timeout", t0, detail, level="WARN")
    return False


def click_safe_send_button(client) -> bool:
    t_click = _ts_now()
    btn = get_safe_send_button(client)
    if btn is None:
        log_timing("send click skipped", t_click, "no safe send button", level="WARN")
        return False

    try:
        client.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
    except Exception:
        pass

    try:
        btn.click()
        time.sleep(SEND_CLICK_SLEEP)
        log_timing("send click", t_click, "native click")
        return True
    except Exception:
        try:
            client.driver.execute_script("arguments[0].click();", btn)
            time.sleep(SEND_CLICK_SLEEP)
            log_timing("send click", t_click, "js click fallback")
            return True
        except Exception as e:
            log_timing("send click failed", t_click, repr(e), level="WARN")
            return False


def _send_registered(client, before_text: str = "") -> bool:
    if client.driver is None:
        return False

    try:
        stop_selectors = [
            "//button[contains(@aria-label,'Stop')]",
            "//button[contains(@title,'Stop')]",
            "//button[.//span[contains(normalize-space(.),'Stop')]]",
        ]
        for sel in stop_selectors:
            btns = client.driver.find_elements("xpath", sel)
            for b in btns[-3:]:
                try:
                    if b.is_displayed() and b.is_enabled():
                        return True
                except Exception:
                    pass
    except Exception:
        pass

    cur = " ".join(get_composer_text(client).split())
    before = " ".join((before_text or "").split())

    if not cur:
        return True

    if before and cur != before and len(cur) < max(20, len(before) // 3):
        return True

    try:
        btn = get_safe_send_button(client)
        if btn is None:
            return True
    except Exception:
        pass

    return False


def wait_for_prompt_to_leave_composer(client, before_text: str = "", timeout: float = LEAVE_COMPOSER_TIMEOUT, poll: float = LEAVE_COMPOSER_POLL) -> bool:
    t0 = _ts_now()
    while _ts_now() - t0 < timeout:
        if _send_registered(client, before_text=before_text):
            log_timing("prompt left composer", t0, "submission registered")
            return True
        time.sleep(poll)

    log_timing("prompt left composer timeout", t0, "submission not confirmed", level="WARN")
    return False


# ---------------- Gemini response helpers ----------------

def _latex_response_is_substantial(text: str) -> bool:
    cleaned = (text or "").strip()
    if len(cleaned) < 200:
        return False
    return ("\\documentclass" in cleaned) or ("\\begin{document}" in cleaned) or ("\\end{document}" in cleaned)


def wait_for_latex_response_ready(client, baseline_text: str = "", timeout: float = EARLY_LATEX_WAIT, poll: float = EARLY_LATEX_POLL) -> str:
    if client.driver is None:
        return ""

    baseline_norm = (baseline_text or "").strip()
    last = ""
    stable = 0
    t0 = time.time()

    while time.time() - t0 < timeout:
        cur = (get_latest_response_text(client.driver) or "").strip()
        if cur and cur != baseline_norm:
            latex = _extract_full_latex_document(cur)
            if latex:
                if cur == last:
                    stable += 1
                else:
                    last = cur
                    stable = 0

                generating = False
                try:
                    for sel in [
                        "//button[contains(@aria-label,'Stop')]",
                        "//button[contains(@title,'Stop')]",
                        "//button[.//span[contains(normalize-space(.),'Stop')]]",
                    ]:
                        btns = client.driver.find_elements("xpath", sel)
                        for b in btns[-3:]:
                            try:
                                if b.is_displayed() and b.is_enabled():
                                    generating = True
                                    break
                            except Exception:
                                pass
                        if generating:
                            break
                except Exception:
                    generating = False

                if stable >= 1 and not generating:
                    log(f"Early LaTeX response confirmed after {time.time() - t0:.1f}s.", "INFO")
                    return latex

        time.sleep(poll)

    return ""


def _build_repair_instruction(tex_source: str, compile_excerpt: str) -> str:
    return (
        "You are repairing an attached LaTeX source file.\n\n"
        "Your task is to return a FULL corrected LaTeX document that will compile successfully with pdflatex.\n\n"
        "Hard requirements:\n"
        "1. Return ONLY the corrected LaTeX source code.\n"
        "2. The response must begin with \\documentclass and end with \\end{document}.\n"
        "3. Do NOT include any explanation, comments, markdown code fences, bullets, notes, or surrounding text.\n"
        "4. Preserve the original content, wording, structure, figures, and equations as much as possible.\n"
        "5. Fix only what is necessary to make the document compile correctly and remain logically consistent.\n\n"
        "Before you return the answer, perform an internal compile-readiness check on the full document and revise it until it is self-consistent.\n"
        "Verify all of the following carefully:\n"
        "- all \\begin{...} and \\end{...} environments are correctly paired\n"
        "- all braces {}, brackets [], and math delimiters are balanced\n"
        "- all commands used are valid in pdflatex\n"
        "- all packages required by the document are present in the preamble\n"
        "- no incompatible environment/options are used\n"
        "- list environments are semantically correct\n"
        "  - for example, if label=(\\alph*) or label=(\\arabic*) is used, do not keep itemize if enumerate is required\n"
        "- all \\includegraphics commands are syntactically valid\n"
        "- captions, section titles, and text do not contain problematic unescaped characters such as stray &, %, #, _, or smart quotes when used outside safe contexts\n"
        "- no markdown artifacts such as ```latex, ``` , or plain-English headers remain\n"
        "- no duplicated \\documentclass, \\begin{document}, or \\end{document} remain\n"
        "- no incomplete fragments or truncated sections remain\n\n"
        "Important:\n"
        "- Think like a strict pdflatex compiler.\n"
        "- If a construct would cause a compile error, fix it before returning.\n"
        "- If there are multiple possible fixes, choose the minimal fix that preserves the source content.\n"
        "- Do not simplify away substantive content unless absolutely necessary for compilation.\n"
        "- Do not invent new questions or remove existing questions unless the source is clearly corrupted.\n"
        "- Keep figure filenames unchanged unless a filename itself is the direct cause of a LaTeX syntax failure.\n\n"
        "Compiler error excerpt:\n"
        "----- BEGIN COMPILE ERROR -----\n"
        f"{compile_excerpt.strip()}\n"
        "----- END COMPILE ERROR -----\n\n"
        "Source LaTeX:\n"
        "----- BEGIN SOURCE -----\n"
        f"{tex_source[:MAX_SOURCE_CHARS_FOR_PROMPT]}\n"
        "----- END SOURCE -----"
    )


def _send_prompt_and_capture_strict_latex(client, gemsel, instruction_text: str, wait_cap: int) -> str:
    t_total = _ts_now()
    if client.driver is None:
        raise RuntimeError("Selenium client driver is not available.")

    baseline_response = (get_latest_response_text(client.driver) or "").strip()
    send_ok = False

    for attempt in range(3):
        t_attempt = _ts_now()
        log(f"[TIMING] prompt attempt {attempt+1}: started", "INFO")

        t_step = _ts_now()
        if stop_generation_if_present(client):
            log_timing(f"attempt {attempt+1} stop prior generation", t_step, "clicked stop", level="WARN")
            time.sleep(STOP_CLICK_SLEEP)
        else:
            log_timing(f"attempt {attempt+1} stop prior generation", t_step, "no stop button")

        t_step = _ts_now()
        clear_composer(client)
        time.sleep(CLEAR_COMPOSER_SLEEP)
        log_timing(f"attempt {attempt+1} clear composer", t_step)

        t_step = _ts_now()
        injected = inject_prompt_text(client, instruction_text, verify_timeout=INJECT_VERIFY_TIMEOUT, poll=INJECT_VERIFY_POLL)
        log_timing(f"attempt {attempt+1} inject+verify prompt", t_step, f"injected={injected}", level=("INFO" if injected else "WARN"))
        if not injected:
            time.sleep(RETRY_SLEEP_MED)
            log_timing(f"attempt {attempt+1} total", t_attempt, "failed at inject step", level="WARN")
            continue

        t_step = _ts_now()
        composer_before_send = get_composer_text(client)
        prompt_ok = prompt_verified_in_composer(client, instruction_text)
        log_timing(
            f"attempt {attempt+1} prompt snapshot",
            t_step,
            f"prompt_ok={prompt_ok}; snapshot={repr(composer_before_send[:120])}",
            level=("INFO" if prompt_ok else "WARN"),
        )
        if not prompt_ok:
            time.sleep(RETRY_SLEEP_MED)
            log_timing(f"attempt {attempt+1} total", t_attempt, "failed at prompt verification", level="WARN")
            continue

        t_step = _ts_now()
        actionable = wait_until_send_actionable(
            client,
            prompt_text=instruction_text,
            timeout=min(8.0, max(2.0, float(wait_cap) * 0.08)),
            poll=0.04,
            stable_rounds=1,
        )
        log_timing(f"attempt {attempt+1} wait send actionable", t_step, f"actionable={actionable}", level=("INFO" if actionable else "WARN"))
        if not actionable:
            time.sleep(RETRY_SLEEP_MED)
            log_timing(f"attempt {attempt+1} total", t_attempt, "send never became actionable", level="WARN")
            continue

        t_step = _ts_now()
        clicked = click_safe_send_button(client)
        log_timing(f"attempt {attempt+1} click send", t_step, f"clicked={clicked}", level=("INFO" if clicked else "WARN"))
        if not clicked:
            time.sleep(RETRY_SLEEP_SHORT)
            log_timing(f"attempt {attempt+1} total", t_attempt, "send click failed", level="WARN")
            continue

        t_step = _ts_now()
        registered = wait_for_prompt_to_leave_composer(
            client,
            before_text=composer_before_send,
            timeout=LEAVE_COMPOSER_TIMEOUT,
            poll=LEAVE_COMPOSER_POLL,
        )
        log_timing(f"attempt {attempt+1} register send", t_step, f"registered={registered}", level=("INFO" if registered else "WARN"))
        if registered:
            send_ok = True
            log_timing(f"attempt {attempt+1} total", t_attempt, "submission registered")
            break

        log(f"Prompt did not register after Send on attempt {attempt+1}.", "WARN")
        time.sleep(RETRY_SLEEP_SHORT)
        log_timing(f"attempt {attempt+1} total", t_attempt, "registration failed", level="WARN")

    if not send_ok:
        log_timing("prompt send pipeline total", t_total, "all attempts failed", level="WARN")
        raise RuntimeError("Prompt could not be reliably submitted to Gemini.")

    t_step = _ts_now()
    early = wait_for_latex_response_ready(
        client,
        baseline_text=baseline_response,
        timeout=min(float(wait_cap), EARLY_LATEX_WAIT),
        poll=EARLY_LATEX_POLL,
    )
    log_timing("early latex wait", t_step, f"hit={bool(early)}")
    if early:
        return early

    log(f"Waiting for Gemini response to finish (strict LaTeX capture, max_wait={wait_cap}) ...")

    t_step = _ts_now()
    gemsel._wait_until_generation_finishes(client.driver, timeout=float(wait_cap), poll=GENERATION_POLL)
    log_timing("wait until generation finishes", t_step)

    t_step = _ts_now()
    dom_ready = (get_latest_response_text(client.driver) or "").strip()
    dom_latex = _extract_full_latex_document(dom_ready)
    log_timing("post-finish DOM check", t_step, f"latex={bool(dom_latex)}")
    if dom_latex:
        return dom_latex

    t_step = _ts_now()
    copied = gemsel.capture_gemini_response_like_manual_copy(
        client.driver,
        wait_cap=wait_cap,
        prefer_latex_doc=True,
        retries=6,
        min_chars=200,
        accept_fn=_latex_response_is_substantial,
    )
    latex = _extract_full_latex_document(copied or "")
    log_timing("manual-copy capture", t_step, f"latex={bool(latex)}")
    if latex:
        return latex

    log("Strict clipboard capture failed; trying bounded DOM extraction.", "WARN")

    t_step = _ts_now()
    dom = gemsel.adaptive_wait_and_copy_full(
        client.driver,
        preset="short",
        overrides={
            "max_wait": min(int(wait_cap), DOM_FALLBACK_MAX_WAIT),
            "min_chars": 200,
            "stable_rounds": 2,
            "poll": DOM_FALLBACK_POLL,
        },
    )
    latex = _extract_full_latex_document(dom or "")
    log_timing("bounded DOM extraction", t_step, f"latex={bool(latex)}")
    if latex:
        return latex

    t_step = _ts_now()
    copied = gemsel.capture_gemini_response_like_manual_copy(
        client.driver,
        wait_cap=FINAL_CLIPBOARD_RETRY_WAIT,
        prefer_latex_doc=True,
        retries=3,
        min_chars=200,
        accept_fn=_latex_response_is_substantial,
    )
    latex = _extract_full_latex_document(copied or "")
    log_timing("final manual-copy capture", t_step, f"latex={bool(latex)}")
    if latex:
        return latex

    raise RuntimeError("Gemini did not return a full LaTeX document; refusing to save non-LaTeX text.")


# ---------------- Gemini repair ----------------

def heavy_clean_via_gemini(tex_path: pathlib.Path, compile_excerpt: str, wait_cap: int = 120) -> Optional[str]:
    log("Starting Gemini repair pass...", "INFO")

    gemsel = _load_local_gemini_selenium_module()
    cfg = gemsel.Config(root=pathlib.Path.cwd())
    client = gemsel.GeminiSeleniumClient(cfg)

    total_t0 = time.perf_counter()

    try:
        timed_call("client.start", client.start, ensure_gemini_on_launch=True)
        timed_call("open_clean_gemini_chat", client.open_clean_gemini_chat)

        baseline_attachment_count = 0
        if client.driver is not None:
            baseline_attachment_count = get_visible_attachment_count(client.driver)

        timed_call("upload_files", client.upload_files, [tex_path])

        settled = timed_call(
            "wait_for_upload_to_settle",
            wait_for_upload_to_settle,
            client,
            [tex_path.name],
            UPLOAD_SETTLE_TIMEOUT,
            UPLOAD_SETTLE_QUIET,
            UPLOAD_SETTLE_POLL,
            baseline_attachment_count,
            1,
        )
        if not settled:
            log("Upload settle wait timed out; continuing with guarded prompt send.", "WARN")

        tex_source = read_utf8_text(tex_path)
        instruction = _build_repair_instruction(tex_source, compile_excerpt)

        response = timed_call(
            "_send_prompt_and_capture_strict_latex",
            _send_prompt_and_capture_strict_latex,
            client,
            gemsel,
            instruction,
            wait_cap,
        )

        log(f"[timing] heavy_clean_via_gemini total: {time.perf_counter() - total_t0:.3f}s", "INFO")
        return (response or "").strip() or None

    finally:
        try:
            timed_call("client.shutdown", client.shutdown)
        except Exception:
            pass


# ---------------- Public API ----------------

def fix_latex(tex_file: str) -> Optional[str]:
    tex_path = pathlib.Path(tex_file)

    if not tex_path.exists():
        raise FileNotFoundError(tex_path)

    log(f"Checking LaTeX compile status: {tex_path.name}", "INFO")

    ok, log_text = pdflatex_run(tex_path)
    if ok:
        log("LaTeX compiles successfully. No fix required.", "OK")
        return None

    log("Initial compile failed. Attempting local deterministic repair first.", "WARN")

    local_ok, local_fixed_path, local_log = try_local_repair(tex_path)
    if local_ok and local_fixed_path is not None:
        log(f"Local deterministic repair succeeded: {local_fixed_path.name}", "OK")
        _unique_rename(tex_path, tex_path.stem + "_orig.tex")
        local_fixed_path.rename(tex_path)
        pdflatex_run(tex_path)
        return None

    current_source_path = local_fixed_path if local_fixed_path and local_fixed_path.exists() else tex_path
    current_log = local_log if local_log else log_text

    for round_idx in range(1, GEMINI_REPAIR_ROUNDS + 1):
        excerpt = extract_compile_error_excerpt(current_log)
        log(f"Gemini repair round {round_idx}/{GEMINI_REPAIR_ROUNDS}", "INFO")

        try:
            repaired = heavy_clean_via_gemini(current_source_path, excerpt, wait_cap=120)
        except Exception as e:
            log(f"Gemini repair failed before a valid LaTeX document was captured: {e}", "ERR")
            break

        if not repaired:
            log("Gemini repair returned empty output.", "ERR")
            break

        repaired = _fix_common_latex_issues(repaired)

        candidate = tex_path.with_name(f"{tex_path.stem}_fixed_round{round_idx}.tex")
        write_utf8_text(candidate, repaired)

        ok, new_log = pdflatex_run(candidate)
        if ok:
            log(f"Gemini repair round {round_idx} compiles successfully.", "OK")
            _unique_rename(tex_path, tex_path.stem + "_orig.tex")
            candidate.rename(tex_path)
            pdflatex_run(tex_path)
            return None

        log(f"Gemini repair round {round_idx} still fails to compile.", "WARN")
        current_source_path = candidate
        current_log = new_log

    log("All repair passes failed. Writing best-effort sanitized fallback and preserving failed rounds.", "ERR")

    best_effort = _fix_common_latex_issues(read_utf8_text(current_source_path))
    fallback = tex_path.with_name(tex_path.stem + "_fixed_failed.tex")
    write_utf8_text(fallback, best_effort)
    return read_utf8_text(tex_path)


# ---------------- CLI ----------------

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python fix_latex_selenium_v4.py file.tex")
        raise SystemExit(1)

    fix_latex(sys.argv[1])