# PR168 — rendered original textbook / slide review packet

A caller can create a NEW non-overlapping, non-symlinked
scratch review directory containing:

- `original_source_review.png`: independent rendering of
  original textbook source page with a red outline ONLY around
  source vector components without measured registration.
- `existing_slide_review.png`: independently rendered original
  slide page, no modifications to source PDF.
- `review_manifest.json`: exact source and slides PDF SHA256,
  independently rendered PNG hashes, original figure locator,
  vector index requiring review and explicit blocker statuses.

Real Thomas Calculus 8.4 page 2/source, slide 5 successfully
created the packet with isolated source vector **index 30**
marked for inspection. Tested reading both original PDFs
read-only, producing file lengths 134154 / 49280 bytes
and JSON receipt 1002 bytes in an isolated scratch folder.
Temporary rendered output was removed after test; no original
G: teaching assets were modified.

No packet field identifies a mathematically complete graph:
figure membership, panel labels, original-to-slide exact
pixel content, encoded <600s replacement and synchronized
narration highlights remain unproven and blocked. Missing
keypoint proximity does not mean omitted slide stroke.

The CLI **always exits status 2** (review required).
Original files cannot be overwritten, output folder must
not exist, cannot overlap original lecture directory or
be a symlink, and fake upstream approval is rejected before
output creation. All output hashes are reproducible receipts,
not publication permission. Only Dell-115 was accessed.
No Whisper/ASR, GCS lease, paid TTS, main merge or publication;
primary Flash-Lite/Kore, 3-real-failure homogeneous fallback,
<600s encoded MP4 and spoken-highlight contract unchanged.
