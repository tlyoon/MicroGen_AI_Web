"""No-network SHA-preserving exact publisher window selection tests."""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import unittest

from selenium_pipeline.rich_source_excerpt_windows import (
    bounded_prompt_partial,MAX_BOUNDED_PROMPT_CHARS)
from selenium_pipeline.rich_unresolved_model_queue import (
    prompt_partial, STATUS)


def synthetic():
    text=(
        "Resistance increases in proportion to the square of velocity. "
        "The net force equals gravitational force minus air resistance. "
        "Terminal speed occurs when force balances weight. "
        "An exact source quote must retain its original symbols and words. "
    )*21
    return {
        "status":STATUS,"slide":2,
        "paid_tts_authorized":False,"student_publication_authorized":False,
        "partial_request_sha256":"f"*64,
        "only_unresolved_original_utterances":[
            {"utterance_id":"s002.utterance.001",
             "verbatim_text":"Terminal speed when resistive force balances weight"},
            {"utterance_id":"s002.utterance.002",
             "verbatim_text":"Net gravitational force minus quadratic resistance"},
        ],
        "visible_targets":[
            {"target_id":"s002.text.001","kind":"text_block",
             "visible_text":"terminal speed is positive","author_rect_pdf_pt":[1,2,3,4]}
        ],
        "source_page_excerpts":[
            {"source_page":i+1,"original_page_text":text}
            for i in range(4)],
    }


class ExactSourceWindowTests(unittest.TestCase):
    def test_compact_is_sha_stable_original_verbatim_windows(self):
        request=synthetic()
        original=copy.deepcopy(request)
        full=prompt_partial(request)
        self.assertGreater(len(full),MAX_BOUNDED_PROMPT_CHARS)
        bounded,meta=bounded_prompt_partial(request)
        self.assertLess(len(bounded),len(full))
        self.assertLessEqual(len(bounded),MAX_BOUNDED_PROMPT_CHARS)
        self.assertEqual(request,original)
        self.assertEqual(meta["original_prompt_characters"],len(full))
        self.assertEqual(meta["sent_prompt_characters"],len(bounded))
        task=json.loads(bounded.rsplit("\n\n",1)[-1])
        self.assertEqual(task["partial_request_sha256"],"f"*64)
        self.assertEqual(
            task["only_unresolved_original_utterances"],
            request["only_unresolved_original_utterances"])
        self.assertEqual(task["visible_targets"],request["visible_targets"])
        self.assertTrue(all(
            segment["original_page_text"] in next(
                original_page["original_page_text"] for original_page in
                request["source_page_excerpts"] if
                original_page["source_page"]==segment["source_page"])
            for segment in task["source_page_excerpts"]))

    def test_repeated_stress_is_identical_no_source_mutation(self):
        request=synthetic()
        snapshot=json.dumps(request,sort_keys=True)
        outputs=set()
        for _ in range(100):
            prompt,metadata=bounded_prompt_partial(request)
            outputs.add((prompt,metadata["sent_prompt_characters"]))
        self.assertEqual(len(outputs),1)
        self.assertEqual(json.dumps(request,sort_keys=True),snapshot)

    def test_short_source_is_not_truncated(self):
        source=synthetic()
        source["source_page_excerpts"]=[{
            "source_page":1,
            "original_page_text":"Force balances weight at terminal speed."}]
        full=prompt_partial(source)
        prompt,metadata=bounded_prompt_partial(source)
        self.assertEqual(prompt,full)
        self.assertEqual(metadata["source_excerpt_mode"],"FULL_ORIGINAL_TEXT")

    def test_unusable_source_window_fails_closed(self):
        request=synthetic()
        request["source_page_excerpts"][0]["original_page_text"]=""
        with self.assertRaisesRegex(ValueError,"physical text"):
            bounded_prompt_partial(request)

    @unittest.skipUnless(os.name=="nt","Dell authentic source fixture")
    def test_dell_source_sha_safe_windowed_unclaimed_slide_five(self):
        from selenium_pipeline.rich_unresolved_model_queue import verify_queue
        from selenium_pipeline.rich_mapping_provider_dispatch import (
            _global_slide_claim,_academic_unclaimed_scope)
        root=Path(os.environ.get("LOCALAPPDATA",""))/"MicroGen_AI_Web_Checkpoints"
        original=root/"20261112_PR528_G2_SERWAY6_4_NARRATION_SOURCE_REUSE_V7"/"source_tree"/"6"/"6.4"
        checkpoint=root/"20261113_G2_RICH_MATH_RECOVERY_CHECKPOINT_V5"/"rich_element_map_945d5c66ec52f0bcb2c34513"
        fallback=root/"20261113_G2_SERWAY64_SAFE_PROSE_VERIFIED_7OF74_V1"
        queue=root/"20261113_G2_SERWAY64_UNRESOLVED_ONLY_RICH_QUEUE_67OF74_V1"
        if not all(x.exists() for x in (original,checkpoint,fallback,queue)):
            self.skipTest("No immutable Dell original source")
        manifest,_,requests=verify_queue(
            source_folder=original,checkpoint=checkpoint,
            fallback_dir=fallback,queue_folder=queue)
        source_sha=manifest["source_inputs_sha256"]["source.pdf"]
        global_claim=_global_slide_claim(
            source_sha256=source_sha,slide=5,source_folder=original,
            queue_folder=queue)
        scoped,excluded=_academic_unclaimed_scope(
            pending=requests[4],source_sha256=source_sha,
            checkpoint_parent=global_claim.parent.parent.parent)
        self.assertEqual(len(scoped["only_unresolved_original_utterances"]),4)
        self.assertEqual(len(excluded),2)
        full=prompt_partial(scoped)
        compact,meta=bounded_prompt_partial(scoped)
        self.assertGreater(len(full),12000)
        self.assertLessEqual(len(compact),MAX_BOUNDED_PROMPT_CHARS)
        task=json.loads(compact.rsplit("\n\n",1)[-1])
        self.assertEqual(task["partial_request_sha256"],scoped["partial_request_sha256"])
        self.assertEqual(
            [x["utterance_id"] for x in task["only_unresolved_original_utterances"]],
            [x["utterance_id"] for x in scoped["only_unresolved_original_utterances"]])
        self.assertFalse(global_claim.exists())
        self.assertTrue(meta["original_source_queue_unchanged"])

if __name__=="__main__":
    unittest.main()
