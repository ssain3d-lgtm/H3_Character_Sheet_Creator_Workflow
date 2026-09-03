"""Generate the KOR workflow from the canonical ENG workflow + tools/kor_overlay.json.

    python tools/build_kor.py <ENG.json> <KOR.json>

The overlay holds only UI text (node titles, markdown notes, group titles, the two
Korean translation-instruction prompts and the workflow id). Everything functional
comes from the ENG file, so the two files can never drift apart.
"""
import json
import os
import sys

HERE = os.path.dirname(__file__)


def build(src, dst, overlay_path=os.path.join(HERE, "kor_overlay.json")):
    d = json.load(open(src, encoding="utf-8"))
    ov = json.load(open(overlay_path, encoding="utf-8"))
    d["id"] = ov["workflow_id"]
    sg = d["definitions"]["subgraphs"][0]
    for n in d["nodes"] + sg["nodes"]:
        key = str(n["id"])
        if key in ov["titles"]:
            n["title"] = ov["titles"][key]
        if n["type"] == "MarkdownNote" and key in ov["notes"]:
            n["widgets_values"][0] = ov["notes"][key]
            if "widgets_values_named" in n:
                n["widgets_values_named"]["text"] = ov["notes"][key]
        if key in ov["widgets"]:
            for idx, val in ov["widgets"][key].items():
                n["widgets_values"][int(idx)] = val
            if "widgets_values_named" in n:
                n["widgets_values_named"] = dict(zip(n["widgets_values_named"].keys(), n["widgets_values"]))
    for grp in d["groups"]:
        grp["title"] = ov["groups"].get(grp["title"], grp["title"])
    sg["name"] = ov.get("subgraph_name", sg["name"])
    for inp in sg["inputs"]:
        if inp.get("label") in ov.get("labels", {}):
            inp["label"] = ov["labels"][inp["label"]]
    for n in d["nodes"]:
        for inp in n.get("inputs", []):
            if inp.get("label") in ov.get("labels", {}):
                inp["label"] = ov["labels"][inp["label"]]
    d["extra"]["workflow_name"] = d["extra"]["workflow_name"].replace("_ENG", "_KOR")
    if "comfyui_mcp" in d["extra"]:
        d["extra"]["comfyui_mcp"]["workflow_path"] = d["extra"]["comfyui_mcp"]["workflow_path"].replace("_ENG", "_KOR")
    json.dump(d, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("wrote", dst)


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
