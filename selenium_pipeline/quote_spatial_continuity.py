"""Geometric continuity check for PDF quotes, not academic math proof.

Text extraction can concatenate distant two-column snippets into one apparent
sentence. Reject a quote unless its exact word sequence is spatially adjacent.
"""
from __future__ import annotations

import math
import re


def _norm(raw: str)->str:
    return re.sub(r"\s+"," ",raw).strip()


def _adjacent(a:tuple,b:tuple)->bool:
    if (len(a)<8 or len(b)<8
        or any(not isinstance(v,(int,float)) or not math.isfinite(v)
               for v in (*a[:4],*b[:4]))):
        return False
    height=max(a[3]-a[1],b[3]-b[1])
    if height<=0:
        return False
    same_line=(a[5],a[6])==(b[5],b[6])
    if same_line:
        gap=b[0]-a[2]
        return -2<=gap<=max(16.0,1.8*height)
    # A wrapped original phrase can cross consecutive lines within
    # the SAME text block, but never concatenate unrelated text blocks.
    return bool(
        a[5]==b[5] and b[6]==a[6]+1
        and b[1]>=a[1]+0.45*height
        and b[1]-a[3]<=2.0*height
        and b[0]>=0
        and b[0]<=a[0]+2.0*height
    )


def coherent_quote_occurrence(page,phrase:str,index:int,expected_occurrences:int)->bool:
    if (type(phrase) is not str or not phrase.strip()
        or type(index) is not int or index<0
        or type(expected_occurrences) is not int or expected_occurrences<1):
        return False
    words=page.get_text("words",sort=True)
    tokens=_norm(phrase).split(" ")
    if not tokens or len(words)<len(tokens) or len(words)>20000:
        return False
    candidates=[]
    for i in range(len(words)-len(tokens)+1):
        group=words[i:i+len(tokens)]
        if _norm(" ".join(str(w[4]) for w in group))==_norm(phrase):
            candidates.append(group)
    # The PDF's logical extracted text and physical word tokenization must
    # agree on occurrence count and order. Ambiguity is never approval.
    if len(candidates)!=expected_occurrences or index>=len(candidates):
        return False
    selected=candidates[index]
    return all(_adjacent(a,b) for a,b in zip(selected,selected[1:]))
