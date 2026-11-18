"""Recover exact legacy Beamer slide-counter clipping in normal production.

Only recognizes the historical MicroGen prompt's original headline preamble.
A physical slide counter must be inset and its correct total frame count
proven in a twice-compiled actual PDF before producer acceptance. This never
relabels physics, rewrites narration, touches original QA sources, or grants
academic / cost / publication authority.
"""
from __future__ import annotations
import re
from pathlib import Path

LEGACY_HEADLINE = re.compile(
    r"\\setbeamertemplate\{headline\}\{%\s*"
    r"\\hfill%\s*"
    r"\\insertframenumber\{\}\s*/\s*\\inserttotalframenumber%\s*"
    r"\\par%\s*\}", re.M)
SAFE_VARIANT = re.compile(
    r"\\setbeamertemplate\{headline\}\{%\s*"
    r"\\vskip7pt%\s*\\leavevmode%\s*"
    r"\\hbox to \\paperwidth\{%\s*"
    r"\\hfill\\scriptsize\\insertframenumber\{\}\s*/\s*"
    r"\\inserttotalframenumber\\hspace\*\{9pt\}%\s*"
    r"\}%\s*\\vskip5pt%\s*\}", re.M)
SAFE_HEADLINE = (
    "\\setbeamertemplate{headline}{%\n"
    "  \\vskip7pt%\n"
    "  \\leavevmode%\n"
    "  \\hbox to \\paperwidth{%\n"
    "    \\hfill\\scriptsize\\insertframenumber{} / \\inserttotalframenumber"
    "\\hspace*{9pt}%\n"
    "  }%\n"
    "  \\vskip5pt%\n"
    "}"
)

def normalize_legacy_headline(tex: str) -> tuple[str,str]:
    """Change only exact known beamer metadata preamble; never frame content."""
    if not isinstance(tex, str) or not tex.strip():
        raise ValueError("Missing original generated Beamer source")
    safe_matches=list(SAFE_VARIANT.finditer(tex))
    if safe_matches:
        if len(safe_matches)!=1 or LEGACY_HEADLINE.search(tex):
            raise ValueError("Ambiguous or repeated Beamer metadata headline")
        match=safe_matches[0]
        canonical=tex[:match.start()]+SAFE_HEADLINE+tex[match.end():]
        return canonical,("ALREADY_SAFE_HEADLINE" if canonical==tex else
                          "SAFE_HEADLINE_CANONICALIZED")
    matches=list(LEGACY_HEADLINE.finditer(tex))
    if len(matches)!=1:
        if len(matches)>1:
            raise ValueError("Multiple legacy metadata headline definitions")
        # Unknown / no headline: do not guess and modify content.
        return tex,"NO_RECOGNIZED_LEGACY_HEADLINE"
    from .recovery_registry import lookup_mechanism
    try:
        registered=lookup_mechanism(
            "slide_layout_repair","LEGACY_BEAMER_TOP_EDGE_SLIDE_COUNTER")
    except (ValueError,OSError) as exc:
        raise ValueError("Known Beamer repair registry is invalid") from exc
    if registered!="INSET_BEAMER_COUNTER_TWO_PASS_PHYSICAL_PROOF":
        raise ValueError("Known Beamer repair not registered or retired")
    start,end=matches[0].span()
    updated=tex[:start]+SAFE_HEADLINE+tex[end:]
    if updated.replace(SAFE_HEADLINE,tex[start:end],1)!=tex:
        raise ValueError("Beamer repair changed anything beyond headline")
    return updated,"KNOWN_LEGACY_HEADLINE_RECOVERED"

