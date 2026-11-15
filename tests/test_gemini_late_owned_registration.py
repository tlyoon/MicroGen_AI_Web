"""Read-only recovery of late Gemini owned-turn proof after one Send.

No browser, model, network, user prompt, or repeated Send.
"""
from __future__ import annotations
import unittest

from selenium_pipeline.gemini_selenium_only_policy import (
    reconcile_late_owned_gemini_registration,
)

BASELINE={"users":0,"models":0,"editor_length":1850,"route":"/app"}
UNVERIFIED={"status":"NO_POSITIVE_NEW_USER_TURN_AFTER_CLICK",
            "registered":False}

class FakeOwned:
    def __init__(self, *, users=0, models=0, editor=0, route="/app",
                 handle="owned", origin="https://gemini.google.com"):
        self.current_window_handle=handle
        self.current_url="https://gemini.google.com/app"
        self.data=dict(users=users,models=models,editor_length=editor,
                       route=route,origin=origin)
        self.scripts=0
    def execute_script(self,script):
        self.scripts+=1
        assert "users.size" in script and "models.length" in script
        return self.data

class LateOwnedRegistrationTests(unittest.TestCase):
    def test_model_finishes_after_early_window_no_resend(self):
        driver=FakeOwned(models=1)
        result=reconcile_late_owned_gemini_registration(
            driver,"owned",BASELINE,UNVERIFIED)
        self.assertEqual(result["status"],
                         "LATE_OWNED_NEW_MODEL_RESPONSE_AND_COMPOSER_CLEARED")
        self.assertTrue(result["registered"])
        self.assertEqual(driver.scripts,1)

    def test_new_user_turn_after_early_window(self):
        driver=FakeOwned(users=1,models=0)
        result=reconcile_late_owned_gemini_registration(
            driver,"owned",BASELINE,UNVERIFIED)
        self.assertTrue(result["registered"])
        self.assertIn("NEW_USER_TURN",result["status"])

    def test_new_route_after_early_window(self):
        driver=FakeOwned(route="/app/new-turn")
        result=reconcile_late_owned_gemini_registration(
            driver,"owned",BASELINE,UNVERIFIED)
        self.assertTrue(result["registered"])
        self.assertIn("NEW_CONVERSATION_ROUTE",result["status"])

    def test_stale_turn_or_uncleared_composer_not_accepted(self):
        for driver in (FakeOwned(), FakeOwned(models=1,editor=1850),
                       FakeOwned(models=1,handle="unrelated"),
                       FakeOwned(models=1,origin="https://evil.invalid")):
            with self.subTest(data=driver.data):
                result=reconcile_late_owned_gemini_registration(
                    driver,"owned",BASELINE,UNVERIFIED)
                self.assertEqual(result,UNVERIFIED)

    def test_earlier_positively_registered_response_unchanged(self):
        driver=FakeOwned(models=0)
        prior={"status":"NEW_USER_TURN_AND_COMPOSER_CLEARED",
               "registered":True}
        self.assertEqual(
            reconcile_late_owned_gemini_registration(
                driver,"owned",BASELINE,prior),prior)
        self.assertEqual(driver.scripts,0)

if __name__=="__main__":
    unittest.main()
