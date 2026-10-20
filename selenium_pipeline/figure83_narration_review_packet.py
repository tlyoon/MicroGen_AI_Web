"""Create isolated original-to-slide Figure 8.3 math review packet.

Montage is exact original source/slide rendered pixels; narration candidate
links are UNAPPROVED. No original PDF, source asset or MP4 overwritten.
"""
from __future__ import annotations
import json,shutil
from pathlib import Path
from .figure_source_identity import require,_sha
from .math_aware_slide5_figure_candidates import audit
from .figure_reflow_review_montage import source_slide_plot_montage

def build(*,source:Path,slides:Path,script:Path,output:Path)->dict:
    source,slides,script,output=(Path(x).absolute() for x in (source,slides,script,output))
    require(all(p.is_file() and not p.is_symlink() for p in (source,slides,script))
            and output.parent.is_dir() and not output.exists()
            and all(not output.is_relative_to(p.parent) for p in (source,slides,script)),
            "Originals must exist; isolated review output must be new")
    originals=[_sha(p) for p in (source,slides,script)]
    review=audit(source=source,slides=slides,script=script)
    require([review["source_sha256"],review["slides_sha256"],review["script_sha256"]]==originals
            and review["figure_element_tts_authorized"] is False,
            "Stale or approved mathematical hypothesis")
    output.mkdir()
    try:
        preview=source_slide_plot_montage(
            source=source,slides=slides,source_page=2,slide_page=5,
            figure_id="8.3",output=output/"source_slide_graph_comparison")
        require(preview["source_sha256"]==originals[0]
                and preview["slides_sha256"]==originals[1]
                and preview["publication_authorized"] is False,
                "Mathematical graph preview unbound to original source")
        result={
            "schema_version":1,
            "status":"FIGURE83_ORIGINAL_PIXELS_AND_SPOKEN_FUNCTION_REVIEW_REQUIRED",
            "original_source_sha256":originals[0],
            "original_slides_sha256":originals[1],
            "original_script_sha256":originals[2],
            "original_montage_sha256":preview["montage_sha256"],
            "figure_id":"8.3","slide":5,
            "narration_utterance_candidates":review["utterances"],
            "source_plot_count":preview["detected_graph_count"],
            "source_plot_order_to_function_names_verified":False,
            "source_math_word_to_slide_pixel_identity_verified":False,
            "mathematical_axes_labels_accuracy_verified":False,
            "spoken_function_to_element_alignment_verified":False,
            "element_tts_authorized":False,
            "student_publication_authorized":False,
        }
        with (output/"figure83_reviewer_packet.json").open("x",encoding="utf8") as f:
            json.dump(result,f,indent=2,ensure_ascii=True,sort_keys=True)
        require([_sha(p) for p in (source,slides,script)]==originals,
                "Original teaching assets changed")
        return result
    except Exception:
        shutil.rmtree(output)
        raise

def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    for field in ("source","slides","script","output"):
        p.add_argument("--"+field,required=True,type=Path)
    a=p.parse_args(argv)
    r=build(source=a.source,slides=a.slides,script=a.script,output=a.output)
    print(json.dumps({"status":r["status"],
        "source_plot_count":r["source_plot_count"],
        "utterance_count":len(r["narration_utterance_candidates"]),
        "element_tts_authorized":r["element_tts_authorized"]},indent=2))
    return 2
if __name__=="__main__":raise SystemExit(main())
