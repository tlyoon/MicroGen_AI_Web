"""Opt-in series bridge to the *existing* MicroGen Gemini/TTS infrastructure.

Series mode is not enabled in runner.py. No output can be published from this
module into a source.pdf directory. All files belong to a separately chosen,
empty machine-local staging directory.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import wave

from .domains import load_profile
from .planning.source_scan import scan_pdf
from .planning.lesson_planner import validate_outline
from .storyboard_authoring import build_authoring_brief
from .storyboard_gate import canonical_sha256, inspect_storyboard


class SeriesBridgeError(ValueError):
    """Source/approval mismatch, stale artifacts, incomplete TTS or unsafe path."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size > 5_000_000:
        raise SeriesBridgeError(f"Missing or oversized JSON record: {path}")
    def unique(pairs):
        out={}
        for key,val in pairs:
            if key in out:
                raise SeriesBridgeError(f"Duplicate record key: {key}")
            out[key]=val
        return out
    doc=json.loads(path.read_text(encoding="utf-8-sig"),object_pairs_hook=unique)
    if not isinstance(doc,dict):
        raise SeriesBridgeError("Expected JSON object")
    return doc


def write_json_new(path: Path, data: dict | list) -> None:
    with path.open("x",encoding="utf-8") as stream:
        json.dump(data,stream,ensure_ascii=False,indent=2)
        stream.write("\n")


def check_selected_inputs(
    *,source_root: Path,source_pdf: Path,outline: dict,
    plan: dict,domain: str,part_id: str,profile_file: Path | None=None,
) -> tuple[dict,object,dict]:
    profile=load_profile(domain,profile_file=profile_file)
    scan=scan_pdf(source_pdf,source_root=source_root)
    try:
        validate_outline(outline,scan,profile,source_pdf=source_pdf)
    except ValueError as exc:
        raise SeriesBridgeError(f"Reviewed source validation failed: {exc}") from exc
    if plan.get("source_sha256")!=scan["source_sha256"]:
        raise SeriesBridgeError("Plan and actual textbook source have different hashes")
    if plan.get("profile")!={"id":profile.id,"version":profile.profile_version}:
        raise SeriesBridgeError("Plan uses a different teaching profile")
    parts=[p for p in plan.get("parts",[]) if p.get("part_id")==part_id]
    if len(parts)!=1:
        raise SeriesBridgeError("Selected part is absent/duplicated in the master plan")
    if plan.get("coverage",{}).get("review_required_concept_ids"):
        raise SeriesBridgeError("Lesson plan still has review-required concepts")
    return scan,profile,parts[0]


def prepare_authoring_bundle(
    *,source_root: Path,source_pdf: Path,outline: dict,plan: dict,
    domain: str,part_id: str,output_dir: Path,profile_file: Path | None=None,
) -> dict:
    """Create prompts, hashes and a local read-only reference PDF.

    No Gemini call is made yet. The later existing Selenium transport can
    receive this source copy and per-part prompt as its explicit inputs.
    """
    scan,profile,part=check_selected_inputs(
        source_root=source_root,source_pdf=source_pdf,outline=outline,
        plan=plan,domain=domain,part_id=part_id,profile_file=profile_file,
    )
    output_dir=output_dir.expanduser().resolve()
    source_root=source_root.resolve()
    source_pdf=source_pdf.resolve()
    if output_dir.exists() or output_dir.is_relative_to(source_root):
        raise SeriesBridgeError(
            "Use a NEW isolated staging folder outside the textbook tree"
        )
    if not output_dir.parent.is_dir():
        raise SeriesBridgeError("Staging parent directory does not exist")
    brief=build_authoring_brief(plan,outline,part_id,profile)
    # The source is copied only after all reviewed inputs pass. This remains
    # a frozen reference; subsequent source drift invalidates the original plan.
    output_dir.mkdir()
    try:
        shutil.copyfile(source_pdf,output_dir/"source.pdf")
        if _sha((output_dir/"source.pdf").read_bytes())!=scan["source_sha256"]:
            raise SeriesBridgeError("Source changed while copying authoring reference")
        (output_dir/"storyboard_authoring_brief.txt").write_text(
            brief,encoding="utf-8")
        (output_dir/"part_slides_instruction.txt").write_text(
            "Use source.pdf only for verified content supporting these reviewed "
            f"concepts: {', '.join(part['concept_ids'])}.\n"
            f"Subchapter: {plan['title']}.\n"
            f"Part {part['index']} of {part['part_count']}.\n"
            f"Planned slide count (including intro/outro): {part['planned_slide_count']}.\n"
            "Use a joint, explicitly reviewed storyboard for figure selection, "
            "semantic visual IDs and speech segments. Render one unique "
            "\\MGElement{stable.element.id}{actual visual} hyperlink anchor "
            "for every visible semantic element. Do not fabricate scientific "
            "content or source figure panels.\n"
            "This brief is only a generation instruction, NOT authorization "
            "to publish the resulting slides/video.\n\n"+brief,encoding="utf-8")
        result={
            "status":"prepared_not_generated",
            "source_sha256":scan["source_sha256"],
            "domain":profile.id,"profile_version":profile.profile_version,
            "part_id":part_id,"plan_sha256":canonical_sha256(plan),
            "concept_ids":part["concept_ids"],
            "planned_slide_count":part["planned_slide_count"],
            "requires":["actual_Gemini_joint_storyboard_authoring",
                        "subject_expert_review","Beamer_render_geometry",
                        "narration_TTS_QA","final_MP4_verification"],
        }
        write_json_new(output_dir/"part_authoring_manifest.json",result)
    except Exception:
        shutil.rmtree(output_dir)
        raise
    return result


