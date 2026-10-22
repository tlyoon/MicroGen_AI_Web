"""Independently recheck that a compact challenge includes every original PDF page."""
from pathlib import Path
import pymupdf
from .figure_source_identity import _sha
def verify_complete_original_excerpt(*,folder:Path,slide:int,excerpt:Path)->dict:
    folder,excerpt=Path(folder),Path(excerpt)
    if (type(slide) is not int or slide<1 or not excerpt.is_file()
        or excerpt.is_symlink() or excerpt.suffix.lower()!=".txt"
        or excerpt.stat().st_size>260000 or excerpt.resolve().is_relative_to(folder.resolve())):
        raise ValueError("External bounded original excerpt required")
    source=folder/"source.pdf";deck=folder/"slides.pdf";script=folder/"script.txt"
    if any(not p.is_file() or p.is_symlink() for p in (source,deck,script)):
        raise ValueError("Original source attachments absent or unsafe")
    evidence=excerpt.read_text(encoding="utf8")
    if len(evidence)>65000:
        raise ValueError("Source challenge excerpt exceeds original bound")
    for file,caption in ((source,"SOURCE"),(deck,"SLIDE"),(script,"SCRIPT")):
        if evidence.count("ORIGINAL "+caption+" SHA256 "+_sha(file))!=1:
            raise ValueError("Original source/slide/script hash absent or duplicated")
    with pymupdf.open(source) as book,pymupdf.open(deck) as slides:
        if not 1<=len(book)<=8 or not 1<=slide<=len(slides):
            raise ValueError("Source excerpt needs supported physical page coverage")
        for page_number in range(1,len(book)+1):
            text=book[page_number-1].get_text(sort=True)
            if not text.strip():
                raise ValueError("Image-only textbook page needs visual review")
            witness="ORIGINAL TEXTBOOK PDF PHYSICAL PAGE "+str(page_number)+"\n"+text
            if evidence.count(witness)!=1:
                raise ValueError("Complete actual textbook page missing or modified")
        slide_text=slides[slide-1].get_text(sort=True)
        witness="ORIGINAL SLIDE PDF PHYSICAL PAGE "+str(slide)+"\n"+slide_text
        if evidence.count(witness)!=1:
            raise ValueError("Original slide text missing or altered")
        return {"status":"ALL_EXTRACTABLE_ORIGINAL_SOURCE_PAGES_INDEPENDENTLY_WITNESSED",
            "physical_textbook_pages":len(book),"slide":slide,
            "verified_original_source_sha256":_sha(source),
            "excerpt_sha256":_sha(excerpt),
            "visual_figure_math_semantics_verified":False,
            "student_publication_authorized":False}
