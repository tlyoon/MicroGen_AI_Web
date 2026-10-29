"""No additional Gemini submission during owned-tab timeout recovery."""
import unittest
from selenium_pipeline.gemini_response_recovery import poll_existing_owned_response


def snap(text="", generating=True, status="empty_model_response"):
    return {"text": text, "generating": generating, "capture_status": status}


class OwnedResponseGrace(unittest.TestCase):
    def test_pending_then_verified_complete_json(self):
        state = iter([snap(), snap('{"a": 1}', False, "visible_model_response")])
        observed = []
        def observe():
            x = next(state)
            observed.append(x)
            return x
        got, last = poll_existing_owned_response(
            observe, accept_fn=lambda raw: raw == '{"a": 1}',
            wait_s=5, poll_s=1,
            clock=lambda: len(observed)-1,
            sleep=lambda _: None)
        self.assertEqual(got, '{"a": 1}')
        self.assertEqual(last["generating"], False)
        self.assertEqual(len(observed), 2)

    def test_never_accept_json_while_generating(self):
        calls = []
        def observe():
            calls.append(1)
            return snap('{"seems":"complete"}', True, "visible_model_response")
        got, last = poll_existing_owned_response(
            observe, accept_fn=lambda _: True, wait_s=2,
            poll_s=1, clock=lambda: len(calls)-1,
            sleep=lambda _: None)
        self.assertIsNone(got)
        self.assertTrue(last["generating"])
        self.assertEqual(len(calls), 2)

    def test_changed_or_unowned_tab_fails_closed(self):
        seen = iter([snap(), snap('{"a":1}', False, "unavailable")])
        got, last = poll_existing_owned_response(
            lambda: next(seen), accept_fn=lambda _: True,
            wait_s=2,poll_s=1,clock=iter([0,0]).__next__,
            sleep=lambda _: None)
        self.assertIsNone(got)
        self.assertEqual(last["capture_status"],"unavailable")

    def test_completed_non_json_stays_untrusted(self):
        got, _ = poll_existing_owned_response(
            lambda: snap("Sorry, cannot fulfill this request.",False,
                         "visible_model_response"),
            accept_fn=lambda t: t.startswith("{"),
            wait_s=2)
        self.assertIsNone(got)

    def test_bad_snapshot_shape_rejected(self):
        got,_ = poll_existing_owned_response(
            lambda: {"text": '{"a":1}', "generating":False},
            accept_fn=lambda _:True,wait_s=2)
        self.assertIsNone(got)

    def test_unbounded_or_non_callable_parameters_rejected(self):
        for seconds in (0,91):
            with self.assertRaises(ValueError):
                poll_existing_owned_response(lambda: snap(),
                    accept_fn=lambda _:True,wait_s=seconds)


if __name__ == "__main__":
    unittest.main()
