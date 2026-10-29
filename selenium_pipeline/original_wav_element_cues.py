"""Create SAMPLE-INDEX timing hypotheses for source slide element highlights.

Uses only source PDF text block rectangles, original WAV PCM amplitude pause
windows, and original hashes. Absolutely NOT speech/text forced alignment.
A provisional event must never certify synchronized narration highlighting.
"""
from __future__ import annotations
import argparse,hashlib,json,math,struct,wave
from pathlib import Path
import pymupdf
from .figure_source_identity import require,_sha

def _candidate_pause_boundaries(samples:bytes, sample_rate:int, count:int)->list[int]:
    require(type(samples) is bytes and 300<=sample_rate<=96000
            and 1<=count<=30 and len(samples)%2==0
            and len(samples)//2<=sample_rate*550,
            "Invalid bounded mono PCM")
    n=len(samples)//2
    require(n>sample_rate, "Audio too short")
    if count==1:return []
    window=max(1,int(sample_rate*.04))
    rms=[]
    for i in range(0,n,window):
        segment=samples[2*i:2*min(n,i+window)]
        nums=struct.unpack(f"<{len(segment)//2}h",segment)
        rms.append((sum(x*x for x in nums)/len(nums))**.5)
    peak=max(rms)
    require(peak>50,"Silent speech WAV cannot be aligned")
    quiet=[v<=max(80,peak*.06) for v in rms]
    runs=[]
    start=None
    for i,state in enumerate(quiet+[False]):
        if state and start is None:start=i
        if not state and start is not None:
            if i-start>=5 and start>0 and i<len(quiet):
                at=int(((start+i)*window)//2)
                if sample_rate//2<at<n-sample_rate//2:
                    runs.append((i-start,at))
            start=None
    # Select strongest silence gaps, with a minimum separation and
    # duration; if ambiguous, STOP rather than invent speech timings.
    picked=[]
    for length,at in sorted(runs,key=lambda v:(-v[0],v[1])):
        if all(abs(at-existing)>=sample_rate for existing in picked):
            picked.append(at)
            if len(picked)==count-1:break
    require(len(picked)==count-1,
            "Insufficient independent source WAV pauses for block timing")
    return sorted(picked)

def propose_wav_pdf_element_highlights(*,slides:Path, wav:Path,
                                       slide_index:int, max_elements:int=12)->dict:
    slides,wav=Path(slides).absolute(),Path(wav).absolute()
    require(slides.is_file() and wav.is_file()
            and not slides.is_symlink() and not wav.is_symlink(),
            "Original slide PDF and recorded PCM WAV required")
    before=(_sha(slides),_sha(wav))
    with pymupdf.open(slides) as deck:
        require(1<=slide_index<=len(deck),"Slide index not present")
        page=deck[slide_index-1]
        blocks=[{"bbox_pt":[round(float(v),3) for v in (
                    max(0,b[0]),max(0,b[1]),
                    min(page.rect.width,b[2]),
                    min(page.rect.height,b[3]))],
                 "original_text":str(b[4]).strip()}
                for b in page.get_text("blocks")
                if len(b)>=5 and str(b[4]).strip() and
                b[2]>b[0] and b[3]>max(8,b[1]) and
                b[0]<page.rect.width and b[1]<page.rect.height
                and b[2]>0 and b[3]>8]
        boxes=[x for x in blocks if len(x["original_text"])>=4]
        require(1<=len(boxes)<=max_elements and len(boxes)<=30,
                "No safely bounded original textual elements")
        require(all(0<=b["bbox_pt"][0]<b["bbox_pt"][2]<=page.rect.width+1
                    and 0<=b["bbox_pt"][1]<b["bbox_pt"][3]<=page.rect.height+1
                    for b in boxes),"Original text geometry escapes slide")
        width,height=page.rect.width,page.rect.height
    with wave.open(str(wav),"rb") as audio:
        require(audio.getnchannels()==1 and audio.getsampwidth()==2
                and audio.getcomptype()=="NONE"
                and audio.getframerate()>0,
                "Require exact original mono PCM16 WAV")
        hz=audio.getframerate()
        count=audio.getnframes()
        require(0<count<hz*550,"WAV too long or empty for element pilot")
        pcm=audio.readframes(count)
    points=[0,*_candidate_pause_boundaries(pcm,hz,len(boxes)),count]
    require(len(points)==len(boxes)+1
            and all(a<b for a,b in zip(points,points[1:])),
            "Invalid or incomplete sample boundaries")
    items=[]
    for idx,(b,start,end) in enumerate(zip(boxes,points,points[1:]),1):
        items.append({
            "element_id":f"slide_{slide_index:02d}_text_{idx:02d}",
            "original_pdf_rect_pt":b["bbox_pt"],
            "original_pdf_text":b["original_text"],
            "original_wav_start_sample":start,
            "original_wav_end_sample":end,
            "start_s":round(start/hz,5),"end_s":round(end/hz,5),
            "spoken_text_alignment_verified":False,
            "mathematical_element_semantics_verified":False,
        })
    require(_sha(slides)==before[0] and _sha(wav)==before[1],
            "Original files changed while analyzing recording")
    return {
        "schema_version":1,
        "status":"PROVISIONAL_PAUSE_MATCHED_ELEMENT_HIGHLIGHT_REVIEW_ONLY",
        "slides_sha256":before[0],"wav_sha256":before[1],
        "slide_index":slide_index,"slide_page_width_pt":width,
        "slide_page_height_pt":height,"wav_sample_rate":hz,
        "original_wav_duration_s":round(count/hz,5),
        "events":items,"speech_alignment_verified":False,
        "rendered_highlight_pixels_verified":False,
        "encoded_mp4_verified":False,"student_publication_authorized":False,
    }

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--slides",type=Path,required=True)
    p.add_argument("--wav",type=Path,required=True)
    p.add_argument("--slide-index",type=int,required=True)
    a=p.parse_args(argv)
    print(json.dumps(propose_wav_pdf_element_highlights(
        slides=a.slides,wav=a.wav,slide_index=a.slide_index),
        indent=2,ensure_ascii=True,sort_keys=True))
    return 2
if __name__=="__main__":
    raise SystemExit(main())
