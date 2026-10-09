"""Detect narration text that is unusually vulnerable to TTS misinterpretation.

This module never rewrites narration. It only identifies ambiguous constructs so
Gemini can regenerate the script before synthesis and so the pipeline can stop
before producing questionable audio.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

SLIDE_RE = re.compile(r"(?m)^\*\*Slide\s+(\d+)\s+\[[^\]\r\n]+\]:")
COMMON_DOTTED_ABBREVIATIONS = re.compile(r"(?i)\b(?:e\.g|i\.e|etc|approx|fig|eq|no|vs)\.")
SINGLE_DOTTED_LETTER = re.compile(r"(?<![A-Za-z])([A-Za-z])\.(?![A-Za-z])")
STANDALONE_LETTER = re.compile(r"(?<![A-Za-z0-9\'])(([A-Za-z]))(?![A-Za-z0-9\'])")
RAW_MATH = re.compile(r"[\\^_]|[±×÷√ΔσΩπ]|(?<=\w)/(?=\w)")
ALL_CAPS = re.compile(r"\b[A-Z]{2,6}\b")


def parse_blocks(text: str) -> list[tuple[int, str]]:
    matches = list(SLIDE_RE.finditer(text))
    result: list[tuple[int, str]] = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[match.end():end].strip().strip("*").strip()
        result.append((int(match.group(1)), body))
    return result


def _line_col(text: str, pos: int) -> tuple[int, int]:
    line = text.count("\n", 0, pos) + 1
    last = text.rfind("\n", 0, pos)
    return line, pos + 1 if last < 0 else pos - last


def _sentence_start(text: str, pos: int) -> bool:
    before = text[:pos].rstrip()
    return not before or before[-1] in ".!?:;"


def collect_tts_risks(text: str, *, slide: int | None = None) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    # Historical Google Cloud TTS trouble tokens are evidence for what the
    # acoustic QA should inspect, not proof that Gemini Flash Lite TTS will
    # mispronounce them. Therefore pronunciation-risk constructs are warnings.
    # Reserve blocking for wording whose intended meaning is intrinsically
    # ambiguous even before synthesis.
    default_severity = "warning"
    blocking_severity = "warning" if slide == 1 else "blocking"

    def add(kind: str, token: str, pos: int, message: str, severity: str | None = None):
        line, column = _line_col(text, pos)
        findings.append({
            "slide": slide,
            "severity": severity or default_severity,
            "kind": kind,
            "text": token,
            "line": line,
            "column": column,
            "message": message,
        })

    covered: list[tuple[int, int]] = []
    for match in COMMON_DOTTED_ABBREVIATIONS.finditer(text):
        covered.append(match.span())
        add(
            "dotted_abbreviation",
            match.group(0),
            match.start(),
            "Dotted abbreviation is a historical TTS pronunciation risk; verify its actual Flash Lite rendering acoustically.",
            severity="warning",
        )

    for match in SINGLE_DOTTED_LETTER.finditer(text):
        if any(a <= match.start() < b for a, b in covered):
            continue
        covered.append(match.span())
        token = match.group(1)
        # A period after a physics variable is often sentence punctuation.
        # Older Google Cloud TTS sometimes expanded forms such as c. in
        # undesirable ways, but Flash Lite must be judged empirically.
        add(
            "dotted_single_letter",
            match.group(0),
            match.start(),
            "Single letter followed by a period is a historical TTS pronunciation risk and must be checked acoustically with the current Flash Lite output.",
            severity="warning",
        )

    explicit_role_re = re.compile(
        r"(?:variable|charge|point|object|sphere|axis|component|coordinate|"
        r"denoted|option|choice|letter|radius|distance|area|length|field|"
        r"magnitude|constant|density|volume|surface|line|plate|rod)\s+$"
    )

    for match in STANDALONE_LETTER.finditer(text):
        token = match.group(1)
        pos = match.start(1)
        if any(a <= pos < b for a, b in covered):
            continue
        tail_raw = text[match.end(1):match.end(1) + 24]
        tail = tail_raw.lower()
        head = text[max(0, pos - 24):pos].lower()

        if token == "a" or token == "I":
            continue
        if token == "A" and _sentence_start(text, pos):
            continue

        explicit_context = bool(
            re.match(r"(?:-|\s+)(?:axis|coordinate|component|direction)\b", tail)
            or explicit_role_re.search(head)
        )

        # Mid-sentence capital A is uniquely dangerous because it may be either
        # the article "a" or the letter name "A". Keep unexplained cases
        # blocking, but treat clearly labelled scientific variables as warnings
        # for acoustic verification rather than regeneration blockers.
        if token == "A" and not explicit_context:
            next_word = re.match(r"\s+([A-Za-z][A-Za-z'-]*)", tail_raw)
            if next_word:
                add(
                    "ambiguous_capital_a",
                    token,
                    pos,
                    "Mid-sentence capital A may be an accidental article or a letter label. Rewrite so the intended spoken meaning is explicit.",
                    severity=blocking_severity,
                )
                continue

        kind = "contextual_letter" if explicit_context else "isolated_letter"
        add(
            kind,
            token,
            pos,
            f"Letter {token!r} must be checked acoustically to confirm the intended letter/variable pronunciation.",
            severity="warning",
        )

    for match in RAW_MATH.finditer(text):
        add(
            "symbolic_notation",
            match.group(0),
            match.start(),
            "Symbolic notation is a pronunciation risk; verify the actual Flash Lite rendering acoustically.",
            severity="warning",
        )

    for match in ALL_CAPS.finditer(text):
        add(
            "acronym",
            match.group(0),
            match.start(),
            "Acronym pronunciation may vary between spelling letters and reading it as a word; verify the intended spoken form.",
            severity="warning",
        )

    seen: set[tuple[str, int, str]] = set()
    unique = []
    for item in findings:
        key = (str(item["kind"]), int(item["column"]), str(item["text"]))
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def analyze_script_text(text: str) -> dict[str, Any]:
    slides = parse_blocks(text)
    findings: list[dict[str, Any]] = []
    if slides:
        for number, body in slides:
            findings.extend(collect_tts_risks(body, slide=number))
    else:
        findings.extend(collect_tts_risks(text, slide=None))

    blocking = [item for item in findings if item["severity"] == "blocking"]
    warnings = [item for item in findings if item["severity"] == "warning"]
    return {
        "version": 1,
        "method": "non-destructive TTS ambiguity lint; no script rewriting",
        "summary": {
            "slides": len(slides),
            "findings": len(findings),
            "blocking": len(blocking),
            "warnings": len(warnings),
        },
        "findings": findings,
    }


def risk_hints_for_audio(script: str) -> list[dict[str, Any]]:
    return collect_tts_risks(script, slide=None)


def blocking_warning_messages(script_path: Path) -> list[str]:
    if not script_path.is_file():
        return [f"TTS-risk audit: missing {script_path.name}"]
    report = analyze_script_text(script_path.read_text(encoding="utf-8"))
    return [
        f"TTS-risk slide {item.get('slide')}: {item['kind']} {item['text']!r} - {item['message']}"
        for item in report["findings"]
        if item["severity"] == "blocking"
    ]


def write_report(report: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    summary = report["summary"]
    lines = [
        "# TTS Script Risk Report",
        "",
        "- This report is non-destructive: it does not rewrite narration.",
        f"- Blocking findings: {summary['blocking']}",
        f"- Warnings: {summary['warnings']}",
        "",
        "| Slide | Severity | Kind | Text | Reason |",
        "|---:|---|---|---|---|",
    ]
    for item in report["findings"]:
        message = str(item["message"]).replace("|", "\\|")
        token = str(item["text"]).replace("|", "\\|")
        lines.append(
            f"| {item.get('slide') or ''} | {item['severity']} | {item['kind']} | {token!r} | {message} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit narration for text likely to be mispronounced by TTS")
    parser.add_argument("--script", type=Path, default=Path("script.txt"))
    parser.add_argument("--json", type=Path, default=Path("script_risk_report.json"))
    parser.add_argument("--markdown", type=Path, default=Path("script_risk_report.md"))
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)

    report = analyze_script_text(args.script.read_text(encoding="utf-8"))
    write_report(report, args.json, args.markdown)
    summary = report["summary"]
    print(
        f"[script-qa] blocking={summary['blocking']} warnings={summary['warnings']} findings={summary['findings']}",
        flush=True,
    )
    for item in report["findings"]:
        print(
            f"[script-qa] slide{item.get('slide')}: {item['severity']} {item['kind']} {item['text']!r}",
            flush=True,
        )
    return 2 if args.strict and summary["blocking"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
