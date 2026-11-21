"""Independent appearance check for source-accurate PNGs on rasterized slides.

Checking a PDF XObject alone is insufficient: an image may be painted outside
the page, clipped or covered by subsequent PDF drawing commands. This routine
rasterizes the final page and compares meaningful source pixels with the page
appearance in 4x4 tiles, rejecting major regional occlusion or altered pixels.
It does NOT replace scientific review, slide legibility, or media acceptance.
"""
from __future__ import annotations
from PIL import Image, ImageChops, ImageFilter

ZOOM = 2.0
MAX_TOTAL_CONTENT_MISMATCH = 0.24
MAX_TILE_CONTENT_MISMATCH = 0.46

def _content_count(mask):
    return mask.histogram()[255]

def _content_mismatch(expected, observed):
    # The two independent renderers use different edge antialiasing.
    # Blur both slightly before thresholding, to preserve coarse fidelity.
    # Slightly stronger symmetric blur tolerates legitimate downsampling of
    # sparse text/diagram pixels; unchanged total/tile occlusion thresholds
    # still reject half-covered images in physical PDF regression tests.
    expected = expected.filter(ImageFilter.GaussianBlur(0.75))
    observed = observed.filter(ImageFilter.GaussianBlur(0.75))
    content = expected.convert("L").point(lambda x: 255 if x < 239 else 0)
    delta = ImageChops.difference(expected, observed).convert("L")
    changed = delta.point(lambda x: 255 if x > 62 else 0)
    mismatch = ImageChops.multiply(content, changed)
    count = _content_count(content)
    return count, _content_count(mismatch)

def render_visibility(page, rectangle, source_image, *, minimum_width_pt=35.0):
    """Return explicit visual evidence; no silent XObject-only acceptance."""
    import fitz
    rect = fitz.Rect(rectangle)
    canvas = page.rect
    if (not rect.is_valid or rect.width < minimum_width_pt or
        rect.height < 24.0 or rect.x0 < canvas.x0 + 0.5 or
        rect.y0 < canvas.y0 + 0.5 or rect.x1 > canvas.x1 - 0.5 or
        rect.y1 > canvas.y1 - 0.5):
        return {"verified":False,"reason":"OUTSIDE_PAGE_OR_TOO_SMALL"}
    width = int(round(rect.width*ZOOM))
    height = int(round(rect.height*ZOOM))
    if width < 80 or height < 48:
        return {"verified":False,"reason":"INSUFFICIENT_RASTER_DETAIL"}
    # PDF render is the acceptance target, not its embedded image dictionary.
    pix=page.get_pixmap(matrix=fitz.Matrix(ZOOM,ZOOM), colorspace=fitz.csRGB, alpha=False)
    page_image=Image.frombytes("RGB",(pix.width,pix.height),pix.samples)
    left,top=int(round(rect.x0*ZOOM)),int(round(rect.y0*ZOOM))
    right,bottom=int(round(rect.x1*ZOOM)),int(round(rect.y1*ZOOM))
    if left<0 or top<0 or right>pix.width or bottom>pix.height:
        return {"verified":False,"reason":"RASTER_CLIPPED_BY_PAGE"}
    observed=page_image.crop((left,top,right,bottom))
    expected=source_image.convert("RGB").resize(observed.size,Image.Resampling.BICUBIC)
    count,mismatch=_content_mismatch(expected,observed)
    if count < 200:
        return {"verified":False,"reason":"SOURCE_CONTENT_TOO_SPARSE_TO_ATTEST"}
    overall=mismatch/count
    worst=0.0
    inspected=0
    w,h=observed.size
    for yy in range(4):
        for xx in range(4):
            tile=(w*xx//4,h*yy//4,w*(xx+1)//4,h*(yy+1)//4)
            exp=expected.crop(tile)
            obs=observed.crop(tile)
            relevant,bad=_content_mismatch(exp,obs)
            if relevant < 55:
                continue
            inspected+=1
            worst=max(worst,bad/relevant)
    return {
        "verified":overall<=MAX_TOTAL_CONTENT_MISMATCH and worst<=MAX_TILE_CONTENT_MISMATCH,
        "reason":"RASTER_CONTENT_VISIBLE" if overall<=MAX_TOTAL_CONTENT_MISMATCH and worst<=MAX_TILE_CONTENT_MISMATCH else "RASTER_OCCLUDED_OR_ALTERED",
        "content_pixels":count,
        "mismatched_content_fraction":round(overall,4),
        "worst_tile_fraction":round(worst,4),
        "content_tiles_checked":inspected,
        "display_width_pt":round(rect.width,2),
        "display_height_pt":round(rect.height,2),
    }
