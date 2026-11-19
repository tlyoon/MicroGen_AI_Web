"""Bounded, read-only local sibling-test import recovery.

The historical test tree has source modules which import other test fixture
modules with bare `test_...` names. Package-style CI invocation must be just
as safe as discovery-style invocation without manual PYTHONPATH changes.
This bootstrap never imports provider code, runs tests, rewrites source,
modifies a Git worktree or approves production release.
"""
from __future__ import annotations

import ast
import os
from pathlib import Path
import re
import sys

from .original_multisource_recovery_campaign import CampaignRecoveryBlocked, require

SIGNATURE = "HISTORICAL_TEST_SIBLING_IMPORTS_REQUIRE_PACKAGE_DISCOVERY_REPAIR"
MECHANISM = "VERIFY_LOCAL_SIBLING_TEST_IMPORTS_AND_INSTALL_BOUNDED_PACKAGE_PATH"
MAX_FILES = 1000
MAX_SOURCE_BYTES = 3_000_000
MAX_IMPORTS = 1000


def _audit_siblings(folder: Path) -> dict:
    require(folder.is_dir() and not folder.is_symlink(),
            "Test source helper directory missing or linked")
    local_files = sorted(folder.glob("test_*.py"))
    require(1 <= len(local_files) <= MAX_FILES,
            "Unsupported test helper source inventory size")
    local_names = {}
    for f in local_files:
        require(f.is_file() and not f.is_symlink()
                and f.resolve().parent == folder.resolve()
                and f.stat().st_size <= MAX_SOURCE_BYTES,
                "Unsafe or oversized test fixture source")
        local_names[f.stem] = f
    references = []
    for f in local_files:
        try:
            tree = ast.parse(f.read_text(encoding="utf-8-sig"), filename=str(f))
        except (SyntaxError, UnicodeDecodeError, ValueError) as exc:
            raise CampaignRecoveryBlocked(
                "Test import inventory cannot verify source AST") from exc
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [name.name for name in node.names
                         if name.name.startswith("test_")]
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("test_"):
                    names = [node.module]
            for name in names:
                require(re.fullmatch(r"test_[A-Za-z0-9_]+", name) is not None
                        and name in local_names,
                        "Unresolved or unsafe legacy test fixture import")
                references.append((f.name, name))
                require(len(references) <= MAX_IMPORTS,
                        "Unbounded sibling test source imports")
    return {
        "status": "SOURCE_VERIFIED_LOCAL_TEST_HELPERS_RESOLVABLE",
        "scanned_test_source_count": len(local_files),
        "legacy_sibling_import_count": len(references),
        "unique_local_sibling_helpers": len({name for _, name in references}),
        "modified_source": False,
        "provider_calls": 0,
        "student_publication_authorized": False,
    }


def bootstrap(test_package_file: str) -> dict:
    """Normal executable import path, automatically invoked by tests package."""
    from .recovery_registry import lookup_mechanism
    require(lookup_mechanism("test_helper_imports", SIGNATURE) == MECHANISM,
            "Test helper import recovery mechanism is missing/retired")
    entry = Path(test_package_file).absolute()
    folder = entry.parent
    root = Path(__file__).resolve().parent.parent
    require(entry.name == "__init__.py" and folder == root / "tests"
            and entry.is_file() and not entry.is_symlink()
            and root.is_dir() and not root.is_symlink()
            and (root / "selenium_pipeline").is_dir(),
            "Only source-bound local tests package may import fixtures")
    audit = _audit_siblings(folder)
    # Add only one trusted source-directory path, never external folders or
    # arbitrary package imports. Sibling imports remain purely test-only.
    name = str(folder)
    if name not in sys.path:
        sys.path.insert(1, name)
    return {**audit, "test_package_path": name,
            "sibling_module_resolution_enabled": True}
