"""Deterministic loss-conservative original-source prompt windowing.

Only the SOURCE PAGE TEXT excerpts in a model *proposal* are shortened.
Full original source and author PDF, SHA-bound queue, original spoken text,
visible target IDs/geometry and strict independent post-model audits are NEVER
changed. Omitted material cannot count as scientific approval: the model
must return null/needs_review for insufficient snippets. No provider call.
"""
from __future__ import annotations

import json
import re

MAX_BOUNDED_PROMPT_CHARS=11000
WINDOW_CHARS=420
STOP=frozenset((
    "that","this","with","from","when","then","into","have","also",
    "only","each","their","there","where","whose","which","while",
    "would","could","should","through","about","some","such",
    "these","those","takes","equal","equals","shown","shows",
    "your","than","what","more","less","note","same","using",
))


def _keywords(utterances:list[dict])->tuple[str,...]:
    if type(utterances) is not list or not utterances:
        raise ValueError("No original unresolved source utterances")
    text=" ".join(str(u.get("verbatim_text","")) for u in utterances
                  if type(u) is dict)
    found=re.findall(r"[a-zA-Z]{4,}",text.lower())
    # Stable, original order; exact source byte windows are selected later.
    return tuple(dict.fromkeys(
        x for x in found if x not in STOP and len(x)>=4
    ))[:35]


def _contiguous_source_windows(text:str,terms:tuple[str,...],
                               *,max_windows:int)->list[str]:
    if type(text) is not str or not text:
        raise ValueError("Source excerpt is not a physical text string")
    if len(text)<=WINDOW_CHARS:
        return [text]
    low=text.lower()
    starts={0,max(0,len(text)-WINDOW_CHARS)}
    for term in terms:
        cursor=0
        matches=0
        while matches<12:
            index=low.find(term,cursor)
            if index<0:
                break
            starts.add(max(0,min(len(text)-WINDOW_CHARS,index-WINDOW_CHARS//3)))
            cursor=index+len(term)
            matches+=1
    ranked=[]
    for start in starts:
        segment=text[start:start+WINDOW_CHARS]
        lower=segment.lower()
        score=sum(2+min(len(term),12)//4 for term in terms if term in lower)
        ranked.append((-score,start,segment))
    ranked.sort(key=lambda x:(x[0],x[1]))
    selected=[]
    for _,start,window in ranked:
        if any(abs(start-old_start)<WINDOW_CHARS//2 for old_start,_ in selected):
            continue
        selected.append((start,window))
        if len(selected)>=max_windows:
            break
    return [x for _,x in sorted(selected)]


def bounded_prompt_partial(request:dict,*,max_chars:int=MAX_BOUNDED_PROMPT_CHARS
                           )->tuple[str,dict]:
    """Return exact old request identity with small, real-source text windows.

    The prompt carries a separate derived excerpt selection, but the
    partial_request_sha256 and all response/merge QA still refer to the
    UNMODIFIED full physically verified queue request.
    """
    from .rich_unresolved_model_queue import prompt_partial
    full=prompt_partial(request)
    original_len=len(full)
    if type(max_chars) is not int or not 3000<=max_chars<=15000:
        raise ValueError("Source prompt budget untrusted")
    if original_len<=max_chars:
        return full,{
            "source_excerpt_mode":"FULL_ORIGINAL_TEXT",
            "original_prompt_characters":original_len,
            "sent_prompt_characters":original_len,
            "source_excerpt_windows":0,
            "original_source_queue_unchanged":True,
        }
    pre,body=full.rsplit("\n\n",1)
    task=json.loads(body)
    pages=task.get("source_page_excerpts")
    if type(pages) is not list or not pages or len(pages)>15:
        raise ValueError("Source page excerpt inventory malformed")
    terms=_keywords(task["only_unresolved_original_utterances"])
    for max_windows in (2,1):
        smaller=[]
        for item in pages:
            if (type(item) is not dict or type(item.get("source_page")) is not int
                    or type(item.get("original_page_text")) is not str):
                raise ValueError("Source page excerpt provenance invalid")
            source=item["original_page_text"]
            for span in _contiguous_source_windows(
                    source,terms,max_windows=max_windows):
                if not span or span not in source:
                    raise ValueError("Generated source window has no original witness")
                smaller.append({
                    "source_page":item["source_page"],
                    "original_page_text":span})
        if not smaller:
            raise ValueError("No source quote windows available")
        task["source_page_excerpts"]=smaller
        # Unchanged source PDF and full queue define acceptance, not a
        # model seeing a short excerpt. Explicit absence remains unapproved.
        instruction=(
            pre+"\nThese are VERBATIM contiguous excerpt WINDOWS, not whole "
            "original pages. Only quote literal consecutive characters "
            "from one listed window. If an equation, figure, sign, domain, "
            "or valid target is not evidenced here, output a NULL target "
            "with needs_review=true; do not guess.\n\n"
        )
        bounded=instruction+json.dumps(
            task,ensure_ascii=False,separators=(",",":"))
        if len(bounded)<=max_chars:
            return bounded,{
                "source_excerpt_mode":"DETERMINISTIC_CONTIGUOUS_SOURCE_WINDOWS_V1",
                "original_prompt_characters":original_len,
                "sent_prompt_characters":len(bounded),
                "source_excerpt_windows":len(smaller),
                "original_source_queue_unchanged":True,
            }
    raise ValueError("Even bounded source quote windows exceed model budget")
