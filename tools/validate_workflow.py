"""Static checks for the H3 character sheet workflows.

    python tools/validate_workflow.py <ENG.json> <KOR.json> README.md

Exit code 1 on any failure. No ComfyUI needed.
"""
import json
import re
import sys

FORBIDDEN = ["팥빙수", "흰 발목 양말", "adult Korean man", "2x3 contact-sheet", "adult woman", "photorealistic studio photography", "tirgger", "turbo_4step", "ethnicity", "comfyui-workflow-encrypt"]
NOTE_ONLY_DIFF = {"MarkdownNote"}
TRANSLATION_PROMPT_NODES = {128, 137}  # KOR / ENG legitimately differ here

errors = []


def err(msg):
    errors.append(msg)


def load(path):
    return json.load(open(path, encoding="utf-8"))


def check_links(d, label):
    nodes = {n["id"]: n for n in d["nodes"]}
    links = {}
    for l in d["links"]:
        if l[0] in links:
            err(f"{label}: duplicate link id {l[0]}")
        links[l[0]] = l
    for lid, (_, src, ss, dst, ds, _t) in links.items():
        if src not in nodes or dst not in nodes:
            err(f"{label}: link {lid} references missing node"); continue
        if nodes[dst]["inputs"][ds].get("link") != lid:
            err(f"{label}: link {lid} not registered on target input")
        if lid not in (nodes[src]["outputs"][ss].get("links") or []):
            err(f"{label}: link {lid} not registered on source output")
    for n in d["nodes"]:
        for inp in n.get("inputs", []):
            if inp.get("link") is not None and inp["link"] not in links:
                err(f"{label}: node {n['id']} input {inp['name']} dangling link {inp['link']}")
        for o in n.get("outputs", []):
            for l in (o.get("links") or []):
                if l not in links or links[l][1] != n["id"]:
                    err(f"{label}: node {n['id']} output has dangling link {l}")
    for sg in d.get("definitions", {}).get("subgraphs", []):
        sn = {n["id"]: n for n in sg["nodes"]}
        sl = {l["id"]: l for l in sg["links"]}
        for l in sg["links"]:
            if l["origin_id"] != -10 and l["origin_id"] not in sn:
                err(f"{label}: subgraph link {l['id']} bad origin")
            if l["target_id"] != -20:
                if l["target_id"] not in sn:
                    err(f"{label}: subgraph link {l['id']} bad target")
                elif sn[l["target_id"]]["inputs"][l["target_slot"]].get("link") != l["id"]:
                    err(f"{label}: subgraph link {l['id']} not registered on target")
        for inp in sg["inputs"]:
            for x in inp.get("linkIds", []):
                if x not in sl or sl[x]["origin_id"] != -10:
                    err(f"{label}: subgraph input {inp['name']} bad linkId {x}")
        for n in sg["nodes"]:
            for inp in n.get("inputs", []):
                if inp.get("link") is not None and inp["link"] not in sl:
                    err(f"{label}: subgraph node {n['id']} dangling link {inp['link']}")


def all_nodes(d):
    out = list(d["nodes"])
    for sg in d.get("definitions", {}).get("subgraphs", []):
        out += sg["nodes"]
    return out


def check_named(d, label):
    for n in all_nodes(d):
        nm = n.get("widgets_values_named")
        if nm is None:
            continue
        if list(nm.values()) != n.get("widgets_values"):
            err(f"{label}: node {n['id']} {n['type']} widgets_values_named differs from widgets_values")


def check_forbidden(d, label):
    # notes may legitimately quote example text, so only functional nodes are scanned
    text = json.dumps([n for n in all_nodes(d) if n["type"] != "MarkdownNote"], ensure_ascii=False)
    for bad in FORBIDDEN:
        if bad in text:
            err(f"{label}: forbidden leftover text {bad!r}")


