"""SHA-attested cached-phase admission for Windows sourcebound orchestration.

The command exit code is not a durable identity proof of files emitted by
figure/slide/narration/TTS/video stages. Re-use requires the *same* protected
source and the full, reproducible immutable phase output manifest. A stored
source-only sample from PR362/443/444 must never bypass another full phase.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

SCHEMA = "WINDOWS_PHASE_OUTPUT_SHA_MANIFEST_V1"
PHASES = ("source_content", "narrated_audio", "sourcebound_video")


class PhaseEvidenceError(ValueError):
    pass


def _sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for b in iter(lambda: stream.read(1024*1024),b""):
            h.update(b)
    return h.hexdigest()


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise PhaseEvidenceError(message)


def _regular(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def _canonical_paths(folder: Path, phase: str) -> list[Path]:
    """Cover every material stage artifact, not merely a successful log."""
    _require(phase in PHASES, "Unknown sourcebound phase")
    root=Path(folder)
    _require(root.is_dir() and not root.is_symlink(), "Stage output tree missing")
    if phase=="source_content":
        required=("slides.tex","slides.pdf","script.txt")
        optional=("script_risk_report.json","script_risk_report.md",
                  "math_semantic_report.json","math_semantic_repair_prompt.json",
                  "figures_manifest.json")
        arts=sorted(p for p in root.iterdir() if
                    p.is_file() and p.suffix.lower() in (".png",".jpg",".jpeg")
                    and not p.name.startswith("."))
        files=[root/n for n in (*required,*optional) if (root/n).exists()]
        files.extend(arts)
    elif phase=="narrated_audio":
        required=("slides.pdf","script.txt","tts_fidelity_report.json")
        optional=("tts_input_manifest.json","tts_fidelity_report.md")
        audio=sorted(root.glob("slide*.wav"))
        _require(bool(audio),"No recorded source-WAV slides to reuse")
        numbers=[]
        for p in audio:
            match=re.fullmatch(r"slide(\d+)\.wav",p.name,re.I)
            _require(match is not None,"Unsafe/unknown original slide WAV filename")
            numbers.append(int(match.group(1)))
        _require(sorted(numbers)==list(range(1,len(numbers)+1)),
                 "Missing or duplicate original slide numbered WAV file")
        try:
            import pymupdf
            with pymupdf.open(root/"slides.pdf") as slides:
                pages=len(slides)
        except (ImportError,OSError,ValueError,RuntimeError) as exc:
            raise PhaseEvidenceError("Cannot verify source slide count for cached PCM") from exc
        _require(len(audio)==pages,
                 "The original authored slide count differs from recorded slide WAV count")
        files=[root/n for n in (*required,*optional) if (root/n).exists()]
        files.extend(audio)
    else:
        required=("lecture_completion.json",)
        optional=("slides.pdf","script.txt","tts_fidelity_report.json")
        video=sorted(root.glob("*.mp4"))
        _require(bool(video),"Cannot skip sourcebound video without real encoded MP4 parts")
        files=[root/n for n in (*required,*optional) if (root/n).exists()]
        files.extend(video)
    _require(all(_regular(root/n) and (root/n).stat().st_size>0
                 for n in required),f"Required original {phase} output missing")
    _require(bool(files) and all(_regular(p) and p.stat().st_size>0
                                 for p in files),"Invalid original output artifact")
    _require(len({p.name for p in files})==len(files),
             "Ambiguous duplicated original stage artifact")
    return sorted(files,key=lambda p:p.name)


def phase_output_manifest(*,folder:Path,phase:str,source_sha256:str)->dict:
    _require(isinstance(source_sha256,str)
             and bool(re.fullmatch("[a-f0-9]{64}",source_sha256)),
             "Require source bound SHA-256 before old stage reuse")
    root=Path(folder)
    source=root/"source.pdf"
    _require(_regular(source) and _sha(source)==source_sha256,
             "Stage output cannot be reused on changed textbook source")
    files=_canonical_paths(root,phase)
    return {
        "schema":SCHEMA,
        "phase":phase,
        "original_source_sha256":source_sha256,
        "output_files_sha256":{p.name:_sha(p) for p in files},
        "scope":"previous_successful_phase_output_bytes_not_full_academic_acceptance",
        "student_publication_authorized":False,
    }


def admit_completed_phase(*,prior:dict,folder:Path,phase:str,
                          source_sha256:str)->tuple[dict,bool]:
    """Return (verified stage output evidence, legacy adoption).

    A source-bound old stage_pass can be *adopted* only when real files match
    strict full stage output structure. Missing or changed files fail CLOSED
    before browser, TTS, FFmpeg, or other paid/non-idempotent work.
    """
    _require(isinstance(prior,dict)
             and prior.get("outcome")=="stage_pass"
             and prior.get("return_code")==0,
             "No previously successful execution phase eligible for reuse")
    fresh=phase_output_manifest(folder=folder,phase=phase,
                                source_sha256=source_sha256)
    old=prior.get("output_evidence")
    if old is not None:
        _require(old==fresh,
                 "Previously successful stage output bytes changed or were removed; "
                 "targeted revalidation required, do not silently repeat paid work")
        return fresh,False
    # Historical successful run lacked individual stage hashes. Retain its
    # command success but adopt only the original source and actual outputs;
    # never transfer any other candidate's broader science approval.
    return fresh,True
