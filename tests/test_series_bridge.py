"""Phase 4 offline integration of reviewed series → legacy TTS inputs/provenance."""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import struct
import tempfile
import unittest
import wave

import pymupdf

from selenium_pipeline.domains import load_profile
from selenium_pipeline.planning import scan_pdf, plan_series
from selenium_pipeline.storyboard_authoring import draft_storyboard
from selenium_pipeline.storyboard_gate import canonical_sha256
from selenium_pipeline.series_bridge import (
    SeriesBridgeError,prepare_authoring_bundle,stage_tts_job,
    approve_storyboard_for_tts,accept_legacy_tts_batch,
    make_tts_script,read_json,invoke_existing_tts,
)
from selenium_pipeline.runner import blocks


class LiveBridgeOfflineTests(unittest.TestCase):
    def setUp(self):
        obj=tempfile.TemporaryDirectory()
        self.addCleanup(obj.cleanup)
        self.root=Path(obj.name)
        folder=self.root/"source"/"2"/"2.2"
        folder.mkdir(parents=True)
        self.source_root=self.root/"source"
        self.source=folder/"source.pdf"
        with pymupdf.open() as doc:
            for i in range(1,4):
                p=doc.new_page()
                p.insert_text((30,80),
                    f"This is synthetic reviewed mathematics source page {i} for safe testing.")
            doc.save(self.source)
        self.scan=scan_pdf(self.source,source_root=self.source_root)
        self.profile=load_profile("mathematics")
        self.outline={
            "schema_version":1,"source_sha256":self.scan["source_sha256"],
            "profile":{"id":"mathematics","version":"1.0.0"},
            "title":"Concepts in derivatives",
            "scope":{"included_pages":[1,2,3],"excluded_pages":[]},
            "approval":{"status":"approved","reviewed_by":"Fixture reviewer",
                        "coverage_note":"The synthetic fixture pages are all covered."},
            "concepts":[{
                "concept_id":f"c{i}","title":f"Derivative concept {i}",
                "source_pages":[i],
                "evidence":[{"page":i,"kind":"text",
                             "excerpt":f"This is synthetic reviewed mathematics source page {i}"}],
                "estimated_teaching_s":80,
                "prerequisites":[],"boundary_after":"preferred",
                "planned_slides":1,
            } for i in range(1,4)]
        }
        self.plan=plan_series(self.outline,self.scan,self.profile,source_pdf=self.source)
        self.part_id="part_01"
        self.board=draft_storyboard(self.plan,self.outline,self.part_id,self.profile)
        for seg in self.board["narration_segments"]:
            if "REVIEW REQUIRED" in seg["spoken_text"]:
                seg["spoken_text"]=(
                    "A derivative describes the local rate of change of a function."
                )
        self.approval={
            "status":"approved",
            "storyboard_sha256":canonical_sha256(self.board),
            "reviewed_by":"Fixture reviewer",
            "review_note":"I reviewed the synthetic test storyboard's scientific content."
        }
        self.kw={
            "source_root":self.source_root,"source_pdf":self.source,
            "outline":self.outline,"plan":self.plan,
            "domain":"mathematics","part_id":self.part_id,
        }

    def job(self):
        dest=self.root/"tts_run"
        res=stage_tts_job(**self.kw,storyboard=self.board,
                          review_receipt=self.approval,destination=dest)
        return dest,res

    def populate_fake_output(self,folder,*,mixed=False,wrong_text=False,missing=False):
        rows=[]
        for i,segment in enumerate(self.board["narration_segments"],1):
            if not (missing and i==2):
                with wave.open(str(folder/f"slide{i}.wav"),"wb") as w:
                    w.setnchannels(1)
                    w.setsampwidth(2)
                    w.setframerate(16000)
                    w.writeframes(struct.pack("<h",1000)*16000)
            rows.append({
                "slide":i,"source_text":("wrong text" if wrong_text and i==1 else segment["spoken_text"]),
                "tts_text":segment["spoken_text"],"provider":"gemini",
                "model":"gemini-3.8-flash-lite-tts",
                "voice":"Kore" if not (mixed and i==2) else "OtherVoice",
            })
        (folder/"tts_input_manifest.json").write_text(
            json.dumps({"version":2,"slides":rows}),encoding="utf-8"
        )

    def test_draft_unapproved_plan_and_prompt_bundle_are_fail_closed(self):
        prompt=self.root/"authoring"
        info=prepare_authoring_bundle(**self.kw,output_dir=prompt)
        self.assertEqual(info["status"],"prepared_not_generated")
        self.assertTrue((prompt/"source.pdf").read_bytes()==self.source.read_bytes())
        brief=(prompt/"part_slides_instruction.txt").read_text(encoding="utf-8")
        self.assertIn("MGElement",brief)
        self.assertIn("Part 1 of 1",brief)
        with self.assertRaisesRegex(SeriesBridgeError,"NEW isolated"):
            prepare_authoring_bundle(**self.kw,output_dir=prompt)
        bad=copy.deepcopy(self.outline)
        bad["approval"]["status"]="unreviewed"
        with self.assertRaises(SeriesBridgeError):
            prepare_authoring_bundle(**{**self.kw,"outline":bad},
                                     output_dir=self.root/"blocked")
        self.assertFalse((self.root/"blocked").exists())

    def test_cannot_stage_inside_source_tree(self):
        with self.assertRaisesRegex(SeriesBridgeError,"outside source tree"):
            stage_tts_job(**self.kw,storyboard=self.board,review_receipt=self.approval,
                          destination=self.source_root/"stage")
        self.assertFalse((self.source_root/"stage").exists())

    def test_stage_tts_exact_narration_blocks_and_no_overwrite(self):
        folder,meta=self.job()
        self.assertEqual(meta["segment_count"],len(self.board["narration_segments"]))
        script=(folder/"script.txt").read_text(encoding="utf-8")
        expected=blocks(script)
        self.assertEqual([s for _,s in expected],
                         [x["spoken_text"] for x in self.board["narration_segments"]])
        self.assertIn("Part 1 of 1",script)
        with self.assertRaises(SeriesBridgeError):
            self.job()
        self.assertEqual(read_json(folder/"tts_job_manifest.json")["status"],
                         "tts_input_ready_not_synthesized")

    def test_stale_or_missing_scientific_approval_blocks(self):
        for problem in ("sha","name","status","note"):
            with self.subTest(problem=problem):
                receipt=copy.deepcopy(self.approval)
                if problem=="sha": receipt["storyboard_sha256"]="0"*64
                if problem=="name": receipt["reviewed_by"]=""
                if problem=="status": receipt["status"]="pending"
                if problem=="note": receipt["review_note"]="not reviewed"
                with self.assertRaises(SeriesBridgeError):
                    approve_storyboard_for_tts(**self.kw,storyboard=self.board,
                                               review_receipt=receipt)

    def test_storyboard_content_change_invalidates_tts_approval(self):
        changed=copy.deepcopy(self.board)
        changed["narration_segments"][2]["spoken_text"]="Altered scientific words are not reviewed."
        with self.assertRaises(SeriesBridgeError):
            stage_tts_job(**self.kw,storyboard=changed,review_receipt=self.approval,
                          destination=self.root/"unapproved")
        self.assertFalse((self.root/"unapproved").exists())

    def test_legacy_tts_wav_manifest_maps_every_segment(self):
        folder,_=self.job()
        self.populate_fake_output(folder)
        manifest=accept_legacy_tts_batch(folder,self.board)
        self.assertEqual(len(manifest),len(self.board["narration_segments"]))
        self.assertEqual(manifest[0]["segment_id"],self.board["narration_segments"][0]["segment_id"])
        self.assertTrue(all(x["voice_id"]=="gemini:gemini-3.8-flash-lite-tts:Kore"
                            for x in manifest))
        self.assertEqual(manifest[-1]["pause_after_ms"],0)
        self.assertEqual(manifest[0]["pause_after_ms"],150)

    def test_missing_audio_or_wrong_tts_text_blocks(self):
        for kind in ("missing","wrong_text","mixed"):
            with self.subTest(kind=kind):
                dest=self.root/f"job_{kind}"
                stage_tts_job(**self.kw,storyboard=self.board,
                              review_receipt=self.approval,destination=dest)
                self.populate_fake_output(dest,**{kind:True})
                with self.assertRaises(SeriesBridgeError):
                    accept_legacy_tts_batch(dest,self.board)

    def test_script_mutation_fails_before_any_real_provider_invocation(self):
        dest,_=self.job()
        with (dest/"script.txt").open("a",encoding="utf-8") as f:
            f.write("\nChanged later")
        with self.assertRaisesRegex(SeriesBridgeError,"changed after review"):
            invoke_existing_tts(
                tts_dir=dest,storyboard=self.board,
                provider="gemini",model="gemini-3.8-flash-lite-tts",
                voice="Kore",python_executable="nonexistent-executable",
            )

    def test_existing_tts_output_blocks_reinvocation(self):
        dest,_=self.job()
        self.populate_fake_output(dest)
        with self.assertRaisesRegex(SeriesBridgeError,"overwrite"):
            invoke_existing_tts(
                tts_dir=dest,storyboard=self.board,
                provider="gemini",model="gemini-3.8-flash-lite-tts",
                voice="Kore",python_executable="nonexistent-executable",
            )

    def test_invalid_foreign_profile_fails_before_creating_output(self):
        with self.assertRaises(SeriesBridgeError):
            prepare_authoring_bundle(**{**self.kw,"domain":"physics"},
                                     output_dir=self.root/"bad_subject")
        self.assertFalse((self.root/"bad_subject").exists())

    def test_gemini_transport_candidate_is_review_pending_and_no_model_required(self):
        from selenium_pipeline.series_gemini import request_storyboard_candidate
        authoring=self.root/"authoring"
        prepare_authoring_bundle(**self.kw,output_dir=authoring)
        target=self.root/"candidate.json"
        invocations=[]
        def fake_gemini(instruction,attachments):
            invocations.append((instruction,attachments))
            return json.dumps(self.board)
        receipt=request_storyboard_candidate(
            **self.kw,authoring_folder=authoring,candidate_path=target,
            transport=fake_gemini,
        )
        self.assertIn("review_required",receipt["status"])
        self.assertEqual(receipt["storyboard_sha256"],canonical_sha256(self.board))
        self.assertEqual(len(invocations),1)
        self.assertEqual(invocations[0][1][0],authoring/"source.pdf")
        self.assertEqual(read_json(target),self.board)
        with self.assertRaises(SeriesBridgeError):
            request_storyboard_candidate(
                **self.kw,authoring_folder=authoring,candidate_path=target,
                transport=fake_gemini,
            )

    def test_gemini_transport_rejects_malformed_and_stale_candidates(self):
        from selenium_pipeline.series_gemini import (
            request_storyboard_candidate,decode_storyboard_response
        )
        authoring=self.root/"authoring"
        prepare_authoring_bundle(**self.kw,output_dir=authoring)
        for label,raw in [
            ("truncated", "{"),
            ("doublekey", '{"x":1,"x":2}'),
            ("commentary", 'Here is JSON: '+json.dumps(self.board)),
            ("unlinked", json.dumps({**self.board,"plan_sha256":"0"*64})),
        ]:
            with self.subTest(label=label):
                target=self.root/(label+".json")
                with self.assertRaises((SeriesBridgeError,ValueError)):
                    request_storyboard_candidate(
                        **self.kw,authoring_folder=authoring,
                        candidate_path=target,transport=lambda instr,paths:raw,
                    )
                self.assertFalse(target.exists())

    def test_gemini_response_supports_only_one_complete_json_fence(self):
        from selenium_pipeline.series_gemini import decode_storyboard_response
        fence=chr(96)*3
        text=fence+"json\n"+json.dumps(self.board)+"\n"+fence
        self.assertEqual(decode_storyboard_response(text),self.board)
        with self.assertRaises(SeriesBridgeError):
            decode_storyboard_response(text+"\nUnapproved extra message.")

    def test_cli_prepare_and_stage_tts_use_reviewed_source_only(self):
        import subprocess
        import sys
        outline_path=self.root/"outline.json"
        plan_path=self.root/"plan.json"
        board_path=self.root/"storyboard.json"
        approval_path=self.root/"approved.json"
        for path,data in [(outline_path,self.outline),(plan_path,self.plan),
                          (board_path,self.board),(approval_path,self.approval)]:
            path.write_text(json.dumps(data),encoding="utf-8")
        cmd=[sys.executable,"-m","selenium_pipeline.series_cli"]
        base=[
            "--source-root",str(self.source_root),
            "--source-pdf",str(self.source),
            "--domain","mathematics","--part","part_01",
            "--outline",str(outline_path),"--plan",str(plan_path),
        ]
        prepared=self.root/"bundle"
        proc=subprocess.run([*cmd,"prepare",*base,"--output",str(prepared)],
                            capture_output=True,text=True,cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertTrue((prepared/"part_authoring_manifest.json").is_file())
        staged=self.root/"cli_tts"
        proc=subprocess.run(
            [*cmd,"stage-tts",*base,"--storyboard",str(board_path),
             "--review-receipt",str(approval_path),"--output",str(staged)],
            capture_output=True,text=True,cwd=Path(__file__).resolve().parents[1]
        )
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.populate_fake_output(staged)
        segments=self.root/"wav_segments.json"
        proc=subprocess.run(
            [*cmd,"accept-wavs","--tts-folder",str(staged),
             "--output",str(segments)],
            capture_output=True,text=True,cwd=Path(__file__).resolve().parents[1]
        )
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertIsInstance(json.loads(segments.read_text()),list)

    def test_recover_candidate_offline_uses_quarantine_without_live_flag(self):
        import subprocess
        import sys
        from selenium_pipeline.gemini_response_recovery import quarantine_snapshot

        authoring = self.root / "prepared_bundle"
        prepare_authoring_bundle(**self.kw, output_dir=authoring)
        outline_file = self.root / "outline.json"
        plan_file = self.root / "plan.json"
        outline_file.write_text(json.dumps(self.outline), encoding="utf-8")
        plan_file.write_text(json.dumps(self.plan), encoding="utf-8")
        record = quarantine_snapshot(
            {"text": json.dumps(self.board), "generating": False,
             "capture_status": "visible_model_response"},
            directory=self.root / "quarantine",
        )
        candidate = self.root / "recovered_candidate.json"
        args = [
            sys.executable, "-m", "selenium_pipeline.series_cli",
            "recover-candidate",
            "--source-root", str(self.source_root),
            "--source-pdf", str(self.source),
            "--outline", str(outline_file),
            "--plan", str(plan_file),
            "--domain", "mathematics",
            "--part", "part_01",
            "--authoring-folder", str(authoring),
            "--quarantine-file", str(record["raw_path"]),
            "--output", str(candidate),
        ]
        first = subprocess.run(
            args, cwd=Path(__file__).resolve().parents[1],
            text=True, capture_output=True, timeout=40,
        )
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(read_json(candidate), self.board)
        # No live --confirm-live required; existing output cannot be overwritten.
        second = subprocess.run(
            args, cwd=Path(__file__).resolve().parents[1],
            text=True, capture_output=True, timeout=40,
        )
        self.assertEqual(second.returncode, 2)
        self.assertIn("Candidate", second.stderr)

    def test_recover_partial_quarantine_cannot_create_approved_candidate(self):
        import subprocess
        import sys
        from selenium_pipeline.gemini_response_recovery import quarantine_snapshot

        authoring = self.root / "prepared_bundle"
        prepare_authoring_bundle(**self.kw, output_dir=authoring)
        outline_file = self.root / "outline.json"
        plan_file = self.root / "plan.json"
        outline_file.write_text(json.dumps(self.outline), encoding="utf-8")
        plan_file.write_text(json.dumps(self.plan), encoding="utf-8")
        record = quarantine_snapshot(
            {"text": '{"truncated":', "generating": True,
             "capture_status": "visible_model_response"},
            directory=self.root / "quarantine",
        )
        candidate = self.root / "should_not_exist.json"
        result = subprocess.run(
            [
                sys.executable, "-m", "selenium_pipeline.series_cli",
                "recover-candidate",
                "--source-root", str(self.source_root),
                "--source-pdf", str(self.source),
                "--outline", str(outline_file),
                "--plan", str(plan_file),
                "--domain", "mathematics",
                "--part", "part_01",
                "--authoring-folder", str(authoring),
                "--quarantine-file", str(record["raw_path"]),
                "--output", str(candidate),
            ],
            cwd=Path(__file__).resolve().parents[1],
            text=True, capture_output=True, timeout=40,
        )
        self.assertEqual(result.returncode, 2)
        self.assertFalse(candidate.exists())

    def test_live_flags_never_call_provider_by_accident(self):
        import subprocess
        import sys
        proc=subprocess.run(
            [sys.executable,"-m","selenium_pipeline.series_cli",
             "candidate","--source-root",str(self.source_root)],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,text=True,
        )
        self.assertEqual(proc.returncode,2)
        self.assertIn("--confirm-live",proc.stderr)


if __name__=="__main__":
    unittest.main()
