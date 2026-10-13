"""Domain-neutral teaching profile API (series-mode infrastructure only).

Not yet called by the legacy runner; see the integrated architecture blueprint.
"""
from .registry import (
    BUILTIN_PROFILES,
    PROFILE_SCHEMA_VERSION,
    PROFILE_STAGES,
    DomainProfile,
    ProfileError,
    load_profile,
    render_stage_guidance,
    validate_profile,
)

__all__ = [
    "BUILTIN_PROFILES", "PROFILE_SCHEMA_VERSION", "PROFILE_STAGES",
    "DomainProfile", "ProfileError", "load_profile",
    "render_stage_guidance", "validate_profile",
]
