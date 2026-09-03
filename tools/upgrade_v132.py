"""Upgrade: v1.3.1 ENG workflow -> v1.3.2 ENG workflow (release hardening + wardrobe fixes).

    python tools/upgrade_v132.py "old/260903_H3_character_sheet(sain2d_modified)_v1.3.1_ENG.json" \
        "260903_H3_character_sheet(sain2d_modified)_v1.3.2_ENG.json"

The KOR file is then generated with tools/build_kor.py.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from wfedit import Graph, sync_named, replace_once  # noqa: E402

VERSION = "v1.3.2"
DATE = "2026-09-03"
TOOBUSY_COMMIT = "bdbed64499d9351cf400c520e8824e33ad9b9702"  # toobusy 0.4.10 (2026-09-01)

STR, IMG, BOOL, SIG, MODEL = "STRING", "IMAGE", "BOOLEAN", "SIGMAS", "MODEL"
EMPTY = 147  # existing "Empty Text" primitive

WARDROBE_PROMPT = (
    "Describe only the clothing in this image for another image model. The image is a clothing cut-out on a grey background; "
    "there may be no visible person. Output one paragraph that begins exactly with \"WARDROBE DESCRIPTION:\".\n"
    "List every garment from top to bottom with its type, colour, material, pattern, length and notable details (collar, tie, buttons, pleats, prints).\n"
    "Then state the footwear explicitly: socks (length and colour, or \"no socks visible\") and shoes (type and colour, or \"no shoes visible\"). "
    "If only one shoe or sock is visible, say the pair is identical.\n"
    "Ignore and never mention the person, face, hair, skin, body shape, pose, background, and image style. Do not add opinions or suggestions."
)
WARDROBE_PREFIX = (
    "WARDROBE DESCRIPTION (text derived from <Picture 2>; it complements the picture and names the socks and shoes explicitly; "
    "where text and picture disagree, the picture wins):\n"
)


def sw_inputs(t):
    return [{"name": "on_false", "type": t, "link": None}, {"name": "on_true", "type": t, "link": None}, {"name": "switch", "type": BOOL, "link": None}]


def build(src, dst):
    d = json.load(open(src, encoding="utf-8"))
    g = Graph(d)
    N = g.node

    # ------------------------------------------------------------ 1. metadata: drop comfyui_mcp, bump version
    d["extra"].pop("comfyui_mcp", None)
    d["extra"]["sain2d_workflow"].update({"version": VERSION, "date": DATE, "toobusy_commit": TOOBUSY_COMMIT})
    d["extra"]["workflow_name"] = dst.rsplit(".", 1)[0]
    d["revision"] = d.get("revision", 0) + 1
    for n in d["nodes"] + d["definitions"]["subgraphs"][0]["nodes"]:
        if n["type"].startswith("ToobusyMiniMaxH3"):
            n["properties"]["ver"] = TOOBUSY_COMMIT

    # ------------------------------------------------------------ 2. Stage 1 prompt: shared head + wardrobe description + layout body
    p3, p4 = N(163)["widgets_values"][0], N(164)["widgets_values"][0]
    head3, tail3 = p3.split("\n\nsummary:", 1)
    head4, tail4 = p4.split("\n\nsummary:", 1)
    assert head3 == head4
    tail3, tail4 = "summary:" + tail3, "summary:" + tail4
    # 4-panel body-lock contradiction: camera/scale locking applies to the full-body shots only
    tail4 = replace_once(tail4, "Use the same relaxed A-pose, stance and weight distribution in every view. Only the viewing direction changes.",
                         "Use the same relaxed A-pose, stance and weight distribution in [Shot 2], [Shot 3] and [Shot 4]. Between those three shots only the viewing direction changes.")
    tail4 = replace_once(tail4, "Use a fixed orthographic-like 85–105 mm lens, identical camera height, camera distance, ground line and subject scale. Never redraw a wider, shorter, taller, heavier, slimmer or differently proportioned body between views.",
                         "For [Shot 2], [Shot 3] and [Shot 4] use a fixed orthographic-like 85–105 mm lens, identical camera height, camera distance, ground line and subject scale. [Shot 1] keeps the same lens, lighting and head but uses a closer chest-up framing, so its subject scale is intentionally larger. Never redraw a wider, shorter, taller, heavier, slimmer or differently proportioned body between the full-body views.")
    N(163)["widgets_values"][0] = tail3
    N(163)["title"] = "Stage 1 Base Prompt · 3-View body (default)"
    N(164)["widgets_values"][0] = tail4
    N(164)["title"] = "Stage 1 Base Prompt · 4-Panel body (experimental)"
    N(165)["title"] = "Sheet Layout Select (body)"
    N(24)["widgets_values"][0] = p3  # fallback == full default prompt

    g.group("⑨")["bounding"][3] = 1900
    g.group("④")["bounding"][2] = 1240
    g.group("⑩")["bounding"][3] = 1300
    g.group("③")["bounding"][3] = 600

    tg_w = g.add_node("TextGenerate", "Gemma Vision · Wardrobe Description (socks / shoes / garments)", (40, 4540), (400, 143),
                      widgets=[WARDROBE_PROMPT, 256, "off", False, True],
                      inputs=[{"name": "clip", "type": "CLIP", "link": None}, {"name": "image", "type": IMG, "shape": 7, "link": None},
                              {"name": "video", "type": IMG, "shape": 7, "link": None}, {"name": "audio", "type": "AUDIO", "shape": 7, "link": None}],
                      outputs=[("generated_text", STR)])
    g.link(25, 0, tg_w, "clip", "CLIP")
    g.link(169, 0, tg_w, "image", IMG)  # the outfit image H3 actually receives
    w_bool = g.add_node("PrimitiveBoolean", "Wardrobe Description · OFF = picture only / ON = picture + Gemma text (default ON)", (460, 4540), (300, 58),
                        widgets=[True], outputs=[("BOOLEAN", BOOL)], color="#432", bgcolor="#653")
    w_pre = g.add_node("StringConcatenate", "Wardrobe Description · Prefix", (40, 4720), (300, 70), widgets=["", "", WARDROBE_PREFIX],
                       inputs=[{"name": "string_a", "type": STR, "widget": {"name": "string_a"}, "link": None}, {"name": "string_b", "type": STR, "widget": {"name": "string_b"}, "link": None}],
                       outputs=[("STRING", STR)])
    g.link(EMPTY, 0, w_pre, "string_a", STR)
    g.link(tg_w, 0, w_pre, "string_b", STR)
    w_sw = g.add_node("ComfySwitchNode", "Wardrobe Description Gate", (460, 4720), (300, 78), widgets=[False], inputs=sw_inputs(STR), outputs=[("output", STR)])
    g.link(EMPTY, 0, w_sw, "on_false", STR)
    g.link(w_pre, 0, w_sw, "on_true", STR)
    g.link(w_bool, 0, w_sw, "switch", BOOL)
    w_prev = g.add_node("PreviewAny", "Wardrobe Description Check", (603, 2090), (520, 200), widgets=[],
                        inputs=[{"name": "source", "type": "*", "link": None}], outputs=[])
    g.link(w_sw, 0, w_prev, "source", STR)

    head = g.add_node("PrimitiveStringMultiline", "Stage 1 Base Prompt · Subject Definitions (shared head)", (1580, 4180), (391, 110), widgets=[head3], outputs=[("STRING", STR)])
    c1 = g.add_node("StringConcatenate", "Stage 1 Prompt · Definitions + Wardrobe Description", (2000, 4180), (391, 70), widgets=["", "", "\n\n"],
                    inputs=[{"name": "string_a", "type": STR, "widget": {"name": "string_a"}, "link": None}, {"name": "string_b", "type": STR, "widget": {"name": "string_b"}, "link": None}],
                    outputs=[("STRING", STR)])
    g.link(head, 0, c1, "string_a", STR)
    g.link(w_sw, 0, c1, "string_b", STR)
    c2 = g.add_node("StringConcatenate", "Stage 1 Prompt · + Layout Body", (1160, 4330), (391, 70), widgets=["", "", "\n\n"],
                    inputs=[{"name": "string_a", "type": STR, "widget": {"name": "string_a"}, "link": None}, {"name": "string_b", "type": STR, "widget": {"name": "string_b"}, "link": None}],
                    outputs=[("STRING", STR)])
    g.link(c1, 0, c2, "string_a", STR)
    g.link(165, 0, c2, "string_b", STR)
    g.link(c2, 0, 24, "string_a", STR)

    # ------------------------------------------------------------ 3. empty-input gates for the two Gemma translators
    def empty_gate(k, text_node, tg_node, consumers, pos_rx, pos_sw):
        rx = g.add_node("RegexMatch", f"User Text Present? · {k}", pos_rx, (220, 130), widgets=["", r"\S", True, False, False],
                        inputs=[{"name": "string", "type": STR, "widget": {"name": "string"}, "link": None}], outputs=[("matches", BOOL)])
        g.link(text_node, 0, rx, "string", STR)
        sw = g.add_node("ComfySwitchNode", f"Translation Gate · {k} (skips Gemma when the box is empty)", pos_sw, (220, 78), widgets=[False], inputs=sw_inputs(STR), outputs=[("output", STR)])
        g.link(EMPTY, 0, sw, "on_false", STR)
        g.link(tg_node, 0, sw, "on_true", STR)
        g.link(rx, 0, sw, "switch", BOOL)
        for nid, inp in consumers:
            g.link(sw, 0, nid, inp, STR)
        return sw

    empty_gate("Stage 1 Direction", 23, 138, [(24, "string_b"), (139, "source")], (790, 4540), (790, 4720))
    empty_gate("Stage 2 Panel Request", 43, 129, [(119, "string_b"), (130, "source")], (40, 4900), (290, 4900))

    # ------------------------------------------------------------ 4. SIGMAS / MODEL source selector (PDD vs BasicScheduler fallback)
    N(7)["mode"] = 0
    N(7)["widgets_values"] = ["sgm_uniform", 30, 1]
    N(7)["title"] = "BasicScheduler · 30-step fallback (used only when Sigmas Source is ON)"
    s_bool = g.add_node("PrimitiveBoolean", "Sigmas Source · OFF = PDD Acc 8-step (default) / ON = BasicScheduler 30-step fallback (no PDD file needed)",
                        (2090, 2010), (370, 58), widgets=[False], outputs=[("BOOLEAN", BOOL)], color="#432", bgcolor="#653")
    s_sig = g.add_node("ComfySwitchNode", "Sigmas Select", (2090, 2100), (180, 78), widgets=[False], inputs=sw_inputs(SIG), outputs=[("output", SIG)])
    g.link(145, 1, s_sig, "on_false", SIG)
    g.link(7, 0, s_sig, "on_true", SIG)
    g.link(s_bool, 0, s_sig, "switch", BOOL)
    g.link(s_sig, 0, 8, "sigmas", SIG)
    g.link(s_sig, 0, 109, "sigmas", SIG)
    s_mod = g.add_node("ComfySwitchNode", "Model Select (PDD patched / plain)", (2090, 2210), (180, 78), widgets=[False], inputs=sw_inputs(MODEL), outputs=[("output", MODEL)])
    g.link(145, 0, s_mod, "on_false", MODEL)
    g.link(144, 0, s_mod, "on_true", MODEL)
    g.link(s_bool, 0, s_mod, "switch", BOOL)
    g.link(s_mod, 0, 136, "model", MODEL)
    s_txt = g.add_node("PrimitiveString", "PDD Info · fallback text", (2280, 2100), (180, 58), widgets=["PDD Acc bypassed — BasicScheduler 30-step fallback in use"], outputs=[("STRING", STR)])
    s_inf = g.add_node("ComfySwitchNode", "PDD Info Select", (2280, 2210), (180, 78), widgets=[False], inputs=sw_inputs(STR), outputs=[("output", STR)])
    g.link(145, 2, s_inf, "on_false", STR)
    g.link(s_txt, 0, s_inf, "on_true", STR)
    g.link(s_bool, 0, s_inf, "switch", BOOL)
    g.link(s_inf, 0, 146, "source", STR)

    # ------------------------------------------------------------ 5. remove the experimental pose_or_extra_ref input from the stable path
    sg = d["definitions"]["subgraphs"][0]
    sg["links"] = [l for l in sg["links"] if l["id"] != 219]
    sg["inputs"] = [i for i in sg["inputs"] if i["name"] != "pose_or_extra_ref"]
    for n in sg["nodes"]:
        if n["id"] == 99:
            for inp in n["inputs"]:
                if inp["name"] == "ref_images.ref_image_4":
                    assert inp["link"] == 219
                    inp["link"] = None
    N(109)["inputs"] = [i for i in N(109)["inputs"] if i["name"] != "pose_or_extra_ref"]
    N(109)["title"] = "Stage 2 Full · Panels 1-4 · Click ON/OFF"

    # ------------------------------------------------------------ 6. notes
    h = N(67)["widgets_values"][0]
    h = replace_once(h, "### 🛟 If the cut-out fails",
                     "### 🧦 Socks and shoes\nSegFormer has no sock class, so socks survive the cut-out only when they are read as part of the shoe. Since v1.3.2 Gemma also writes a **WARDROBE DESCRIPTION** (garments, socks, shoes) from the cut-out and it is inserted into the Stage 1 prompt, so the feet no longer depend on a few grey pixels. Check it in **③ Wardrobe Description Check**; switch it off in ⑨ if it misreads the outfit.\n\n### 🛟 If the cut-out fails")
    N(67)["widgets_values"][0] = h
    m = N(20)["widgets_values"][0]
    m = replace_once(m, "Custom nodes: SAM3Segment", "Custom nodes: SAM3Segment") if "Custom nodes: SAM3Segment" in m else m
    m = replace_once(m, "## ⑦ 8-step PDD accelerator · loaded by the `PDD Acc Apply` node\n",
                     "## ⑦ 8-step PDD accelerator · loaded by the `PDD Acc Apply` node\nCannot get the file? Flip **Sigmas Source** in ④ to ON: the PDD node is skipped and a 30-step BasicScheduler runs instead (slower, no extra file).\n")
    m = replace_once(m, "- Face cut-out → SAM3", "- toobusy node pack: tested static build 0.4.10, commit `bdbed644`\n- Face cut-out → SAM3")
    N(20)["widgets_values"][0] = m
    c = N(69)["widgets_values"][0]
    c = replace_once(c, "**Version:** v1.3.1 · 2026-09-03\n",
                     f"**Version:** {VERSION} · {DATE}\n\n**{VERSION} changes**\n- Gemma wardrobe description (socks / shoes / garments) inserted into the Stage 1 prompt\n- Gemma translators are skipped when the ③ / ⑧ boxes are empty\n- Sigmas Source switch: PDD 8-step (default) or BasicScheduler 30-step fallback, feeding Stage 1 and Stage 2\n- Experimental direct pose input removed from the Stage 2 subgraph; 4-panel body-lock wording fixed\n- toobusy pinned to 0.4.10, `comfyui_mcp` metadata removed\n")
    N(69)["widgets_values"][0] = c
    o = N(66)["widgets_values"][0]
    o = replace_once(o, "1. **① LOAD MODELS** — only check that no loader says `MISSING`.",
                     "1. **① LOAD MODELS** — only check that no loader says `MISSING`. No PDD file? Turn **Sigmas Source** ON in ④.")
    N(66)["widgets_values"][0] = o

    sync_named(d)
    json.dump(d, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("wrote", dst, "nodes", len(d["nodes"]), "links", len(d["links"]))


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
