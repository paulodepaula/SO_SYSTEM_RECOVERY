#!/usr/bin/env python3
"""Embed the supplied notebook and generate consistent line icons for LVGL 9.

Pillow rasterizes procedural art at build time, not on the recovery target.
The output is a C image descriptor array; no downloads or runtime decoders.
"""
from __future__ import annotations

import sys
from pathlib import Path
from PIL import Image, ImageDraw

ICONS = (
    "home", "list", "drive", "charge", "settings", "file", "wifi",
    "image", "eye", "power", "refresh", "play", "keyboard",
    "download", "directory", "save", "ok"
)


def icon(name: str) -> Image.Image:
    # Draw at 4x and downsample for smooth, uniform 2-px outlines.
    factor = 4
    image = Image.new("RGBA", (24*factor, 24*factor))
    d = ImageDraw.Draw(image)
    color = (255, 255, 255, 255)
    def pt(xy):
        return tuple(round(n*factor) for n in xy)
    def line(coords, width=2):
        d.line([pt(x) for x in coords], fill=color, width=round(width*factor), joint="curve")
    def rect(box, width=2, fill=None, radius=0):
        xy=pt(box[:2])+pt(box[2:])
        if radius:
            d.rounded_rectangle(xy,radius=radius*factor,outline=color,width=round(width*factor),
                                fill=color if fill else None)
        else:
            d.rectangle(xy,outline=color,width=round(width*factor),
                        fill=color if fill else None)
    def ellipse(box, width=2, fill=False):
        d.ellipse(pt(box[:2])+pt(box[2:]),outline=color,width=round(width*factor),
                  fill=color if fill else None)
    def arc(box,a,b,width=2):
        d.arc(pt(box[:2])+pt(box[2:]),a,b,fill=color,width=round(width*factor))
    if name=="home":
        line([(3,11),(12,4),(21,11)])
        line([(6,10),(6,20),(18,20),(18,10)])
        line([(10,20),(10,14),(14,14),(14,20)])
    elif name=="list":
        for y in (6,12,18):
            rect((3,y-1,5,y+1),1,True)
            line([(9,y),(21,y)])
    elif name=="drive":
        rect((3,6,21,19),radius=3)
        line([(5,14),(19,14)])
        ellipse((16,16,18,18),1,True)
    elif name=="charge":
        line([(13,2),(6,13),(12,13),(10,22),(19,10),(13,10),(13,2)],2.3)
    elif name=="settings":
        ellipse((8,8,16,16),2)
        for a,b,c,e in [((12,2),(12,6),(12,4),(12,6)),((12,18),(12,22),(12,18),(12,20)),
                          ((2,12),(6,12),(2,12),(6,12)),((18,12),(22,12),(18,12),(22,12)),
                          ((5,5),(8,8),(5,5),(8,8)),((16,16),(19,19),(16,16),(19,19)),
                          ((19,5),(16,8),(19,5),(16,8)),((8,16),(5,19),(8,16),(5,19))]:
            line([a,b],2.3)
    elif name=="file":
        line([(5,2),(14,2),(20,8),(20,22),(5,22),(5,2)])
        line([(14,2),(14,8),(20,8)])
        line([(8,13),(17,13)])
        line([(8,17),(16,17)])
    elif name=="wifi":
        arc((2,5,22,20),205,335,2.3)
        arc((6,10,18,21),205,335,2.3)
        ellipse((10.5,18,13.5,21),1,True)
    elif name=="image":
        rect((3,4,21,20),radius=2)
        ellipse((7,7,10,10),1,True)
        line([(5,17),(10,12),(13,15),(16,11),(20,16)])
    elif name=="eye":
        line([(2,12),(7,7),(12,6),(17,7),(22,12),(17,17),(12,18),(7,17),(2,12)])
        ellipse((9,9,15,15),1.8)
    elif name=="power":
        arc((4,4,20,21),-50,230,2.3)
        line([(12,2),(12,13)],2.3)
    elif name=="refresh":
        arc((4,4,20,20),200,20,2.3)
        arc((4,4,20,20),20,200,2.3)
        line([(19,5),(21,11),(15,10)])
        line([(5,19),(3,13),(9,14)])
    elif name=="play":
        d.polygon([pt((7,4)),pt((20,12)),pt((7,20))],fill=color)
    elif name=="keyboard":
        rect((2,6,22,19),radius=2)
        for y in (10,13):
            for x in (6,10,14,18):
                d.rectangle(pt((x,y))+pt((x+1,y+1)),fill=color)
        line([(8,16),(16,16)],1.4)
    elif name=="download":
        line([(12,3),(12,15)],2.3)
        line([(7,10),(12,15),(17,10)],2.3)
        line([(4,18),(4,21),(20,21),(20,18)])
    elif name=="directory":
        line([(2,8),(2,20),(22,20),(22,7),(11,7),(9,4),(2,4),(2,8)])
    elif name=="save":
        rect((4,3,20,21),radius=2)
        rect((8,3,16,9),1)
        rect((8,14,16,21),1)
    elif name=="ok":
        line([(4,12),(10,18),(20,6)],2.6)
    else:
        raise ValueError(name)
    return image.resize((24,24),Image.Resampling.LANCZOS)


def emit_image(name: str, image: Image.Image) -> str:
    width,height=image.size
    raw=image.convert("RGBA").tobytes()
    # LV_COLOR_FORMAT_ARGB8888 on little-endian x86 uses BGRA byte order.
    packed=bytearray()
    for i in range(0,len(raw),4):
        packed.extend((raw[i+2],raw[i+1],raw[i],raw[i+3]))
    rows=[]
    for i in range(0,len(packed),32):
        rows.append("    "+", ".join(f"0x{n:02x}" for n in packed[i:i+32])+",")
    return f"""static const uint8_t pix_{name}[] = {{
{chr(10).join(rows)}
}};
const lv_image_dsc_t redeti_{name} = {{
    .header.magic = LV_IMAGE_HEADER_MAGIC,
    .header.cf = LV_COLOR_FORMAT_ARGB8888,
    .header.flags = 0,
    .header.w = {width},
    .header.h = {height},
    .header.stride = {width*4},
    .data_size = sizeof(pix_{name}),
    .data = pix_{name},
}};
"""


def generate(dest: Path) -> None:
    chunks=["/* RedeTI assets; notebook supplied by user, icons generated offline. */",
            "#include <lvgl/lvgl.h>"]
    # The supplied, transparent notebook is stored in Git (not downloaded).
    hero_source=Path(__file__).resolve().parent / "assets/source/hero-laptop-panel.png"
    with Image.open(hero_source) as original:
        if original.size != (380,197) or original.format != "PNG":
            raise ValueError("Expected committed 380x197 hero-laptop-panel.png")
        hero=original.convert("RGBA")  # Also supports optimized PNG palette + tRNS.
    chunks.append(emit_image("hero_laptop",hero))
    for name in ICONS:
        chunks.append(emit_image("icon_"+name,icon(name)))
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text("\n".join(chunks),encoding="utf-8")


if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: premium_assets.py OUTPUT_C")
    generate(Path(sys.argv[1]))
