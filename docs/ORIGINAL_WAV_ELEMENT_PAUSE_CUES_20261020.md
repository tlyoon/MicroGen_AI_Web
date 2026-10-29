# PR177 — original WAV sample-indexed provisional highlight cues

For existing Thomas Calculus 8.4 slide 5, the original source slides.pdf has eight separate visible text geometry blocks (not all correspond to independently spoken phrases). The original 59.45533-second slide5.wav has sufficient acoustic pause evidence to generate eight contiguous sample-indexed candidate intervals: 0,3.56,4.94,13.14,19.96,44.64,49.48,54.38,59.45533 sec. Each interval is linked in order to an original rendered PDF text-block rectangle and the EXACT same original source WAV/PDF hashes. No cuts, paid TTS or ASR/Whisper required.

**Critical:** pause detection is NOT forced speech-to-text alignment. The mapping from each sound interval to each visual text block is a HYPOTHESIS requiring separate word/element timing verification; it must not confer synchronized narrated highlight technical acceptance, even if a provisional pilot MP4 is rendered. Additional source blocks, overlapping formula parts, or emphasis can require a better transcript-backed alignment. Audio with inadequate pauses fails closed instead of assuming evenly spaced words.

Dell-115 only, parent PR176 exact SHA `86d9b816d3c1b3f4b390eb69173404974c31bbfa`. Source/slides/WAV/MP4 unchanged. Not student-publishable, strictly <600s MP4 and math QA unchanged.
