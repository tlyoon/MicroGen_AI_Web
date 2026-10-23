"""External write-once source-chunk acknowledgements; never skip unknown turns."""
import hashlib,json,os
from pathlib import Path
from .textbook_source_bounded_page_chunks import validate_chunk_coverage
def record_chunk_ack(*,manifest:dict,log:Path,chunk_index:int,
                     response:dict,owned_session_id:str)->dict:
 validated=validate_chunk_coverage(manifest)
 chunks=manifest["chunks"]
 if (type(chunk_index) is not int or chunk_index<0 or chunk_index>=len(chunks)
     or type(owned_session_id) is not str or len(owned_session_id)<8):
  raise ValueError("Stable original chunk index and owned session required")
 p=Path(log).absolute()
 if p.suffix!=".jsonl" or not p.parent.is_dir() or p.is_symlink():
  raise ValueError("External append-only JSONL required")
 history=[]
 if p.exists():
  for line in p.read_text(encoding="utf8").splitlines():
   history.append(json.loads(line))
 if len(history)!=chunk_index:
  raise ValueError("Prior same-session chunk ACKs missing, duplicated or ambiguous")
 if any(row.get("owned_session_id")!=owned_session_id or
        row.get("original_source_sha256")!=manifest["source_sha256"] or
        row.get("chunk_index")!=i
        for i,row in enumerate(history)):
  raise ValueError("Resumed from an unrelated Gemini session or original textbook")
 chunk=chunks[chunk_index]
 if (type(response) is not dict or response.get("chunk_sha256")!=chunk["fragment_sha256"]
     or response.get("received") is not True or
     response.get("physical_page")!=chunk["physical_page"] or
     response.get("start_char")!=chunk["start_char"]):
  raise ValueError("Gemini has not positively ACKed the exact source fragment")
 row={"chunk_index":chunk_index,"owned_session_id":owned_session_id,
      "original_source_sha256":manifest["source_sha256"],
      "fragment_sha256":chunk["fragment_sha256"],
      "physical_page":chunk["physical_page"],"start_char":chunk["start_char"],
      "event":"MODEL_ACK_ONLY_NOT_MATHEMATICAL_APPROVAL"}
 with p.open("a",encoding="utf8") as w:
  w.write(json.dumps(row,sort_keys=True)+"\n");w.flush();os.fsync(w.fileno())
 return {"status":"EXACT_SAME_SESSION_CHUNK_ACK_STAGED",
         "acknowledged_chunks":len(history)+1,
         "expected_chunks":len(chunks),"mathematics_approved":False}
