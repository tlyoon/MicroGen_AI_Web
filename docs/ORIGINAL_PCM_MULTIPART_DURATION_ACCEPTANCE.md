# Original-source actual-WAV multipart duration envelope

This Windows-only, read-only planner requires the original source PDF, exact compiled slide PDF, narration script, all recorded mono PCM16 slide WAVs, and an all-passing source-bound TTS QA report. It hashes every input and recorded WAV. It creates no videos, overwrites no source/audio, and never authorizes publication.

**Real Dell-115 acceptance (2026-10-30):**
- Thomas §8.4: 17 QA-passed WAVs, 2 contiguous parts; maximum projected duration including configured 1.5 seconds per slide = **538.52 seconds**. Source/slide/script/QA and PCM inputs remained intact.
- Thomas §8.5: 11 QA-passed WAVs, 1 part; maximum projected duration = **466.86 seconds**.
- In both cases planned parts are below the conservative 540-second planning budget, hence strictly below the 600-second contractual video limit. **No MP4 is approved by this test.**
- The output sidecars are stored outside production source folders; the source PDF remains unchanged.

Final decoded MP4 duration and pixel-accurate source-element highlighting remain mandatory independent production acceptance gates. Oversized single-slide speech fails closed pending legitimate source-grounded utterance splitting.