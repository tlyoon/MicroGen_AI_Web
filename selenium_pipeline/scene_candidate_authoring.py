"""Generic review-only PDF-to-element authoring candidate extractor.

No narration, no guessed equations, no approval. Builds reproducible visual
targets, evidence hints and source-page candidates so authoring can be
accelerated while preserving mandatory scholarly/editorial review. The JSON
is intentionally NOT consumable by the TTS or production staging gate.
"""
from __future__ import annotations
import argparse,hashlib,json,re,unicodedata
from collections import Counter
from pathlib import Path
import pymupdf

STOP=set("the and for with from what that this into are can have will your they each when then plus an to of or a x u is in on by as at be we it".split())

def hash_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""):h.update(b)
    return h.hexdigest()

def terms(t:str)->list[str]:
    t=unicodedata.normalize("NFKC",t).casefold()
    return [w for w in re.findall(r"[a-z][a-z0-9]{2,}",t) if w not in STOP]

def best_pages(text:str,original:list[str])->list[dict]:
    words=Counter(terms(text))
    if not words:return []
    scored=[]
    for k,page in enumerate(original,1):
        hits=Counter(terms(page))
        numerator=sum(min(v,hits.get(w,0)) for w,v in words.items())
        denom=sum(words.values())
        score=numerator/denom if denom else 0.0
        if score>0:scored.append({"source_page":k,"word_overlap":round(score,3)})
    return sorted(scored,key=lambda a:(-a["word_overlap"],a["source_page"]))[:3]

def visible_multi_panel_labels(text_blocks:list[str])->list[str]:
    """Conservative evidence of captioned subpanels, independent of image aspect.

    A text block explicitly naming (a) and (b), etc., is enough to REQUIRE
    panel review for images on that slide. It never certifies image panels,
    their identities or source meaning. A single '(a)' is not evidence.
    """
    for text in text_blocks:
        labels=re.findall(r"(?<![A-Za-z0-9])\(([a-d])\)(?![A-Za-z0-9])",
                          str(text),flags=re.IGNORECASE)
        distinct=sorted({s.lower() for s in labels})
        if len(distinct)>=2:
            return distinct
    return []


