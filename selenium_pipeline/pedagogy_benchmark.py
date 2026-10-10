"""Blind pedagogical A/B benchmark for MicroGen slide and narration generation.

The benchmark isolates slide+narration authoring by seeding both model arms with
identical source and figure assets. It combines deterministic diagnostics with
one or more blinded multimodal pedagogical judges. Scientific critical errors
are hard failures and cannot be averaged away by presentation quality.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .runner import blocks, load_microvid_env

MODEL_ARMS = {
    "flash_3_8": {
        "display": "Gemini 3.8 Flash",
        "model": "gemini-3.8-flash",
        "phase": "development",
        "ui_mode": "flash",
    },
    "pro_3_1": {
        "display": "Gemini 3.1 Pro",
        "model": "gemini-3.1-pro-preview",
        "phase": "production",
        "ui_mode": "pro",
    },
}

RUBRIC = {
    "slides": {
        "scientific_accuracy": 10,
        "concept_selection_completeness": 6,
        "pedagogical_sequencing": 7,
        "explanatory_clarity": 6,
        "cognitive_load": 4,
        "figure_integration": 4,
        "visual_communication": 3,
    },
    "narration": {
        "scientific_accuracy": 8,
        "explanatory_added_value": 8,
        "conceptual_clarity": 6,
        "logical_flow": 4,
        "appropriate_depth": 3,
        "natural_teaching_language": 3,
        "math_scientific_verbalization": 3,
    },
    "integration": {
        "synchronization": 7,
        "complementarity": 7,
        "attention_signalling": 4,
        "terminology_notation_consistency": 4,
        "overall_teaching_coherence": 3,
    },
}

CRITICAL_FAILURES = (
    "incorrect physical law or materially incorrect scientific statement",
    "incorrect equation or materially wrong interpretation of an equation",
    "reversed or false causal relationship",
    "figure interpreted in a materially incorrect way",
    "contradiction with the supplied source that would misteach the topic",
    "explanation likely to create a substantive physics misconception",
)

WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)?")
INCLUDEGRAPHICS_RE = re.compile(
    r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}",
    re.IGNORECASE,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _chapter(subchapter: str) -> str:
    return subchapter.split(".", 1)[0]


def _tokens(text: str) -> list[str]:
    return [m.group(0).lower().replace("’", "'") for m in WORD_RE.finditer(text)]


def _bigrams(tokens: list[str]) -> set[tuple[str, str]]:
    return set(zip(tokens, tokens[1:])) if len(tokens) > 1 else set()


def _phrase_overlap(slide_text: str, narration: str) -> float:
    slide_bigrams = _bigrams(_tokens(slide_text))
    if not slide_bigrams:
        return 0.0
    narration_bigrams = _bigrams(_tokens(narration))
    return len(slide_bigrams & narration_bigrams) / len(slide_bigrams)


def _mean(values: list[float]) -> float:
    return statistics.mean(values) if values else 0.0


def _median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def _slide_texts(slides_pdf: Path) -> list[str]:
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    reader = PdfReader(str(slides_pdf))
    return [(page.extract_text() or "").strip() for page in reader.pages]


def deterministic_metrics(folder: Path) -> dict[str, Any]:
    slide_texts = _slide_texts(folder / "slides.pdf")
    narration = blocks((folder / "script.txt").read_text(encoding="utf-8"))
    if len(slide_texts) != len(narration):
        raise ValueError(
            f"Slide/narration count mismatch: {len(slide_texts)} vs {len(narration)}"
        )

    slide_words = [len(_tokens(text)) for text in slide_texts]
    narration_words = [len(_tokens(text)) for _n, text in narration]
    overlaps = [
        _phrase_overlap(slide_text, narr_text)
        for slide_text, (_n, narr_text) in zip(slide_texts, narration)
    ]

    tex = (folder / "slides.tex").read_text(encoding="utf-8", errors="replace")
    figures = INCLUDEGRAPHICS_RE.findall(tex)
    unique_figures = sorted(set(Path(x).name for x in figures))

    risk_summary: dict[str, Any] = {}
    risk_path = folder / "script_risk_report.json"
    if risk_path.is_file():
        try:
            risk_summary = json.loads(risk_path.read_text(encoding="utf-8")).get("summary", {})
        except Exception:
            risk_summary = {}

    dense_threshold = int(os.environ.get("MICROGEN_BENCHMARK_DENSE_SLIDE_WORDS", "85"))
    return {
        "slide_count": len(slide_texts),
        "slide_words_total": sum(slide_words),
        "slide_words_mean": round(_mean([float(x) for x in slide_words]), 2),
        "slide_words_median": round(_median([float(x) for x in slide_words]), 2),
        "slide_words_max": max(slide_words, default=0),
        "dense_slides_over_threshold": [
            i + 1 for i, count in enumerate(slide_words) if count > dense_threshold
        ],
        "narration_words_total": sum(narration_words),
        "narration_words_mean": round(_mean([float(x) for x in narration_words]), 2),
        "narration_words_max": max(narration_words, default=0),
        "narration_to_slide_word_ratio": round(
            sum(narration_words) / max(1, sum(slide_words)), 3
        ),
        "slide_to_narration_phrase_overlap_mean": round(_mean(overlaps), 3),
        "slide_to_narration_phrase_overlap_by_slide": [
            round(x, 3) for x in overlaps
        ],
        "figure_references": len(figures),
        "unique_figures": unique_figures,
        "unique_figure_count": len(unique_figures),
        "script_risk_summary": risk_summary,
    }


def seed_shared_assets(baseline_folder: Path, target_folder: Path) -> None:
    target_folder.mkdir(parents=True, exist_ok=True)
    for item in baseline_folder.glob("Figure*.png"):
        shutil.copy2(item, target_folder / item.name)
    for name in ("png_dimensions.json",):
        src = baseline_folder / name
        if src.is_file():
            shutil.copy2(src, target_folder / name)
    for name in ("crops", "pages"):
        src = baseline_folder / name
        dst = target_folder / name
        if src.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)


def _generation_command(
    source_root: Path,
    arm_work_root: Path,
    subchapter: str,
) -> list[str]:
    return [
        sys.executable,
        "-u",
        "-m",
        "selenium_pipeline",
        "--source-root",
        str(source_root),
        "--work-root",
        str(arm_work_root),
        "--subchapter",
        subchapter,
        "--from-stage",
        "slides",
        "--through-stage",
        "script_qa",
        "--force-from",
        "slides",
    ]


def generate_arm(
    *,
    source_root: Path,
    arm_work_root: Path,
    subchapter: str,
    model_key: str,
    log_path: Path,
) -> dict[str, Any]:
    spec = MODEL_ARMS[model_key]
    env = os.environ.copy()
    env.update(
        {
            "MICROGEN_MODEL_PHASE": spec["phase"],
            "MICROGEN_GEMINI_UI_MODE": spec["ui_mode"],
            "MICROGEN_LLM_MODEL": spec["model"],
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
        }
    )
    command = _generation_command(source_root, arm_work_root, subchapter)
    started = time.monotonic()
    arm_attempts = max(
        1,
        int(os.environ.get("MICROGEN_BENCHMARK_ARM_ATTEMPTS", "3")),
    )
    cooldown = max(
        0.0,
        float(os.environ.get("MICROGEN_BENCHMARK_ARM_RETRY_DELAY_SECONDS", "15")),
    )
    proc = None
    for attempt in range(1, arm_attempts + 1):
        mode = "w" if attempt == 1 else "a"
        with log_path.open(mode, encoding="utf-8") as log:
            log.write(
                f"\n=== BENCHMARK ARM ATTEMPT {attempt}/{arm_attempts} ===\n"
                + "$ "
                + " ".join(command)
                + "\n"
            )
            log.flush()
            proc = subprocess.run(
                command,
                cwd=str(Path(__file__).resolve().parent.parent),
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=int(
                    os.environ.get(
                        "MICROGEN_BENCHMARK_GENERATION_TIMEOUT_SECONDS",
                        "7200",
                    )
                ),
                check=False,
            )
        if proc.returncode == 0:
            break
        print(
            f"[benchmark] {spec['display']} arm attempt "
            f"{attempt}/{arm_attempts} failed with exit {proc.returncode}",
            flush=True,
        )
        if attempt < arm_attempts and cooldown:
            time.sleep(cooldown)

    elapsed = time.monotonic() - started
    if proc is None or proc.returncode:
        code = None if proc is None else proc.returncode
        raise RuntimeError(
            f"{spec['display']} generation failed after {arm_attempts} arm "
            f"attempt(s) (last exit {code}); see {log_path}"
        )
    folder = arm_work_root / _chapter(subchapter) / subchapter
    for required in ("slides.pdf", "slides.tex", "script.txt", "script_risk_report.json"):
        if not (folder / required).is_file():
            raise RuntimeError(f"{spec['display']} missing required output {required}")
    return {
        "model_key": model_key,
        "model": spec["model"],
        "display": spec["display"],
        "elapsed_seconds": round(elapsed, 2),
        "folder": str(folder),
    }


def _response_text(response: object) -> str:
    value = getattr(response, "text", None)
    if value:
        return str(value).strip()
    pieces: list[str] = []
    for candidate in getattr(response, "candidates", None) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            value = getattr(part, "text", None)
            if value:
                pieces.append(str(value))
    if pieces:
        return "\n".join(pieces).strip()
    raise RuntimeError("Pedagogical judge returned no text")


def _parse_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    fence = chr(96) * 3
    if stripped.startswith(fence):
        stripped = re.sub(r"^" + re.escape(fence) + r"(?:json)?\s*", "", stripped, flags=re.I)
        stripped = re.sub(r"\s*" + re.escape(fence) + r"$", "", stripped)
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, flags=re.S)
        if not match:
            raise RuntimeError(f"Judge did not return JSON: {text[:500]}")
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise RuntimeError("Judge JSON must be an object")
    return value


def _rubric_prompt() -> str:
    lines = []
    for section, criteria in RUBRIC.items():
        lines.append(f"{section.upper()} ({sum(criteria.values())} points)")
        for name, cap in criteria.items():
            lines.append(f"- {name}: 0 to {cap}")
    critical = "\n".join(f"- {x}" for x in CRITICAL_FAILURES)
    return "\n".join(lines) + "\n\nCRITICAL SCIENTIFIC FAILURES:\n" + critical


def _judge_prompt(script_a: str, script_b: str) -> str:
    schema_scores = {
        section: {name: 0 for name in criteria}
        for section, criteria in RUBRIC.items()
    }
    schema = {
        "versions": {
            "A": {
                "scores": schema_scores,
                "critical_failures": [],
                "strengths": [],
                "weaknesses": [],
                "pedagogical_evidence": [],
            },
            "B": {
                "scores": schema_scores,
                "critical_failures": [],
                "strengths": [],
                "weaknesses": [],
                "pedagogical_evidence": [],
            },
        },
        "paired_preference": "A clearly better | A slightly better | equivalent | B slightly better | B clearly better",
        "preference_reasons": [],
        "what_winner_does_better_pedagogically": [],
        "transferable_prompt_improvements": [],
    }
    return f"""You are an expert university physics educator evaluating two BLINDED
