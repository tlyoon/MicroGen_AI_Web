import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from selenium_pipeline.pedagogy_benchmark import (
    RUBRIC,
    _phrase_overlap,
    blind_mapping,
    generate_arm,
    normalize_judgment,
    seed_shared_assets,
)


class PedagogyBenchmarkTests(unittest.TestCase):
    def test_rubric_totals_100(self):
        self.assertEqual(
            sum(sum(criteria.values()) for criteria in RUBRIC.values()),
            100,
        )
        self.assertEqual(sum(RUBRIC["slides"].values()), 40)
        self.assertEqual(sum(RUBRIC["narration"].values()), 35)
        self.assertEqual(sum(RUBRIC["integration"].values()), 25)

    def test_phrase_overlap_detects_redundancy(self):
        slide = "Resistance becomes exactly zero below the critical temperature."
        repeated = (
            "Resistance becomes exactly zero below the critical temperature. "
            "This is the central observation."
        )
        explanatory = (
            "The transition is not merely a gradual reduction in resistance; "
            "the material enters a qualitatively different superconducting state."
        )
        self.assertGreater(_phrase_overlap(slide, repeated), 0.8)
        self.assertLess(_phrase_overlap(slide, explanatory), 0.25)

    def test_blind_mapping_contains_both_models(self):
        mapping = blind_mapping("26.5", 1)
        self.assertEqual(set(mapping), {"A", "B"})
        self.assertEqual(set(mapping.values()), {"flash_3_8", "pro_3_1"})
        self.assertEqual(mapping, blind_mapping("26.5", 1))

    def test_normalize_judgment_clamps_scores_and_hard_fails(self):
        scores = {
            section: {name: cap for name, cap in criteria.items()}
            for section, criteria in RUBRIC.items()
        }
        scores["slides"]["scientific_accuracy"] = 999
        raw = {
            "versions": {
                "A": {
                    "scores": scores,
                    "critical_failures": [],
                },
                "B": {
                    "scores": scores,
                    "critical_failures": ["Incorrect physical law on slide 4"],
                },
            },
            "paired_preference": "B clearly better",
        }
        out = normalize_judgment(raw)
        self.assertEqual(out["versions"]["A"]["total_score"], 100.0)
        self.assertFalse(out["versions"]["A"]["hard_fail"])
        self.assertTrue(out["versions"]["B"]["hard_fail"])
        self.assertFalse(out["versions"]["B"]["acceptable"])

    def test_seed_shared_assets_copies_only_shared_figure_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = root / "baseline"
            target = root / "target"
            baseline.mkdir()
            (baseline / "Figure 26.10.png").write_bytes(b"png")
            (baseline / "png_dimensions.json").write_text("{}", encoding="utf-8")
            (baseline / "slides.pdf").write_bytes(b"old")
            (baseline / "crops").mkdir()
            (baseline / "crops" / "x.png").write_bytes(b"x")
            (baseline / "pages").mkdir()
            (baseline / "pages" / "1.png").write_bytes(b"y")

            seed_shared_assets(baseline, target)

            self.assertTrue((target / "Figure 26.10.png").is_file())
            self.assertTrue((target / "png_dimensions.json").is_file())
            self.assertTrue((target / "crops" / "x.png").is_file())
            self.assertTrue((target / "pages" / "1.png").is_file())
            self.assertFalse((target / "slides.pdf").exists())

    def test_generate_arm_retries_failed_transport(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            arm_root = root / "arm"
            target = arm_root / "26" / "26.5"
            calls = []

            def fake_run(*_args, **_kwargs):
                calls.append(1)
                if len(calls) == 1:
                    return SimpleNamespace(returncode=1)
                target.mkdir(parents=True, exist_ok=True)
                (target / "slides.pdf").write_bytes(b"pdf")
                (target / "slides.tex").write_text("slides", encoding="utf-8")
                (target / "script.txt").write_text("script", encoding="utf-8")
                (target / "script_risk_report.json").write_text("{}", encoding="utf-8")
                return SimpleNamespace(returncode=0)

            with patch.dict(
                os.environ,
                {
                    "MICROGEN_BENCHMARK_ARM_ATTEMPTS": "2",
                    "MICROGEN_BENCHMARK_ARM_RETRY_DELAY_SECONDS": "0",
                },
                clear=False,
            ), patch(
                "selenium_pipeline.pedagogy_benchmark.subprocess.run",
                side_effect=fake_run,
            ):
                result = generate_arm(
                    source_root=root / "source",
                    arm_work_root=arm_root,
                    subchapter="26.5",
                    model_key="flash_3_8",
                    log_path=root / "generation.log",
                )

            self.assertEqual(len(calls), 2)
            self.assertEqual(result["model_key"], "flash_3_8")
            self.assertTrue((target / "slides.pdf").is_file())


if __name__ == "__main__":
    unittest.main()