def approve_storyboard_for_tts(
    *,source_root: Path,source_pdf: Path,outline: dict,plan: dict,
    storyboard: dict,review_receipt: dict,domain: str,part_id: str,
    profile_file: Path | None=None,
) -> dict:
    """Require explicit externally reviewed/approved scientific content.

    The receipt proves that a responsible reviewer explicitly approved the
    exact storyboard content. It is not an automatic scientific verifier.
    """
    scan,profile,_=check_selected_inputs(
        source_root=source_root,source_pdf=source_pdf,outline=outline,
        plan=plan,domain=domain,part_id=part_id,profile_file=profile_file,
    )
    structural=inspect_storyboard(
        storyboard,plan,outline,profile,scan=scan,source_pdf=source_pdf)
    if storyboard["part_id"]!=part_id:
        raise SeriesBridgeError("Requested video part and storyboard mismatch")
    if not isinstance(review_receipt,dict) or set(review_receipt)!={
            "status","storyboard_sha256","reviewed_by","review_note"}:
        raise SeriesBridgeError("Missing exact storyboard reviewer receipt")
    if (review_receipt["status"]!="approved"
            or review_receipt["storyboard_sha256"]!=canonical_sha256(storyboard)
            or not isinstance(review_receipt["reviewed_by"],str)
            or len(review_receipt["reviewed_by"].strip())<3
            or not isinstance(review_receipt["review_note"],str)
            or len(review_receipt["review_note"].strip())<20):
        raise SeriesBridgeError("Storyboard semantic review incomplete or stale")
    return structural


def make_tts_script(storyboard: dict) -> str:
    """Reuse existing synthesize_folder() '**Slide N [.. sec]:' grammar.

    Here a 'Slide N' *TTS block* denotes one semantic narration segment,
    NOT necessarily one rendered Beamer slide. Mapping remains in storyboard.
    """
    blocks=[]
    for index,seg in enumerate(storyboard["narration_segments"],1):
        text=seg["spoken_text"]
        if not isinstance(text,str) or not text.strip():
            raise SeriesBridgeError("Missing spoken segment text")
        if "\n**Slide" in text or "\r**Slide" in text:
            raise SeriesBridgeError("Narration contains a reserved legacy TTS header")
        blocks.append(f"**Slide {index} [{seg['estimated_duration_s']:.1f} sec]:\n"
                      f"{text.strip()}\n")
    return "\n".join(blocks)


def stage_tts_job(
    *,source_root: Path,source_pdf: Path,outline: dict,plan: dict,
    storyboard: dict,review_receipt: dict,domain: str,part_id: str,
    destination: Path,profile_file: Path | None=None,
) -> dict:
    """Materialize a self-contained, no-overwrite per-part TTS work folder."""
    structural=approve_storyboard_for_tts(
        source_root=source_root,source_pdf=source_pdf,outline=outline,
        plan=plan,storyboard=storyboard,review_receipt=review_receipt,
        domain=domain,part_id=part_id,profile_file=profile_file,
    )
    destination=destination.expanduser().resolve()
    if destination.exists() or destination.is_relative_to(source_root.resolve()):
        raise SeriesBridgeError("TTS staging path must be new and outside source tree")
    if not destination.parent.is_dir():
        raise SeriesBridgeError("TTS staging parent missing")
    script=make_tts_script(storyboard)
    from .automatic_math_semantic_qa import inspect_math_semantics
    scientific=inspect_math_semantics(script,source_sha256=structural.get("source_sha256"))
    if scientific["blocking_count"]:
        raise SeriesBridgeError(
            "Scientific domain/sign QA blocks TTS: "
            + ", ".join(sorted({r["rule"] for r in scientific["findings"]})))
    from .vendor_template_v2.script_tts_risk import analyze_script_text
    report=analyze_script_text(script)
    if any(r["severity"]=="blocking" for r in report["findings"]):
        raise SeriesBridgeError("Speech script has blocking technical-pronunciation risks")
    destination.mkdir()
    try:
        (destination/"script.txt").write_text(script,encoding="utf-8")
        write_json_new(destination/"storyboard.json",storyboard)
        write_json_new(destination/"tts_review_receipt.json",review_receipt)
        meta={
            "status":"tts_input_ready_not_synthesized",
            "part_id":part_id,"storyboard_sha256":canonical_sha256(storyboard),
            "script_sha256":_sha((destination/"script.txt").read_bytes()),
            "review_receipt_sha256":canonical_sha256(review_receipt),
            "segment_count":len(storyboard["narration_segments"]),
            "structural_status":structural["status"],
        }
        write_json_new(destination/"tts_job_manifest.json",meta)
        return meta
    except Exception:
        shutil.rmtree(destination)
        raise


