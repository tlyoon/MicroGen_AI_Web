"""Strict perceptual voice-continuity QA for fallback TTS audio."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

VOICE_PROMPT = """You are a strict audio continuity reviewer for an educational video.

Listen to the REFERENCE clips and the CANDIDATE clip. The spoken words differ,
so judge the narrator's audible voice rather than the content.

The candidate is allowed into the same video only if it sounds like the same
narrator to an ordinary listener. Compare speaker identity/timbre, accent,
perceived gender/vocal character, pitch range, cadence, speaking rate, energy,
and general delivery. Minor sentence-specific prosody is acceptable. A
noticeable model/provider voice change is not.

Return JSON only:
{
  "same_voice": true,
  "similarity_percent": 0.0,
  "material_differences": [],
  "notes": "brief justification"
}
"""


def _response_text(response: object) -> str:
    value = getattr(response, "text", None)
    if value:
        return str(value).strip()
    pieces = []
    for candidate in getattr(response, "candidates", None) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            value = getattr(part, "text", None)
            if value:
                pieces.append(str(value))
    if pieces:
        return "\n".join(pieces).strip()
    raise RuntimeError("Voice-consistency QA returned no text")


def _parse_json(text: str) -> dict[str, Any]:
    import re
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.I)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, flags=re.S)
        if not match:
            raise RuntimeError(f"Voice QA did not return JSON: {text[:300]}")
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise RuntimeError("Voice QA JSON must be an object")
    return value


def _inspect_direct(candidate: Path, references: list[Path], model: str) -> dict[str, Any]:
    from google import genai
    from google.genai import types
    from gemini_keys import call_with_client_failover

    timeout_ms = max(
        120_000,
        int(os.environ.get("MICROGEN_TTS_VOICE_QA_REQUEST_TIMEOUT_MS", "300000")),
    )

    def client_factory(api_key: str):
        return genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=timeout_ms,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )

    contents: list[Any] = [VOICE_PROMPT]
    for i, ref in enumerate(references, start=1):
        contents.append(f"REFERENCE {i}:")
        contents.append(types.Part.from_bytes(data=ref.read_bytes(), mime_type="audio/wav"))
    contents.append("CANDIDATE:")
    contents.append(types.Part.from_bytes(data=candidate.read_bytes(), mime_type="audio/wav"))

    response = call_with_client_failover(
        client_factory,
        lambda client: client.models.generate_content(
            model=model,
            contents=contents,
            config={"temperature": 0, "response_mime_type": "application/json"},
        ),
        label=f"TTS voice continuity {candidate.name}",
        max_retries=1,
    )
    return _parse_json(_response_text(response))


def _terminate_tree(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        try:
            os.killpg(process.pid, 9)
        except Exception:
            process.kill()


def compare_voice(
    candidate: Path,
    references: list[Path],
    *,
    model: str = "gemini-3.8-flash",
    threshold: float | None = None,
) -> dict[str, Any]:
    if len(references) < 2:
        raise RuntimeError("At least two primary-voice reference WAVs are required")
    threshold = (
        float(os.environ.get("MICROGEN_TTS_VOICE_MATCH_MIN_PERCENT", "95"))
        if threshold is None else float(threshold)
    )
    timeout = max(
        60,
        int(float(os.environ.get("MICROGEN_TTS_VOICE_QA_HARD_TIMEOUT_SECONDS", "300"))),
    )
    attempts = max(1, int(os.environ.get("MICROGEN_TTS_VOICE_QA_ATTEMPTS", "2")))
    last_error: BaseException | None = None

    for attempt in range(1, attempts + 1):
        with tempfile.TemporaryDirectory(prefix="microgen_voice_qa_") as td:
            request = Path(td) / "request.json"
            output = Path(td) / "result.json"
            request.write_text(json.dumps({
                "candidate": str(candidate),
                "references": [str(p) for p in references[:3]],
                "model": model,
                "output": str(output),
            }), encoding="utf-8")
            proc = subprocess.Popen(
                [sys.executable, "-m", "selenium_pipeline.tts_voice_consistency_worker",
                 "--request", str(request)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=os.environ.copy(),
                start_new_session=(os.name != "nt"),
                creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0),
            )
            try:
                worker_output, _ = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                _terminate_tree(proc)
                last_error = TimeoutError(
                    f"Voice-continuity QA exceeded {timeout}s on attempt {attempt}/{attempts}"
                )
                continue
            if proc.returncode != 0 or not output.is_file():
                last_error = RuntimeError(
                    f"Voice-continuity QA worker failed: {(worker_output or '')[-1200:]}"
                )
                continue
            result = json.loads(output.read_text(encoding="utf-8"))
            similarity = float(result.get("similarity_percent", 0.0))
            differences = result.get("material_differences") or []
            result["threshold_percent"] = threshold
            result["accepted"] = bool(
                result.get("same_voice") is True
                and similarity >= threshold
                and not differences
            )
            return result

    if last_error:
        raise last_error
    raise RuntimeError("Voice-continuity QA failed without a result")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--reference", type=Path, action="append", required=True)
    parser.add_argument("--model", default="gemini-3.8-flash")
    parser.add_argument("--threshold", type=float, default=None)
    args = parser.parse_args(argv)
    result = compare_voice(args.candidate, args.reference, model=args.model, threshold=args.threshold)
    print(json.dumps(result, indent=2))
    return 0 if result["accepted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
