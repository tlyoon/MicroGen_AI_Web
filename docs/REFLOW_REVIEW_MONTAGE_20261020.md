# PR173 — side-by-side exact-source-ink review montage

A source-slide figure geometry acceptance mismatch can be investigated
with a new **isolated, not publishable** rendered review montage.
The command uses the independently matched original source figure
panel y bands and original PDF render x bounds, alongside the
actual visible existing slide bitmap x bands. It preserves both
side-by-side pixel crops without resizing, and creates a hash-bound
manifest. This makes missing axes or altered source plot ink
inspectable without guessing the published graphic.

Real original Thomas Calculus 8.4 source p2 to slide5:
a fresh Dell-115 isolated review directory produced
`source_slide_comparison.png` (58,377 bytes) and
`review_manifest.json` (2,826 bytes), exit status 2.
The scratch directory was deleted after QA.
Original source.pdf and slides.pdf remained untouched.
The command refuses existing output, original lecture subfolder
output, invalid source hashes/graph counts/bounds and symlinks.

This montage is NOT a source-identical replacement for the
slide; original textbook figure axes/labels still require
independent mathematical verification. CLI return 2 and
all student publication/encoded MP4/highlight flags false.
Run solely on Dell-115, parent PR172 SHA
`5b4b558f8e7beb283c2568d2b2eefbebcc25e1ca`.
No other PCs, paid calls, Whisper/ASR, main merge, GCS lease,
or historical source/slides/WAV/MP4 changes.
