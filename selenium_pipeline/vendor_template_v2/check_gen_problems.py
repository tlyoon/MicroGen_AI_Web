import os

def scan_problem_sets(root_dir="."):
    # The 4 specific suffixes we are looking for per set
    required_suffixes = ["_mcq.xml", "_mcq.html", ".tex", ".pdf"]

    print(f"{'CHAPTER':<8} | {'BASE PREFIX':<35} | {'STATUS'}")
    print("-" * 85)

    # Get numbered directories only (1, 2, 7, etc.)
    chapters = sorted([d for d in os.listdir(root_dir) if d.isdigit() and os.path.isdir(os.path.join(root_dir, d))])

    for chapter in chapters:
        problems_path = os.path.join(root_dir, chapter, "problems")
        
        if not os.path.isdir(problems_path):
            continue

        # Map to store: 'SECTION_2-1_problemset' -> {'.tex', '.pdf', etc}
        file_map = {}

        # Corrected the loop here: just iterate over os.listdir()
        for filename in os.listdir(problems_path):
            
            # 1. Skip 'problems.pdf' and files that don't match our pattern
            if filename.lower() == "problems.pdf" or "_problemset" not in filename:
                continue

            # 2. Extract the base prefix
            # If it's an MCQ file, the prefix is everything before '_mcq'
            if "_mcq" in filename:
                base = filename.split("_mcq")[0]
            else:
                # Otherwise, it's a standard .tex or .pdf, strip the extension
                base = os.path.splitext(filename)[0]

            if base not in file_map:
                file_map[base] = set()

            # 3. Store what suffix this specific file represents
            # This identifies if we found the .tex, .pdf, _mcq.html, or _mcq.xml
            suffix = filename.replace(base, "")
            file_map[base].add(suffix)

        # 4. Check results for this chapter
        chapter_output_found = False
        for base, found_suffixes in sorted(file_map.items()):
            chapter_output_found = True
            missing = [s for s in required_suffixes if s not in found_suffixes]

            if not missing:
                print(f"{chapter:<8} | {base:<35} | COMPLETE")
            else:
                # Show exactly which files are missing from the set
                print(f"{chapter:<8} | {base:<35} | MISSING: {', '.join(missing)}")
        
        if chapter_output_found:
            print("") # Visual break between chapters

if __name__ == "__main__":
    scan_problem_sets()