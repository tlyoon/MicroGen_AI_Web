# -*- coding: utf-8 -*-
# MicroGen_AI Educational Automation Package
# © 2025 Dr. Yoon Tiem Leong, School of Physics, Universiti Sains Malaysia.
#
# Improved batch driver:
# - Works with subchapter names like 22-1, 22-1plus22-2, 22.1, 22.2, ...
# - Allows selecting by chapter ('22') or exact subchapter ('22-1', '22.1')
# - Can also process all subchapters

from __future__ import annotations

import os
import re
import sys
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# ---------------------------------------------------------------------
# stdout unicode safe
# ---------------------------------------------------------------------
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

#subprocess.run(["python", "launch_gemini_chrome.py"])

# ---------------------------------------------------------------------
# USER SELECTION
# Choose ONLY ONE mode:
#
# 1) Exact items or chapter-wide selection via subchapters
#    - '22'    -> means all subchapters under chapter 22
#    - '22.1'  -> exact subchapter folder name
#    - '22.*'  -> all subchapters under chapter 22
#
# 2) chapters = ['22']   -> all subchapters under chapter 22
#
# 3) PROCESS_ALL = True  -> all detected subchapters
# ---------------------------------------------------------------------

chapters = [ ]; subchapters = [ ] ; PROCESS_ALL = True
#chapters = [ ]; subchapters = [ '33.6','33.7' ] ; PROCESS_ALL = False   
#chapters = [ '33' ]; subchapters = [ '] ; PROCESS_ALL = False

# ---------------------------------------------------------------------
# OPTIONAL OVERRIDES
# If None, auto-detection is used.
# ---------------------------------------------------------------------
WORKSPACE_ROOT_OVERRIDE: Optional[str] = None
TEMPLATE_DIR_OVERRIDE: Optional[str] = None


# ---------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------

@dataclass
class SubchapterInfo:
    chapter: str
    name: str
    path: Path

    @property
    def display(self) -> str:
        return f"{self.chapter}/{self.name}"


def log(msg: str, level: str = "INFO") -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")


def get_script_dir() -> Path:
    return Path(__file__).resolve().parent


def is_numeric_chapter_dir(p: Path) -> bool:
    return p.is_dir() and re.fullmatch(r"[1-9]\d*", p.name) is not None


def has_numeric_chapter_dirs(root: Path) -> bool:
    try:
        return any(is_numeric_chapter_dir(p) for p in root.iterdir())
    except Exception:
        return False


def detect_workspace_root() -> Path:
    """
    Try to locate the workspace root that contains numeric chapter folders
    such as 1, 2, 22, 23, ...
    Search order:
      1. explicit override
      2. script directory
      3. script directory / 'chapters'
      4. each parent of script dir
      5. each parent / 'chapters'
      6. current working directory
      7. cwd / 'chapters'
      8. each parent of cwd
      9. each parent / 'chapters'
    """
    if WORKSPACE_ROOT_OVERRIDE:
        root = Path(WORKSPACE_ROOT_OVERRIDE).expanduser().resolve()
        if not root.exists():
            raise FileNotFoundError(f"WORKSPACE_ROOT_OVERRIDE does not exist: {root}")
        if not has_numeric_chapter_dirs(root):
            raise FileNotFoundError(
                f"WORKSPACE_ROOT_OVERRIDE does not contain numeric chapter folders: {root}"
            )
        return root

    candidates: List[Path] = []
    script_dir = get_script_dir()
    cwd = Path.cwd().resolve()

    # script dir and related
    candidates.append(script_dir)
    candidates.append(script_dir / "chapters")
    for p in [script_dir, *script_dir.parents]:
        candidates.append(p)
        candidates.append(p / "chapters")

    # cwd and related
    candidates.append(cwd)
    candidates.append(cwd / "chapters")
    for p in [cwd, *cwd.parents]:
        candidates.append(p)
        candidates.append(p / "chapters")

    seen = set()
    uniq_candidates = []
    for c in candidates:
        try:
            rc = c.resolve()
        except Exception:
            continue
        if rc not in seen:
            seen.add(rc)
            uniq_candidates.append(rc)

    for c in uniq_candidates:
        if c.exists() and has_numeric_chapter_dirs(c):
            return c

    raise FileNotFoundError(
        "Could not auto-detect workspace root containing numeric chapter folders "
        "(e.g. 22, 23, ...). Set WORKSPACE_ROOT_OVERRIDE manually."
    )


