"""Original-source and REAL recorded PCM Vosk word-timestamp element QA.

Read-only inference for the SIXTEEN historically recorded Thomas 8.4 slides
(other than corrected source-locked Slide4). Use the original source PDF
element draft/geometry, exact narration text, unbiased offline spoken word
timestamps from genuine original WAVs, and source hashes to produce a
conservative audio-alignment + visual-target candidate worklist.

Word recognition/time does NOT prove source geometry or semantic meaning.
No guessed mapping, arbitrary equal-duration bin, re-synthesized voice or
reviewer status may become an accepted per-element highlight.
"""
from __future__ import annotations
from difflib import SequenceMatcher
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import wave

import pymupdf

from .element_plan_autodraft import propose
from .original_replacement_video_handoff import _sha
from .offline_vosk_corrected_math_speech_qa import (
    MODEL_NAME, MODEL_ZIP_SHA256,
)
from .video_ffmpeg import ffmpeg_executable


SENTENCE_BREAK=re.compile(r"(?<=[.?!])\s+(?=[A-Z])")
HISTORIC_SLIDES=tuple(i for i in range(1,18) if i!=4)


def require(ok:bool,message:str):
    if not ok:raise ValueError(message)


def normalize(text:str)->list[str]:
    """Simple acoustic phrase normalization; do NOT normalize math polarity."""
    s=text.casefold().replace("non-negative","nonnegative")
    s=s.replace("non negative","nonnegative")
    s=s.replace("end-point","endpoint").replace("end point","endpoint")
    return re.findall(r"[a-z]+|[0-9]+",s)


def tokenize_reference_sentences(text:str)->tuple[list[dict],list[str]]:
    """Keep exact original TTS narration substrings and token offsets."""
    require(type(text) is str and text.strip(),"No source narration")
    spans=[s.strip() for s in SENTENCE_BREAK.split(text.strip()) if s.strip()]
    require(1<=len(spans)<=30,"Narration sentence count exceeded bound")
    refs=[]
    tokens=[]
    for n,sentence in enumerate(spans,1):
        word_list=normalize(sentence)
        require(word_list, "Source narration sentence has no text tokens")
        begin=len(tokens)
        tokens.extend(word_list)
        refs.append({"sentence_index":n,
                     "narration_fragment":sentence,
                     "narration_fragment_sha256":
                         hashlib.sha256(sentence.encode("utf8")).hexdigest(),
                     "expected_token_begin":begin,
                     "expected_token_end":len(tokens),
                     "expected_token_count":len(word_list)})
    return refs,tokens


def _ASR_surface_normalize(words:list[dict])->list[str]:
    """Retain one token per acoustic timestamp; no multiword hallucination."""
    replacement={
        "eggs":"x","ex":"x","acts":"x",
        "you":"u","pie":"pi","sea":"c","see":"c",
        "four":"for",
    }
    return [replacement.get(item["word"].casefold(),item["word"].casefold())
            for item in words]


