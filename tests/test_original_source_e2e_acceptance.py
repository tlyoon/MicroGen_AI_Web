"""Windows full original-source academic/multimedia gate.

Tests real PyMuPDF publisher/author PDF inputs and frozen source-mapping
evidence, never TTS, model UI, FFmpeg or an arbitrary approval marker.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pymupdf

from selenium_pipeline.rich_element_mapping_checkpoint import (
    require_automatic_mapping_or_checkpoint,ElementMappingCheckpointBlocked)
from selenium_pipeline.rich_element_safe_prose_fallback import stage_section
from selenium_pipeline.rich_unresolved_model_queue import prepare_queue
from selenium_pipeline.original_source_e2e_acceptance import (
    inspect_source_e2e,execute_prepared,SourceReleaseBlocked)


class OriginalE2EExecutionGateTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.original=self.root/"original"/"8"/"8.4"
        self.original.mkdir(parents=True)
        self.source=self.original/"source.pdf"
        self.slides=self.original/"slides.pdf"
        self.script=self.original/"script.txt"
        self.prose="The experiment provides evidence for the observed physical process."
        self.second="The measurement confirms the predicted qualitative behavior."
        with pymupdf.open() as d:
            page=d.new_page()
            page.insert_text((60,90),self.prose)
            page.insert_text((60,130),self.second)
            d.save(self.source)
        with pymupdf.open() as d:
            page=d.new_page()
            page.insert_text((60,90),self.prose)
            page.insert_text((60,130),self.second)
            page.draw_line((70,195),(180,215))
            d.save(self.slides)
        self.script.write_text(
            "**Slide 1 [12sec]:\n"+self.prose+" "+self.second,
            encoding="utf8")
        self.immutable=[p.read_bytes() for p in
                        (self.source,self.slides,self.script)]
        c=self.root/"mapping"
        c.mkdir()
        with self.assertRaises(ElementMappingCheckpointBlocked):
            require_automatic_mapping_or_checkpoint(
                source=self.source,slides=self.slides,script=self.script,
                checkpoint_root=c)
        self.ck=next(c.glob("rich_element_map_*"))
        self.fallback=self.root/"accepted_prose"
        stage_section(source_folder=self.original,checkpoint=self.ck,
                      destination=self.fallback)
        self.queue=self.root/"unresolved_queue"
        prepare_queue(source_folder=self.original,checkpoint=self.ck,
                      fallback_dir=self.fallback,destination=self.queue)

    def inspect(self,**kwargs):
        return inspect_source_e2e(lecture=self.original,
            checkpoint=self.ck,fallback_dir=self.fallback,
            queue_dir=self.queue,**kwargs)

    def test_no_response_does_not_mean_all_lecture_semantics_passed(self):
        r=self.inspect()
        self.assertEqual(r["status"],
                         "BLOCKED_UNRESOLVED_SOURCE_VISUAL_NARRATION")
        self.assertFalse(r["full_semantic_source_review_ready"])
        self.assertFalse(r["execution_allowed_without_new_paid_or_model_calls"])
        self.assertFalse(r["dry_run_proves_entire_lecture_ready"])
        self.assertFalse(r["new_model_or_tts_calls"])
        self.assertFalse(r["student_publication_authorized"])

    def test_prose_only_complete_response_still_requires_real_element_audio(self):
        r=self.inspect(model_responses=self.fallback)
        self.assertEqual(r["unresolved_source_element_mappings"],0)
        self.assertTrue(r["full_semantic_source_review_ready"])
        self.assertEqual(r["status"],"SOURCE_MAPPING_VERIFIED_ELEMENT_PCM_REQUIRED")
        with patch("selenium_pipeline.full_pipeline_video_handoff.complete_from_published",
                   side_effect=AssertionError("No PCM, no rendering")) as video:
            with self.assertRaisesRegex(SourceReleaseBlocked,
                                        "not ready"):
                execute_prepared(lecture=self.original,
                    checkpoint=self.ck,fallback_dir=self.fallback,
                    queue_dir=self.queue,model_responses=self.fallback)
        video.assert_not_called()

    def _install_synthetic_element_pcm_fixture(self):
        """A source-locked PCM carrier, not proof of actual spoken English."""
        import hashlib
        import math
        import struct
        import wave
        from selenium_pipeline.tts_effective_identity import DEFAULT

        def sha(file):
            return hashlib.sha256(file.read_bytes()).hexdigest()

        clips=["s01_e01.wav","s01_e02.wav"]
        phrases=[self.prose,self.second]
        # The actual PDF is verified by the same source_bound_plan entrypoint.
        authored={
            "schema_version":1,
            "status":"author_specified_unapproved_element_narration",
            "source_sha256":sha(self.source),
            "slides_sha256":sha(self.slides),
            "voice_id":"gemini-3.8-flash-lite-tts Kore",
            "parts":[{"part_id":"part_01","slides":[{
                "slide":1,"source_page":1,"source_evidence":self.prose,
                "elements":[
                    {"wav":name,"spoken_text":words,
                     "anchor":{"type":"text_block","index":i,
                               "text_evidence":words[:25]}}
                    for i,(name,words) in enumerate(zip(clips,phrases))
                ]}]}]}
        plan=self.original/"element_narration_plan.json"
        plan.write_text(json.dumps(authored),encoding="utf8")
        aud=self.original/"element_wav"
        aud.mkdir()
        for n,name in enumerate(clips):
            with wave.open(str(aud/name),"wb") as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(24000)
                values=[int(2000*math.sin(2*math.pi*(220+55*n)*i/24000))
                        for i in range(12000)]
                f.writeframes(struct.pack("<"+"h"*len(values),*values))
        upstream=aud/"_producer"
        upstream.mkdir()
        (upstream/"script.txt").write_text(
            "".join(f"**Slide {i} [30s]:\n\n{txt}\n\n"
                    for i,txt in enumerate(phrases,1)),encoding="utf8")
        producer={
            "version":2,"primary":DEFAULT,
            "slides":[{"slide":i,"source_text":txt,"tts_text":txt,
                       **DEFAULT,"fallback_used":False}
                      for i,txt in enumerate(phrases,1)]
        }
        (upstream/"tts_input_manifest.json").write_text(
            json.dumps(producer),encoding="utf8")
        declarations=[{
            "wav":name,"sha256":sha(aud/name),
            "spoken_text_sha256":hashlib.sha256(txt.encode("utf8")).hexdigest(),
            "provider":"gemini","model":"gemini-3.8-flash-lite-tts",
            "voice":"Kore",
        } for name,txt in zip(clips,phrases)]
        (self.original/"element_tts_manifest.json").write_text(
            json.dumps({
                "schema_version":1,
                "status":"verified_source_bound_element_audio",
                "source_sha256":sha(self.source),
                "slides_sha256":sha(self.slides),
                "authored_plan_sha256":sha(plan),
                "provider":"gemini","model":"gemini-3.8-flash-lite-tts",
                "voice":"Kore","all_elements_one_voice":True,
                "producer_manifest_sha256":sha(
                    upstream/"tts_input_manifest.json"),
                "producer_script_sha256":sha(upstream/"script.txt"),
                "elements":declarations}),encoding="utf8")
        return aud

    def test_forged_presence_only_audio_is_rejected_before_video_or_tts(self):
        for name in ("element_narration_plan.json","element_tts_manifest.json"):
            (self.original/name).write_text("{}",encoding="utf8")
        (self.original/"element_wav").mkdir()
        with patch("selenium_pipeline.full_pipeline_video_handoff.complete_from_published",
                side_effect=AssertionError("No rendering from empty WAVs")) as render:
            with self.assertRaisesRegex(SourceReleaseBlocked,
                                        "Existing element PCM lacks verified"):
                execute_prepared(lecture=self.original,checkpoint=self.ck,
                    fallback_dir=self.fallback,queue_dir=self.queue,
                    model_responses=self.fallback)
        render.assert_not_called()
        self.assertFalse((self.original/"lecture_completion.json").exists())

    def test_verified_element_pcm_uses_only_the_existing_renderer(self):
        self._install_synthetic_element_pcm_fixture()
        readiness=self.inspect(model_responses=self.fallback)
        self.assertEqual(readiness["status"],
                         "READY_FOR_STRICT_RECORDED_AUDIO_MULTIPART_RENDER")
        self.assertTrue(readiness["existing_per_element_recorded_audio_available"])
        record=readiness["existing_element_pcm_technical_proof"]
        self.assertEqual(record["element_count"],2)
        self.assertEqual(record["source_slide_count"],1)
        self.assertFalse(record["verified_audio_words_match_script"])
        self.assertFalse(readiness["actual_audio_text_fidelity_independently_verified"])
        with patch("selenium_pipeline.full_pipeline_video_handoff.complete_from_published",
                return_value={
                    "status":"INSTALLED_TECHNICALLY_ACCEPTED_MULTIPART_VIDEO",
                    "part_count":1,
                    "student_publication_authorized":False}) as video:
            result=execute_prepared(lecture=self.original,checkpoint=self.ck,
                fallback_dir=self.fallback,queue_dir=self.queue,
                model_responses=self.fallback)
        self.assertEqual(result["status"],
                         "ORIGINAL_SOURCE_STRICT_MULTIPART_TECHNICAL_PASS")
        video.assert_called_once_with(source=self.source,
                                      require_slide_tts_qa=False)
        self.assertEqual(self.immutable,[p.read_bytes() for p in
                             (self.source,self.slides,self.script)])
        self.assertFalse(result["student_publication_authorized"])

    def test_pcm_missing_clip_and_forged_producer_hash_fail_closed(self):
        audio=self._install_synthetic_element_pcm_fixture()
        real_clip=audio/"s01_e02.wav"
        existing=real_clip.read_bytes()
        real_clip.unlink()
        with self.assertRaisesRegex(SourceReleaseBlocked,
                                    "Existing element PCM lacks verified"):
            self.inspect(model_responses=self.fallback)
        real_clip.write_bytes(existing)
        producer=self.original/"element_tts_manifest.json"
        object_=json.loads(producer.read_text("utf8"))
        object_["elements"][0]["sha256"]="f"*64
        producer.write_text(json.dumps(object_),encoding="utf8")
        with self.assertRaisesRegex(SourceReleaseBlocked,
                                    "Existing element PCM lacks verified"):
            self.inspect(model_responses=self.fallback)
        self.assertEqual(self.immutable,[p.read_bytes() for p in
                             (self.source,self.slides,self.script)])


    def test_rehashed_fake_wav_still_fails_physical_pcm_preflight(self):
        import hashlib
        pcm=self._install_synthetic_element_pcm_fixture()
        fake=pcm/"s01_e02.wav"
        fake.write_bytes(b"not-a-waveform")
        manifest=self.original/"element_tts_manifest.json"
        record=json.loads(manifest.read_text("utf8"))
        # Even a forged producer manifest hash that matches the fake bytes
        # must NOT substitute for an actual independently decoded PCM.
        record["elements"][1]["sha256"]=hashlib.sha256(fake.read_bytes()).hexdigest()
        manifest.write_text(json.dumps(record),encoding="utf8")
        with patch("selenium_pipeline.full_pipeline_video_handoff.complete_from_published",
                   side_effect=AssertionError("Do not render corrupt PCM")) as render:
            with self.assertRaisesRegex(SourceReleaseBlocked,
                                        "Existing element PCM lacks verified"):
                execute_prepared(lecture=self.original,checkpoint=self.ck,
                    fallback_dir=self.fallback,queue_dir=self.queue,
                    model_responses=self.fallback)
        render.assert_not_called()
        self.assertFalse((self.original/"lecture_completion.json").exists())
        self.assertEqual(self.immutable,[p.read_bytes() for p in
                             (self.source,self.slides,self.script)])

    def test_accepted_multipart_is_reused_without_recomputing_all_stages(self):
        with patch("selenium_pipeline.sourcebound_completion_guard.inspect_sourcebound_completion",
             return_value={"status":"ALREADY_COMPLETED_SOURCEBOUND_MULTIPART",
                           "part_count":2}):
            r=inspect_source_e2e(lecture=self.original)
        self.assertEqual(r["status"],
                         "REUSED_PHYSICALLY_VERIFIED_MULTIPART_TECHNICAL_ONLY")
        self.assertEqual(r["part_count"],2)
        self.assertFalse(r["all_seven_stages_recomputed"])

    def test_partial_element_audio_is_protected_not_regenerated(self):
        (self.original/"element_narration_plan.json").write_text("{}")
        with self.assertRaisesRegex(SourceReleaseBlocked,"Partial recorded"):
            self.inspect(model_responses=self.fallback)
        self.assertFalse((self.original/"element_wav").exists())

    def test_physical_original_source_change_invalidates_earlier_receipt(self):
        self.source.write_bytes(b"publisher source was changed")
        with self.assertRaises((ValueError,SourceReleaseBlocked)):
            self.inspect(model_responses=self.fallback)

    def test_wrong_publisher_version_is_rejected_before_any_render(self):
        with self.assertRaisesRegex(SourceReleaseBlocked,"Wrong publisher"):
            self.inspect(expected_publisher_sha256="f"*64)


class RealSerwayE2EExistingAssetPreflight(unittest.TestCase):
    def test_real_full_source_review_blocks_without_per_element_pcm(self):
        from selenium_pipeline.figure_source_identity import _sha
        base=Path.home()/"AppData"/"Local"/"MicroGen_AI_Web_Checkpoints"
        lecture=(base/
            "20261112_PR528_G2_SERWAY6_4_NARRATION_SOURCE_REUSE_V7"/
            "source_tree"/"6"/"6.4")
        checkpoint=(base/
            "20261113_G2_RICH_MATH_RECOVERY_CHECKPOINT_V5"/
            "rich_element_map_945d5c66ec52f0bcb2c34513")
        fallback=base/"20261113_G2_SERWAY64_SAFE_PROSE_VERIFIED_7OF74_V1"
        queue=base/"20261113_G2_SERWAY64_UNRESOLVED_ONLY_RICH_QUEUE_67OF74_V1"
        if not all(p.exists() for p in (lecture,checkpoint,fallback,queue)):
            self.skipTest("Actual Serway 6.4 source only on Dell-115")
        assets={n:_sha(lecture/n) for n in
                ("source.pdf","slides.pdf","script.txt")}
        with (patch("selenium_pipeline.full_pipeline_video_handoff."
                    "complete_from_published",
                    side_effect=AssertionError("No original audio render")),
              patch("selenium_pipeline.series_gemini._browser_request",
                    side_effect=AssertionError("No consumed review replay"))):
            result=inspect_source_e2e(
                lecture=lecture,checkpoint=checkpoint,
                fallback_dir=fallback,queue_dir=queue)
        self.assertEqual(result["status"],
            "BLOCKED_UNRESOLVED_SOURCE_VISUAL_NARRATION")
        self.assertEqual(result["original_slide_count"],14)
        self.assertEqual(result["independently_previously_verified_text_links"],7)
        self.assertEqual(result["unresolved_source_element_mappings"],67)
        self.assertFalse(result["existing_per_element_recorded_audio_available"])
        self.assertIsNone(result["existing_element_pcm_technical_proof"])
        self.assertFalse(result["actual_audio_text_fidelity_independently_verified"])
        self.assertFalse(result["execution_allowed_without_new_paid_or_model_calls"])
        self.assertFalse(result["student_publication_authorized"])
        self.assertEqual(assets,{n:_sha(lecture/n) for n in assets})


if __name__=="__main__":
    unittest.main()
