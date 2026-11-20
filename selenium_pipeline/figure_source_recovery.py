"""Source-verified reuse of existing panels after duplicate-target mapping failures.

Fail closed unless every new source crop is pixel-identical to exactly one
previously published lettered panel, and the old complete parent exactly
contains the crops in their original order. No image writes occur here.
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from .figure_composites import normalized_target_filename

_SIMPLE_PARENT = re.compile(r"(?i)^figure\s+(\d+)\.(\d+)\.png$")
_PANEL = re.compile(r"(?i)^figure\s+(\d+)\.(\d+)\s*(?:\(([a-z])\)|([a-z]))\.png$")


def _pixels(path: Path):
    from PIL import Image
    with Image.open(path) as im:
        im.load()
        rgba = im.convert("RGBA")
        return rgba.size, rgba.tobytes()


def _matches(a: Path, b: Path) -> bool:
    try:
        return _pixels(a) == _pixels(b)
    except (OSError, ValueError, ImportError):
        return False


def _parent_is_exact_mosaic(parent: Path, crops: list[Path]) -> bool:
    """Only accept an exact prior, gap-free horizontal or vertical layout."""
    try:
        from PIL import Image
        with Image.open(parent) as source:
            full = source.convert("RGBA")
        tiles = []
        for crop in crops:
            with Image.open(crop) as im:
                tiles.append(im.convert("RGBA"))
        if not tiles:
            return False
        if full.size == (sum(t.width for t in tiles), max(t.height for t in tiles)):
            x = 0
            for tile in tiles:
                if full.crop((x, 0, x + tile.width, tile.height)).tobytes() != tile.tobytes():
                    return False
                x += tile.width
            return True
        if full.size == (max(t.width for t in tiles), sum(t.height for t in tiles)):
            y = 0
            for tile in tiles:
                if full.crop((0, y, tile.width, y + tile.height)).tobytes() != tile.tobytes():
                    return False
                y += tile.height
            return True
    except (OSError, ValueError, ImportError):
        return False
    return False


def reuse_verified_prior_panels(
    triples: list[tuple[str, str, str]],
    crops_dir: Path,
    roots: tuple[Path, ...],
) -> list[tuple[str, str, str]]:
    """Repair only independently proven prior panel mappings.

    A model can label two distinct crops as the same parent figure. We never
    invent a panel order or image: all crops and the complete parent must
    pixel-match a previously published set of lettered files. Otherwise
    leave the mapping unchanged for the existing fail-closed validator.
    """
    targets = [normalized_target_filename(t) for _, _, t in triples]
    counts = Counter(t.casefold() for t in targets)
    duplicates = {t for t, n in counts.items() if n > 1}
    if not duplicates:
        return triples

    roots = tuple(Path(root) for root in roots)
    result = list(triples)
    for key in duplicates:
        indices = [i for i, target in enumerate(targets) if target.casefold() == key]
        matched = _SIMPLE_PARENT.fullmatch(targets[indices[0]])
        if matched is None:
            continue
        chapter, figure = matched.groups()
        crop_paths = [Path(crops_dir) / triples[i][0] for i in indices]
        if not all(path.is_file() for path in crop_paths):
            continue

        # Build candidate panel names from existing files only, never
        # from a guess about how many panels a textbook figure contains.
        candidates: dict[str, Path] = {}
        conflict = False
        for root in roots:
            if not root.is_dir():
                continue
            for f in root.iterdir():
                if not f.is_file() or f.suffix.lower() != ".png":
                    continue
                m = _PANEL.fullmatch(f.name)
                if not m or (m[1], m[2]) != (chapter, figure):
                    continue
                letter = (m[3] or m[4]).lower()
                if letter in candidates and not _matches(f, candidates[letter]):
                    conflict = True
                    break
                candidates[letter] = f
            if conflict:
                break
        if conflict or len(candidates) < len(indices):
            continue

        fixed: list[Path] = []
        seen: set[str] = set()
        for crop in crop_paths:
            matches = [(letter, f) for letter, f in candidates.items() if _matches(crop, f)]
            if len(matches) != 1 or matches[0][0] in seen:
                fixed = []
                break
            letter, previous = matches[0]
            seen.add(letter)
            fixed.append(previous)
        if len(fixed) != len(indices):
            continue

        # Confirm the old parent consists of exactly these *source-derived*
        # tiles before using its part labels to resolve the duplicate target.
        parent = next(
            (root / targets[indices[0]] for root in roots
             if (root / targets[indices[0]]).is_file()
             and _parent_is_exact_mosaic(root / targets[indices[0]], crop_paths)),
            None,
        )
        if parent is None:
            continue
        for index, old in zip(indices, fixed):
            crop, label, _ = triples[index]
            result[index] = (crop, label, old.name)
    return result
