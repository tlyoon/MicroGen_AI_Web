"""Technical G3 page-level audio/video duration comparison utilities."""

import math

def compare_g3_audio_video_page_durations(
wav_durations_ms, frame_durations_ms, tolerance_ms
):
    """Compare per-page WAV and video frame durations within a tolerance."""
    wav_list = (
    list(wav_durations_ms)
    if isinstance(wav_durations_ms, (list, tuple))
    else []
    )
    frame_list = (
    list(frame_durations_ms)
    if isinstance(frame_durations_ms, (list, tuple))
    else []
    )
    valid_tolerance = (
    isinstance(tolerance_ms, (int, float))
    and not isinstance(tolerance_ms, bool)
    and math.isfinite(tolerance_ms)
    and tolerance_ms >= 0
    )
    page_count = max(len(wav_list), len(frame_list))
    mismatched_pages = [
    idx + 1
    for idx in range(page_count)
    if not (
    valid_tolerance
    and idx < len(wav_list)
    and idx < len(frame_list)
    and isinstance(wav_list[idx], (int, float))
    and not isinstance(wav_list[idx], bool)
    and math.isfinite(wav_list[idx])
    and wav_list[idx] >= 0
    and isinstance(frame_list[idx], (int, float))
    and not isinstance(frame_list[idx], bool)
    and math.isfinite(frame_list[idx])
    and frame_list[idx] >= 0
    and abs(wav_list[idx] - frame_list[idx]) <= tolerance_ms
    )
    ]
    return {
    "technical_timing_match": bool(
    valid_tolerance and page_count > 0 and not mismatched_pages
    ),
    "mismatched_pages": mismatched_pages,
    "independent_scientific_acceptance": False,
    "independent_acoustic_acceptance": False,
    "independent_video_highlight_acceptance": False,
    "student_publication_authorized": False,
    }
