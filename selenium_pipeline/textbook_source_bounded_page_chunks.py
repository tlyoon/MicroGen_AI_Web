"""Lossless physical-page source text chunks bounded for Gemini Quill.

All chunks retain original PDF ordering. No candidate mathematics or TTS
is approved simply because chunk hashes match.
"""
import hashlib
from pathlib import Path
import pymupdf
def original_textbook_chunks(source_pdf:Path,*,limit:int=1600)->dict:
 p=Path(source_pdf)
 if not p.is_file() or p.is_symlink() or type(limit) is not int or not 256<=limit<=4000:
  raise ValueError("Readable bounded real textbook PDF required")
 chunks=[];pages=[]
 with pymupdf.open(p) as doc:
  if not 1<=len(doc)<=8:raise ValueError("Original textbook page scope unbounded")
  for number,page in enumerate(doc,1):
   txt=page.get_text(sort=True)
   if not txt.strip():raise ValueError("Image-only original page needs visual review")
   pages.append(txt)
   piece_limit=limit
   for offset in range(0,len(txt),piece_limit):
    part=txt[offset:offset+piece_limit]
    chunks.append({"physical_page":number,"start_char":offset,
       "original_page_chars":len(txt),"fragment":part,
       "fragment_sha256":hashlib.sha256(part.encode("utf8")).hexdigest()})
 return {"status":"COMPLETE_PHYSICAL_PAGE_TEXT_FRAGMENTS_NOT_REVIEWED",
         "source_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
         "page_count":len(pages),"chunk_count":len(chunks),
         "chunks":chunks,"visual_math_verified":False}
def validate_chunk_coverage(manifest:dict)->dict:
 if type(manifest) is not dict or type(manifest.get("chunks")) is not list:
  raise ValueError("Invalid complete original physical page chunk manifest")
 reconstructed={};next_offset={}
 for row in manifest["chunks"]:
  if type(row) is not dict:raise ValueError("Invalid chunk")
  page=row.get("physical_page");offset=row.get("start_char");s=row.get("fragment")
  if (type(page) is not int or not 1<=page<=8 or
      type(offset) is not int or type(s) is not str or not s
      or offset!=next_offset.get(page,0) or
      hashlib.sha256(s.encode()).hexdigest()!=row.get("fragment_sha256")):
   raise ValueError("Incomplete, duplicated or corrupted original page text")
  reconstructed[page]=reconstructed.get(page,"")+s;next_offset[page]=offset+len(s)
  if next_offset[page]>row.get("original_page_chars",-1):
   raise ValueError("Original page overflow")
 if (sorted(reconstructed)!=list(range(1,manifest.get("page_count",0)+1))
     or len(manifest["chunks"])!=manifest.get("chunk_count")):
  raise ValueError("Original page omitted")
 for row in manifest["chunks"]:
  if next_offset[row["physical_page"]]!=row["original_page_chars"]:
   raise ValueError("Original physical page truncated")
 return {"status":"ALL_EXTRACTABLE_PAGE_TEXT_LOSSLESS",
         "pages":len(reconstructed),"chunks":len(manifest["chunks"]),
         "visual_math_verified":False}
