from __future__ import annotations
import json,re,hashlib
from pathlib import Path

# "sixteen oh eight" and "sixteen zero eight" denote the same YEAR (1608),
# not arbitrary scientific values. Source PDF must print the exact year.
_CENTURIES={"ten":10,"eleven":11,"twelve":12,"thirteen":13,"fourteen":14,"fifteen":15,
"sixteen":16,"seventeen":17,"eighteen":18,"nineteen":19,"twenty":20}
_DIGITS={"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9}
_WORDS=re.compile(r"[a-z]+")
def _normal(text):
    return " ".join(_WORDS.findall(str(text).lower().replace("-"," ")))
def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def apply(folder:Path,report:dict)->dict:
    folder=Path(folder)
    if not isinstance(report,dict):raise ValueError("Report must be a dict")
    issues=[s for s in report.get("slides",[]) if s.get("status")!="pass"]
    if not issues:return report
    source=folder/"source.pdf"
    if not source.is_file() or source.is_symlink():return report
    result=json.loads(json.dumps(report))
    import pymupdf
    with pymupdf.open(source) as pdf:
        src=" ".join(pg.get_text() for pg in pdf)
    amended=[]
    for item in result.get("slides",[]):
        if item.get("status")=="pass":continue
        critical=item.get("critical_token_issues") or []
        if len(critical)!=1 or critical[0].get("category")!="number":continue
        if item.get("audio_defects") or item.get("pronunciation_issues"):continue
        if float(item.get("fidelity_percent",0))<float(result.get("threshold_percent",99)):continue
        q=critical[0]
        reference=_normal(q.get("script_text",""))
        actual=_normal(q.get("heard_as",""))
        m=re.fullmatch(r"([a-z]+) zero ([a-z]+)",reference)
        n=re.fullmatch(r"([a-z]+) (?:o|oh) ([a-z]+)",actual)
        if not m or not n or m.group(1)!=n.group(1) or m.group(2)!=n.group(2):continue
        if m.group(1) not in _CENTURIES or m.group(2) not in _DIGITS:continue
        year=100*_CENTURIES[m.group(1)]+_DIGITS[m.group(2)]
        if not 1001<=year<=2099 or not re.search(r"(?<!\d)"+str(year)+r"(?!\d)",src):continue
        written=_normal(item.get("ground_truth",""))
        spoken=_normal(item.get("transcript",""))
        if written.count(reference)!=1 or spoken.count(actual)!=1:continue
        if written.replace(reference,"YEAR",1)!=spoken.replace(actual,"YEAR",1):continue
        wav=folder/str(item.get("audio_file",""))
        if not wav.is_file() or wav.is_symlink():continue
        item["original_critical_token_issues"]=critical
        item["critical_token_issues"]=[]
        item["status"]="pass"
        item["source_verified_spoken_year_zero_variant"]={
          "status":"PASS_SOURCE_PRINTED_YEAR_SAME_VALUE","year":year,
          "script_phrase":q["script_text"],"heard_phrase":q["heard_as"],
          "source_pdf_sha256":_sha(source),"wav_sha256":_sha(wav),
          "audio_replaced":False,"source_or_numeric_value_changed":False,
          "raw_listener_evidence_preserved":True}
        amended.append(item["slide"])
    if amended:
        result["summary"]["passed"]=sum(s.get("status")=="pass" for s in result["slides"])
        result["summary"]["review"]=sum(s.get("status")!="pass" for s in result["slides"])
        result["summary"]["blocking_failures"]=result["summary"]["review"]
        result["source_verified_spoken_year_zero_recovery_v1"]={"slides":amended,"no_new_audio_or_model_request":True}
    return result
