# -*- coding: utf-8 -*
# MicroGen_AI Educational Automation Package
# © 2025 Dr. Yoon Tiem Leong, School of Physics, Universiti Sains Malaysia.
# This file is part of the MicroGen_AI package.
# Licensed under the MIT License (see LICENSE file in the project root).
# You may not use this file except in compliance with the License.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.


from pathlib import Path
import re

base = Path.cwd()
num_dir_re = re.compile(r"^\d+$")  # top-level dirs like "10", "11"

# sort parents numerically (10, 11, 12, ...)
parents = sorted(
    (p for p in base.iterdir() if p.is_dir() and num_dir_re.match(p.name)),
    key=lambda p: int(p.name)
)

import os
import subprocess
import sys,shutil
from pathlib import Path
##
##
import glob
base_dir = Path.cwd().parent
# --- auto-detect template folder matching "template_v*" ---
matches = sorted(glob.glob(str(base_dir / "template_v*")))
if not matches:
    raise FileNotFoundError("❌ No directory matching pattern 'template_v*' found.")
template_dir = Path(matches[-1])  # pick the latest (alphabetically or numerically)
print(f"📦 Using template directory: {template_dir}")

for top in parents:
    # subdirs like "10.1", "10.2", ... inside "10"
    sub_re = re.compile(rf"^{re.escape(top.name)}\.(\d+)$")
    best_minor = None
    best_name = None

    for sub in top.iterdir():
        if not sub.is_dir():
            continue
        m = sub_re.match(sub.name)
        if m:
            minor = int(m.group(1))
            if best_minor is None or minor > best_minor:
                best_minor, best_name = minor, sub.name

    if best_name:
        dirr = os.path.join(top.name, best_name)        
        f2cp = 'crop_pbset_fr_source_v2.py'
        file=os.path.join(template_dir,f2cp)
        src = Path(file)      
        dst = os.path.join(dirr, f2cp)
        shutil.copyfile(src, dst)
        print(f"Copied {src} into {dst}")
        #
        #f2cp= '.env'
        #file=os.path.join(template_dir,f2cp)
        #src = Path(file)      
        #dst = os.path.join(dirr, f2cp) 
        #shutil.copyfile(src, dst)
        #print(f"Copied and replaced: {dst}")
        #     
        try:
            croppy = "crop_pbset_fr_source_v2.py"
            origdir=os.getcwd()             
            os.chdir(dirr)
            print(f'To execute {croppy} in',os.getcwd())
            subprocess.run([sys.executable, croppy])    
            os.chdir(origdir)
            print('just exited, i am now in ',os.getcwd())
            print('')
        except:
            pass
