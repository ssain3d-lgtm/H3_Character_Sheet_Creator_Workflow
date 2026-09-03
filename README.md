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
| `260903_H3_character_sheet(sain2d_modified)_KOR.json` | **v1.3** workflow (Korean UI) |
| `260903_H3_character_sheet(sain2d_modified)_ENG.json` | **v1.3** workflow (English UI) |
| `old/` | Previous v1.2 workflows (2026-09-01), kept for reference |
| `asset/` | Sample reference images and output |

To reproduce the example, copy `asset/face_ref.png` and `asset/clothes_ref.png` into your ComfyUI `input/` folder; the Stage 1 loaders point to those names by default.

## What changed in v1.3 (2026-09-03)

Consistency-focused fixes after a review of the v1.2 graph.

- **Gender-neutral identity role.** The Stage 1 prompt no longer hard-codes `adult woman`; gender presentation, age and ethnicity are read from the face reference.
- **Rendering style follows the face reference.** `photorealistic studio photography` was removed. The prompt now tells H3 to match the reference style (photo / illustration / anime) instead of pulling anime references toward photorealism.
- **Prompt section order fixed.** The `overall_soundscape` / `non_diegetic_music` block is appended after the user direction, at the very end of the Stage 1 prompt, the same way Stage 2 already did.
- **Stage 2 sees the whole turnaround.** Stage 2 used a crop of the front view only, while its prompt described the input as the full turnaround. The front / side / back sheet is now passed as Picture 1, so hair and costume are known from every angle.
- **Style LoRA marked optional.** The loader labelled "4-Step Turbo LoRA" actually held a realism LoRA and was bypassed. It is now labelled optional and stays bypassed; acceleration comes from the 8-step PDD accelerator. Keep it OFF for anime / illustrated references.
- **Leftover test inputs cleared.** The ENG file shipped with `흰 발목 양말, 신발 없음` in the Stage 1 direction box (it silently removed shoes from every run), the KOR file with a panel-3 request, and the H3 node with an unrelated stale prompt. All cleared; image loaders point to neutral placeholder names.
- **Guidance added.** The outfit photo must show both shoes and both arms; hats / sunglasses / bags are dropped unless enabled on the Extract Clothes Only node.

Untested by the author in ComfyUI at the time of writing: the Stage 2 full-sheet reference is a prompt/graph-level change and should be checked on one Stage 2 run.

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
CLIP   qwen3vl_32b_minimax_h3_int8_convrot.safetensors
       gemma4_e4b_it_fp8_scaled.safetensors
VAE    minimax_h3_t1_image_vae_step1597.safetensors
       minimax_h3_audio_vae_fp32.safetensors
Accel  MiniMax-H3-Ref2VA-Acc-8Step.safetensors  (PDD Acc Apply node)

Optional (bypassed by default)
LoRA   any H3 style LoRA, e.g. h3-realism-people-t2v-i2v-r2v (trigger: r34l1sm) — photo references only
```

Custom nodes: ComfyUI-RMBG (RMBG, SAM3Segment, ClothesSegment), rgthree, Toobusy H3 node pack

## Usage

1. Drag the JSON into ComfyUI to load it
2. Upload a face image to `Stage 1 REQUIRED 1` and an outfit image to `Stage 1 REQUIRED 2`
3. Run → the 3-view sheet is saved to `output/charsheet/`

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
| `260903_H3_character_sheet(sain2d_modified)_KOR.json` | **v1.3** 워크플로우 (한글 UI) |
| `260903_H3_character_sheet(sain2d_modified)_ENG.json` | **v1.3** 워크플로우 (영문 UI) |
| `old/` | 이전 v1.2 워크플로우 (2026-09-01), 참고용 보관 |
| `asset/` | 예시 참조 이미지 및 결과물 |

예시를 재현하려면 `asset/face_ref.png`, `asset/clothes_ref.png`를 ComfyUI `input/` 폴더에 복사하세요. 1단계 로더가 기본으로 이 파일명을 가리킵니다.

## v1.3 변경점 (2026-09-03)

v1.2 그래프 검토 후 캐릭터 일관성 위주로 수정했습니다.

- **성별 중립 정체성 역할.** 1단계 프롬프트에 박혀 있던 `adult woman`을 제거하고, 성별·나이·인종을 얼굴 참조에서 읽도록 변경.
- **그림체를 얼굴 참조에 맞춤.** `photorealistic studio photography` 강제를 제거하고, 참조의 스타일(실사/일러스트/애니)을 그대로 따르도록 지시. 애니 참조가 실사 쪽으로 밀리는 현상 방지.
- **프롬프트 섹션 순서 수정.** `overall_soundscape` / `non_diegetic_music` 블록을 사용자 지시 뒤, 프롬프트 맨 끝에 붙이도록 변경 (2단계와 동일한 방식).
- **2단계가 3뷰 전체를 참조.** 기존에는 정면 크롭만 넣으면서 프롬프트는 "turnaround 결과"라고 설명해 불일치가 있었습니다. 이제 전/측/후면 시트 전체를 Picture 1로 전달해 머리·의상을 모든 각도에서 참조합니다.
- **스타일 LoRA를 선택 사항으로 표기.** "4-Step Turbo LoRA"로 표시된 로더에 실제로는 리얼리즘 LoRA가 들어 있었고 바이패스 상태였습니다. 선택 사항으로 표기하고 바이패스 유지. 가속은 8-step PDD 가속기가 담당합니다. 애니/일러스트 참조에는 OFF를 유지하세요.
- **테스트 입력값 제거.** ENG 파일의 1단계 지시 칸에 `흰 발목 양말, 신발 없음`이 남아 있어 모든 실행에서 신발이 사라졌고, KOR 파일에는 패널 3 요청, H3 노드에는 무관한 옛 프롬프트가 남아 있었습니다. 모두 비우고 이미지 로더는 중립 파일명으로 교체.
- **안내 추가.** 의상 사진에 신발 두 짝과 팔 두 개가 보여야 하며, 모자·선글라스·가방은 의상 추출 노드에서 켜지 않으면 빠집니다.

작성 시점에 ComfyUI에서 실행 검증하지 않은 항목: 2단계 3뷰 전체 참조는 그래프·프롬프트 수준 변경이므로 2단계 1회 실행으로 확인을 권합니다.

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
CLIP   qwen3vl_32b_minimax_h3_int8_convrot.safetensors
       gemma4_e4b_it_fp8_scaled.safetensors
VAE    minimax_h3_t1_image_vae_step1597.safetensors
       minimax_h3_audio_vae_fp32.safetensors
Accel  MiniMax-H3-Ref2VA-Acc-8Step.safetensors  (PDD Acc Apply 노드)

선택 (기본 바이패스)
LoRA   H3 스타일 LoRA, 예: h3-realism-people-t2v-i2v-r2v (trigger: r34l1sm) — 실사 참조 전용
```

커스텀 노드: ComfyUI-RMBG (RMBG, SAM3Segment, ClothesSegment), rgthree, Toobusy H3 노드팩

## 사용법

1. ComfyUI에 JSON을 드래그해서 로드
2. `1단계 필수 1` 에 얼굴 이미지, `1단계 필수 2` 에 의상 이미지 업로드
3. 실행 → `output/charsheet/` 에 3-뷰 시트 저장
