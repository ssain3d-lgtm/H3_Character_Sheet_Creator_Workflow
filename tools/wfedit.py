"""Small helper for editing ComfyUI workflow JSON (top-level graph only)."""
import copy

WIDGET_NAMES = {
    "PrimitiveBoolean": ["value"],
    "PrimitiveString": ["value"],
    "PrimitiveStringMultiline": ["value"],
    "ComfySwitchNode": ["switch"],
    "StringConcatenate": ["string_a", "string_b", "delimiter"],
    "RegexMatch": ["string", "regex_pattern", "case_insensitive", "multiline", "dotall"],
    "MarkdownNote": ["text"],
}


class Graph:
    def __init__(self, d):
        self.d = d
        self.nodes = {n["id"]: n for n in d["nodes"]}
        self.links = {l[0]: l for l in d["links"]}

    def node(self, i):
        return self.nodes[i]

    def _next_node_id(self):
        self.d["last_node_id"] = max(self.d["last_node_id"], max(self.nodes)) + 1
        return self.d["last_node_id"]

    def _next_link_id(self):
        sg_max = max([l["id"] for sg in self.d.get("definitions", {}).get("subgraphs", []) for l in sg["links"]] or [0])
        self.d["last_link_id"] = max(self.d["last_link_id"], max(self.links), sg_max) + 1
        return self.d["last_link_id"]

    def add_node(self, type_, title, pos, size, widgets=None, inputs=(), outputs=(), mode=0,
                 properties=None, color=None, bgcolor=None, node_id=None):
        nid = node_id or self._next_node_id()
        assert nid not in self.nodes
        n = {
            "id": nid, "type": type_, "pos": list(pos), "size": list(size), "flags": {}, "order": 0,
            "mode": mode,
            "inputs": [dict(i) for i in inputs],
            "outputs": [{"name": o[0], "type": o[1], "links": []} for o in outputs],
            "title": title,
            "properties": properties or {"cnr_id": "comfy-core", "ver": "0.34.0", "Node name for S&R": type_},
        }
        if widgets is not None:
            n["widgets_values"] = list(widgets)
            names = WIDGET_NAMES.get(type_)
            if names and len(names) == len(widgets):
                n["widgets_values_named"] = dict(zip(names, widgets))
        if color:
            n["color"] = color
        if bgcolor:
            n["bgcolor"] = bgcolor
        self.d["nodes"].append(n)
        self.nodes[nid] = n
        return nid

    def link(self, src, src_slot, dst, dst_input, type_):
        """Connect src:slot -> dst.input_name. Replaces an existing link on that input."""
        dn = self.nodes[dst]
        idx = next(i for i, inp in enumerate(dn["inputs"]) if inp["name"] == dst_input)
        old = dn["inputs"][idx].get("link")
        if old is not None:
            self.unlink(old)
        lid = self._next_link_id()
        self.d["links"].append([lid, src, src_slot, dst, idx, type_])
        self.links[lid] = self.d["links"][-1]
        dn["inputs"][idx]["link"] = lid
        out = self.nodes[src]["outputs"][src_slot]
        out["links"] = (out.get("links") or []) + [lid]
        return lid

    def unlink(self, lid):
        l = self.links.pop(lid)
        self.d["links"] = [x for x in self.d["links"] if x[0] != lid]
        _, src, ss, dst, ds, _ = l
        out = self.nodes[src]["outputs"][ss]
        out["links"] = [x for x in (out.get("links") or []) if x != lid] or None
        self.nodes[dst]["inputs"][ds]["link"] = None

    def add_input(self, nid, name, type_, widget=True):
        n = self.nodes[nid]
        assert not any(i["name"] == name for i in n["inputs"])
        entry = {"name": name, "type": type_, "link": None}
        if widget:
            entry["widget"] = {"name": name}
        n["inputs"].append(entry)

    def group(self, prefix):
        return next(g for g in self.d["groups"] if g["title"].startswith(prefix))


def sync_named(d):
    """Make widgets_values_named agree with widgets_values everywhere (top level + subgraphs)."""
    all_nodes = list(d["nodes"])
    for sg in d.get("definitions", {}).get("subgraphs", []):
        all_nodes += sg["nodes"]
    for n in all_nodes:
        nm = n.get("widgets_values_named")
        wv = n.get("widgets_values")
        if nm is None:
            continue
        if wv is None or len(nm) != len(wv):
            del n["widgets_values_named"]
            continue
        n["widgets_values_named"] = dict(zip(nm.keys(), wv))


def replace_once(s, old, new):
    assert s.count(old) == 1, (s.count(old), old[:80])
    return s.replace(old, new)