def draft(source:Path,slides:Path)->dict:
    if not source.is_file() or not slides.is_file():
        raise FileNotFoundError("A readable source.pdf and slides.pdf are required")
    with pymupdf.open(source) as original,pymupdf.open(slides) as rendered:
        if not original.page_count or not rendered.page_count:
            raise ValueError("Empty PDF cannot be authored")
        sourcepages=[p.get_text() for p in original]
        scenes=[]
        for i,page in enumerate(rendered,1):
            strings=[]
            targets=[]
            skipped=[]
            body=[]
            for j,block in enumerate(page.get_text("blocks")):
                if len(block)<5 or not isinstance(block[4],str):
                    continue
                value=" ".join(block[4].split())
                if not value:continue
                rect=pymupdf.Rect(block[:4])
                if rect.y0<35:
                    if len(value)>3: strings.append(value)
                    continue
                if rect.y1>page.rect.height-15:continue
                body.append(value)
                if len(value)<9 or rect.width<20 or rect.height<6:
                    skipped.append(j)
                    continue
                targets.append({
                    "draft_element_id":f"s{i:03d}.text.{j:03d}",
                    "type":"text_block",
                    "anchor":{"type":"text_block","index":j,
                              "text_evidence":value[:min(35,len(value))]},
                    "rect_pt":[round(x,2) for x in rect],
                    "visible_text":value[:500],
                    "proposed_spoken_text":None,
                    "review_required":True})
            # A displayed mathematical derivation may be split across
            # 2–3 physically adjacent PDF text blocks by Beamer/PyMuPDF.
            # Produce review-only bounded *grouped visual targets*, rather
            # than forcing the narrator to focus on a random fraction piece.
            from .sourcebound_multiblock_text_focus import discover_groups
            targets.extend(discover_groups(page,i,targets))
            # A portrait/square montage may contain (a), (b), (c). Aspect
            # ratio alone cannot detect this ordinary multi-panel figure.
            panel_labels=visible_multi_panel_labels(body)
            xref_image_regions=[]
            for j,image in enumerate(page.get_images(full=True)):
                rects=page.get_image_rects(image[0])
                if len(rects)!=1:
                    skipped.append(f"ambiguous_image_{j}")
                    continue
                r=rects[0]
                xref_image_regions.append(r)
                if r.width<20 or r.height<20:
                    skipped.append(f"tiny_image_{j}")
                    continue
                targets.append({
                    "draft_element_id":f"s{i:03d}.figure.{j:03d}",
                    "type":"image_whole",
                    "anchor":{"type":"image_whole","index":j},
                    "rect_pt":[round(x,2) for x in r],
                    "suspected_multipart":bool(
                        panel_labels or (r.width>200 and r.width/r.height>2.5)),
                    "visible_caption_subpanel_labels_unverified":panel_labels,
                    "actual_panel_count_unverified":True,
                    "image_xref":image[0],
                    "proposed_spoken_text":None,
                    "review_required":True})
            # PyMuPDF/Beamer can encode large mathematically meaningful
            # images as *inline* PDF image blocks with no registered xref.
            # The preceding get_images() call misses them entirely. Preserve
            # original physical bytes + index; skip tiny bullet/decorative
            # icons and never double-count registered xref image placements.
            for j, block in enumerate(page.get_text("dict").get("blocks", [])):
                if block.get("type") != 1:
                    continue
                r=pymupdf.Rect(block.get("bbox", ()))
                if r.is_empty or r.is_infinite or r.width<45 or r.height<35:
                    skipped.append(f"decorative_or_tiny_inline_image_{j}")
                    continue
                if any((r & previous).get_area() >=
                       .90 * min(r.get_area(), previous.get_area())
                       for previous in xref_image_regions):
                    continue
                raw=block.get("image")
                if not isinstance(raw, bytes) or not raw:
                    skipped.append(f"missing_inline_image_bytes_{j}")
                    continue
                digest=hashlib.sha256(raw).hexdigest()
                targets.append({
                    "draft_element_id":f"s{i:03d}.inline.{j:03d}",
                    "type":"inline_image_whole",
                    "anchor":{"type":"inline_image_whole",
                              "index":j,"digest_sha256":digest},
                    "rect_pt":[round(x,2) for x in r],
                    "suspected_multipart":bool(
                        panel_labels or (r.width>200 and r.width/r.height>2.5)),
                    "visible_caption_subpanel_labels_unverified":panel_labels,
                    "actual_panel_count_unverified":True,
                    "image_sha256":digest,
                    "proposed_spoken_text":None,
                    "review_required":True,
                })
            top=" / ".join(strings[:2])
            pages=best_pages(" ".join(body),sourcepages)
            scenes.append({
                "slide_number":i,"title_hint":top,
                "source_page_candidates_unverified":pages,
                "source_page_verified":False,
                "source_evidence_verified":False,
                "academic_approval":False,
                "narration_approval":False,
                "targets":targets,
                "omitted_fragment_indices_needing_review":skipped})
        return {"schema_version":1,"status":"REVIEW_REQUIRED_NOT_TTS_READY",
          "source_sha256":hash_file(source),"slides_sha256":hash_file(slides),
          "source_page_count":len(sourcepages),"slide_count":len(scenes),
          "candidate_target_count":sum(len(s["targets"]) for s in scenes),
          "figure_target_count":sum(sum(t["type"] in
              {"image_whole","inline_image_whole"} for t in s["targets"])
              for s in scenes),
          "all_narration_authored":False,"all_source_pages_verified":False,
          "automatic_approval":False,
          "warning":"No audio production or student release may use this draft. Confirm source pages, all mathematical expressions, figure panels and narration manually or with independent reviewed evidence.",
          "slides":scenes}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-pdf",type=Path,required=True)
    p.add_argument("--slides-pdf",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise FileExistsError("Refusing to overwrite draft")
    obj=draft(a.source_pdf,a.slides_pdf)
    if not a.out.parent.is_dir():raise FileNotFoundError("Output parent missing")
    with a.out.open("x",encoding="utf8") as f:
        json.dump(obj,f,indent=2,ensure_ascii=False)
        f.write("\n")
    print(json.dumps({k:obj[k] for k in ("status","slide_count","source_page_count","candidate_target_count","figure_target_count")},indent=2))

if __name__=="__main__":main()
