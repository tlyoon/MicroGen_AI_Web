"""Rebind verified unchanged narration to one isolated, visually corrected slide.

This only emits a new REVIEW-only authored plan and cryptographic evidence.
It does not issue TTS requests, edit WAVs, or mark speech/academic approval.
All non-target rendered slides must be pixel-identical; all slide text and
embedded image bytes must be identical, including on the target page.
"""
from __future__ import annotations
import argparse,hashlib,json,wave
from pathlib import Path
import pymupdf
from .element_narration_stage import rectangle,normalize

def sha(p:Path)->str:
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""):h.update(b)
    return h.hexdigest()

def check(value,msg):
    if not value: raise ValueError(msg)

def save(path,data):
    with path.open("x",encoding="utf8") as f:
        json.dump(data,f,indent=2,ensure_ascii=False)
        f.write("\n")

def rebind(*,source:Path,old_slides:Path,new_slides:Path,voice_plan:Path,
           audio:Path,figure_receipt:Path,out_plan:Path,out_receipt:Path)->dict:
    paths=[Path(x).resolve() for x in
           (source,old_slides,new_slides,voice_plan,audio,figure_receipt,out_plan,out_receipt)]
    source,old_slides,new_slides,voice_plan,audio,figure_receipt,out_plan,out_receipt=paths
    check(all(p.is_file() and not p.is_symlink() for p in
              (source,old_slides,new_slides,voice_plan,figure_receipt)),
          "Missing source PDF, slides, frozen narration plan or figure receipt")
    check(audio.is_dir() and not audio.is_symlink(),"Audio folder missing")
    check(out_plan!=out_receipt and not out_plan.exists() and not out_receipt.exists()
          and out_plan.parent.is_dir() and out_receipt.parent.is_dir(),
          "Output plan and receipt must be new")
    for new in (out_plan,out_receipt):
        check(not new.is_relative_to(source.parent)
              and not new.is_relative_to(old_slides.parent)
              and not new.is_relative_to(new_slides.parent)
              and not new.is_relative_to(audio),
              "Refuse to write in source, corrected PDF, or audio folder")
    original=json.loads(voice_plan.read_text(encoding="utf8"))
    resize=json.loads(figure_receipt.read_text(encoding="utf8"))
    job=json.loads((audio/"tts_synthesis_receipt.json").read_text(encoding="utf8"))
    check(original.get("status")=="author_specified_unapproved_element_narration"
          and original["source_sha256"]==sha(source)
          and original["slides_sha256"]==sha(old_slides),
          "Original voice-bound plan or input provenance changed")
    check(resize["status"]=="REVIEW_ONLY_ISOLATED_FIGURE_RESIZE"
          and resize["source_slides_sha256"]==sha(old_slides)
          and resize["derived_slides_sha256"]==sha(new_slides)
          and resize["production_approved"] is False,
          "Correction receipt not bound to both exact PDFs")
    check(job["status"]=="real_gemini_tts_generated_review_only_word_fidelity_unverified"
          and job["voice"]=="Kore" and job["model"]=="gemini-3.8-flash-lite-tts"
          and job["provider"]=="gemini"
          and job["same_declared_voice_all_segments"] is True
          and job["audible_word_fidelity_verified"] is False,
          "Unapproved or inconsistent original TTS synthesis")
    elements=[el for part in original["parts"] for slide in part["slides"]
              for el in slide["elements"]]
    audio_index={row["filename"]:row for row in job["segments"]}
    check(len(audio_index)==len(job["segments"])==len(elements),
          "Audio-to-element cardinality mismatch")
    for el in elements:
        filename=el["wav"]
        clip=audio/filename
        proof=audio/(filename+".verified.json")
        check(filename in audio_index and clip.is_file() and proof.is_file()
              and not clip.is_symlink() and not proof.is_symlink(),
              "Missing or unsafe source WAV/proof")
        record=audio_index[filename]
        verified=json.loads(proof.read_text(encoding="utf8"))
        expected=hashlib.sha256(el["spoken_text"].encode("utf8")).hexdigest()
        check(record["spoken_text_sha256"]==verified["spoken_text_sha256"]==expected
              and record["wav_sha256"]==verified["wav_sha256"]==sha(clip)
              and verified["voice"]=="Kore"
              and verified["model"]=="gemini-3.8-flash-lite-tts",
              "Cannot reuse audio: waveform, transcript or voice provenance mismatch")
        with wave.open(str(clip),"rb") as w:
            check(w.getnchannels()==1 and w.getsampwidth()==2
                  and w.getframerate()==24000
                  and w.getcomptype()=="NONE",
                  "Incompatible source audio wave format")
    target=int(resize["target_slide"])
    changed=[]
    anchor_diffs=[]
    with pymupdf.open(old_slides) as old,pymupdf.open(new_slides) as new:
        check(len(old)==len(new) and len(old)>0 and 1<=target<=len(old),
              "Changed slide count or invalid target")
        for idx,(a,b) in enumerate(zip(old,new),1):
            check(a.rect==b.rect and a.rotation==b.rotation,
                  "Slide geometry dimensions or rotation changed")
            check(normalize(a.get_text())==normalize(b.get_text()),
                  "Rendered slide mathematical text changed")
            aa,bb=a.get_images(full=True),b.get_images(full=True)
            check(len(aa)==len(bb),"Embedded image count changed")
            for x,y in zip(aa,bb):
                check(hashlib.sha256(old.extract_image(x[0])["image"]).digest()==
                      hashlib.sha256(new.extract_image(y[0])["image"]).digest(),
                      "Embedded figure pixels changed/cropped")
            p=a.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False)
            q=b.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False)
            if hashlib.sha256(p.samples).digest()!=hashlib.sha256(q.samples).digest():
                changed.append(idx)
        check(changed==[target],"Other rendered slides changed: "+str(changed))
        for part in original["parts"]:
            for scene in part["slides"]:
                slide_number=scene["slide"]
                for item in scene["elements"]:
                    before,kind1=rectangle(old[slide_number-1],item["anchor"])
                    try:
                        after,kind2=rectangle(new[slide_number-1],item["anchor"])
                    except Exception as exc:
                        raise ValueError(f"Corrected slide {slide_number} element {item['wav']!r} anchor {item['anchor']!r} failed: {exc}") from exc
                    check(kind1==kind2,"Semantic anchor type changed")
                    if slide_number!=target:
                        check(max(abs(x-y) for x,y in zip(before,after))<0.5,
                              "Anchor drift on an otherwise identical slide")
                    elif before!=after:
                        anchor_diffs.append({"wav":item["wav"],"kind":kind1,
                            "before_bbox":[round(v,3) for v in before],
                            "after_bbox":[round(v,3) for v in after]})
    check(anchor_diffs,"No changed target-slide anchor geometry found")
    revised=json.loads(json.dumps(original))
    revised["slides_sha256"]=sha(new_slides)
    revised["layout_only_rebind_from_voice_plan_sha256"]=sha(voice_plan)
    revised["layout_only_rebind_receipt_sha256"]=sha(figure_receipt)
    receipts={
        "status":"REVIEW_ONLY_LAYOUT_REBIND_SAME_NARRATION_NOT_CERTIFIED",
        "source_sha256":sha(source),
        "old_slides_sha256":sha(old_slides),
        "new_slides_sha256":sha(new_slides),
        "old_voice_bound_plan_sha256":sha(voice_plan),
        "tts_synthesis_receipt_sha256":sha(audio/"tts_synthesis_receipt.json"),
        "figure_resize_receipt_sha256":sha(figure_receipt),
        "changed_slide_numbers":changed,
        "changed_element_anchors":anchor_diffs,
        "narration_wav_count":len(elements),
        "all_original_wav_bytes_and_text_hashes_verified":True,
        "same_named_tts_voice":True,
        "audio_regeneration_required_if_spoken_words_changed":True,
        "independent_asr_verified_all":False,
        "academic_approval":False,"production_approved":False,
        "video_rerender_and_pixel_revalidation_required":True
    }
    save(out_plan,revised)
    save(out_receipt,receipts)
    return {"status":receipts["status"],"wav_count":len(elements),
            "changed_slides":changed,"changed_element_anchors":anchor_diffs,
            "new_plan":str(out_plan),"receipt":str(out_receipt)}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("source","old-slides","new-slides","voice-plan","audio",
                 "figure-receipt","out-plan","out-receipt"):
        p.add_argument("--"+name,required=True,type=Path)
    a=vars(p.parse_args(argv))
    args={name.replace("-","_"):value for name,value in a.items()}
    print(json.dumps(rebind(**args),indent=2))
if __name__=="__main__":main()
