"""Unattended, *verified* element TTS batch from exact source/slide narration.

Uses existing paid Gemini Flash-Lite/Kore batch engine, its 3-attempt retry
policy, whole-batch fallback and observed attempt evidence; no human signoff
and NO fabricated source/element mapping. Incomplete/ambiguous slides refuse
before any billed TTS call. Original lesson files are never overwritten.
"""
from __future__ import annotations
import hashlib
import json
import shutil
import tempfile
import wave
from pathlib import Path
from collections.abc import Callable

from .automatic_element_narration import (
    inspect_text_only, plan_for_audio, sha, AutomaticElementAudioError, need)
from .runner import blocks
from .tts_effective_identity import DEFAULT, verify_effective_identity
from .tts_attempt_evidence import AttemptEvidence
from .element_highlight_workflow import source_bound_plan

def _digest(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()

def _write_new(path:Path,obj:dict):
    with path.open("x",encoding="utf-8") as h:
        json.dump(obj,h,indent=2,ensure_ascii=False)
        h.write("\n")

def _duration(wav:Path)->float:
    need(wav.is_file() and not wav.is_symlink(),f"Missing narrated PCM WAV: {wav.name}")
    with wave.open(str(wav),"rb") as reader:
        need(reader.getnchannels()==1 and reader.getsampwidth()==2
             and reader.getcomptype()=="NONE" and 0<reader.getframerate()<=96000,
             "Original element TTS is not mono 16-bit PCM WAV")
        sec=reader.getnframes()/reader.getframerate()
    need(.2<=sec<=120, "Original element TTS duration unsupported")
    return sec

def _check_producer(folder:Path,text:list[str]):
    slots=list(enumerate(text,1))
    require_names=[f"slide{n}.wav" for n,_ in slots]
    manifest_path=folder/"tts_input_manifest.json"
    need(manifest_path.is_file() and not manifest_path.is_symlink(),
         "TTS batch has no independently checkable producer manifest")
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    result=verify_effective_identity(manifest,slots)
    if result["fallback_used"]:
        evidence=manifest.get("attempt_evidence")
        need(isinstance(evidence,dict),
             "Fallback requires original observed provider retry journal")
        AttemptEvidence.verify_saved(folder,slots,evidence)
    need(sorted(x.name for x in folder.glob("slide[0-9]*.wav"))
         ==sorted(require_names),"TTS batch WAV coverage incomplete")
    seconds=[_duration(folder/name) for name in require_names]
    return manifest,result,seconds

def produce_element_audio(*,source:Path,slides:Path,script:Path,
                          local_work_root:Path,
                          synthesizer:Callable|None=None)->dict:
    """One verified technical-only batch, preserving all existing source outputs.

    The normal runner may call this after slides/narration/script QA. For
    insufficient source evidence, exits BEFORE any billable Gemini call.
    """
    source,slides,script=(Path(x).resolve() for x in (source,slides,script))
    base=source.parent
    need(slides==base/"slides.pdf" and script==base/"script.txt"
         and source==base/"source.pdf",
         "Only canonical source-adjacent lecture files are accepted")
    outputs=(base/"element_narration_plan.json",
             base/"element_wav",base/"element_tts_manifest.json")
    need(all(not path.exists() and not path.is_symlink() for path in outputs),
         "Element stage already exists; never overwrite or silently resume")
    evidence=inspect_text_only(source=source,slides=slides,script=script)
    fragments=[entry["elements"][0]["spoken_text"] for entry in evidence["elements"]]
    # Preflight script encoding and exact TTS parser roundtrip before billing.
    tts_script="".join(f"**Slide {n} [30s]:\n\n{text}\n\n"
                       for n,text in enumerate(fragments,1))
    need([x for _,x in blocks(tts_script)]==fragments,
         "Narration changed while preparing exact element-TTS batch")
    root=Path(local_work_root).expanduser().resolve()
    need(root.is_dir() and not root.is_symlink()
         and not root.is_relative_to(base),
         "Local element-TTS staging must be outside the source directory")
    work=Path(tempfile.mkdtemp(prefix="microgen_element_tts_",dir=root))
    created=[]
    try:
        (work/"script.txt").write_text(tts_script,encoding="utf-8")
        if synthesizer is None:
            from .runner import load_microvid_env
            from .tts_billing_guard import require_tts_cost_authorization
            from .tts import synthesize_folder
            require_tts_cost_authorization("gemini",routine_gemini=True)
            load_microvid_env()
            synthesizer=synthesize_folder
        synthesizer(work,DEFAULT["provider"],DEFAULT["model"],DEFAULT["voice"])
        manifest,effective,timings=_check_producer(work,fragments)
        final=plan_for_audio(
            evidence,timings,provider=effective["provider"],
            model=effective["model"],voice=effective["voice"])
        final_path=work/"final_plan.json"
        _write_new(final_path,final)
        # Ensure source-grounded page/geometry and full slide coverage
        # without creating another video or paying for TTS.
        need(all(sha(original)==evidence[key] for original,key in (
            (source,"source_sha256"),(slides,"slides_sha256"),
            (script,"script_sha256"))),
            "Original lecture source/slide/narration changed during TTS")
        need(all(not path.exists() and not path.is_symlink()
                 for path in outputs),
             "Concurrent TTS writer created an output; refuse overwrite")
        # Commit immutable generated evidence. Roll back exclusively created
        # paths on failure, never touch pre-existing inputs or historical WAVs.
        audio_dir=outputs[1]
        audio_dir.mkdir()
        created.append(audio_dir)
        for n,entry in enumerate(evidence["elements"],1):
            original=work/f"slide{n}.wav"
            target=audio_dir/entry["elements"][0]["wav"]
            with original.open("rb") as src,target.open("xb") as dst:
                shutil.copyfileobj(src,dst)
            need(sha(original)==sha(target),"TTS WAV changed during copy")
        # Recheck the entire planned lecture and PDF element geometry using
        # the actual, copied per-element original PCM WAVs.
        source_bound_plan(
            source=source,slides=slides,plan=final_path,audio=audio_dir)
        audit=audio_dir/"_producer"
        audit.mkdir()
        for name in ("script.txt","tts_input_manifest.json"):
            with (work/name).open("rb") as src,(audit/name).open("xb") as dst:
                shutil.copyfileobj(src,dst)
        if effective["fallback_used"]:
            original_journal=work/".tts_attempt_evidence"
            need(original_journal.is_dir() and not original_journal.is_symlink(),
                 "Missing immutable observed TTS attempt journal")
            shutil.copytree(original_journal,audit/".tts_attempt_evidence")
            AttemptEvidence.verify_saved(
                audit,list(enumerate(fragments,1)),
                manifest["attempt_evidence"])
        provenance={
            "schema_version":1,
            "status":"verified_source_bound_element_audio",
            "source_sha256":evidence["source_sha256"],
            "slides_sha256":evidence["slides_sha256"],
            "authored_plan_sha256":sha(final_path),
            "source_script_sha256":evidence["script_sha256"],
            "provider":effective["provider"],
            "model":effective["model"],
            "voice":effective["voice"],
            "all_elements_one_voice":True,
            "effective_identity":effective,
            "producer_manifest_sha256":sha(audit/"tts_input_manifest.json"),
            "producer_script_sha256":sha(audit/"script.txt"),
            "human_review_required":False,
            "conditional_cloud_fallback_verified":(
                effective["provider"]=="chirp3" and
                effective["fallback_used"]),
            "gemini_primary_attempts":(3 if effective["provider"]=="chirp3" else 0),
            "gemini_secondary_attempts":(3 if effective["provider"]=="chirp3" else 0),
            "elements":[{
                "wav":entry["elements"][0]["wav"],
                "sha256":sha(audio_dir/entry["elements"][0]["wav"]),
                "spoken_text_sha256":_digest(text.encode("utf-8")),
                "provider":effective["provider"],
                "model":effective["model"],
                "voice":effective["voice"],
            } for entry,text in zip(evidence["elements"],fragments)]
        }
        # Only original observed evidence, not counters above, can authorize
        # Cloud TTS. The producer's saved retry journal is mandatory on fallback.
        _write_new(outputs[0],final)
        created.append(outputs[0])
        _write_new(outputs[2],provenance)
        created.append(outputs[2])
        from .sourcebound_production_video import verify_element_tts_batch
        verify_element_tts_batch(
            source=source,slides=slides,authored=outputs[0],audio=audio_dir)
        shutil.rmtree(work)
        return {"status":"ELEMENT_AUDIO_READY_FOR_AUTOMATIC_VIDEO_STAGE",
                "elements":len(fragments),"parts":len(final["parts"]),
                "effective_model":effective["model"],
                "human_review_required":False,
                "existing_assets_overwritten":False}
    except BaseException:
        for output in reversed(created):
            if output.is_dir():shutil.rmtree(output,ignore_errors=True)
            else:output.unlink(missing_ok=True)
        # Keep local .tts_candidate/ledger to safely investigate failed API
        # attempts and prevent unproven repeated billing, never on source root.
        raise