def check_parity(e, k):
    en = {n["id"]: n for n in e["nodes"]}
    kn = {n["id"]: n for n in k["nodes"]}
    if set(en) != set(kn):
        err(f"parity: node id sets differ {sorted(set(en) ^ set(kn))}")
    for i in sorted(set(en) & set(kn)):
        a, b = en[i], kn[i]
        if a["type"] != b["type"]:
            err(f"parity: node {i} type differs")
        if a.get("mode", 0) != b.get("mode", 0):
            err(f"parity: node {i} mode differs")
        if [x.get("link") for x in a.get("inputs", [])] != [x.get("link") for x in b.get("inputs", [])]:
            err(f"parity: node {i} input links differ")
        if a["type"] not in NOTE_ONLY_DIFF and i not in TRANSLATION_PROMPT_NODES and a.get("widgets_values") != b.get("widgets_values"):
            err(f"parity: node {i} {a['type']} widget values differ")
    if sorted(map(tuple, e["links"])) != sorted(map(tuple, k["links"])):
        err("parity: top-level link tables differ")
    se, sk = e["definitions"]["subgraphs"][0], k["definitions"]["subgraphs"][0]
    if [(n["type"], n.get("mode"), n.get("widgets_values")) for n in se["nodes"]] != [(n["type"], n.get("mode"), n.get("widgets_values")) for n in sk["nodes"]]:
        err("parity: subgraph nodes differ")
    if se["links"] != sk["links"]:
        err("parity: subgraph links differ")


def check_recipe(d, label):
    nodes = {n["id"]: n for n in d["nodes"]}
    by_type = {}
    for n in d["nodes"]:
        by_type.setdefault(n["type"], []).append(n)
    ks = by_type.get("KSamplerSelect", [])
    if not ks or ks[0]["widgets_values"][0] != "euler":
        err(f"{label}: KSamplerSelect must be euler for PDD")
    pdd = by_type.get("MiniMaxH3PDDAccApply", [])
    if not pdd or str(pdd[0]["widgets_values"][1]) != "8":
        err(f"{label}: PDD Acc must run 8 steps")
    shift = by_type.get("MiniMaxH3SigmaShift", [])
    if not shift or shift[0]["widgets_values"][:2] != [12, 3]:
        err(f"{label}: SigmaShift must be 12/3")
    if not by_type.get("BasicGuider"):
        err(f"{label}: BasicGuider missing")
    for s in by_type.get("SamplerCustomAdvanced", []):
        sig = next(i for i in s["inputs"] if i["name"] == "sigmas")
        src = next(l for l in d["links"] if l[0] == sig["link"])[1]
        if nodes[src]["type"] != "MiniMaxH3PDDAccApply":
            err(f"{label}: sampler {s['id']} sigmas must come from PDD Acc Apply")
    # Stage 2 dynamic picture numbering: every optional role line must pass through a RegexMatch gate
    if len(by_type.get("RegexMatch", [])) < 3:
        err(f"{label}: expected 3 RegexMatch picture gates for optional references")
    for n in by_type.get("ToobusyMiniMaxH3SemanticReference", []):
        if "<Picture" in n["widgets_values"][2]:
            err(f"{label}: SemanticReference {n['id']} role label carries a hard-coded picture number")


def check_models(d, readme, label):
    files = []
    for n in d["nodes"]:
        if n["type"] in ("UNETLoader", "CLIPLoader", "VAELoader", "MiniMaxH3PDDAccApply"):
            files.append(n["widgets_values"][0])
    note = next(n for n in d["nodes"] if n["type"] == "MarkdownNote" and "models" in n["widgets_values"][0].lower() and "safetensors" in n["widgets_values"][0])
    for f in files:
        if f not in readme:
            err(f"{label}: model file {f} not listed in README")
        if f not in note["widgets_values"][0]:
            err(f"{label}: model file {f} not listed in the in-canvas model note")


def main(eng, kor, readme_path):
    e, k = load(eng), load(kor)
    readme = open(readme_path, encoding="utf-8").read()
    for d, label in ((e, "ENG"), (k, "KOR")):
        check_links(d, label)
        check_named(d, label)
        check_forbidden(d, label)
        check_recipe(d, label)
        check_models(d, readme, label)
    check_parity(e, k)
    if re.search(r"[가-힣]", json.dumps([n for n in e["nodes"] if n["id"] != 69], ensure_ascii=False)):
        err("ENG: Hangul found outside the credits note")
    if errors:
        print("\n".join("FAIL " + x for x in errors))
        sys.exit(1)
    print(f"OK  {eng}  {kor}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
