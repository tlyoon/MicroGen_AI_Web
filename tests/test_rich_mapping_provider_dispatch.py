"""Windows no-network provider readiness and exactly-once model-response tests.

Uses physical synthetic PDF source/author bytes, real frozen worklist, safe
prose fallback and unresolved-only queue. Mock only the external provider UI
and model response: no real paid generation or browser/tab navigation.
"""
from __future__ import annotations
import json
import os
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
        # A fresh, isolated *machine-global* claim directory per test. The
        # production dispatcher always uses canonical LOCALAPPDATA; changing
        # --attempt-root cannot reset its once-only source claim.
        self.local_appdata=self.root/"LOCALAPPDATA"
        self.local_appdata.mkdir()
        environment=patch.dict(os.environ,{"LOCALAPPDATA":str(self.local_appdata)})
        environment.start()
        self.addCleanup(environment.stop)
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

    def test_real_transport_scopes_rich_model_fallback_and_restores_env(self):
        from selenium_pipeline.rich_mapping_provider_dispatch import _real_transport
        from selenium_pipeline.series_gemini import OwnedGeminiResponse
        watched=("MICROGEN_ACTIVE_GENERATION_STAGE",
                 "MICROGEN_GEMINI_UI_MODE","MICROGEN_LLM_MODEL",
                 "MICROGEN_GEMINI_THINKING_LEVEL",
                 "MICROGEN_MODEL_ROUTE_REASON",
                 "MICROGEN_MODEL_ROUTE_REQUESTED",
                 "MICROGEN_MODEL_ROUTE_OFFERED")
        before={name:os.environ.get(name) for name in watched}
        seen=[]
        def owned_only(prompt,attachments,*,port,wait_cap_s,min_chars,
                       accept_fn):
            seen.append((os.environ.get("MICROGEN_ACTIVE_GENERATION_STAGE"),
                         os.environ.get("MICROGEN_GEMINI_THINKING_LEVEL"),
                         port,wait_cap_s))
            # Mimic an independently verified *owned-tab* adapter event,
            # not a provider call or scientific approval.
            os.environ["MICROGEN_GEMINI_UI_MODE"]="pro"
            os.environ["MICROGEN_LLM_MODEL"]="gemini-3.1-pro"
            os.environ["MICROGEN_MODEL_ROUTE_REASON"]=(
                "EXACT_PREFERRED_ABSENT_STAGE_COMPATIBLE_FALLBACK")
            return OwnedGeminiResponse(
                '{"slide":1}',registration_status="NEW_TURN_REGISTERED",
                new_turn_verified=True)
        with patch("selenium_pipeline.series_gemini._browser_request",
                   side_effect=owned_only):
            result=_real_transport("gemini","synthetic prompt",9222,25)
        self.assertEqual(seen[0][0],"rich_mapping")
        self.assertIn(seen[0][1],("medium","high"))
        self.assertEqual(result.rich_ui_family_verified,"pro")
        self.assertEqual(result.rich_thinking_verified,seen[0][1])
        self.assertEqual(result.rich_fallback_reason,
                         "EXACT_PREFERRED_ABSENT_STAGE_COMPATIBLE_FALLBACK")
        self.assertEqual({name:os.environ.get(name)for name in watched},before)

    def test_rich_transport_concurrent_environment_stress(self):
        from concurrent.futures import ThreadPoolExecutor
        from time import sleep
        from selenium_pipeline.rich_mapping_provider_dispatch import _real_transport
        from selenium_pipeline.series_gemini import OwnedGeminiResponse
        watched=("MICROGEN_ACTIVE_GENERATION_STAGE",
                 "MICROGEN_GEMINI_THINKING_LEVEL",
                 "MICROGEN_GEMINI_UI_MODE",
                 "MICROGEN_LLM_MODEL",
                 "MICROGEN_MODEL_ROUTE_REASON")
        seen=[]
        def owned_only(prompt,attachments,*,port,wait_cap_s,min_chars,
                       accept_fn):
            before=(os.getenv("MICROGEN_ACTIVE_GENERATION_STAGE"),
                    os.getenv("MICROGEN_GEMINI_THINKING_LEVEL"),
                    os.getenv("MICROGEN_GEMINI_UI_MODE"),
                    os.getenv("MICROGEN_LLM_MODEL"),
                    os.getenv("MICROGEN_MODEL_ROUTE_REASON"))
            # Simulate a verified Pro/High vendor fallback while another
            # rich mapping worker is trying to enter its own model stage.
            os.environ["MICROGEN_GEMINI_UI_MODE"]="pro"
            os.environ["MICROGEN_GEMINI_THINKING_LEVEL"]="high"
            os.environ["MICROGEN_MODEL_ROUTE_REASON"]="VERIFIED_HIGH_FALLBACK"
            sleep(0.002)
            seen.append((prompt,before,os.getenv("MICROGEN_GEMINI_UI_MODE")))
            return OwnedGeminiResponse(
                '{"slide":1}',registration_status="NEW_TURN_REGISTERED",
                new_turn_verified=True)
        with patch.dict(os.environ,{"MICROGEN_ACTIVE_GENERATION_STAGE":"figures",
                                    "MICROGEN_GEMINI_THINKING_LEVEL":"low",
                                    "MICROGEN_GEMINI_UI_MODE":"flash-lite"}):
            before={name:os.environ.get(name) for name in watched}
            with patch("selenium_pipeline.series_gemini._browser_request",
                       side_effect=owned_only):
                with ThreadPoolExecutor(max_workers=8) as pool:
                    results=list(pool.map(
                        lambda i:_real_transport("gemini",str(i),9222,25),
                        range(64)))
            self.assertEqual(
                {name:os.environ.get(name) for name in watched},before)
        self.assertEqual(len(seen),64)
        self.assertTrue(all(stage=="rich_mapping" and effort=="medium"
                            and requested_family=="flash"
                            and requested_model=="gemini-3.8-flash"
                            and previous_route is None and family=="pro"
                            for _,(stage,effort,requested_family,
                                   requested_model,previous_route),family in seen))
        self.assertTrue(all(r.rich_ui_family_verified=="pro"
                            and r.rich_thinking_verified=="high"
                            and r.gemini_new_user_turn_verified
                            for r in results))

    def test_rich_transport_presend_failure_restores_environment(self):
        from selenium_pipeline.rich_mapping_provider_dispatch import _real_transport
        watched=("MICROGEN_ACTIVE_GENERATION_STAGE",
                 "MICROGEN_GEMINI_THINKING_LEVEL",
                 "MICROGEN_GEMINI_UI_MODE")
        with patch.dict(os.environ,{"MICROGEN_ACTIVE_GENERATION_STAGE":"figures",
                                    "MICROGEN_GEMINI_THINKING_LEVEL":"low",
                                    "MICROGEN_GEMINI_UI_MODE":"flash-lite"}):
            before={name:os.environ.get(name) for name in watched}
            with patch("selenium_pipeline.series_gemini._browser_request",
                       side_effect=RuntimeError("pre-send UI unavailable")):
                with self.assertRaisesRegex(RuntimeError,"pre-send UI"):
                    _real_transport("gemini","test",9222,25)
            self.assertEqual({name:os.environ.get(name) for name in watched},
                             before)

    def test_no_direct_chatgpt_or_api_generation_transport(self):
        from selenium_pipeline.rich_mapping_provider_dispatch import _real_transport
        for name,port in (("chatgpt",9223),("api",9222)):
            with self.subTest(name=name):
                with self.assertRaisesRegex(RichMappingError,
                                             "sole supported LLM generation route"):
                    _real_transport(name,"synthetic prompt",port,12)

    def _canonical_global_claim(self):
        from selenium_pipeline.figure_source_identity import _sha
        return (self.local_appdata/"MicroGen_AI_Web_Checkpoints"/
                ".microgen_rich_mapping_once"/_sha(self.source)/
                "slide_001.once.json")

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
        global_claim=self._canonical_global_claim()
        self.assertTrue(global_claim.is_file())
        self.assertEqual(json.loads(global_claim.read_text())["status"],
                         "MAY_HAVE_SUBMITTED_RECONCILE_BEFORE_RESEND")
        with self.assertRaisesRegex(RichMappingError,"already claimed"):
            self._call(uncertain)
        # A new caller attempt directory does NOT reset the shared claim.
        second_root=self.root/"alternate_attempt_root"
        second_root.mkdir()
        with self.assertRaisesRegex(RichMappingError,
                                    "Source-global original slide already claimed"):
            dispatch_one(source_folder=self.original,checkpoint=self.ck,
                         fallback_dir=self.fallback,queue_folder=self.queue,
                         slide=1,attempt_root=second_root,
                         provider_statuses=self.provider,transport=uncertain,
                         wait_cap_s=12)
        self.assertEqual(list(second_root.iterdir()),[])
        self.assertEqual(attempts,[("gemini",9222)])

    def test_successful_response_claim_cannot_replay_from_new_attempt_directory(self):
        sent=[]
        first=self._call(lambda *args:(sent.append(args),self.reply())[1])
        global_claim=self._canonical_global_claim()
        self.assertEqual(first["status"],"CAPTURED_SOURCE_VERIFIED_REVIEW_ONLY")
        self.assertTrue(global_claim.is_file())
        self.assertEqual(json.loads(global_claim.read_text())["status"],
                         "CAPTURED_SOURCE_VERIFIED_REVIEW_ONLY")
        alternate=self.root/"new_session_attempt"
        alternate.mkdir()
        with self.assertRaisesRegex(RichMappingError,
                                    "Source-global original slide already claimed"):
            dispatch_one(source_folder=self.original,checkpoint=self.ck,
                         fallback_dir=self.fallback,queue_folder=self.queue,
                         slide=1,attempt_root=alternate,
                         provider_statuses=self.provider,
                         transport=lambda *args:(_ for _ in ()).throw(
                             AssertionError("One-time Send was already captured")),
                         wait_cap_s=12)
        self.assertEqual(len(sent),1)
        self.assertFalse(any(alternate.iterdir()))

    def test_absent_gemini_never_creates_source_global_claim(self):
        status=[{"provider":"gemini","debug_port":9222,
                 "status":"BROWSER_UNAVAILABLE",
                 "authenticated_ui_ready":False,
                 "model_submission_performed":False}]
        result=self._call(None,providers=status)
        self.assertEqual(result["model_submissions"],0)
        self.assertFalse(self._canonical_global_claim().exists())

    def test_concurrent_new_attempt_roots_have_one_atomic_global_winner(self):
        from concurrent.futures import ThreadPoolExecutor
        import threading
        alternate=self.root/"competing_attempt_root"
        alternate.mkdir()
        submitted=[]
        lock=threading.Lock()

        def transport(*args):
            with lock:
                submitted.append(args)
            return self.reply()

        def call(attempt_root):
            try:
                return dispatch_one(
                    source_folder=self.original,checkpoint=self.ck,
                    fallback_dir=self.fallback,queue_folder=self.queue,
                    slide=1,attempt_root=attempt_root,
                    provider_statuses=self.provider,
                    transport=transport,wait_cap_s=12)
            except RichMappingError as exc:
                return {"status":"GLOBAL_DUPLICATE_DENIED","error":str(exc)}

        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(call,[self.out,alternate]))
        self.assertEqual(len(submitted),1)
        self.assertEqual(
            sorted(row["status"] for row in results),
            ["CAPTURED_SOURCE_VERIFIED_REVIEW_ONLY",
             "GLOBAL_DUPLICATE_DENIED"])
        self.assertEqual(json.loads(self._canonical_global_claim().read_text())[
                         "status"],"CAPTURED_SOURCE_VERIFIED_REVIEW_ONLY")

    def test_distinct_publisher_sha_gets_a_distinct_global_scope(self):
        # Truly new source bytes need a fresh source mapping checkpoint and
        # independent queue; changing the caller's attempt folder alone does
        # not count as a new source.
        first=self._call(lambda *args:self.reply())
        self.assertEqual(first["status"],"CAPTURED_SOURCE_VERIFIED_REVIEW_ONLY")
        old_claim=self._canonical_global_claim()
        self.assertTrue(old_claim.is_file())
        from selenium_pipeline.rich_mapping_provider_dispatch import _global_slide_claim
        fake_different_sha="a"*64
        new_path=_global_slide_claim(
            source_sha256=fake_different_sha,slide=1,
            source_folder=self.original,queue_folder=self.queue)
        self.assertNotEqual(new_path,old_claim)
        self.assertFalse(new_path.exists())
        self.assertTrue(old_claim.is_file())

    def _academic_claim(self,identifiers):
        from selenium_pipeline.figure_source_identity import _sha
        digest=_sha(self.source)
        folder=(self.local_appdata/"MicroGen_AI_Web_Checkpoints"/
                ".microgen_academic_source_once"/digest)
        folder.mkdir(parents=True,exist_ok=True)
        h="d"*64
        (folder/(h+".json")).write_text(json.dumps({
            "schema_version":1,
            "type":"THIRD_PASS_CHANGED_SOURCE_REVIEW",
            "source_sha256":digest,
            "utterance_ids":identifiers,
            "request_sha256":h,
        }),encoding="utf8")
        return folder

    def test_previously_academic_claimed_only_unit_stops_before_send(self):
        req=json.loads((self.queue/"slide_001.unresolved_request.json").read_text("utf8"))
        ident=req["only_unresolved_original_utterances"][0]["utterance_id"]
        self._academic_claim([ident])
        called=[]
        result=self._call(lambda *args:called.append(args))
        self.assertEqual(result["status"],
            "ALL_UNRESOLVED_SLIDE_UNITS_PREVIOUSLY_ACADEMIC_CLAIMED_NO_SEND")
        self.assertEqual(result["academic_claimed_units_excluded"],1)
        self.assertEqual(result["new_eligible_utterances"],0)
        self.assertEqual(called,[])
        self.assertEqual(list(self.out.iterdir()),[])
        self.assertFalse(self._canonical_global_claim().exists())

    def _add_second_unreviewed_math_unit(self):
        prose="The experiment provides evidence for the observed physical process."
        math1="For tangent substitution, x equals a times tangent theta."
        math2="For secant substitution, y equals b times secant theta."
        for path,with_vector in ((self.source,False),(self.slides,True)):
            with pymupdf.open() as pdf:
                page=pdf.new_page()
                for i,words in enumerate((prose,math1,math2)):
                    page.insert_text((70,85+43*i),words)
                if with_vector:
                    page.draw_line((70,250),(240,220))
                pdf.save(path)
        self.script.write_text(
            "**Slide 1 [14 seconds]:\n"+prose+" "+math1+" "+math2,
            encoding="utf8")
        root=self.root/"second_original_sha_cache"
        root.mkdir()
        with self.assertRaises(ElementMappingCheckpointBlocked):
            require_automatic_mapping_or_checkpoint(
                source=self.source,slides=self.slides,script=self.script,
                checkpoint_root=root)
        self.ck=next(root.glob("rich_element_map_*"))
        self.fallback=self.root/"second_accepted_source_prose"
        stage_section(source_folder=self.original,checkpoint=self.ck,
                      destination=self.fallback)
        self.queue=self.root/"second_unresolved_only"
        prepare_queue(source_folder=self.original,checkpoint=self.ck,
                      fallback_dir=self.fallback,destination=self.queue)
        self.original_bytes=[x.read_bytes() for x in
                             (self.source,self.slides,self.script)]

    def test_shared_academic_claim_filters_only_old_unit_then_merges_null(self):
        self._add_second_unreviewed_math_unit()
        req=json.loads((self.queue/"slide_001.unresolved_request.json").read_text("utf8"))
        units=req["only_unresolved_original_utterances"]
        self.assertEqual(len(units),2)
        old_id,new_id=(u["utterance_id"] for u in units)
        self._academic_claim([old_id])
        seen=[]
        def only_unclaimed(provider,prompt,port,wait):
            task=json.loads(prompt.split("\n\n")[-1])
            selected=task["only_unresolved_original_utterances"]
            self.assertEqual([x["utterance_id"] for x in selected],[new_id])
            self.assertNotIn(old_id,prompt)
            self.assertNotEqual(task["partial_request_sha256"],
                                req["partial_request_sha256"])
            seen.append((provider,port))
            return json.dumps({
                "slide":1,
                "partial_request_sha256":task["partial_request_sha256"],
                "associations":[{
                    "utterance_id":new_id,
                    "target_id":None,"source_page":None,
                    "source_quote":None,"needs_review":True,
                    "reason":"Exact independent math evidence not available"}],
            })
        record=self._call(only_unclaimed)
        self.assertEqual(record["status"],"CAPTURED_SOURCE_VERIFIED_REVIEW_ONLY")
        self.assertEqual(record["requested_utterances"],1)
        self.assertEqual(record["prior_academic_claimed_original_units_excluded"],1)
        self.assertEqual(seen,[("gemini",9222)])
        merged=json.loads((self.out/"slide_001.merged_response.json").read_text("utf8"))
        associations={x["utterance_id"]:x for x in merged["associations"]}
        self.assertIsNone(associations[old_id]["target_id"])
        self.assertTrue(associations[old_id]["needs_review"])
        self.assertIn("Prior source-global academic claim",
                      associations[old_id]["reason"])
        self.assertIsNone(associations[new_id]["target_id"])
        self.assertFalse(merged["student_publication_authorized"])
        self.assertEqual(self.original_bytes,[x.read_bytes() for x in
                             (self.source,self.slides,self.script)])

    def test_claim_appearing_during_provider_preflight_stops_without_send(self):
        req=json.loads((self.queue/"slide_001.unresolved_request.json").read_text("utf8"))
        uid=req["only_unresolved_original_utterances"][0]["utterance_id"]
        from selenium_pipeline.rich_mapping_provider_readiness import (
            choose_provider as ordinary_choose)
        def claim_during_readiness(rows):
            self._academic_claim([uid])
            return ordinary_choose(rows)
        attempts=[]
        with patch("selenium_pipeline.rich_mapping_provider_dispatch."
                   "choose_provider",side_effect=claim_during_readiness):
            with self.assertRaisesRegex(RichMappingError,
                                        "claimed while provider preflight"):
                self._call(lambda *args:attempts.append(args))
        self.assertEqual(attempts,[])
        self.assertFalse(self._canonical_global_claim().exists())
        self.assertEqual(list(self.out.iterdir()),[])

    def test_rejects_untrusted_academic_claim_instead_of_sending(self):
        req=json.loads((self.queue/"slide_001.unresolved_request.json").read_text("utf8"))
        identifier=req["only_unresolved_original_utterances"][0]["utterance_id"]
        folder=self._academic_claim([identifier])
        target=next(folder.glob("*.json"))
        invalid=json.loads(target.read_text("utf8"))
        invalid["source_sha256"]="f"*64
        target.write_text(json.dumps(invalid),encoding="utf8")
        called=[]
        with self.assertRaises((ValueError,RichMappingError)):
            self._call(lambda *args:called.append(args))
        self.assertEqual(called,[])
        self.assertFalse(self._canonical_global_claim().exists())

    def test_symlinked_source_claim_index_fails_before_any_provider_send(self):
        from selenium_pipeline.figure_source_identity import _sha
        root=self.local_appdata/"MicroGen_AI_Web_Checkpoints"
        root.mkdir()
        sibling=self.root/"foreign"
        sibling.mkdir()
        try:
            (root/".microgen_rich_mapping_once").symlink_to(
                sibling,target_is_directory=True)
        except (NotImplementedError,OSError):
            self.skipTest("Windows does not permit creation of directory symlinks")
        sent=[]
        with self.assertRaisesRegex(RichMappingError,
                                    "Unsafe global original-slide claim index"):
            self._call(lambda *args:sent.append(args))
        self.assertEqual(sent,[])
        self.assertFalse((sibling/_sha(self.source)).exists())


