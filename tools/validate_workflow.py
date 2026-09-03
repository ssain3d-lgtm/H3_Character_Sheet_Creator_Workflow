"""Static checks for the H3 character sheet workflows (no ComfyUI needed).

    python tools/validate_workflow.py [--toobusy PATH] [ENG.json KOR.json ...]

With no file arguments every "*_ENG.json" in the repository root is validated together
with its "*_KOR.json" twin. --toobusy points at a checkout of nicekriss/toobusy so the
Stage 2 role simulation runs the real ToobusyMiniMaxH3SemanticReference class; without
it a faithful emulation is used. Exit code 1 on any failure.
"""
import glob
import importlib.util
import itertools
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOBUSY_COMMIT = "bdbed64499d9351cf400c520e8824e33ad9b9702"
FORBIDDEN = ["팥빙수", "흰 발목 양말", "adult Korean man", "2x3 contact-sheet", "adult woman", "photorealistic studio photography",
             "tirgger", "turbo_4step", "ethnicity", "comfyui-workflow-encrypt", "pose_or_extra_ref"]
TRANSLATION_PROMPT_NODES = {128, 137}
WIDGET_NAMES = {
    "PrimitiveBoolean": ["value"], "PrimitiveString": ["value"], "PrimitiveStringMultiline": ["value"],
    "ComfySwitchNode": ["switch"], "StringConcatenate": ["string_a", "string_b", "delimiter"],
    "RegexMatch": ["string", "regex_pattern", "case_insensitive", "multiline", "dotall"],
    "ToobusyMiniMaxH3SemanticReference": ["enabled", "routing", "role_label", "analysis"],
}

errors = []


def err(msg):
    errors.append(msg)


def load(path):
    return json.load(open(path, encoding="utf-8"))


def all_nodes(d):
    out = list(d["nodes"])
    for sg in d.get("definitions", {}).get("subgraphs", []):
        out += sg["nodes"]
    return out


# ----------------------------------------------------------------------------- structure
def check_links(d, label):
    ids = [n["id"] for n in d["nodes"]]
    if len(ids) != len(set(ids)):
        err(f"{label}: duplicate node ids")
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
        sids = [n["id"] for n in sg["nodes"]]
        if len(sids) != len(set(sids)):
            err(f"{label}: duplicate subgraph node ids")
        lids = [l["id"] for l in sg["links"]]
        if len(lids) != len(set(lids)):
            err(f"{label}: duplicate subgraph link ids")
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
        # interface: the instance node must expose exactly the subgraph's inputs / outputs, in order
        inst = [n for n in d["nodes"] if n["type"] == sg["id"]]
        if len(inst) != 1:
            err(f"{label}: expected exactly one instance of subgraph {sg['id']}"); continue
        inst = inst[0]
        sg_names = [i["name"] for i in sg["inputs"]]
        inst_names = [i["name"] for i in inst["inputs"]]
        widget_names = set(inst.get("widgets_values_named", {}))
        if [n for n in sg_names if n in inst_names] != inst_names or not (set(sg_names) - set(inst_names)) <= widget_names:
            err(f"{label}: subgraph instance inputs differ from subgraph interface")
        if [o["name"] for o in inst["outputs"]] != [o["name"] for o in sg["outputs"]]:
            err(f"{label}: subgraph instance outputs differ from subgraph interface")
        for idx, inp in enumerate(sg["inputs"]):
            for x in inp["linkIds"]:
                if sl[x]["origin_slot"] != idx:
                    err(f"{label}: subgraph input {inp['name']} link {x} has wrong origin_slot")


def check_named(d, label):
    for n in all_nodes(d):
        nm = n.get("widgets_values_named")
        if nm is None:
            continue
        if list(nm.values()) != n.get("widgets_values"):
            err(f"{label}: node {n['id']} {n['type']} widgets_values_named differs from widgets_values")


