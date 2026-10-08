#!/usr/bin/env bash
# fix_video.sh
#
# Run from current directory
#   template_v2 must exist in the parent directory, i.e., ../template_v2
#
# What it does for each numbered chapter/subchapter directory like 22/22.1, 22/22.2, ... :
#   1) copy selected files from ../template_v2
#   2) run: python fix_slides_figure_sizes.py
#   3) run: pdflatex slides.tex
#
# Dry run:
#   ./fix_video.sh --dry-run
#
# Normal run:
#   ./fix_video.sh

set -u

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" || "${1:-}" == "-n" ]]; then
    DRY_RUN=1
fi

ROOT_DIR="$(pwd)"
TEMPLATE_DIR="$(cd ../template_v2 && pwd)"

FILES_TO_COPY=(
    "slice_pdf.py"
    "fix_slides_figure_sizes.py"
    "text_to_speech_v25.py"
    "gen_video.py"
)

log() {
    printf '[%s] %s\n' "$(date '+%F %T')" "$*"
}

run_cmd() {
    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "DRY-RUN: $*"
    else
        eval "$@"
    fi
}

copy_files_into_dir() {
    local target_dir="$1"
    local f
    for f in "${FILES_TO_COPY[@]}"; do
        if [[ ! -f "$TEMPLATE_DIR/$f" ]]; then
            log "WARNING: missing template file: $TEMPLATE_DIR/$f"
            continue
        fi
        run_cmd "cp -f \"$TEMPLATE_DIR/$f\" \"$target_dir/\""
    done
}

process_subdir() {
    local subdir="$1"

    log "Processing: $subdir"
    copy_files_into_dir "$subdir"

    if [[ ! -f "$subdir/slides.tex" ]]; then
        log "WARNING: slides.tex not found in $subdir ; skipping execution"
        return
    fi

    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "DRY-RUN: cd \"$subdir\" && python fix_slides_figure_sizes.py"
        echo "DRY-RUN: cd \"$subdir\" && pdflatex slides.tex"
    else
        (
            cd "$subdir" || exit 1

            log "Running python fix_slides_figure_sizes.py in $subdir"
            python fix_slides_figure_sizes.py
            py_status=$?
            if [[ $py_status -ne 0 ]]; then
                log "WARNING: fix_slides_figure_sizes.py failed in $subdir with exit code $py_status"
                exit $py_status
            fi

            log "Running pdflatex slides.tex in $subdir"
            pdflatex slides.tex
            tex_status=$?
            if [[ $tex_status -ne 0 ]]; then
                log "WARNING: pdflatex failed in $subdir with exit code $tex_status"
                exit $tex_status
            fi
        )
    fi
}

main() {
    log "Root directory     : $ROOT_DIR"
    log "Template directory : $TEMPLATE_DIR"
    if [[ "$DRY_RUN" -eq 1 ]]; then
        log "Mode               : DRY RUN"
    else
        log "Mode               : LIVE"
    fi

    local chapter_dir
    local subdir
    local found=0

    shopt -s nullglob
    for chapter_dir in "$ROOT_DIR"/*; do
        [[ -d "$chapter_dir" ]] || continue

        # Match top-level numbered directories only: 22, 23, 24, ...
        if [[ "$(basename "$chapter_dir")" =~ ^[0-9]+$ ]]; then
            for subdir in "$chapter_dir"/*; do
                [[ -d "$subdir" ]] || continue

                # Match numbered subdirectories only: 22.1, 22.2, 23.4, ...
                if [[ "$(basename "$subdir")" =~ ^[0-9]+\.[0-9]+$ ]]; then
                    found=1
                    process_subdir "$subdir"
                fi
            done
        fi
    done
    shopt -u nullglob

    if [[ "$found" -eq 0 ]]; then
        log "No numbered subdirectories found."
    else
        log "Done."
    fi
}

main
