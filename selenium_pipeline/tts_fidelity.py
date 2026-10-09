"""Post-TTS audio fidelity QA using Gemini native audio understanding.

No Whisper dependency is used. Gemini listens to each WAV, returns an
audio-derived transcript and pronunciation observations, and MicroGen computes
normalized word-level edit distance against the exact script locally.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import difflib
import hashlib
import json
import os
import re
import unicodedata
import wave
from pathlib import Path
from typing import Any

from .runner import blocks, load_microvid_env

DEFAULT_MODEL = os.environ.get("MICROGEN_TTS_QA_MODEL", "gemini-3.8-flash")
DEFAULT_THRESHOLD = float(
    os.environ.get("MICROGEN_TTS_FIDELITY_MIN_PERCENT", "99.0")
)

QA_PROMPT = """You are a strict quality-control listener for text-to-speech audio.

Listen to the attached WAV and compare it with the GROUND TRUTH SCRIPT below.

Requirements:
1. Put the words actually spoken in "transcript". Do not silently repair,
   paraphrase, normalize, or improve the audio.
2. Ignore only punctuation, capitalization, harmless pause differences, and
   genuinely inaudible typography. Do not ignore a pronunciation difference.
3. Treat omitted words, added words, repeated words, changed numbers, changed
   scientific terms, changed signs or directions, and changed mathematical
   meaning as fidelity errors.
4. Independently verify pronunciation. A transcript that looks textually correct
   does NOT prove the audio is correct.
5. Pay special attention to scientific notation, units, variable names, single
   letters, letter names, acronyms, abbreviations, signs, exponents, and proper
   names.
6. Historical Google Cloud TTS failure modes are examples of what to
   inspect, not assumptions about the present Gemini Flash Lite TTS engine.
   Listen empirically and report what this WAV actually does. In particular,
   check whether:
   - a token such as "c." is expanded to an unintended word such as "circa";
   - a variable or label such as "Y" is pronounced as an unrelated word or
     sound instead of the intended letter/variable;
   - article "a" is read as the letter name "ay", or a genuine letter A is read
     as the article;
   - abbreviations or initials are expanded unexpectedly;
   - a mathematical sign, unit, exponent, or variable is given the wrong spoken
     value even when the rest of the sentence is correct.
   Do not flag any of these merely because the token appears in the script; flag
   them only when the audio itself is wrong, ambiguous, or defective.
7. For every item in EXTRA PRONUNCIATION RISKS, listen specifically to that
   span and report the actual spoken rendering. If it is ambiguous or wrong,
   add a critical_token_issue even if the ordinary transcript otherwise matches.
8. Do not infer missing speech from the script. Judge what is audibly present.
9. Return JSON only with this shape:
{
  "transcript": "verbatim words actually heard",
  "pronunciation_issues": [
    {"script_text": "...", "heard_as": "...", "severity": "minor|major", "note": "..."}
  ],
  "critical_token_issues": [
    {"script_text": "...", "heard_as": "...", "category": "letter|abbreviation|variable|unit|number|sign|exponent|name|other", "severity": "major", "note": "..."}
  ],
  "audio_defects": ["clipping, truncation, unexpected silence, repetition, or other defect"],
  "notes": "brief optional QA note"
}

EXTRA PRONUNCIATION RISKS:
<<<{risk_checks}>>>