class DellRealAcademicAndRichScopeTests(unittest.TestCase):
    def test_real_original_queue_never_resubmits_academic_claimed_units(self):
        from selenium_pipeline.figure_source_identity import _sha
        from selenium_pipeline.rich_unresolved_model_queue import verify_queue
        from selenium_pipeline.rich_mapping_provider_dispatch import (
            _academic_unclaimed_scope,_global_slide_claim)
        root=Path.home()/"AppData"/"Local"/"MicroGen_AI_Web_Checkpoints"
        folder=(root/"20261112_PR528_G2_SERWAY6_4_NARRATION_SOURCE_REUSE_V7"/
                "source_tree"/"6"/"6.4")
        checkpoint=(root/"20261113_G2_RICH_MATH_RECOVERY_CHECKPOINT_V5"/
                    "rich_element_map_945d5c66ec52f0bcb2c34513")
        fallback=root/"20261113_G2_SERWAY64_SAFE_PROSE_VERIFIED_7OF74_V1"
        queue=root/"20261113_G2_SERWAY64_UNRESOLVED_ONLY_RICH_QUEUE_67OF74_V1"
        if not all(x.exists() for x in
                   (folder/"source.pdf",checkpoint,fallback,queue)):
            self.skipTest("Original Serway §6.4 only on authorized Dell-115")
        before={x:_sha(folder/x)for x in
                ("source.pdf","slides.pdf","script.txt")}
        manifest,_,rows=verify_queue(
            source_folder=folder,checkpoint=checkpoint,
            fallback_dir=fallback,queue_folder=queue)
        self.assertEqual(manifest["source_inputs_sha256"]["source.pdf"],
                         before["source.pdf"])
        pending=excluded=eligible=0
        for slide,request in enumerate(rows,1):
            global_claim=_global_slide_claim(
                source_sha256=before["source.pdf"],slide=slide,
                source_folder=folder,queue_folder=queue)
            proposed,old=_academic_unclaimed_scope(
                pending=request,source_sha256=before["source.pdf"],
                checkpoint_parent=global_claim.parent.parent.parent)
            ids=[x["utterance_id"]for x in
                 proposed["only_unresolved_original_utterances"]]
            self.assertFalse(set(ids)&set(old))
            self.assertEqual(
                len(ids)+len(old),
                len(request["only_unresolved_original_utterances"]))
            pending+=len(request["only_unresolved_original_utterances"])
            excluded+=len(old)
            eligible+=len(ids)
        self.assertEqual(pending,manifest["only_unresolved_utterances_requested"])
        self.assertEqual(pending,excluded+eligible)
        self.assertEqual(before,{x:_sha(folder/x)for x in before})


if __name__=="__main__":
    unittest.main()
