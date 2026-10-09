# -*- coding: utf-8 -*-
# MicroGen_AI Educational Automation Package
# © 2025 Dr. Yoon Tiem Leong, School of Physics, Universiti Sains Malaysia.
#
# Improved batch wrapper for problem-set generation:
#     * find chapter/problems/ directories
#     * copy template_v* files into each problems directory
#     * run w_gen_problems.py, w_gen_xml.py inside each problems directory
# - Allows selecting specific chapters or processing all detected chapters
# - Supports dry-run mode

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
# 1) chapters = ['22']        -> process 22/problems only
# 2) chapters = ['22', '23']  -> process selected chapter/problems dirs
# 3) PROCESS_ALL = True       -> process all detected chapter/problems dirs
# ---------------------------------------------------------------------
#chapters = ['30','31','32','33']          # examples: ['22'], ['22', '23']
#chapters = ['33']          # examples: ['22'], ['22', '23']
chapters = [ ]          # examples: ['22'], ['22', '23']
PROCESS_ALL = True #False             # set True to process all detected chapters

# ---------------------------------------------------------------------
# DRY RUN
# True  -> print what would be done, but do not copy or execute
# False -> perform actual copy and execution
# ---------------------------------------------------------------------
DRY_RUN = False # False  #True #False ##

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
class ProblemDirInfo:
    chapter: str
    path: Path

    @property
    def display(self) -> str:
        return f"{self.chapter}/problems"


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


def discover_problem_dirs(workspace_root: Path) -> List[ProblemDirInfo]:
    """
    Find all chapter/problems directories inside numeric chapter folders.
    """
    discovered: List[ProblemDirInfo] = []

    chapter_dirs = sorted(
        [p for p in workspace_root.iterdir() if is_numeric_chapter_dir(p)],
        key=lambda x: int(x.name)
    )

    for chap_dir in chapter_dirs:
        psdir = chap_dir / "problems"
        if psdir.is_dir():
            discovered.append(
                ProblemDirInfo(
                    chapter=chap_dir.name,
                    path=psdir.resolve()
                )
            )

    return discovered


def resolve_selected_problem_dirs(all_items: List[ProblemDirInfo]) -> List[ProblemDirInfo]:
    """
    Selection rules:
      - chapters = ['22'] -> only 22/problems
      - chapters = ['22', '23'] -> selected chapter/problems dirs
      - PROCESS_ALL = True -> everything
    """
    if PROCESS_ALL:
        return all_items

    selected: List[ProblemDirInfo] = []

    if chapters:
        chapter_set = {str(c).strip() for c in chapters if str(c).strip()}
        selected.extend([item for item in all_items if item.chapter in chapter_set])

    # de-duplicate while preserving order
    seen = set()
    uniq: List[ProblemDirInfo] = []
    for item in selected:
        key = item.path
        if key not in seen:
            seen.add(key)
            uniq.append(item)

    return uniq


def copy_template_files(template_dir: Path, target_dir: Path, dry_run: bool = False) -> None:
    files = [f for f in template_dir.iterdir() if f.is_file()]

    if dry_run:
        log(f"[DRY RUN] Would copy {len(files)} template file(s) from {template_dir} to {target_dir}")
        #for f in files:
        #    print(f"    COPY  {f}  ->  {target_dir / f.name}")
        return

    copied = 0
    for f in files:
        shutil.copy2(f, target_dir / f.name)
        copied += 1
    log(f"Copied {copied} template file(s) from {template_dir} to {target_dir}")


def run_py(
    script: str,
    cwd: Path,
    extra_env: Optional[dict] = None,
    log_file: Optional[str] = None,
    dry_run: bool = False,
) -> None:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    script_path = cwd / script
    if not script_path.exists() and not dry_run:
        raise FileNotFoundError(f"Script not found: {script_path}")

    if dry_run:
        print(f"    RUN   python {script}    (cwd={cwd})")
        if log_file is not None:
            print(f"    LOG   {cwd / log_file}")
        return

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

        prefix = f"[{cwd.parent.name}/{cwd.name}/{script}] "

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


