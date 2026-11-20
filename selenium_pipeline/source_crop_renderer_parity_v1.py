"""Portable same-source PNG crop parity across PyMuPDF rendering versions.

A valid PNG generated from an immutable PDF may differ by a few antialiased
edge pixels when independently reconstructed on a different MuPDF build.
Do not require a cross-version PNG byte hash for re-rendered trial pixels;
the actual stored PNG MUST still match the source-locked ledger SHA-256.
Reject changed geometry, absent panels, altered labels, or substantial edits.
This does not replace source caption/panel witnesses, PDF XObject provenance,
or final-page raster visibility checks.
"""
from __future__ import annotations

from pathlib import Path
from PIL import Image,ImageChops

MAX_CHANNEL_DIFFERENCE = 24
MAX_GREY_DIFFERENCE = 20
MAX_FRACTION_DIFF_GT1 = 0.018
MAX_FRACTION_DIFF_GT5 = 0.006
MAX_TILE_FRACTION_DIFF_GT5 = 0.018


def verified_renderer_parity(*,reconstructed:Path,ledger_png:Path)->dict:
    from .cross_pc_artifact_recovery_registry import require_cross_pc_handler
    require_cross_pc_handler("SOURCE_CROP_PIXELS_DIFFER_ACROSS_RENDERERS")
    reconstructed=Path(reconstructed)
    ledger_png=Path(ledger_png)
    if (not reconstructed.is_file() or not ledger_png.is_file()
        or reconstructed.is_symlink() or ledger_png.is_symlink()):
        raise ValueError("Source crop renderer parity needs regular PNG files")
    # Pillow otherwise accepts hidden bytes appended after PNG IEND;
    # never let a forged matching ledger SHA disguise that alteration.
    iend=b"\x00\x00\x00\x00IEND\xaeB\x60\x82"
    for source in (reconstructed,ledger_png):
        if (source.suffix.lower()!=".png"
            or not source.read_bytes().endswith(iend)):
            raise ValueError("PNG is not an intact exact source PDF crop")
        try:
            with Image.open(source) as check:
                check.verify()  # PNG critical chunk CRC validation
        except Exception as exc:
            raise ValueError("PNG CRC or source crop structure invalid") from exc
    with Image.open(reconstructed) as x, Image.open(ledger_png) as y:
        if (x.format!="PNG" or y.format!="PNG"
            or x.size!=y.size or x.width<30 or x.height<30
            or x.mode not in ("RGB","RGBA") or y.mode not in ("RGB","RGBA")):
            raise ValueError("Source crop PNG format, color or geometry mismatch")
        a,b=x.convert("RGB"),y.convert("RGB")
    delta=ImageChops.difference(a,b)
    channel=delta.histogram()
    max_channel=max(
        max(i for i,cnt in enumerate(channel[j*256:(j+1)*256]) if cnt)
        for j in range(3))
    grey=delta.convert("L")
    h=grey.histogram()
    n=grey.width*grey.height
    above1=sum(h[2:])/n
    above5=sum(h[6:])/n
    above20=sum(h[21:])
    worst_tile_gt5=0.0
    for ty in range(4):
        for tx in range(4):
            tile=grey.crop((tx*grey.width//4,ty*grey.height//4,
                            (tx+1)*grey.width//4,(ty+1)*grey.height//4))
            pix=tile.width*tile.height
            worst_tile_gt5=max(
                worst_tile_gt5,sum(tile.histogram()[6:])/pix)
    if (max_channel>MAX_CHANNEL_DIFFERENCE
        or above20>0
        or above1>MAX_FRACTION_DIFF_GT1
        or above5>MAX_FRACTION_DIFF_GT5
        or worst_tile_gt5>MAX_TILE_FRACTION_DIFF_GT5):
        raise ValueError(
            "Source crop exceeds bounded cross-renderer antialiasing drift")
    return {
        "status":"SAME_SOURCE_CROP_RENDERER_PARITY_VERIFIED",
        "max_channel_difference":max_channel,
        "changed_gt1_fraction":round(above1,8),
        "changed_gt5_fraction":round(above5,8),
        "worst_tile_gt5_fraction":round(worst_tile_gt5,8),
        "changed_gt20_pixels":above20,
        "source_png_original_sha_required_externally":True,
        "scientific_or_student_approval":False,
    }
