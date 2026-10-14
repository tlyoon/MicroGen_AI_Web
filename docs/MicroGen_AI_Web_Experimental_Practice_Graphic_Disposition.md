# Explicit source-grounded experimental practice-graphic disposition

**Problem found in actual Thomas Calculus §2.2 pilot (Yoga 6, 14 October 2026):** Original textbook PDF page 9 is headed "Limits from Graphs" in Exercises 2.2, and its four unlabeled graph drawings belong to Exercises 1–4. There are no printed "Figure 2.x" labels to map. An otherwise correct Gemini model therefore returned \`MAPPING_REVIEW_REQUIRED\`. Repeatedly prompting for nonexistent figure numbers wasted minutes and correctly blocked the old full figure stage.

## Intended behavior

- The default is **never to exclude a source crop**. All figures require normal successful mappings.
- In an **isolated, unapproved experimental pilot only**, an operator may explicitly classify the **entire exercise page's existing graphics** as practice-only when the source PDF's own printed text contains the supplied exact heading and contains no numbered figure labels. Raw \`fig_N.png\` images are **preserved in their crop directory** and are not assigned invented captions, discarded, or published as numbered figures.
- The required \`figure_practice_disposition.json\` sits **beside the original source.pdf copy in the work folder**, not beside the cloud teaching root. It records the source PDF SHA-256, rendered page PNG SHA-256, each original crop's name/SHA-256 and an exact checked page heading. It explicitly says \`scientific_review_status=unreviewed\` and \`student_publication_permitted=false\`.
- A second, explicit environment gate \`MICROGEN_ENABLE_EXPERIMENTAL_PRACTICE_SCOPE=1\` must be set **on this run** to use the unapproved disposition. A missing flag with a present manifest is a **blocking error**, not an excuse to skip. Hash changes, unsafe paths, source figure citations or changed crops also fail closed.
- The mapper skips only the specifically declared page, while the updated \`runner.valid("figures", folder)\` accounts for its preserved exercise-only crops. Successfully mapped numbered figures on all other pages still require byte-identical original crops, renamed targets and published work-root copies.
- This does **not** approve lesson coverage, mathematical narration, missing panels, video release or any new automatic inference of practice pages. The reviewed concept outline and independently accepted source figure images remain separate approval gates.

## Explicit one-time operation for the disposable Yoga 6 pilot

The original textbook file is not edited. Run with an isolated up-to-date clone (paths here are pilot-specific):

\`\`\`powershell
$root = 'C:\MicroGen_Phase5_YogaPilot_Work_20261014\2\2.2'
$py   = 'C:\Users\User\miniconda3\envs\docling_3\python.exe'
$env:PYTHONPATH = 'C:\MicroGen_Phase5_ExerciseScopeQA_20261014'
& $py -m selenium_pipeline.figure_practice_disposition --work-root $root --page 9 --source-heading 'Limits from Graphs'
$env:MICROGEN_ENABLE_EXPERIMENTAL_PRACTICE_SCOPE = '1'
# The verified page-mapping checkpoints allow pages 1-8 to be reused.
& $py 'C:\MicroGen_Phase5_ExerciseScopeQA_20261014\selenium_pipeline\vendor_template_v2\map_and_rename_selenium_v8.py' --start 1 --end 11 --copy_to_root 1
\`\`\`

Execute the mapper in the \`$root\` current directory when using its direct CLI, and ensure Chrome debugging/authentication is already available when needed. The mapping stage should now skip page 9 as a practice graphic source rather than send false caption requests. Pages 10–11 contain no source figure crops and require no model request.

This temporary experimental manifest **must not be copied into another textbook or trusted as a curriculum approval receipt**. Actual teaching release still requires expert mathematical/source visual checks and approved planned video coverage. To add another special page for a different book, inspect the original source and create a separate explicit disposition rather than modifying this file.

## Regression coverage

\`tests/test_figure_practice_disposition.py\` checks omission by default, explicit opt-in, genuine source-heading evidence, the numbered-figure guard, no silent overwrite, changed source/page/crop hashes, altered manifest, corrupt JSON, separate practice status, and fail-closed runner figure validation.

The existing source-bound mapping checkpoints and full regression suite remain required.
