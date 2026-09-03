# Test status

Two kinds of evidence are kept apart here. **Static CI** proves the JSON is well-formed and wired the way the design says. **Runtime tests** prove ComfyUI actually produces the intended images. Only the second kind can mark a release "verified".

## Static CI (automatic, every push)

`.github/workflows/validate.yml` → `tools/validate_workflow.py`

| Check | v1.3.2 |
|---|---|
| Link / node / subgraph integrity, unique ids, subgraph interface matches the instance node | pass |
| `widgets_values` == `widgets_values_named` on every node; KOR carries the same named keys | pass |
| KOR is byte-identical to ENG + `tools/kor_overlay.json` | pass |
| KOR / ENG functional parity (types, modes, links, widget values, subgraph) | pass |
| Forbidden leftovers (old prompts, test inputs, `comfyui-workflow-encrypt`, `pose_or_extra_ref`), `extra.comfyui_mcp` absent in root and `old/` | pass |
| Stage 1 recipe: euler, PDD 8-step, SigmaShift 12/3, BasicGuider; Sigmas Select defaults to PDD, fallback is an active BasicScheduler; Model Select driven by the same switch | pass |
| Stage 2 recipe: sampler sigmas from the shared selector, BasicGuider conditioned by the H3 node, fixed seed, Picture 1 = Stage 1 sheet, refs 1–3 mapped, no extra refs | pass |
| SemanticReference routing = `auto`, role labels carry no fixed picture number, toobusy `ver` pinned to `bdbed644` | pass |
| Stage 2 role simulation: 27 cases (each optional slot OFF / ON-safe / ON-rejected) — `<Picture N>` tags match H3's compaction, descriptions survive, rejected slots carry no tag. Runs the real toobusy class in CI, an emulation locally | pass |
| Model file names identical across loaders, in-canvas note and README; LoRA file name is a plain `.safetensors` name | pass |
| No tracked bytecode | pass |

## Runtime tests (manual, in ComfyUI)

Environment used: _not yet recorded_. Fill in ComfyUI version, frontend version, GPU, toobusy commit, PDD pack commit.

| # | Test | Expected | v1.3.2 result |
|---|---|---|---|
| R1 | Load ENG and KOR JSON on the classic canvas | no missing nodes after installing the six packs; no red nodes | not run |
| R2 | Stage 1, Stage 2 OFF, sample assets | 3-view sheet saved to `output/charsheet/`; no request for pose / optional image files | not run |
| R3 | R2 with **Wardrobe Description** ON vs OFF, same seed | socks and shoes match `clothes_ref.png` more reliably with ON; preview shows a sane `WARDROBE DESCRIPTION:` | not run |
| R4 | ③ box empty | `Stage 1 Request · Translated Output Check` shows an empty string (Gemma skipped) | not run |
| R5 | ③ box = `black loafers, no socks` | translated text present; feet follow the direction | not run |
| R6 | **Sigmas Source** ON without the PDD file present | Stage 1 completes with BasicScheduler 30 steps; PDD info preview shows the fallback text | not run |
| R7 | Sheet Layout ON (4-panel) | four columns: chest-up close-up + front / side / back; no fifth cell | not run |
| R8 | Stage 2 ON, pose only, panel count 1 / 2 / 3 / 4 | exact panel count; `Stage 2 Final Prompt Check` shows only `<Picture 1>` | not run |
| R9 | Stage 2 with prop / environment / accessory switches in all 8 ON/OFF combinations | final prompt tags are `<Picture 2..N>` in slot order of the ON references; images match the described roles | not run |
| R10 | Stage 2 with a reference Gemma marks `VISUAL_REFERENCE: NO` | that role line has no `<Picture N>` tag; later references are renumbered | not run |
| R11 | Final 16:9 composite | exact 16:9, Stage 1 sheet left, panels right, no "sheet-in-sheet" | not run |
| R12 | `Restore widget values by name` ON vs OFF | identical prompts and inputs after reload | not run |

Record results by editing this table (pass / fail + short note) and commit them together with the sample outputs.
