"""Deterministic layout pass for the top-level graph.

    python tools/tidy_layout.py <workflow.json> [<out.json>]

Every node is packed inside its group in data-flow order (topological depth inside the
group, then the original top-to-bottom / left-to-right order) one row per depth level (wrapping
when a row is wider than the group), so links flow top to bottom. Groups keep their width, band (row) and
left-to-right order and are re-stacked so nothing overlaps. Collapsed nodes keep their
collapsed state. Node sizes, links and widgets are untouched, so the result is
functionally identical.
"""
import json
import sys

PAD_SIDE, PAD_TOP, PAD_BOTTOM = 40, 80, 40
GAP_X, GAP_Y, TITLE_H, GUTTER = 40, 40, 30, 80
BAND_TOL = 200


def eff_size(n):
    w, h = n["size"]
    if n.get("flags", {}).get("collapsed"):
        return min(w, max(160, 7.5 * len(n.get("title") or n["type"]) + 60)), 0
    return w, h


def inside(n, b):
    x, y = n["pos"]
    return b[0] <= x <= b[0] + b[2] and b[1] - TITLE_H <= y <= b[1] + b[3]


def tidy(d):
    preds = {}
    for _, src, _, dst, _, _ in d["links"]:
        preds.setdefault(dst, set()).add(src)
    groups = sorted(d["groups"], key=lambda g: (g["bounding"][1], g["bounding"][0]))
    members = {g["id"]: [n for n in d["nodes"] if inside(n, g["bounding"])] for g in groups}
    placed = set()

    for g in groups:
        ms = [n for n in members[g["id"]] if n["id"] not in placed]
        members[g["id"]] = ms
        placed.update(n["id"] for n in ms)
        ids = {n["id"] for n in ms}
        depth = {}

        def dep(i, stack=()):
            if i in depth:
                return depth[i]
            if i in stack:
                return 0
            ps = [p for p in preds.get(i, ()) if p in ids]
            depth[i] = 1 + max((dep(p, stack + (i,)) for p in ps), default=-1)
            return depth[i]

        for n in ms:
            dep(n["id"])
        ms.sort(key=lambda n: (depth[n["id"]], n["pos"][0], n["pos"][1]))
        b = g["bounding"]
        widest = max((eff_size(n)[0] for n in ms), default=0)
        if widest + 2 * PAD_SIDE > b[2]:
            b[2] = int(widest + 2 * PAD_SIDE)
        x0, right = b[0] + PAD_SIDE, b[0] + b[2] - PAD_SIDE
        y_title = b[1] + PAD_TOP
        cur_depth, x, row_h = None, x0, 0
        for n in ms:
            w, h = eff_size(n)
            new_row = depth[n["id"]] != cur_depth or (x > x0 and x + w > right)
            if new_row and (cur_depth is not None):
                y_title += row_h + TITLE_H + GAP_Y
                x, row_h = x0, 0
            cur_depth = depth[n["id"]]
            n["pos"] = [int(x), int(y_title + TITLE_H)]
            x += w + GAP_X
            row_h = max(row_h, h)
        if ms:
            b[3] = int(y_title + TITLE_H + row_h + PAD_BOTTOM - b[1])

    bands = []
    for g in groups:
        for band in bands:
            if abs(band[0] - g["bounding"][1]) <= BAND_TOL:
                band[1].append(g)
                break
        else:
            bands.append([g["bounding"][1], [g]])
    y = 0
    for _, gs in sorted(bands, key=lambda b: b[0]):
        gs.sort(key=lambda g: g["bounding"][0])
        x, bottom = 0, y
        for g in gs:
            b = g["bounding"]
            dx, dy = x - b[0], y - b[1]
            for n in members[g["id"]]:
                n["pos"] = [n["pos"][0] + dx, n["pos"][1] + dy]
            b[0], b[1] = x, y
            x += b[2] + GUTTER
            bottom = max(bottom, y + b[3])
        y = bottom + GUTTER
    d["extra"]["ds"] = {"scale": 0.2, "offset": [80, 80]}
    return d


if __name__ == "__main__":
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else src
    d = json.load(open(src, encoding="utf-8"))
    tidy(d)
    json.dump(d, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("tidied", dst)
