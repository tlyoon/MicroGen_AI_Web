"""Project contract: no Whisper or faster-whisper installation, use, or fallback.

Tests execute with Python stdlib; comments saying 'No Whisper' are harmless.
"""
from __future__ import annotations

import ast
from pathlib import Path
import re
import unittest
import warnings

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "selenium_pipeline"
BLOCKED = frozenset(("whisper", "faster_whisper", "ctranslate2"))


def runtime_imports(source: str) -> list[str]:
    """Check actual Python imports, including literal dynamic imports."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        tree = ast.parse(source)
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names
                         if alias.name.split(".")[0] in BLOCKED)
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] in BLOCKED:
                found.append(node.module or "")
        elif isinstance(node, ast.Call) and node.args:
            func = node.func
            dynamic = (isinstance(func, ast.Name) and func.id == "__import__"
                       or isinstance(func, ast.Attribute)
                       and func.attr == "import_module")
            if dynamic and isinstance(node.args[0], ast.Constant) and isinstance(
                    node.args[0].value, str):
                name = node.args[0].value
                if name.split(".")[0] in BLOCKED:
                    found.append(name)
    return found


def dependency_declarations(source: str) -> list[str]:
    """Reject direct package pins and direct installer declarations."""
    found = []
    package = r"(?:whisper|openai[-_]whisper|faster[-_]whisper|ctranslate2)"
    for line in source.splitlines():
        clean = line.partition("#")[0].strip()
        if not clean:
            continue
        if re.search(r"^" + package + r"(?:\b|\[|[=<>!~])", clean, re.I):
            found.append(clean)
        if re.search(r"\b(?:pip|pip3|uv)\s+install\s+[^#\n]*\b" + package + r"\b",
                     clean, re.I):
            found.append(clean)
    return found


def read_legacy_text(path: Path) -> str:
    """Existing source tree contains UTF-8 BOM and older Windows encodings."""
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252")


class NoWhisperContractTests(unittest.TestCase):
    def test_runtime_tree_contains_no_whisper_imports(self):
        offenders = []
        for file in RUNTIME.rglob("*.py"):
            try:
                for imported in runtime_imports(read_legacy_text(file)):
                    offenders.append(f"{file.relative_to(ROOT)}: {imported}")
            except SyntaxError as exc:
                self.fail(f"Unable to verify source imports for {file}: {exc}")
        self.assertEqual(offenders, [], "Whisper import forbidden by project contract")

    def test_package_manifests_do_not_install_whisper(self):
        files = list(ROOT.glob("requirements*.txt"))
        files += [ROOT / f for f in ("pyproject.toml", "setup.py", "setup.cfg",
                                    "Pipfile", "environment.yml", "environment.yaml")]
        offenders = [(f.name, line) for f in files if f.is_file()
                     for line in dependency_declarations(read_legacy_text(f))]
        self.assertEqual(offenders, [], "Whisper install forbidden by project contract")

    def test_no_whisper_runtime_modules(self):
        names = [str(f.relative_to(ROOT)) for f in RUNTIME.rglob("*.py")
                 if "whisper" in f.name.casefold() or "ctranslate2" in f.name.casefold()]
        self.assertEqual(names, [])

    def test_guard_rejects_direct_and_dynamic_imports(self):
        for code in ("import whisper", "from faster_whisper import WhisperModel",
                     "import ctranslate2", "__import__('whisper')",
                     "importlib.import_module('faster_whisper')"):
            with self.subTest(code=code):
                self.assertTrue(runtime_imports(code))

    def test_guard_rejects_whisper_install_specs(self):
        for line in ("faster-whisper==1.2.1", "openai-whisper>=1",
                     "ctranslate2", "pip install faster-whisper"):
            with self.subTest(line=line):
                self.assertTrue(dependency_declarations(line))
        self.assertFalse(dependency_declarations("# Do not use Whisper"))


if __name__ == "__main__":
    unittest.main()
