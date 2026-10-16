"""Fail-closed technical review audit for a complete element-level lesson.

Checks only demonstrable structural, audio, source, frame and duration facts.
NEVER treats narration script or image hashes as proof of academic validity,
correct spoken words, source semantics, or human review.
"""
from __future__ import annotations
import argparse,hashlib,json,wave
from pathlib import Path


def require(ok,message):
    if not ok: raise ValueError(message)


def H(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""):h.update(b)
    return h.hexdigest()


def load(p):return json.loads(p.read_text(encoding="utf8"))


def check_independent_asr(plan: dict, audio: Path, directory: Path | None,
                          *, required: bool = False,
                          authored_sha256: str | None = None) -> dict:
    """ASR evidence never certifies spoken words; incomplete/mismatched clips block."""
    events=[el for p in plan["parts"] for sl in p["slides"] for el in sl["elements"]]
    if directory is None:
        if required:
            raise ValueError("Independent ASR evidence missing")
        return {"status":"not_run","checked":0,"total":len(events),
                "matched":0,"flagged":0,"human_certified":False}
    directory=Path(directory).resolve()
    job=load(directory/"asr_job.json")
    require(authored_sha256 is not None and
            job.get("plan_sha256")==authored_sha256,
            "ASR job plan SHA mismatch")
    require(job["model"] in ("gemini-3.1-flash-lite","gemini-3.5-flash",
                              "gemini-flash-web-ui")
            and job["source_model"]=="gemini-3.8-flash-lite-tts",
            "ASR model not distinct from TTS")
    require(len(job["clips"])==len(events)
            and job["clips"]==[el["wav"] for el in events],
            "ASR job covers a different scene")
    checked=0
    matched=0
    flagged=0
    for event in events:
        row=directory/(event["wav"]+".asr.json")
        if not row.is_file():
            continue
        data=load(row)
        wav=audio/event["wav"]
        require(data["wav"]==event["wav"]
                and data["wav_sha256"]==H(wav)
                and data["reference_sha256"]==
                    hashlib.sha256(event["spoken_text"].encode("utf8")).hexdigest(),
                "Stale independent ASR evidence")
        require(data["asr_model"]==job["model"]
                and data["transcript_sha256"]==
                    hashlib.sha256(data["transcript"].encode("utf8")).hexdigest(),
                "Tampered or mismatched ASR model transcript")
        if job["model"]=="gemini-flash-web-ui":
            require(data.get("backend")=="selenium_flash_browser"
                    and data.get("exact_web_model_version_unverified") is True,
                    "Cannot accept unauthenticated browser-mode ASR provenance")
        checked+=1
        if data["metrics"]["machine_asr_consistent"]:
            matched+=1
        else:
            flagged+=1
    complete=checked==len(events)
    if required and (not complete or flagged):
        raise ValueError("Independent ASR incomplete or mismatched; block acceptance")
    return {"status":("machine_consistent_not_certified" if complete and not flagged
               else "partial_or_flagged_requires_review"),
            "checked":checked,"total":len(events),
            "matched":matched,"flagged":flagged,
            "human_certified":False}