def verify_slide_counter_pdf(pdf_file: Path,*,min_top_inset_pt=1.0,
                             min_right_inset_pt=5.0) -> dict:
    """Independently inspect every compiled counter's physical PDF text box."""
    import pymupdf
    pdf_file=Path(pdf_file)
    if not pdf_file.is_file() or pdf_file.is_symlink():
        raise ValueError("Actual unlinked Beamer PDF needed")
    evidence=[]
    with pymupdf.open(pdf_file) as doc:
        if not 1<=len(doc)<=250:
            raise ValueError("Invalid generated presentation page count")
        total=len(doc)
        for index,page in enumerate(doc,1):
            expected=f"{index} / {total}"
            hits=[]
            for block in page.get_text("dict").get("blocks",[]):
                if block.get("type")!=0:
                    continue
                for line in block.get("lines",[]):
                    for span in line.get("spans",[]):
                        if re.fullmatch(r"\d+\s*/\s*\d+",span.get("text","").strip()):
                            hits.append(span)
            if len(hits)!=1 or " ".join(hits[0]["text"].split())!=expected:
                raise ValueError(f"PDF slide {index}: unique correct {expected} counter missing")
            x0,y0,x1,y1=map(float,hits[0]["bbox"])
            if not (x0>=0 and y0>=min_top_inset_pt
                    and x1<=page.rect.width-min_right_inset_pt
                    and y1<max(28.0,.14*page.rect.height)):
                raise ValueError(
                    f"PDF slide {index}: page counter touches/crosses top or right edge")
            evidence.append({"slide":index,"counter":expected,
                             "bbox_pt":[round(v,3) for v in (x0,y0,x1,y1)]})
    return {"status":"REAL_BEAMER_PAGE_COUNTERS_PHYSICALLY_VERIFIED",
            "slide_count":len(evidence),
            "counter_geometry":evidence,
            "mathematics_approved":False,
            "scientific_review_approved":False,
            "paid_tts_authorized":False,
            "student_publication_authorized":False}

def verify_existing_slide_counter_contract(*,tex_file:Path,pdf_file:Path)->dict:
    """Reject known clipped/incorrect MicroGen counters before cache adoption.

    This is a READ-ONLY predicate for ordinary, previously generated Beamer
    decks. The normal new-slide producer owns automatic deterministic
    normalization and two-pass compilation; cached/accepted decks must not
    be rewritten without a separately authorized, versioned output.
    """
    tex_file,pdf_file=Path(tex_file),Path(pdf_file)
    if (not tex_file.is_file() or tex_file.is_symlink()
            or not pdf_file.is_file() or pdf_file.is_symlink()):
        raise ValueError("Unlinked existing Beamer TeX and PDF are required")
    source=tex_file.read_text(encoding="utf8")
    old=list(LEGACY_HEADLINE.finditer(source))
    safe=list(SAFE_VARIANT.finditer(source))
    if len(old)>1 or len(safe)>1 or (old and safe):
        raise ValueError("Ambiguous known Beamer page-counter template")
    if old:
        # The exact historical counter was measured at/over the top edge.
        # Never rubber-stamp or silently rewrite a previously accepted deck.
        raise ValueError(
            "Known legacy Beamer headline requires versioned normalized candidate")
    if safe:
        verified=verify_slide_counter_pdf(pdf_file)
        return {"status":"KNOWN_SAFE_HEADLINE_AND_PHYSICAL_PDF_VERIFIED",
                "slide_count":verified["slide_count"],
                "pdf_counter_geometry_verified":True,
                "source_tex_modified":False,
                "source_pdf_modified":False,
                "academic_approval":False}
    return {"status":"NO_RECOGNIZED_MICROGEN_PAGE_COUNTER_LAYOUT",
            "pdf_counter_geometry_verified":False,
            "source_tex_modified":False,"source_pdf_modified":False,
            "academic_approval":False}

