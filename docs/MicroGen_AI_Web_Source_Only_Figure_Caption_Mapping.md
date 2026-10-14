# MicroGen figure-caption mapping: source-only prompt

The caption-mapping phase must use **only** the attached original textbook page image and its extracted figure crops. Figure identity must not be inferred from online searches, generic textbook recall, or guessed numbering. The Gemini prompt now explicitly forbids web lookup and tells the model to return `MAPPING_REVIEW_REQUIRED` if a crop cannot be matched to a caption on that page.

A multipart source crop, including Figure 2.10(a–c) from Thomas Calculus §2.2, must not be renamed or treated as only one of its panels. Source pixel fidelity still requires independent crop/figure QA; the prompt alone does not prove fidelity.

This is an **instruction-level improvement, not a control over Gemini's browser tools or proof that it obeyed**. Fail-closed mapping count checks and figure target collision guards remain necessary. Long Gemini response times and rejected page mappings must not produce a successful stage receipt. The problem was detected during the 14 October 2026 Yoga 6 isolated pilot; the model sometimes entered "Searching the web" for a simple local-caption task. Prompt changes take effect on a **new invocation**, not an already-running Python process.

The current experimental Thomas source's Section 2.1 carryover exercise and §2.2 exercise bank must not silently become lecture exposition. This needs the separate approved instructional scope/part plan; caption extraction does not approve curriculum scope.