def check_tts_quality(plan: dict, audio: Path, quality_report: Path | None,
                      *, required: bool = False,
                      authored_sha256: str | None = None,
                      authored_path: Path | None = None,
                      asr_dir: Path | None = None) -> dict:
    """Verify a complete immutable screening report without approving speech."""
    elements = [el for part in plan["parts"] for slide in part["slides"]
                for el in slide["elements"]]
    if quality_report is None:
        if required:
            raise ValueError("Three-layer TTS quality evidence missing")
        return {"status": "not_run", "checked": 0, "total": len(elements),
                "machine_complete": False, "human_certified": False}
    quality_report = Path(quality_report).resolve()
    report = load(quality_report)
    require(report.get("schema_version") == 1
            and report.get("status") == "QUALITY_SCREEN_REVIEW_ONLY"
            and report.get("plan_sha256") == authored_sha256
            and report.get("total_clips") == len(elements),
            "Stale or invalid TTS quality report")
    rows = report.get("clips")
    require(isinstance(rows, list) and len(rows) == len(elements),
            "TTS quality coverage incomplete")
    require(authored_path is not None and
            H(Path(authored_path).resolve()) == authored_sha256,
            "Audited TTS quality plan path or hash missing")
    # Re-evaluate every acoustic sample and ASR/math flag from original
    # inputs. A forged JSON status cannot authorize machine QA.
    from .tts_quality_gate import screen
    regenerated = screen(plan=Path(authored_path), audio=audio,
                         asr_dir=asr_dir, output=None)
    require(regenerated == report,
            "TTS quality evidence differs from independent recomputation")
    flagged = 0
    for el, row in zip(elements, rows):
        wav = audio / el["wav"]
        require(row.get("wav") == el["wav"]
                and row.get("wav_sha256") == H(wav)
                and row.get("reference_sha256") ==
                    hashlib.sha256(el["spoken_text"].encode("utf8")).hexdigest(),
                "TTS quality report mismatched audio or script")
        require(row.get("human_listening_approved") is False,
                "Machine quality report cannot certify human listening")
        if row.get("quality_state") != "machine_screen_consistent_not_certified":
            flagged += 1
    complete = flagged == 0 and report.get("all_machine_checks_passed") is True
    require(report.get("production_approved") is False
            and report.get("human_listening_complete") is False,
            "Review-only quality report claims unauthorized approval")
    if required and not complete:
        raise ValueError("TTS quality screen incomplete/flagged; block acceptance")
    return {"status": ("machine_screen_consistent_not_certified" if complete
                       else "partial_or_flagged_requires_listening"),
            "checked": len(rows), "total": len(elements),
            "flagged": flagged, "machine_complete": complete,
            "human_certified": False}


def verify_layout_only_rebind(*,current:dict, source:Path, slides:Path,
            audio:Path, old_slides:Path | None,
            previous_voice_plan:Path | None, rebind_receipt:Path | None,
            figure_resize_receipt:Path | None)->dict:
    required=(
        "layout_only_rebind_from_voice_plan_sha256" in current or
        any(x is not None for x in
            (old_slides,previous_voice_plan,rebind_receipt,figure_resize_receipt))
    )
    if not required:
        return {"status":"not_required"}
    require(all(x is not None for x in
        (old_slides,previous_voice_plan,rebind_receipt,figure_resize_receipt)),
        "Layout-only narration rebind requires all four origin evidence files")
    old_slides,previous_voice_plan,rebind_receipt,figure_resize_receipt=(
        Path(x).resolve() for x in
        (old_slides,previous_voice_plan,rebind_receipt,figure_resize_receipt))
    old=load(previous_voice_plan)
    reb=load(rebind_receipt)
    resized=load(figure_resize_receipt)
    rebuilt=dict(old)
    rebuilt["slides_sha256"]=H(slides)
    rebuilt["layout_only_rebind_from_voice_plan_sha256"]=H(previous_voice_plan)
    rebuilt["layout_only_rebind_receipt_sha256"]=H(figure_resize_receipt)
    require(rebuilt==current,
        "Rebound narration plan modifies content beyond the approved PDF SHA and provenance fields")
    require(reb["status"]=="REVIEW_ONLY_LAYOUT_REBIND_SAME_NARRATION_NOT_CERTIFIED"
            and reb["old_voice_bound_plan_sha256"]==H(previous_voice_plan)
            and reb["old_slides_sha256"]==H(old_slides)
            and reb["new_slides_sha256"]==H(slides)
            and reb["source_sha256"]==H(source)
            and reb["figure_resize_receipt_sha256"]==H(figure_resize_receipt)
            and reb["tts_synthesis_receipt_sha256"]==H(audio/"tts_synthesis_receipt.json")
            and reb["all_original_wav_bytes_and_text_hashes_verified"] is True
            and reb["academic_approval"] is False
            and reb["production_approved"] is False,
            "Rebind provenance invalid, stale or improperly approved")
    require(resized["status"]=="REVIEW_ONLY_ISOLATED_FIGURE_RESIZE"
            and resized["source_slides_sha256"]==H(old_slides)
            and resized["derived_slides_sha256"]==H(slides)
            and resized["production_approved"] is False
            and reb["changed_slide_numbers"]==
                  resized["changed_rendered_slide_numbers"]==
                      [resized["target_slide"]]
            and len(reb["changed_element_anchors"])>=1,
            "Changed-slide or element-anchor correction not independently bounded")
    return {"status":"review_only_layout_rebind_evidence_pass",
            "changed_original_slide_numbers":reb["changed_slide_numbers"],
            "changed_highlight_anchor_count":len(reb["changed_element_anchors"]),
            "narration_unchanged_sha_verified":True,
            "independent_speech_complete":False,
            "production_approved":False}


