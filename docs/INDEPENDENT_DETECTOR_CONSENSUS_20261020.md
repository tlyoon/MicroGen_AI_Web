# PR162 — independent AKAZE cross-check of ORB figure geometry

Dell-115 isolated new branch stacked on PR161 exact
`95d21224683fd3495ebe01716c2ed78ec23606b3`.
Independent ORB/RANSAC analysis is checked by separately
detecting AKAZE descriptors in the same original PDF
vector-render corridor and the independently visible embedded
slide bitmap. Applies descriptor-ratio filtering, separate
RANSAC per four arbitrary equal-width slide scan bins,
and checks fitted linear components (0.035 tolerance)
and translation (12 px tolerance). Disagreements and
insufficient independent inliers are not confirmed.

Real original Thomas Calculus 8.4 Figure 8.3, source page 2,
slide 5: AKAZE yields 23 candidate descriptor matches.
Independent consistency with ORB in arbitrary scan bins
0 and 3 only (9 and 5 AKAZE RANSAC inliers). Bins 1 and 2
lack sufficient independent AKAZE evidence, NOT proof that
the original graph/slide pixels are invalid.
These bins are not scientifically proven figure panels.
All four-bin panel count, scientific correctness, missing
or extra axes/curves/labels, rendered figure completeness,
and student publication remain UNVERIFIED. No TTS/video
generated. A second local detector match is not
independent mathematical validation.
Source/slide SHA hashes unchanged; CLI exits 2.

7 focused tests cover good transforms, mismatched translation,
scale, inadequate secondary evidence, malformed/nonfinite
fits and mismatched bin indices. Preserve historical assets,
three dirty G: trees, unrelated old uncommitted checkout,
HP/Yoga6/Zenbook, paid TTS, Whisper/ASR, GCS external
lease, protected main and publication. Strict <600s
encoded MP4 parts, real spoken-element highlighting,
Flash-Lite/Kore default and approved voice-consistent
fallback after 3 actual failures remain contract rules.
