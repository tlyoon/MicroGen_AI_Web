"""Finite pre-Send restoration of the SAME authorized primary Chrome profile.

The already-enrolled profile is identified from the normal MicroGen path and
must physically exist with prior Chrome state before any Chrome launch. This
routine does not choose a model, sign in, upload data, type a prompt or Send.
Only the owning stage can separately verify the actual model and Thinking.
"""
from __future__ import annotations

from pathlib import Path


def recover_existing_primary_debug_session(port: int) -> bool:
    """Reopen only a previously initialized primary profile, never Account B.

    Called only within the caller's normal per-port lock and before any model
    submission. Failure is a hard no-Send boundary; there is no blind retry,
    alternate account creation or fallback to a fresh run_* Chrome profile.
    """
    from .launch_gemini import DEFAULT_PORT, ready, launch, profile_root
    if type(port) is not int or port != DEFAULT_PORT:
        return False
    if ready(port):
        return True
    from .recovery_registry import lookup_mechanism
    try:
        mechanism = lookup_mechanism(
            "presend_capability_repair",
            "AUTHORIZED_PRIMARY_PERSISTENT_DEBUG_SESSION_LOST_NO_SEND")
        if mechanism != (
            "REOPEN_ONLY_EXISTING_PRIMARY_PROFILE_THEN_REVERIFY_NO_SEND"):
            return False
    except (ValueError, OSError):
        return False
    try:
        profile = Path(profile_root(None))
        # Existing authorization means an already initialized profile, not
        # merely a directory name. Refuse symlink/empty/unknown profiles.
        state = profile / "Local State"
        default = profile / "Default"
        if (not profile.is_dir() or profile.is_symlink()
                or not state.is_file() or state.is_symlink()
                or not default.is_dir() or default.is_symlink()):
            return False
        selected_port, selected_profile = launch()
        return (type(selected_port) is int and selected_port == DEFAULT_PORT
                and Path(selected_profile) == profile and ready(DEFAULT_PORT))
    except Exception:
        # Chrome startup, authentication or endpoint failure must not cause
        # a source-claim retry. The caller still enforces actual model/effort.
        return False