def accept_legacy_tts_batch(tts_dir: Path,storyboard: dict,
                            *,pause_after_ms: int=150) -> list[dict]:
    """Adapt REAL MicroGen tts.py outputs to the Phase 3B WAV alignment engine.

    Fail closed on wrong text, unequal provenance, partial WAVs and mismatched
    provider/model/voice. Acoustics and speech content still need QA.
    """
    if not 0<=pause_after_ms<=1500:
        raise SeriesBridgeError("Invalid between-segment silence")
    saved=read_json(tts_dir/"tts_input_manifest.json")
    expected=storyboard["narration_segments"]
    items=saved.get("slides",[])
    if len(items)!=len(expected):
        raise SeriesBridgeError("Incomplete TTS manifest for semantic segments")
    manifest=[]
    actual_voices=set()
    for i,(seg,row) in enumerate(zip(expected,items),1):
        if row.get("slide")!=i or row.get("source_text")!=seg["spoken_text"] or (
                row.get("tts_text")!=seg["spoken_text"]):
            raise SeriesBridgeError(f"TTS speech text differs at segment {i}")
        identity=tuple(row.get(k) for k in ("provider","model","voice"))
        if any(not isinstance(x,str) or not x for x in identity):
            raise SeriesBridgeError("Missing TTS provider/model/voice provenance")
        actual_voices.add(identity)
        path=tts_dir/f"slide{i}.wav"
        if not path.is_file():
            raise SeriesBridgeError(f"Missing generated WAV for segment {i}")
        try:
            with wave.open(str(path),"rb") as f:
                if f.getnframes()<=0 or f.getcomptype()!="NONE":
                    raise SeriesBridgeError(f"Invalid PCM WAV for segment {i}")
        except (OSError,wave.Error) as exc:
            raise SeriesBridgeError(f"Unreadable PCM WAV for segment {i}") from exc
        manifest.append({
            "segment_id":seg["segment_id"],
            "filename":path.name,
            "speech_sha256":_sha(seg["spoken_text"].encode("utf-8")),
            "voice_id":":".join(identity),
            "pause_after_ms":pause_after_ms if i<len(expected) else 0,
        })
    if len(actual_voices)!=1:
        raise SeriesBridgeError(
            "Mixed TTS engines/models/voices; regenerate entire video part "
            "using a single verified voice before timing"
        )
    return manifest


def invoke_existing_tts(
    *,tts_dir: Path,storyboard: dict,provider: str,model: str,voice: str,
    python_executable: str=sys.executable,timeout_s: int=3600,
) -> list[dict]:
    """Explicit live TTS integration; NEVER called from preparing/QA paths.

    The caller must stage and approve the exact storyboard beforehand.
    """
    if provider not in ("gemini","chirp3") or not model or not voice:
        raise SeriesBridgeError("TTS provider/model/voice must be explicit")
    data=read_json(tts_dir/"tts_job_manifest.json")
    if data.get("status")!="tts_input_ready_not_synthesized" or (
            data.get("storyboard_sha256")!=canonical_sha256(storyboard)):
        raise SeriesBridgeError("Live TTS job is missing or stale")
    if _sha((tts_dir/"script.txt").read_bytes())!=data["script_sha256"]:
        raise SeriesBridgeError("Speech script changed after review")
    stored_storyboard=read_json(tts_dir/"storyboard.json")
    stored_approval=read_json(tts_dir/"tts_review_receipt.json")
    if (canonical_sha256(stored_storyboard)!=canonical_sha256(storyboard)
            or canonical_sha256(stored_approval)!=data.get("review_receipt_sha256")
            or stored_approval.get("status")!="approved"
            or stored_approval.get("storyboard_sha256")!=canonical_sha256(storyboard)):
        raise SeriesBridgeError("TTS review receipt or storyboard changed after approval")
    if any(tts_dir.glob("slide*.wav")):
        raise SeriesBridgeError("Refusing to overwrite existing TTS WAVs")
    # Reuse the established per-user AppData/Microvid credential loader,
    # without copying secrets into a source folder or Git checkout.
    from .runner import load_microvid_env
    load_microvid_env()
    cmd=[python_executable,"-m","selenium_pipeline.tts",
         "--folder",str(tts_dir),"--provider",provider,
         "--model",model,"--voice",voice]
    try:
        result=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout_s)
    except subprocess.TimeoutExpired as exc:
        raise SeriesBridgeError("Live TTS exceeded bounded job timeout") from exc
    if result.returncode:
        raise SeriesBridgeError("Existing MicroGen TTS failed: "
                                +(result.stdout+"\n"+result.stderr)[-1400:])
    return accept_legacy_tts_batch(tts_dir,storyboard)
