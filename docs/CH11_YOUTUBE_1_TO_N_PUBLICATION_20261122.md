# Chapter 11: verified one-to-many YouTube publication

On 22 November 2026, the user authorized Chapter 11-only upload and replacement of obsolete YouTube videos. Chapter 11 narrated MP4 rendering had already been approved for the explicit slide -> narration -> TTS -> MP4 scope, without requiring synchronized figure/equation highlighting. The full G3 highlight gate remains not performed; no full G3 scientific video acceptance is claimed.

## Five previous videos, eleven replacements

| Section | Retired original ID | Ordered replacement IDs |
| --- | --- | --- |
| 11.1 | 71H0K7Uj1z8 | 7W00EBqoHgQ, MmGe4P7sVnU |
| 11.2 | XbS9osdzjCA | RzCIJPHLrBQ, KJYhzHAHlCI, Wu8G527UdwE |
| 11.3 | Q1-sl0t_XOg | _5IJE67QlAM, KBmJ25_9OmM |
| 11.4 | jzNGexiV9Vw | Vw7H9yR18OI, jJ2WVXq5jZk, i_m7_cGtGzI |
| 11.5 | IbwXkizjNmM | Fy8Z5ijNgBg |

The 11 new videos are public, processed, source-fingerprint verified and positioned in playlist PLUUmsE42J5mSGz5f5jqybHIFgNqSI5tZ5 at positions 50 through 60 inclusive. The 5 originals and their orphaned playlist references were retired only after all document and PDF gates passed. Final playlist count: 79. Out-of-scope playlist relative order unchanged.

## Word DOCX and PDF synchronization

Original authoritative Word DOCX Drive ID was preserved: 1rqGGZm-tIcC2mcQCk5mc-waWKYm5QHt3 (ZCA101_2627SEM1, not similarly named older document). The authoritative remote file was fetched via Google Drive connector instead of stale Yoga6 DriveFS.

Original DOCX SHA256: b2943ff14a2937f3237ec3ba7610f85c16ef14a01e80bf82f9ab68ba1103d66b
Verified updated remote DOCX SHA256: a452070627efa1fb66166f394d8cd250e9e6841852494dc2056cfcc6558639eb
Original backup Drive ID: 1Fb_6d-1PJIbaCnNtewI6SJTAHAu6a7c3

All 11 separately clickable video hyperlinks were verified directly in the updated remotely fetched DOCX. No former video hyperlink remains active. Unrelated rows, PDF links and problem-set links remained unchanged. All five linked PDFs were fetched remotely and their binary SHA256s matched the accepted local slides PDFs; no PDF replacement was needed.

## Historical recovery and permanent implementation

Previously tested selenium_pipeline.youtube_publication_recovery guards were reused for stale DriveFS, public-visibility polling, predelete acceptance, and orphan cleanups. Dell-115 YouTube credential refresh returned invalid_grant; an already-authorized Yoga6 token for the same channel was used without copying credentials. YouTube visibility readback lag after the first change was recovered using bounded read-only polls, not repeating acknowledged mutations.

New reusable selenium_pipeline.youtube_multipart_recovery_v2 primitives provide:
- Manifest-driven and SHA-pinned 1-to-N and M-to-N parts discovery, support for zero-based and one-based slides_partNN numbering, strict time cap, and expressly scoped technical narration acceptance
- Dynamic part titles, with no assumed fixed number of MP4s or mixing generations
- Raw Google Drive Word DOCX hyperlink and remote PDF SHA verification, rejecting stale DriveFS readback and mismatched part labels
- Full playlist ordered-insertion and retirement invariants, with strict preservation of out-of-scope videos
- A complete predelete gate requiring all public/processed new video IDs, correct document links, verified PDFs and original-video identity
- Restart-safe deletion state recovery; after a mutation is acknowledged or its result uncertain, only readback is permitted, never blindly reissue a destructive request

A new executable recovery-registry entry has signature ONE_OLD_YOUTUBE_VIDEO_SUPERSEDED_BY_MULTIPLE_VERIFIED_MP4_PARTS and handler NORMAL_SOURCE_PINNED_ONE_TO_N_YOUTUBE_DOCX_RECONCILIATION.

All source/project and OAuth credentials remain in their authorized machine stores, not in Git. This mechanism does not weaken standard G3 visual-highlight acceptance or broaden the authorized Chapter 11-only publication scope.

## Durable real-execution evidence

All paths below are under G:\My Drive\Serway\Serway_8_14\.microgen_coordination on Yoga6 and synchronized Drive:
- youtube_ch11_inventory_20261122.json
- youtube_ch11_preflight_20261122.json
- youtube_ch11_upload_20261122.json
- youtube_ch11_processing_20261122.json
- youtube_ch11_playlist_prepare_20261122.json
- youtube_ch11_remote_predelete_acceptance_20261122.json
- youtube_ch11_retirement_20261122.json
- youtube_ch11_final_reconciliation_20261122.json

The final reconciliation reports all five originals conclusively absent, eleven new videos public and ordered, all five remote PDF links exact, all eleven document video links exact, and every out-of-scope playlist entry preserved.
