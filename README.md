# H3 Character Sheet Creator Workflow

**English** | [한국어](#한국어)

A ComfyUI workflow that takes a **face reference** and an **outfit reference** and generates a **3-view character sheet** (front / side / back). Built on MiniMax-H3 Ref2VA.

> Original workflow by **너바베** — [로컬 일관성 끝판왕 · 미니맥스 H3로 캐릭터 시트 만들기 | ComfyUI 워크플로우](https://www.youtube.com/watch?v=nsvAbax4jng)  
> This repository is a modified version (sain2d).

## Example

| Face reference | Outfit reference |
|:---:|:---:|
| <img src="asset/face_ref.png" width="300"> | <img src="asset/clothes_ref.png" width="300"> |

⬇️

![3-view character sheet](asset/H3_2STAGE_STAGE1_3VIEW_00072_.png)

The **identity** (facial features, hair) comes from the face reference and **only the clothing** is taken from the outfit reference, merged into a single character.

## Files

| File | Description |
|---|---|
| `260903_H3_character_sheet(sain2d_modified)_v1.3.2_KOR.json` | **v1.3.2** workflow (Korean UI) — generated from the ENG file |
| `260903_H3_character_sheet(sain2d_modified)_v1.3.2_ENG.json` | **v1.3.2** workflow (English UI) — canonical file |
| `old/` | v1.2, v1.3 and v1.3.1 workflows, kept for reference |
| `tools/` | `validate_workflow.py` (static checks run by CI), `build_kor.py` + `kor_overlay.json` (KOR generator), `upgrade_v131.py` / `upgrade_v132.py` (the version transforms), `tidy_layout.py` (deterministic node layout: one row per flow depth inside each group, groups re-stacked without overlap), `render_layout.py` (PNG preview of the layout, needs Pillow) |
| `TESTING.md` | Static CI results and the manual ComfyUI runtime test log, kept separate |
| `asset/` | Sample reference images and output (demonstration only; rights to the sample artwork stay with their owners) |

To reproduce the example, copy `asset/face_ref.png` and `asset/clothes_ref.png` into your ComfyUI `input/` folder; the Stage 1 loaders point to those names by default.

## What changed in v1.3.2 (2026-09-03)

Release hardening after a second review of v1.3.1, plus two fixes for outfits / socks / shoes drifting away from the reference.

- **Why feet drifted.** SegFormer has no sock class, its mask is computed on a 1024×1024 squash, and the prompt never named the footwear, so socks and shoes rode on a few grey pixels. On top of that the Gemma translator ran on an empty ③ box and its output landed under the highest-priority user direction, which is allowed to change "anything worn".
- **Gemma wardrobe description.** Gemma now reads the outfit cut-out and writes `WARDROBE DESCRIPTION:` (garments, socks, shoes) which is inserted after the subject definitions. Switch in ⑨, preview in ③. Default ON.
- **Empty-input gates.** ③ and ⑧ translators are skipped (lazy switch) when the box is empty; the prompt gets an empty string instead of whatever Gemma would improvise.
- **Sigmas Source switch.** OFF = PDD Acc 8-step (default), ON = active BasicScheduler at 30 steps with the un-patched model, feeding both the Stage 1 sampler and the Stage 2 subgraph. Lets Stage 1 run without the PDD file.
- **Stable path only.** The experimental `pose_or_extra_ref` subgraph input is gone. The 4-panel body-lock text now locks camera distance / scale for Shots 2–4 only.
- **Pins and metadata.** toobusy pinned to 0.4.10, commit `bdbed644` (the 0.4.10 fix stops an optional FlashVSR import from taking the H3 helpers down). `extra.comfyui_mcp` removed from every shipped and archived JSON. Tracked bytecode removed, `.gitignore` added.
- **Validation.** `tools/validate_workflow.py` now also checks: `comfyui_mcp` absence (root and `old/`), unique node / link ids, subgraph interface vs instance node, Stage 2 recipe, the Sigmas / Model selector wiring, LoRA file names, SemanticReference routing = `auto`, toobusy pin, all root ENG/KOR pairs, and it **simulates the Stage 2 role assembly for 27 cases** (each optional slot OFF / ON-safe / ON-rejected) against H3's reference compaction — using the real toobusy class in CI.
- **Runtime evidence is tracked separately** in `TESTING.md`. Nothing in v1.3.2 has been run in ComfyUI yet; the static checks pass.

## What changed in v1.3.1 (2026-09-03)

Hotfix after an external review of v1.3. Adult characters only: the prompt fixes `adult` on purpose.

- **Stage 2 `<Picture N>` numbers are now dynamic.** ComfyUI's H3 node skips empty reference slots and numbers the remaining images in order, so with the prop switch OFF the environment picture was really `<Picture 2>` while the prompt still said `<Picture 3>`. Each optional role line now gets its tag from a Regex gate on Gemma's `VISUAL_REFERENCE: YES` verdict plus the switches, so the tag always matches what H3 sees. A reference that is enabled but rejected by Gemma keeps its text description and simply carries no tag.
- **Named widget values re-synced.** v1.3 changed `widgets_values` but left the old `widgets_values_named` copies in place (old `adult woman` prompt, the `흰 발목 양말` test input, the stale 2x3 prompt). ComfyUI can restore either representation, so both now agree, and CI fails if they ever drift again.
- **Fallback switches.** Face Source (SAM3 crop / raw photo) and Outfit Source (clothes cut-out / background-removed photo) under the previews; the previews show what H3 actually receives.
- **Sheet layout switch.** OFF = the proven 3-view turnaround; ON = an experimental 4-panel sheet (chest-up close-up + front / side / back). The 4-panel prompt has not been run yet.
- **Model guidance unified.** The in-canvas note now lists the INT8 Qwen encoder the loader expects (NVFP4 as a smaller alternative), the PDD accelerator's real repo and `models/pdd_acc/` folder, and the correct realism LoRA file name.
- **Housekeeping.** `ethnicity` removed from the prompt, attention / scheduler / LoRA nodes relabelled, subgraph renamed `Stage 2 Pose Sheet Generator`, `pose_or_extra_ref` marked experimental, node pack ids corrected (`comfyui-rmbg`, `comfyui-kjnodes`, `comfyui-custom-scripts`, `toobusy`, `rgthree-comfy`, PDD via `aux_id`), v1.3.1 metadata added under `extra.sain2d_workflow`.
- **KOR is generated, not hand-edited.** `tools/build_kor.py` overlays Korean titles / notes on the ENG file; CI rebuilds it and fails on any difference.
- **CI.** `.github/workflows/validate.yml` runs `tools/validate_workflow.py`: link integrity, named/positional widget parity, KOR/ENG functional parity, forbidden leftovers, PDD recipe (euler / 8 steps / shift 12·3 / BasicGuider), picture-tag gates, model names consistent across loaders, note and README.

## What changed in v1.3 (2026-09-03)

Consistency-focused fixes after a review of the v1.2 graph.

- **Gender-neutral identity role.** The Stage 1 prompt no longer hard-codes `adult woman`; gender presentation, age and ethnicity are read from the face reference.
- **Rendering style follows the face reference.** `photorealistic studio photography` was removed. The prompt now tells H3 to match the reference style (photo / illustration / anime) instead of pulling anime references toward photorealism.
- **Prompt section order fixed.** The `overall_soundscape` / `non_diegetic_music` block is appended after the user direction, at the very end of the Stage 1 prompt, the same way Stage 2 already did.
- **Stage 2 sees the whole turnaround.** Stage 2 used a crop of the front view only, while its prompt described the input as the full turnaround. The front / side / back sheet is now passed as Picture 1, so hair and costume are known from every angle.
- **Style LoRA marked optional.** The loader labelled "4-Step Turbo LoRA" actually held a realism LoRA and was bypassed. It is now labelled optional and stays bypassed; acceleration comes from the 8-step PDD accelerator. Keep it OFF for anime / illustrated references.
- **Leftover test inputs cleared.** The ENG file shipped with `흰 발목 양말, 신발 없음` in the Stage 1 direction box (it silently removed shoes from every run), the KOR file with a panel-3 request, and the H3 node with an unrelated stale prompt. All cleared; image loaders point to neutral placeholder names.
- **Guidance added.** The outfit photo must show both shoes and both arms; hats / sunglasses / bags are dropped unless enabled on the Extract Clothes Only node.

## How it works

**Stage 1 — 3-view sheet**
- Face image → head isolated with `SAM3Segment`
- Outfit image → background removed with `RMBG`, then clothing isolated with `ClothesSegment` (SegFormer); face, hair, arms and legs are removed automatically
- Both references feed H3 to produce the front / side / back sheet

**Stage 2 — Pose variations (optional)**
- Stage 1 sheet + a pose reference (analysed by Gemma as text only, so the pose photo's identity never leaks in) to generate 1–4 panels
- Optional inputs: prop / weapon, background / environment, extra accessory

## Required models

```
UNET   minimax_h3_ref2va_pruned_int8_convrot.safetensors
CLIP   qwen3vl_32b_minimax_h3_int8_convrot.safetensors   (~27 GB; qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors ~16 GB is a smaller alternative, select it in the loader)
       gemma4_e4b_it_fp8_scaled.safetensors
VAE    minimax_h3_t1_image_vae_step1597.safetensors
       minimax_h3_audio_vae_fp32.safetensors
Accel  MiniMax-H3-Ref2VA-Acc-8Step.safetensors  → models/pdd_acc/  (PDD Acc Apply node)

Optional (bypassed by default)
LoRA   h3-realism-people-t2v-i2v-r2v.safetensors (trigger: r34l1sm, strength 1.0) — photo references only
```

## Custom nodes

Everything else is ComfyUI core (**0.34 or newer** — the MiniMax H3, TextGenerate, Switch and Resolution Selector nodes are core nodes and do not exist in older builds).

| Node pack | Nodes used | Where |
|---|---|---|
| [ComfyUI-RMBG](https://github.com/1038lab/ComfyUI-RMBG) (1038lab) | `RMBG`, `SAM3Segment`, `ClothesSegment` | Stage 1 face / outfit cut-out |
| [rgthree-comfy](https://github.com/rgthree/rgthree-comfy) | `Fast Groups Muter` | Stage 2 ON/OFF switch |
| [toobusy](https://github.com/nicekriss/toobusy) (nicekriss) · **0.4.10, commit `bdbed644`** (statically verified build; 0.4.9 adds the nodes, 0.4.10 fixes an optional-dependency import that could block them) | `ToobusyMiniMaxH3ImageLatent`, `ToobusyMiniMaxH3SemanticReference` | H3 T=1 image latent, optional-reference gates |
| [ComfyUI-MiniMax-H3-PDD-Acc](https://github.com/Jalen-Brunson/ComfyUI-MiniMax-H3-PDD-Acc) (Jalen-Brunson) | `MiniMaxH3PDDAccApply` | 8-step accelerator. LoRA file goes in `models/pdd_acc/`, download from [alibaba-pai/MiniMax-H3-Acc-LoRAs](https://huggingface.co/alibaba-pai/MiniMax-H3-Acc-LoRAs) |
| [ComfyUI-KJNodes](https://github.com/kijai/ComfyUI-KJNodes) (kijai) | `ImageConcanate` | Stage 2 final composite only |
| [ComfyUI-Custom-Scripts](https://github.com/pythongosssss/ComfyUI-Custom-Scripts) (pysssss) | `MathExpression` | Stage 2 final composite only |

Node pack ids inside the JSON were corrected in v1.3.1 (`comfyui-rmbg`, `comfyui-kjnodes`, `comfyui-custom-scripts`, `toobusy`, `rgthree-comfy`; the PDD pack is referenced by `aux_id` because it is not in the registry), so ComfyUI-Manager's "Install Missing Custom Nodes" should resolve them. rgthree must be recent enough to toggle nodes inside subgraphs.

## Usage

1. Drag the JSON into ComfyUI to load it
2. Upload a face image to `Stage 1 REQUIRED 1` and an outfit image to `Stage 1 REQUIRED 2`
3. Run → the 3-view sheet is saved to `output/charsheet/`

## FAQ

**Can I give it a pose reference (photo or OpenPose) and generate the character in that pose?**
Yes, that is what Stage 2 does. Drop the pose image into `Stage 2 Pose Reference Source` (group ⑦) and flip `STAGE2_SWITCH` on. Gemma reads the pose and writes a `POSE TRANSFER` block (torso lean, arm / leg angles, head direction, which limb is closer to the camera), and Panel 1 reproduces it. The pose image itself is never fed to H3, so the pose photo's face, body and outfit cannot leak into your character.

- An OpenPose skeleton works, since Gemma just describes what it sees, but a photo, a 3D mannequin render or a posed figure usually gives a more accurate description than a stick figure.
- H3 Ref2VA has no ControlNet, so this is prompt-guided pose transfer, not pixel-exact. If it drifts, type a correction into `Stage 2 Pose Request · Manual Override`; that text outranks the automatic analysis.
- One pose reference per run, applied to Panel 1. Panels 2–4 are defined by text in group ⑧ (e.g. `Panel 2: crouching, weapon in both hands`).
- For a sprite sheet with many poses, run Stage 2 once per pose. Seeds are fixed and the same Stage 1 sheet is the reference every time, so the character stays consistent across runs. Assemble the frames outside ComfyUI. This makes stills, not pixel-registered animation frames.
- Feeding the pose image to H3 directly is deliberately not wired: identity bleed from the pose photo is a real risk, and the experimental input was removed in v1.3.2.

**Nodes show up red / Manager wants to install something odd.**
- Update ComfyUI first. `MiniMaxH3ReferenceToVideo`, `TextGenerate`, `Switch`, `Resolution Selector` and subgraphs are core nodes that need 0.34 or newer; a "missing node" on those is a version problem, not a missing pack.
- Install the six packs in the table above (Manager → Install Missing Custom Nodes).
- Nodes 2.0 (the new Vue node renderer, `Comfy.VueNodes.Enabled`) is optional. The workflow was built and laid out on the classic canvas; if a custom node's widgets look wrong or a switch does not toggle, turn Nodes 2.0 off in Settings → Lite Graph and reload.
- The SAM3 and SegFormer weights for the cut-out nodes download themselves on the first Queue.
- The PDD accelerator LoRA goes in `models/pdd_acc/` (see the table). Without it, flip **Sigmas Source** in ④ to ON: the PDD node is skipped and a 30-step BasicScheduler runs for both stages.

---

# 한국어

얼굴 참조 이미지와 의상 참조 이미지를 넣으면 **3-뷰(정면/측면/후면) 캐릭터 시트**를 만들어 주는 ComfyUI 워크플로우입니다. MiniMax-H3 Ref2VA 기반.

> 원작 워크플로우: **너바베** — [로컬 일관성 끝판왕 · 미니맥스 H3로 캐릭터 시트 만들기 | ComfyUI 워크플로우](https://www.youtube.com/watch?v=nsvAbax4jng)  
> 이 레포는 수정본입니다 (sain2d).

## 결과 예시

| 얼굴 참조 | 의상 참조 |
|:---:|:---:|
| <img src="asset/face_ref.png" width="300"> | <img src="asset/clothes_ref.png" width="300"> |

⬇️

![3-view character sheet](asset/H3_2STAGE_STAGE1_3VIEW_00072_.png)

얼굴 참조에서 **인물 정체성(이목구비·헤어)** 을, 의상 참조에서 **옷만** 가져와 하나의 캐릭터로 합성합니다.

## 파일

| 파일 | 설명 |
|---|---|
| `260903_H3_character_sheet(sain2d_modified)_v1.3.2_KOR.json` | **v1.3.2** 워크플로우 (한글 UI) — ENG 파일에서 생성 |
| `260903_H3_character_sheet(sain2d_modified)_v1.3.2_ENG.json` | **v1.3.2** 워크플로우 (영문 UI) — 원본 파일 |
| `old/` | v1.2, v1.3, v1.3.1 워크플로우, 참고용 보관 |
| `tools/` | `validate_workflow.py` (CI 정적 검사), `build_kor.py` + `kor_overlay.json` (KOR 생성기), `upgrade_v131.py` / `upgrade_v132.py` (버전 변환), `tidy_layout.py` (결정적 노드 정렬: 그룹 안에서 흐름 깊이별 한 행, 그룹은 겹침 없이 재배치), `render_layout.py` (레이아웃 PNG 미리보기, Pillow 필요) |
| `TESTING.md` | 정적 CI 결과와 수동 ComfyUI 실행 테스트 기록을 분리해 관리 |
| `asset/` | 예시 참조 이미지 및 결과물 (시연용이며 예시 그림의 권리는 원저작자에게 있습니다) |

예시를 재현하려면 `asset/face_ref.png`, `asset/clothes_ref.png`를 ComfyUI `input/` 폴더에 복사하세요. 1단계 로더가 기본으로 이 파일명을 가리킵니다.

## v1.3.2 변경점 (2026-09-03)

v1.3.1 2차 리뷰 반영 릴리스 강화와, 의상·양말·신발이 참조와 달라지는 문제 수정 2건.

- **발 부분이 달라지던 이유.** SegFormer에 양말 클래스가 없고, 마스크를 1024×1024로 찌그러뜨려 계산하며, 프롬프트가 신발을 텍스트로 지정하지 않아 양말·신발이 회색 위 몇 픽셀에만 의존했습니다. 또 ③ 칸이 비어도 Gemma 번역이 실행되어 그 출력이 "입은 것 전부"를 바꿀 수 있는 최우선 사용자 지시 아래에 붙었습니다.
- **Gemma 의상 설명.** Gemma가 의상 추출 결과를 읽어 `WARDROBE DESCRIPTION:`(옷·양말·신발)을 쓰고, 주체 정의 뒤에 삽입합니다. 스위치는 ⑨, 미리보기는 ③. 기본 ON.
- **빈 입력 게이트.** ③·⑧ 칸이 비어 있으면 번역 노드를 건너뛰고(lazy 스위치) 빈 문자열을 붙입니다.
- **시그마 소스 스위치.** OFF = PDD 가속 8스텝(기본), ON = 패치 없는 모델 + BasicScheduler 30스텝. 1단계 샘플러와 2단계 서브그래프가 같은 스위치를 씁니다. PDD 파일 없이도 1단계 실행 가능.
- **안정 경로만 유지.** 실험적 `pose_or_extra_ref` 서브그래프 입력 제거. 4패널 체형 고정 문구는 카메라 거리·스케일 고정을 Shot 2~4에만 적용하도록 수정.
- **고정과 메타데이터.** toobusy를 0.4.10, 커밋 `bdbed644`로 고정(0.4.10에서 선택 의존성 FlashVSR import가 H3 노드까지 막던 문제 수정). 배포·보관 JSON 전부에서 `extra.comfyui_mcp` 제거. 추적되던 바이트코드 삭제, `.gitignore` 추가.
- **검증 확장.** `tools/validate_workflow.py`가 추가로 검사: `comfyui_mcp` 부재(루트와 `old/`), 노드·링크 id 유일성, 서브그래프 인터페이스와 인스턴스 노드 일치, 2단계 레시피, 시그마/모델 선택기 배선, LoRA 파일명, SemanticReference routing = `auto`, toobusy 고정, 루트의 모든 ENG/KOR 쌍. 그리고 **2단계 역할 조립을 27가지 경우**(선택 슬롯별 OFF / ON-안전 / ON-거부)로 시뮬레이션해 H3의 참조 압축과 대조합니다. CI에서는 실제 toobusy 클래스를 사용.
- **실행 증거는 `TESTING.md`에 분리 기록.** v1.3.2는 아직 ComfyUI에서 실행하지 않았고, 정적 검사만 통과한 상태입니다.

## v1.3.1 변경점 (2026-09-03)

v1.3 외부 리뷰 반영 핫픽스. 성인 캐릭터 전용이며 프롬프트의 `adult`는 의도된 고정값입니다.

- **2단계 `<Picture N>` 번호를 동적으로 부여.** ComfyUI H3 노드는 빈 참조 슬롯을 건너뛰고 남은 이미지에 순서대로 번호를 붙입니다. 소품 스위치가 OFF면 배경 이미지는 실제로 `<Picture 2>`인데 프롬프트는 `<Picture 3>`이라고 적혀 있었습니다. 이제 각 선택 역할 문장의 태그는 Gemma의 `VISUAL_REFERENCE: YES` 판정에 대한 Regex 게이트와 스위치 상태로 계산되어 H3가 보는 번호와 항상 일치합니다. 켜져 있지만 Gemma가 거부한 참조는 텍스트 설명만 남고 태그가 붙지 않습니다.
- **named 위젯값 재동기화.** v1.3은 `widgets_values`만 바꾸고 `widgets_values_named` 사본(옛 `adult woman` 프롬프트, `흰 발목 양말` 테스트 입력, 옛 2x3 프롬프트)을 남겨 두었습니다. ComfyUI는 둘 중 어느 쪽으로도 복원할 수 있으므로 둘을 일치시켰고, 다시 어긋나면 CI가 실패합니다.
- **대체 스위치.** 미리보기 아래에 얼굴 소스(SAM3 크롭 / 원본 사진), 의상 소스(의상 추출 / 배경 제거 사진) 스위치 추가. 미리보기는 H3에 실제 입력되는 이미지를 보여줍니다.
- **시트 구성 스위치.** OFF = 검증된 3뷰 턴어라운드, ON = 실험적 4패널(상반신 클로즈업 + 전/측/후면). 4패널 프롬프트는 아직 실행해 보지 않았습니다.
- **모델 안내 통일.** 캔버스 노트가 로더와 같은 INT8 Qwen 인코더를 기본으로 안내(NVFP4는 경량 대안)하고, PDD 가속기의 실제 저장소와 `models/pdd_acc/` 폴더, 올바른 리얼리즘 LoRA 파일명을 표기합니다.
- **정리.** 프롬프트에서 `ethnicity` 제거, attention/scheduler/LoRA 노드 제목 수정, 서브그래프 이름을 `Stage 2 Pose Sheet Generator`로, `pose_or_extra_ref`는 실험적으로 표기, 노드팩 id 교정(`comfyui-rmbg`, `comfyui-kjnodes`, `comfyui-custom-scripts`, `toobusy`, `rgthree-comfy`, PDD는 `aux_id`), `extra.sain2d_workflow`에 v1.3.1 메타데이터 추가.
- **KOR는 수작업이 아니라 생성.** `tools/build_kor.py`가 ENG 파일에 한글 제목·노트를 덮어씌우며, CI가 재생성해 차이가 있으면 실패합니다.
- **CI.** `.github/workflows/validate.yml`이 `tools/validate_workflow.py`를 실행: 링크 무결성, named/positional 위젯 일치, KOR/ENG 기능 동등성, 금지 잔재, PDD 레시피(euler / 8스텝 / shift 12·3 / BasicGuider), Picture 태그 게이트, 로더·노트·README 모델명 일치.

## v1.3 변경점 (2026-09-03)

v1.2 그래프 검토 후 캐릭터 일관성 위주로 수정했습니다.

- **성별 중립 정체성 역할.** 1단계 프롬프트에 박혀 있던 `adult woman`을 제거하고, 성별·나이·인종을 얼굴 참조에서 읽도록 변경.
- **그림체를 얼굴 참조에 맞춤.** `photorealistic studio photography` 강제를 제거하고, 참조의 스타일(실사/일러스트/애니)을 그대로 따르도록 지시. 애니 참조가 실사 쪽으로 밀리는 현상 방지.
- **프롬프트 섹션 순서 수정.** `overall_soundscape` / `non_diegetic_music` 블록을 사용자 지시 뒤, 프롬프트 맨 끝에 붙이도록 변경 (2단계와 동일한 방식).
- **2단계가 3뷰 전체를 참조.** 기존에는 정면 크롭만 넣으면서 프롬프트는 "turnaround 결과"라고 설명해 불일치가 있었습니다. 이제 전/측/후면 시트 전체를 Picture 1로 전달해 머리·의상을 모든 각도에서 참조합니다.
- **스타일 LoRA를 선택 사항으로 표기.** "4-Step Turbo LoRA"로 표시된 로더에 실제로는 리얼리즘 LoRA가 들어 있었고 바이패스 상태였습니다. 선택 사항으로 표기하고 바이패스 유지. 가속은 8-step PDD 가속기가 담당합니다. 애니/일러스트 참조에는 OFF를 유지하세요.
- **테스트 입력값 제거.** ENG 파일의 1단계 지시 칸에 `흰 발목 양말, 신발 없음`이 남아 있어 모든 실행에서 신발이 사라졌고, KOR 파일에는 패널 3 요청, H3 노드에는 무관한 옛 프롬프트가 남아 있었습니다. 모두 비우고 이미지 로더는 중립 파일명으로 교체.
- **안내 추가.** 의상 사진에 신발 두 짝과 팔 두 개가 보여야 하며, 모자·선글라스·가방은 의상 추출 노드에서 켜지 않으면 빠집니다.

## 동작 방식

**Stage 1 — 3-뷰 시트 생성**
- 얼굴 이미지 → `SAM3Segment`로 머리만 추출
- 의상 이미지 → `RMBG`로 배경 제거 후 `ClothesSegment`(SegFormer)로 옷만 추출 (얼굴·머리·팔다리 자동 제거)
- 두 참조를 H3에 물려 정면/측면/후면 3-뷰 시트 출력

**Stage 2 — 포즈 전개 (선택)**
- Stage 1 시트 + 포즈 참조(Gemma가 텍스트로만 분석하므로 포즈 사진의 인물이 섞이지 않음)로 1~4 패널 생성
- 선택 입력: 소품/무기, 배경/환경, 추가 액세서리

## 필요 모델

```
UNET   minimax_h3_ref2va_pruned_int8_convrot.safetensors
CLIP   qwen3vl_32b_minimax_h3_int8_convrot.safetensors   (~27 GB; qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors ~16 GB is a smaller alternative, select it in the loader)
       gemma4_e4b_it_fp8_scaled.safetensors
VAE    minimax_h3_t1_image_vae_step1597.safetensors
       minimax_h3_audio_vae_fp32.safetensors
Accel  MiniMax-H3-Ref2VA-Acc-8Step.safetensors  → models/pdd_acc/  (PDD Acc Apply 노드)

선택 (기본 바이패스)
LoRA   h3-realism-people-t2v-i2v-r2v.safetensors (trigger: r34l1sm, 강도 1.0) — 실사 참조 전용
```

## 커스텀 노드

나머지는 모두 ComfyUI 코어 노드입니다 (**0.34 이상** 필요 — MiniMax H3, TextGenerate, Switch, Resolution Selector 노드가 코어에 포함된 버전).

| 노드팩 | 사용 노드 | 위치 |
|---|---|---|
| [ComfyUI-RMBG](https://github.com/1038lab/ComfyUI-RMBG) (1038lab) | `RMBG`, `SAM3Segment`, `ClothesSegment` | 1단계 얼굴/의상 추출 |
| [rgthree-comfy](https://github.com/rgthree/rgthree-comfy) | `Fast Groups Muter` | 2단계 ON/OFF 스위치 |
| [toobusy](https://github.com/nicekriss/toobusy) (nicekriss) · **0.4.10, 커밋 `bdbed644`** (정적 검증 기준 빌드; 0.4.9에서 노드 추가, 0.4.10에서 선택 의존성 import 문제 수정) | `ToobusyMiniMaxH3ImageLatent`, `ToobusyMiniMaxH3SemanticReference` | H3 T=1 이미지 latent, 선택 참조 게이트 |
| [ComfyUI-MiniMax-H3-PDD-Acc](https://github.com/Jalen-Brunson/ComfyUI-MiniMax-H3-PDD-Acc) (Jalen-Brunson) | `MiniMaxH3PDDAccApply` | 8-step 가속기. LoRA 파일은 `models/pdd_acc/`에, 다운로드는 [alibaba-pai/MiniMax-H3-Acc-LoRAs](https://huggingface.co/alibaba-pai/MiniMax-H3-Acc-LoRAs) |
| [ComfyUI-KJNodes](https://github.com/kijai/ComfyUI-KJNodes) (kijai) | `ImageConcanate` | 2단계 최종 합성 전용 |
| [ComfyUI-Custom-Scripts](https://github.com/pythongosssss/ComfyUI-Custom-Scripts) (pysssss) | `MathExpression` | 2단계 최종 합성 전용 |

v1.3.1에서 JSON 안의 노드팩 id를 교정했습니다(`comfyui-rmbg`, `comfyui-kjnodes`, `comfyui-custom-scripts`, `toobusy`, `rgthree-comfy`, PDD 팩은 레지스트리에 없어 `aux_id`로 참조). ComfyUI-Manager의 "Install Missing Custom Nodes"로 해결되어야 합니다. rgthree는 서브그래프 내부 노드를 토글할 수 있는 최신 버전이어야 합니다.

## 사용법

1. ComfyUI에 JSON을 드래그해서 로드
2. `1단계 필수 1` 에 얼굴 이미지, `1단계 필수 2` 에 의상 이미지 업로드
3. 실행 → `output/charsheet/` 에 3-뷰 시트 저장

## 자주 묻는 질문

**포즈 참조(사진이나 OpenPose)를 넣고 그 포즈로 생성할 수 있나요?**
네, 2단계가 그 역할입니다. `2단계 포즈 분석 원본`(⑦ 그룹)에 포즈 이미지를 넣고 `STAGE2_SWITCH`를 ON으로 켜세요. Gemma가 포즈를 읽어 `POSE TRANSFER` 블록(상체 기울기, 팔·다리 각도, 머리 방향, 카메라에 가까운 팔다리)을 쓰고, 패널 1이 그 포즈를 재현합니다. 포즈 이미지 자체는 H3에 들어가지 않으므로 포즈 사진의 얼굴·몸·옷이 캐릭터에 섞이지 않습니다.

- OpenPose 스켈레톤도 됩니다. Gemma가 보이는 대로 설명하기 때문입니다. 다만 사진, 3D 마네킹 렌더, 포즈 잡은 피규어가 막대 그림보다 정확하게 읽힙니다.
- H3 Ref2VA에는 ControlNet이 없어서 프롬프트 기반 포즈 전달입니다. 픽셀 단위로 맞지는 않습니다. 틀어지면 `2단계 포즈 요청 · 수동 덮어쓰기` 칸에 수정 문구를 적으세요. 그 텍스트가 자동 분석보다 우선합니다.
- 실행 1회에 포즈 참조 1개, 패널 1에 적용됩니다. 패널 2~4는 ⑧ 그룹에 텍스트로 지정합니다 (예: `패널 2: 웅크린 자세, 양손으로 무기`).
- 포즈가 많은 스프라이트 시트는 포즈마다 2단계를 한 번씩 돌리세요. 시드가 고정이고 매번 같은 1단계 시트를 참조하므로 실행 간 캐릭터가 유지됩니다. 프레임 조립은 ComfyUI 밖에서 하세요. 정지 이미지를 만드는 도구이지 픽셀 정렬된 애니메이션 프레임을 만들지는 않습니다.
- 포즈 이미지를 H3에 직접 넣는 경로는 일부러 연결하지 않았습니다. 포즈 사진의 정체성이 섞일 위험이 커서 실험적 입력을 v1.3.2에서 제거했습니다.

**노드가 빨갛게 뜨거나 Manager가 이상한 팩을 설치하려고 합니다.**
- ComfyUI부터 업데이트하세요. `MiniMaxH3ReferenceToVideo`, `TextGenerate`, `Switch`, `Resolution Selector`, 서브그래프는 0.34 이상이 필요한 코어 노드입니다. 이 노드들의 "missing node"는 버전 문제이지 팩 누락이 아닙니다.
- 위 표의 팩 6개를 설치하세요 (Manager → Install Missing Custom Nodes).
- Nodes 2.0(새 Vue 노드 렌더러, `Comfy.VueNodes.Enabled`)은 선택 사항입니다. 이 워크플로우는 기존 캔버스에서 만들고 배치했으므로, 커스텀 노드 위젯이 이상하게 보이거나 스위치가 안 바뀌면 설정 → Lite Graph에서 Nodes 2.0을 끄고 다시 로드하세요.
- 추출 노드용 SAM3·SegFormer 가중치는 첫 Queue 때 자동으로 받습니다.
- PDD 가속기 LoRA는 `models/pdd_acc/`에 넣습니다 (표 참고). 없으면 ④의 **시그마 소스**를 ON으로 바꾸세요. PDD 노드를 건너뛰고 두 단계 모두 30스텝 BasicScheduler로 돌아갑니다.
