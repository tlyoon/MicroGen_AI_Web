"""Finite presend recovery of the user's previously enrolled Account B profile.

Only an existing, initialized and separately authorized account profile under
Dell-115's known MicroGen alternate directory may be reopened. The caller
holds the same per-port Chrome lock. This creates no account, credentials,
fresh Chrome profile, prompt, PDF upload, user message, paid API or Send.
Actual Gemini login, Pro/Medium and owned-tab checks remain mandatory.
"""
from __future__ import annotations

from pathlib import Path

_REGISTERED_SIGNATURE="AUTHORIZED_ENROLLED_ALTERNATE_PROFILE_OFFLINE_NO_SEND"
_REGISTERED_MECHANISM="REOPEN_ONLY_ENROLLED_ACCOUNT_B_THEN_REVERIFY_NO_SEND"
_ENROLLED_LABEL="AccountB"


def enrolled_alternate_profile_present()->bool:
    """Read-only enrollment predicate; never treat mere filename as login."""
    from .launch_gemini import profile_root
    profile=Path(profile_root(_ENROLLED_LABEL))
    state=profile/"Local State"
    default=profile/"Default"
    return bool(profile.is_dir() and not profile.is_symlink()
                and state.is_file() and not state.is_symlink()
                and default.is_dir() and not default.is_symlink())


def enrolled_alternate_port_owned()->bool:
    """Local Chrome command-line proof that port 9225 belongs to Account B.

    Authentication, model and Thinking are separately verified by the owned
    Selenium tab. A listening port or a Chrome profile directory alone is not
    sufficient to authorize an alternate account.
    """
    from .launch_gemini import ALT_PORT,ready,profile_root
    if not enrolled_alternate_profile_present() or not ready(ALT_PORT):
        return False
    try:
        import os
        import psutil
        enrolled=Path(profile_root(_ENROLLED_LABEL))
        # On Windows, temp/user-data paths may be entered through an NTFS
        # junction or another canonical alias. Chrome records the *raw*
        # --user-data-dir argument passed by our launcher; Path.resolve()
        # can canonicalize that same enrolled directory to a different
        # string. Accept ONLY these two known equivalent representations.
        expected={os.path.normcase(os.path.normpath(str(enrolled))),
                  os.path.normcase(os.path.normpath(str(enrolled.resolve())))}
        port_flag=f"--remote-debugging-port={ALT_PORT}"
        for proc in psutil.process_iter(["name","cmdline"]):
            try:
                name=str(proc.info.get("name") or "").lower()
                argv=proc.info.get("cmdline") or []
                if "chrome" not in name or port_flag not in argv:
                    continue
                roots=[x[len("--user-data-dir="):] for x in argv
                       if isinstance(x,str)
                       and x.startswith("--user-data-dir=")]
                if len(roots)!=1:
                    continue
                if os.path.normcase(os.path.normpath(roots[0])) in expected:
                    return True
            except (psutil.NoSuchProcess,psutil.AccessDenied):
                continue
    except Exception:
        return False
    return False


def recover_existing_alternate_debug_session(port:int)->bool:
    from .launch_gemini import ALT_PORT,profile_root,ready,launch
    if type(port) is not int or port!=ALT_PORT:
        return False
    if ready(port):
        return enrolled_alternate_port_owned()
    from .recovery_registry import lookup_mechanism
    try:
        if (lookup_mechanism("presend_capability_repair",
                            _REGISTERED_SIGNATURE)!=_REGISTERED_MECHANISM):
            return False
        profile=Path(profile_root(_ENROLLED_LABEL))
        state=profile/"Local State"
        default=profile/"Default"
        if (not profile.is_dir() or profile.is_symlink()
                or not state.is_file() or state.is_symlink()
                or not default.is_dir() or default.is_symlink()):
            return False
        selected_port,selected_profile=launch(
            _ENROLLED_LABEL,port=ALT_PORT,existing_profile_only=True)
        return (type(selected_port) is int and selected_port==ALT_PORT
                and Path(selected_profile)==profile
                and enrolled_alternate_port_owned())
    except Exception:
        # A missing/retired registry or failed launch cannot make an old
        # uncertain source claim eligible for another Send.
        return False
