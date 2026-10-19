# PR153 source pre-caption vector object inventory

20 Oct 2026; Dell-115 only. Stacked on draft PR152 exact HEAD
`0979ac83ef718aac935b507251deb3b6a718869e`.
This is a read-only, hash-preserving inventory, not reconstructed
author-intended source graph geometry.

`figure_pre_caption_vector_inventory.inventory_pre_caption_vectors`
enumerates original source drawing objects contained within a
conservative pre-caption page scan corridor. It does NOT merge
objects into a bounding box, certify their ownership of any one
figure, infer a/b/c panels, split source graph elements, certify
scientific content or authorize TTS/video. Rectangles after the
heading, outside the scan column, and off-page borders are excluded
with explicit reason counts. Zero-height/width but nontrivial PDF
vector line objects remain observable rather than silently omitted.

## Actual original Thomas 8.4 source page 2 / Figure 8.3

Exact heading `FIGURE 8.3`, y404.11. Scan corridor
`[0,0,207.835,401.11]`, includes 23 vector objects from 44
on original page; exclusions: 2 off-page, 5 after heading,
14 outside left column; all indices are original PDF drawing IDs.
The falsely linked adjacent procedure instruction drawing #37
is **not** in the pre-caption inventory. Original SHA256
`b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068`
unchanged. Figure caption shares PDF text block with right-side
procedure text (PR152), so visual region still requires independent
original figure membership/panel/label and source-to-slide proof.

Generated-PDF adversarial tests exercise multiple small graph line
strokes, nontrivial zero-width/height geometries, rejected lower
procedure box/off-page border, empty inventory and wrong caption.
This inventory is *not sufficient* for academic or video readiness.
No writing to original teaching assets, Git dirty shared worktrees,
other machines, or protected main; no paid TTS/YouTube/Moodle.
Full contract: strictly under 600s per encoded video part, real
narrated element highlight, primary Flash-Lite and approved
homogeneous retry fallback after 3 genuine failures.
