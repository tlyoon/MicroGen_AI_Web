"""Conservative mathematical boundary guard for generated source-slide LaTeX.

Detect the precise pedagogical error of assigning the arctangent OPEN
principal range to BOTH sine and tangent as an inverse-domain fact.
A singular integrand may deliberately use a smaller open sine interval:
those contexts are not reported. This check does not certify other math.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

from .figure_source_identity import require, _sha

_STRICT=(re.escape(r"-\frac{\pi}{2}")+r"\s*<\s*"+
         re.escape(r"\theta")+r"\s*<\s*"+
         re.escape(r"\frac{\pi}{2}"))
_SHARED=re.compile(r"for\s+(?:both\s+)?sine\s+and\s+tangent",re.I)
_FRAMES=re.compile(r"\\begin\{frame\}(.*?)\\end\{frame\}",re.S)
_CONTEXT=re.compile(r"domain\s+restrictions|reversib|inverse\s+trigonometric",
                    re.I)


def inspect_tex(content:str)->dict:
    require(isinstance(content,str) and len(content)<2_000_000,
            "Missing or excessive generated slide TeX")
    findings=[]
    for idx,match in enumerate(_FRAMES.finditer(content),start=1):
        raw=match.group(1)
        # Consume each exact \item separately, not an unrelated strict
        # tangent equation on another slide or another bullet.
        for statement in re.split(r"\\item\b",raw):
            if (re.search(_STRICT,statement)
                    and _SHARED.search(statement)
                    and _CONTEXT.search(statement)):
                findings.append({
                    "slide":idx,
                    "rule":"principal_arcsine_endpoints_wrongly_open",
                    "severity":"blocking",
                    "incorrect_claim":"identical strict (-pi/2,pi/2) inverse domain for sine and tangent",
                    "required_distinction":{
                        "arctangent":"-pi/2 < theta < pi/2",
                        "arcsine":"-pi/2 <= theta <= pi/2"},
                    "source_verification_and_correction_required":True,
                    "unrelated_scientific_content_approved":False
                })
    return {"schema_version":1,
            "status":("INVERSE_TRIG_PRINCIPAL_DOMAIN_BLOCKED"
                      if findings else "NO_KNOWN_SHARED_STRICT_INVERSE_DOMAIN_ERROR"),
            "blocking_count":len(findings),"findings":findings,
            "all_other_mathematics_semantically_verified":False}


def enforce(*,latex_path:Path,source_pdf:Path)->dict:
    latex_path,source_pdf=(Path(x).absolute() for x in
                           (latex_path,source_pdf))
    require(latex_path.is_file() and source_pdf.is_file()
            and not latex_path.is_symlink() and not source_pdf.is_symlink(),
            "Source PDF and generated slides.tex must be present")
    source_before,tex_before=_sha(source_pdf),_sha(latex_path)
    report=inspect_tex(latex_path.read_text(encoding="utf8"))
    require(_sha(source_pdf)==source_before and _sha(latex_path)==tex_before,
            "Original mathematical input changed during inverse-domain check")
    require(report["blocking_count"]==0,
            "Inverse-domain academic defect blocked: shared strict "
            "principal angle range for arcsine and arctangent; "
            "independently verify source and correct slides before TTS/video")
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--latex-path",required=True,type=Path)
    p.add_argument("--source-pdf",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    args=p.parse_args(argv)
    out=args.out.absolute()
    require(out.parent.is_dir() and not out.exists()
            and not out.is_symlink() and
            not out.is_relative_to(args.latex_path.absolute().parent),
            "Exclusive review receipt outside original source folder required")
    tex=args.latex_path.read_text(encoding="utf8")
    report=inspect_tex(tex)
    report["original_source_sha256"]=_sha(args.source_pdf)
    report["original_latex_sha256"]=_sha(args.latex_path)
    with out.open("x",encoding="utf8") as f:
        json.dump(report,f,indent=2)
        f.write("\n")
    print(json.dumps({"status":report["status"],
                      "blocking_count":report["blocking_count"]}))
    return 2 if report["blocking_count"] else 0

if __name__=="__main__":
    raise SystemExit(main())
