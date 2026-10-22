"""Independent genuine textbook-page quote witness; never math-semantic approval."""
from __future__ import annotations
import hashlib,re
from pathlib import Path
import pymupdf
from .figure_source_identity import require,_sha

def prove_source_quote_occurrence(*,source_pdf:Path,expected_sha256:str,
                                  page_number:int,verbatim_quote:str,
                                  occurrence_index:int|None=None)->dict:
    source_pdf=Path(source_pdf).absolute()
    require(source_pdf.is_file() and _sha(source_pdf)==expected_sha256
            and type(page_number) is int and page_number>=1
            and type(verbatim_quote) is str and 8<=len(verbatim_quote)<=800
            and not any(c in verbatim_quote for c in ("\x00","\r")),
            "Original PDF or source quote invalid")
    with pymupdf.open(source_pdf) as pdf:
        require(page_number<=len(pdf),"Source quote page does not exist")
        text=pdf[page_number-1].get_text(sort=True)
    collapse=lambda s:re.sub(r"\s+"," ",s).strip()
    norm=collapse(text);needle=collapse(verbatim_quote)
    require(len(needle)>=8,"Empty normalized textbook claim")
    hits=[];start=0
    while True:
        pos=norm.find(needle,start)
        if pos<0:break
        hits.append(pos);start=pos+1
    require(hits and (len(hits)==1 and occurrence_index is None or
                     type(occurrence_index) is int and
                     0<=occurrence_index<len(hits)),
            "Ambiguous or unlocatable exact original textbook quote")
    index=0 if occurrence_index is None else occurrence_index
    require(_sha(source_pdf)==expected_sha256,"Source changed after checking")
    return {"status":"EXACT_ORIGINAL_PDF_PAGE_QUOTE_PRESENT",
        "source_sha256":expected_sha256,"source_page":page_number,
        "quote_sha256":hashlib.sha256(needle.encode()).hexdigest(),
        "quote_occurrences":len(hits),"chosen_occurrence":index,
        "math_semantics_author_verified":False,"publication_authorized":False}
