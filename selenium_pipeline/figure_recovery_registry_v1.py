"""Pinned, finite, fail-closed figure recovery registry for merged-main pipeline."""
import json
from pathlib import Path
REGISTRY_PATH=Path(__file__).with_name("figure_recovery_registry_v1.json")
_ALLOWED=("source_figure_recovery","FIGURE_CAPTIONED_VECTOR_OR_COMPOSITE_CROP_MISSING",
          "GENERATE_SOURCE_BOUND_HYBRID_CROPS_VERIFY_PANELS_THEN_ATOMIC_PROMOTION",
          "NORMAL_FIGURES_STAGE_ORIGINAL_SOURCE_HYBRID_CROP_POST_MAPPING")
def lookup_mechanism(match_type: str, signature: str, *, path: Path|None=None) -> str|None:
    target=Path(path or REGISTRY_PATH)
    if not target.is_file() or target.is_symlink() or not (1<=target.stat().st_size<=4096):
        raise ValueError("Missing/unsafe figure recovery registry")
    obj=json.loads(target.read_text(encoding="utf-8"))
    if (type(obj) is not dict or set(obj)!={"schema_version","status","entries"}
        or obj["schema_version"]!=1 or obj["status"]!="SOURCE_FIGURE_EXECUTABLE_RECOVERY_REGISTRY_V1"
        or type(obj["entries"]) is not list or len(obj["entries"])!=1):
        raise ValueError("Invalid figure recovery registry schema")
    e=obj["entries"][0]
    if (type(e) is not dict
        or set(e)!={"match_type","signature","mechanism","handler","attempt_limit","enabled"}
        or tuple(e[k] for k in ("match_type","signature","mechanism","handler"))!=_ALLOWED
        or type(e["enabled"]) is not bool or not e["enabled"]
        or type(e["attempt_limit"]) is not int or e["attempt_limit"]!=2):
        raise ValueError("Unregistered/disabled/modified source figure recovery")
    if match_type!=_ALLOWED[0] or signature!=_ALLOWED[1]:
        return None
    return e["mechanism"]
