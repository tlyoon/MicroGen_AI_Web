# -*- coding: utf-8 -*-
# MicroGen_AI Educational Automation Package
# (c) 2025 Dr. Yoon Tiem Leong, School of Physics, Universiti Sains Malaysia.

import glob
import subprocess
import sys
from pathlib import Path

import fix_latex_selenium_v4 as fl


def run_clean_leftover() -> None:
    script_path = Path(__file__).resolve().with_name("run_clean_leftover.py")
    subprocess.run([sys.executable, str(script_path)], check=True)


def main() -> None:
    run_clean_leftover()

    all_tex = sorted(set(glob.glob("*.tex")))
    for q in all_tex:
        print(q, flush=True)
        fl.fix_latex(str(q))

    run_clean_leftover()


if __name__ == "__main__":
    main()