"""Versioned, declarative teaching-domain profiles for future MicroGen series mode.

Loading a profile neither enables a generation mode nor executes user code.
This module deliberately uses the Python standard library only.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

PROFILE_SCHEMA_VERSION = 1
PROFILE_STAGES = (
    "source_analysis", "lesson_planning", "slides",
    "narration", "highlighting", "quality_review",
)
BUILTIN_PROFILES = ("general", "physics", "mathematics")
_PROFILE_KEYS = frozenset({
    "schema_version", "id", "profile_version", "display_name",
    "maturity", "content_types", "review_checks", "prompt_sections",
})
_PROFILE_ID = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_CHECK_ID = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


class ProfileError(ValueError):
    """A profile is missing, malformed or not permitted by the v1 contract."""


@dataclass(frozen=True)
class DomainProfile:
    id: str
    profile_version: str
    display_name: str
    maturity: str
    content_types: tuple[str, ...]
    review_checks: tuple[str, ...]
    prompt_sections: tuple[tuple[str, tuple[str, ...]], ...]

    def guidance(self, stage: str) -> tuple[str, ...]:
        if stage not in PROFILE_STAGES:
            raise ProfileError(f"Unsupported teaching stage: {stage!r}")
        return dict(self.prompt_sections)[stage]


def _pairs_unique(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProfileError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _nonempty_list(data: object, key: str, *, pattern: re.Pattern | None = None) -> tuple[str, ...]:
    if not isinstance(data, list) or not data:
        raise ProfileError(f"{key} must be a nonempty array")
    if any(not isinstance(s, str) or not s.strip() for s in data):
        raise ProfileError(f"{key} must contain only nonempty strings")
    if len(set(data)) != len(data):
        raise ProfileError(f"{key} contains duplicate strings")
    if pattern and any(not pattern.fullmatch(s) for s in data):
        raise ProfileError(f"{key} contains an invalid identifier")
    return tuple(data)


def validate_profile(data: object) -> DomainProfile:
    """Fail closed on unknown fields, schema versions and malformed guidance."""
    if not isinstance(data, dict):
        raise ProfileError("Profile root must be an object")
    keys = set(data)
    if keys != _PROFILE_KEYS:
        raise ProfileError(
            f"Profile keys mismatch: missing={sorted(_PROFILE_KEYS - keys)}, "
            f"unknown={sorted(keys - _PROFILE_KEYS)}"
        )
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ProfileError("Unsupported profile schema_version; expected integer 1")
    name = data["id"]
    if not isinstance(name, str) or not _PROFILE_ID.fullmatch(name):
        raise ProfileError("Invalid domain profile id")
    version = data["profile_version"]
    if not isinstance(version, str) or not _VERSION.fullmatch(version):
        raise ProfileError("profile_version must be semver X.Y.Z")
    title = data["display_name"]
    if not isinstance(title, str) or not 2 <= len(title) <= 96:
        raise ProfileError("display_name must be 2–96 characters")
    maturity = data["maturity"]
    if maturity not in ("experimental", "development"):
        raise ProfileError("Invalid profile maturity")
    content_types = _nonempty_list(data["content_types"], "content_types", pattern=_CHECK_ID)
    checks = _nonempty_list(data["review_checks"], "review_checks", pattern=_CHECK_ID)
    prompts = data["prompt_sections"]
    if not isinstance(prompts, dict) or set(prompts) != set(PROFILE_STAGES):
        raise ProfileError("prompt_sections requires each named v1 stage exactly once")
    sections = []
    for stage in PROFILE_STAGES:
        rules = _nonempty_list(prompts[stage], f"prompt_sections.{stage}")
        if any(not 8 <= len(rule) <= 900 for rule in rules):
            raise ProfileError(f"Invalid guidance length in {stage}")
        sections.append((stage, rules))
    return DomainProfile(
        id=name, profile_version=version, display_name=title,
        maturity=maturity, content_types=content_types,
        review_checks=checks, prompt_sections=tuple(sections),
    )


def load_profile(domain: str | None = None, *, profile_file: str | Path | None = None) -> DomainProfile:
    """Load a built-in by domain, or a user-selected JSON file (no plugins executed).

    The optional domain asserts the external file's declared ID; it never
    chooses a different profile silently.
    """
    if profile_file is None:
        if domain not in BUILTIN_PROFILES:
            raise ProfileError(
                f"Unknown built-in domain {domain!r}; supported: {', '.join(BUILTIN_PROFILES)}. "
                "Use profile_file to load a custom domain."
            )
        path = Path(__file__).with_name("profiles") / f"{domain}.json"
    else:
        path = Path(profile_file).expanduser()
    if not path.is_file():
        raise ProfileError(f"Profile file not found: {path}")
    if path.stat().st_size > 1024 * 1024:
        raise ProfileError("Profile file exceeds 1 MiB safety limit")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=_pairs_unique)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProfileError(f"Cannot parse profile JSON: {path}") from exc
    profile = validate_profile(data)
    if domain is not None and domain != profile.id:
        raise ProfileError(f"Requested domain {domain!r} differs from profile ID {profile.id!r}")
    return profile


def render_stage_guidance(profile: DomainProfile, stage: str) -> str:
    """Compose a neutral teaching baseline with subject guidance, no model call."""
    baseline = load_profile("general").guidance(stage)
    subject = () if profile.id == "general" else profile.guidance(stage)
    lines = [f"Teaching context: {profile.display_name} (profile {profile.id}@{profile.profile_version}).",
             "Ground all facts in the supplied source and preserve its exact meanings."]
    lines.extend(f"- {rule}" for rule in (*baseline, *subject))
    return "\n".join(lines)
