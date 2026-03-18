# Phase 4: Image Editing Model Analysis for Game Development

**Date**: 2026-03-17 to 2026-03-18
**Hardware**: RTX 5090 (32GB VRAM), CUDA 12.8
**Reference Characters**: Clover and Sable (Neko Cafe) — turnaround sheets
**Test Suite**: 6 expressions, 3 scene/outfit edits, 2 CG scenes, 3 multi-character scenes

---

## Models Tested

### 1. Qwen-Image-Edit-2511 (via ComfyUI FP8) — **Selected for production**
- **Model**: `Qwen/Qwen-Image-Edit-2511`
- **Runtime**: ComfyUI headless server with FP8 (e4m3fn) quantized weights
- **Model files**: `drbaph/Qwen-Image-Edit-2511-FP8` (diffusion), `Comfy-Org/HunyuanVideo_1.5_repackaged` (text encoder), `Comfy-Org/Qwen-Image_ComfyUI` (VAE)
- **VRAM**: ~20GB with FP8
- **Speed**: ~50s/image (20 steps)
- **License**: Apache 2.0
- **Single-character results**: 8/11 succeeded (3 had polling timing issues, not model failures)
- **Multi-character results**: 3/3 succeeded

### 2. LongCat-Image-Edit-Turbo — **Runner-up for single-character CGs**
- **HuggingFace**: `meituan-longcat/LongCat-Image-Edit-Turbo`
- **Pipeline**: `LongCatImageEditPipeline` (diffusers native)
- **Quantization**: bf16 (fits without quantization)
- **VRAM**: ~18GB peak with CPU offload
- **Speed**: ~33s/image (8 steps)
- **License**: Apache 2.0
- **Single-character results**: 11/11 succeeded
- **Multi-character results**: 3/3 succeeded (but with artifacts)

### 3. FLUX.1 Kontext (dev) — NF4 Quantized
- **HuggingFace**: `black-forest-labs/FLUX.1-Kontext-dev`
- **Pipeline**: `FluxKontextPipeline` (diffusers native)
- **Quantization**: NF4 via BitsAndBytes
- **VRAM**: ~12GB peak
- **Speed**: ~35s/image (24 steps)
- **License**: Non-commercial model weights
- **Single-character results**: 11/11 succeeded
- **Multi-character results**: 3/3 succeeded

### 4. OmniGen2
- **HuggingFace**: `OmniGen2/OmniGen2`
- **Pipeline**: Custom (requires dedicated venv due to dependency conflicts)
- **VRAM**: ~20GB with CPU offload
- **Speed**: ~38s/image (30 steps)
- **License**: Apache 2.0
- **Single-character results**: 11/11 succeeded
- **Multi-character results**: 3/3 succeeded

### 5. IP-Adapter Plus + SDXL
- **HuggingFace**: `h94/IP-Adapter` + `stabilityai/stable-diffusion-xl-base-1.0`
- **Speed**: ~3s/image
- **License**: Apache 2.0
- **Results**: 9/9 succeeded but weak identity preservation — generates "inspired by" rather than editing

### 6. SDXL Inpainting
- **Results**: 4/4 succeeded but minimal expression changes. Not viable for this workflow.

---

## Final Rankings (Human-Evaluated)

### Single-Character Expression Sprites

| Criterion | Qwen (ComfyUI) | LongCat | Kontext | OmniGen2 |
|-----------|----------------|---------|---------|----------|
| **Body stability across expressions** | Best — body doesn't move | Good | Good features but misaligned between edits | Good |
| **Expression quality** | Adequate but stiff | Most natural for anime style | Distinct but subtle | Slightly uncanny |
| **Art style match to reference** | Excellent | Excellent (slight color drift) | Excellent | Slightly off |
| **Production readiness** | 9/10 | 8/10 | 6/10 (alignment issues) | 5/10 |

### Single-Character CG Scenes

| Criterion | Qwen (ComfyUI) | LongCat | Kontext | OmniGen2 |
|-----------|----------------|---------|---------|----------|
| **Composition** | Excellent | Best — cinematic, natural | Plain | Good |
| **Atmosphere/lighting** | Excellent | Excellent — cozy, lived-in | Adequate | Good |
| **Character fidelity** | Excellent | Very good (slight color drift) | Excellent | Good (loses calico hair split) |
| **Production readiness** | 9/10 | 9/10 | 6/10 | 5/10 |

### Multi-Character Scenes (Clover + Sable)

