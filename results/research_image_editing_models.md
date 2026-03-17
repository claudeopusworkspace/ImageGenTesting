# Research: Native Image Editing Models (Input Image + Text Instruction -> Modified Image)

**Date**: 2026-03-17
**Scope**: Models that natively accept an input image + text instruction and output a modified image. NOT adapter systems (IP-Adapter, ControlNet). Focus on expression changes, outfit swaps, angle changes, and identity preservation for anime/stylized art.

---

## Table of Contents

1. [FLUX.1 Kontext (dev)](#1-flux1-kontext-dev)
2. [FLUX.2 (dev)](#2-flux2-dev)
3. [Qwen-Image-Edit / Edit-2511](#3-qwen-image-edit--edit-2511)
4. [OmniGen2](#4-omnigen2)
5. [OmniGen v1](#5-omnigen-v1)
6. [HunyuanImage-3.0-Instruct](#6-hunyuanimage-30-instruct)
7. [LongCat-Image-Edit-Turbo](#7-longcat-image-edit-turbo)
8. [Step1X-Edit](#8-step1x-edit)
9. [ICEdit (MoE-LoRA)](#9-icedit-moe-lora)
10. [InstructPix2Pix & Successors (UltraEdit)](#10-instructpix2pix--successors-ultraedit)
11. [Z-Image-Edit](#11-z-image-edit)
12. [CogView4](#12-cogview4)
13. [Qwen-Image-Layered](#13-qwen-image-layered)
14. [Summary Comparison Table](#summary-comparison-table)
15. [Recommendations for Anime Character Editing](#recommendations-for-anime-character-editing)

---

## 1. FLUX.1 Kontext (dev)

**Developer**: Black Forest Labs
**Release**: May 2025
**HuggingFace**: [`black-forest-labs/FLUX.1-Kontext-dev`](https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev)

### Architecture
- 12B parameter rectified flow transformer
- Guidance-distilled for efficiency
- In-context image generation: prompts with both text and images

### Capabilities
- **Local editing**: Make targeted modifications without affecting the rest of the image
- **Character consistency**: Preserve unique elements across scenes (94.7% consistency accuracy per community testing)
- **Style transfer**: Convert photos to anime, Ghibli, comic, oil painting, etc.
- **Multiple successive edits** with minimal visual drift
- Both text-to-image and image-to-image generation in one model

### VRAM Requirements
| Configuration | VRAM |
|---|---|
| Full BF16 | ~24 GB |
| FP8 quantized | ~12 GB |
| FP4 quantized (SVDQuant) | ~7 GB |
| With TensorRT optimization | 2.1x faster, lower VRAM |

### Diffusers Support
Yes -- native `FluxKontextPipeline`:
```python
from diffusers import FluxKontextPipeline
pipe = FluxKontextPipeline.from_pretrained(
    "black-forest-labs/FLUX.1-Kontext-dev",
    torch_dtype=torch.bfloat16
).to("cuda")
output = pipe(image=input_image, prompt="Add a hat to the cat", guidance_scale=2.5).images[0]
```

### License
**FLUX.1 [dev] Non-Commercial License** -- Generated outputs can be used for personal, scientific, and commercial purposes, but the model weights themselves are non-commercial.

### Anime/Stylized Art Handling
**Strong.** Can convert photographs into anime-style illustrations while maintaining facial structure, expression, and pose. Community reports strong results with anime-style character edits. Supports Ghibli-inspired, comic book, and various stylized aesthetics.

### Fine-Grained Editing
**Yes** -- targeted local edits (change just the expression, just the outfit) without affecting the rest. One of the best at this.

### Community Feedback
Widely praised. Considered the gold standard for open-weight image editing as of mid-2025. ComfyUI integration available. Fast inference (3-5 seconds for 1024x1024). Strong ecosystem of community workflows.

---

## 2. FLUX.2 (dev)

**Developer**: Black Forest Labs
**Release**: November 2025
**HuggingFace**: [`black-forest-labs/FLUX.2-dev`](https://huggingface.co/black-forest-labs/FLUX.2-dev)

### Architecture
- 32B parameter rectified flow transformer (significantly larger than Kontext's 12B)
- Guidance-distilled

### Capabilities
- State-of-the-art text-to-image generation
- **Single-reference editing** and **multi-reference editing** (multiple input images)
- Character, object, and style reference without finetuning
- Superset of Kontext capabilities with higher quality

### VRAM Requirements
| Configuration | VRAM |
|---|---|
| Full BF16 | Very high (80GB+ recommended) |
| 4-bit quantized + remote text encoder | RTX 4090 viable |
| GGUF quantized | Consumer GPU viable |

### Diffusers Support
Yes -- `Flux2Pipeline`:
```python
from diffusers import Flux2Pipeline
pipe = Flux2Pipeline.from_pretrained("black-forest-labs/FLUX.2-dev", torch_dtype=torch.bfloat16)
```

### License
**FLUX Non-Commercial License** -- same terms as Kontext dev. Generated outputs usable for personal/scientific/commercial purposes.

### Anime/Stylized Art Handling
Not explicitly documented, but inherits and improves upon Kontext's capabilities. The larger parameter count should yield better quality across all styles.

### Fine-Grained Editing
**Yes** -- supports both single-reference and multi-reference editing.

### Community Feedback
947K+ downloads/month. Massive community adoption. Considered the successor to Kontext for higher-quality work, but at a significant VRAM cost.

---

## 3. Qwen-Image-Edit / Edit-2511

**Developer**: Alibaba Tongyi Qianwen
**Release**: August 2025 (original), December 2025 (2511 version)
**HuggingFace**:
- [`Qwen/Qwen-Image-Edit`](https://huggingface.co/Qwen/Qwen-Image-Edit) (original)
- [`Qwen/Qwen-Image-Edit-2511`](https://huggingface.co/Qwen/Qwen-Image-Edit-2511) (latest)
- [`Qwen/Qwen-Image-Edit-2509`](https://huggingface.co/Qwen/Qwen-Image-Edit-2509) (mid version)

### Architecture
- Built on Qwen-Image (20B parameter MMDiT)
- Dual input path: Qwen2.5-VL for visual semantic control + VAE Encoder for visual appearance control
- This dual-path design enables both semantic editing (understanding what to change) and appearance editing (preserving what shouldn't change)

### Capabilities
**Semantic Editing:**
- IP creation and character consistency preservation
- Object rotation (90, 180 degrees)
- Style transfer (e.g., Studio Ghibli)
- Novel view synthesis

**Appearance Editing:**
- Add/remove/modify specific elements while keeping other regions unchanged
- Background modification, clothing changes, fine detail removal

**Text Editing (bilingual):**
- Add, delete, modify text within images
- Preserve font, size, and style

**2511 Improvements over original:**
- Mitigated image drift for better consistency
- Improved character consistency for single-subject and multi-person editing
- Integrated popular LoRA capabilities
- Enhanced industrial design generation
- Strengthened geometric reasoning

### VRAM Requirements
| Configuration | VRAM |
|---|---|
| Full BF16 (20B model) | ~60 GB storage, 40+ GB VRAM |
| FP8 | RTX 4090 (24 GB) recommended |
| NF4 (4-bit quantized) | ~20 GB, can work on 16 GB |
| GGUF quantized (q4_0/q8_0) | ~8 GB VRAM |
| CPU offloading (per-layer) | 3-4 GB VRAM |

### Diffusers Support
Yes -- native pipelines:
```python
# Original
from diffusers import QwenImageEditPipeline
pipeline = QwenImageEditPipeline.from_pretrained("Qwen/Qwen-Image-Edit")

# 2511 version
from diffusers import QwenImageEditPlusPipeline
pipeline = QwenImageEditPlusPipeline.from_pretrained("Qwen/Qwen-Image-Edit-2511", torch_dtype=torch.bfloat16)
```

### License
**Apache 2.0** -- fully open for commercial use.

### Anime/Stylized Art Handling
**Good.** Demonstrated style transfer to Studio Ghibli. The model supports anime-style conversions, and community feedback indicates quality holds for non-realistic tasks including anime. The dual semantic/appearance path is particularly well-suited for maintaining character identity during style changes.

### Fine-Grained Editing
**Excellent.** The dual-path architecture was specifically designed for this -- semantic understanding of what to change + appearance preservation of what shouldn't change. Can do precise local edits (change only expression, only outfit) with good region isolation.

### Community Feedback
100+ HuggingFace Spaces. Active community. The 2511 version is a significant upgrade over the original. Apache 2.0 license makes it very attractive for commercial use. The Qwen-Image ecosystem (generation + editing + layered) is one of the most complete.

---

## 4. OmniGen2

**Developer**: VectorSpaceLab
**Release**: June 2025
**HuggingFace**: [`OmniGen2/OmniGen2`](https://huggingface.co/OmniGen2/OmniGen2)
**GitHub**: [VectorSpaceLab/OmniGen2](https://github.com/VectorSpaceLab/OmniGen2)

### Architecture
- Foundation: Qwen-VL-2.5
- 3B Vision-Language Model + 4B diffusion model (~7B total)
- Two distinct decoding pathways for text and image with unshared parameters
- Decoupled image tokenizer

### Capabilities
- Visual understanding (inherits from Qwen-VL-2.5)
- Text-to-image generation
- **Instruction-guided image editing** (state-of-the-art among open-source at release)
- In-context generation (combine diverse inputs)
- Clothing modification, action adjustment, background processing

### VRAM Requirements
| Configuration | VRAM |
|---|---|
| Native (RTX 3090) | ~17 GB |
| CPU offload enabled | ~8.5 GB (negligible speed impact) |
| Sequential CPU offload | <3 GB (significantly slower) |

**This is notably efficient for its capabilities.**

### Diffusers Support
Yes -- `OmniGen2Pipeline`:
```python
from OmniGen2 import OmniGen2Pipeline
pipe = OmniGen2Pipeline("OmniGen2/OmniGen2")
pipe.enable_model_cpu_offload()  # For lower VRAM
```
Also supported by ComfyUI (official support since July 2025).

### License
**Apache 2.0** -- fully open for commercial use.

### Anime/Stylized Art Handling
**Mixed results.** Community reviews note the model tends toward anime aesthetics in some cases but can overdo stylistic elements (e.g., excessive purple tint, lost eye detail in anime tests). Not as refined as FLUX Kontext for stylized content. May improve with LoRAs.

### Fine-Grained Editing
**Good.** Supports instruction-guided editing for specific changes. Key parameters: `image_guidance_scale` (1.2-2.0 for editing) controls reference image fidelity vs edit strength.

### Community Feedback
Praised for unified capabilities (understand + generate + edit in one model). The ~17 GB VRAM requirement is attractive. Best with English prompts. Quality competitive but below FLUX Kontext for editing specifically. Training code and datasets released.

---

## 5. OmniGen v1

**Developer**: VectorSpaceLab (Shitao)
**Release**: October 2024
**HuggingFace**: [`Shitao/OmniGen-v1`](https://huggingface.co/Shitao/OmniGen-v1)
**GitHub**: [VectorSpaceLab/OmniGen](https://github.com/VectorSpaceLab/OmniGen)

### Architecture
- Unified image generation framework
- ~15.8 GB model size

### Capabilities
- Text-to-image generation
- Image editing via text instructions
- Image-conditioned generation
- Referring expression generation (combine multiple images via natural language)

### VRAM Requirements
- ~22+ GB for 1024x1024 images
- Reduced with `offload_model=True`

### Diffusers Support
Custom inference code via the OmniGen library. Integrated into diffusers main as of later updates.

### License
**MIT** -- fully open, permissive.

### Anime/Stylized Art Handling
Not specifically addressed. Examples focus on photorealistic subjects.

### Community Feedback
Superseded by OmniGen2 in most respects. Still usable and has the advantage of MIT license vs Apache 2.0 (though both are permissive).

---

## 6. HunyuanImage-3.0-Instruct

**Developer**: Tencent Hunyuan
**Release**: January 26, 2026
**HuggingFace**: [`tencent/HunyuanImage-3.0-Instruct`](https://huggingface.co/tencent/HunyuanImage-3.0-Instruct)
**Also**: [`tencent/HunyuanImage-3.0-Instruct-Distil`](https://huggingface.co/tencent/HunyuanImage-3.0-Instruct-Distil) (faster variant)
**GitHub**: [Tencent-Hunyuan/HunyuanImage-3.0](https://github.com/Tencent-Hunyuan/HunyuanImage-3.0)

### Architecture
- **80B total parameters, ~13B active per token** (MoE with 64 experts, 8 active)
- Unified autoregressive multimodal framework (NOT a DiT -- unique architecture)
- Decoder-only with Mixture-of-Experts
- Native Chain-of-Thought (CoT) reasoning during inference

### Capabilities
- **Text-to-Image (T2I)**
- **Text-Image-to-Image (TI2I)** editing with reasoning
- **Multi-Image Fusion** (up to 3 reference images)
- **CoT Thinking**: Model internally reasons through editing intent step-by-step
- **Prompt Self-Rewrite**: Automatically enhances sparse prompts into detailed descriptions
- Add elements, remove objects, modify styles, background replacement
- Converting anime characters to photorealistic renders and vice versa
- Adding fictional characters into real photos

### VRAM Requirements
| Configuration | VRAM |
|---|---|
| HunyuanImage-3.0-Instruct | >= 8x 80GB GPUs (640 GB total) |
| HunyuanImage-3.0-Instruct-Distil | >= 8x 80GB GPUs |
| HunyuanImage-3.0 (base, no editing) | >= 3x 80GB GPUs |
| NF4 quantized (ComfyUI) | 24-32 GB (community nodes) |

**This is extremely resource-intensive. Impractical for consumer hardware in full precision.**

### Diffusers Support
**No native diffusers pipeline.** Uses custom inference code via `transformers.AutoModelForCausalLM`. Requires Python 3.12+, CUDA 12.8, PyTorch 2.8.0.

```python
from transformers import AutoModelForCausalLM
model = AutoModelForCausalLM.from_pretrained("./HunyuanImage-3-Instruct",
    attn_implementation="sdpa", trust_remote_code=True,
    torch_dtype="auto", device_map="auto")
cot_text, samples = model.generate_image(
    prompt="Edit instruction here",
    image=["input.png"],
    seed=42, bot_task="think_recaption", diff_infer_steps=50
)
```

### License
**Custom license** ("other") -- check repository for specifics. Not a standard open license.

### Anime/Stylized Art Handling
**Strong.** Explicitly demonstrated converting anime characters to photorealistic renders and vice versa. Excels at style transfer tasks. The reasoning capability helps it understand complex style-related instructions.

### Fine-Grained Editing
**Excellent in theory.** The CoT reasoning means it can break down complex edit instructions into components. However, the massive resource requirements limit practical experimentation.

### Community Feedback
Impressive quality -- outperforms DALL-E 3 and Flux in human evaluations. But the 640 GB VRAM requirement for full Instruct version makes it impractical for most users. The NF4 quantized ComfyUI version (24-32 GB) makes it more accessible but with quality tradeoffs. First inference run takes ~10 minutes due to kernel compilation.

---

## 7. LongCat-Image-Edit-Turbo

**Developer**: Meituan
**Release**: February 3, 2026
**HuggingFace**:
- [`meituan-longcat/LongCat-Image-Edit-Turbo`](https://huggingface.co/meituan-longcat/LongCat-Image-Edit-Turbo) (distilled, fast)
- [`meituan-longcat/LongCat-Image-Edit`](https://huggingface.co/meituan-longcat/LongCat-Image-Edit) (full)
**GitHub**: [meituan-longcat/LongCat-Image](https://github.com/meituan-longcat/LongCat-Image)

### Architecture
- 6B parameters (MM-DiT-style, similar to Flux.1-dev)
- Separate attention paths for text and image in early layers, fused in later stages
- Image conditioning via modifications to VAE features, 3D RoPE embeddings, and token sequencing
- Turbo variant: distilled for 8 NFEs (10x speedup over full model)

### Capabilities
- Global editing and local editing
- Text modification within images
- Reference-guided editing
- Bilingual (Chinese-English) editing
- State-of-the-art among open-source image editing models at release
- Strong instruction following and visual consistency

### VRAM Requirements
| Configuration | VRAM |
|---|---|
| Turbo with CPU offload | ~18 GB |
| Full model without offload | ~60 GB |
| High VRAM (full on GPU) | 60+ GB |

### Diffusers Support
Yes -- `LongCatImageEditPipeline`:
```python
from diffusers import LongCatImageEditPipeline
pipe = LongCatImageEditPipeline.from_pretrained(
    "meituan-longcat/LongCat-Image-Edit-Turbo", torch_dtype=torch.bfloat16)
pipe.enable_model_cpu_offload()
image = pipe(img, prompt='Change the cat to a dog',
    guidance_scale=1, num_inference_steps=8).images[0]
```

**Important**: For text rendering tasks, target text MUST be enclosed in quotation marks.

### License
**Apache 2.0** -- fully open for commercial use.

### Anime/Stylized Art Handling
**Good.** Community review specifically noted: "Miyazaki-like color palette and compositions were surprisingly strong with hazy horizons, layered depth, and gentle lighting." For anime-inspired key visuals or storyboards, LongCat-Image "already feels production-usable." Ink outlines sometimes appear too clean (more modern anime than retro).

### Fine-Grained Editing
**Good.** Supports both global and local editing modes. Strong semantic understanding for precise instruction following.

### Community Feedback
53K+ downloads/month. Praised for the Turbo variant's speed (8 steps!) and quality balance. The 6B parameter count makes it efficient. ComfyUI integration available. The bilingual support is a plus.

---

## 8. Step1X-Edit

**Developer**: StepFun
**Release**: April 2025 (v1.0), later updates to v1.1 and v1.2
**HuggingFace**: [`stepfun-ai/Step1X-Edit`](https://huggingface.co/stepfun-ai/Step1X-Edit)
**GitHub**: [stepfun-ai/Step1X-Edit](https://github.com/stepfun-ai/Step1X-Edit)

### Architecture
- MLLM-based instruction parser generates editing tokens
- DiT-based diffusion decoder generates the output image
- Combines language understanding with diffusion generation

### Capabilities
- Instruction-based image editing from natural language
- Text-to-image generation (added in v1.1)
- **Anime character hand-fixing** via pretrained LoRA
- English and Chinese prompt support
- LoRA fine-tuning support for custom editing tasks

### VRAM Requirements
| Configuration | VRAM |
|---|---|
| Full BF16 (1024px) | 42.5-49.8 GB |
| FP8 quantized | 31-34 GB |
| CPU offload | 25.9-29.1 GB |
| FP8 + CPU offload | ~18 GB |

Recommended: 80 GB GPUs for best quality/efficiency.

### Diffusers Support
Yes -- custom diffusers branches:
```python
from diffusers import Step1XEditPipelineV1P2
pipe = Step1XEditPipelineV1P2.from_pretrained(
    "stepfun-ai/Step1X-Edit-v1p2", torch_dtype=torch.bfloat16).to("cuda")
output = pipe(image=image, prompt="add a ruby pendant",
    num_inference_steps=50, true_cfg_scale=6)
```

### License
**Apache 2.0** -- fully open for commercial use.

### Anime/Stylized Art Handling
**Specifically addressed.** The repo includes a hand-fixing LoRA specifically for anime characters, indicating the developers actively considered anime use cases. This is a unique feature among the models surveyed.

### Fine-Grained Editing
**Good.** Designed for "authentic user editing instructions." The GEdit-Bench benchmark covers real-world editing scenarios.

### Community Feedback
12 HuggingFace Spaces. Supports TeaCache and xDiT multi-GPU for 2.5x speedup. The anime hand-fixing LoRA is a notable differentiator. LoRA fine-tuning support makes it customizable for specific use cases.

---

## 9. ICEdit (MoE-LoRA)

**Developer**: River Zhang et al. (Academic)
**Release**: 2025 (NeurIPS 2025)
**HuggingFace**: [`sanaka87/ICEdit-MoE-LoRA`](https://huggingface.co/sanaka87/ICEdit-MoE-LoRA)
**GitHub**: [River-Zhang/ICEdit](https://github.com/River-Zhang/ICEdit)

### Architecture
- **LoRA on top of FLUX.1-fill-dev** (not a standalone model)
- Only 200M trainable parameters (1% of base model)
- Trained on only 50K samples (0.1% of typical training data)
- MoE-LoRA variant for more efficient adaptation
- Uses vision-language models to select better initial noise patterns

### Capabilities
- Adding/removing objects
- Color attribute modifications
- Style transfer
- Background changes
- Multi-turn sequential edits
- Comparable to GPT-4o in character ID preservation

### VRAM Requirements
| Configuration | VRAM |
|---|---|
| Standard setup | ~35 GB (512x768) |
| CPU offloading | ~24 GB (RTX 3090) |
| GGUF quantized | ~10 GB |
| ComfyUI-nunchaku | ~4 GB (!) |

The 4 GB option via nunchaku is remarkable.

### Diffusers Support
Custom inference scripts on top of FLUX.1-fill-dev. Gradio demo available. ComfyUI workflows provided.

### License
**Non-commercial use only.** Explicitly states: "Our project cannot be used for commercial purposes."

### Anime/Stylized Art Handling
**Explicitly limited.** Documentation states: "Training dataset is mostly targeted at realistic images. For non-realistic images, such as anime or blurry pictures, the success rate of editing drops and could potentially affect final image quality."

### Fine-Grained Editing
**Good for realistic images.** High success rates for most tasks except object removal. The MoE routing helps adapt to different edit types.

### Community Feedback
Impressive for its efficiency (200M params, 50K training samples). The 4 GB VRAM option via nunchaku is a game-changer for accessibility. However, the non-commercial license and weak anime support are significant limitations.

---

## 10. InstructPix2Pix & Successors (UltraEdit)

### InstructPix2Pix (Original)
**Developer**: Tim Brooks et al. (UC Berkeley / OpenAI)
**Release**: 2022
**HuggingFace**: [`timbrooks/instruct-pix2pix`](https://huggingface.co/timbrooks/instruct-pix2pix)
**GitHub**: [timothybrooks/instruct-pix2pix](https://github.com/timothybrooks/instruct-pix2pix)

- Based on Stable Diffusion 1.5
- The pioneer of instruction-based image editing
- ~1B parameters
- VRAM: ~8 GB
- License: Custom (check repo)
- **Largely superseded** by all models above. Quality is noticeably lower than 2025 models.
- Diffusers support: `StableDiffusionInstructPix2PixPipeline`

### UltraEdit (NeurIPS 2024)
**Developer**: PKU NLP / Haozhe Zhao
**HuggingFace**: [`BleachNick/SD3_UltraEdit_w_mask`](https://huggingface.co/BleachNick/SD3_UltraEdit_w_mask)
**GitHub**: [pkunlp-icler/UltraEdit](https://github.com/pkunlp-icler/ultraedit)

- Built on Stable Diffusion 3
- Trained on ~4M editing samples (much larger than InstructPix2Pix)
- Supports region-based editing with automatic region annotations
- Uses real images for training data diversity
- Diffusers: `StableDiffusion3InstructPix2PixPipeline`
- Sets records on MagicBrush and Emu-Edit benchmarks
- Better than InstructPix2Pix but still outclassed by dedicated 2025 models

### SeedEdit 3.0 (ByteDance)
**Release**: June 2025
- Built on Seedream 3.0
- Strong preservation of image subjects, backgrounds, and details
- Portrait retouching, background changes, perspective shifts, lighting adjustments
- **NOT open source** -- available only via API (fal.ai, WaveSpeedAI, etc.)
- No public weights on HuggingFace

---

## 11. Z-Image-Edit

**Developer**: Alibaba Tongyi MAI
**Status**: **NOT YET RELEASED** (as of March 2026)
**Planned HuggingFace**: Tongyi-MAI organization
**GitHub**: [Tongyi-MAI/Z-Image](https://github.com/Tongyi-MAI/Z-Image)

### What We Know
- 6B parameters (S3-DiT architecture -- Scalable Single-Stream DiT)
- Part of the Z-Image family alongside Z-Image-Turbo (released) and Z-Image-Omni-Base (unreleased)
- Fine-tuned specifically for image editing tasks
- 50 NFE inference steps
- Expected to fit in ~16 GB VRAM based on Z-Image-Turbo specs
- License expected: Apache 2.0

### Currently Available: Z-Image-Turbo (generation only)
- [`Tongyi-MAI/Z-Image-Turbo`](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo)
- 6B params, 8 NFEs, sub-second inference, 16 GB VRAM
- #1 open-source on Artificial Analysis leaderboard
- Apache 2.0

**Bottom line**: Z-Image-Edit looks very promising (6B params, efficient, Apache 2.0) but weights are not yet available. Worth monitoring.

---

## 12. CogView4

**Developer**: THUDM / Zhipu AI
**HuggingFace**: [`THUDM/CogView4-6B`](https://huggingface.co/THUDM/CogView4-6B)

### Assessment
**CogView4 is text-to-image ONLY.** It does NOT support image-to-image editing. The pipeline only accepts text prompts with no input image parameter. Not relevant to this research.

---

## 13. Qwen-Image-Layered

**Developer**: Alibaba Tongyi Qianwen
**Release**: December 2025
**HuggingFace**: [`Qwen/Qwen-Image-Layered`](https://huggingface.co/Qwen/Qwen-Image-Layered)
**GitHub**: [QwenLM/Qwen-Image-Layered](https://github.com/QwenLM/Qwen-Image-Layered)

### What It Does
Not a direct instruction-based editor, but a **layer decomposition model** that splits an image into multiple RGBA layers. Each layer can then be independently manipulated (resize, reposition, recolor, remove, replace) without affecting others.

### Why It's Relevant
This is a complementary approach: decompose a character into layers (body, hair, outfit, background), then edit individual layers. Combined with Qwen-Image-Edit, this creates a powerful non-destructive editing pipeline.

### Technical Details
- RGBA-VAE for unified RGB/RGBA latent representation
- VLD-MMDiT architecture for variable-layer decomposition
- Supports recursive decomposition (infinite depth)
- Apache 2.0 license
- Diffusers integration available

---

## Summary Comparison Table

| Model | Params | VRAM (Practical) | License | Diffusers | Anime Quality | Fine-Grained Edits | Overall Edit Quality |
|---|---|---|---|---|---|---|---|
| **FLUX.1 Kontext** | 12B | 7-24 GB | Non-commercial* | Yes | Strong | Excellent | Excellent |
| **FLUX.2 dev** | 32B | 24+ GB (quantized) | Non-commercial* | Yes | Good (assumed) | Excellent | State-of-art |
| **Qwen-Image-Edit-2511** | 20B | 4-24 GB | **Apache 2.0** | Yes | Good | Excellent | Excellent |
| **OmniGen2** | ~7B | 3-17 GB | **Apache 2.0** | Yes | Mixed | Good | Good |
| **HunyuanImage-3.0-Instruct** | 80B (13B active) | 24+ GB (quant) / 640 GB (full) | Custom | No (custom) | Strong | Excellent | Excellent |
| **LongCat-Image-Edit-Turbo** | 6B | 18 GB (offload) | **Apache 2.0** | Yes | Good | Good | Very Good |
| **Step1X-Edit** | Unknown | 18-50 GB | **Apache 2.0** | Yes (custom branch) | Has anime LoRA | Good | Good |
| **ICEdit** | 200M LoRA | 4-35 GB | Non-commercial | Custom | **Weak** | Good (realistic) | Good |
| **UltraEdit (SD3)** | SD3-based | ~16 GB | Open | Yes | Moderate | Good | Good |
| **OmniGen v1** | ~15.8 GB | 22+ GB | **MIT** | Custom->Yes | Unknown | Moderate | Moderate |

*FLUX non-commercial: model weights are non-commercial, but generated outputs can be used commercially.

---

## Recommendations for Anime Character Editing

### Best Overall for Anime Editing: **FLUX.1 Kontext (dev)**
- 94.7% character consistency
- Strong anime conversion capabilities
- Can run on 7 GB VRAM (FP4 quantized)
- Best community ecosystem and tooling
- **Caveat**: Non-commercial model license (outputs are commercial-OK)

### Best with Commercial License: **Qwen-Image-Edit-2511**
- Apache 2.0 -- fully commercial
- Dual semantic/appearance path is ideal for preserving identity during edits
- Style transfer to anime demonstrated
- Can run on consumer hardware with quantization (4-8 GB VRAM via GGUF)
- Most complete ecosystem (Edit + Layered + Generation)

### Best for Low VRAM: **OmniGen2**
- 17 GB native, 8.5 GB with offload, <3 GB sequential
- Apache 2.0 license
- Unified model (understand + generate + edit)
- **Caveat**: Anime results are mixed -- may overdone stylistic elements

### Best Speed/Efficiency: **LongCat-Image-Edit-Turbo**
- Only 8 inference steps (10x faster than full models)
- 6B params, 18 GB with offload
- Apache 2.0 license
- Community notes it's "production-usable" for anime storyboards
- Bilingual support

### Most Powerful (If Resources Available): **HunyuanImage-3.0-Instruct**
- CoT reasoning for complex edit understanding
- Excellent anime-to-photo and photo-to-anime conversion
- Outperforms DALL-E 3 and Flux in human evals
- **Caveat**: 640 GB VRAM full / 24+ GB NF4 quantized. Custom license.

### For Expression Changes Specifically
Expression changes on anime characters require:
1. **Identity preservation** -- the face/character must remain recognizable
2. **Local editing** -- only the expression should change
3. **Stylistic consistency** -- anime art style must be maintained

**Top picks for this specific task**:
1. **FLUX.1 Kontext** -- best at targeted local edits with identity preservation
2. **Qwen-Image-Edit-2511** -- dual-path architecture designed for this exact scenario
3. **LongCat-Image-Edit-Turbo** -- good local editing, fast iteration for experimentation

### Models to Watch
- **Z-Image-Edit** -- 6B params, Apache 2.0, efficient. Unreleased but very promising.
- **FLUX.2 dev** -- 32B successor to Kontext, likely best quality but heavy VRAM needs.
- **Step1X-Edit** -- Has anime-specific LoRA for hand fixing; may expand anime support.

---

## Key Takeaways

1. **The field exploded in 2025-2026.** There are now many viable options for native image editing, far beyond the InstructPix2Pix era.

2. **FLUX Kontext is the community favorite** for quality and ecosystem, but its non-commercial model license may matter depending on use case.

3. **Qwen-Image-Edit-2511 is the strongest Apache 2.0 option** with the most complete feature set (semantic + appearance editing, text editing, style transfer).

4. **For anime specifically**, FLUX Kontext and Qwen-Image-Edit are the strongest. LongCat-Image-Edit-Turbo is a strong budget/speed option. OmniGen2 and ICEdit have weaker anime support.

5. **VRAM is increasingly manageable** thanks to quantization (GGUF, NF4, FP8, FP4). Most models can now run on a 24 GB GPU, and some down to 4-8 GB with aggressive quantization.

6. **CogView4 and SeedEdit** are NOT viable for this use case -- CogView4 is text-to-image only, and SeedEdit has no public weights.

7. **HunyuanImage-3.0-Instruct is technically impressive** but the 640 GB VRAM requirement for full quality makes it impractical without multi-GPU server infrastructure. The NF4 quantized version is a compromise.
