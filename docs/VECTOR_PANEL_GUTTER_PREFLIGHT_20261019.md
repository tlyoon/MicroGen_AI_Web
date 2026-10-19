# Vector figure panel seam evidence

A standalone preflight, stacked after the exact source-vector -> slide
raster comparison of PR #143. It detects visible nonwhite strokes near
declared horizontal/vertical panel boundaries in the actual source PDF.
It requires a white-background region, stable original/source SHA-256,
and complete full-height/full-width gutter stripes, not isolated samples.
The gutter width is bounded (2–8 pixels half-width). Missing source PDF
(a)/(b)/(c) labels, vector paths crossing seams, changed captions and
source-to-slide raster mismatch fail closed upstream.

**The evidence is necessary only within this restricted class, but NOT
sufficient** to certify the author-intended panel identities or shapes.
A shifted boundary can still fall into another blank gap. Therefore all
semantic, panel-completeness, human approval and TTS/video authorization
flags remain false. No production stage is altered.

Tests use actual synthetic source-vector and slide-raster PDFs. They
verify positive full-stripe white regions; a narrow red source mark
near an otherwise legal seam fails this new check despite passing parent
geometry; wrong labels, boundary-crossing lines, source-caption drift
and invalid gutter sizes are rejected. Additional negative test confirms
that plausible shifted separators never gain false semantic approval.

Next: read-only textbook-source pilot / pilot report with source hashes,
no changes to historical teaching files or student publication.