MicroGen lesson versions derived from the SAME authoritative source PDF.

Your goal is not to reward verbosity, polish, or model style. Judge which lesson
better helps a university physics student build a correct, coherent mental model
with manageable cognitive load.

You receive, in order:
1. AUTHORITATIVE SOURCE PDF.
2. VERSION A SLIDES PDF.
3. VERSION A NARRATION below.
4. VERSION B SLIDES PDF.
5. VERSION B NARRATION below.

Do not guess model identity. Evaluate both versions independently before making
the paired comparison.

Pedagogical principles:
- Scientific correctness is mandatory.
- Important source concepts should be selected and sequenced coherently.
- Slides should not become textbook pages; visual hierarchy and cognitive load matter.
- Figures should be used to explain physics, not decorate.
- Narration should add interpretation, causal reasoning, emphasis, transitions,
  and conceptual explanation instead of merely reading slide text.
- Some repetition for emphasis is useful; penalize extensive unproductive redundancy.
- Narration must stay synchronized with what the learner sees.
- Mathematical symbols, variables, units and terminology must be introduced and
  verbalized in pedagogically sensible ways.
- Penalize unsupported additions, omissions of key concepts, misleading simplifications,
  and explanations likely to create misconceptions.
- A critical scientific failure is a HARD FAIL and cannot be compensated by aesthetics.

