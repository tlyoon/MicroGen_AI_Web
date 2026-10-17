"""Source-bound, append-only observed TTS attempt journal.

One immutable event is written only AFTER an individual provider call returns or
raises. Hash chaining detects accidental editing, deletion and reordering, but
does not cryptographically prove a remote provider received the call. No API.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .tts_effective_identity import DEFAULT, FLASH, LITE, CHIRP


class TTSAttemptEvidenceError(RuntimeError):
    pass


ROOT = ".tts_attempt_evidence"
GENESIS = "0" * 64
MODELS = {LITE, FLASH, CHIRP}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


class AttemptEvidence:
    """A journal in the ORIGINAL job workspace, never the ephemeral batch."""

    def __init__(self, folder: Path, items: list[tuple[int, str]], *,
                 requested: dict[str, str] | None = None):
        self.folder = Path(folder)
        self.path = self.folder / ROOT
        if not items or len({number for number, _ in items}) != len(items):
            raise TTSAttemptEvidenceError("Empty or repeated narration slide identities")
        self.identity = {
            "schema_version": 1,
            "requested": requested if requested is not None else DEFAULT,
            "script_sha256": sha((self.folder / "script.txt").read_bytes()),
            "slides": {str(n): sha(t.encode("utf-8")) for n, t in items},
        }
        if self.identity["requested"] != DEFAULT:
            raise TTSAttemptEvidenceError(
                "Conditional Cloud policy requires original Flash-Lite/Kore")
        if self.path.is_symlink():
            raise TTSAttemptEvidenceError("Unsafe symlinked TTS attempt journal")
        self.path.mkdir(exist_ok=True)
        identity_path = self.path / "identity.json"
        if identity_path.exists() or identity_path.is_symlink():
            if (identity_path.is_symlink() or not identity_path.is_file()
                    or identity_path.read_bytes() != canonical(self.identity)):
                raise TTSAttemptEvidenceError("TTS attempt journal source/model changed")
        else:
            if list(self.path.iterdir()):
                raise TTSAttemptEvidenceError("Orphaned attempt files cannot be adopted")
            with identity_path.open("xb") as stream:
                stream.write(canonical(self.identity))
                stream.flush()
                os.fsync(stream.fileno())
        self.read()

    def read(self) -> list[dict]:
        if self.path.is_symlink() or not self.path.is_dir():
            raise TTSAttemptEvidenceError("Missing or unsafe attempt evidence")
        allowed = {"identity.json"}
        prev = GENESIS
        entries = []
        sequence = 1
        while True:
            name = f"{sequence:06d}.json"
            path = self.path / name
            if not path.exists() and not path.is_symlink():
                break
            if path.is_symlink() or not path.is_file():
                raise TTSAttemptEvidenceError("Unsafe or symlinked attempt evidence")
            try:
                observed = json.loads(path.read_bytes())
            except (ValueError, UnicodeError) as exc:
                raise TTSAttemptEvidenceError("Unreadable TTS attempt event") from exc
            if not isinstance(observed, dict):
                raise TTSAttemptEvidenceError("Attempt event is not an object")
            digest = observed.get("sha256")
            raw = {k: v for k, v in observed.items() if k != "sha256"}
            if (set(raw) != {"sequence", "previous_sha256", "provider", "model",
                             "slide", "round", "outcome", "error_type"}
                    or raw["sequence"] != sequence
                    or raw["previous_sha256"] != prev
                    or raw["provider"] not in ("gemini", "chirp3")
                    or raw["model"] not in MODELS
                    or (raw["provider"] == "gemini") != (raw["model"] in (LITE, FLASH))
                    or type(raw["slide"]) is not int
                    or str(raw["slide"]) not in self.identity["slides"]
                    or type(raw["round"]) is not int or raw["round"] < 1
                    or raw["outcome"] not in ("success", "transient_failure",
                                               "permanent_failure")
                    or (raw["outcome"] == "success") != (raw["error_type"] == "")
                    or not isinstance(raw["error_type"], str)
                    or sha(canonical(raw)) != digest):
                raise TTSAttemptEvidenceError("TTS attempt evidence hash/identity mismatch")
            allowed.add(name)
            entries.append(observed)
            prev = digest
            sequence += 1
        if {p.name for p in self.path.iterdir()} != allowed:
            raise TTSAttemptEvidenceError("Gap, partial or unrecognized attempt records")
        return entries

    def record(self, *, provider: str, model: str, slide: int,
               round_number: int, outcome: str, error_type: str = "") -> dict:
        old = self.read()
        value = {
            "sequence": len(old) + 1,
            "previous_sha256": old[-1]["sha256"] if old else GENESIS,
            "provider": provider,
            "model": model,
            "slide": slide,
            "round": round_number,
            "outcome": outcome,
            "error_type": error_type,
        }
        value["sha256"] = sha(canonical(value))
        filename = self.path / f"{value['sequence']:06d}.json"
        with filename.open("xb") as stream:
            stream.write(canonical(value))
            stream.flush()
            os.fsync(stream.fileno())
        self.read()
        return value

    def verify_exhausted(self, model: str, *, minimum_attempts: int = 3) -> dict:
        """Verify actual locally observed retryable outcomes, not manifest claims."""
        if model not in (LITE, FLASH):
            raise TTSAttemptEvidenceError("Only failed Gemini models justify Cloud")
        entries = [e for e in self.read() if e["model"] == model]
        by_slide: dict[int, list[dict]] = {}
        for entry in entries:
            by_slide.setdefault(entry["slide"], []).append(entry)
        failed: list[int] = []
        for slide, history in by_slide.items():
            if (len(history) >= minimum_attempts
                    and all(e["outcome"] == "transient_failure" for e in history)
                    and [e["round"] for e in history] ==
                        list(range(1, len(history) + 1))):
                failed.append(slide)
        if not failed:
            raise TTSAttemptEvidenceError(
                f"No verified {minimum_attempts}-attempt exhausted slide for {model}")
        # A whole-batch fallback is justified if one or more original slides
        # demonstrably failed. Other slides may have succeeded.
        return {
            "model": model,
            "failed_slides": sorted(failed),
            "observed_attempts_by_slide": {
                str(n): len(history) for n, history in sorted(by_slide.items())
            },
            "last_sha256": self.tip(),
        }

    def verify_before(self, provider: str, model: str) -> dict:
        """Fail BEFORE any higher-tier paid request without lower-tier proof."""
        if provider == "gemini" and model == FLASH:
            return {"lite": self.verify_exhausted(LITE)}
        if provider == "chirp3" and model == CHIRP:
            lite = self.verify_exhausted(LITE)
            flash = self.verify_exhausted(FLASH)
            events = self.read()
            last_lite = max(i for i, event in enumerate(events)
                            if event["model"] == LITE)
            first_flash = min(i for i, event in enumerate(events)
                              if event["model"] == FLASH)
            if first_flash <= last_lite:
                raise TTSAttemptEvidenceError(
                    "Flash was called before Lite retries completed")
            return {"lite": lite, "flash": flash}
        raise TTSAttemptEvidenceError("Unapproved TTS escalation model")

    def tip(self) -> str:
        events = self.read()
        return events[-1]["sha256"] if events else GENESIS

    @classmethod
    def verify_saved(cls, folder: Path, items: list[tuple[int, str]],
                     proof: dict) -> dict:
        """Read only existing journal; do not create a missing journal."""
        if not isinstance(proof, dict) or proof.get("path") != ROOT:
            raise TTSAttemptEvidenceError("Missing or unbound attempt journal proof")
        folder = Path(folder)
        if not (folder / ROOT / "identity.json").is_file():
            raise TTSAttemptEvidenceError("Missing original attempt journal")
        found = cls(folder, items)
        if found.tip() != proof.get("sha256"):
            raise TTSAttemptEvidenceError("Retry journal changed after TTS publication")
        return found.verify_before("chirp3", CHIRP) if proof.get(
            "effective_model") == CHIRP else found.verify_before("gemini", FLASH)
