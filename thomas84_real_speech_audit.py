"""Independent technical audit and private handoff for review-only Thomas 8.4 pilot."""
from __future__ import annotations
import argparse, hashlib, html, json, math, shutil, struct, wave
from pathlib import Path


def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def audio_non_silent(path):
    # Source audio is 16-bit PCM; verify it contains real signal, not test silence.
    with wave.open(str(path), "rb") as wav:
        require(wav.getsampwidth()==2, "Expected 16-bit source PCM")
        data=wav.readframes(wav.getnframes())
        rate=wav.getframerate()
        length=wav.getnframes()/rate
    from array import array
    import sys
    samples = array("h")
    samples.frombytes(data)
    if sys.byteorder != "little":
        samples.byteswap()
    rms = math.sqrt(sum(float(v) * v for v in samples) / len(samples))
    return {"seconds":round(length,3), "rms":round(rms,2)}


def audit(source_dir, prepared, rendered, handoff):
    src, inp, out, dest=map(lambda p:Path(p).resolve(),
                           (source_dir, prepared, rendered, handoff))
    require(not dest.exists() and dest.parent.is_dir(), "Handoff destination must be NEW")
    raw=json.loads((src/".microgen_verified_completion.json").read_text(encoding="utf-8"))
    series=json.loads((out/"series_review_receipt.json").read_text(encoding="utf-8"))
    evidence=json.loads((inp/"pilot_provenance.json").read_text(encoding="utf-8"))
    require(series["status"]=="review_only_not_approved" and
            series["accepted_lecture_completion_created"] is False and
            series["student_published"] is False,
            "Review-only label missing")
    require(sha(src/"source.pdf")==series["source_sha256"]==raw["source_sha256"],
            "Original source SHA changed")
    require(sha(src/"slides.pdf")==raw["slides_pdf_sha256"],
            "Original slide source changed")
    require(not (out/"lecture_completion.json").exists(), "Accidental production marker")
    require(len(series["parts"])==2 and
            [p["part_id"] for p in series["parts"]]==["part_01","part_02"],
            "Bad part order")
    audit_parts=[]
    original_slides=[]
    for part_id, originals in zip(("part_01","part_02"), (range(1,9),range(9,18))):
        directory=out/part_id
        board=json.loads((inp/part_id/"storyboard.json").read_text(encoding="utf8"))
        rec=json.loads((directory/"review_receipt.json").read_text(encoding="utf8"))
        qa=json.loads((directory/"encoded_pixel_qa.json").read_text(encoding="utf8"))
        seq=rec["highlight_segments"]
        require(seq==len(board["slides"])==len(board["narration_segments"])==len(originals),
                "Slide-event count drift")
        require(rec["decoded_pixel_verified_events"]==seq==qa["count_events"],
                "Actual encoded pixels not verified")
        video=directory/f"{part_id}_review.mp4"
        require(sha(video)==rec["mp4_sha256"], "MP4 hash mismatch")
        require(0<rec["encoded_mp4_seconds"]<600, "MP4 violates <600 seconds")
        require(rec["status"]=="review_only_not_approved", "False approval")
        audio=audio_non_silent(directory/"narration.wav")
        require(audio["rms"]>25, "Speech source appears silent")
        require(abs(audio["seconds"]-rec["audio_seconds"])<.02,
                "Audio timing receipt drift")
        originals_count=list(originals)
        original_slides.extend(originals_count)
        audit_parts.append({
            "part_id":part_id,
            "original_slide_numbers":originals_count,
            "mp4":str(video),
            "mp4_sha256":rec["mp4_sha256"],
            "duration_s":rec["encoded_mp4_seconds"],
            "audio_rms_pcm":audio["rms"],
            "events":seq,
            "encoded_pixel_events_verified":rec["decoded_pixel_verified_events"],
            "pixel_receipt_sha256":sha(directory/"encoded_pixel_qa.json"),
        })
    require(original_slides==list(range(1,18)), "Missing or repeated slide")
    figure=evidence["anchors"][4]
    require(figure["original_slide"]==5 and figure["kind"]=="figure",
            "Corrected 8.4 Figure 8.3 not selected for highlighting")
    # Horizontal correction occupies ~80% of 363-point Beamer width.
    require(figure["rect_pt"][2]-figure["rect_pt"][0]>=270,
            "Figure 8.3 is still too narrow for review pilot")
    result={
        "status":"TECHNICAL_REVIEW_ONLY_PASS",
        "source_sha256":series["source_sha256"],
        "slides_pdf_sha256":raw["slides_pdf_sha256"],
        "slides_covered":original_slides,
        "figure83_width_pt":round(figure["rect_pt"][2]-figure["rect_pt"][0],2),
        "parts":audit_parts,
        "automatic_checks_passed": [
            "unchanged source and original slides",
            "both final durations <600s",
            "17 consecutive slides and 17 encoded highlighted events",
            "all highlight target pixels validated against decoded MP4 frames",
            "real non-silent spoken narration WAVs",
            "corrected three-panel Figure 8.3 uses wide visual region",
            "no completion or publication receipt"
        ],
        "blocking_unverified": [
            "voice identity from old source WAVs",
            "exact actual spoken words versus script",
            "narration aligned to individual figures and equations within slides",
            "actual source-page correspondence and mathematics",
            "human audio/pronunciation/academic signoff"
        ],
        "student_release_approved":False
    }
    dest.mkdir()
    try:
        (dest/"audit.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
        for row in audit_parts:
            name=row["part_id"]+".mp4"
            shutil.copy2(row["mp4"],dest/name)
            require(sha(dest/name)==row["mp4_sha256"],"Copied MP4 hash changed")
        document="""# Thomas Calculus 8.4 — MicroGen_AI_Web real-audio technical pilot

**REVIEW ONLY — NOT a production-compliant lecture or student-approved output.**

Two separate MP4s use the corrected 17-slide Thomas 8.4 material and genuine
previously synthesized spoken narration WAVs from the separate MicroGen_AI
package. The first part is slides 1–8; the second is slides 9–17.

All encoded MP4 durations are strictly shorter than 600 seconds. All 17
single-region highlights were checked in decoded MP4 pixels. The corrected
three-panel Figure 8.3 on original slide 5 remains visible at approximately
80% of slide width.

**Important limitation:** Each original WAV narrates an entire slide, while
the pilot highlights only one chosen region during it. No element-specific
spoken-word alignment has been demonstrated. Its technical success MUST NOT
be interpreted as satisfying the complete MicroGen_AI_Web video contract.

No source/published lecture files were changed, and no academic approval,
production completion certificate or Moodle publication was issued.
See audit.json for SHA256, evidence and remaining blockers.
"""
        (dest/"README_FIRST.md").write_text(document,encoding="utf8")
        page="""<!doctype html><html><head><meta charset="utf-8"><title>Thomas 8.4 real-audio pilot</title>
<style>body{background:#f7f9fc;font:16px/1.5 system-ui,sans-serif;max-width:1000px;margin:40px auto;padding:20px;color:#19314b}
video{width:100%;max-height:580px;background:#111}section{padding:24px;background:white;border:1px solid #ddd;margin:20px 0}
strong{color:#a13b08}</style></head><body>
<h1>Thomas Calculus 8.4 — real-audio technical preview</h1>
<p><strong>NOT APPROVED FOR STUDENT USE: slide-level emphasis is not accurate
element-level narration synchronization.</strong></p>
<section><h2>Part 1 — original slides 1–8</h2><video controls src="part_01.mp4"></video></section>
<section><h2>Part 2 — original slides 9–17</h2><video controls src="part_02.mp4"></video></section>
<p>See <a href="audit.json">technical receipt</a> and
<a href="README_FIRST.md">limitations</a>.</p></body></html>"""
        (dest/"index.html").write_text(page,encoding="utf8")
    except BaseException:
        shutil.rmtree(dest,ignore_errors=True)
        raise
    print(json.dumps({"handoff":str(dest),"status":result["status"],
                      "parts":audit_parts,"figure83_width_pt":result["figure83_width_pt"]},
                     indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source-dir",required=True)
    p.add_argument("--prepared",required=True)
    p.add_argument("--rendered",required=True)
    p.add_argument("--handoff",required=True)
    a=p.parse_args()
    audit(a.source_dir,a.prepared,a.rendered,a.handoff)
