"""Source-free failure-injection for the real autonomous QA orchestration.

No Gemini request, audio decoding, student approval, publication or local model.
Production always executes its independent source/media/speech validators.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from selenium_pipeline.evidence_reuse_contract import file_sha256
from selenium_pipeline.windows_autonomous_lecture_qa import inspect


WORDS = "The charged particle moves in a constant electric field."


def fixture(tmp_path: Path):
    folder = tmp_path / "lecture"
    queue = tmp_path / "independent_ai_queue"
    audio = tmp_path / "existing_recorded_audio"
    asr = tmp_path / "distinct_model_asr_receipts"
    for path in (folder, queue, audio, asr):
        path.mkdir()
    (folder / "source.pdf").write_bytes(b"synthetic original PDF test only")
    (folder / "slides.pdf").write_bytes(b"synthetic original slide PDF test only")
    (folder / "script.txt").write_text(
        "**Slide 1 [8 sec]: " + WORDS, encoding="utf-8")
    names = {name: file_sha256(folder / name)
             for name in ("source.pdf", "slides.pdf", "script.txt")}
    plan = folder / "element_narration_plan.json"
    item = {
        "status": "author_specified_unapproved_element_narration",
        "source_sha256": names["source.pdf"],
        "slides_sha256": names["slides.pdf"],
        "script_sha256": names["script.txt"],
        "parts": [{"slides": [{"slide": 1, "elements": [
            {"wav": "element1.wav", "spoken_text": WORDS}]}]}]
    }
    plan.write_text(json.dumps(item), encoding="utf8")
    receipt = {
        "origin": "independent_fresh_decoded_pixel_reverification",
        "authored_plan_sha256": file_sha256(plan),
        "source_sha256": names["source.pdf"],
        "slides_sha256": names["slides.pdf"],
        "original_narration_script_sha256": names["script.txt"],
    }
    (folder / "lecture_completion.json").write_text(
        json.dumps(receipt), encoding="utf8")
    admitted = {
        "status": "INDEPENDENTLY_REVALIDATED_AI_SOURCE_MATH_AGREEMENT_QUEUE",
        "original_utterances": 1,
        "pending_or_disputed": 0,
        "student_publication_authorized": False,
        "accepted_ai_evidence": [
            {"utterance_id": "s001.u001",
             "original_spoken_sha256": hashlib.sha256(
                 WORDS.encode("utf8")).hexdigest()}],
    }
    screened = {
        "status": "QUALITY_SCREEN_REVIEW_ONLY",
        "plan_sha256": file_sha256(plan),
        "all_machine_checks_passed": True,
        "total_clips": 1,
        "machine_screen_passed": 1,
        "pending_asr": 0,
        "manual_review_required": 0,
        "technical_rejected": 0,
    }
    video = {
        "status": "accepted_synchronized_series",
        "verification_scope": "technical_media_only",
        "parts": [{"part_id": "part_01", "duration_s": 72.1,
                   "highlight_events": 1}],
    }
    def review_fn(*, queue_root, folder):
        return admitted
    def speech_fn(*, plan, audio, asr_dir, output=None):
        return screened
    def video_fn(root, *, probe=None):
        return video
    return folder, queue, plan, audio, asr, admitted, screened, video, (
        review_fn, speech_fn, video_fn)


def run(f):
    folder, queue, plan, audio, asr, _a, _s, _v, validators = f
    return inspect(
        folder=folder, queue_root=queue, plan=plan,
        audio=audio, asr_dir=asr,
        review_fn=validators[0], speech_fn=validators[1],
        video_fn=validators[2],
    )


def test_all_source_audio_video_checks_are_scoped_never_student_release(tmp_path, monkeypatch):
    monkeypatch.setattr("selenium_pipeline.windows_autonomous_lecture_qa.os.name", "nt")
    output = run(fixture(tmp_path))
    assert output["status"] == "AI_SOURCE_SPEECH_AND_SYNC_MEDIA_TECHNICAL_QA_VERIFIED"
    assert output["autonomous_scoped_technical_qa_accepted"] is True
    assert output["human_academic_approval_required_by_this_preflight"] is False
    assert output["final_full_lecture_academic_acceptance"] is False
    assert output["acoustic_voice_identity_independently_verified"] is False
    assert output["student_publication_authorized"] is False
    assert output["new_model_or_tts_calls"] is False


@pytest.mark.parametrize("case", [
    "missing_math_agreement", "missing_one_ai_utterance",
    "pending_independent_asr", "missing_speech_clip", "overlong_video",
    "source_plan_changed", "media_plan_changed", "duplicate_wav",
    "script_changed_after_review", "unverified_pixel_media",
])
def test_false_or_incomplete_evidence_is_not_promoted(tmp_path, monkeypatch, case):
    monkeypatch.setattr("selenium_pipeline.windows_autonomous_lecture_qa.os.name", "nt")
    f = fixture(tmp_path)
    folder, queue, plan, audio, asr, review, speech, video, _ = f
    if case == "missing_math_agreement":
        review["pending_or_disputed"] = 1
    elif case == "missing_one_ai_utterance":
        review["accepted_ai_evidence"] = []
    elif case == "pending_independent_asr":
        speech["pending_asr"] = 1
    elif case == "missing_speech_clip":
        speech["machine_screen_passed"] = 0
    elif case == "overlong_video":
        video["parts"][0]["duration_s"] = 600.0
    elif case == "source_plan_changed":
        data = json.loads(plan.read_text())
        data["source_sha256"] = "0" * 64
        plan.write_text(json.dumps(data))
    elif case == "media_plan_changed":
        data = json.loads((folder / "lecture_completion.json").read_text())
        data["authored_plan_sha256"] = "f" * 64
        (folder / "lecture_completion.json").write_text(json.dumps(data))
    elif case == "duplicate_wav":
        data = json.loads(plan.read_text())
        data["parts"][0]["slides"][0]["elements"].append(
            data["parts"][0]["slides"][0]["elements"][0].copy())
        plan.write_text(json.dumps(data))
    elif case == "script_changed_after_review":
        (folder / "script.txt").write_text("Changed script without review")
    elif case == "unverified_pixel_media":
        video["verification_scope"] = "legacy_video_only"
    with pytest.raises((ValueError, KeyError, RuntimeError)):
        run(f)


def test_not_a_source_sized_canary_or_paid_asr_dispatch(tmp_path, monkeypatch):
    monkeypatch.setattr("selenium_pipeline.windows_autonomous_lecture_qa.os.name", "nt")
    f = fixture(tmp_path)
    invoked = {"review": 0, "screen": 0, "video": 0}
    def reviewer(**_):
        invoked["review"] += 1
        return f[5]
    def screener(**_):
        invoked["screen"] += 1
        return f[6]
    def verifier(*_, **__):
        invoked["video"] += 1
        return f[7]
    report = inspect(
        folder=f[0], queue_root=f[1], plan=f[2], audio=f[3], asr_dir=f[4],
        review_fn=reviewer, speech_fn=screener, video_fn=verifier)
    assert invoked == {"review": 1, "screen": 1, "video": 1}
    assert report["new_model_or_tts_calls"] is False


def test_release_board_refuses_partial_autonomous_ai_qa_inputs():
    from selenium_pipeline.windows_release_readiness_board import main
    with pytest.raises(SystemExit) as error:
        main(["--jobs-dir", "C:\\unrelated\\job_receipts",
              "--fresh-trial-dir", "C:\\unrelated\\trial",
              "--autonomous-qa-folder", "C:\\unrelated\\lecture"])
    assert error.value.code == 2


def test_qa_technical_evidence_cannot_transfer_to_another_original():
    from selenium_pipeline.windows_release_readiness_board import (
        _autonomous_qa_matches_distinct_second_source as matching,
    )
    first = "a" * 64
    second = "b" * 64
    qa = {
        "status": "AI_SOURCE_SPEECH_AND_SYNC_MEDIA_TECHNICAL_QA_VERIFIED",
        "autonomous_scoped_technical_qa_accepted": True,
        "source_sha256": second,
        "student_publication_authorized": False,
    }
    candidate = {
        "technical_second_source_candidate_ready_for_academic_review": True,
        "distinct_original_source_sha256_verified": True,
        "historical_source_sha256": first,
        "candidate_source_sha256": second,
    }
    assert matching(qa, candidate)
    assert not matching({**qa, "source_sha256": first}, candidate)
    assert not matching(qa, {**candidate, "historical_source_sha256": second})
    assert not matching(qa, {**candidate,
                              "distinct_original_source_sha256_verified": False})
    assert not matching({**qa, "student_publication_authorized": True}, candidate)
    assert not matching({**qa, "status": "unverified"}, candidate)
