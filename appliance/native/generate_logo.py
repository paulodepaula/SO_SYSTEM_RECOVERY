#!/usr/bin/env python3
"""Generate a self-contained LVGL RGB565 logo from committed PD SVG/WebP.

This is an offline asset converter, not a network fetch. Source is the project's
exact embedded image, never a placeholder logo.
"""
from __future__ import annotations
import base64
import io
import re
import sys
from pathlib import Path
from PIL import Image


def convert(source: Path, dest: Path, size: int = 64) -> None:
    svg = source.read_text(encoding="utf-8")
    match = re.search(r"href=\"data:image/webp;base64,([A-Za-z0-9+/=]+)\"", svg)
    if not match:
        raise ValueError("PD logo asset must contain embedded WebP")
    raw = base64.b64decode(match.group(1), validate=True)
    with Image.open(io.BytesIO(raw)) as img:
        # White background is intentional and matches supplied identity.
        image = Image.new("RGB", img.size, "white")
        if img.mode in {"RGBA", "LA"}:
            image.paste(img.convert("RGBA"), mask=img.convert("RGBA").getchannel("A"))
        else:
            image.paste(img.convert("RGB"))
        image = image.resize((size, size), Image.Resampling.LANCZOS)
    pixels = bytearray()
    for red, green, blue in image.getdata():
        rgb565 = ((red >> 3) << 11) | ((green >> 2) << 5) | (blue >> 3)
        pixels += rgb565.to_bytes(2, "little")
    lines = []
    for i in range(0, len(pixels), 16):
        lines.append("    " + "".join(f"0x{b:02x}, " for b in pixels[i:i+16]))
    content = f"""/* Generated from assets/logo-paulo.svg. Do not manually edit. */
#include "lvgl/lvgl.h"
static const uint8_t pd_pixels[] = {{
{chr(10).join(lines)}
}};
const lv_image_dsc_t redeti_pd_logo = {{
    .header.magic = LV_IMAGE_HEADER_MAGIC,
    .header.cf = LV_COLOR_FORMAT_RGB565,
    .header.flags = 0,
    .header.w = {size},
    .header.h = {size},
    .header.stride = {size*2},
    .data_size = sizeof(pd_pixels),
    .data = pd_pixels,
}};
"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: generate_logo.py INPUT_SVG OUTPUT_C")
    convert(Path(sys.argv[1]), Path(sys.argv[2]))