| Criterion | Qwen (ComfyUI) | Kontext | OmniGen2 | LongCat |
|-----------|----------------|---------|----------|---------|
| **Character distinction** | Both clearly recognizable | Both recognizable | Both recognizable | Both recognizable |
| **Skin color accuracy (Sable)** | Too dark (fixable with prompting) | Inconsistent between images | Closest to reference | Best retention |
| **Character interaction** | Best — natural body language | Characters feel separate | Adequate | Adequate |
| **Stability** | Excellent | Good | Good | Artifacts and logical errors |
| **Production readiness** | 8/10 | 6/10 | 5/10 | 4/10 |

---

## Key Findings

### 1. Qwen-Image-Edit is the best all-rounder for VN asset production
Strongest body stability (critical for expression sprites that won't feel jarring when swapped), excellent scene compositions, and native multi-image reference support. Requires ComfyUI with FP8 weights — does not run well through diffusers alone.

### 2. LongCat is the runner-up for single-character work
Produces the most natural-feeling expressions for anime style and the best CG compositions. Its weakness is slight color/texture drift between generations and instability with multi-character scenes (artifacts, logical errors). Best used for single-character CGs where composition matters most.

### 3. FLUX Kontext preserves features but not alignment
While Kontext keeps character features (calico ears, hair split, outfit) very well, the body shifts position between expression edits. This makes it unsuitable for VN expression sprites where consistency frame-to-frame is critical. CG scenes are competent but plain compared to Qwen/LongCat.

### 4. OmniGen2 has an uncanny quality
Despite good technical metrics, the outputs have a subtly "off" feel — slightly wrong proportions, overly clean line art. This is a subjective but consistent human observation across all tests.

### 5. Skin color drift is solvable with prompt engineering
Qwen consistently darkened Sable's skin when prompted with relative terms like "darker skin." Testing showed:
- **"darker skin"** → too dark (model over-interprets)
- **No skin description** → closest to reference (let the image speak)
- **"light brown skin"** → also close to reference
- **"slightly warmer than the first"** → still too dark

**Rule**: Avoid relative skin descriptions. Either omit skin color entirely or use specific neutral terms. The reference image alone provides sufficient guidance.

---

## Recommended Production Workflow for Neko Cafe

### Primary: Qwen-Image-Edit-2511 via ComfyUI (FP8)
- **Expression sprites**: Feed front-view crop, describe only the expression change. ~50s/image.
- **CG event scenes**: Feed character reference(s), describe the scene. ~50-75s/image.
- **Multi-character scenes**: Use image1 + image2 inputs. Avoid relative skin descriptions.
- **Prompting guidelines**: Be specific about what to change, don't describe features the reference already shows (especially skin color). Let the reference images do the heavy lifting.

### Secondary: LongCat-Image-Edit-Turbo via diffusers
- **Single-character CGs**: When composition and atmosphere matter most and Qwen's output feels too stiff.
- **Not recommended for**: Multi-character scenes, expression sprite sheets.

### Infrastructure
- ComfyUI runs as a headless server at localhost:8188
- Workflows submitted via REST API (Python client scripts)
- Model files: 3 symlinked safetensors (~29GB total download)

---

## Technical Notes

### Qwen-Image-Edit Memory Profile
- Transformer: 40.9 GB (bf16), ~20 GB (FP8) — runs 20-40x per image
- Text Encoder (Qwen2.5-VL 7B): 16.6 GB (bf16), ~8.8 GB (FP8)
- VAE: 0.25 GB
- **FP8 via ComfyUI**: ~20GB VRAM, 50s/image — the only viable approach on 32GB
- **NF4 via diffusers**: fits in VRAM but produces heavy noise artifacts
- **bf16 via diffusers**: 57.8GB, requires CPU offloading → 25 min/image (unusable)

### ComfyUI Workflow Structure (Qwen-Image-Edit)
The workflow follows this node chain:
1. `CLIPLoader` (type: `qwen_image`) → text encoder
2. `UNETLoader` (weight_dtype: `fp8_e4m3fn`) → diffusion model
3. `VAELoader` → VAE
4. `ModelSamplingAuraFlow` (shift: 3.1) → sampling config
5. `CFGNorm` (strength: 1.0) → classifier-free guidance normalization
6. `TextEncodeQwenImageEditPlus` → encode prompt + reference images
7. `FluxKontextMultiReferenceLatentMethod` (index_timestep_zero) → reference latent handling
8. `KSampler` (steps: 20, cfg: 4.0, euler/simple) → diffusion
9. `VAEDecode` → latent to pixels

### OmniGen2 Dependency Isolation
OmniGen2's requirements.txt pins `torch==2.6.0` and `transformers==4.51.3`, which breaks other models. Must use a dedicated venv at `/workspace/OmniGen2/.venv/`.

### IP-Adapter SDXL Gotcha
The Plus ViT-H weights require the image encoder from `models/image_encoder`, NOT `sdxl_models/image_encoder`. Must explicitly load `CLIPVisionModelWithProjection` with `subfolder="models/image_encoder"`.
