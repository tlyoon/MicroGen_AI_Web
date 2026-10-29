import tempfile,unittest,json
from pathlib import Path
from selenium_pipeline.one_shot_gemini_source_health_probe import (
    run_one_health_probe,make_source_sized_probe,EXPECTED)
from selenium_pipeline.scoped_original_math_review_window import (
    create_window,inspect_window)
from test_scoped_original_math_review_window import (
    original_fixture,CONSENT)

def setup_window(path):
    f,q=original_fixture(path)
    w=Path(path)/"separate_window"
    create_window(original_folder=f,queue_root=q,window_root=w,
                  approval_reference=CONSENT,now=1000)
    return f,q,w

def good(_):
    return {"raw":json.dumps(EXPECTED),"same_owned_gemini_session":True,
            "model_stopped_generating":True}

class OneShot(unittest.TestCase):
 def test_sized_transport_and_verified_exact_json(self):
    text=make_source_sized_probe()
    self.assertGreaterEqual(len(text),1200)
    self.assertLessEqual(len(text),3000)
    with tempfile.TemporaryDirectory() as d:
        f,q,w=setup_window(d);called=[]
        result=run_one_health_probe(window_root=w,
             transport=lambda x:(called.append(x),good(x))[1],now=1000)
        self.assertEqual(result["status"],"GEMINI_TRANSPORT_HEALTH_VERIFIED")
        self.assertEqual(len(called),1)
        self.assertTrue(inspect_window(window_root=w,now=1000)
                        ["eligible_for_single_authorized_dispatch"])
        second=run_one_health_probe(window_root=w,transport=good,now=1001)
        self.assertFalse(second["model_request_sent"])
 def test_failed_transport_is_cooldown_not_math_attempt(self):
    with tempfile.TemporaryDirectory() as d:
        f,q,w=setup_window(d);count=[]
        def fail(_):
            count.append(1)
            raise TimeoutError("Owned tab still generating")
        result=run_one_health_probe(window_root=w,transport=fail,now=1000)
        self.assertEqual(result["status"],"GEMINI_TRANSPORT_STILL_UNHEALTHY")
        self.assertFalse(inspect_window(window_root=w,now=1000)
                         ["eligible_for_single_authorized_dispatch"])
        self.assertEqual(run_one_health_probe(window_root=w,transport=fail,now=2000)
                         ["status"],"HEALTH_PROBE_COOLDOWN")
        self.assertEqual(count,[1])
        result=run_one_health_probe(window_root=w,transport=good,now=5000)
        self.assertEqual(result["status"],"GEMINI_TRANSPORT_HEALTH_VERIFIED")
        self.assertEqual(inspect_window(window_root=w)["new_window_confirmed_submissions"],0)
 def test_unowned_or_bad_json_never_writes_success_receipt(self):
    with tempfile.TemporaryDirectory() as d:
        f,q,w=setup_window(d)
        outcome=run_one_health_probe(window_root=w,
           transport=lambda _ :{"raw":"not JSON",
             "same_owned_gemini_session":False,"model_stopped_generating":True},
           now=1000)
        self.assertEqual(outcome["status"],"GEMINI_TRANSPORT_STILL_UNHEALTHY")
        self.assertFalse((w/"source_transport_health.json").exists())
 def test_unresolved_previous_probe_prevents_another_one(self):
    with tempfile.TemporaryDirectory() as d:
        f,q,w=setup_window(d)
        (w/"health_attempts.jsonl").write_text(
            json.dumps({"event":"HEALTH_PROBE_BEGIN","at":1000,
                        "id":"unknown-remote-request"})+"\n")
        x=run_one_health_probe(window_root=w,transport=lambda _:self.fail(),now=5000)
        self.assertEqual(x["status"],"PREVIOUS_HEALTH_PROBE_UNRESOLVED")
 def test_occupied_probe_lock_never_stolen(self):
    with tempfile.TemporaryDirectory() as d:
        f,q,w=setup_window(d)
        lock=w/"health_probe.claimlock";lock.write_text("other process")
        with self.assertRaises(FileExistsError):
            run_one_health_probe(window_root=w,transport=good,now=1000)
        self.assertTrue(lock.exists())
