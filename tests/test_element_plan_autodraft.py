"""Generic script/PDF element candidate matching and controlled manual promotion."""
import copy
import hashlib
import json
import tempfile
import unittest
import wave
from pathlib import Path

import pymupdf

from selenium_pipeline.element_plan_autodraft import (
    AutoDraftError, utterances, propose, similarity, stable_recommendations,
)
from selenium_pipeline.element_plan_review_bridge import (
    PlanPromotionError, promoted, template,
)
from selenium_pipeline.element_narration_stage import prepare, ElementStageError
from selenium_pipeline.element_plan_review_worklist import worklist


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CandidateAuthoringTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root=Path(tmp.name)
        self.root=root
        source_tree=root/"textbook"
        source_tree.mkdir()
        self.source=source_tree/"source.pdf"
        self.slides=source_tree/"slides.pdf"
        self.script=source_tree/"script.txt"
        self.wavdir=root/"frozen_wavs"
        self.wavdir.mkdir()
        with pymupdf.open() as d:
            p=d.new_page()
            p.insert_text((65,120),"Source evidence concerning mathematical substitution and geometry.")
            d.save(self.source)
        with pymupdf.open() as d:
            for i in (1,2,3):
                p=d.new_page()
                p.insert_text((65,100),f"Mathematical substitution slide {i} explains geometry.")
            d.save(self.slides)
        self.sentences=[
            "We use mathematical substitution to analyze the diagram. "
            "This geometry explains the integral.",
            "We describe the geometry with mathematical substitution.",
            "This mathematical substitution example ends our lecture."
        ]
        self.script.write_text("".join(
            f"**Slide {i} [15 sec]:\n{s}**\n\n" for i,s in
            enumerate(self.sentences,1)),encoding="utf8")
        self.draft=propose(source_pdf=self.source,slides_pdf=self.slides,
                           script_txt=self.script)
        self.draft_path=root/"auto.json"
        self.draft_path.write_text(json.dumps(self.draft),encoding="utf8")
        self.decisions=template(self.draft)
        self.decisions["schema_version"]=1
        self.decisions["status"]="REVIEWED_SELECTION_FOR_PROCESSING"
        self.decisions["draft_sha256"]=sha(self.draft_path)
        self.decisions["voice_id"]="gemini_gemini-3.8-flash-lite-tts_Kore_REVIEW_ONLY"
        self.decisions["tts_model"]="gemini-3.8-flash-lite-tts"
        self.decisions["tts_voice"]="Kore"
        self.decisions["reviewer_note"]="Every slide and source passage was visually checked."
        self.decisions["part_boundaries_after_slides"]=[2]
        for n,(proposal,selected) in enumerate(zip(
                self.draft["slides"],self.decisions["slides"]),1):
            selected["source_page"]=1
            selected["source_evidence"]="Source evidence concerning mathematical substitution"
            selected["review_note"]="Verified the mathematical source passage"
            target=next(x for x in proposal["auto_candidate_targets"]
                        if x["kind"]=="text_block")
            name=f"s{n:02d}_e01.wav"
            with wave.open(str(self.wavdir/name),"wb") as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000)
                w.writeframes(b"\x01\x01"*24000)
            selected["elements"]=[{
                "draft_element_id":target["draft_element_id"],
                "utterance_ids":[x["proposal_id"] for x in
                                  proposal["proposed_utterances"]],
                "wav":name,"element_review_note":
                    "This is the correct full rendered text anchor",
            }]
            spoken=self.sentences[n-1]
            (self.wavdir/(name+".verified.json")).write_text(json.dumps({
                 "filename":name,"wav_sha256":sha(self.wavdir/name),
                 "spoken_text_sha256":hashlib.sha256(
                     spoken.encode("utf8")).hexdigest(),
                 "model":"gemini-3.8-flash-lite-tts",
                 "voice":"Kore"}),encoding="utf8")
        self.selection=root/"decisions.json"
        self.save()
    def save(self):
        self.selection.write_text(json.dumps(self.decisions),encoding="utf8")
    def promote(self):
        return promoted(source=self.source,slides=self.slides,script=self.script,
                 draft_path=self.draft_path,selection=self.selection,
                 audio=self.wavdir)

    def test_review_worklist_never_promotes_visual_hints(self):
        doc=worklist(self.draft)
        self.assertIn("REVIEW-ONLY",doc)
        self.assertIn("Script fragment",doc)
        self.assertIn("Slide 1",doc)
        self.assertIn("UNVERIFIED",doc)
        self.assertIn("Academic approval remains separate",doc)
        fake=copy.deepcopy(self.draft)
        fake["can_stage_or_synthesize_audio"]=True
        with self.assertRaises(AutoDraftError):
            worklist(fake)

    def test_unreviewed_autodraft_cannot_stage_even_with_real_wavs(self):
        with self.assertRaises(ElementStageError):
            prepare(source_pdf=self.source,slides_pdf=self.slides,
                    authored_json=self.draft_path,recorded_audio=self.wavdir,
                    destination=self.root/"unapproved_staging")
        self.assertFalse((self.root/"unapproved_staging").exists())

    def test_no_words_are_generated_or_removed(self):
        self.assertEqual(self.draft["slide_count"],3)
        self.assertFalse(self.draft["can_stage_or_synthesize_audio"])
        self.assertTrue(self.draft["no_new_narration_words"])
        self.assertGreaterEqual(self.draft["candidate_target_count"],3)
        self.assertEqual(self.draft["utterance_count"],4)
        for slide,original in zip(self.draft["slides"],self.sentences):
            self.assertEqual(slide["verbatim_slide_narration"],original)
            self.assertEqual("".join(x["verbatim_script_fragment"] for x
                  in slide["proposed_utterances"]),original)
            self.assertTrue(slide["review_required"])
            self.assertTrue(all(not x["approved_for_tts"] for x in
                       slide["proposed_utterances"]))

    def test_decimal_number_and_sentence_boundaries(self):
        raw="Section 8.4 includes 3.14. Then we evaluate the integral."
        self.assertEqual("".join(utterances(raw)),raw)
        self.assertEqual(len(utterances(raw)),2)

    def test_lexical_ranking_does_not_claim_figure_understanding(self):
        self.assertEqual(similarity("mathematical substitution",
                                    "mathematical substitution"),1)
        ranked=stable_recommendations("unknown figure contents",[
            {"draft_element_id":"figure","kind":"image_whole",
             "visible_text":"unknown figure contents","anchor":{"type":"image_whole"}}])
        self.assertEqual(ranked,[])

    def test_template_never_guesses_source_or_wav(self):
        t=template(self.draft)
        self.assertEqual(t["status"],"REVIEW_SELECTION_INCOMPLETE")
        self.assertEqual(len(t["slides"]),3)
        self.assertTrue(all(x["source_page"] is None
                            and x["source_evidence"] is None
                            and not x["elements"] for x in t["slides"]))
        self.assertFalse(t["academic_approval"])

    def test_valid_review_promotes_only_to_unapproved_stageable_plan(self):
        result=self.promote()
        self.assertEqual(result["status"],
                         "author_specified_unapproved_element_narration")
        self.assertEqual([len(x["slides"]) for x in result["parts"]],[2,1])
        self.assertEqual(result["source_sha256"],sha(self.source))
        self.assertEqual(result["slides_sha256"],sha(self.slides))
        self.assertEqual([e["spoken_text"] for p in result["parts"]
            for s in p["slides"] for e in s["elements"]],
                         self.sentences)
        authored=self.root/"reviewed_plan.json"
        authored.write_text(json.dumps(result),encoding="utf8")
        staged=prepare(source_pdf=self.source,slides_pdf=self.slides,
                authored_json=authored,recorded_audio=self.wavdir,
                destination=self.root/"staged")
        self.assertEqual(staged["status"],"review_only")
        evidence=json.loads((self.root/"staged"/"element_stage_receipt.json").read_text())
        self.assertTrue(evidence["complete_lecture_coverage"])
        self.assertFalse(evidence["audio_text_fidelity_verified"])
        self.assertFalse(evidence["mathematical_approval"])

    def test_reviewed_candidate_is_reusable_with_real_encoded_highlight_video(self):
        """Convert a reviewer-mapped synthetic plan to actual 2-part MP4."""
        from selenium_pipeline.highlight_video_preview import ffmpeg_path
        from selenium_pipeline.element_highlight_workflow import review
        try:
            ffmpeg_path()
        except Exception as exc:
            self.skipTest("FFmpeg not installed: "+str(exc))
        converted=self.promote()
        plan=self.root/"approved_for_processing_not_academics.json"
        plan.write_text(json.dumps(converted),encoding="utf8")
        raw_before={p.name:sha(p) for p in self.wavdir.iterdir()}
        result=review(source=self.source,slides=self.slides,authored=plan,
                      audio=self.wavdir,output_root=self.root/"review_video")
        self.assertEqual((result["covered_slides"],result["covered_elements"]),
                         (3,3))
        self.assertEqual([x["narrated_highlight_events"] for x in result["parts"]],
                         [2,1])
        self.assertTrue(all(x["encoded_pixels_rechecked"] for x in result["parts"]))
        self.assertFalse(result["scientific_semantic_mapping_approved"])
        self.assertFalse(result["human_listening_approved"])
        self.assertFalse(result["student_published"])
        self.assertEqual(raw_before,{p.name:sha(p) for p in self.wavdir.iterdir()})
        self.assertFalse((self.root/"review_video"/"lecture_completion.json").exists())

    def test_reject_missing_wav(self):
        (self.wavdir/"s01_e01.wav").unlink()
        with self.assertRaisesRegex(PlanPromotionError,"does not exist"):
            self.promote()

    def test_reject_changed_original_script(self):
        self.script.write_text(self.script.read_text()+"Falsified")
        with self.assertRaisesRegex(PlanPromotionError,"stale"):
            self.promote()

    def test_reject_changed_approved_draft(self):
        self.draft_path.write_text(self.draft_path.read_text()+" ")
        with self.assertRaisesRegex(PlanPromotionError,"missing, unsigned"):
            self.promote()

    def test_reject_modified_candidate_with_updated_decision_hash(self):
        tampered=json.loads(self.draft_path.read_text())
        tampered["slides"][0]["proposed_utterances"][0][
           "verbatim_script_fragment"]="Invented words not in narration"
        self.draft_path.write_text(json.dumps(tampered),encoding="utf8")
        self.decisions["draft_sha256"]=sha(self.draft_path)
        self.save()
        with self.assertRaisesRegex(PlanPromotionError,"modified or stale"):
            self.promote()

    def test_reject_unverified_source_evidence(self):
        self.decisions["slides"][1]["source_evidence"]="Invented textbook conclusion"
        self.save()
        with self.assertRaisesRegex(PlanPromotionError,"not present"):
            self.promote()

    def test_reject_omitted_original_narration_sentence(self):
        self.decisions["slides"][0]["elements"][0]["utterance_ids"]=[
            self.draft["slides"][0]["proposed_utterances"][0]["proposal_id"]]
        self.save()
        with self.assertRaisesRegex(PlanPromotionError,"missing/repeated"):
            self.promote()

    def test_reject_reversed_narration_sentence_order(self):
        ids=self.decisions["slides"][0]["elements"][0]["utterance_ids"]
        self.decisions["slides"][0]["elements"][0]["utterance_ids"]=list(reversed(ids))
        self.save()
        with self.assertRaisesRegex(PlanPromotionError,"missing/repeated"):
            self.promote()

    def test_reject_fake_processing_approval_without_review(self):
        self.decisions["slides"][0]["elements"][0]["element_review_note"]=""
        self.save()
        with self.assertRaisesRegex(PlanPromotionError,"rationale"):
            self.promote()

    def test_reject_unverified_tts_origin(self):
        (self.wavdir/"s02_e01.wav.verified.json").unlink()
        with self.assertRaisesRegex(PlanPromotionError,"Missing reviewed input"):
            self.promote()

    def test_reject_changed_audio_bytes_against_tts_provenance(self):
        with (self.wavdir/"s02_e01.wav").open("ab") as stream:
            stream.write(b"tampered")
        with self.assertRaisesRegex(PlanPromotionError,"Gemini TTS provenance"):
            self.promote()

    def test_reject_mixed_voice_in_signed_tts_provenance(self):
        evidence=self.wavdir/"s02_e01.wav.verified.json"
        data=json.loads(evidence.read_text())
        data["voice"]="OtherVoice"
        evidence.write_text(json.dumps(data))
        with self.assertRaisesRegex(PlanPromotionError,"Gemini TTS provenance"):
            self.promote()

    def test_reject_duplicate_wav_names(self):
        self.decisions["slides"][1]["elements"][0]["wav"]="s01_e01.wav"
        self.save()
        with self.assertRaisesRegex(PlanPromotionError,"duplicate"):
            self.promote()

    def test_reject_invalid_part_boundary(self):
        self.decisions["part_boundaries_after_slides"]=[3]
        self.save()
        with self.assertRaisesRegex(PlanPromotionError,"boundaries"):
            self.promote()

    def test_no_implicit_academic_approval(self):
        self.decisions["academic_approval"]=True
        self.save()
        with self.assertRaisesRegex(PlanPromotionError,"improperly academic"):
            self.promote()

    def test_reject_nonconsecutive_script_headers(self):
        self.script.write_text("**Slide 2 [15 sec]:\nMissing Slide 1**")
        with self.assertRaises(AutoDraftError):
            propose(source_pdf=self.source,slides_pdf=self.slides,
                    script_txt=self.script)


if __name__=="__main__": unittest.main()