def real_word_anchor_candidates(expected:list[str],
                                recognized:list[dict],
                                utterances:list[dict])->list[dict]:
    """Keep ONLY actual acoustic word timestamps, never proportional bins."""
    need_count=len(expected)
    require(need_count>0 and all(isinstance(x,str) for x in expected),
            "Missing expected source audio transcript")
    filtered=[]
    last=-1.0
    for row in recognized:
        start,end=row.get("start"),row.get("end")
        word=row.get("word")
        require(isinstance(word,str) and word.strip()
                and isinstance(start,(float,int)) and
                isinstance(end,(float,int))
                and 0<=start<=end and start>=last-.001
                and end<600 and math.isfinite(start) and math.isfinite(end),
                "Audio recognizer supplied nonmonotonic/nonreal word timestamps")
        filtered.append({"word":word.strip(),"start":float(start),
                         "end":float(end)})
        last=float(start)
    acoustic=_ASR_surface_normalize(filtered)
    matcher=SequenceMatcher(None,expected,acoustic,autojunk=False)
    positions={}
    for block in matcher.get_matching_blocks():
        for j in range(block.size):
            positions[block.a+j]=block.b+j
    answer=[]
    for row in utterances:
        start,end=row["expected_token_begin"],row["expected_token_end"]
        require(0<=start<end<=need_count,"Original source utterance offsets invalid")
        anchors=[positions[n] for n in range(start,end) if n in positions]
        nmatched=len(anchors)
        confidence=round(nmatched/(end-start),4)
        need(min(anchors,default=0)>=0,"Bad ASR anchors")
        # Two genuinely recognized anchors or a clear one-word source slide
        # are needed to propose an utterance start/end. Otherwise UNSOLVED.
        supported=(nmatched>=2 or ((end-start)<=3 and nmatched>=1))
        if supported:
            minword=filtered[min(anchors)]
            maxword=filtered[max(anchors)]
            begin=round(minword["start"],4)
            finish=round(maxword["end"],4)
            if begin>=finish:supported=False
        else:
            begin=finish=None
        answer.append({
            "sentence_index":row["sentence_index"],
            "narration_fragment_sha256":row["narration_fragment_sha256"],
            "expected_word_count":end-start,
            "actual_ASR_aligned_anchor_count":nmatched,
            "actual_ASR_word_anchor_fraction":confidence,
            "first_matched_real_audio_second":begin if supported else None,
            "last_matched_real_audio_second":finish if supported else None,
            "actual_spoken_segment_complete_verified":False,
            "word_timing_hypothesis_available":bool(supported),
            "real_speech_to_source_element_semantics_verified":False,
        })
    return answer


def _real_local_vosk_transcribe(*,model,exe:str,audio_path:Path)->tuple[list[dict],str]:
    try:
        from vosk import KaldiRecognizer
    except ImportError as exc:
        raise ValueError("Authorized free offline Vosk model not installed") from exc
    p=subprocess.run(
        [exe,"-hide_banner","-nostdin","-loglevel","error",
         "-i",str(audio_path),"-ar","16000","-ac","1",
         "-f","s16le","-c:a","pcm_s16le","pipe:1"],
        capture_output=True,timeout=60)
    require(p.returncode==0 and len(p.stdout)>8000,
            "Could not extract actual original PCM for local recognition")
    engine=KaldiRecognizer(model,16000)
    engine.SetWords(True)
    chunks=[]
    for i in range(0,len(p.stdout),8000):
        if engine.AcceptWaveform(p.stdout[i:i+8000]):
            chunks.append(json.loads(engine.Result()))
    chunks.append(json.loads(engine.FinalResult()))
    recognized=[]
    for event in chunks:
        recognized.extend(event.get("result",[]))
    transcription=" ".join(v.get("word","") for v in recognized)
    return recognized,transcription


def source_ranked_target_candidates(speech:dict,visuals:dict)->dict:
    """Lexical PDF ranking only: no automatic semantic target acceptance."""
    choices=speech.get("candidate_target_rankings_unverified") or []
    ranked=[]
    for choice in choices[:4]:
        target=visuals.get(choice["draft_element_id"])
        if target is None:continue
        require(target.get("author_reviewed") is False
                and target.get("source_evidence_verified") is False,
                "Unapproved original visual candidate falsely approved")
        ranked.append({
            "visual_target_id":choice["draft_element_id"],
            "pdf_rect_pt":target["rendered_rect_pt"],
            "visible_pdf_text":target.get("visible_text"),
            "lexical_overlap_hint_not_semantic":float(choice["overlap_hint"]),
            "is_figure_panel_ambiguous":target.get("panel_identity_review_required"),
        })
    top=ranked[0]["lexical_overlap_hint_not_semantic"] if ranked else 0.0
    second=ranked[1]["lexical_overlap_hint_not_semantic"] if len(ranked)>1 else 0.0
    clear=(top>=.43 and top-second>=.17
           and not speech.get("mapping_ambiguous")
           and not (ranked[0].get("is_figure_panel_ambiguous") if ranked else False))
    return {"ranked_original_pdf_visual_candidates":ranked,
            "top_visual_lexical_match_unambiguous":bool(clear),
            "top_visual_id_only_candidate":ranked[0]["visual_target_id"]
                if ranked and clear else None,
            "source_semantic_speech_element_match_proven":False,
            "academic_mathematics_approved":False}


