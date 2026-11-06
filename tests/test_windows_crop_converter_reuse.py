"""Source-free physical crop-script regression: no Docling/Gemini required."""
from __future__ import annotations

import ast
from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest


SCRIPT = (Path(__file__).resolve().parents[1] / "selenium_pipeline"
          / "vendor_template_v2" / "crop_figs_v3.py")


class FakePageImage:
    def save(self, path, fmt):
        Path(path).write_bytes(b"synthetic PNG image")


class FakePdfReader:
    def __init__(self, path):
        self.pages = ["one", "two"]


class FakePdfWriter:
    def add_page(self, _page):
        pass

    def write(self, stream):
        stream.write(b"synthetic isolated PDF page")


class FakeDocument:
    def iterate_items(self):
        return iter(())


class CropFigureConverterReuseTests(unittest.TestCase):
    def test_two_fake_pages_share_one_docling_converter_with_phase_heartbeats(self):
        source = SCRIPT.read_text(encoding="utf-8")
        parsed = ast.parse(source)
        calls = [node for node in ast.walk(parsed)
                 if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name)
                 and node.func.id == "DocumentConverter"]
        self.assertEqual(len(calls), 1)
        for node in ast.walk(parsed):
            if isinstance(node, (ast.For, ast.While)):
                self.assertFalse(any(isinstance(part, ast.Call)
                    and isinstance(part.func, ast.Name)
                    and part.func.id == "DocumentConverter"
                    for part in ast.walk(node)),
                    "Expensive converter must not be recreated per page")
        begin = next(i for i, node in enumerate(parsed.body)
                     if isinstance(node, ast.If)
                     and "os.path.isfile" in ast.unparse(node.test))
        body = ast.Module(body=parsed.body[begin:], type_ignores=[])
        ast.fix_missing_locations(body)
        counter = {"constructors": 0, "conversions": 0, "rasterizations": 0}

        class FakeConverter:
            def __init__(self, **kwargs):
                counter["constructors"] += 1

            def convert(self, path):
                counter["conversions"] += 1
                self.assert_path = Path(path)
                return SimpleNamespace(document=FakeDocument())

        def fake_rasterize(path, dpi):
            counter["rasterizations"] += 1
            self.assertEqual(dpi, 200)
            return [FakePageImage(), FakePageImage()]

        class FakePicture:
            pass

        names = {
            "Path": Path, "os": os, "ikB": 2.55,
            "convert_from_path": fake_rasterize,
            "PdfReader": FakePdfReader, "PdfWriter": FakePdfWriter,
            "PdfPipelineOptions": lambda **kwargs: kwargs,
            "PictureItem": FakePicture,
            "InputFormat": SimpleNamespace(PDF="pdf"),
            "PdfFormatOption": lambda **kwargs: kwargs,
            "DocumentConverter": FakeConverter,
        }
        with tempfile.TemporaryDirectory() as tmp:
            previous = os.getcwd()
            try:
                os.chdir(tmp)
                Path("source.pdf").write_bytes(b"%PDF synthetic")
                output = io.StringIO()
                with redirect_stdout(output):
                    exec(compile(body, str(SCRIPT), "exec"), names)
                for page in (1, 2):
                    self.assertTrue(
                        (Path("crops") / f"page_{page}" /
                         f"page_{page}.png").is_file())
                text = output.getvalue()
                self.assertIn("LOCAL_FIGURE_DOCLING_READY", text)
                self.assertIn("LOCAL_FIGURE_CROP_PAGE_START page=1", text)
                self.assertIn("LOCAL_FIGURE_CROP_PAGE_DONE page=2", text)
            finally:
                os.chdir(previous)
        self.assertEqual(counter,
                         {"constructors": 1, "conversions": 2, "rasterizations": 1})


if __name__ == "__main__":
    unittest.main()