def detect_template_dir(workspace_root: Path) -> Path:
    """
    Automatically detect the latest template_v* directory located in the
    same directory as this script. If none is found there, fall back to
    searching workspace_root and its parents.
    """

    # If user explicitly overrides
    if TEMPLATE_DIR_OVERRIDE:
        tdir = Path(TEMPLATE_DIR_OVERRIDE).expanduser().resolve()
        if not tdir.exists() or not tdir.is_dir():
            raise FileNotFoundError(f"TEMPLATE_DIR_OVERRIDE is invalid: {tdir}")
        return tdir

    script_dir = get_script_dir()

    # 1️⃣ Prefer template_v* beside this script
    candidates = sorted(script_dir.glob("template_v*"))

    if candidates:
        return candidates[-1].resolve()

    # 2️⃣ Otherwise search workspace_root
    candidates = sorted(Path(workspace_root).glob("template_v*"))

    if candidates:
        return candidates[-1].resolve()

    # 3️⃣ Otherwise search parents
    for p in [workspace_root, *workspace_root.parents]:
        candidates = sorted(Path(p).glob("template_v*"))
        if candidates:
            return candidates[-1].resolve()

    raise FileNotFoundError(
        "No directory matching 'template_v*' could be found."
    )


def discover_subchapters(workspace_root: Path) -> List[SubchapterInfo]:
    """
    Find all subchapter folders inside numeric chapter folders.
    Excludes folders whose names contain 'problems'.
    """
    discovered: List[SubchapterInfo] = []

    chapter_dirs = sorted(
        [p for p in workspace_root.iterdir() if is_numeric_chapter_dir(p)],
        key=lambda x: int(x.name)
    )

    for chap_dir in chapter_dirs:
        subdirs = sorted([p for p in chap_dir.iterdir() if p.is_dir()], key=lambda x: x.name)
        for sd in subdirs:
            if "problems" in sd.name.lower():
                continue
            discovered.append(
                SubchapterInfo(
                    chapter=chap_dir.name,
                    name=sd.name,
                    path=sd.resolve()
                )
            )

    return discovered


def resolve_selected_subchapters(all_items: List[SubchapterInfo]) -> List[SubchapterInfo]:
    """
    Selection rules:
      - chapters = ['22'] -> all under chapter 22
      - subchapters = ['22'] -> all under chapter 22
      - subchapters = ['22-*'] -> all under chapter 22
      - subchapters = ['22.1'] -> exact folder name match
      - subchapters = ['22-1'] -> exact folder name match
      - PROCESS_ALL = True -> everything
    """
    if PROCESS_ALL:
        return all_items

    selected: List[SubchapterInfo] = []

    if chapters:
        chapter_set = {str(c).strip() for c in chapters}
        selected.extend([item for item in all_items if item.chapter in chapter_set])

    if subchapters:
        tokens = [str(s).strip() for s in subchapters if str(s).strip()]
        for token in tokens:
            # case 1: token is chapter only, e.g. '22'
            if re.fullmatch(r"[1-9]\d*", token):
                selected.extend([item for item in all_items if item.chapter == token])
                continue

            # case 2: chapter wildcard, e.g. '22-*' or '22.*'
            m = re.fullmatch(r"([1-9]\d*)[-.]\*", token)
            if m:
                chap = m.group(1)
                selected.extend([item for item in all_items if item.chapter == chap])
                continue

            # case 3: exact folder name
            selected.extend([item for item in all_items if item.name == token])

    # de-duplicate while preserving order
    seen = set()
    uniq: List[SubchapterInfo] = []
    for item in selected:
        key = item.path
        if key not in seen:
            seen.add(key)
            uniq.append(item)

    return uniq


