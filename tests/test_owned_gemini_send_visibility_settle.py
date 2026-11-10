import unittest
from selenium_pipeline.gemini_response_recovery import await_owned_gemini_send_visible

class Fake:
 def __init__(self,states,handle="owned",url="https://gemini.google.com/app"):
  self.states=iter(states);self.current_window_handle=handle;self.current_url=url
 def execute_script(self,js):
  return next(self.states)
def state(visible):
 return {"doc_visible":True,"composer_present":True,"send_count":1,
         "visible_send_count":1 if visible else 0}
class Settle(unittest.TestCase):
 def test_quill_async_send_is_only_accepted_when_visible(self):
  c=[0]
  def clock():return c[0]
  def sleep(t):c[0]+=t
  driver=Fake([state(False),state(False),state(True)])
  self.assertTrue(await_owned_gemini_send_visible(driver,"owned",
     wait_s=6,poll_s=1,clock=clock,sleep=sleep))
  self.assertEqual(c[0],2)
 def test_quill_editor_and_send_control_may_both_arrive_late(self):
  # Real academic review previously failed before Send after three browser
  # prepares: do not treat the first empty Quill render as terminal.
  c=[0]
  def clock():return c[0]
  def sleep(t):c[0]+=t
  empty={"doc_visible":True,"composer_present":False,
         "send_count":0,"visible_send_count":0}
  editor={"doc_visible":True,"composer_present":True,
          "send_count":0,"visible_send_count":0}
  driver=Fake([empty,editor,state(True)])
  self.assertTrue(await_owned_gemini_send_visible(driver,"owned",
      wait_s=3,poll_s=0.5,clock=clock,sleep=sleep))
  self.assertEqual(c[0],1.0)

 def test_shared_composer_selectors_include_quill_not_just_role_textbox(self):
  class Inspecting(Fake):
   def execute_script(self,js):
    self.assertion=js
    return state(True)
  driver=Inspecting([state(True)])
  self.assertTrue(await_owned_gemini_send_visible(driver,"owned",
      wait_s=0,poll_s=0.5))
  self.assertIn('div.ql-editor[contenteditable="true"]',driver.assertion)
  self.assertIn('[contenteditable="true"][role="textbox"]',driver.assertion)
  self.assertIn("!b.disabled",driver.assertion)
  self.assertIn("aria-disabled",driver.assertion)

 def test_multiple_eligible_buttons_fail_closed(self):
  s=state(True);s["send_count"]=2;s["visible_send_count"]=2
  self.assertFalse(await_owned_gemini_send_visible(Fake([s]),"owned"))

 def test_hidden_stays_hidden_no_submission(self):
  c=[0]
  def clock():return c[0]
  def sleep(t):c[0]+=t
  driver=Fake([state(False)]*12)
  self.assertFalse(await_owned_gemini_send_visible(driver,"owned",
     wait_s=3,poll_s=1,clock=clock,sleep=sleep))
 def test_foreign_tab_and_non_gemini_page_rejected(self):
  self.assertFalse(await_owned_gemini_send_visible(Fake([state(True)]),"wrong"))
  self.assertFalse(await_owned_gemini_send_visible(
      Fake([state(True)],url="https://example.com"),"owned"))
 def test_composer_missing_is_not_assumed_ready(self):
  st=state(True);st["composer_present"]=False
  self.assertFalse(await_owned_gemini_send_visible(Fake([st]),"owned"))
