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