RUBRIC:
{_rubric_prompt()}

For every score below the maximum, give concrete slide-level evidence when possible.
Use the source PDF as authority. Return JSON only. Do not include markdown fences.

VERSION A NARRATION:
---A---
{script_a}
---END A---

VERSION B NARRATION:
---B---
{script_b}
---END B---

Return this JSON structure:
{json.dumps(schema, indent=2)}
"""


def _validated_scores(version: dict[str, Any]) -> dict[str, Any]:
    supplied = version.get("scores") or {}
    normalized: dict[str, dict[str, float]] = {}
    total = 0.0
    for section, criteria in RUBRIC.items():
        section_in = supplied.get(section) or {}
        section_out: dict[str, float] = {}
        for name, cap in criteria.items():
            value = float(section_in.get(name, 0))
            value = max(0.0, min(float(cap), value))
            section_out[name] = round(value, 3)
            total += value
        normalized[section] = section_out
    critical = [str(x) for x in (version.get("critical_failures") or []) if str(x).strip()]
    return {
        "scores": normalized,
        "total_score": round(total, 3),
        "hard_fail": bool(critical),
        "acceptable": not bool(critical),
        "critical_failures": critical,
        "strengths": [str(x) for x in (version.get("strengths") or [])],
        "weaknesses": [str(x) for x in (version.get("weaknesses") or [])],
        "pedagogical_evidence": [str(x) for x in (version.get("pedagogical_evidence") or [])],
    }


def normalize_judgment(raw: dict[str, Any]) -> dict[str, Any]:
    versions = raw.get("versions") or {}
    if "A" not in versions or "B" not in versions:
        raise ValueError("Judge response must contain versions A and B")
    pref = str(raw.get("paired_preference", "equivalent")).strip()
    allowed = {
        "A clearly better", "A slightly better", "equivalent",
        "B slightly better", "B clearly better",
    }
    if pref not in allowed:
        pref = "equivalent"
    return {
        "versions": {
            "A": _validated_scores(versions["A"]),
            "B": _validated_scores(versions["B"]),
        },
        "paired_preference": pref,
        "preference_reasons": [str(x) for x in (raw.get("preference_reasons") or [])],
        "what_winner_does_better_pedagogically": [
            str(x) for x in (raw.get("what_winner_does_better_pedagogically") or [])
        ],
        "transferable_prompt_improvements": [
            str(x) for x in (raw.get("transferable_prompt_improvements") or [])
        ],
    }


def blind_mapping(subchapter: str, run_number: int) -> dict[str, str]:
    bit = int(hashlib.sha256(f"{subchapter}:{run_number}".encode()).hexdigest()[-1], 16) % 2
    if bit:
        return {"A": "flash_3_8", "B": "pro_3_1"}
    return {"A": "pro_3_1", "B": "flash_3_8"}


def judge_pair(
    *,
    source_pdf: Path,
    folders: dict[str, Path],
    mapping: dict[str, str],
    judge_model: str,
) -> dict[str, Any]:
    load_microvid_env()
    from google import genai
    from google.genai import types
    from gemini_keys import call_with_client_failover

    folder_a = folders[mapping["A"]]
    folder_b = folders[mapping["B"]]
    script_a = (folder_a / "script.txt").read_text(encoding="utf-8")
    script_b = (folder_b / "script.txt").read_text(encoding="utf-8")
    prompt = _judge_prompt(script_a, script_b)
    timeout_ms = int(os.environ.get("MICROGEN_BENCHMARK_JUDGE_TIMEOUT_MS", "600000"))

    def client_factory(api_key: str):
        return genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=timeout_ms,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )

    contents = [
        prompt,
        "AUTHORITATIVE SOURCE PDF:",
        types.Part.from_bytes(data=source_pdf.read_bytes(), mime_type="application/pdf"),
        "VERSION A SLIDES PDF:",
        types.Part.from_bytes(data=(folder_a / "slides.pdf").read_bytes(), mime_type="application/pdf"),
        "VERSION B SLIDES PDF:",
        types.Part.from_bytes(data=(folder_b / "slides.pdf").read_bytes(), mime_type="application/pdf"),
    ]

    started = time.monotonic()
    response = call_with_client_failover(
        client_factory,
        lambda client: client.models.generate_content(
            model=judge_model,
            contents=contents,
            config={"temperature": 0, "response_mime_type": "application/json"},
        ),
        label=f"Pedagogy benchmark judge {judge_model}",
        max_retries=1,
    )
    result = normalize_judgment(_parse_json(_response_text(response)))
    result["judge_model"] = judge_model
    result["elapsed_seconds"] = round(time.monotonic() - started, 2)
    return result


def _preference_winner(pref: str) -> str | None:
    if pref.startswith("A "):
        return "A"
    if pref.startswith("B "):
        return "B"
    return None


def consensus(judgments: list[dict[str, Any]], mapping: dict[str, str]) -> dict[str, Any]:
    by_model: dict[str, dict[str, Any]] = {}
    for model_key in MODEL_ARMS:
        label = "A" if mapping["A"] == model_key else "B"
        values = [j["versions"][label] for j in judgments]
        by_model[model_key] = {
            "display": MODEL_ARMS[model_key]["display"],
            "mean_score": round(_mean([v["total_score"] for v in values]), 3),
            "scores": [v["total_score"] for v in values],
            "hard_fail_judges": sum(1 for v in values if v["hard_fail"]),
            "acceptable_judges": sum(1 for v in values if v["acceptable"]),
        }

    votes = Counter()
    for judgment in judgments:
        winner_label = _preference_winner(judgment["paired_preference"])
        if winner_label:
            votes[mapping[winner_label]] += 1
        else:
            votes["tie"] += 1

    flash = by_model["flash_3_8"]
    pro = by_model["pro_3_1"]
    if pro["hard_fail_judges"] == 0 and flash["hard_fail_judges"] > 0:
        winner = "pro_3_1"
    elif flash["hard_fail_judges"] == 0 and pro["hard_fail_judges"] > 0:
        winner = "flash_3_8"
    elif abs(pro["mean_score"] - flash["mean_score"]) < 1.0:
        winner = "tie"
    else:
        winner = "pro_3_1" if pro["mean_score"] > flash["mean_score"] else "flash_3_8"

    return {
        "by_model": by_model,
        "paired_preference_votes": dict(votes),
        "winner": winner,
        "winner_display": "Equivalent" if winner == "tie" else MODEL_ARMS[winner]["display"],
        "score_difference_pro_minus_flash": round(pro["mean_score"] - flash["mean_score"], 3),
    }


def write_human_review_sheet(run_dir: Path) -> None:
    lines = [
        "# Blind Human Pedagogical Review",
        "",
        "Review Version A and Version B without consulting the benchmark report first.",
        "Use the source PDF as the scientific authority.",
        "",
    ]
    for section, criteria in RUBRIC.items():
        lines.append(f"## {section.title()} — {sum(criteria.values())} points")
        for name, cap in criteria.items():
            lines.append(f"- {name.replace('_', ' ').title()}: ___ / {cap}")
        lines.append("")
    lines.extend(
        [
            "## Hard scientific failure check",
            "Any substantive scientific error below makes that version unacceptable:",
        ]
    )
    lines.extend(f"- {item}" for item in CRITICAL_FAILURES)
    lines.extend(
        [
            "",
            "## Pairwise choice",
            "- [ ] A clearly better",
            "- [ ] A slightly better",
            "- [ ] Equivalent",
            "- [ ] B slightly better",
            "- [ ] B clearly better",
            "",
            "Why does the preferred version teach the physics better?",
            "",
            "Which features should be transferred into the MicroGen prompt?",
            "",
            "<!-- Mapping intentionally hidden here. It is revealed in the benchmark report. -->",
        ]
    )
    (run_dir / "human_review_sheet.md").write_text("\n".join(lines), encoding="utf-8")


def _format_metrics(metrics: dict[str, Any]) -> str:
    return (
        f"{metrics['slide_count']} slides; "
        f"{metrics['slide_words_mean']:.1f} slide words/slide; "
        f"{metrics['narration_words_mean']:.1f} narration words/slide; "
        f"phrase overlap {metrics['slide_to_narration_phrase_overlap_mean']:.3f}; "
        f"{metrics['unique_figure_count']} unique figures"
    )


def write_report(run_dir: Path, report: dict[str, Any]) -> None:
    (run_dir / "benchmark_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    mapping = report["blind_mapping"]
    lines = [
        "# MicroGen Pedagogical Benchmark",
        "",
        f"- Subchapter: **{report['subchapter']}**",
        f"- Created: {report['created_at_utc']}",
        f"- Version A: **{MODEL_ARMS[mapping['A']]['display']}**",
        f"- Version B: **{MODEL_ARMS[mapping['B']]['display']}**",
        "",
        "## Deterministic diagnostics",
        "",
    ]
    for model_key, metrics in report["deterministic_metrics"].items():
        lines.append(f"- **{MODEL_ARMS[model_key]['display']}**: {_format_metrics(metrics)}")
    lines.extend(["", "## Blind pedagogical judges", ""])
    for judgment in report["judgments"]:
        lines.append(f"### {judgment['judge_model']}")
        for label in ("A", "B"):
            v = judgment["versions"][label]
            lines.append(
                f"- Version {label}: **{v['total_score']:.1f}/100**"
                + (" — HARD FAIL" if v["hard_fail"] else "")
            )
        lines.append(f"- Paired preference: **{judgment['paired_preference']}**")
        for reason in judgment.get("preference_reasons", [])[:5]:
            lines.append(f"  - {reason}")
        lines.append("")
    c = report["consensus"]
    lines.extend(
        [
            "## Consensus",
            "",
            f"- Gemini 3.1 Pro mean: **{c['by_model']['pro_3_1']['mean_score']:.2f}/100**",
            f"- Gemini 3.8 Flash mean: **{c['by_model']['flash_3_8']['mean_score']:.2f}/100**",
            f"- Pro − Flash: **{c['score_difference_pro_minus_flash']:+.2f} points**",
            f"- Benchmark winner: **{c['winner_display']}**",
            "",
            "Scores are pedagogical proxies, not direct student-learning outcomes. "
            "The blinded human review sheet and, ultimately, student learning/retention "
            "remain the stronger validation layers.",
        ]
    )
    (run_dir / "benchmark_report.md").write_text("\n".join(lines), encoding="utf-8")


def run_one(
    *,
    source_root: Path,
    baseline_work_root: Path,
    benchmark_root: Path,
    subchapter: str,
    run_number: int,
    judge_models: list[str],
    generate: bool = True,
) -> Path:
    chapter = _chapter(subchapter)
    source_pdf = source_root / chapter / subchapter / "source.pdf"
    baseline_folder = baseline_work_root / chapter / subchapter
    if not source_pdf.is_file():
        raise FileNotFoundError(source_pdf)
    if not baseline_folder.is_dir():
        raise FileNotFoundError(baseline_folder)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + f"_r{run_number}"
    run_dir = benchmark_root / chapter / subchapter / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    mapping = blind_mapping(subchapter, run_number)
    generation_order = ["flash_3_8", "pro_3_1"]
    if run_number % 2 == 0:
        generation_order.reverse()

    generation: dict[str, Any] = {}
    folders: dict[str, Path] = {}
    for model_key in MODEL_ARMS:
        arm_root = run_dir / model_key
        folder = arm_root / chapter / subchapter
        folders[model_key] = folder
        seed_shared_assets(baseline_folder, folder)

    if generate:
        for model_key in generation_order:
            print(f"[benchmark] generating {MODEL_ARMS[model_key]['display']}", flush=True)
            generation[model_key] = generate_arm(
                source_root=source_root,
                arm_work_root=run_dir / model_key,
                subchapter=subchapter,
                model_key=model_key,
                log_path=run_dir / f"generation_{model_key}.log",
            )
    else:
        for model_key, folder in folders.items():
            generation[model_key] = {
                "model_key": model_key,
                "model": MODEL_ARMS[model_key]["model"],
                "display": MODEL_ARMS[model_key]["display"],
                "elapsed_seconds": None,
                "folder": str(folder),
            }

    metrics = {model_key: deterministic_metrics(folder) for model_key, folder in folders.items()}
    write_human_review_sheet(run_dir)

    judgments: list[dict[str, Any]] = []
    judge_errors: list[dict[str, str]] = []
    for judge_model in judge_models:
        print(f"[benchmark] blinded judge: {judge_model}", flush=True)
        try:
            judgments.append(
                judge_pair(
                    source_pdf=source_pdf,
                    folders=folders,
                    mapping=mapping,
                    judge_model=judge_model,
                )
            )
        except Exception as exc:
            judge_errors.append(
                {
                    "judge_model": judge_model,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            print(
                f"[benchmark] judge {judge_model} failed: {type(exc).__name__}: {exc}",
                flush=True,
            )

    if not judgments:
        raise RuntimeError(
            "All pedagogical judges failed; generation artifacts are preserved in "
            f"{run_dir}"
        )

    report = {
        "version": 1,
        "created_at_utc": _utc_now(),
        "subchapter": subchapter,
        "source_pdf": str(source_pdf),
        "source_sha256": _sha256(source_pdf),
        "baseline_figure_folder": str(baseline_folder),
        "generation_order": generation_order,
        "generation": generation,
        "blind_mapping": mapping,
        "rubric": RUBRIC,
        "critical_failure_policy": list(CRITICAL_FAILURES),
        "deterministic_metrics": metrics,
        "judgments": judgments,
        "judge_errors": judge_errors,
        "consensus": consensus(judgments, mapping),
    }
    write_report(run_dir, report)
    print(f"[benchmark] complete: {run_dir}", flush=True)
    print(
        f"[benchmark] winner: {report['consensus']['winner_display']} | "
        f"Pro-Flash={report['consensus']['score_difference_pro_minus_flash']:+.2f}",
        flush=True,
    )
    return run_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Blind pedagogical benchmark: Gemini 3.1 Pro vs Gemini 3.8 Flash"
    )
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--baseline-work-root", type=Path, required=True)
    parser.add_argument("--benchmark-root", type=Path, required=True)
    parser.add_argument("--subchapter", required=True)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument(
        "--judge-model",
        action="append",
        dest="judge_models",
        default=None,
        help="Repeat for multiple blind judges. Default: Flash 3.8 and Pro 3.1.",
    )
    parser.add_argument(
        "--no-generate",
        action="store_true",
        help="Evaluate already-generated arm folders in a newly prepared run (advanced/debug).",
    )
    args = parser.parse_args(argv)

    judges = args.judge_models or [
        "gemini-3.8-flash",
        "gemini-3.1-pro-preview",
    ]
    if args.runs < 1:
        parser.error("--runs must be at least 1")

    completed: list[str] = []
    for run_number in range(1, args.runs + 1):
        completed.append(
            str(
                run_one(
                    source_root=args.source_root,
                    baseline_work_root=args.baseline_work_root,
                    benchmark_root=args.benchmark_root,
                    subchapter=args.subchapter,
                    run_number=run_number,
                    judge_models=judges,
                    generate=not args.no_generate,
                )
            )
        )
    print(json.dumps({"completed_runs": completed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
