"""No-browser regression tests for safe Selenium owned-tab rotation."""
import ast
import unittest
from pathlib import Path
from typing import Optional

from selenium_pipeline import runner


class FakeSwitch:
    def __init__(self, driver): self.driver=driver
    def window(self, handle):
        if handle not in self.driver.handles:
            raise RuntimeError("no such window")
        self.driver.current=handle
        self.driver.events.append(("switch",handle))
    def new_window(self, kind):
        if self.driver.current not in self.driver.handles:
            raise RuntimeError("no such window: target window already closed")
        self.driver.counter+=1
        handle=f"owned-{self.driver.counter}"
        self.driver.handles.append(handle)
        self.driver.current=handle
        self.driver.events.append(("new",handle))


class FakeDriver:
    def __init__(self, handles, current):
        self.handles=list(handles)
        self.current=current
        self.counter=0
        self.events=[]
        self.switch_to=FakeSwitch(self)
        self.refuse_close=False
    @property
    def window_handles(self): return list(self.handles)
    @property
    def current_window_handle(self): return self.current
    def close(self):
        if self.refuse_close: raise RuntimeError("close temporarily unavailable")
        if self.current not in self.handles: raise RuntimeError("target already closed")
        self.handles.remove(self.current)
        self.events.append(("close",self.current))
        self.current=None


class TabRotationTests(unittest.TestCase):
    def setUp(self):
        file=Path(runner.REPO)/"selenium_pipeline"/"vendor_template_v2"/"selenium.py"
        tree=ast.parse(file.read_text(encoding="utf-8"))
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
                and n.name=="_rotate_owned_gemini_tab")
        ns={"Optional":Optional}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),
                     str(file),"exec"),ns)
        self.rotate=ns[fn.name]
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef)
                 and n.name=="GeminiSeleniumClient")
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef)
                    and n.name=="open_clean_gemini_chat")
        calls=[n.func.id for n in ast.walk(method)
               if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)]
        self.assertIn("_rotate_owned_gemini_tab",calls)

    def test_keeps_borrowed_tab_and_replaces_owned_tab(self):
        d=FakeDriver(["borrowed","old-owned"],"old-owned")
        current=self.rotate(d,"old-owned")
        self.assertEqual(d.window_handles,["borrowed",current])
        self.assertEqual(d.current,current)
        self.assertLess(d.events.index(("new",current)),
                        d.events.index(("close","old-owned")))

    def test_first_tab_creation_does_not_close_borrowed_tab(self):
        d=FakeDriver(["borrowed"],"borrowed")
        current=self.rotate(d,None)
        self.assertIn("borrowed",d.window_handles)
        self.assertIn(current,d.window_handles)
        self.assertEqual(d.current,current)

    def test_recovers_when_previous_owned_tab_was_closed_externally(self):
        d=FakeDriver(["borrowed"],"stale-tab")
        current=self.rotate(d,"stale-tab")
        self.assertEqual(d.current,current)
        self.assertEqual(d.window_handles,["borrowed",current])

    def test_cleanup_failure_keeps_new_browser_target(self):
        d=FakeDriver(["borrowed","old-owned"],"old-owned")
        d.refuse_close=True
        with self.assertRaisesRegex(RuntimeError,"close temporarily unavailable"):
            self.rotate(d,"old-owned")
        self.assertTrue(d.current.startswith("owned-"))
        self.assertIn("borrowed",d.window_handles)

    def test_no_live_tab_fails_without_closing_other_browser(self):
        d=FakeDriver([],"stale")
        with self.assertRaisesRegex(RuntimeError,"no live tab"):
            self.rotate(d,"stale")


if __name__=="__main__": unittest.main()
