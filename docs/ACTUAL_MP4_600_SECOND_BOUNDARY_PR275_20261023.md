# PR275: exact PCM multipart accounting and actual encoded time limit

The existing per-element PCM sample clock splitter caps each grouped part
strictly BELOW 540 seconds, with a conservative 60-second margin to
the contractual encoded duration of less than 600 seconds.
This change adds adversarial exact-boundary tests requiring no lost,
duplicated or reordered source utterance IDs or PCM samples at the
540-second planning boundary.

Additionally FFmpeg encodes actual 599-second and 600-second sparse
synthetic video+audio MP4 files and the existing independent probe
accepts strictly below 600 seconds and rejects exactly 600 seconds.
No parameter that weakens the existing 540s plan or 600s final
acceptance is changed. No real 540s narrated element-highlights are
claimed to have been rendered by these sparse-media tests.

Original Thomas 8.4 mathematics 0/71 accepted; no real new TTS,
source media edits, student release or changes to scheduled tasks.