def check_forbidden(d, label):
    text = json.dumps([n for n in all_nodes(d) if n["type"] != "MarkdownNote"], ensure_ascii=False)
    text += json.dumps(d["definitions"]["subgraphs"][0]["inputs"], ensure_ascii=False)
    for bad in FORBIDDEN:
        if bad in text:
            err(f"{label}: forbidden leftover text {bad!r}")
    if "comfyui_mcp" in d.get("extra", {}):
        err(f"{label}: extra.comfyui_mcp must not be shipped")
    for n in all_nodes(d):
        if n["type"].startswith("ToobusyMiniMaxH3") and n["properties"].get("ver") != TOOBUSY_COMMIT:
            err(f"{label}: node {n['id']} toobusy ver must be pinned to {TOOBUSY_COMMIT[:8]}")


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
        if a["type"] != "MarkdownNote" and i not in TRANSLATION_PROMPT_NODES and a.get("widgets_values") != b.get("widgets_values"):
            err(f"parity: node {i} {a['type']} widget values differ")
        if ("widgets_values_named" in a) != ("widgets_values_named" in b) or list(a.get("widgets_values_named", {})) != list(b.get("widgets_values_named", {})):
            err(f"parity: node {i} widgets_values_named keys differ")
    if sorted(map(tuple, e["links"])) != sorted(map(tuple, k["links"])):
        err("parity: top-level link tables differ")
    se, sk = e["definitions"]["subgraphs"][0], k["definitions"]["subgraphs"][0]
    if [(n["type"], n.get("mode"), n.get("widgets_values")) for n in se["nodes"]] != [(n["type"], n.get("mode"), n.get("widgets_values")) for n in sk["nodes"]]:
        err("parity: subgraph nodes differ")
    if se["links"] != sk["links"] or [i["name"] for i in se["inputs"]] != [i["name"] for i in sk["inputs"]]:
        err("parity: subgraph links / interface differ")


# ----------------------------------------------------------------------------- recipe
def src_of(d, node, input_name):
    nodes = {n["id"]: n for n in d["nodes"]}
    inp = next((i for i in node["inputs"] if i["name"] == input_name), None)
    if inp is None or inp.get("link") is None:
        return None, None
    l = next(x for x in d["links"] if x[0] == inp["link"])
    return nodes[l[1]], l[2]


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
    pdd = pdd[0] if pdd else None
    shift = by_type.get("MiniMaxH3SigmaShift", [])
    if not shift or shift[0]["widgets_values"][:2] != [12, 3]:
        err(f"{label}: SigmaShift must be 12/3")
    if not by_type.get("BasicGuider"):
        err(f"{label}: BasicGuider missing")
    # sigmas selector: default path PDD, fallback BasicScheduler; both consumers share it
    samplers = by_type.get("SamplerCustomAdvanced", [])
    inst = [n for n in d["nodes"] if n["type"] == d["definitions"]["subgraphs"][0]["id"]][0]
    sel = set()
    for s in samplers + [inst]:
        n, _ = src_of(d, s, "sigmas")
        if n is None or n["type"] != "ComfySwitchNode":
            err(f"{label}: sigmas of node {s['id']} must come from the Sigmas Select switch"); continue
        sel.add(n["id"])
    if len(sel) != 1:
        err(f"{label}: Stage 1 sampler and Stage 2 subgraph must share one Sigmas Select switch")
    else:
        sw = nodes[next(iter(sel))]
        off, _ = src_of(d, sw, "on_false")
        on, _ = src_of(d, sw, "on_true")
        ctl, _ = src_of(d, sw, "switch")
        if off is None or off["type"] != "MiniMaxH3PDDAccApply":
            err(f"{label}: Sigmas Select default (OFF) path must be PDD Acc Apply")
        if on is None or on["type"] != "BasicScheduler" or on.get("mode", 0) != 0:
            err(f"{label}: Sigmas Select ON path must be an active BasicScheduler")
        if ctl is None or ctl["type"] != "PrimitiveBoolean" or ctl["widgets_values"][0] is not False:
            err(f"{label}: Sigmas Source switch must default to OFF (PDD)")
        att = by_type.get("ModelAttentionBackend", [])[0]
        msw, _ = src_of(d, att, "model")
        if msw is None or msw["type"] != "ComfySwitchNode":
            err(f"{label}: attention backend model must come from the Model Select switch")
        else:
            moff, _ = src_of(d, msw, "on_false")
            mon, _ = src_of(d, msw, "on_true")
            mctl, _ = src_of(d, msw, "switch")
            if moff is None or moff["type"] != "MiniMaxH3PDDAccApply" or mon is None or mon["type"] != "MiniMaxH3SigmaShift":
                err(f"{label}: Model Select must choose between PDD-patched and plain (SigmaShift) model")
            if mctl is None or mctl["id"] != ctl["id"]:
                err(f"{label}: Model Select must be driven by the same Sigmas Source switch")
    # Stage 2 subgraph recipe
    sg = d["definitions"]["subgraphs"][0]
    sn = {n["id"]: n for n in sg["nodes"]}
    sl = {l["id"]: l for l in sg["links"]}
    in_idx = {i["name"]: idx for idx, i in enumerate(sg["inputs"])}
    ref = [n for n in sg["nodes"] if n["type"] == "MiniMaxH3ReferenceToVideo"]
    smp = [n for n in sg["nodes"] if n["type"] == "SamplerCustomAdvanced"]
    if len(ref) != 1 or len(smp) != 1:
        err(f"{label}: Stage 2 subgraph must hold one H3 reference node and one sampler"); return
    ref, smp = ref[0], smp[0]

    def sg_src(node, name):
        inp = next(i for i in node["inputs"] if i["name"] == name)
        if inp.get("link") is None:
            return None
        return sl[inp["link"]]
    l = sg_src(smp, "sigmas")
    if l is None or l["origin_id"] != -10 or l["origin_slot"] != in_idx.get("sigmas"):
        err(f"{label}: Stage 2 sampler sigmas must come from the subgraph 'sigmas' input")
    l = sg_src(smp, "guider")
    if l is None or sn[l["origin_id"]]["type"] != "BasicGuider":
        err(f"{label}: Stage 2 sampler must use BasicGuider")
    guider = sn[l["origin_id"]] if l else None
    if guider:
        lc = sg_src(guider, "conditioning")
        if lc is None or lc["origin_id"] != ref["id"]:
            err(f"{label}: Stage 2 guider must be conditioned by the H3 reference node")
    l = sg_src(smp, "noise")
    if l is None or sn[l["origin_id"]]["widgets_values"][1] != "fixed":
        err(f"{label}: Stage 2 noise must be a fixed seed")
    l = sg_src(ref, "ref_images.ref_image_0")
    if l is None or l["origin_id"] != -10 or l["origin_slot"] != in_idx.get("image"):
        err(f"{label}: Stage 2 Picture 1 must be the Stage 1 sheet (subgraph 'image' input)")
    for k in (1, 2, 3):
        l = sg_src(ref, f"ref_images.ref_image_{k}")
        if l is None or l["origin_id"] != -10 or l["origin_slot"] != in_idx.get(f"ref_images.ref_image_{k}"):
            err(f"{label}: Stage 2 ref_image_{k} must map to the matching subgraph input")
    for inp in ref["inputs"]:
        if inp["name"].startswith("ref_images.ref_image_") and inp["name"][-1] not in "0123" and inp.get("link") is not None:
            err(f"{label}: unexpected extra Stage 2 reference {inp['name']}")
    # optional references must be routed 'auto'
    for n in by_type.get("ToobusyMiniMaxH3SemanticReference", []):
        if n["widgets_values"][1] != "auto":
            err(f"{label}: SemanticReference {n['id']} routing must be 'auto'")
        if "<Picture" in n["widgets_values"][2]:
            err(f"{label}: SemanticReference {n['id']} role label carries a hard-coded picture number")


