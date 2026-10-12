"""Offline fault-injection tests for fail-closed Gemini figure mapping."""
from __future__ import annotations
import ast
import os
import tempfile
import types
import unittest
from pathlib import Path

from selenium_pipeline import runner


class DummyGemini:
    def __init__(self, _config):
        self.shutdown_called = False
    def start(self, ensure_gemini_on_launch=True):
        pass
    def shutdown(self):
        self.shutdown_called = True


class FigureMappingFailures(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        for i in (1,2):
            page=self.root/"pages"/f"page_{i}"
            crops=self.root/"crops"/f"page_{i}"
            page.mkdir(parents=True)
            crops.mkdir(parents=True)
            (page/f"page_{i}.png").write_bytes(b"page")
            (crops/"fig_1.png").write_bytes(b"crop")
        source=(Path(runner.REPO)/"selenium_pipeline"/"vendor_template_v2"/"map_and_rename_selenium_v8.py")
        tree=ast.parse(source.read_text(encoding="utf-8"))
        method=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=="run_mapping")
        module=ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[]))
        self.ns={
            "CFG":types.SimpleNamespace(root=self.root,pages_dir="pages",crops_dir="crops",gemini_url="url",
                 debug_port=9222, wait_mapping_max=120, chrome_exe=None,user_data_dir=None,
                 profile_directory=None,fallback_user_data_dir=None,fallback_profile_directory=None,
                 use_persistent_chrome=False,force_kill_chrome_to_free_port=False),
            "os":os,"Path":Path,"gemsel":types.SimpleNamespace(Config=lambda **kwargs:None,
                                    GeminiSeleniumClient=DummyGemini),
            "natural_sort_key":lambda value:value,
            "log":lambda *args:None,"log_timing":lambda *args:None,
            "GeminiGenerationStalled":type("GeminiGenerationStalled",(RuntimeError,),{}),
        }
        exec(compile(module,str(source),"exec"),self.ns)
    def run_mapping(self):
        self.ns["run_mapping"]("pages","crops",1,2,120,False,False)
    def test_a_failed_page_blocks_entire_figures_stage(self):
        def mock(_client,page,crops,**kwargs):
            if page.stem=="page_2": raise RuntimeError("Stale Gemini attachment")
            out=crops/"Figure_1.png";out.write_bytes(b"mapped");return None,[out]
        self.ns["map_and_rename_single_step"]=mock
        with self.assertRaisesRegex(RuntimeError,"incomplete for 1/2 page"):
            self.run_mapping()
    def test_zero_mapped_output_does_not_count_as_success(self):
        self.ns["map_and_rename_single_step"]=lambda *_args,**_kwargs:(None,[])
        with self.assertRaisesRegex(RuntimeError,"incomplete for 2/2 page"):
            self.run_mapping()
    def test_all_successful_mapping_pages_pass(self):
        def mock(_client,page,crops,**kwargs):
            out=crops/"Figure_1.png";out.write_bytes(b"mapped");return None,[out]
        self.ns["map_and_rename_single_step"]=mock
        self.run_mapping()
    def test_missing_full_page_is_a_failure(self):
        (self.root/"pages"/"page_2"/"page_2.png").unlink()
        self.ns["map_and_rename_single_step"]=lambda *_args,**_kwargs:(None,[self.root/"dummy.png"])
        with self.assertRaisesRegex(RuntimeError,"incomplete for 1/2 page"):
            self.run_mapping()


if __name__=="__main__":
    unittest.main()