GROUND TRUTH SCRIPT:
<<<{script}>>>
"""


def _integer_words(value: int) -> str:
    small = (
        "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
        "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
        "sixteen", "seventeen", "eighteen", "nineteen",
    )
    tens = ("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")
    if value < 20:
        return small[value]
    if value < 100:
        return tens[value // 10] + ((" " + small[value % 10]) if value % 10 else "")
    if value < 1000:
        return small[value // 100] + " hundred" + (
            (" " + _integer_words(value % 100)) if value % 100 else ""
        )
    if value < 1_000_000:
        return _integer_words(value // 1000) + " thousand" + (
            (" " + _integer_words(value % 1000)) if value % 1000 else ""
        )
    return str(value)


def _ordinal_words(value: int) -> str:
    irregular = {
        1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
        6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth",
        11: "eleventh", 12: "twelfth", 13: "thirteenth", 14: "fourteenth",
        15: "fifteenth", 16: "sixteenth", 17: "seventeenth", 18: "eighteenth",
        19: "nineteenth",
    }
    if value in irregular:
        return irregular[value]
    if value < 100:
        tens_value = (value // 10) * 10
        if value % 10 == 0:
            base = _integer_words(tens_value)
            return base[:-1] + "ieth" if base.endswith("y") else base + "th"
        return _integer_words(tens_value) + " " + _ordinal_words(value % 10)
    base = _integer_words(value)
    return base + "th" if base != str(value) else str(value)


def normalize_for_comparison(text: str) -> str:
    text = unicodedata.normalize("NFKC", str(text)).lower()
    text = (
        text.replace("?", "'")
        .replace("?", "'")
        .replace("?", "-")
        .replace("?", "-")
    )
    # Apostrophes and quotation marks are not audible.  Treat e.g. Coulombs and
    # Coulomb's, or quoted 'A' and A, as the same spoken token.
    text = text.replace("'", "")
    text = re.sub(r"(?<=\d),(?=\d)", "", text)

    digit_words = {
        "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
        "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine",
    }

    def decimal_repl(match: re.Match[str]) -> str:
        whole = _integer_words(int(match.group(1)))
        fraction = " ".join(digit_words[d] for d in match.group(2))
        return f"{whole} point {fraction}"

    text = re.sub(r"\b(\d+)\.(\d+)\b", decimal_repl, text)

    def number_repl(match: re.Match[str]) -> str:
        value = int(match.group(1))
        suffix = match.group(2)
        return _ordinal_words(value) if suffix else _integer_words(value)

    text = re.sub(r"\b(\d+)(st|nd|rd|th)?\b", number_repl, text)
    text = re.sub(r"[-_/]", " ", text)
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def _tokens(text: str) -> list[str]:
    normalized = normalize_for_comparison(text)
    return normalized.split() if normalized else []


def word_error_stats(reference: str, hypothesis: str) -> dict[str, Any]:
    ref = _tokens(reference)
    hyp = _tokens(hypothesis)
    n, m = len(ref), len(hyp)
    dp: list[list[tuple[int, int, int, int]]] = [
        [(0, 0, 0, 0) for _ in range(m + 1)] for _ in range(n + 1)
    ]
    for i in range(1, n + 1):
        dp[i][0] = (i, 0, i, 0)
    for j in range(1, m + 1):
        dp[0][j] = (j, 0, 0, j)

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref[i - 1] == hyp[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
                continue
            c, s, d, ins = dp[i - 1][j - 1]
            sub = (c + 1, s + 1, d, ins)
            c, s, d, ins = dp[i - 1][j]
            delete = (c + 1, s, d + 1, ins)
            c, s, d, ins = dp[i][j - 1]
            insert = (c + 1, s, d, ins + 1)
            dp[i][j] = min(
                (sub, delete, insert),
                key=lambda x: (x[0], x[1] + x[2] + x[3], x[2], x[3]),
            )

    edits, substitutions, deletions, insertions = dp[n][m]
    wer = edits / n if n else (0.0 if not hyp else 1.0)
    fidelity = max(0.0, 100.0 * (1.0 - wer))
    return {
        "reference_words": n,
        "heard_words": m,
        "substitutions": substitutions,
        "deletions": deletions,
        "insertions": insertions,
        "word_errors": edits,
        "word_error_rate": round(wer, 6),
        "fidelity_percent": round(fidelity, 3),
    }


def diff_spans(reference: str, hypothesis: str, limit: int = 12) -> list[dict[str, str]]:
    ref = _tokens(reference)
    hyp = _tokens(hypothesis)
    matcher = difflib.SequenceMatcher(a=ref, b=hyp, autojunk=False)
    findings: list[dict[str, str]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        findings.append(
            {
                "type": tag,
                "expected": " ".join(ref[i1:i2]),
                "heard": " ".join(hyp[j1:j2]),
            }
        )
        if len(findings) >= limit:
            break
    return findings


def wav_duration_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as wav_file:
        rate = wav_file.getframerate()
        return wav_file.getnframes() / rate if rate else 0.0


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
    raise RuntimeError("Gemini TTS QA returned no text")


def _parse_json_payload(text: str) -> dict[str, Any]:
    stripped = text.strip()
    fence = chr(96) * 3
    if stripped.startswith(fence):
        stripped = re.sub(
            r"^" + re.escape(fence) + r"(?:json)?\s*",
            "",
            stripped,
            flags=re.IGNORECASE,
        )
        stripped = re.sub(r"\s*" + re.escape(fence) + r"$", "", stripped)
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if not match:
            raise RuntimeError(f"TTS QA did not return JSON: {text[:300]}")
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise RuntimeError("TTS QA JSON must be an object")
    return value


def _risk_checks_text(script: str) -> str:
    from .vendor_template_v2.script_tts_risk import risk_hints_for_audio

    findings = risk_hints_for_audio(script)
    if not findings:
        return "No pre-identified ambiguous tokens. Still perform the full pronunciation checks."
    return "\n".join(
        f"- {item['kind']}: {item['text']!r} — {item['message']}"
        for item in findings
    )


def inspect_audio(
    wav_path: Path,
    script: str,
    *,
    model: str = DEFAULT_MODEL,
) -> dict[str, Any]:
    from google import genai
    from google.genai import types
    from gemini_keys import call_with_client_failover

    audio = wav_path.read_bytes()
    prompt = QA_PROMPT.replace("{script}", script).replace("{risk_checks}", _risk_checks_text(script))
    timeout_ms = max(
        120_000,
        int(os.environ.get("MICROGEN_TTS_QA_REQUEST_TIMEOUT_MS", "360000")),
    )

    def qa_client(api_key: str):
        return genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=timeout_ms,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )

    def request(client):
        return client.models.generate_content(
            model=model,
            contents=[
                prompt,
                types.Part.from_bytes(data=audio, mime_type="audio/wav"),
            ],
            config={"temperature": 0, "response_mime_type": "application/json"},
        )

    response = call_with_client_failover(
        qa_client,
        request,
        label=f"TTS fidelity {wav_path.name}",
        max_retries=2,
    )
    return _parse_json_payload(_response_text(response))


def evaluate_slide(
    number: int,
    script: str,
    wav_path: Path,
    *,
    model: str = DEFAULT_MODEL,
    threshold: float = DEFAULT_THRESHOLD,
) -> dict[str, Any]:
    payload = inspect_audio(wav_path, script, model=model)
    transcript = str(payload.get("transcript", "")).strip()
    if not transcript:
        raise RuntimeError(f"slide{number}: TTS QA returned an empty transcript")

    stats = word_error_stats(script, transcript)
    pronunciation = payload.get("pronunciation_issues") or []
    critical = payload.get("critical_token_issues") or []
    defects = payload.get("audio_defects") or []
    major_pronunciation = any(
        isinstance(item, dict)
        and str(item.get("severity", "")).lower() == "major"
        for item in pronunciation
    )
    status = "pass"
    if stats["fidelity_percent"] < threshold or major_pronunciation or critical or defects:
        status = "review"

    duration = wav_duration_seconds(wav_path)
    return {
        "slide": number,
        "audio_file": wav_path.name,
        "duration_seconds": round(duration, 3),
        "heard_words_per_minute": (
            round(max(1, stats["heard_words"]) * 60.0 / duration, 2)
            if duration
            else None
        ),
        "ground_truth": script,
        "transcript": transcript,
        **stats,
        "status": status,
        "differences": diff_spans(script, transcript),
        "pronunciation_issues": pronunciation,
        "critical_token_issues": critical,
        "audio_defects": defects,
        "notes": payload.get("notes", ""),
    }


def _rescore_result(result: dict[str, Any], threshold: float) -> dict[str, Any]:
    result = dict(result)
    script = str(result.get("ground_truth", ""))
    transcript = str(result.get("transcript", ""))
    stats = word_error_stats(script, transcript)
    pronunciation = result.get("pronunciation_issues") or []
    critical = result.get("critical_token_issues") or []
    defects = result.get("audio_defects") or []
    major_pronunciation = any(
        isinstance(item, dict)
        and str(item.get("severity", "")).lower() == "major"
        for item in pronunciation
    )
    result.update(stats)
    result["differences"] = diff_spans(script, transcript)
    result["status"] = (
        "review"
        if stats["fidelity_percent"] < threshold or major_pronunciation or critical or defects
        else "pass"
    )
    return result


def _cache_key(wav_path: Path, script: str, model: str, threshold: float) -> str:
    digest = hashlib.sha256()
    digest.update(b"microgen-tts-qa-v1\0")
    digest.update(model.encode("utf-8"))
    digest.update(f"{threshold:.6f}".encode("ascii"))
    digest.update(QA_PROMPT.encode("utf-8"))
    digest.update(script.encode("utf-8"))
    with wav_path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _evaluate_cached(
    folder: Path,
    number: int,
    script: str,
    *,
    model: str,
    threshold: float,
) -> dict[str, Any]:
    wav_path = folder / f"slide{number}.wav"
    if not wav_path.is_file():
        raise FileNotFoundError(wav_path)
    cache_dir = folder / ".tts_qa_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"slide{number}.json"
    key = _cache_key(wav_path, script, model, threshold)
    if cache_path.is_file():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            cached = {}
        if cached.get("_cache_key") == key and isinstance(cached.get("result"), dict):
            result = _rescore_result(cached["result"], threshold)
            print(f"[tts-qa] reusing cached slide{number} result", flush=True)
            return result

    print(f"[tts-qa] checking slide{number}.wav against script", flush=True)
    result = evaluate_slide(
        number,
        script,
        wav_path,
        model=model,
        threshold=threshold,
    )
    temporary = cache_path.with_suffix(".json.partial")
    temporary.write_text(
        json.dumps({"_cache_key": key, "result": result}, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary.replace(cache_path)
    return result


def _ground_truth_items(folder: Path) -> list[tuple[int, str]]:
    script_items = blocks((folder / "script.txt").read_text(encoding="utf-8"))
    manifest_path = folder / "tts_input_manifest.json"
    if not manifest_path.is_file():
        return script_items
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_items = [
            (int(item["slide"]), str(item["tts_text"]).strip())
            for item in manifest.get("slides", [])
        ]
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return script_items
    if [n for n, _ in manifest_items] != [n for n, _ in script_items]:
        return script_items
    if any(not text for _, text in manifest_items):
        return script_items
    return manifest_items


def build_report(
    folder: Path,
    *,
    model: str = DEFAULT_MODEL,
    threshold: float = DEFAULT_THRESHOLD,
    workers: int | None = None,
) -> dict[str, Any]:
    items = _ground_truth_items(folder)
    if workers is None:
        workers = max(1, int(os.environ.get("MICROGEN_TTS_QA_WORKERS", "1")))
    workers = max(1, min(int(workers), len(items) or 1))

    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                _evaluate_cached,
                folder,
                number,
                script,
                model=model,
                threshold=threshold,
            ): number
            for number, script in items
        }
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            print(
                f"[tts-qa] slide{result['slide']}: "
                f"{result['fidelity_percent']:.3f}% "
                f"({result['word_errors']} word errors) -> {result['status']}",
                flush=True,
            )

    results.sort(key=lambda item: int(item["slide"]))
    fidelities = [float(item["fidelity_percent"]) for item in results]
    review = [item for item in results if item["status"] != "pass"]
    return {
        "version": 1,
        "method": (
            "Gemini native audio inspection + local normalized word edit "
            "distance; no Whisper"
        ),
        "model": model,
        "threshold_percent": threshold,
        "summary": {
            "slides": len(results),
            "passed": len(results) - len(review),
            "review": len(review),
            "mean_fidelity_percent": (
                round(sum(fidelities) / len(fidelities), 3)
                if fidelities
                else 0.0
            ),
            "minimum_fidelity_percent": (
                round(min(fidelities), 3) if fidelities else 0.0
            ),
            "blocking_failures": len(review),
        },
        "slides": results,
    }


def write_report(folder: Path, report: dict[str, Any]) -> tuple[Path, Path]:
    json_path = folder / "tts_fidelity_report.json"
    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    summary = report["summary"]
    lines = [
        "# TTS Fidelity Report",
        "",
        f"- Method: {report['method']}",
        f"- Model: {report['model']}",
        f"- Pass threshold: {report['threshold_percent']}%",
        f"- Mean fidelity: {summary['mean_fidelity_percent']}%",
        f"- Minimum fidelity: {summary['minimum_fidelity_percent']}%",
        f"- Slides passed: {summary['passed']}/{summary['slides']}",
        "",
        "| Slide | Fidelity | Word errors | Status | Main differences |",
        "|---:|---:|---:|---|---|",
    ]
    for item in report["slides"]:
        differences = "; ".join(
            f"{d['type']}: '{d['expected']}' -> '{d['heard']}'"
            for d in item["differences"][:3]
        )
        lines.append(
            f"| {item['slide']} | {item['fidelity_percent']:.3f}% | "
            f"{item['word_errors']} | {item['status']} | {differences} |"
        )
    md_path = folder / "tts_fidelity_report.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate MicroGen TTS WAV fidelity against script.txt"
    )
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, int(os.environ.get("MICROGEN_TTS_QA_WORKERS", "1"))),
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Return non-zero if any slide is below threshold or has a major "
            "audio or pronunciation issue."
        ),
    )
    args = parser.parse_args(argv)
    load_microvid_env()
    report = build_report(
        args.folder,
        model=args.model,
        threshold=args.threshold,
        workers=args.workers,
    )
    json_path, md_path = write_report(args.folder, report)
    print(
        f"[tts-qa] wrote {json_path.name} and {md_path.name}",
        flush=True,
    )
    summary = report["summary"]
    print(
        f"[tts-qa] mean={summary['mean_fidelity_percent']:.3f}% "
        f"minimum={summary['minimum_fidelity_percent']:.3f}% "
        f"review={summary['review']}",
        flush=True,
    )
    return 2 if args.strict and summary["blocking_failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