def audit(*,source,slides,authored,audio,staged,rendered,report,
          asr_dir=None,require_asr=False,old_slides=None,
          previous_voice_plan=None,rebind_receipt=None,figure_resize_receipt=None,
          quality_report=None,require_quality=False):
    source,slides,authored,audio,staged,rendered,report=map(
       lambda x:Path(x).resolve(),(source,slides,authored,audio,staged,rendered,report))
    require(not report.exists() and report.parent.is_dir(),
            "Review report output must be new")
    original=load(authored)
    provenance=load(staged/"element_stage_receipt.json")
    series=load(rendered/"series_review_receipt.json")
    job=load(audio/"tts_synthesis_receipt.json")
    require(original["source_sha256"]==H(source)==series["source_sha256"]
            ==provenance["source_sha256"],"Source drift")
    require(original["slides_sha256"]==H(slides)
            ==provenance["slides_sha256"],"Slide PDF drift")
    require(job["status"]=="real_gemini_tts_generated_review_only_word_fidelity_unverified"
            and job["same_declared_voice_all_segments"] is True
            and job["audible_word_fidelity_verified"] is False,
            "TTS has no immutable unapproved receipt")
    require(provenance["complete_lecture_coverage"] is True
            and provenance["audio_text_fidelity_verified"] is False
            and provenance["mathematical_approval"] is False,
            "Coverage or uncertainty receipt invalid")
    require(series["status"]=="review_only_not_approved"
            and series["student_published"] is False
            and series["accepted_lecture_completion_created"] is False,
            "Unauthorized production approval")
    require(not (rendered/"lecture_completion.json").exists(),
            "Unexpected production completion receipt")
    require(job["model"]=="gemini-3.8-flash-lite-tts"
            and job["voice"]=="Kore"
            and job["provider"]=="gemini",
            "Inconsistent provider/model/voice")
    layout_rebind=verify_layout_only_rebind(
        current=original,source=source,slides=slides,audio=audio,
        old_slides=old_slides,previous_voice_plan=previous_voice_plan,
        rebind_receipt=rebind_receipt,figure_resize_receipt=figure_resize_receipt)
    parts=original["parts"]
    require(len(parts)==len(series["parts"])==2,"Two teaching parts required")
    flat=[r for part in parts for slide in part["slides"] for r in slide["elements"]]
    ordered=[s["slide"] for part in parts for s in part["slides"]]
    require(ordered==list(range(1,18)) and len(flat)>=40,
            "Original textbook slides have missing/duplicated or insufficient element coverage")
    require([s["slide"] for s in parts[0]["slides"]]==list(range(1,9))
            and [s["slide"] for s in parts[1]["slides"]]==list(range(9,18)),
            "Conceptual video boundary misplaced")
    audio_records={x["filename"]:x for x in job["segments"]}
    require(len(audio_records)==len(flat)
            and len(job["segments"])==len(flat),"Missing source synthesized segments")
    duration_groups=[]
    for part_idx,part in enumerate(parts):
        part_id=part["part_id"]
        main=rendered/part_id
        prep=staged/part_id
        rec=load(main/"review_receipt.json")
        qa=load(main/"encoded_pixel_qa.json")
        board=load(prep/"storyboard.json")
        chunks=load(prep/"tts_chunks.json")["segments"]
        scene=[el for slide in part["slides"] for el in slide["elements"]]
        count=len(scene)
        require(len(board["narration_segments"])==len(chunks)==count
                and rec["highlight_segments"]==count
                and rec["decoded_pixel_verified_events"]==count
                and rec["encoded_transition_qa"]["verified_transition_count"]==count
                and qa["count_events"]==count,"Missing an element or an encoded frame check")
        require(rec["encoded_transition_qa"]["max_encoded_frame_drift_s"]<=.15,
                "Frame transition timing failed")
        require(len(qa["checks"])==count,"Missing decoded event checks")
        for index,(event,chunk,seg,check) in enumerate(zip(
              scene,chunks,board["narration_segments"],qa["checks"]),1):
            wav_file=audio/event["wav"]
            require(wav_file.is_file(),"Missing original TTS audio")
            row=audio_records.get(event["wav"])
            require(row is not None and row["wav_sha256"]==H(wav_file)
                    and row["spoken_text_sha256"]==
                        hashlib.sha256(event["spoken_text"].encode("utf8")).hexdigest(),
                    "TTS source manifest incorrect")
            proof=load(audio/(event["wav"]+".verified.json"))
            require(proof["wav_sha256"]==H(wav_file)
                    and proof["spoken_text_sha256"]==row["spoken_text_sha256"]
                    and proof["model"]==job["model"]
                    and proof["voice"]==job["voice"],
                    "Audio provenance/voice mismatch")
            staged_wav=prep/"wav"/chunk["filename"]
            require(staged_wav.is_file() and H(staged_wav)==H(wav_file),
                    "Prepared WAV differs from frozen Gemini audio")
            require(chunk["speech_sha256"]==row["spoken_text_sha256"]
                    and seg["segment_id"]==chunk["segment_id"],
                    "Segment transcript binding changed")
            require(check["event"]==index and
                    all(float(target["highlight_evidence_gain"])>0 for target in
                        check["target_checks"]) and
                    check["target_checks"],"Decoded MP4 active pixel missing")
            with wave.open(str(wav_file),"rb") as w:
                require(w.getnchannels()==1 and w.getsampwidth()==2 and
                        w.getframerate()==24000,"Voice audio format inconsistent")
        video=main/f"{part_id}_review.mp4"
        require(video.is_file() and H(video)==rec["mp4_sha256"],
                "Encoded MP4 digest incorrect")
        require(0<rec["encoded_mp4_seconds"]<600,
                "Video reached 10 minute rejection threshold")
        duration_groups.append({
            "part":part_id,"slides":[s["slide"] for s in part["slides"]],
            "duration_s":rec["encoded_mp4_seconds"],
            "audio_s":rec["audio_seconds"],
            "elements":count,
            "decoded_pixel_checked":rec["decoded_pixel_verified_events"],
            "max_transition_drift_s":rec["encoded_transition_qa"]["max_encoded_frame_drift_s"],
            "mp4_sha256":rec["mp4_sha256"],"video_path":str(video)})
    asr=check_independent_asr(original,audio,asr_dir,required=require_asr,
                              authored_sha256=H(authored))
    quality=check_tts_quality(original,audio,quality_report,required=require_quality,
                              authored_sha256=H(authored),authored_path=authored,
                              asr_dir=asr_dir)
    result={
        "status":"FULL_SLIDE_COVERAGE_TECHNICAL_REVIEW_PASS_NOT_PRODUCTION_APPROVAL",
        "independent_model_speech_audit":asr,
        "three_layer_tts_quality_screen":quality,
        "production_eligible":False,
        "layout_only_narration_rebind":layout_rebind,
        "source_sha256":H(source),"slides_sha256":H(slides),
        "coverage_slides":ordered,
        "coverage_elements":len(flat),
        "part_videos":duration_groups,
        "same_declared_gemini_tts_model_and_voice":True,
        "all_real_wavs_bound_by_sha256":True,
        "all_encoded_element_pixels_verified":True,
        "academic_quality_human_signoff":False,
        "word_level_speech_fidelity_verified":False,
        "source_semantic_correctness_certified":False,
        "student_publication":False,
        "production_completion_receipt":False}
    with report.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False)
        f.write("\n")
    print(json.dumps(result,indent=2))
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for name in ("source","slides","authored","audio","staged","rendered","report"):
        p.add_argument("--"+name,required=True,type=Path)
    p.add_argument("--asr-dir",type=Path)
    p.add_argument("--require-asr",action="store_true")
    p.add_argument("--quality-report",type=Path)
    p.add_argument("--require-quality",action="store_true")
    p.add_argument("--old-slides",type=Path)
    p.add_argument("--previous-voice-plan",type=Path)
    p.add_argument("--rebind-receipt",type=Path)
    p.add_argument("--figure-resize-receipt",type=Path)
    args=p.parse_args()
    audit(**vars(args))
