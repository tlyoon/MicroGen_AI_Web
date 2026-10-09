#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import importlib.util
import json
import re
import sys
import time
from pathlib import Path

from PyPDF2 import PdfReader


def load_local_selenium_helper():
    script_dir = Path(__file__).resolve().parent
    helper_path = script_dir / "selenium.py"
    if not helper_path.is_file():
        raise FileNotFoundError(f"❌ Local helper not found: {helper_path}")

    module_name = "_microgen_local_selenium"
    spec = importlib.util.spec_from_file_location(module_name, helper_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"❌ Could not load module spec from {helper_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_local_selenium = load_local_selenium_helper()
Config = _local_selenium.Config
GeminiSeleniumClient = _local_selenium.GeminiSeleniumClient
capture_gemini_response_like_manual_copy = (
    _local_selenium.capture_gemini_response_like_manual_copy
)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def strip_code_fences(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def extract_json_object(text: str) -> str:
    text = strip_code_fences(text)
    if text.startswith("{") and text.endswith("}"):
        return text

    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if m:
        return m.group(0).strip()

    raise RuntimeError("❌ Could not locate a JSON object in Gemini response.")


def build_prompt(
    toc_text: str,
    source_md_name: str,
    output_filename: str,
    end_page: int,
) -> str:
    return f"""
IMPORTANT: You must follow the instruction below exactly.
Return JSON only.
Do not summarize the uploaded files.
Do not offer help or suggestions.
Do not ask follow-up questions.

You are a textbook analysis assistant.

You are provided with TWO uploaded files and one pasted text block:
1) An uploaded PDF slice file named `{output_filename}` containing the first {end_page} pages of a searchable textbook PDF. This file contains the TOC region/pages and includes visible page numbers.
2) An uploaded Markdown file named `{source_md_name}` containing the textbook body content.
3) A pasted TOC text extracted from the uploaded PDF slice.

Use BOTH uploaded files in your analysis:
- Open and inspect `{output_filename}` to verify TOC entries, printed page numbers, headings, and local context.
- Open and inspect `{source_md_name}` to match subchapter titles against the textbook body.

Your task is to return a structured JSON list of all subchapter entries and unnumbered subsections that appear in the TOC, with correct begin/end pages (visible) and physical pages, using a single page offset.

(1) Enumerate ALL subchapters / subsections
- Parse ALL TOC lines to extract:
  • Every numbered subchapter (e.g., "1.1", "2.3", "22.6.4.1") under each chapter, with no omissions.
  • Any unnumbered TOC subsections (e.g., "Practice Exercises", "Questions", "Review Problems", "Summary") that belong to the most recent chapter.
- For unnumbered items, assign them to the current chapter scope.

(2) Determine a SINGLE page offset
- Compute one integer offset so that:
  physical_page = visible_page + offset
- Derive it by matching at least three subchapter titles between the TOC and the uploaded Markdown file `{source_md_name}`.
- Normalize titles when matching: lowercase, collapse whitespace, remove dot leaders, de-hyphenate line breaks, Unicode NFKC.
- You may consult the uploaded PDF `{output_filename}` to confirm printed page numbers in headers/footers or to disambiguate locations.
- Apply this single offset to all items:
  • begin_physical = begin + offset
  • end_physical   = end + offset

(3) Begin/End rules (visible pages)
- For each numbered subchapter within a chapter:
  begin = its TOC page
  end = next sibling's TOC page within the same chapter
- For unnumbered items:
  treat exactly like subchapters
- For the final item in a chapter:
  if no next chapter is present in the TOC context, set end = begin + 5

(4) Output format
Return JSON only. No commentary. No code fences.

{{
  "offset": <integer>,
  "subchapters": [
    {{
      "title": "<exact title as printed in TOC>",
      "begin": <int visible>,
      "begin_physical": <int>,
      "end": <int visible>,
      "end_physical": <int>
    }}
  ]
}}

===== BEGIN TOC TEXT =====
{toc_text}
===== END TOC TEXT =====
""".strip()


def verify_prompt_landed(client, marker: str = "Return JSON only") -> None:
    editor = client._get_prompt_editable()
    landed = ""
    try:
        landed = (
            editor.get_attribute("innerText")
            or editor.get_attribute("textContent")
            or editor.text
            or ""
        ).strip()
    except Exception:
        landed = ""

    if not landed:
        try:
            landed = (editor.get_attribute("value") or "").strip()
        except Exception:
            landed = ""

    if marker not in landed:
        preview = landed[:250].replace("\n", "\\n")
        raise RuntimeError(
            "❌ Prompt text did not land in Gemini composer. "
            f"Expected marker '{marker}' not found. Composer preview: {preview!r}"
        )


def main() -> None:
    start_time = time.time()

    start_page = 1
    end_page = 36
    output_filename = f"{start_page}_{end_page}.pdf"
    source_md_name = "source.md"
    wait_cap = 600

    p_pdf = Path(output_filename)
    if not p_pdf.is_file():
        raise FileNotFoundError(f"❌ PDF slice not found: {output_filename}")

    p_md = Path(source_md_name)
    if not p_md.is_file():
        raise FileNotFoundError(f"❌ Markdown body not found: {source_md_name}")

    reader = PdfReader(str(p_pdf))
    toc_text = ""
    for i in range(min(50, len(reader.pages))):
        page = reader.pages[i].extract_text() or ""
        if page:
            toc_text += page + "\n"

    if not toc_text.strip():
        raise RuntimeError("❌ TOC text could not be extracted from the PDF slice.")

    prompt = build_prompt(
        toc_text=toc_text,
        source_md_name=source_md_name,
        output_filename=output_filename,
        end_page=end_page,
    )

    cfg = Config(root=Path.cwd())
    client = GeminiSeleniumClient(cfg)

    try:
        client.start(ensure_gemini_on_launch=True)
        client.open_clean_gemini_chat()

        client.upload_files([p_pdf, p_md])
        time.sleep(2.0)

        if not client.type_prompt_text(prompt, retries=3):
            raise RuntimeError("❌ Could not type into Gemini prompt field.")

        verify_prompt_landed(client, marker="Return JSON only")

        if not client.click_send_with_fallbacks(retries=3):
            raise RuntimeError("❌ Could not send prompt to Gemini.")

        print(f"⏳ Waiting for Gemini response (up to {wait_cap}s) ...")
        response_text = capture_gemini_response_like_manual_copy(
            client.driver,
            wait_cap=wait_cap,
            prefer_latex_doc=False,
            retries=6,
        )

        if not response_text:
            raise RuntimeError("❌ Empty response from Gemini UI.")

        print("🔎 Raw Gemini Response:\n", response_text)

    finally:
        try:
            client.shutdown()
        except Exception:
            pass

    json_text = extract_json_object(response_text)

    try:
        result = json.loads(json_text)
    except Exception as e:
        Path("subchapter_index_physical.raw.txt").write_text(response_text, encoding="utf-8")
        raise RuntimeError(
            f"❌ Failed to parse JSON from Gemini response. "
            f"Raw saved to subchapter_index_physical.raw.txt ({e})"
        )

    Path("subchapter_index_physical.json").write_text(
        json.dumps(result.get("subchapters", []), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(
        f"✅ subchapter_index_physical.json created with offset "
        f"{result.get('offset', 'N/A')}. Elapsed {time.time() - start_time:.2f}s"
    )


if __name__ == "__main__":
    main()
