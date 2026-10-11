from pathlib import Path
import pymupdf
from selenium_pipeline.slide_change_planner import changed_pages

def pdf(path, pages, extra=False):
    d=pymupdf.open()
    for i in range(pages):
        p=d.new_page()
        p.insert_text((40,60),"Text "+str(i))
        if extra and i==0:
            p.insert_text((40,100),"Restored figure")
    d.save(path)
    d.close()

def test_identical_pdf_has_no_affected_pages(tmp_path):
    p=tmp_path/"one.pdf"
    pdf(p,2)
    assert changed_pages(p,p)["affected"]==[]

def test_content_change_marks_page(tmp_path):
    a,b=tmp_path/"a.pdf",tmp_path/"b.pdf"
    pdf(a,2)
    pdf(b,2,True)
    assert changed_pages(a,b)["affected"]==[1]

def test_page_count_change_requires_full_review(tmp_path):
    a,b=tmp_path/"a.pdf",tmp_path/"b.pdf"
    pdf(a,2)
    pdf(b,3)
    assert changed_pages(a,b)["affected"]==[1,2,3]