def main(SCRIPT_PIPELINE, stage_label: Optional[str] = None) -> int:
    workspace_root = detect_workspace_root()
    template_dir = detect_template_dir(workspace_root)
    all_problem_dirs = discover_problem_dirs(workspace_root)

    if not all_problem_dirs:
        raise RuntimeError(f"No chapter/problems directories found under workspace root: {workspace_root}")

    log(f"Script directory   : {get_script_dir()}")
    log(f"Launch directory   : {Path.cwd().resolve()}")
    log(f"Workspace root     : {workspace_root}")
    log(f"Template directory : {template_dir}")
    log(f"Detected {len(all_problem_dirs)} problem directorie(s)")
    log(f"Dry run mode       : {DRY_RUN}")

    if DRY_RUN:
        print("\n" + "=" * 70)
        if stage_label:
            print(f"DRY RUN PIPELINE: {stage_label}")
        else:
            print("DRY RUN PIPELINE")
        for idx, (script, logfile) in enumerate(SCRIPT_PIPELINE, start=1):
            print(f"  [{idx}] {script}  ->  {logfile}")
        print("=" * 70)

    print("\nDetected problem directories:")
    for item in all_problem_dirs:
        print(f"  - {item.display}")

    selected = resolve_selected_problem_dirs(all_problem_dirs)

    if not selected:
        log("No matching problem directories selected. Aborting.", level="ERROR")
        return 1

    print("\nSelected problem directories to process:")
    for item in selected:
        print(f"  - {item.display}")

    print("")
    failures = []

    for idx, item in enumerate(selected, start=1):
        log(f"Processing [{idx}/{len(selected)}]: {item.display}")

        try:
            copy_template_files(template_dir, item.path, dry_run=DRY_RUN)
            for script, logfile in SCRIPT_PIPELINE:
                log(f"{'[DRY RUN] Would run' if DRY_RUN else 'Running'} {script} in {item.path}")
                run_py(
                    script,
                    cwd=item.path,
                    log_file=logfile,
                    dry_run=DRY_RUN,
                )

            print("")
            log(f"{'[DRY RUN] Would complete' if DRY_RUN else 'Completed'}: {item.display}")

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
        if DRY_RUN:
            log("Dry run completed successfully")
        else:
            log("All selected problem directories completed successfully")
        return 0


if __name__ == "__main__":
    STAGES = [
        ["crop_figs_v3.py"],
        ["map_and_rename_selenium_v8.py"],
        ["map_and_rename_selenium_v8.py"],  # intentionally run twice
        ["gen_problem_sets_selenium_v10.py"],
        ["gen_problem_sets_selenium_v10.py"],# intentionally run twice
        ["convert_pdftex_mcq_selenium_v7.py"],
        ["convert_pdftex_mcq_selenium_v7.py"],  # intentionally run twice
        ["run_clean_leftover.py"],
    ]

    def make_log_name(script_name: str) -> str:
        script_name = str(script_name).strip()
        if not script_name:
            raise ValueError("Empty script name encountered.")
        return Path(script_name).stem + ".log"

    def normalize_stage(stage_scripts):
        if not isinstance(stage_scripts, (list, tuple)) or not stage_scripts:
            raise ValueError(f"Invalid stage definition: {stage_scripts!r}")

        pipeline = []
        for script in stage_scripts:
            script = str(script).strip()
            if not script:
                raise ValueError(f"Blank script entry found in stage: {stage_scripts!r}")
            if not script.endswith(".py"):
                raise ValueError(f"Script must end with .py: {script!r}")

            pipeline.append((script, make_log_name(script)))
        return pipeline

    overall_failures = []

    for stage_index, stage_scripts in enumerate(STAGES, start=1):
        script_pipeline = normalize_stage(stage_scripts)
        stage_label = f"Stage {stage_index}/{len(STAGES)}"

        print("\n" + "=" * 70)
        if DRY_RUN:
            print(f"MAIN BLOCK PLAN: {stage_label}")
        else:
            print(stage_label)

        for script, logfile in script_pipeline:
            print(f"  - {script}  ->  {logfile}")
        print("=" * 70 + "\n")

        rc = main(script_pipeline, stage_label=stage_label)
        if rc != 0:
            overall_failures.append((stage_label, rc))
            if not DRY_RUN:
                break

    print("\n" + "#" * 70)
    if overall_failures:
        log(f"Overall run completed with {len(overall_failures)} failed stage(s)", level="ERROR")
        for stage_label, rc in overall_failures:
            print(f"  - {stage_label}: return code {rc}")
        sys.exit(1)
    else:
        if DRY_RUN:
            log("Overall dry run completed successfully for all stages")
        else:
            log("All stages completed successfully")
        sys.exit(0)