def original_audio_pdf_timing_worklist(
    *, original:Path,model_dir:Path,output_receipt:Path)->dict:
    root=Path(original).absolute()
    model_path=Path(model_dir).absolute()
    output=Path(output_receipt).absolute()
    require(root.is_dir() and not root.is_symlink()
            and output.parent.is_dir() and not output.exists()
            and not output.is_relative_to(root.parent),
            "External exclusive source-hash-tied Dell audit required")
    model_zip=model_path.parent/(MODEL_NAME+".zip")
    require(model_path.is_dir() and model_path.name==MODEL_NAME
            and not model_path.is_symlink() and model_zip.is_file()
            and not model_zip.is_symlink() and _sha(model_zip)==MODEL_ZIP_SHA256,
            "Offline unbiased original-source ASR model changed/missing")
    protected={name:_sha(root/name) for name in (
        "source.pdf","slides.pdf","script.txt","script_tts.json","slides.mp4")}
    require(protected["source.pdf"]==
            "b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068",
            "Not the verified original Thomas 8.4 source")
    tts_source=json.loads((root/"script_tts.json").read_text(encoding="utf8"))
    need_tts=tts_source.get("slides")
    require(type(need_tts) is list and len(need_tts)==17
            and [n.get("slide") for n in need_tts]==list(range(1,18)),
            "Actual original per-slide TTS transcript changed")
    draft=propose(source_pdf=root/"source.pdf",slides_pdf=root/"slides.pdf",
                  script_txt=root/"script.txt")
    require(draft["slides_sha256"]==protected["slides.pdf"]
            and draft["script_sha256"]==protected["script.txt"]
            and len(draft["slides"])==17,
            "Original slide PDF geometry provenance changed")
    from vosk import Model,SetLogLevel
    SetLogLevel(-1)
    model=Model(str(model_path))
    exe=ffmpeg_executable()
    entries=[]
    hashes={}
    for index in HISTORIC_SLIDES:
        wavefile=root/f"slide{index}.wav"
        wav_hash=_sha(wavefile)
        hashes[wavefile.name]=wav_hash
        with wave.open(str(wavefile),"rb") as wav:
            duration=wav.getnframes()/wav.getframerate()
            require(wav.getnchannels()==1 and wav.getsampwidth()==2
                    and wav.getframerate()==24000 and
                    wav.getcomptype()=="NONE" and 1<duration<160,
                    "Original historical PCM did not meet expected format")
        actual_words,heard=_real_local_vosk_transcribe(
            model=model,exe=exe,audio_path=wavefile)
        sentence_rows,reference=tokenize_reference_sentences(
            tts_source["slides"][index-1]["tts_text"])
        times=real_word_anchor_candidates(reference,actual_words,sentence_rows)
        slide=draft["slides"][index-1]
        literal=slide.get("proposed_utterances",[])
        visuals={q["draft_element_id"]:q
                 for q in slide.get("auto_candidate_targets",[])}
        selection=[]
        for j,segment in enumerate(times):
            if j<len(literal):
                match=source_ranked_target_candidates(literal[j],visuals)
                spoken_match=normalize(sentence_rows[j]["narration_fragment"])
                draft_match=normalize(literal[j]["verbatim_script_fragment"])
                narration_consistent=SequenceMatcher(
                    None,spoken_match,draft_match,autojunk=False).ratio()>=.70
            else:
                match={"ranked_original_pdf_visual_candidates":[],
                       "top_visual_lexical_match_unambiguous":False,
                       "top_visual_id_only_candidate":None,
                       "source_semantic_speech_element_match_proven":False,
                       "academic_mathematics_approved":False}
                narration_consistent=False
            selection.append({
                **segment,
                "original_actual_slide_narration_fragment":
                    sentence_rows[j]["narration_fragment"],
                "original_script_tts_matches_draft_fragment":
                    bool(narration_consistent),
                **match,
                "eligible_for_final_student_highlight":False,
            })
        rows={
            "slide":index,
            "historical_WAV_sha256":wav_hash,
            "actual_original_PCM_duration_s":round(duration,6),
            "actual_unprompted_Vosk_recognized_word_count":len(actual_words),
            "asr_transcript":heard,
            "script_utterance_count":len(sentence_rows),
            "visible_original_PDF_candidate_target_count":len(visuals),
            "utterance_audio_word_timing_anchor_count":
                sum(bool(v["word_timing_hypothesis_available"]) for v in selection),
            "lexically_unique_visible_pdf_targets":
                sum(bool(v["top_visual_lexical_match_unambiguous"]) for v in selection),
            "candidate_elements":selection,
            "actual_math_semantic_alignment_accepted":False,
            "source_speech_element_highlight_ready":False,
        }
        entries.append(rows)
        print("ORIGINAL_PDF_AUDIO_REAL_WORD_TIMING",
              "slide",index,
              "audio_words",len(actual_words),
              "sentence_anchors",rows["utterance_audio_word_timing_anchor_count"],
              "/",len(sentence_rows),
              "visible_pdf_candidates",rows["lexically_unique_visible_pdf_targets"],
              flush=True)
    require(len(entries)==16 and
            [e["slide"] for e in entries]==list(HISTORIC_SLIDES),
            "Real original slide audio timeline missing")
    require(all(_sha(root/name)==sha
                for name,sha in {**protected,**hashes}.items()),
            "Original source files or historical PCM changed during recognition")
    report={
        "schema_version":1,
        "status":"REAL_HISTORICAL_16_SLIDES_ASR_TO_ORIGINAL_PDF_ELEMENT_CANDIDATES_REVIEW_ONLY",
        "source_original_hashes":protected,
        "original_historical_WAV_hashes":hashes,
        "unbiased_offline_speech_model":MODEL_NAME,
        "source_model_zip_sha256":MODEL_ZIP_SHA256,
        "actual_historical_slides_inspected":16,
        "total_expected_utterances":
            sum(e["script_utterance_count"] for e in entries),
        "audio_word_timing_hypotheses":
            sum(e["utterance_audio_word_timing_anchor_count"] for e in entries),
        "visually_lexical_unique_target_hypotheses":
            sum(e["lexically_unique_visible_pdf_targets"] for e in entries),
        "independent_utterance_to_math_element_semantics_certified":False,
        "complete_video_spoken_element_synchronization_certified":False,
        "academic_source_math_two_pass_approved":False,
        "student_publication_authorized":False,
        "whisper_used":False,
        "network_asr_used":False,
        "provider_synthesis_requests_sent":0,
        "source_originals_modified":False,
        "slides":entries,
    }
    with output.open("x",encoding="utf8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False)
        f.write("\n")
    print(json.dumps({
        "status":report["status"],
        "actual_16_historical_slides":16,
        "timed_utterances":report["audio_word_timing_hypotheses"],
        "candidate_unique_visual_targets":
            report["visually_lexical_unique_target_hypotheses"],
        "release_accepted":False,
    }))
    return report


def main(argv=None):
    import argparse
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("--original",type=Path,required=True)
    a.add_argument("--model-dir",type=Path,required=True)
    a.add_argument("--out",type=Path,required=True)
    args=a.parse_args(argv)
    original_audio_pdf_timing_worklist(
        original=args.original,model_dir=args.model_dir,
        output_receipt=args.out)


if __name__=="__main__":
    main()
