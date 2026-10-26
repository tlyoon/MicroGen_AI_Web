"""Repartition *measured* WAV frames after any future corrected audio arrives.

Historic audio may be counted as a temporary planning placeholder ONLY.
Output never claims a corrected lesson or approves an encoded MP4.
"""
from __future__ import annotations
import wave
from pathlib import Path
from .original_wav_multipart_plan import choose_contiguous_wav_parts,inspect_original_slide_wav_plan
from .figure_source_identity import require
from .original_replacement_video_handoff import _sha

def _duration(p):
    with wave.open(str(p),"rb") as w:
        require(w.getcomptype()=="NONE" and w.getnchannels() in (1,2)
                and w.getnframes()>0 and w.getframerate()>=8000,
                "Expected actual PCM audio frames")
        return w.getnframes()/w.getframerate()
def measured_replacement_replan(*,chapter:Path,replacements:dict|None=None,
                                audio_budget_s:float=540.0)->dict:
    root=Path(chapter).absolute()
    require(root.is_dir() and not root.is_symlink(),"Actual original chapter is required")
    changes={} if replacements is None else replacements
    require(type(changes) is dict and len(changes)<=200,"Bounded replacement WAV mapping required")
    used=set()
    sections=[]
    for topic in ("8.4","8.5","8.6"):
        original=inspect_original_slide_wav_plan(root/topic,audio_budget_s=audio_budget_s)
        frames=[]
        changed=[]
        for item in original["wav_evidence"]:
            num=item["slide_index"]; key=f"{topic}/{num}"
            waves=changes.get(key)
            if waves is None:
                duration=item["duration_s"]
            else:
                require(type(waves) is list and 1<=len(waves)<=40
                        and (key!="8.4/4" or len(waves)==5),
                        "Replacement must contain complete named new utterance chunks")
                durations=[]
                for name in waves:
                    path=Path(name).absolute()
                    require(path.is_file() and not path.is_symlink()
                            and not path.is_relative_to(root) and path.suffix.lower()==".wav",
                            "Replacement PCM must be external to original chapter")
                    hash_value=_sha(path)
                    require(hash_value!=item["sha256"]
                            and hash_value not in used,
                            "Old/duplicate audio masquerading as newly narrated content")
                    used.add(hash_value)
                    durations.append(_duration(path))
                duration=sum(durations)
                changed.append({"slide":num,"count":len(waves),
                                "measured_replacement_audio_s":round(duration,4),
                                "text_or_voice_fidelity_independently_verified":False})
            frames.append(duration)
        parts=choose_contiguous_wav_parts(frames,audio_budget_s=audio_budget_s)
        new_parts=[]
        for i,(start,end) in enumerate(parts,1):
            new_parts.append({"part_id":f"part_{i:02d}",
                              "slides":[start+1,end],
                              "wav_only_duration_s":round(sum(frames[start:end]),4),
                              "new_encoded_video_duration_verified":False,
                              "element_highlight_speech_sync_verified":False})
        sections.append({"subchapter":topic,
                         "original_source_sha256":original["source_sha256"],
                         "original_slides_sha256":original["slides_sha256"],
                         "historic_audio_still_used":len(changed)<len(frames),
                         "new_audio_candidate_slide_count":len(changed),
                         "new_audio_candidate_details":changed,
                         "all_candidate_parts_within_audio_budget":all(
                             x["wav_only_duration_s"]<=audio_budget_s+.0001 for x in new_parts),
                         "parts":new_parts})
    require(set(changes)=={f'{section["subchapter"]}/{x["slide"]}'
                 for section in sections for x in section["new_audio_candidate_details"]},
                 "Unknown subchapter/slide replacement requested")
    return {"status":"REAL_PCM_DURATION_REPARTITION_CANDIDATE_ONLY",
            "audio_budget_s":audio_budget_s,
            "original_chapter":str(root),
            "source_sections":sections,
            "new_audio_candidate_slides":sum(s["new_audio_candidate_slide_count"]
                                               for s in sections),
            "new_audio_claimed_speech_correct":False,
            "new_audio_claimed_same_voice":False,
            "independent_source_math_accepted":False,
            "all_new_encoded_videos_accepted":False,
            "student_publication_authorized":False}
