"""Real-incident analogue: 11-character 'Gemini said' after stopped generation.

No prompt resend, borrowed tab, inferred scientific approval or publication.
"""
import unittest
from selenium_pipeline.gemini_response_recovery import poll_existing_owned_response


def sample(text, generating=False, status="visible_model_response"):
    return {"text":text, "generating":generating, "capture_status":status}


class PlaceholderRecovery(unittest.TestCase):
    def test_stopped_short_placeholder_can_later_yield_owned_json(self):
        readings=iter([
            sample("Gemini said"),
            sample("Gemini said"),
            sample('{"probe":"microgen_source_transport_ok"}'),
        ])
        observations=[]
        def observe():
            item=next(readings)
            observations.append(item)
            return item
        recovered,last=poll_existing_owned_response(
            observe, accept_fn=lambda raw: raw=='{"probe":"microgen_source_transport_ok"}',
            wait_s=12,poll_s=2,clock=lambda:2*(len(observations)-1),
            sleep=lambda _:None)
        self.assertEqual(recovered,'{"probe":"microgen_source_transport_ok"}')
        self.assertEqual(len(observations),3)
        self.assertFalse(last["generating"])

    def test_placeholder_persisting_never_gets_accepted(self):
        seen=[]
        def observe():
            seen.append(1)
            return sample("Gemini said")
        found,last=poll_existing_owned_response(
            observe,accept_fn=lambda r:r.startswith("{"),
            wait_s=6,poll_s=2,clock=lambda:2*(len(seen)-1),
            sleep=lambda _:None)
        self.assertIsNone(found)
        self.assertEqual(last["text"],"Gemini said")
        self.assertGreaterEqual(len(seen),3)

    def test_owned_tab_lost_during_grace_fails_closed(self):
        states=iter([sample("Gemini said"),
                     sample('{"canary":true}',status="unavailable")])
        found,last=poll_existing_owned_response(
            lambda:next(states),accept_fn=lambda raw:raw.startswith('{'),
            wait_s=5,poll_s=1,clock=iter([0,0]).__next__,
            sleep=lambda _:None)
        self.assertIsNone(found)
        self.assertEqual(last["capture_status"],"unavailable")

    def test_never_accept_complete_json_while_still_generating(self):
        count=[]
        def observe():
            count.append(1)
            return sample('{"probe":"microgen_source_transport_ok"}',generating=True)
        found,_=poll_existing_owned_response(
            observe,accept_fn=lambda _:True,wait_s=4,poll_s=1,
            clock=lambda:len(count)-1,sleep=lambda _:None)
        self.assertIsNone(found)


if __name__ == "__main__":
    unittest.main()
