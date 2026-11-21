"""Finite executable registry for source-verified figure repairs."""
import json
from pathlib import Path
REGISTRY_PATH = Path(__file__).with_name("figure_recovery_registry_v1.json")
_KIND="source_figure_recovery"
_HANDLER="NORMAL_FIGURES_STAGE_ORIGINAL_SOURCE_HYBRID_CROP_POST_MAPPING"
_ALLOWED={
 (_KIND,"FIGURE_CAPTIONED_VECTOR_OR_COMPOSITE_CROP_MISSING"):
   "GENERATE_SOURCE_BOUND_HYBRID_CROPS_VERIFY_PANELS_THEN_ATOMIC_PROMOTION",
 (_KIND,"SOURCE_SHA_BOUND_V3_COMPLETE_FIGURES"):
   "RECOVER_SHA_PINNED_SOURCE_CROPS_WITH_NO_LEGACY_MAPPING_SEND",
}
_KEYS={"match_type","signature","mechanism","handler","attempt_limit","enabled"}
def lookup_mechanism(match_type: str, signature: str, *, path: Path|None=None) -> str|None:
    target=Path(path or REGISTRY_PATH)
    if not target.is_file() or target.is_symlink() or not 1<=target.stat().st_size<=4096:
        raise ValueError("Missing/unsafe figure recovery registry")
    data=json.loads(target.read_text(encoding="utf-8"))
    if (type(data) is not dict or set(data)!={"schema_version","status","entries"}
        or data["schema_version"]!=1
        or data["status"]!="SOURCE_FIGURE_EXECUTABLE_RECOVERY_REGISTRY_V1"
        or type(data["entries"]) is not list):
        raise ValueError("Invalid figure recovery registry schema")
    if len(data["entries"]) != len(_ALLOWED):
        raise ValueError("Unregistered/disabled/modified source figure recovery")
    seen=set()
    for entry in data["entries"]:
        if type(entry) is not dict or set(entry)!=_KEYS:
            raise ValueError("Unregistered/disabled/modified source figure recovery")
        key=(entry["match_type"],entry["signature"])
        if (key not in _ALLOWED or key in seen or entry["mechanism"]!=_ALLOWED[key]
            or entry["handler"]!=_HANDLER or type(entry["attempt_limit"]) is not int
            or entry["attempt_limit"]!=2 or entry["enabled"] is not True):
            raise ValueError("Unregistered/disabled/modified source figure recovery")
        seen.add(key)
    if seen!=set(_ALLOWED):
        raise ValueError("Unregistered/disabled/modified source figure recovery")
    return _ALLOWED.get((match_type,signature))
