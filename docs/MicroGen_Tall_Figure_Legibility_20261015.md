# Tall composite figure legibility guard

Date: 15 October 2026. This is a reusable prevention for the
Thomas Calculus 13th edition section 8.4 slide 5 defect.

Figure 8.3 has three vertically stacked complete inverse-trigonometric
graphs (232x480 pixels). It was rendered at height 0.23 of Beamer
textheight, taking only 8.0% of the finished slide width. Image
presence, completeness and LaTeX compilation checks all passed even
though the mathematical labels were unreadable in projected viewing.

The existing preflight flagged only overly wide figures reduced
into narrow columns. It is extended with a conservative portrait
case: minimum 160x360 pixels, aspect ratio at most 0.75, explicit
height at most 0.30 textheight, and estimated final frame width
at most 0.18. The width estimate uses the usual textheight/textwidth
ratio 0.72. This is a preflight heuristic, not an exact page measure;
rendered-slide visual review remains mandatory.

The bounded slide generator rejects such candidates, saves the reason
and retries with instructions to preserve all original figure panels,
labels and domains while presenting them legibly. It may reflow whole
panels horizontally or use a dedicated slide. Original wide-figure
safeguards remain; small legitimate icons are excluded by raster size.

A separate local review candidate reflows the three complete source
panels horizontally on the SAME slide 5, without editing the original
17-page slide text. The candidate compiles to 17 slides and the graph
now spans 86.5% of slide width, compared with 8.0% originally.
This proposed candidate is not approved student course content until
the corrected slides and corresponding video have been reviewed;
any publication requires a new receipt and integrity check.
