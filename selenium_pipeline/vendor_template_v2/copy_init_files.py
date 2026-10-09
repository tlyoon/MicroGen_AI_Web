from pathlib import Path
import re, glob, shutil

script_dir = Path(__file__).resolve().parent
parent_dir = script_dir.parent

def template_version_key(path: Path) -> int:
    m = re.fullmatch(r"template_v(\d+)", path.name)
    if not m:
        return -1
    return int(m.group(1))

candidates = [
    p for p in parent_dir.iterdir()
    if p.is_dir() and re.fullmatch(r"template_v\d+", p.name)
]

if not candidates:
    raise FileNotFoundError(f"No template_v* directory found under: {parent_dir}")

template_dir = max(candidates, key=template_version_key)

print(f"Using latest template directory: {template_dir}")

cwd_dir = Path(__file__).resolve().parent
print(f"Demo directory     : {cwd_dir}")
print(f"Template directory : {template_dir}")

# --------------------------------------------------
# directories
# --------------------------------------------------


# --------------------------------------------------
# files to copy
# --------------------------------------------------

patterns = [
    "gen_md36.py",
    "gen_json3.py",
    "selenium.py",
    "launch_gemini_chrome.py",
    "gen_folders_v*.py",
    "gen_folders_problems.py",
    "w_gen_problems_xml_in_chapters_sel_v*.py",
    "w_gen_slides_video_in_chapters_sel_v*.py",
]

# --------------------------------------------------
# copy files
# --------------------------------------------------

copied = 0

for pattern in patterns:

    matches = glob.glob(str(template_dir / pattern))

    for file in matches:

        src = Path(file)
        dst = cwd_dir / src.name

        shutil.copy2(src, dst)

        print(f"Copied: {src.name}")
        copied += 1

print(f"\nTotal files copied: {copied}")