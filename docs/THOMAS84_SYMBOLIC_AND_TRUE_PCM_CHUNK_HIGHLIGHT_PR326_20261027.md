# PR326 — Source-registered actual PCM-frame timing for five original Slide-4 highlights

27 October 2026. Windows-only on Dell-115; stacked draft on PR325 at `8bc3583762bea33189fd882fce879d66645947a8`. No HP, Yoga6, Zenbook, Linux/Ubuntu CI, Whisper, Moodle publication, protected G: modifications or Gemini/API billing.

## Concrete correction of the previous technical limitation

PR325 rendered FIVE genuinely original-PDF-source highlights in a real decoded 45s MP4, but its five intervals were evenly spaced over the historical whole-slide WAV. Even though pixel QA passed, those bins did **not** align narration with slide elements.

The new `original_slide4_real_pcm_chunk_highlight` uses five **distinct actual PCM WAV files**, one per exact original registered utterance, and calculates each highlight transition from its `wave.getnframes()` and native PCM sample rate. This code does not guess equal durations or arbitrary timestamps. It inherits PR319's SHA-bound corrected utterance text and source element IDs, PR320's original slide PDF pixel reconstruction, and PR321's safeguards against historical file reuse, fake WAV headers, symlinks, extra audio files and inconsistent audio formats. It requires all five fresh candidates, excludes duplicate PCM hashes, and fails closed with no accepted video if they do not exist.

Once five external WAVs are supplied in an isolated AppData folder, it concatenates the actual PCM samples and switches through the corresponding source-PDF highlighted images at 24fps. The resulting review MP4 is independently decoded at all five measured WAV-frame-derived windows, with pixel comparisons against the intended original-PDF source element. FFmpeg also checks actual encoded audiovisual duration under 600 seconds and source hashes before/after. It uses an explicit RED `REVIEW ONLY - WAV WORDS AND KORE VOICE UNVERIFIED` banner on every frame and an exclusive external output folder.

**Crucial acceptance distinction:** A WAV that matches the PCM format, size and source utterance *filename* is NOT guaranteed to speak the corrected text, have the genuine Kore voice, or come from Flash-Lite. The review-only encoder explicitly reports all three unverified, even when five time switches and all decoded image pixels are technically correct. A small synthetic PCM tone fixture, if used in tests, exercises ONLY frame timing and encoder behavior and must be deleted after tests; it is NOT produced or described as authentic speech. No correction/WAV/provider request or original file rewrite is performed in this PR.

## Independent mathematical cross-check, not fabricated Gemini academic sign-off

The original textbook's physical source PDF Figure8.2 has the absolute-value radicals `√(a²+x²)=a|sec θ|`, `√(a²−x²)=a|cos θ|`, and `√(x²−a²)=a|tan θ|`, for `a>0`, verified directly from real page-1 raster in PR325. A **separate Wolfram Language kernel via the connected Wolfram service** independently returned `True` for 13 symbolic tests: the three radical identities, three interval sign simplifications, two negative-angle numerical witnesses, four zero-leg degeneracies, and a counterexample to allowing `a<0` without changing the root sign. This independently corroborates existing SymPy proofs but is NOT equivalent to source-locked two-pass Gemini/human scholarly review of five English utterances. Dell-115's locally installed Mathematica 12.3 is presently NOT ACTIVATED (wolframscript exits -1), so normal standalone Windows production cannot rely on local Wolfram. The new independent result is recorded as evidence only and does not bypass the two-pass source academic approval gate or permit TTS publication.

## Genuine acceptance conditions still required

1. External academically accepted source-locked text review for all revised five utterances; the prior one-use Gemini request was exhausted with 0 model text. No automatic resend.
2. Five actual newly generated Flash-Lite Kore WAVs with trusted provider/voice provenance, nonhistorical exact text-byte SHA identity and independent spoken-content verification (not merely bytes or metadata).
3. Measured PCM chunk timing and decoded original source-element highlight pixels, without the red review-only warning for accepted production.
4. Full newly corrected/encoded multi-part video review, genuine original math QA and every duration strictly less than 600 seconds. All six corrected §8.4–8.6 clips remain unaccepted; no YouTube/Moodle publication.

Source and historical output remain untouched on G:, and all generated temporary audio tests are in isolated AppData/test directories.