def copy_template_files(template_dir: Path, target_dir: Path) -> None:
    copied = 0
    for f in template_dir.iterdir():
        if f.is_file():
            shutil.copy2(f, target_dir / f.name)
            copied += 1
    log(f"Copied {copied} template file(s) from {template_dir} to " + target_dir.name)


def run_py(
    script: str,
    cwd: Path,
    extra_env: Optional[dict] = None,
    log_file: Optional[str] = None,
) -> None:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    script_path = cwd / script
    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    log_handle = None
    try:
        if log_file is not None:
            log_path = cwd / log_file
            log_handle = open(log_path, "w", encoding="utf-8", errors="replace")

        proc = subprocess.Popen(
            [sys.executable, script],
            cwd=str(cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        prefix = f"[{cwd.name}/{script}] "

        assert proc.stdout is not None
        for line in proc.stdout:
            stamped_line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {prefix}{line}"
            print(stamped_line, end="")
            sys.stdout.flush()
            if log_handle is not None:
                log_handle.write(stamped_line)
                log_handle.flush()

        proc.stdout.close()
        returncode = proc.wait()

        if returncode != 0:
            raise RuntimeError(f"{script} failed with code {returncode} in {cwd}")

    finally:
        if log_handle is not None:
            log_handle.close()



def main(SCRIPT_1, SCRIPT_2, LOG_1, LOG_2) -> int:
    workspace_root = detect_workspace_root()
    template_dir = detect_template_dir(workspace_root)
    all_subchapters = discover_subchapters(workspace_root)

    if not all_subchapters:
        raise RuntimeError(f"No subchapter directories found under workspace root: {workspace_root}")

    log(f"Script directory   : {get_script_dir()}")
    log(f"Launch directory   : {Path.cwd().resolve()}")
    log(f"Workspace root     : {workspace_root}")
    log(f"Template directory : {template_dir}")
    log(f"Detected {len(all_subchapters)} subchapter directorie(s)")

    print("\nDetected subchapters:")
    for item in all_subchapters:
        print(f"  - {item.display}")

    selected = resolve_selected_subchapters(all_subchapters)

    if not selected:
        log("No matching subchapters selected. Aborting.", level="ERROR")
        return 1

    print("\nSelected subchapters to process:")
    for item in selected:
        print(f"  - {item.display}")

    print("")
    failures = []

    for idx, item in enumerate(selected, start=1):
        log(f"Processing [{idx}/{len(selected)}]: {item.display}")

        try:
            list_of_files = ['slides.pdf', 'slides.tex', 'script.txt', 'slides.mp4']
            result = all((item.path / f).is_file() for f in list_of_files)

            if result:
                print(f"{list_of_files} are in existence in {item.name}")
                print(f"To skip current execution in {item.name}\n")
            else:
                missing = [f for f in list_of_files if not (item.path / f).is_file()]
                print(f"{missing} are not in existence in {item.name}")
                print(f"To execute in {item.name}")

                copy_template_files(template_dir, item.path)

                if SCRIPT_1.strip():
                    log(f"Running {SCRIPT_1} in {item.name}")
                    run_py(SCRIPT_1, cwd=item.path, log_file=LOG_1)

                if SCRIPT_2.strip():
                    log(f"Running {SCRIPT_2} in {item.name}")
                    run_py(SCRIPT_2, cwd=item.path, log_file=LOG_2)

                log(f"Completed: {item.display}\n")

        except Exception as e:
            failures.append((item.display, str(e)))
            log(f"FAILED: {item.display} -> {e}", level="ERROR")
            print("")

    print("\n" + "=" * 70)
    if failures:
        log(f"Completed with {len(failures)} failure(s)", level="ERROR")
        for name, err in failures:
            print(f"  - {name}: {err}")
        return 1
    else:
        log("All selected subchapters completed successfully")
        return 0


if __name__ == "__main__":
    overall_status = 0

    def make_log_name(script_name: str) -> str:
        script_name = script_name.strip()
        if not script_name:
            return ""
        return Path(script_name).stem + ".log"
    
    
    ### 1 ###
    SCRIPT_1 = "crop_figs_v3.py"
    SCRIPT_2 = ""
    LOG_1 = make_log_name(SCRIPT_1)
    LOG_2 = make_log_name(SCRIPT_2)
    overall_status |= main(SCRIPT_1, SCRIPT_2, LOG_1, LOG_2)
    
    
    ### 2 ###
    SCRIPT_1 = "map_and_rename_selenium_v8.py"
    SCRIPT_2 = ""
    LOG_1 = make_log_name(SCRIPT_1)
    LOG_2 = make_log_name(SCRIPT_2)
    overall_status |= main(SCRIPT_1, SCRIPT_2, LOG_1, LOG_2)
    #overall_status |= main(SCRIPT_1, SCRIPT_2, LOG_1, LOG_2)  
    
    ### 2.5 ###
    SCRIPT_1 = "map_and_rename_selenium_v8.py"
    SCRIPT_2 = ""
    LOG_1 = make_log_name(SCRIPT_1)
    LOG_2 = make_log_name(SCRIPT_2)
    overall_status |= main(SCRIPT_1, SCRIPT_2, LOG_1, LOG_2)  # execute twice
    
    
    ### 3 ###
    SCRIPT_1 = "gen_slides_selenium_v11.py"
    SCRIPT_2 = ""
    LOG_1 = make_log_name(SCRIPT_1)
    LOG_2 = make_log_name(SCRIPT_2)
    overall_status |= main(SCRIPT_1, SCRIPT_2, LOG_1, LOG_2)
    
    ### 3.5 ###
    SCRIPT_1 = "gen_slides_selenium_v11.py" # execute twice
    SCRIPT_2 = ""
    LOG_1 = make_log_name(SCRIPT_1)
    LOG_2 = make_log_name(SCRIPT_2)
    overall_status |= main(SCRIPT_1, SCRIPT_2, LOG_1, LOG_2)
    
    
    ### 4 ###
    SCRIPT_1 = "gen_script_selenium_v15.py"
    SCRIPT_2 = ""
    LOG_1 = make_log_name(SCRIPT_1)
    LOG_2 = make_log_name(SCRIPT_2)
    overall_status |= main(SCRIPT_1, SCRIPT_2, LOG_1, LOG_2)
    
    ### 4.5 ###
    SCRIPT_1 = "gen_script_selenium_v15.py"     #execute twice
    SCRIPT_2 = ""
    LOG_1 = make_log_name(SCRIPT_1)
    LOG_2 = make_log_name(SCRIPT_2)
    overall_status |= main(SCRIPT_1, SCRIPT_2, LOG_1, LOG_2)
    
    ### 5 ###
    SCRIPT_1 = "text_to_speech_v25.py"
    SCRIPT_2 = ""
    LOG_1 = make_log_name(SCRIPT_1)
    LOG_2 = make_log_name(SCRIPT_2)
    overall_status |= main(SCRIPT_1, SCRIPT_2, LOG_1, LOG_2)

    ### 6 ###
    SCRIPT_1 = "slice_pdf.py"
    SCRIPT_2 = ""
    LOG_1 = make_log_name(SCRIPT_1)
    LOG_2 = make_log_name(SCRIPT_2)
    overall_status |= main(SCRIPT_1, SCRIPT_2, LOG_1, LOG_2)
    
    ### 7 ###
    SCRIPT_1 = "gen_video.py"
    SCRIPT_2 = ""
    LOG_1 = make_log_name(SCRIPT_1)
    LOG_2 = make_log_name(SCRIPT_2)
    overall_status |= main(SCRIPT_1, SCRIPT_2, LOG_1, LOG_2)
    
    ### 8 ###
    SCRIPT_1 = "run_clean_leftover.py"
    SCRIPT_2 = ""
    LOG_1 = make_log_name(SCRIPT_1)
    LOG_2 = make_log_name(SCRIPT_2)
    overall_status |= main(SCRIPT_1, SCRIPT_2, LOG_1, LOG_2)    
    
    sys.exit(overall_status)
