"""Render the top-level layout of a workflow JSON to a PNG (groups, nodes, links).

    python tools/render_layout.py <workflow.json> <out.png> [scale]
"""
import json
import sys

from PIL import Image, ImageDraw

TITLE_H = 30


def render(path, out, scale=0.22):
    d = json.load(open(path, encoding="utf-8"))
    nodes = {n["id"]: n for n in d["nodes"]}
    xs = [g["bounding"][0] + g["bounding"][2] for g in d["groups"]] + [n["pos"][0] + n["size"][0] for n in d["nodes"]]
    ys = [g["bounding"][1] + g["bounding"][3] for g in d["groups"]] + [n["pos"][1] + n["size"][1] for n in d["nodes"]]
    W, H = int((max(xs) + 100) * scale), int((max(ys) + 100) * scale)
    im = Image.new("RGB", (W, H), (28, 28, 30))
    dr = ImageDraw.Draw(im)
    s = lambda v: int(v * scale)
    for g in d["groups"]:
        x, y, w, h = g["bounding"]
        col = g.get("color", "#444")
        dr.rectangle([s(x), s(y), s(x + w), s(y + h)], outline=col, width=2)
        dr.text((s(x) + 4, s(y) + 3), g["title"][:60], fill=col)
    for l in d["links"]:
        a, b = nodes.get(l[1]), nodes.get(l[3])
        if not a or not b:
            continue
        ax, ay = a["pos"][0] + a["size"][0], a["pos"][1] + 10
        bx, by = b["pos"][0], b["pos"][1] + 10
        dr.line([s(ax), s(ay), s(bx), s(by)], fill=(90, 90, 110), width=1)
    for n in d["nodes"]:
        x, y = n["pos"]
        w, h = n["size"]
        if n.get("flags", {}).get("collapsed"):
            h = 0
        fill = (60, 60, 70) if n["type"] != "MarkdownNote" else (50, 60, 50)
        dr.rectangle([s(x), s(y - TITLE_H), s(x + w), s(y + h)], fill=fill, outline=(140, 140, 160))
        dr.text((s(x) + 2, s(y - TITLE_H) + 1), (n.get("title") or n["type"])[:40], fill=(230, 230, 230))
    im.save(out)
    print("rendered", out, im.size)


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 0.22)
