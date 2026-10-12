"""Regression tests for Gemini PDF/TXT/JSON upload completion gate."""
import ast
import unittest
from pathlib import Path
from selenium_pipeline import runner


class Clock:
    def __init__(self): self.value=0.0
    def monotonic(self): return self.value
    def sleep(self,n): self.value+=n


class Driver:
    def __init__(self,states): self.states=states;self.calls=0
    def execute_script(self,_):
        i=min(self.calls,len(self.states)-1)
        self.calls+=1
        return self.states[i]


class DocumentUploadReadyTests(unittest.TestCase):
    def setUp(self):
        self.file=Path(runner.REPO)/"selenium_pipeline"/"vendor_template_v2"/"selenium.py"
        tree=ast.parse(self.file.read_text(encoding="utf-8"))
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
                and n.name=="_wait_for_gemini_document_upload_ready")
        self.clock=Clock()
        ns={"time":self.clock}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),
                     str(self.file),"exec"),ns)
        self.wait=ns[fn.name]
    def test_waits_for_all_three_document_previews(self):
        driver=Driver([
            {"previews":0,"loading":3,"errors":[]},
            {"previews":2,"loading":1,"errors":[]},
            {"previews":3,"loading":0,"errors":[]},
        ])
        self.wait(driver,3,timeout_s=3.0,stable_s=0.5)
        self.assertGreaterEqual(driver.calls,6)
    def test_does_not_pass_while_upload_is_busy(self):
        d=Driver([{"previews":3,"loading":1,"errors":[]}])
        with self.assertRaises(TimeoutError):
            self.wait(d,3,timeout_s=1.0)
    def test_does_not_accept_empty_document_previews(self):
        d=Driver([{"previews":0,"loading":0,"errors":[]}])
        with self.assertRaisesRegex(TimeoutError,"expected 3"):
            self.wait(d,3,timeout_s=1.0)
    def test_blocks_attachment_errors(self):
        d=Driver([{"previews":3,"loading":0,"errors":["Upload error"]}])
        with self.assertRaises(TimeoutError):
            self.wait(d,3,timeout_s=1.0)
    def test_uploader_actually_invokes_guard(self):
        source=ast.parse(self.file.read_text(encoding="utf-8"))
        cls=next(n for n in source.body
                 if isinstance(n,ast.ClassDef) and n.name=="GeminiSeleniumClient")
        fn=next(n for n in cls.body
                if isinstance(n,ast.FunctionDef) and n.name=="upload_files")
        calls=[n.func.id for n in ast.walk(fn)
               if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)]
        self.assertIn("_wait_for_gemini_document_upload_ready",calls)


if __name__=="__main__": unittest.main()
