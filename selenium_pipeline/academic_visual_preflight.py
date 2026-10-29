"""Conservative PDF mathematics/figure technical preflight.

This audits *observable* geometry and missing/clipped image instances. It does
NOT certify mathematical truth, semantic equivalence, or figure correspondence
to source textbook. Those remain independent review requirements.
"""
from __future__ import annotations
import argparse,hashlib,json,re
from pathlib import Path
import pymupdf

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1048576),b""):h.update(c)
    return h.hexdigest()

def inspect(pdf:Path,*,min_figure_width_fraction:float=.18,
            min_panel_width_fraction:float=.13,
            lower_margin_pt:float=8)->dict:
    if not pdf.is_file():raise FileNotFoundError(pdf)
    all_pages=[]
    counts={"clipped_content":0,"small_figures":0,
            "composite_figure_review":0,"small_text_spans":0,
            "orphan_equation_fragments":0}
    with pymupdf.open(pdf) as pages:
        for n,page in enumerate(pages,1):
            findings=[]
            w,h=page.rect.width,page.rect.height
            # inspect rendered text spans: math expressions are often fragmented
            # by TeX into independent text blocks; no semantic inference here.
            page_obj=page.get_text("dict")
            for b in page_obj.get("blocks",[]):
                if b.get("type")!=0:continue
                r=pymupdf.Rect(b["bbox"])
                if r.x0 < -1 or r.y0 < -1 or r.x1 > w+1 or r.y1 > h+1:
                    findings.append({"severity":"blocker","reason":"clipped_content",
                           "bbox":[round(v,2) for v in r]})
                    counts["clipped_content"]+=1
                for line in b.get("lines",[]):
                    for span in line.get("spans",[]):
                        t=span.get("text","").strip()
                        if t and float(span.get("size",0))<6.5:
                            findings.append({"severity":"review","reason":"small_text_span",
                              "text_sample":t[:55],"size_pt":round(span["size"],2)})
                            counts["small_text_spans"]+=1
            for j,item in enumerate(page.get_images(full=True)):
                xref=item[0]
                rects=page.get_image_rects(xref)
                if len(rects)!=1:
                    findings.append({"severity":"blocker","reason":"missing_or_ambiguous_pdf_image",
                                     "xref":xref,"placements":len(rects)})
                    counts["clipped_content"]+=1
                    continue
                r=rects[0]
                if (r.x0<-1 or r.y0<-1 or r.x1>w+1 or r.y1>h+1):
                    findings.append({"severity":"blocker","reason":"clipped_figure",
                         "xref":xref,"bbox":[round(v,2) for v in r]})
                    counts["clipped_content"]+=1
                wide=r.width/w
                if wide<min_figure_width_fraction:
                    findings.append({"severity":"review","reason":"figure_small_on_slide",
                        "xref":xref,"width_fraction":round(wide,3)})
                    counts["small_figures"]+=1
                if r.width>200 and r.width/r.height>2.5:
                    # Multi-panel evidence requires manual panel-count confirmation.
                    potential_panel_frac=wide/3
                    findings.append({"severity":"review",
                        "reason":"possible_multipart_composite_panel_count_unverified",
                        "xref":xref,"whole_width_fraction":round(wide,3),
                        "three_panel_estimated_width_fraction":round(potential_panel_frac,3),
                        "three_panel_width_below_threshold":
                            potential_panel_frac<min_panel_width_fraction})
                    counts["composite_figure_review"]+=1
            all_pages.append({"page":n,"findings":findings,
                "blocking_technical":any(x["severity"]=="blocker" for x in findings),
                "requires_human_quality_review":bool(findings)})
        return {
          "schema_version":1,
          "status":"TECHNICAL_PREFLIGHT_REVIEW_REQUIRED",
          "pdf_sha256":sha(pdf),
          "pages":len(all_pages),
          "blocker_count":sum(sum(x["severity"]=="blocker"
               for x in p["findings"]) for p in all_pages),
          "findings_total":sum(len(p["findings"]) for p in all_pages),
          "counts":counts,
          "mathematical_correctness_verified":False,
          "source_equation_equivalence_verified":False,
          "figure_panel_completeness_certified":False,
          "human_figure_legibility_approved":False,
          "details":all_pages}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--slides-pdf",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    args=p.parse_args()
    if args.out.exists() or not args.out.parent.is_dir():
        raise ValueError("Preflight output must be a new path under existing folder")
    result=inspect(args.slides_pdf)
    with args.out.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps({k:result[k] for k in
        ("status","pages","blocker_count","findings_total","counts")},indent=2))

if __name__=="__main__":main()
