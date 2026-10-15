"""Gemini focus emulation applies only to verified owned tabs."""
import unittest
from unittest.mock import patch
from selenium_pipeline.series_gemini import _vendor_module

class Dummy:
    current_window_handle="owned"
    def __init__(self,visibility="hidden",activate=True,error=False):
        self.visibility=visibility
        self.activate=activate
        self.error=error
        self.calls=[]
    def execute_script(self,script,*args):
        self.calls.append(("script",script))
        if script=="return document.visibilityState":return self.visibility
        raise AssertionError("Unknown script")
    def execute_cdp_cmd(self,name,args):
        self.calls.append(("cdp",name,args))
        if self.error:raise RuntimeError("Unavailable")
        if name!="Emulation.setFocusEmulationEnabled":raise AssertionError(name)
        if args=={"enabled":True} and self.activate:self.visibility="visible"
        return {}

def client(driver,owned="owned"):
    v=_vendor_module()
    c=v.GeminiSeleniumClient.__new__(v.GeminiSeleniumClient)
    c.driver=driver
    c._automation_tab=owned
    c._owned_tab_focus_emulated=False
    return c

class OwnedTabFocusTests(unittest.TestCase):
    def test_visible_skips_emulation(self):
        d=Dummy(visibility="visible");c=client(d)
        self.assertEqual(c._ensure_owned_tab_visible(),"already_visible")
        self.assertFalse(any(x[0]=="cdp" for x in d.calls))
        self.assertFalse(c._owned_tab_focus_emulated)

    def test_hidden_is_restored(self):
        d=Dummy();c=client(d)
        self.assertEqual(c._ensure_owned_tab_visible(),"focused_owned_tab")
        self.assertTrue(c._owned_tab_focus_emulated)
        self.assertEqual(d.calls[-2:],[("cdp","Emulation.setFocusEmulationEnabled",{"enabled":True}),
            ("script","return document.visibilityState")])

    def test_wrong_tab_never_touched(self):
        d=Dummy();d.current_window_handle="borrowed";c=client(d)
        with self.assertRaisesRegex(RuntimeError,"unowned"):
            c._ensure_owned_tab_visible()
        self.assertFalse(d.calls)

    def test_no_owned_tab_fails(self):
        d=Dummy();c=client(d,owned=None)
        with self.assertRaisesRegex(RuntimeError,"no owned tab"):
            c._ensure_owned_tab_visible()
        self.assertFalse(d.calls)

    def test_cdp_unsupported_fails_closed(self):
        d=Dummy(error=True);c=client(d)
        with self.assertRaisesRegex(RuntimeError,"focus emulation failed"):
            c._ensure_owned_tab_visible()
        self.assertFalse(c._owned_tab_focus_emulated)

    def test_unresponsive_page_fails_closed(self):
        d=Dummy(activate=False);c=client(d)
        with patch("time.sleep",lambda _:None):
            with self.assertRaisesRegex(RuntimeError,"remained background-hidden"):
                c._ensure_owned_tab_visible(wait_s=0)
        self.assertTrue(c._owned_tab_focus_emulated)

    def test_other_state_rejected(self):
        d=Dummy(visibility="prerender");c=client(d)
        with self.assertRaisesRegex(RuntimeError,"Unexpected"):
            c._ensure_owned_tab_visible()
        self.assertFalse(any(x[0]=="cdp" for x in d.calls))

    def test_cleanup_disables_focus_and_closes_only_owned_tab(self):
        class Closing(Dummy):
            window_handles=["owned","borrowed"]
            @property
            def switch_to(self):
                class Switch:
                    def __init__(self,outer):self.outer=outer
                    def window(self,handle):self.outer.current_window_handle=handle
                return Switch(self)
            def close(self):
                self.calls.append(("close",self.current_window_handle))
                self.window_handles.remove(self.current_window_handle)
            def quit(self):self.calls.append(("quit",))
        d=Closing();c=client(d);c._owned_tab_focus_emulated=True
        c._launched_profile_dir=None
        c.shutdown()
        self.assertIn(("cdp","Emulation.setFocusEmulationEnabled",{"enabled":False}),d.calls)
        self.assertIn(("close","owned"),d.calls)
        self.assertIn("borrowed",d.window_handles)
        self.assertFalse(c._owned_tab_focus_emulated)

if __name__=="__main__":
    unittest.main()
