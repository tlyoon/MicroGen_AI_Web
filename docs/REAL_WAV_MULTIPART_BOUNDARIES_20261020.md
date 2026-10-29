# PR174 — real slide WAV boundary preflight for strict <600s lecture

Read the original per-slide WAV files, check uncompressed PCM,
contiguous numerical indices and rendered PDF slide count, and
choose a minimal-count, balanced contiguous whole-slide
grouping with a **540-second audio-only budget per part**.
This leaves 60 seconds for encoding/transitions/time alignment
headroom relative to the strictly less than 600-second
final encoded MP4 rule, but is NOT a guarantee of encoded
duration and NOT a substitute for actual FFmpeg evidence.

For original Thomas Calculus 8.4: 17 original slide WAVs
total **632.7107 seconds**, measured from exact WAV
sample rates and frames. Two proposed non-destructive parts:
**slides 1–8 = 321.8927s** and
**slides 9–17 = 310.8180s**.
Neither slide-level narration needs to be cut, no TTS call
is required merely to identify a suitable boundary, and
the original 633.93s MP4 remains unchanged and noncompliant.

The planner is deterministic, verifies each source PDF,
slide PDF, WAV count and original file hash, rejects a
single slide WAV exceeding audio budget, missing indices,
malformed audio, excessive part count and stale source.
It is explicitly a CANDIDATE, not a generated video.
CLI return 2, `encoded_video_part_strictly_below_600_verified=False`,
`speech_element_highlights_verified=False`,
`student_publication_authorized=False`.
A later stage must independently render and actually
measure every MP4 part, verify voiced-element
highlight pixels/timings, and retain human academic
listening QA.

Dell-115 only, parent PR173 exact head
`79a8084b522937b7ddc973003091e74361adee12`.
Never alter original source, WAV, slides, MP4 or other
users' G: trees. No HP/Yoga6/Zenbook, Whisper/ASR,
GCS lease, paid TTS, main merge or publication.