def recover_versioned_legacy_counter_deck(*, original_folder:Path,
                                          checkpoint_root:Path)->dict:
    """Automatically create a distinct, immutable, locally rendered candidate.

    Use this only for the exact historical metadata headline. It never writes
    original TeX/PDF, resets scientific QA, submits Gemini prompts, calls
    billable APIs, or publishes a candidate. A content-identified record is
    idempotently reused; a torn local build has at most one further attempt.
    """
    import hashlib
    import json
    import os
    import shutil
    import subprocess

    def hash_file(path):
        digest=hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b""):
                digest.update(chunk)
        return digest.hexdigest()

    def new_json(path,obj):
        with path.open("x",encoding="utf8") as out:
            json.dump(obj,out,sort_keys=True,indent=2)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())

    source=Path(original_folder).absolute()
    parent=Path(checkpoint_root).absolute()
    if (not source.is_dir() or source.is_symlink()
            or not parent.is_dir() or parent.is_symlink()
            or parent==source or parent.is_relative_to(source)):
        raise ValueError("Versioned counter recovery needs separate unlinked source and checkpoint roots")
    inputs={name:source/name for name in ("source.pdf","slides.tex","slides.pdf")}
    if any(not p.is_file() or p.is_symlink() or p.stat().st_size<=0
           for p in inputs.values()):
        raise ValueError("Original PDF and both existing slide artifacts required")
    if any(p.stat().st_size>32_000_000 for p in inputs.values()):
        raise ValueError("Oversized original Beamer input")
    before={name:hash_file(path) for name,path in inputs.items()}
    original_tex=inputs["slides.tex"].read_text(encoding="utf8")
    normalized,action=normalize_legacy_headline(original_tex)
    if action!="KNOWN_LEGACY_HEADLINE_RECOVERED":
        raise ValueError("Only known old MicroGen headline is eligible for counter recovery")
    if normalized==original_tex:
        raise ValueError("No changed exact known headline to repair")
    import pymupdf
    with pymupdf.open(inputs["slides.pdf"]) as original:
        old_count=len(original)
    if not 1<=old_count<=250:
        raise ValueError("Invalid original presentation page count")
    candidates=[p for p in source.iterdir() if p.suffix.lower() in (
        ".png",".jpg",".jpeg",".sty")]
    if (len(candidates)>60 or any(
            not p.is_file() or p.is_symlink() or p.stat().st_size>32_000_000
            for p in candidates)
            or sum(p.stat().st_size for p in candidates)>100_000_000):
        raise ValueError("Unsupported linked, oversized or excessive Beamer assets")
    identity=hashlib.sha256((
        str(source).lower()+"|"+before["source.pdf"]+"|"+
        before["slides.tex"]+"|"+before["slides.pdf"]).encode("utf8")).hexdigest()
    base=parent/"beamer_counter_candidate_v1"
    home=base/identity
    claim={"schema_version":1,"identity_sha256":identity,
           "original_input_sha256":before,
           "original_page_count":old_count,
           "repair_signature":"LEGACY_BEAMER_TOP_EDGE_SLIDE_COUNTER",
           "original_modified":False,"new_model_requests":0,
           "academic_approval":False,"student_publication_authorized":False}
    from .three_pc_worker import LocalInstanceLock
    with LocalInstanceLock("beamer_counter_"+identity[:24],
                           parent/"beamer_counter_locks"):
        base.mkdir(parents=True,exist_ok=True)
        if not home.exists():
            home.mkdir(exist_ok=False)
            new_json(home/"claim.json",claim)
        if not home.is_dir() or home.is_symlink():
            raise ValueError("Unsafe versioned Beamer candidate location")
        claim_path=home/"claim.json"
        # A crash after creating the empty content-addressed directory but
        # before writing the local claim is CERTIFIED no-compile/no-Send.
        # Reuse only an entirely empty directory; arbitrary partial contents
        # without a claim are unsafe and must not be reinterpreted.
        if not claim_path.exists() and not any(home.iterdir()):
            new_json(claim_path,claim)
        if (not claim_path.is_file() or claim_path.is_symlink()
                or json.loads(claim_path.read_text("utf8"))!=claim):
            raise ValueError("Candidate source/claim identity is missing or changed")

        def check_existing(saved):
            if (type(saved) is not dict
                    or saved.get("schema_version")!=1
                    or saved.get("status")!="VERSIONED_BEAMER_COUNTER_PDF_VERIFIED"
                    or saved.get("identity_sha256")!=identity
                    or saved.get("original_input_sha256")!=before
                    or saved.get("original_page_count")!=old_count
                    or saved.get("new_model_requests")!=0
                    or saved.get("original_modified") is not False
                    or saved.get("academic_approval") is not False
                    or saved.get("student_publication_authorized") is not False
                    or saved.get("candidate_relative_path") not in
                         ("attempt_01","attempt_02")):
                raise ValueError("Candidate receipt did not verify original source")
            deck=home/saved["candidate_relative_path"]
            tex,pdf=deck/"slides.tex",deck/"slides.pdf"
            if (not deck.is_dir() or deck.is_symlink()
                    or not tex.is_file() or tex.is_symlink()
                    or not pdf.is_file() or pdf.is_symlink()
                    or hash_file(tex)!=saved.get("candidate_tex_sha256")
                    or hash_file(pdf)!=saved.get("candidate_pdf_sha256")
                    or tex.read_text("utf8")!=normalized):
                raise ValueError("Versioned counter candidate content changed")
            # Asset bytes are part of the rendered geometry even though the
            # model-source PDFs remain unchanged. Neither a stale figure nor
            # a rewritten candidate image can inherit prior verification.
            asset_names={p.name for p in candidates}
            present_assets={p.name for p in deck.iterdir() if
                            p.suffix.lower() in (".png",".jpg",".jpeg",".sty")}
            if (present_assets!=asset_names or any(
                    not (deck/p.name).is_file() or
                    (deck/p.name).is_symlink() or
                    hash_file(deck/p.name)!=hash_file(p)
                    for p in candidates)):
                raise ValueError("Versioned candidate figure assets changed")
            tested=verify_slide_counter_pdf(pdf)
            if tested["slide_count"]!=old_count:
                raise ValueError("Versioned deck page count changed")
            if any(hash_file(p)!=before[name] for name,p in inputs.items()):
                raise ValueError("Original source changed since stored counter repair")
            return {**saved,"candidate_tex_path":str(tex),
                    "candidate_pdf_path":str(pdf),
                    "reused_verified_candidate":True}

        receipt=home/"result.json"
        if receipt.exists():
            if not receipt.is_file() or receipt.is_symlink():
                raise ValueError("Versioned counter receipt is unsafe")
            return check_existing(json.loads(receipt.read_text("utf8")))
        if (home/"deterministic_failure.json").exists():
            raise ValueError("Prior deterministic counter repair failed, do not repeat")
        next_attempt=next((
            i for i in (1,2) if not (home/f"attempt_{i:02d}").exists()),None)
        if next_attempt is None:
            raise ValueError("Finite local counter recovery budget exhausted")
        attempt=home/f"attempt_{next_attempt:02d}"
        attempt.mkdir(exist_ok=False)
        (attempt/"slides.tex").write_text(normalized,encoding="utf8")
        for asset in candidates:
            shutil.copy2(asset,attempt/asset.name)
        if (any(hash_file(p)!=before[name] for name,p in inputs.items())
                or any(hash_file(attempt/p.name)!=hash_file(p)
                       for p in candidates)):
            raise ValueError("Original inputs/assets changed while staging versioned deck")
        command=["pdflatex","-interaction=nonstopmode","-halt-on-error",
                 "-no-shell-escape","slides.tex"]
        for pass_number in (1,2):
            try:
                produced=subprocess.run(command,cwd=attempt,
                    stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                    text=True,timeout=150,check=False)
            except (OSError,subprocess.TimeoutExpired) as exc:
                new_json(home/"deterministic_failure.json",{
                    "schema_version":1,"status":"LOCAL_NATIVE_COMPILE_UNAVAILABLE",
                    "error_class":type(exc).__name__,"new_model_requests":0})
                raise ValueError("Native Beamer compile unavailable, no retry") from exc
            (attempt/f"compile_pass_{pass_number}.log").write_text(
                produced.stdout or "",encoding="utf8")
            if produced.returncode:
                new_json(home/"deterministic_failure.json",{
                    "schema_version":1,"status":"LOCAL_NATIVE_COMPILE_FAILED",
                    "pass":pass_number,"exit_code":produced.returncode,
                    "new_model_requests":0})
                raise ValueError("Native Beamer repair failed; original untouched")
        try:
            verified=verify_slide_counter_pdf(attempt/"slides.pdf")
            if verified["slide_count"]!=old_count:
                raise ValueError("Versioned slide count changed from original")
        except (ValueError,OSError) as exc:
            new_json(home/"deterministic_failure.json",{
                "schema_version":1,"status":"LOCAL_PHYSICAL_COUNTER_VERIFICATION_FAILED",
                "error_class":type(exc).__name__,"new_model_requests":0})
            raise
        if any(hash_file(p)!=before[name] for name,p in inputs.items()):
            raise ValueError("Original inputs changed after compilation")
        saved={"schema_version":1,
               "status":"VERSIONED_BEAMER_COUNTER_PDF_VERIFIED",
               "identity_sha256":identity,"original_input_sha256":before,
               "original_page_count":old_count,
               "candidate_relative_path":attempt.name,
               "candidate_tex_sha256":hash_file(attempt/"slides.tex"),
               "candidate_pdf_sha256":hash_file(attempt/"slides.pdf"),
               "new_model_requests":0,"original_modified":False,
               "academic_approval":False,"student_publication_authorized":False}
        new_json(receipt,saved)
        return check_existing(saved)
