"""Quicklook Preview Generator for AI agent visual grounding."""

import io
import base64
from typing import Optional
import numpy as np
from PIL import Image


def generate_ascii_preview(data: np.ndarray, width: int = 40, height: int = 20) -> str:
    """
    Generate an ASCII density map from a 2D float array (e.g. NDVI or elevation).
    Helps text-only LLMs understand spatial clustering and distribution.
    """
    if data.ndim == 3:
        data = data[0]

    # Subsample data to target ASCII dimensions
    h, w = data.shape
    step_y = max(1, h // height)
    step_x = max(1, w // width)
    sub = data[::step_y, ::step_x]

    # Map values to density ramp
    ramp = " .:-=+*#%@"
    valid = sub[~np.isnan(sub)]
    if len(valid) == 0:
        return "[Empty or All-NaN Raster]"

    min_val, max_val = np.min(valid), np.max(valid)
    val_range = max(1e-5, max_val - min_val)

    lines = []
    for row in sub:
        line_chars = []
        for val in row:
            if np.isnan(val):
                line_chars.append(" ")
            else:
                norm = int(((val - min_val) / val_range) * (len(ramp) - 1))
                norm = max(0, min(len(ramp) - 1, norm))
                line_chars.append(ramp[norm])
        lines.append("".join(line_chars))

    return "\n".join(lines)


def array_to_png_bytes(data: np.ndarray, colormap: str = "viridis") -> bytes:
    """Convert a normalized 2D numpy array into a PNG image byte buffer."""
    if data.ndim == 3:
        data = data[0]

    valid = data[~np.isnan(data)]
    if len(valid) == 0:
        img = Image.new("L", (100, 100), color=0)
    else:
        min_v, max_v = np.min(valid), np.max(valid)
        rng = max(1e-5, max_v - min_v)
        norm = np.clip((data - min_v) / rng * 255.0, 0, 255).astype(np.uint8)
        img = Image.fromarray(norm, mode="L")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
