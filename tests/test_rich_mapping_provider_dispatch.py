"""Windows no-network provider readiness and exactly-once model-response tests.

Uses physical synthetic PDF source/author bytes, real frozen worklist, safe
prose fallback and unresolved-only queue. Mock only the external provider UI
and model response: no real paid generation or browser/tab navigation.
"""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf
from selenium_pipeline.rich_mapping_provider_readiness import (
    inspect_provider,choose_provider)
from selenium_pipeline.rich_mapping_provider_dispatch import (
    dispatch_one,RichMappingError)
from selenium_pipeline.rich_element_mapping_checkpoint import (
    require_automatic_mapping_or_checkpoint,ElementMappingCheckpointBlocked)
from selenium_pipeline.rich_element_safe_prose_fallback import stage_section
from selenium_pipeline.rich_unresolved_model_queue import prepare_queue


class Element:
    def __init__(self,label="",visible=True):
        self.text=label
        self._visible=visible
    def is_displayed(self):
        return self._visible


class FakeDriver:
    def __init__(self,provider,authenticated):
        self.provider=provider
        self.authenticated=authenticated
        self.window_handles=["tab_1"]
        self.switch_to=self
        self.current_url=(
            "https://gemini.google.com/app" if provider=="gemini"
            else "https://chatgpt.com/")
    def window(self,handle):
        assert handle=="tab_1"
    def find_elements(self,kind,selector):
        assert kind=="css selector"
        if self.provider=="gemini":
            if selector.startswith('button[aria-label^='):
                return [Element()] if self.authenticated else []
            return []
        if selector=="button":
            return ([] if self.authenticated else [Element("Log in")])
        if selector=="#prompt-textarea":
            return [Element()] if self.authenticated else []
        return []


class ProviderReadinessTests(unittest.TestCase):
    def test_gemini_current_authenticated_flash_session_is_observed_read_only(self):
        p=inspect_provider("gemini",9222,
            browser_factory=lambda _:FakeDriver("gemini",True),
            endpoint=lambda _:{"Browser":"Chrome/156",
                               "webSocketDebuggerUrl":"ws://127.0.0.1"})
        self.assertEqual(p["status"],"AUTHENTICATED_COMPOSER_READY")
        self.assertFalse(p["model_submission_performed"])
        self.assertEqual(choose_provider([p])["chosen_provider"],"gemini")

    def test_chatgpt_guest_login_is_not_accepted_as_authenticated(self):
        p=inspect_provider("chatgpt",9223,
            browser_factory=lambda _:FakeDriver("chatgpt",False),
            endpoint=lambda _:{"Browser":"Chrome/156",
                               "webSocketDebuggerUrl":"ws://127.0.0.1"})
        self.assertEqual(p["status"],"LOGIN_REQUIRED")
        self.assertEqual(choose_provider([p])["chosen_provider"],None)

    def test_no_fallback_even_when_chatgpt_is_authenticated(self):
        a={"provider":"gemini","status":"BROWSER_UNAVAILABLE",
           "authenticated_ui_ready":False,"model_submission_performed":False}
        b={"provider":"chatgpt","status":"AUTHENTICATED_COMPOSER_READY",
           "authenticated_ui_ready":True,"model_submission_performed":False}
        choice=choose_provider([a,b])
        self.assertIsNone(choice["chosen_provider"])
        self.assertEqual(choice["status"],"GEMINI_SELENIUM_TEMPORARY_FAILURE_STOP")
        self.assertIn("No ChatGPT or Gemini API",choice["reminder"])
        self.assertEqual(choose_provider([a,b],
              model_submission_uncertain=True)["status"],
              "RECONCILE_EXISTING_GEMINI_SEND_NO_RETRY")


class OneShotOriginalSourceQueueTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.original=self.root/"publisher"/"22"/"22.1"
        self.original.mkdir(parents=True)
        self.source=self.original/"source.pdf"
        self.slides=self.original/"slides.pdf"
        self.script=self.original/"script.txt"
        prose="The experiment provides evidence for the observed physical process."
        equation="For tangent substitution, x equals a times tangent theta."
        with pymupdf.open() as doc:
            pg=doc.new_page()
            pg.insert_text((70,90),prose)
            pg.insert_text((70,133),equation)
            doc.save(self.source)
        with pymupdf.open() as doc:
            pg=doc.new_page()
            pg.insert_text((70,90),prose)
            pg.insert_text((70,133),equation)
            pg.draw_line((80,210),(220,195))
            doc.save(self.slides)
        self.script.write_text(
            "**Slide 1 [14 seconds]:\n"+prose+" "+equation,
            encoding="utf8")
        root=self.root/"original_sha_cache"
        root.mkdir()
        with self.assertRaises(ElementMappingCheckpointBlocked):
            require_automatic_mapping_or_checkpoint(
                source=self.source,slides=self.slides,script=self.script,
                checkpoint_root=root)
        self.ck=next(root.glob("rich_element_map_*"))
        self.fallback=self.root/"accepted_source_prose"
        stage_section(source_folder=self.original,checkpoint=self.ck,
                      destination=self.fallback)
        self.queue=self.root/"sourcebound_unresolved_only"
        prepare_queue(source_folder=self.original,checkpoint=self.ck,
                      fallback_dir=self.fallback,destination=self.queue)
        self.out=self.root/"model_attempts"
        self.out.mkdir()
        self.provider=[{
            "provider":"gemini",
            "debug_port":9222,
            "status":"AUTHENTICATED_COMPOSER_READY",
            "authenticated_ui_ready":True,
            "model_submission_performed":False,
        }]
        self.original_bytes=[p.read_bytes() for p in
                             (self.source,self.slides,self.script)]

    def _call(self,transport,providers=None):
        return dispatch_one(source_folder=self.original,
               checkpoint=self.ck,fallback_dir=self.fallback,
               queue_folder=self.queue,slide=1,attempt_root=self.out,
               provider_statuses=(providers if providers is not None
                                  else self.provider),
               transport=transport,wait_cap_s=12)

    def reply(self):
        req=json.loads((self.queue/"slide_001.unresolved_request.json").read_text("utf8"))
        uid=req["only_unresolved_original_utterances"][0]["utterance_id"]
        return json.dumps({"slide":1,
            "partial_request_sha256":req["partial_request_sha256"],
            "associations":[{"utterance_id":uid,"target_id":None,
              "source_page":None,"source_quote":None,
              "reason":"Independent equation proof required",
              "needs_review":True}]})

    def test_model_captured_once_and_prose_reused_without_paid_generation(self):
        record=self._call(lambda provider,prompt,port,wait:self.reply())
        self.assertEqual(record["status"],"CAPTURED_SOURCE_VERIFIED_REVIEW_ONLY")
        self.assertEqual(record["prior_accepted_prose_links_protected"],1)
        self.assertEqual(record["requested_utterances"],1)
        self.assertFalse(record["paid_tts_authorized"])
        claim=self.out/"slide_001.one_submission.json"
        self.assertTrue(claim.is_file())
        self.assertTrue((self.out/"slide_001.merged_response.json").is_file())
        self.assertEqual([p.read_bytes() for p in
                 (self.source,self.slides,self.script)],self.original_bytes)

    def test_invalid_return_quarantines_as_maybe_sent_and_never_retries(self):
        with self.assertRaises(RichMappingError):
            self._call(lambda provider,prompt,port,wait:
                       '{"invalid incomplete response"')
        claim=self.out/"slide_001.one_submission.json"
        self.assertEqual(json.loads(claim.read_text("utf8"))["status"],
                         "MAY_HAVE_SUBMITTED_RECONCILE_BEFORE_RESEND")
        with self.assertRaisesRegex(RichMappingError,"already claimed"):
            self._call(lambda *x: (_ for _ in ()).throw(
                AssertionError("Model must not be called twice")))

    def test_offline_providers_do_not_claim_or_send_a_job(self):
        report=self._call(lambda *x: (_ for _ in ()).throw(
                    AssertionError("Provider unavailable must not send")),providers=[{
                "provider":"gemini","debug_port":9222,
                "status":"BROWSER_UNAVAILABLE",
                "authenticated_ui_ready":False,
                "model_submission_performed":False,
            }])
        self.assertEqual(report["status"],
                         "GEMINI_SELENIUM_TEMPORARY_FAILURE_STOP")
        self.assertEqual(list(self.out.iterdir()),[])

    def test_gemini_unavailable_stops_without_chatgpt_even_when_signed_in(self):
        statuses=[
            {"provider":"gemini","debug_port":9222,
             "status":"BROWSER_UNAVAILABLE",
             "authenticated_ui_ready":False,"model_submission_performed":False},
            {"provider":"chatgpt","debug_port":9223,
             "status":"AUTHENTICATED_COMPOSER_READY",
             "authenticated_ui_ready":True,"model_submission_performed":False},
        ]
        called=[]
        result=self._call(lambda *a:called.append(a),providers=statuses)
        self.assertEqual(result["status"],"GEMINI_SELENIUM_TEMPORARY_FAILURE_STOP")
        self.assertIn("No ChatGPT or Gemini API",result["stop_message"])
        self.assertEqual(called,[])
        self.assertEqual(list(self.out.iterdir()),[])

    def test_chatgpt_only_readiness_never_calls_real_transport(self):
        statuses=[{"provider":"chatgpt","debug_port":9223,
                   "status":"AUTHENTICATED_COMPOSER_READY",
                   "authenticated_ui_ready":True,"model_submission_performed":False}]
        with patch(
            "selenium_pipeline.rich_mapping_provider_dispatch._real_transport",
            side_effect=AssertionError("No ChatGPT request allowed")) as sender:
            result=self._call(None,providers=statuses)
        self.assertEqual(result["status"],"GEMINI_SELENIUM_TEMPORARY_FAILURE_STOP")
        sender.assert_not_called()

    def test_no_direct_chatgpt_or_api_generation_transport(self):
        from selenium_pipeline.rich_mapping_provider_dispatch import _real_transport
        for name,port in (("chatgpt",9223),("api",9222)):
            with self.subTest(name=name):
                with self.assertRaisesRegex(RichMappingError,
                                             "sole supported LLM generation route"):
                    _real_transport(name,"synthetic prompt",port,12)

    def test_postsend_gemini_timeout_stops_without_retry_or_provider_switch(self):
        attempts=[]
        def uncertain(provider,prompt,port,wait):
            attempts.append((provider,port))
            raise TimeoutError("Gemini owned tab response not attributable")
        with self.assertRaises(TimeoutError):
            self._call(uncertain)
        self.assertEqual(attempts,[("gemini",9222)])
        claim=json.loads((self.out/"slide_001.one_submission.json").read_text())
        self.assertEqual(claim["status"],"MAY_HAVE_SUBMITTED_RECONCILE_BEFORE_RESEND")
        with self.assertRaisesRegex(RichMappingError,"already claimed"):
            self._call(uncertain)
        self.assertEqual(attempts,[("gemini",9222)])


if __name__=="__main__":
    unittest.main()
