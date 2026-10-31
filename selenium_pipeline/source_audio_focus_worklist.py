"""Join verified real PCM timing candidates to original PDF review targets.

Only review candidates: neither a lexical match nor a word timestamp can
certify the meaning of a mathematical formula or figure panel.
"""
from __future__ import annotations
import argparse, json, math, wave
from pathlib import Path
from .element_plan_autodraft import propose, stable_recommendations
from .original_thomas84_offline_word_pdf_timing import tokenize_reference_sentences
from .source_label_geometry_evidence import inspect as inspect_labels
from .runner import blocks
from .figure_source_identity import require, _sha

def inspect(*, root:Path, timing_receipt:Path)->dict:
    root,timing_receipt=Path(root).absolute(),Path(timing_receipt).absolute()
    require(timing_receipt.is_file() and not timing_receipt.is_symlink(),
            "Missing real acoustic analysis receipt")
    timing=json.loads(timing_receipt.read_text(encoding="utf8"))
    require(timing.get("status")=="REAL_ASR_WORD_TIMING_CANDIDATES_ONLY"
            and len(timing.get("sections",[]))==3
            and timing.get("student_publication_authorized") is False,
            "Unrecognized original-acoustic receipt")
    sections=[]
    for sec, previous in zip(("8.4","8.5","8.6"),timing["sections"]):
        folder=root/sec
        files=[folder/x for x in ("source.pdf","slides.pdf","script.txt")]
        require(previous.get("section")==sec
                and all(p.is_file() and not p.is_symlink() for p in files),
                "Section identity or source evidence missing")
        hashes=[_sha(p) for p in files]
        require(hashes==[previous[k] for k in (
                    "source_sha256","slides_sha256","script_sha256")],
                "Original source changed after acoustic analysis")
        draft=propose(source_pdf=files[0],slides_pdf=files[1],script_txt=files[2])
        labels=inspect_labels(source=files[0],slides=files[1],script=files[2])
        spoken=blocks(files[2].read_text(encoding="utf-8-sig"))
        require(len(draft["slides"])==len(spoken)==len(previous["slides"])
                ==len(labels["slides"]), "Original slide count drift")
        rows=[]
        for (index,text),slide,acoustic,label_row in zip(
            spoken,draft["slides"],previous["slides"],labels["slides"]
        ):
            require(index==slide["slide_number"]==acoustic["slide"]==label_row["slide"],
                    "Timing and visual slide identifiers mismatch")
            wav=folder/f"slide{index}.wav"
            require(_sha(wav)==acoustic["wav_sha256"],
                    "Original WAV differs from genuine acoustic timing source")
            with wave.open(str(wav),"rb") as audio:
                duration = audio.getnframes()/audio.getframerate()
            require(math.isfinite(duration) and duration > 0
                    and abs(duration-acoustic["wav_duration_s"]) <= .0002,
                    "Acoustic receipt duration mismatches original PCM")
            sentences,_=tokenize_reference_sentences(text)
            timed=acoustic["sentence_timing_candidates"]
            require(len(sentences)==len(timed)==acoustic["sentence_count"],
                    "Original utterance segment count changed")
            choices=[]
            previous_start = -1.0
            targets=slide["auto_candidate_targets"]
            for original_sentence, anchor in zip(sentences,timed):
                require(original_sentence["narration_fragment_sha256"]==
                        anchor["narration_fragment_sha256"],
                        "Actual timing no longer maps to this spoken text")
                fraction=anchor["actual_ASR_word_anchor_fraction"]
                count=anchor["actual_ASR_aligned_anchor_count"]
                expected=anchor["expected_word_count"]
                require(type(count) is int and type(expected) is int
                        and 0 <= count <= expected and expected > 0
                        and type(fraction) in (float,int) and math.isfinite(fraction)
                        and abs(fraction - round(count/expected,4)) <= .00011,
                        "Acoustic anchor count/fraction contradicts original words")
                if anchor["word_timing_hypothesis_available"]:
                    require(count > 0,"Timed utterance lacks real acoustic word evidence")
                    start,end=(anchor["first_matched_real_audio_second"],
                               anchor["last_matched_real_audio_second"])
                    require(all(type(v) in (float,int) and math.isfinite(v)
                                for v in (start,end)) and
                            0 <= start <= end <= duration + .001,
                            "Word timing lies outside actual PCM duration")
                    require(start >= previous_start,
                            "Word-timed sentences violate narration order")
                    previous_start = start
                else:
                    require(anchor["first_matched_real_audio_second"] is None
                            and anchor["last_matched_real_audio_second"] is None,
                            "Unanchored narration cannot carry invented timing")
                candidates=stable_recommendations(
                    original_sentence["narration_fragment"],targets)
                choices.append({
                    "sentence_index":original_sentence["sentence_index"],
                    "source_narration_sha256":anchor["narration_fragment_sha256"],
                    "real_acoustic_timing_candidate":bool(anchor[
                        "word_timing_hypothesis_available"]),
                    "real_audio_first_second":anchor["first_matched_real_audio_second"],
                    "real_audio_last_second":anchor["last_matched_real_audio_second"],
                    "actual_word_anchor_fraction":anchor["actual_ASR_word_anchor_fraction"],
                    "source_pdf_text_focus_candidates_review_only":candidates,
                    "semantic_equation_or_figure_match_verified":False,
                    "highlight_approved":False,
                })
            require(sum(bool(x["real_acoustic_timing_candidate"]) for x in choices)
                    == acoustic["actual_timed_sentence_candidates"],
                    "Acoustic receipt aggregate contradicts individual sentences")
            rows.append({"slide":index,"wav_sha256":acoustic["wav_sha256"],
                         "source_grounded_visible_labels":label_row["labels"],
                         "sentences":choices,
                         "full_element_focus_verified":False})
        require([_sha(p) for p in files]==hashes,
                "Original teaching materials changed during source mapping")
        sections.append({"section":sec,"slide_count":len(rows),"slides":rows})
    return {"schema_version":1,
            "status":"REAL_WORD_TIMING_TO_PDF_FOCUS_CANDIDATES_REVIEW_ONLY",
            "sections":sections,
            "slide_count":sum(s["slide_count"] for s in sections),
            "timed_narration_candidates":sum(
                sum(x["real_acoustic_timing_candidate"] for x in slide["sentences"])
                for sec in sections for slide in sec["slides"]),
            "mathematical_semantic_mapping_accepted":False,
            "encoded_element_highlights_accepted":False,
            "student_publication_authorized":False}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("root","timing-receipt","out"):
        p.add_argument("--"+key,type=Path,required=True)
    a=p.parse_args(argv)
    out=a.out.absolute()
    require(out.parent.is_dir() and not out.exists() and not out.is_symlink()
            and not out.is_relative_to(a.root.absolute()),
            "External exclusive audit output required")
    report=inspect(root=a.root,timing_receipt=a.timing_receipt)
    with out.open("x",encoding="utf8") as f:
        json.dump(report,f,indent=2)
        f.write("\n")
    print(json.dumps({k:report[k] for k in (
        "status","slide_count","timed_narration_candidates")}))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
