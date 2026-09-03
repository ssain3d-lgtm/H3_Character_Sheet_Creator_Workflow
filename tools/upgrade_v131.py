"""One-off upgrade: v1.3 ENG workflow -> v1.3.1 ENG workflow.

Run from the repository root:
    python tools/upgrade_v131.py old/260903_H3_character_sheet(sain2d_modified)_ENG.json \
        "260903_H3_character_sheet(sain2d_modified)_v1.3.1_ENG.json"

The KOR file is then generated from the ENG file with tools/build_kor.py.
"""
import json
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
from wfedit import Graph, sync_named, replace_once  # noqa: E402

VERSION = "v1.3.1"
DATE = "2026-09-03"

STR = "STRING"
IMG = "IMAGE"
BOOL = "BOOLEAN"
PICTURE_YES = r"VISUAL_REFERENCE\s*:\s*YES"


def build(src, dst):
    d = json.load(open(src, encoding="utf-8"))
    g = Graph(d)
    N = g.node

    # ------------------------------------------------------------------ 1. Stage 1 prompt text
    p3 = N(24)["widgets_values"][0]
    p3 = replace_once(
        p3,
        "Read the gender presentation, age and ethnicity directly from <Picture 1> and keep them unchanged.",
        "Read the gender presentation, apparent age, skin tone and visible facial features directly from <Picture 1> and keep them unchanged.",
    )
    assert "ethnicity" not in p3

    # 4-panel variant (close-up + front / side / back), derived from the 3-view text
    p4 = p3
    p4 = replace_once(
        p4,
        "Present exactly three complete full-body views — front, strict right-side profile and back — on a neutral light-grey studio background",
        "Present exactly four views — a chest-up front close-up, then complete full-body front, strict right-side profile and back views — on a neutral light-grey studio background",
    )
    p4 = p4.replace("(appears in [Shot 1], [Shot 2], [Shot 3])", "(appears in [Shot 1], [Shot 2], [Shot 3], [Shot 4])")
    assert p4.count("[Shot 4])") == 2
    p4 = replace_once(p4, "remains identical in all three shots", "remains identical in all four shots")
    p4 = replace_once(
        p4,
        "Arrange exactly three equal vertical views side by side from left to right. All three views must share one ground line, one subject scale, one camera distance, one camera height and one lighting setup.",
        "Arrange exactly four equal vertical views side by side from left to right. [Shot 2], [Shot 3] and [Shot 4] must share one ground line, one subject scale, one camera distance, one camera height and one lighting setup. [Shot 1] uses the same lighting with a closer camera.",
    )
    p4 = replace_once(p4, "[Shot 3] Complete full-body back view", "[Shot 4] Complete full-body back view")
    p4 = replace_once(p4, "[Shot 2] Complete full-body strict 90-degree", "[Shot 3] Complete full-body strict 90-degree")
    p4 = replace_once(
        p4,
        "[Shot 1] Complete full-body front view in a relaxed A-pose, face looking directly toward the camera. Both feet point forward and are fully visible.",
        "[Shot 1] Chest-up front close-up: head, complete hairstyle, face and shoulders fill the column, face looking directly toward the camera with a calm neutral expression.\n\n[Shot 2] Complete full-body front view in a relaxed A-pose, face looking directly toward the camera. Both feet point forward and are fully visible.",
    )
    p4 = replace_once(
        p4,
        "The same hairstyle from <Picture 1> must remain visible in all three shots and change only according to the viewing direction. Show the complete head and both complete feet in every shot.",
        "The same hairstyle from <Picture 1> must remain visible in all four shots and change only according to the viewing direction. Show the complete head in every shot and both complete feet in [Shot 2], [Shot 3] and [Shot 4].",
    )
    p4 = replace_once(p4, "All three views are rotations of one unchanged adult body mesh.", "The three full-body views are rotations of one unchanged adult body mesh, and the close-up shows the same head at a closer camera distance.")
    p4 = replace_once(p4, "hand size and foot size in all three views.", "hand size and foot size in all full-body views.")
    p4 = replace_once(p4, "the three-shot front / side / back layout", "the four-shot close-up / front / side / back layout")
    p4 = replace_once(p4, "apply it consistently to every visible area of skin in all three shots", "apply it consistently to every visible area of skin in all four shots")
    assert "three" not in p4.replace("three full-body views", ""), [l for l in p4.split("\n") if "three" in l]

    # ------------------------------------------------------------------ 2. Sheet-layout switch feeding node 24
    g.group("③")["bounding"][3] = 480
    n_layout = g.add_node("PrimitiveBoolean", "Sheet Layout · OFF = 3-view front/side/back (default) / ON = 4-panel close-up + front/side/back (EXPERIMENTAL)",
                          (40, 2090), (560, 58), widgets=[False], outputs=[("BOOLEAN", BOOL)], color="#432", bgcolor="#653")
    g.group("⑩")["bounding"][3] = 1150
    n_p3 = g.add_node("PrimitiveStringMultiline", "Stage 1 Base Prompt · 3-View (default)", (1580, 4020), (391, 110), widgets=[p3], outputs=[("STRING", STR)])
    n_p4 = g.add_node("PrimitiveStringMultiline", "Stage 1 Base Prompt · 4-Panel (experimental)", (2000, 4020), (391, 110), widgets=[p4], outputs=[("STRING", STR)])
    n_psw = g.add_node("ComfySwitchNode", "Sheet Layout Select", (1160, 4180), (391, 78), widgets=[False],
                       inputs=[{"name": "on_false", "type": STR, "link": None}, {"name": "on_true", "type": STR, "link": None}, {"name": "switch", "type": BOOL, "link": None}],
                       outputs=[("output", STR)])
    g.link(n_p3, 0, n_psw, "on_false", STR)
    g.link(n_p4, 0, n_psw, "on_true", STR)
    g.link(n_layout, 0, n_psw, "switch", BOOL)
    g.add_input(24, "string_a", STR)
    g.link(n_psw, 0, 24, "string_a", STR)
    N(161)["pos"] = [1160, 4020]
    N(24)["widgets_values"][0] = p3  # fallback value == default prompt
    N(24)["title"] = "Stage 1 Prompt · Base (3-view / 4-panel) + User Direction"

    # ------------------------------------------------------------------ 3. Face / outfit fallback switches
    g.group("②")["bounding"][2] = 1180
    n_fb = g.add_node("PrimitiveBoolean", "Face Source · OFF = SAM3 head cut-out (default) / ON = raw face photo", (2820, 690), (330, 58), widgets=[False], outputs=[("BOOLEAN", BOOL)], color="#432", bgcolor="#653")
    n_fsw = g.add_node("ComfySwitchNode", "Face Reference Select", (2820, 790), (330, 78), widgets=[False],
                       inputs=[{"name": "on_false", "type": IMG, "link": None}, {"name": "on_true", "type": IMG, "link": None}, {"name": "switch", "type": BOOL, "link": None}],
                       outputs=[("output", IMG)])
    g.link(155, 0, n_fsw, "on_false", IMG)
    g.link(16, 0, n_fsw, "on_true", IMG)
    g.link(n_fb, 0, n_fsw, "switch", BOOL)
    g.link(n_fsw, 0, 13, "ref_images.ref_image_0", IMG)
    g.link(n_fsw, 0, 153, "images", IMG)

    n_ob = g.add_node("PrimitiveBoolean", "Outfit Source · OFF = clothes cut-out (default) / ON = background-removed full photo", (2820, 1190), (330, 58), widgets=[False], outputs=[("BOOLEAN", BOOL)], color="#432", bgcolor="#653")
    n_osw = g.add_node("ComfySwitchNode", "Outfit Reference Select", (2820, 1300), (330, 78), widgets=[False],
                       inputs=[{"name": "on_false", "type": IMG, "link": None}, {"name": "on_true", "type": IMG, "link": None}, {"name": "switch", "type": BOOL, "link": None}],
                       outputs=[("output", IMG)])
    g.link(157, 0, n_osw, "on_false", IMG)
    g.link(159, 0, n_osw, "on_true", IMG)
    g.link(n_ob, 0, n_osw, "switch", BOOL)
    g.link(n_osw, 0, 13, "ref_images.ref_image_1", IMG)
    g.link(n_osw, 0, 154, "images", IMG)
    N(154)["pos"] = [2820, 900]
    # SAM3 head mask: offset 8 px bled background / shoulders into the identity crop; 2 px is enough to keep hair edges
    assert N(155)["type"] == "SAM3Segment" and N(155)["widgets_values"][6] == 8
    N(155)["widgets_values"][6] = 2
    N(153)["title"] = "Extraction Check · Identity (what H3 receives)"
    N(154)["title"] = "Extraction Check · Outfit (what H3 receives)"

    # ------------------------------------------------------------------ 4. Stage 2 dynamic <Picture N> numbering
    # H3 core skips None references and numbers the remaining images in slot order, so an
    # optional reference that is OFF (or rejected by Gemma) shifts every later number.
    g.group("⑨")["bounding"][3] = 1300
    sw_in = lambda: [{"name": "on_false", "type": STR, "link": None}, {"name": "on_true", "type": STR, "link": None}, {"name": "switch", "type": BOOL, "link": None}]
    c2 = g.add_node("PrimitiveString", "Tag Constant · <Picture 2>", (40, 3720), (220, 58), widgets=["<Picture 2>"], outputs=[("STRING", STR)])
    c3 = g.add_node("PrimitiveString", "Tag Constant · <Picture 3>", (290, 3720), (220, 58), widgets=["<Picture 3>"], outputs=[("STRING", STR)])
    c4 = g.add_node("PrimitiveString", "Tag Constant · <Picture 4>", (540, 3720), (220, 58), widgets=["<Picture 4>"], outputs=[("STRING", STR)])
    empty = 147  # existing "Empty Text" primitive

    def gate_and_pass(k, enabled_node, analysis_node, y):
        sw = g.add_node("ComfySwitchNode", f"Analysis Gate · Optional {k} (empty when OFF)", (40, y), (220, 78), widgets=[False], inputs=sw_in(), outputs=[("output", STR)])
        g.link(empty, 0, sw, "on_false", STR)
        g.link(analysis_node, 0, sw, "on_true", STR)
        g.link(enabled_node, 0, sw, "switch", BOOL)
        rx = g.add_node("RegexMatch", f"Picture Attached? · Optional {k}", (290, y), (220, 130),
                        widgets=["", PICTURE_YES, True, False, False],
                        inputs=[{"name": "string", "type": STR, "widget": {"name": "string"}, "link": None}],
                        outputs=[("matches", BOOL)])
        g.link(sw, 0, rx, "string", STR)
        return rx

    def role_line(k, tag_node, sem_node, rx, pos_concat, pos_line):
        cc = g.add_node("StringConcatenate", f"Picture Tag + Role · Optional {k}", pos_concat, (220, 70), widgets=["", "", " = "],
                        inputs=[{"name": "string_a", "type": STR, "widget": {"name": "string_a"}, "link": None}, {"name": "string_b", "type": STR, "widget": {"name": "string_b"}, "link": None}],
                        outputs=[("STRING", STR)])
        g.link(tag_node, 0, cc, "string_a", STR)
        g.link(sem_node, 1, cc, "string_b", STR)
        ln = g.add_node("ComfySwitchNode", f"Role Line · Optional {k} (tagged only when a picture is attached)", pos_line, (220, 78), widgets=[False], inputs=sw_in(), outputs=[("output", STR)])
        g.link(sem_node, 1, ln, "on_false", STR)
        g.link(cc, 0, ln, "on_true", STR)
        g.link(rx, 0, ln, "switch", BOOL)
        return ln

    def tag_switch(title, pos, cond_rx, on_true_node, on_false_node):
        sw = g.add_node("ComfySwitchNode", title, pos, (220, 78), widgets=[False], inputs=sw_in(), outputs=[("output", STR)])
        g.link(on_false_node, 0, sw, "on_false", STR)
        g.link(on_true_node, 0, sw, "on_true", STR)
        g.link(cond_rx, 0, sw, "switch", BOOL)
        return sw

    rx4 = gate_and_pass(4, 85, 77, 3820)
    line4 = role_line(4, c2, 81, rx4, (540, 3820), (790, 3820))
    rx5 = gate_and_pass(5, 86, 78, 4000)
    tag5 = tag_switch("Picture Tag · Optional 5 (3 if prop attached, else 2)", (540, 4000), rx4, c3, c2)
    line5 = role_line(5, tag5, 82, rx5, (790, 4000), (40, 4180))
    rx6 = gate_and_pass(6, 87, 79, 4180)  # placed at x=290 / 540 by helper -> shift below
    # helper placed rx6's gate at (40,4100) which collides with line5; move them
    N(rx6 - 1)["pos"] = [290, 4180]
    N(rx6)["pos"] = [540, 4180]
    tag6a = tag_switch("Picture Tag · Optional 6 when prop attached (4 if env attached, else 3)", (790, 4180), rx5, c4, c3)
    tag6b = tag_switch("Picture Tag · Optional 6 when prop not attached (3 if env attached, else 2)", (40, 4360), rx5, c3, c2)
    tag6 = tag_switch("Picture Tag · Optional 6", (290, 4360), rx4, tag6a, tag6b)
    line6 = role_line(6, tag6, 83, rx6, (540, 4360), (790, 4360))
    g.link(line4, 0, 88, "string_b", STR)
    g.link(line5, 0, 89, "string_b", STR)
    g.link(line6, 0, 90, "string_b", STR)

    # role labels no longer carry a hard-coded picture number
    for nid, old, new in (
        (81, "<Picture 2> = optional prop or object reference", "optional prop or object reference"),
        (82, "<Picture 3> = optional environment reference", "optional environment reference"),
        (83, "<Picture 4> = optional additional prop or accessory reference", "optional additional prop or accessory reference"),
    ):
        N(nid)["widgets_values"][2] = replace_once(N(nid)["widgets_values"][2], old, new)
    for nid in (113, 114):
        N(nid)["widgets_values"][0] += " If no picture is attached for the prop, build the object from its text description in the enabled reference roles."

    q = N(49)["widgets_values"][0]
    q = replace_once(q, "shows this same character from the front, the side and the back.", "shows this same character from the front, the side and the back (plus a chest-up close-up when the 4-panel layout was used).")
    q = replace_once(q, "Each additional enabled picture contributes only its own named prop, accessory or environment", "Each additional attached picture is bound to exactly one role line below by its <Picture N> tag and contributes only its own named prop, accessory or environment")
    N(49)["widgets_values"][0] = q
    r = N(88)["widgets_values"][0]
    N(88)["widgets_values"][0] = replace_once(r, "<Picture 1> = the Stage 1 front / side / back turnaround sheet of the character.", "<Picture 1> = the Stage 1 turnaround sheet of the character (front / side / back, plus a close-up in the 4-panel layout).")
    N(54)["widgets_values"][2] = "\n\nEnabled reference roles (these extend subject_definitions above; a role without a <Picture N> tag is text-only and has no picture attached):\n"

    # ------------------------------------------------------------------ 5. Model chain labels / LoRA / attention
    N(17)["widgets_values"][0] = "h3-realism-people-t2v-i2v-r2v.safetensors"
    N(17)["widgets_values"][1] = 1.0
    N(17)["title"] = "OPTIONAL · Style LoRA · loras (bypassed by default · photo refs only · trigger r34l1sm)"
    N(136)["title"] = "MiniMax H3 · Comfy Kitchen Attention · after PDD Acc"
    N(7)["title"] = "OPTIONAL · BasicScheduler (fallback when PDD Acc is unavailable · bypassed)"

    # ------------------------------------------------------------------ 6. Resolution note
    g.group("④")["bounding"][3] = 600
    g.add_node("MarkdownNote", "Resolution Presets", (1270, 2140), (340, 130),
               widgets=["**Resolution Selector presets**\n- Draft: `2` MP · fastest, soft detail\n- Standard: `3` MP · inside the T=1 image VAE's validated range\n- High: `8` MP (default) · the sample sheet; sharper layout, some airbrushing on hair / fabric\n\nKeep `1:1 (Square)` when Stage 2 is used. 4-panel layout benefits from the High preset."],
               properties={"Node name for S&R": "MarkdownNote"}, color="#432", bgcolor="#653")

    # ------------------------------------------------------------------ 7. Notes
    m = N(20)["widgets_values"][0]
    m = replace_once(
        m,
        "## ③ H3 Qwen text encoder · `models/text_encoders/`\n[qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors)\n",
        "## ③ H3 Qwen text encoder · `models/text_encoders/`\nDefault (matches the loader): [qwen3vl_32b_minimax_h3_int8_convrot.safetensors](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors) · ~27 GB\nSmaller alternative for 24–32 GB cards: [qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors) · ~16 GB — pick it in the loader after downloading.\n",
    )
    m = replace_once(
        m,
        "Only enable a LoRA (e.g. a realism LoRA) for **photographic** references.",
        "Only enable a LoRA for **photographic** references, e.g. [h3-realism-people-t2v-i2v-r2v.safetensors](https://huggingface.co/fal/MiniMax-H3-Realism-People-LoRA) (trigger word `r34l1sm`, strength 1.0; 0.6–0.8 for a lighter touch).",
    )
    N(20)["widgets_values"][0] = m

    h = N(67)["widgets_values"][0]
    h = replace_once(
        h,
        "### 👀 How to check it worked",
        "### 🛟 If the cut-out fails\nTwo switches sit under the previews. **Face Source ON** sends the raw face photo instead of the SAM3 crop; **Outfit Source ON** sends the background-removed full photo instead of the clothes cut-out. The previews always show what H3 actually receives.\nLong hair, buns or a hat cut off? Change the SAM3 prompt from `head` to `head and hair` (or `head and hat`).\n\n### 👀 How to check it worked",
    )
    N(67)["widgets_values"][0] = h

    c = N(69)["widgets_values"][0]
    c = replace_once(
        c,
        "**Version:** v1.3 · 2026-09-03\n",
        f"**Version:** {VERSION} · {DATE}\n\n**{VERSION} changes**\n- Stage 2 optional references get their `<Picture N>` numbers dynamically (H3 renumbers when a slot is OFF or rejected)\n- Face / outfit fallback switches, 3-view / 4-panel sheet layout switch (4-panel is experimental)\n- Named widget values re-synced, Qwen INT8 default documented, LoRA file name fixed, node pack ids corrected\n",
    )
    N(69)["widgets_values"][0] = c

    o = N(66)["widgets_values"][0]
    o = replace_once(o, "3. **③** — only if you want to change body type or styling. (Optional)", "3. **③** — only if you want to change body type or styling, or switch to the experimental 4-panel layout. (Optional)")
    N(66)["widgets_values"][0] = o

    # ------------------------------------------------------------------ 8. Subgraph / metadata / pack ids
    sg = d["definitions"]["subgraphs"][0]
    sg["name"] = "Stage 2 Pose Sheet Generator"
    for inp in sg["inputs"]:
        if inp["name"] == "pose_or_extra_ref":
            inp["label"] = "EXPERIMENTAL · direct pose ref (unconnected)"
    for inp in N(109)["inputs"]:
        if inp["name"] == "pose_or_extra_ref":
            inp["label"] = "EXPERIMENTAL · direct pose ref (unconnected)"

    d["extra"]["sain2d_workflow"] = {
        "version": VERSION, "date": DATE, "modified_by": "sain2d", "ai_collaboration": "Claude",
        "based_on": "너무바쁜베짱이 (2BZ) · H3 캐릭터시트 간편제작기 3+3 v1.0",
        "repo": "https://github.com/ssain3d-lgtm/H3_Character_Sheet_Creator_Workflow",
    }
    d["extra"]["workflow_name"] = dst.rsplit(".", 1)[0]
    if "comfyui_mcp" in d["extra"]:
        d["extra"]["comfyui_mcp"]["workflow_path"] = "workflows/" + dst
    d["revision"] = d.get("revision", 0) + 1

    PACKS = {
        "RMBG": ("comfyui-rmbg", "1038lab/ComfyUI-RMBG"),
        "SAM3Segment": ("comfyui-rmbg", "1038lab/ComfyUI-RMBG"),
        "ClothesSegment": ("comfyui-rmbg", "1038lab/ComfyUI-RMBG"),
        "ImageConcanate": ("comfyui-kjnodes", "kijai/ComfyUI-KJNodes"),
        "MathExpression|pysssss": ("comfyui-custom-scripts", "pythongosssss/ComfyUI-Custom-Scripts"),
        "MiniMaxH3PDDAccApply": (None, "Jalen-Brunson/ComfyUI-MiniMax-H3-PDD-Acc"),
        "ToobusyMiniMaxH3ImageLatent": ("toobusy", "nicekriss/toobusy"),
        "ToobusyMiniMaxH3SemanticReference": ("toobusy", "nicekriss/toobusy"),
        "Fast Groups Muter (rgthree)": ("rgthree-comfy", "rgthree/rgthree-comfy"),
    }
    for n in d["nodes"] + sg["nodes"]:
        if n["type"] in PACKS:
            cnr, aux = PACKS[n["type"]]
            props = n.setdefault("properties", {})
            if props.get("cnr_id") == "comfyui-workflow-encrypt":
                props.pop("ver", None)
            if cnr:
                props["cnr_id"] = cnr
            else:
                props.pop("cnr_id", None)
                props.pop("ver", None)
            props["aux_id"] = aux
            props.setdefault("Node name for S&R", n["type"])

    sync_named(d)
    json.dump(d, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("wrote", dst, "nodes", len(d["nodes"]), "links", len(d["links"]))


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