# ----------------------------------------------------------------------------- Stage 2 role simulation
def load_toobusy_class(path):
    if not path:
        return None
    p = os.path.join(path, "minimax_h3_semantic_reference_node", "minimax_h3_semantic_reference.py")
    spec = importlib.util.spec_from_file_location("toobusy_semref", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.ToobusyMiniMaxH3SemanticReference


class EmulatedSemanticReference:
    """Mirror of toobusy 0.4.10 ToobusyMiniMaxH3SemanticReference.select()."""

    @staticmethod
    def _parse(analysis):
        text = (analysis or "").strip()
        m = re.search(r"VISUAL_REFERENCE\s*:\s*(YES|NO)", text, flags=re.IGNORECASE)
        safe = bool(m and m.group(1).upper() == "YES")
        dm = re.search(r"SEMANTIC_DESCRIPTION\s*:\s*(.+)", text, flags=re.IGNORECASE | re.DOTALL)
        desc = dm.group(1).strip() if dm else re.sub(r"^\s*VISUAL_REFERENCE\s*:\s*(?:YES|NO)\s*$", "", text, flags=re.IGNORECASE | re.MULTILINE).strip()
        return safe, desc

    def select(self, enabled, routing, role_label, analysis=None, image=None):
        if not enabled or analysis is None:
            return (None, "")
        safe, desc = self._parse(analysis)
        use = routing == "visual_reference" or (routing == "auto" and safe)
        label = role_label.strip()
        role = f"{label}: {desc}" if label and desc else desc
        return (image if use else None, role)


class Sim:
    def __init__(self, d, semref_cls, bool_overrides, text_stubs):
        self.d = d
        self.nodes = {n["id"]: n for n in d["nodes"]}
        self.links = {l[0]: l for l in d["links"]}
        self.semref = semref_cls() if semref_cls else EmulatedSemanticReference()
        self.bools = bool_overrides
        self.stubs = text_stubs
        self.cache = {}

    def widget(self, n, name):
        names = WIDGET_NAMES.get(n["type"])
        if "widgets_values_named" in n and name in n["widgets_values_named"]:
            return n["widgets_values_named"][name]
        return n["widgets_values"][names.index(name)]

    def inp(self, n, name):
        i = next((x for x in n["inputs"] if x["name"] == name), None)
        if i is None or i.get("link") is None:
            return self.widget(n, name)
        l = self.links[i["link"]]
        return self.out(l[1], l[2])

    def out(self, nid, slot):
        key = (nid, slot)
        if key in self.cache:
            return self.cache[key]
        n = self.nodes[nid]
        t = n["type"]
        if t == "PrimitiveBoolean":
            v = self.bools.get(nid, n["widgets_values"][0])
        elif t in ("PrimitiveString", "PrimitiveStringMultiline"):
            v = n["widgets_values"][0]
        elif t == "ComfySwitchNode":
            v = self.inp(n, "on_true") if self.inp(n, "switch") else self.inp(n, "on_false")
        elif t == "RegexMatch":
            flags = (re.IGNORECASE if self.widget(n, "case_insensitive") else 0) | (re.MULTILINE if self.widget(n, "multiline") else 0) | (re.DOTALL if self.widget(n, "dotall") else 0)
            v = re.search(self.widget(n, "regex_pattern"), self.inp(n, "string"), flags) is not None
        elif t == "StringConcatenate":
            v = self.inp(n, "string_a") + self.widget(n, "delimiter") + self.inp(n, "string_b")
        elif t == "TextGenerate":
            v = self.stubs.get(nid, "")
        elif t == "LoadImage":
            v = f"IMG{nid}"
        elif t == "ToobusyMiniMaxH3SemanticReference":
            res = self.semref.select(self.inp(n, "enabled"), n["widgets_values"][1], n["widgets_values"][2], analysis=self.inp(n, "analysis"), image=self.inp(n, "image"))
            v = res[slot]
        else:
            raise RuntimeError(f"simulation cannot evaluate node {nid} {t}")
        self.cache[key] = v
        return v


def check_stage2_roles(d, label, semref_cls):
    nodes = {n["id"]: n for n in d["nodes"]}
    inst = [n for n in d["nodes"] if n["type"] == d["definitions"]["subgraphs"][0]["id"]][0]
    sem = sorted([n for n in d["nodes"] if n["type"] == "ToobusyMiniMaxH3SemanticReference"], key=lambda n: n["id"])
    if len(sem) != 3:
        err(f"{label}: expected 3 SemanticReference gates"); return
    slots = []
    for k, s in enumerate(sem, start=1):
        en, _ = src_of(d, s, "enabled")
        an, _ = src_of(d, s, "analysis")
        ref_src, _ = src_of(d, inst, f"ref_images.ref_image_{k}")
        if ref_src is None or ref_src["id"] != s["id"]:
            err(f"{label}: Stage 2 ref_image_{k} must be fed by SemanticReference {s['id']}")
        slots.append((s, en["id"], an["id"]))
    # the final role text is the output of the last 'Role Join' concat feeding the Stage 2 prompt chain
    # the role block is string_b of the concat whose delimiter introduces "Enabled reference roles"
    final = [n for n in d["nodes"] if n["type"] == "StringConcatenate" and "Enabled reference roles" in n["widgets_values"][2]]
    if len(final) != 1:
        err(f"{label}: cannot find the 'Enabled reference roles' concat"); return
    join, _ = src_of(d, final[0], "string_b")
    if join is None:
        err(f"{label}: role block is not linked"); return
    states = ("off", "safe", "rejected")
    n_cases = 0
    for combo in itertools.product(states, repeat=3):
        bools, stubs = {}, {}
        for (s, en_id, an_id), st in zip(slots, combo):
            bools[en_id] = st != "off"
            stubs[an_id] = ("VISUAL_REFERENCE: YES" if st == "safe" else "VISUAL_REFERENCE: NO") + f"\nSEMANTIC_DESCRIPTION: desc-{an_id}"
        sim = Sim(d, semref_cls, bools, stubs)
        attached = []
        for k in (1, 2, 3):
            i = next(x for x in inst["inputs"] if x["name"] == f"ref_images.ref_image_{k}")
            l = sim.links[i["link"]]
            attached.append(sim.out(l[1], l[2]) is not None)
        text = sim.out(join["id"], 0)
        # expected numbering: Picture 1 is the sheet, then attached optionals in slot order
        expected = {}
        num = 2
        for k, a in enumerate(attached):
            if a:
                expected[k] = num
                num += 1
        tags = [int(x) for x in re.findall(r"<Picture (\d+)>", text)]
        exp_tags = [1] + [expected[k] for k in range(3) if k in expected]
        if tags != exp_tags:
            err(f"{label}: combo {combo}: picture tags {tags} != expected {exp_tags}")
        for (s, en_id, an_id), st, k in zip(slots, combo, range(3)):
            desc = f"desc-{an_id}"
            if st == "off" and desc in text:
                err(f"{label}: combo {combo}: disabled slot {k + 1} leaked its description")
            if st != "off" and desc not in text:
                err(f"{label}: combo {combo}: enabled slot {k + 1} lost its description")
            if st == "rejected" and re.search(rf"<Picture \d+> = [^\n]*{desc}", text):
                err(f"{label}: combo {combo}: rejected slot {k + 1} still carries a picture tag")
        n_cases += 1
    return n_cases


# ----------------------------------------------------------------------------- models / docs
def check_models(d, readme, label):
    files = []
    for n in d["nodes"]:
        if n["type"] in ("UNETLoader", "CLIPLoader", "VAELoader", "MiniMaxH3PDDAccApply", "LoraLoaderModelOnly"):
            files.append(n["widgets_values"][0])
        if n["type"] == "LoraLoaderModelOnly" and not re.fullmatch(r"[\w.\-]+\.safetensors", n["widgets_values"][0]):
            err(f"{label}: LoRA file name {n['widgets_values'][0]!r} is not a plain .safetensors name")
    note = next(n for n in d["nodes"] if n["type"] == "MarkdownNote" and "models" in n["widgets_values"][0].lower() and "safetensors" in n["widgets_values"][0])
    for f in files:
        if f not in readme:
            err(f"{label}: model file {f} not listed in README")
        if f not in note["widgets_values"][0]:
            err(f"{label}: model file {f} not listed in the in-canvas model note")
    if TOOBUSY_COMMIT[:8] not in readme:
        err("README must record the pinned toobusy commit")


def check_archives():
    for f in glob.glob(os.path.join(ROOT, "old", "*.json")):
        if "comfyui_mcp" in load(f).get("extra", {}):
            err(f"old/{os.path.basename(f)}: extra.comfyui_mcp must be stripped")


def main(argv):
    toobusy = None
    if "--toobusy" in argv:
        i = argv.index("--toobusy")
        toobusy = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    semref_cls = load_toobusy_class(toobusy)
    pairs = []
    if argv:
        pairs = [(argv[i], argv[i + 1]) for i in range(0, len(argv), 2)]
    else:
        for e in sorted(glob.glob(os.path.join(ROOT, "*_ENG.json"))):
            k = e.replace("_ENG.json", "_KOR.json")
            if not os.path.exists(k):
                err(f"{os.path.basename(e)} has no KOR twin")
                continue
            pairs.append((e, k))
    if not pairs:
        err("no workflow pairs found")
    readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    for eng, kor in pairs:
        e, k = load(eng), load(kor)
        for d, label in ((e, "ENG"), (k, "KOR")):
            label = f"{os.path.basename(eng if label == 'ENG' else kor)}"
            check_links(d, label)
            check_named(d, label)
            check_forbidden(d, label)
            check_recipe(d, label)
            check_models(d, readme, label)
            cases = check_stage2_roles(d, label, semref_cls)
        check_parity(e, k)
        if re.search(r"[가-힣]", json.dumps([n for n in e["nodes"] if n["id"] != 69], ensure_ascii=False)):
            err(f"{os.path.basename(eng)}: Hangul found outside the credits note")
    check_archives()
    if errors:
        print("\n".join("FAIL " + x for x in errors))
        sys.exit(1)
    print(f"OK  {len(pairs)} pair(s), Stage 2 role simulation {cases} cases each, semantic reference = {'toobusy ' + TOOBUSY_COMMIT[:8] if semref_cls else 'emulated'}")


if __name__ == "__main__":
    main(sys.argv[1:])
