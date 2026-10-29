# PR274: Extend actual encoded element-highlight sequence beyond two events

Tests reuse the real FFmpeg review renderer with a new synthetic third
equation at a distinct source PDF rectangle and separate nonconstant
original PCM WAV. Enforce exact adjacent PCM sample boundaries,
three distinct highlighted targets in actual decoded MP4 midpoint
frames, and decode/match real AAC audio against concatenated WAV.
Reject absent third real element WAV *before* any render destination
is created. The renderer honestly still flags full frame-by-frame
transition timing unverified; do not treat midpoint checks as complete
visual synchronization certification.

No Gemini or external TTS, no changes to original lectures, and no
student publication.
