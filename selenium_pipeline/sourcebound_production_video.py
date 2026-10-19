"""Fail-closed bridge: source-bound, decoded-pixel VERIFIED element video -> production.

Only consumes a COMPLETE original lecture with real per-element WAV and
source-bound element anchors. No human academic permission is required for
technical stage progression. This bridge does NOT synthesize element WAVs,
invent source anchors, use static slide video or publish to YouTube.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

from .element_highlight_workflow import verify_rendered, read
from .encoded_highlight_pixels import verify_encoded_highlight_pixels
from .production_video_contract import verify_series


class ProductionRenderError(ValueError):
    """A source, element, media, preservation or technical QA gate failed."""


def require(ok: bool, explanation: str) -> None:
    if not ok:
        raise ProductionRenderError(explanation)


def digest(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"Missing original file: {path}")
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def write_new(path: Path, data: dict) -> None:
    with path.open("x",encoding="utf-8") as handle:
        json.dump(data,handle,indent=2,ensure_ascii=False)
        handle.write("\n")


def _copy_new(source: Path, target: Path) -> str:
    before=digest(source)
    target.parent.mkdir(parents=True,exist_ok=True)
    require(not target.exists() and not target.is_symlink(),
            f"Refuse overwrite: {target}")
    with source.open("rb") as src, target.open("xb") as out:
        shutil.copyfileobj(src,out,1024*1024)
    require(digest(source)==before and digest(target)==before,
            f"Copy changed source or target: {target}")
    return before


def accept_candidate(*,source: Path,slides: Path,authored: Path,audio: Path,
                     review_root: Path,candidate: Path) -> dict:
    """Produce a NEW self-auditable candidate containing accepted *technical* receipts.

    Review-only cannot turn into an accepted series by renaming receipt status:
    this step recomputes decoded MP4 pixel correctness from original frames
    *before and after copy*, validates every source anchor/WAV, and verifies
    the standard production_video_contract using actual FFmpeg.
    """
    paths=tuple(Path(x).absolute() for x in (source,slides,authored,audio,review_root))
    require(not any(p.is_symlink() for p in paths),"Symlinked source/evidence forbidden")
    source,slides,authored,audio,review=(p.resolve() for p in paths)
    root=Path(candidate).absolute()
    require(not root.exists() and not root.is_symlink()
            and root.parent.is_dir() and not root.parent.is_symlink(),
            "Production candidate must be a fresh isolated directory")
    root=root.resolve()
    require(all(not root.is_relative_to(p) and not p.is_relative_to(root)
                for p in (source.parent,audio,review)),
            "Production candidate must not overlap original lecture or review")
    # Fail before expensive FFmpeg, file-copy or any candidate output.
    # A review-only image/panel anchor is not an independently source-proven
    # figure: PR140-146 candidate receipts cannot confer TTS/video approval.
    from .figure_narration_promotion import (
        FigureNarrationPromotionBlocked, check_production_anchor_provenance)
    authored_sha_before=digest(authored)
    try:
        check_production_anchor_provenance(read(authored))
    except FigureNarrationPromotionBlocked as exc:
        raise ProductionRenderError(str(exc)) from exc
    proof=verify_rendered(
        source=source,slides=slides,authored=authored,audio=audio,
        staged=review/"staged",rendered=review/"rendered",
        output=None,recheck_pixels=True)
    require(proof["status"]=="COMPLETE_ELEMENT_HIGHLIGHT_TECHNICAL_REVIEW_ONLY"
            and proof["production_approved"] is False
            and proof["student_published"] is False,
            "Only fully verified original review media can be converted")
    saved=read(review/"highlight_technical_review.json")
    require(saved==proof,"Frozen review receipt differs from fresh decoded verification")
    plan=read(authored)
    require(digest(authored)==authored_sha_before,
            "Authored source-bound plan changed during production verification")
    try:
        check_production_anchor_provenance(plan)
    except FigureNarrationPromotionBlocked as exc:
        raise ProductionRenderError(str(exc)) from exc
    require(len(plan["parts"])==len(proof["parts"]),"Missing or unordered parts")
    original_hashes={str(path):digest(path) for path in
                     (source,slides,authored,
                      *(audio/element["wav"]
                        for part in plan["parts"]
                        for slide in part["slides"]
                        for element in slide["elements"]))}
    root.mkdir()
    try:
        _copy_new(source,root/"source.pdf")
        _copy_new(slides,root/"slides.pdf")
        _copy_new(authored,root/"element_narration_plan.json")
        machine_script=(source.parent/"script.txt")
        if plan.get("status")=="machine_verified_exact_text_element_narration":
            _copy_new(machine_script,root/"script.txt")
        _copy_new(review/"highlight_technical_review.json",
                  root/"source_review_receipt.json")
        checks=[]
        for index,part in enumerate(plan["parts"],1):
            ident=f"part_{index:02d}"
            require(part["part_id"]==ident,"Part plan noncontiguous")
            origin=review/"rendered"/ident
            created=root/ident
            created.mkdir()
            mp4=created/(ident+".mp4")
            _copy_new(origin/(ident+"_review.mp4"),mp4)
            wav=created/"narration.wav"
            _copy_new(origin/"narration.wav",wav)
            for name in ("encoded_pixel_qa.json","element_geometry.json",
                         "narration_timeline.json","review_receipt.json",
                         "clean_slides.pdf"):
                _copy_new(origin/name,created/name)
            # Never dereference untrusted symlinked reference frames.
            require(all(path.is_file() and not path.is_symlink()
                        for path in (origin/"scratch_frames").rglob("*")),
                    "Reference image tree has non-file entries")
            shutil.copytree(origin/"scratch_frames",created/"scratch_frames")
            from .element_highlight_workflow import digest as sha
            require(digest(origin/"encoded_pixel_qa.json")==
                    digest(created/"encoded_pixel_qa.json"),
                    "Copied pixel QA differs from original")
            timeline=read(created/"narration_timeline.json")
            geometry=read(created/"element_geometry.json")
            decoded=verify_encoded_highlight_pixels(
                mp4=mp4,frames_dir=created/"scratch_frames",
                geometry=geometry,timeline=timeline)
            qa=read(created/"encoded_pixel_qa.json")
            require(decoded["count_events"]==qa["count_events"]
                    and decoded["time_window_samples_checked"]==qa["time_window_samples_checked"]
                    and decoded["pause_samples_checked"]==qa["pause_samples_checked"],
                    "Newly copied MP4 fails independent decoded highlight tests")
            events=[]
            for row in timeline["events"]:
                ids=row["element_ids"]
                require(isinstance(ids,list) and len(ids)==1,
                        "Single source spoken element required per highlight event")
                events.append({
                    "slide_id":row["slide_id"],"target_id":ids[0],
                    "start_ms":row["start_ms"],"end_ms":row["end_ms"],
                })
            audio_hash=digest(wav)
            cues={"status":"approved_audio_timed_visual_cues",
                  "audio_sha256":audio_hash,"events":events}
            alignment={"status":"verified_final_audio_alignment",
                       "audio_sha256":audio_hash,
                       "duration_ms":timeline["duration_ms"],
                       "events":events}
            write_new(created/"visual_cues.json",cues)
            write_new(created/"narration_alignment.json",alignment)
            prior=read(created/"review_receipt.json")
            # 'unverified=[]' here refers only to this standard *technical
            # receipt* and never to independent academic or listening approval.
            receipt={
                "schema_version":1,"part_id":ident,
                "status":"accepted_synchronized_part",
                "renderer":"audio_timed_highlight_renderer",
                "acceptance_scope":"technical_only",
                "human_academic_review_verified":False,
                "student_published":False,
                "unverified":[],
                "mp4_sha256":digest(mp4),"audio_sha256":audio_hash,
                "visual_cues_sha256":digest(created/"visual_cues.json"),
                "alignment_sha256":digest(created/"narration_alignment.json"),
                "duration_s":prior["encoded_mp4_seconds"],
                "encoded_transition_qa":prior["encoded_transition_qa"],
                "decoded_pixel_qa_sha256":digest(created/"encoded_pixel_qa.json"),
                "element_geometry_sha256":digest(created/"element_geometry.json"),
                "narration_timeline_sha256":digest(created/"narration_timeline.json"),
                "review_receipt_sha256":digest(created/"review_receipt.json"),
                "decoded_pixel_reverification":True,
            }
            write_new(created/"part_receipt.json",receipt)
            checks.append({"part_id":ident,
                           "receipt_sha256":digest(created/"part_receipt.json")})
        require(all(digest(p)==value for p,value in
                    ((Path(name),value) for name,value in original_hashes.items())),
                "Original lecture source/slide/plan changed during conversion")
        manifest={
            "schema_version":1,"status":"accepted_synchronized_series",
            "source_sha256":digest(root/"source.pdf"),
            "slides_sha256":digest(root/"slides.pdf"),
            "authored_plan_sha256":digest(root/"element_narration_plan.json"),
            "original_narration_script_sha256":(
                digest(root/"script.txt")
                if plan.get("status")=="machine_verified_exact_text_element_narration"
                else None),
            "source_review_sha256":digest(root/"source_review_receipt.json"),
            "origin":"independent_fresh_decoded_pixel_reverification",
            "acceptance_scope":"technical_only",
            "human_academic_review_verified":False,
            "student_published":False,
            "parts":checks,
        }
        write_new(root/"lecture_completion.json",manifest)
        outcome=verify_production_candidate(root)
        return {"status":"ACCEPTED_TECHNICAL_HIGHLIGHT_PRODUCTION_CANDIDATE",
                "candidate":str(root),"parts":outcome["parts"],
                "human_review_required":False,"student_published":False}
    except BaseException:
        shutil.rmtree(root,ignore_errors=True)
        raise


def verify_production_candidate(candidate: Path) -> dict:
    """Read-only full QA, including *fresh* actual MP4 pixel decoding."""
    root=Path(candidate).resolve()
    report=verify_series(root)
    manifest=read(root/"lecture_completion.json")
    require(report["status"]=="accepted_synchronized_series"
            and manifest.get("origin")=="independent_fresh_decoded_pixel_reverification"
            and manifest.get("acceptance_scope")=="technical_only"
            and manifest.get("student_published") is False,
            "No source-grounded production technical receipt")
    require(manifest.get("slides_sha256")==digest(root/"slides.pdf")
            and manifest.get("authored_plan_sha256")
                ==digest(root/"element_narration_plan.json")
            and manifest.get("source_review_sha256")
                ==digest(root/"source_review_receipt.json"),
            "Original slide, source plan or review evidence changed")
    authored=read(root/"element_narration_plan.json")
    if authored.get("status")=="machine_verified_exact_text_element_narration":
        require(manifest.get("original_narration_script_sha256")
                ==digest(root/"script.txt"),
                "Machine-anchored original script is missing or changed")
        from .automatic_element_narration import verify_automatic_source_mapping
        verify_automatic_source_mapping(
            source=root/"source.pdf",slides=root/"slides.pdf",plan=authored)
    for part in report["parts"]:
        directory=root/part["part_id"]
        receipt=read(directory/"part_receipt.json")
        for label,name in (
            ("decoded_pixel_qa_sha256","encoded_pixel_qa.json"),
            ("element_geometry_sha256","element_geometry.json"),
            ("narration_timeline_sha256","narration_timeline.json"),
            ("review_receipt_sha256","review_receipt.json"),
        ):
            require(receipt.get(label)==digest(directory/name),
                    "Production source-bound pixel evidence mutated")
        rebuilt=verify_encoded_highlight_pixels(
            mp4=directory/(part["part_id"]+".mp4"),
            frames_dir=directory/"scratch_frames",
            geometry=read(directory/"element_geometry.json"),
            timeline=read(directory/"narration_timeline.json"))
        stored=read(directory/"encoded_pixel_qa.json")
        require(rebuilt["count_events"]==stored["count_events"]
                and rebuilt["time_window_samples_checked"]
                    ==stored["time_window_samples_checked"]
                and rebuilt["pause_samples_checked"]
                    ==stored["pause_samples_checked"],
                "Production MP4 encoded-pixel evidence cannot be freshly reproduced")
    return report


def install_new_production_parts(*,candidate: Path,subchapter: Path) -> dict:
    """Publish ONLY new verified multipart files; all existing bytes protected.

    A failed copy or verification rolls back only newly created files/folders.
    Never deletes source.pdf, slides.pdf or legacy slides.mp4.
    """
    candidate=Path(candidate).resolve()
    dest=Path(subchapter).resolve()
    require(dest.is_dir() and dest/"source.pdf" != candidate/"source.pdf"
            and not candidate.is_relative_to(dest)
            and not dest.is_relative_to(candidate),
            "Install source folder and candidate must be separate")
    technical=verify_production_candidate(candidate)
    require(digest(dest/"source.pdf")==digest(candidate/"source.pdf"),
            "Cannot install candidate for different source.pdf")
    require(digest(dest/"slides.pdf")==digest(candidate/"slides.pdf"),
            "Cannot install candidate for different slides.pdf")
    original_plan=dest/"element_narration_plan.json"
    original_review=dest/"source_review_receipt.json"
    for destination_file,source_file in (
        (original_plan,candidate/"element_narration_plan.json"),
        (original_review,candidate/"source_review_receipt.json"),
    ):
        require(not destination_file.is_symlink()
                and (not destination_file.exists()
                     or digest(destination_file)==digest(source_file)),
                "Original subchapter contains conflicting anchored provenance")
    targets=[dest/part["part_id"] for part in technical["parts"]]
    targets.append(dest/"lecture_completion.json")
    require(all(not path.exists() and not path.is_symlink() for path in targets),
            "Existing part/completion receipt must never be overwritten")
    installed=[]
    try:
        for part in technical["parts"]:
            name=part["part_id"]
            source=candidate/name
            target=dest/name
            require(not target.exists(),"Part race: refusing overwrite")
            # Claim only a freshly created directory. If copy fails midway,
            # the exclusively owned partially filled directory is rolled back.
            target.mkdir()
            installed.append(target)
            for original in source.rglob("*"):
                require(not original.is_symlink(),
                        "Candidate has symlinked files; installation denied")
                relative=original.relative_to(source)
                to=target/relative
                if original.is_dir():
                    to.mkdir(parents=True,exist_ok=True)
                elif original.is_file():
                    _copy_new(original,to)
                else:
                    raise ProductionRenderError("Candidate contains non-file evidence")
            require(digest(source/"part_receipt.json")==digest(target/"part_receipt.json"),
                    "Installed part receipt changed while copying")
        # Retain the precise source element plan and original review evidence
        # beside the accepted MP4. If already present, their SHA MUST match.
        for dest_name,origin in (
            (original_plan,candidate/"element_narration_plan.json"),
            (original_review,candidate/"source_review_receipt.json"),
        ):
            if not dest_name.exists():
                _copy_new(origin,dest_name)
                installed.append(dest_name)
        copied=dest/"lecture_completion.json"
        _copy_new(candidate/"lecture_completion.json",copied)
        installed.append(copied)
        verified=verify_series(dest)
        require(verified["status"]=="accepted_synchronized_series",
                "Installed lecture completion failed source-bound acceptance")
        for checked in verified["parts"]:
            part=dest/checked["part_id"]
            reaudited=verify_encoded_highlight_pixels(
                mp4=part/(checked["part_id"]+".mp4"),
                frames_dir=part/"scratch_frames",
                geometry=read(part/"element_geometry.json"),
                timeline=read(part/"narration_timeline.json"))
            original_qa=read(part/"encoded_pixel_qa.json")
            require(reaudited["count_events"]==original_qa["count_events"]
                    and reaudited["time_window_samples_checked"]
                        ==original_qa["time_window_samples_checked"]
                    and reaudited["pause_samples_checked"]
                        ==original_qa["pause_samples_checked"],
                    "Installed MP4 fails fresh encoded pixel verification")
        return {"status":"INSTALLED_TECHNICALLY_ACCEPTED_MULTIPART_VIDEO",
                "subchapter":str(dest),"part_count":len(verified["parts"]),
                "human_review_required":False,"student_published":False}
    except BaseException:
        for path in reversed(installed):
            if path.is_dir():
                shutil.rmtree(path,ignore_errors=True)
            elif path.is_file():
                path.unlink()
        raise


def verify_element_tts_batch(*,source: Path,slides: Path,
                             authored: Path,audio: Path) -> dict:
    """Verify original element-WAV provenance without inventing ASR/human review.

    A slideN.wav cannot be silently subdivided into missing words/elements.
    The separate upstream element TTS producer must supply one immutable
    manifest, one SHA-bound WAV and the exact original spoken text per element.
    Voice is a declared, manifest-bound technical identity; this does not
    falsely claim independently attested provider origin or human listening.
    """
    parent=source.parent
    attested=parent/"element_tts_manifest.json"
    require(attested.is_file() and not attested.is_symlink(),
            "Missing required per-element TTS provenance manifest")
    record=read(attested)
    plan=read(authored)
    require(record.get("schema_version")==1 and
            record.get("status")=="verified_source_bound_element_audio"
            and record.get("source_sha256")==digest(source)
            and record.get("slides_sha256")==digest(slides)
            and record.get("authored_plan_sha256")==digest(authored)
            and record.get("all_elements_one_voice") is True,
            "Element audio provenance is stale, incomplete or mixed")
    provider=record.get("provider")
    model=record.get("model")
    voice=record.get("voice")
    identity=(provider,model,voice)
    allowed={
        ("gemini","gemini-3.8-flash-lite-tts","Kore"),
        ("gemini","gemini-3.8-flash-tts","Kore"),
        ("chirp3","chirp3-hd","en-US-Chirp3-HD-Corey"),
    }
    require(identity in allowed and
            isinstance(plan.get("voice_id"),str) and
            model in plan["voice_id"] and voice in plan["voice_id"],
            "Element voice/model diverges from approved TTS family or plan")
    if provider=="chirp3":
        require(record.get("conditional_cloud_fallback_verified") is True
                and record.get("gemini_primary_attempts",0)>=3
                and record.get("gemini_secondary_attempts",0)>=3,
                "Cloud element TTS requires exhausted Gemini retries")
    upstream=audio/"_producer"
    model_manifest=upstream/"tts_input_manifest.json"
    batch_script=upstream/"script.txt"
    require(record.get("producer_manifest_sha256")==digest(model_manifest)
            and record.get("producer_script_sha256")==digest(batch_script),
            "Original element TTS batch identity or transcript changed")
    from .tts_effective_identity import verify_effective_identity
    from .runner import blocks
    slots=blocks(batch_script.read_text(encoding="utf-8"))
    effective=verify_effective_identity(read(model_manifest),slots)
    require((effective["provider"],effective["model"],effective["voice"])
            ==identity,
            "Claimed element voice differs from actual producer batch receipt")
    if effective["fallback_used"]:
        from .tts_attempt_evidence import AttemptEvidence
        AttemptEvidence.verify_saved(upstream,slots,
                                    read(model_manifest)["attempt_evidence"])
    elif provider=="chirp3":
        raise ProductionRenderError("Cloud TTS without observed fallback is prohibited")
    expected=[element for part in plan["parts"] for slide in part["slides"]
              for element in slide["elements"]]
    chunks=record.get("elements")
    require(isinstance(chunks,list) and len(chunks)==len(expected),
            "Element TTS provenance does not cover all spoken elements")
    require([text for _,text in slots] == [e["spoken_text"] for e in expected],
            "Actual TTS batch differs from exact source-bound narrated words")
    for claimed,entry in zip(chunks,expected):
        require(isinstance(claimed,dict)
                and claimed.get("wav")==entry["wav"]
                and claimed.get("sha256")==digest(audio/entry["wav"])
                and claimed.get("spoken_text_sha256")==hashlib.sha256(
                    entry["spoken_text"].encode("utf-8")).hexdigest()
                and tuple(claimed.get(key) for key in
                          ("provider","model","voice"))==identity,
                "Element WAV/text/model hash or uniform voice mismatch")
    return {"provider":provider,"model":model,"voice":voice,
            "element_count":len(expected),
            "manifest_sha256":digest(attested),
            "human_review_required":False}


def render_and_install_prepared(*,source: Path,slides: Path,
                                authored: Path,audio: Path,
                                local_work_root: Path) -> dict:
    """Unattended final video stage ONLY after genuine element-level inputs exist.

    The regular TTS stage currently produces per-SLIDE WAVs, not separate
    element WAVs. No guessing/splicing/ASR is allowed. The required authored
    source-anchored plan and per-element WAVs must be separately generated.
    A new local staging directory preserves failure evidence; on success
    removes only its own freshly created workspace.
    """
    import tempfile
    source,slides,authored,audio=(Path(x).resolve()
                                  for x in (source,slides,authored,audio))
    subchapter=source.parent
    require(authored == subchapter/"element_narration_plan.json"
            and audio == subchapter/"element_wav"
            and slides == subchapter/"slides.pdf",
            "Normal automatic stage requires canonical source-bound element inputs")
    require(source.is_file() and slides.is_file() and authored.is_file()
            and audio.is_dir(),"No complete per-element input plan/WAVs; "
            "static-slide renderer is prohibited")
    verify_element_tts_batch(
        source=source,slides=slides,authored=authored,audio=audio)
    local=Path(local_work_root).expanduser().resolve()
    require(local.is_dir() and not local.is_relative_to(subchapter),
            "Temporary production staging must be outside textbook source tree")
    scratch=Path(tempfile.mkdtemp(prefix="microgen_highlight_",dir=local))
    review_dir=scratch/"review"
    candidate_dir=scratch/"candidate"
    try:
        from .element_highlight_workflow import review
        review(source=source,slides=slides,authored=authored,
               audio=audio,output_root=review_dir)
        accept_candidate(source=source,slides=slides,authored=authored,
                         audio=audio,review_root=review_dir,candidate=candidate_dir)
        # TTS provenance cannot mutate after the slow FFmpeg render and
        # before installing the candidate beside the original source.
        verify_element_tts_batch(
            source=source,slides=slides,authored=authored,audio=audio)
        result=install_new_production_parts(
            candidate=candidate_dir,subchapter=subchapter)
        try:
            shutil.rmtree(scratch)
        except OSError:
            print("[microgen] accepted video; local staging cleanup deferred")
        return result
    except Exception:
        # Preserve local diagnostic MP4/WAV/receipt materials after failure.
        # Never alter the original lecture, regardless of error.
        raise


def main(argv=None)->int:
    parser=argparse.ArgumentParser(description="MicroGen source-bound video production bridge")
    parser.add_argument("command",choices=("accept","verify","install"))
    for name in ("source","slides","authored","audio","review-root","candidate","subchapter"):
        parser.add_argument("--"+name,type=Path)
    args=parser.parse_args(argv)
    if args.command=="accept":
        required=("source","slides","authored","audio","review_root","candidate")
        require(all(getattr(args,k) is not None for k in required),
                "Accept requires source, slides, authored, audio, review-root, candidate")
        result=accept_candidate(source=args.source,slides=args.slides,
            authored=args.authored,audio=args.audio,
            review_root=args.review_root,candidate=args.candidate)
    elif args.command=="verify":
        require(args.candidate is not None,"Verify requires candidate")
        result=verify_production_candidate(args.candidate)
    else:
        require(args.candidate is not None and args.subchapter is not None,
                "Install requires candidate and subchapter")
        result=install_new_production_parts(
            candidate=args.candidate,subchapter=args.subchapter)
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
