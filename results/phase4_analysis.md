# Phase 4: Image Editing Model Analysis for Game Development

**Date**: 2026-03-17
**Hardware**: RTX 5090 (32GB VRAM), CUDA 12.8
**Reference Character**: Clover (Neko Cafe) — calico catgirl, turnaround sheet
**Test Suite**: 6 expressions, 3 scene/outfit edits, 2 CG scenes per model

---

## Models Tested

### 1. FLUX.1 Kontext (dev) — NF4 Quantized
- **HuggingFace**: `black-forest-labs/FLUX.1-Kontext-dev`
- **Pipeline**: `FluxKontextPipeline` (diffusers native)
- **Quantization**: NF4 via BitsAndBytes
- **VRAM**: ~12GB peak
- **Speed**: ~33s/image (24 steps)
- **License**: Non-commercial model weights; outputs commercially usable
- **Results**: 11/11 succeeded

### 2. LongCat-Image-Edit-Turbo
- **HuggingFace**: `meituan-longcat/LongCat-Image-Edit-Turbo`
- **Pipeline**: `LongCatImageEditPipeline` (diffusers native)
- **Quantization**: bf16 (fits without quantization)
- **VRAM**: ~18GB peak with CPU offload
- **Speed**: ~33s/image (8 steps)
- **License**: Apache 2.0
- **Results**: 11/11 succeeded

### 3. IP-Adapter Plus + SDXL
- **HuggingFace**: `h94/IP-Adapter` + `stabilityai/stable-diffusion-xl-base-1.0`
- **Pipeline**: `AutoPipelineForText2Image` + IP-Adapter loader
- **Key detail**: Must load ViT-H encoder from `models/image_encoder` (not `sdxl_models/image_encoder`)
- **VRAM**: ~9GB
- **Speed**: ~3s/image (30 steps)
- **License**: Apache 2.0
- **Results**: 9/9 succeeded (expressions + CG single + CG multi)

### 4. SDXL Inpainting
- **HuggingFace**: `diffusers/stable-diffusion-xl-1.0-inpainting-0.1`
- **Pipeline**: `AutoPipelineForInpainting`
- **VRAM**: ~7GB
- **Speed**: ~2s/image
- **License**: Open
- **Results**: 4/4 succeeded (face-only expression edits)

### 5. Qwen-Image-Edit-2511 (Incomplete)
- **HuggingFace**: `Qwen/Qwen-Image-Edit-2511`
- **Status**: Could not run at acceptable speed through diffusers
- **Issue**: 57.8GB model (40.9GB transformer + 16.6GB text encoder). NF4 quantization ran at ~66s/image but produced heavy noise artifacts. FP8 weights exist but require ComfyUI's native FP8 compute infrastructure.
- **Prior testing**: Michael confirmed 30-60s/image via ComfyUI with FP8 (e4m3fn) weights, good quality
- **License**: Apache 2.0
- **Action**: Set up ComfyUI headless server for future testing

### 6. OmniGen2 (Incomplete)
- **HuggingFace**: `OmniGen2/OmniGen2`
- **Status**: Failed due to missing Python.h during CUDA kernel compilation at inference time
- **Issue**: OmniGen2 requires runtime CUDA compilation (custom attention kernels). Environment fix (python3-dev installed) resolved the build error but the model was OOM-killed before producing results during Qwen retries.
- **License**: Apache 2.0
- **Action**: Retry in isolated session

---

## Head-to-Head Comparison

### Expression Editing (Face-Only Changes)

| Criterion | FLUX Kontext | LongCat Turbo | IP-Adapter+SDXL | SDXL Inpaint |
|-----------|-------------|---------------|-----------------|--------------|
| **Expression clarity** | Excellent — distinct, readable | Excellent — more dramatic/exaggerated | Weak — subtle, hard to distinguish | Minimal change |
| **Identity preservation** | Best — near-perfect consistency | Very good — slight variations | Moderate — generates "inspired by" not edits | Good (masked region only) |
| **Outfit/pose consistency** | Perfect — nothing changes except face | Perfect | N/A (generates new image) | Good (outside mask unchanged) |
| **Art style fidelity** | Maintains original style exactly | Maintains style with slight softening | Generates in SDXL style (different from reference) | Generates in SDXL style |
| **Speed** | 33s | 33s | 3s | 2s |

### Scene/Outfit Changes (Larger Edits)

| Criterion | FLUX Kontext | LongCat Turbo |
|-----------|-------------|---------------|
| **Outfit swap quality** | Good — conservative, faithful | Excellent — creative, detailed (plaid scarf, fur trim) |
| **Scene composition** | Good — character centered, clean | Excellent — cinematic framing, atmospheric |
| **Character recognition in scenes** | Excellent — clearly Clover | Very good — recognizable but slightly generic |
| **Background detail** | Good | Excellent — populated, lived-in environments |

### CG Event Scenes

