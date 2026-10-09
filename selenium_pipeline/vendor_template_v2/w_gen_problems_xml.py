# MicroGen_AI Educational Automation Package
# © 2025 Dr. Yoon Tiem Leong, School of Physics, Universiti Sains Malaysia.
#
# This file is part of the MicroGen_AI package.
#
# Licensed under the MIT License (see LICENSE file in the project root).
# You may not use this file except in compliance with the License.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

import time
import os
import functions
start_time = time.time()

# --- your code here ---
#prefices = ["w_gen_problems","w_gen_xml","duplicate_texpdf","run_gen_problems","run_gen_xml"]
#prefices = ["w_run_gen_xml","duplicate_texpdf","run_gen_xml"]
prefices = ["w_gen_problems","w_gen_xml"]

functions.prefices(prefices)
# --- your code here ---

fn = 'run_gen_problems_xml.py'
elapsed = time.time() - start_time
print(f"{fn} elapsed time: {elapsed:.4f} seconds")
with open(f"{fn}_timing.log", "a", encoding="utf-8") as log_file:
    log_file.write(f"{fn} elapsed time: {elapsed:.4f} seconds\n")
    


