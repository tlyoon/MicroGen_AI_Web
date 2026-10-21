"""Validate physical element WAV integrity without pretending it proves spoken semantics.

Does not generate or approve audio, billing, highlight sync or student release.
"""
from __future__ import annotations
import hashlib,math,re,wave
from pathlib import Path
from .figure_source_identity import require,_sha

def inspect_element_wav_claims(packet:dict,claims:list[dict])->dict:
    require(type(packet) is dict and packet.get("status")=="ORIGINAL_FIGURE83_REVIEW_ONLY"
            and packet.get("paid_tts_authorized") is False
            and packet.get("student_publication_authorized") is False
            and type(packet.get("review_utterances")) is list,
            "Require original source-bound review packet, not a paid-job authorization")
    indexed={entry["utterance_id"]:entry for entry in packet["review_utterances"]}
    require(len(indexed)==len(packet["review_utterances"])
            and type(claims) is list and len(claims)<=len(indexed),
            "Duplicate original utterances or unbounded element audio claims")
    processed=[];voice_keys=set();ids=set()
    for item in claims:
        require(type(item) is dict
                and type(item.get("utterance_id")) is str
                and item["utterance_id"] in indexed
                and item["utterance_id"] not in ids
                and item.get("human_math_and_speech_approved") is False,
                "No guessed element text may be treated as source-approved")
        ids.add(item["utterance_id"])
        path=Path(item["wav_path"]).absolute()
        digest=item.get("sha256")
        require(type(digest) is str and bool(re.fullmatch(r"[0-9a-f]{64}",digest))
                and path.is_file() and path.suffix.lower()==".wav",
                "Require an existing checksum-bound WAV clip")
        require(type(item.get("voice_id")) is str and
                1<=len(item["voice_id"])<=100
                and item.get("engine") in ("gemini-flash-lite","google-cloud-tts"),
                "Require declared TTS engine and one consistent voice")
        attempts=item.get("primary_attempts_failed")
        require(type(attempts) is int and 0<=attempts<=20 and
                (item["engine"]!="google-cloud-tts" or attempts>=3),
                "Cloud fallback only after three genuine Flash-Lite failures")
        actual=_sha(path)
        require(actual==digest,"Recorded element WAV checksum mismatch")
        try:
            with wave.open(str(path),"rb") as w:
                frames=w.getnframes();sample_rate=w.getframerate()
                channels=w.getnchannels();sample_width=w.getsampwidth()
                require(channels==1 and sample_width==2
                        and 8000<=sample_rate<=96000 and frames>0
                        and frames<sample_rate*600,
                        "Unexpected bounded WAV PCM encoding or length")
                duration=frames/sample_rate
        except (wave.Error,EOFError,ValueError,OSError) as exc:
            raise ValueError("Corrupt or unsupported claimed element WAV") from exc
        require(type(item.get("duration_s")) in (int,float)
                and math.isfinite(item["duration_s"])
                and abs(duration-item["duration_s"])<=1/sample_rate+1e-6,
                "Element WAV metadata duration is not PCM measured")
        voice_keys.add(item["voice_id"])
        processed.append({"utterance_id":item["utterance_id"],
                          "wav_sha256":actual,"pcm_duration_s":round(duration,5),
                          "engine":item["engine"],"voice_id":item["voice_id"],
                          "physical_audio_integrity_verified":True,
                          "spoken_words_mapped_to_visual_element_verified":False})
    require(len(voice_keys)<=1,"Mixed voices in a lecture are not permitted")
    return {"status":"ELEMENT_AUDIO_PHYSICAL_INTEGRITY_ONLY",
            "integrity_checked_clip_count":len(processed),
            "element_audio_integrity_receipts":processed,
            "all_original_utterances_have_verified_element_audio":
                len(processed)==len(indexed) and bool(indexed),
            "mathematical_utterance_semantics_verified":False,
            "spoken_element_timing_verified":False,
            "production_video_authorized":False,
            "paid_tts_authorized":False,
            "student_publication_authorized":False}
