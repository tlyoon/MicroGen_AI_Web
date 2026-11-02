"""Exact source, stage-input and output hashes for main MicroGen runner resume.

This augments—not replaces—runner.check_valid and strict audio/figure/video
academic rules. No publication, paid provider calls or material repair here.
"""
from __future__ import annotations
import hashlib
import re
from pathlib import Path

SCHEMA="MICROGEN_RUNNER_STAGE_SHA256_V1"
STAGES=("figures","slides","narration","script_qa","tts","tts_qa","video")

class RunnerReuseError(ValueError):
    pass

def _hash(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def _assert(ok:bool,why:str)->None:
    if not ok:raise RunnerReuseError(why)

def _paths(folder:Path,stage:str)->tuple[list[Path],list[Path]]:
    _assert(stage in STAGES,"Unknown runner stage")
    root=Path(folder)
    _assert(root.is_dir() and not root.is_symlink(),"Original job workspace absent")
    def exact(*names):
        return [root/n for n in names]
    figures=sorted(p for p in root.iterdir() if
                   p.is_file() and not p.is_symlink()
                   and (p.name.lower().startswith("figure") or
                        p.name=="figures_manifest.json")
                   and p.suffix.lower() in (".png",".jpg",".jpeg",".json"))
    wavs=sorted(p for p in root.glob("slide*.wav")
                if re.fullmatch(r"slide[1-9][0-9]*\.wav",p.name,re.I))
    source=exact("source.pdf")
    if stage=="figures":
        # The geometric/source image audit remains independently mandatory.
        inputs=source
        # Figure-free textbooks still have real source page/crop extraction
        # receipts; their previous no-image pass is not permission to rerun
        # Gemini just because there is no Figure*.png in the source section.
        extracted=[p for dirname in ("pages","crops")
                   for p in (root/dirname).rglob("*")
                   if p.is_file() and not p.is_symlink()]
        outputs=figures+sorted(extracted)
        _assert(outputs,"No source figure/page extraction evidence to reuse")
    elif stage=="slides":
        inputs=source+figures
        outputs=exact("slides.tex","slides.pdf")
    elif stage=="narration":
        inputs=source+exact("slides.pdf")
        outputs=exact("script.txt")
    elif stage=="script_qa":
        inputs=source+exact("slides.pdf","script.txt")
        outputs=exact("script_risk_report.json","script_risk_report.md",
                      "math_semantic_report.json","math_semantic_repair_prompt.json")
    elif stage=="tts":
        inputs=source+exact("slides.pdf","script.txt")
        outputs=wavs
        manifest=root/"tts_input_manifest.json"
        if manifest.exists(): outputs.append(manifest)
        _assert(bool(wavs),"No physical original sound files")
    elif stage=="tts_qa":
        inputs=source+exact("slides.pdf","script.txt")+wavs
        outputs=exact("tts_fidelity_report.json","tts_fidelity_report.md")
        _assert(bool(wavs),"No physical original sound files at audio QA")
    else:
        inputs=source+exact("slides.pdf","script.txt")+wavs
        outputs=exact("lecture_completion.json")
        # Multipart output must not be mistaken for old static slides.mp4.
        parts=sorted(p for p in root.glob("*.mp4") if p.is_file())
        _assert(bool(parts),"No real encoded MP4 to reuse")
        outputs+=parts
    names=[p.relative_to(root).as_posix() for p in inputs+outputs]
    _assert(len(set(names))==len(names),
            "Unclear duplicate artifact across inputs and outputs")
    _assert(all(p.is_file() and not p.is_symlink() and p.stat().st_size>0
                for p in inputs+outputs),"Missing, empty or symlinked source/stage output")
    return inputs,outputs

def build_stage_evidence(folder:Path,stage:str,source_sha256:str)->dict:
    _assert(bool(re.fullmatch(r"[0-9a-f]{64}",source_sha256)),
            "No verified original source SHA")
    inputs,outputs=_paths(Path(folder),stage)
    _assert(_hash(Path(folder)/"source.pdf")==source_sha256,
            "Source changed since previously accepted stage")
    return {
        "schema":SCHEMA,
        "stage":stage,
        "original_source_sha256":source_sha256,
        "input_sha256":{p.relative_to(folder).as_posix():_hash(p) for p in inputs},
        "output_sha256":{p.relative_to(folder).as_posix():_hash(p) for p in outputs},
        "technical_scope_only":True,
        "student_publication_authorized":False,
    }

def decide_stage_reuse(*,folder:Path,stage:str,
                       source_sha256:str,accepted:dict,
                       model_stamp:str,validity_passed:bool)->tuple[dict,bool]:
    """Safely accept prior identical stage model, inputs and file fingerprints.

    Legacy model-only stamps can be adopted iff the exact stage is still
    genuinely check_valid. Otherwise block, never trigger billable replay.
    """
    _assert(isinstance(accepted,dict) and accepted.get("model")==model_stamp,
            "Model/version differs from old accepted stage")
    _assert(validity_passed is True,
            "Prior accepted stage fails current technical validation")
    current=build_stage_evidence(folder,stage,source_sha256)
    old=accepted.get("artifact_evidence")
    if old is not None:
        _assert(old==current,
                "Previously validated stage input or output hashes changed; "
                "halt for targeted review instead of blindly regenerating")
        return current,False
    return current,True

def refresh_repaired_tts_evidence(*,folder:Path,source_sha256:str,
                                  accepted_tts:dict,model_stamp:str,
                                  tts_and_qa_valid:bool)->dict:
    """After successful source-bound selective QA WAV repairs, refresh old TTS
    file snapshot—never a fresh synthesis and never a new release approval."""
    _assert(tts_and_qa_valid is True,
            "Cannot refresh original audio proof without actual TTS QA passing")
    _assert(isinstance(accepted_tts,dict) and
            accepted_tts.get("model")==model_stamp,
            "Selected QA repairs cannot claim a different model's previous audio")
    return build_stage_evidence(folder,"tts",source_sha256)