| Criterion | FLUX Kontext | LongCat Turbo | IP-Adapter+SDXL |
|-----------|-------------|---------------|-----------------|
| **Composition** | Good — character-focused | Excellent — full scene, VN-ready | Decent — character with props |
| **Lighting/atmosphere** | Warm, appropriate | Cinematic, professional | Basic |
| **Character fidelity** | Excellent — calico ears, hair split, outfit all correct | Very good — captures the essence | Moderate — general catgirl aesthetic |
| **Multi-character** | Not tested (single-ref model) | Not tested | Attempted — both characters look too similar |
| **VN production readiness** | 7/10 | 9/10 | 4/10 |

---

## Key Findings

### 1. FLUX Kontext is the identity preservation champion
For VN expression sprites where the character MUST look identical across all variants, Kontext is the clear winner. The outfit, pose, hair, ears — everything stays pixel-consistent. Only the face changes. This is exactly what you need for a character sprite sheet.

### 2. LongCat produces the best CG art
For event CGs where you want a beautiful scene with a recognizable character, LongCat's compositions are significantly better. The reading book scene and cafe scenes have professional-quality framing and lighting. If you showed these to someone, they'd believe they came from a visual novel.

### 3. LongCat is more expressive, Kontext is more controlled
LongCat's embarrassed face (visible blushing, closed eyes) and angry face (bared teeth) are more dramatic and VN-appropriate. Kontext's expressions are subtler and more realistic. For anime VN work, LongCat's approach is arguably better.

### 4. IP-Adapter is great for concept exploration
At 3s/image, IP-Adapter is 10x faster than the editing models. It doesn't truly edit — it generates new images using the reference as style guidance. But for quickly exploring "what would this character look like in different situations," it's invaluable. The results are lower fidelity but useful for brainstorming.

### 5. SDXL Inpainting is not viable for this workflow
The base SDXL inpainting model (not anime-trained) barely changes expressions. An anime-specific inpainting model (like AnimagineXL with inpainting) might work better, but the approach is fundamentally limited by mask precision.

### 6. Qwen-Image-Edit remains promising but needs ComfyUI
The dual semantic/appearance path architecture is theoretically ideal for "change expression, keep everything else." Michael's prior ComfyUI testing confirmed good results at 30-60s. The FP8 inference infrastructure in ComfyUI is necessary — diffusers doesn't support native FP8 compute for this model.

---

## Recommended Workflow for Neko Cafe

### Expression Sprite Sheets
**Primary**: FLUX Kontext
- Feed the front-view crop from the turnaround sheet
- Generate 6-8 expressions per character
- ~33s each, full batch of 8 in ~4.5 minutes
- Near-perfect identity consistency across all expressions

### CG Event Scenes
**Primary**: LongCat-Image-Edit-Turbo
- Feed the full turnaround sheet or front crop as reference
- Describe the scene in the prompt
- Produces VN-ready compositions with atmospheric lighting
- Apache 2.0 — fully commercial

### Rapid Concept Exploration
**Primary**: IP-Adapter Plus + SDXL
- 3s/image for quick "what if" iterations
- Use to explore scene compositions, outfit ideas, etc.
- Not for final production — use as reference/storyboard

### Future: Qwen-Image-Edit-2511 (via ComfyUI)
- Set up ComfyUI headless server with FP8 weights
- Best for fine-grained edits where you want precise control over what changes and what doesn't
- Apache 2.0 license is attractive for commercial work

---

## Technical Notes

### IP-Adapter SDXL Gotcha
The Plus ViT-H weights (`ip-adapter-plus_sdxl_vit-h.safetensors`) require the image encoder from `models/image_encoder`, NOT `sdxl_models/image_encoder`. Auto-resolution picks the wrong one (ViT-bigG with 1664-dim hidden states vs expected 1280-dim). Must explicitly load:
```python
image_encoder = CLIPVisionModelWithProjection.from_pretrained(
    "h94/IP-Adapter", subfolder="models/image_encoder", torch_dtype=torch.float16
)
pipe = AutoPipelineForText2Image.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    image_encoder=image_encoder, torch_dtype=torch.float16
).to("cuda")
```

### RGBA Input Images
All reference images from turnaround sheets may have alpha channels (RGBA). Always convert to RGB before passing to any editing pipeline: `Image.open(path).convert("RGB")`.

### Qwen-Image-Edit Memory Profile
- Transformer: 40.9 GB (bf16) — this runs 28x per image, so offloading it is catastrophic for speed
- Text Encoder (Qwen2.5-VL 7B): 16.6 GB — runs once, offloading is acceptable
- VAE: 0.25 GB — negligible
- Total: 57.8 GB bf16, requires FP8 or NF4 to fit in 32GB VRAM
- NF4 via BitsAndBytes: fits but produces noise artifacts (quantization too aggressive for this architecture)
- FP8 via ComfyUI: works well at ~30-60s/image (Michael's prior testing)
