# Reference-Based Image Generation Research

**Date**: 2026-03-17
**Focus**: Image-conditioned generation -- taking a reference image as input and generating variations, expressions, poses, or scenes while preserving character identity.

---

## Table of Contents

1. [IP-Adapter (h94/IP-Adapter)](#1-ip-adapter)
2. [FLUX Kontext](#2-flux-kontext)
3. [InstantID / IP-Adapter FaceID](#3-instantid--ip-adapter-faceid)
4. [img2img Approaches](#4-img2img-approaches)
5. [ControlNet + Reference Image Combos](#5-controlnet--reference-image-combos)
6. [Newer Models (2025-2026)](#6-newer-models-2025-2026)
7. [Comparison Matrix](#7-comparison-matrix)
8. [Recommendations for Anime/VN Use Cases](#8-recommendations)

---

## 1. IP-Adapter

**Repository**: [h94/IP-Adapter](https://huggingface.co/h94/IP-Adapter)
**Paper**: arXiv:2308.06721
**Developer**: Tencent AI Lab
**License**: Apache 2.0

### How It Works

IP-Adapter adds image prompting capabilities to diffusion models by **decoupling cross-attention layers** for image and text features. The original UNet/DiT is frozen; only the newly added cross-attention layers for the image encoder are trained. This makes the adapter lightweight (~22M parameters per adapter file, ~100MB on disk) while the image encoder is the main memory cost.

The key insight: image features from a CLIP/SigLIP vision encoder are injected through separate cross-attention layers, allowing independent control of text and image conditioning strength via `set_ip_adapter_scale()`.

### Variants

#### For SD 1.5 (subfolder: `models/`)
| Filename | Type | Notes |
|---|---|---|
| `ip-adapter_sd15.bin` | Global embedding | Base variant, ~22M params |
| `ip-adapter_sd15_light.bin` | Global embedding | Better text prompt compatibility |
| `ip-adapter-plus_sd15.bin` | Patch embeddings | Closer to reference image |
| `ip-adapter-plus-face_sd15.bin` | Patch + face | Optimized for face images |
| `ip-adapter-full-face_sd15.bin` | Full face | Best face detail preservation |

#### For SDXL (subfolder: `sdxl_models/`)
| Filename | Type | Notes |
|---|---|---|
| `ip-adapter_sdxl.bin` | Global OpenCLIP-ViT-bigG-14 | Base SDXL variant |
| `ip-adapter_sdxl_vit-h.bin` | Global OpenCLIP-ViT-H-14 | Lighter encoder |
| `ip-adapter-plus_sdxl_vit-h.safetensors` | Patch embeddings | Closer to reference |
| `ip-adapter-plus-face_sdxl_vit-h.safetensors` | Patch + face | Best for face identity |

#### Image Encoders
| Encoder | Parameters | Used By |
|---|---|---|
| `models/image_encoder` (OpenCLIP-ViT-H-14) | 632M | SD 1.5 models |
| `sdxl_models/image_encoder` (OpenCLIP-ViT-bigG-14) | 1,845M | SDXL models |

### FLUX Support

**Model**: [InstantX/FLUX.1-dev-IP-Adapter](https://huggingface.co/InstantX/FLUX.1-dev-IP-Adapter)
- Uses `google/siglip-so400m-patch14-384` vision encoder (NOT CLIP)
- 128 image tokens, 2-layer MLPProjModel
- Added to 38 single + 19 double FLUX transformer blocks
- Trained on 10M dataset, batch 128, 80K steps

**Also**: [XLabs-AI/flux-ip-adapter](https://huggingface.co/XLabs-AI/flux-ip-adapter)
- Uses `openai/clip-vit-large-patch14` encoder
- Integrated into diffusers natively

**Critical limitation for FLUX IP-Adapter**: The InstantX version explicitly states it is **"NOT designed for fine-grained style transfer or character consistency"**. There is a trade-off between content leakage and style transfer. The XLabs version is better integrated into diffusers but has similar limitations.

### Diffusers Usage (SDXL)

```python
import torch
from diffusers import AutoPipelineForText2Image
from transformers import CLIPVisionModelWithProjection

# Load with explicit image encoder for Plus variants
image_encoder = CLIPVisionModelWithProjection.from_pretrained(
    "h94/IP-Adapter",
    subfolder="models/image_encoder",
    torch_dtype=torch.float16
)

pipeline = AutoPipelineForText2Image.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    image_encoder=image_encoder,
    torch_dtype=torch.float16
).to("cuda")

pipeline.load_ip_adapter(
    "h94/IP-Adapter",
    subfolder="sdxl_models",
    weight_name="ip-adapter-plus-face_sdxl_vit-h.safetensors"
)
pipeline.set_ip_adapter_scale(0.7)

image = pipeline(
    prompt="anime girl smiling, happy expression",
    ip_adapter_image=reference_image,
    negative_prompt="deformed, ugly, low quality",
).images[0]
```

### Diffusers Usage (FLUX)

```python
import torch
from diffusers import FluxPipeline

pipe = FluxPipeline.from_pretrained(
    "black-forest-labs/FLUX.1-dev",
    torch_dtype=torch.bfloat16
).to("cuda")

pipe.load_ip_adapter(
    "XLabs-AI/flux-ip-adapter",
    weight_name="ip_adapter.safetensors",
    image_encoder_pretrained_model_name_or_path="openai/clip-vit-large-patch14"
)
pipe.set_ip_adapter_scale(1.0)

image = pipe(
    prompt="wearing sunglasses",
    ip_adapter_image=reference_image,
    width=1024, height=1024,
    true_cfg_scale=4.0,
).images[0]
```

### Character Identity from Single Reference

- **Plus-face variants**: Best for face preservation. Uses patch embeddings for finer detail.
- **Scale tuning**: 0.5-0.8 is the sweet spot for identity + prompt editability.
- **Single reference**: Works reasonably well for general resemblance, but NOT pixel-perfect.
- **Expression changes**: Achievable by varying the text prompt while keeping IP-Adapter scale moderate (0.5-0.6). Higher scale = more locked to reference expression.

### Anime/Stylized Art Performance

- IP-Adapter works well with anime SDXL models (AnimagineXL, Illustrious-XL) when the reference image is also anime-style.
- Cross-domain (photo reference -> anime output) is inconsistent; works better with the style-focused `ip-adapter-plus` variant.
- For anime, IP-Adapter Plus with style-layer targeting (InstantStyle approach) gives best results.
- **Limitation**: IP-Adapter alone struggles with cross-style consistency. Combining with LoRA training yields more reliable results.

### VRAM Requirements

| Setup | VRAM |
|---|---|
| SDXL + IP-Adapter (fp16) | 12-16 GB |
| SDXL + IP-Adapter + ControlNet (fp16) | 16-20 GB |
| FLUX + IP-Adapter (bf16) | 24-32 GB |
| With `enable_model_cpu_offload()` | Reduces by ~40% |

### Advanced: InstantStyle (Style/Layout Control)

IP-Adapter can be targeted to specific model layers to separate style from content:

```python
# Style-only injection (up block_0)
scale = {
    "up": {"block_0": [0.0, 1.0, 0.0]},
}
pipeline.set_ip_adapter_scale(scale)
```

This prevents content leakage while preserving artistic style from the reference.

### Advanced: Multiple IP-Adapters

Combine face identity + style in one pipeline:

```python
pipeline.load_ip_adapter(
    "h94/IP-Adapter",
    subfolder="sdxl_models",
    weight_name=[
        "ip-adapter-plus_sdxl_vit-h.safetensors",      # style
        "ip-adapter-plus-face_sdxl_vit-h.safetensors"   # face identity
    ]
)
pipeline.set_ip_adapter_scale([0.7, 0.3])  # style stronger, face lighter

image = pipeline(
    prompt="anime character in cyberpunk city",
    ip_adapter_image=[style_images, face_image],  # list of lists
).images[0]
```

### Advanced: IP-Adapter Masking

Assign different reference images to different regions of the output:

```python
from diffusers.image_processor import IPAdapterMaskProcessor

processor = IPAdapterMaskProcessor()
masks = processor.preprocess([mask1, mask2], height=1024, width=1024)

image = pipeline(
    prompt="two characters talking",
    ip_adapter_image=[[face1, face2]],
    cross_attention_kwargs={"ip_adapter_masks": masks}
).images[0]
```

---

## 2. FLUX Kontext

**Model ID**: [black-forest-labs/FLUX.1-Kontext-dev](https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev)
**Developer**: Black Forest Labs
**Paper**: arXiv:2506.15742
**License**: FLUX.1 [dev] Non-Commercial License
**Parameters**: 12 billion

### What Is It?

FLUX Kontext is a **12B rectified flow transformer** specialized for **in-context image editing**. Unlike regular FLUX (text-to-image), Kontext takes both an input image AND a text instruction, performing edits while preserving the parts of the image not mentioned in the instruction. It was trained using guidance distillation.

### How It Differs from Regular FLUX

| Feature | FLUX.1 Dev | FLUX.1 Kontext Dev |
|---|---|---|
| Primary use | Text-to-image | Image editing via text instructions |
| Input | Text prompt only | Image + text instruction |
| Reference handling | None (needs IP-Adapter) | Native -- built into the model |
| Character consistency | Requires external tools | Built-in, ~98% identity retention |
| Iterative editing | Not designed for it | Robust across multiple edits |
| Pipeline class | `FluxPipeline` | `FluxKontextPipeline` |

### Capabilities

1. **Image editing**: "Add a hat to the cat", "Change the background to a forest"
2. **Character reference**: Maintain character appearance across scenes without fine-tuning
3. **Style reference**: Apply consistent artistic styles
4. **Object reference**: Keep specific objects consistent
5. **Expression/pose changes**: Achievable through text instructions like "make her smile" or "change pose to sitting"
6. **Iterative refinement**: Multiple successive edits with minimal visual drift
7. **Inpainting**: Via `FluxKontextInpaintPipeline` for targeted region editing

### Diffusers Usage

```python
import torch
from diffusers import FluxKontextPipeline
from diffusers.utils import load_image

pipe = FluxKontextPipeline.from_pretrained(
    "black-forest-labs/FLUX.1-Kontext-dev",
    torch_dtype=torch.bfloat16
).to("cuda")

input_image = load_image("character_reference.png")

# Expression change
image = pipe(
    image=input_image,
    prompt="Make the character smile with eyes closed, happy expression",
    guidance_scale=2.5,
).images[0]
```

### Kontext Inpainting

```python
from diffusers import FluxKontextInpaintPipeline

pipe = FluxKontextInpaintPipeline.from_pretrained(
    "black-forest-labs/FLUX.1-Kontext-dev",
    torch_dtype=torch.bfloat16
).to("cuda")

image = pipe(
    prompt="Change expression to surprised",
    image=source_image,
    mask_image=face_mask,  # white = repaint, black = keep
    strength=1.0,
).images[0]
```

### Multi-Image Reference

Kontext supports combining up to 4 reference images for precision control:
- Face from one image + background from another
- Clothing reference + pose reference
- An "Image Stitch Node" approach for multi-image composition

### Pose Control LoRA

[thedeoxen/refcontrol-flux-kontext-reference-pose-lora](https://huggingface.co/thedeoxen/refcontrol-flux-kontext-reference-pose-lora) -- fuses reference identity with a pose control map.

### VRAM Requirements

| Format | VRAM | Speed |
|---|---|---|
| BF16 (full) | ~24 GB | Baseline |
| FP8 (quantized) | ~12 GB | 2x faster |
| FP4 (quantized, RTX 50xx) | ~7 GB | 2.1x faster |

FP8 quantization via `optimum-quanto`:
```python
# See NVIDIA blog for FP8/FP4 optimization details
```

Group offloading for lower VRAM:
```python
from diffusers.hooks import apply_group_offloading
apply_group_offloading(
    pipe.transformer,
    offload_type="leaf_level",
    offload_device=torch.device("cpu"),
    onload_device=torch.device("cuda"),
    use_stream=True,
)
```

### Anime/Stylized Art Performance

- Kontext preserves style when editing anime images -- if the input is anime, the output stays anime.
- Expression/pose changes work well when prompted clearly.
- No specific anime fine-tuning reported, but the general editing capability extends to stylized art.
- Best practice: Be explicit about what to keep ("maintain anime style, same character design") and what to change.
- Multi-image reference workflows can combine anime style references with character identity references.

### Assessment for Character Consistency

**This is currently the strongest single-model solution for reference-based character variation.** The native in-context editing capability means no separate adapter loading, no separate face encoder, and no complex multi-model pipelines. The trade-off is the FLUX.1 [dev] non-commercial license and the 12B model size requiring significant VRAM.

---

## 3. InstantID / IP-Adapter FaceID

### InstantID

**Model ID**: [InstantX/InstantID](https://huggingface.co/InstantX/InstantID)
**Paper**: arXiv:2401.07519
**License**: Apache 2.0
**Base Model**: SDXL

#### Architecture

InstantID uses a **dual approach**:
1. **IP-Adapter**: Encodes face identity from InsightFace embeddings
2. **ControlNet**: Uses facial keypoints for spatial/pose control

This combination provides both semantic identity (who the person is) and geometric structure (face shape, pose).

#### How to Use with Diffusers

```python
import cv2
import torch
import numpy as np
from diffusers import ControlNetModel
from diffusers.utils import load_image
from insightface.app import FaceAnalysis
from pipeline_stable_diffusion_xl_instantid import StableDiffusionXLInstantIDPipeline, draw_kps

# Face analysis
app = FaceAnalysis(name='antelopev2', root='./',
                   providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))

# Load models
controlnet = ControlNetModel.from_pretrained(
    "./checkpoints/ControlNetModel", torch_dtype=torch.float16)

pipe = StableDiffusionXLInstantIDPipeline.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    controlnet=controlnet,
    torch_dtype=torch.float16
).cuda()
pipe.load_ip_adapter_instantid("./checkpoints/ip-adapter.bin")

# Extract face
face_image = load_image("reference.jpg")
face_info = app.get(cv2.cvtColor(np.array(face_image), cv2.COLOR_RGB2BGR))
face_info = sorted(face_info, key=lambda x: (x['bbox'][2]-x['bbox'][0])*(x['bbox'][3]-x['bbox'][1]))[-1]
face_emb = face_info['embedding']
face_kps = draw_kps(face_image, face_info['kps'])

pipe.set_ip_adapter_scale(0.8)

image = pipe(
    prompt="a person in cyberpunk city at night",
    image_embeds=face_emb,
    image=face_kps,
    controlnet_conditioning_scale=0.8,
).images[0]
```

#### VRAM Requirements
- SDXL + ControlNet + IP-Adapter (fp16): ~10-12 GB
- With additional models: ~14-16 GB

#### Anime/Stylized Art Performance

**Limited.** InstantID relies on InsightFace for face detection and embedding extraction. InsightFace is trained on **real human faces** and:
- Often **fails to detect anime faces** entirely
- Even when it detects them, the embeddings are optimized for photorealistic faces
- Results with anime references are poor to unusable
- Workaround: Use a real face as identity reference, then apply anime style via prompt/LoRA -- but this defeats the purpose of anime-native workflows

**Verdict**: InstantID is excellent for photorealistic face identity transfer but **not suitable for anime/stylized characters**.

### IP-Adapter FaceID

**Repository**: [h94/IP-Adapter-FaceID](https://huggingface.co/h94/IP-Adapter-FaceID)

#### Variants
| Model | Base | Notes |
|---|---|---|
| `ip-adapter-faceid_sd15.bin` | SD 1.5 | Base FaceID |
| `ip-adapter-faceid_sdxl.bin` | SDXL | SDXL version |
| `ip-adapter-faceid-plus_sd15.bin` | SD 1.5 | FaceID + CLIP |
| `ip-adapter-faceid-plusv2_sd15.bin` | SD 1.5 | Controllable CLIP weight |
| `ip-adapter-faceid-plusv2_sdxl.bin` | SDXL | Best quality |
| `ip-adapter-faceid-portrait_sd15.bin` | SD 1.5 | Multi-image (default 5) |

#### How It Differs from Regular IP-Adapter

- Uses **InsightFace face embeddings** instead of CLIP image embeddings
- Includes a LoRA component for better identity adaptation
- Plus variants combine FaceID + CLIP for both identity AND appearance
- PlusV2 adds controllable weighting between the two

#### Diffusers Usage

```python
from insightface.app import FaceAnalysis
import torch
import cv2
import numpy as np

app = FaceAnalysis(name="buffalo_l",
                   providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))

# Extract face embedding
image_cv2 = cv2.cvtColor(np.asarray(face_image), cv2.COLOR_BGR2RGB)
faces = app.get(image_cv2)
face_embed = torch.from_numpy(faces[0].normed_embedding).unsqueeze(0)
ref_embeds = torch.stack([face_embed], dim=0).unsqueeze(0)
neg_embeds = torch.zeros_like(ref_embeds)
id_embeds = torch.cat([neg_embeds, ref_embeds]).to(dtype=torch.float16, device="cuda")

pipeline.load_ip_adapter(
    "h94/IP-Adapter-FaceID",
    subfolder=None,
    weight_name="ip-adapter-faceid_sdxl.bin",
    image_encoder_folder=None
)

image = pipeline(
    prompt="portrait of a person in forest",
    ip_adapter_image_embeds=[id_embeds],
).images[0]
```

#### Anime/Stylized Art Performance

**Same limitation as InstantID** -- relies on InsightFace which is trained on real faces. Does not work reliably with anime faces. The FaceID models are trained on photorealistic base models (Realistic_Vision, RealVisXL).

#### License
**Non-commercial** (due to InsightFace restrictions).

---

## 4. img2img Approaches

### Standard img2img (SDXL)

```python
from diffusers import AutoPipelineForImage2Image

pipe = AutoPipelineForImage2Image.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    torch_dtype=torch.float16
).to("cuda")

image = pipe(
    prompt="same character, angry expression, detailed anime art",
    image=reference_image,
    strength=0.4,  # key parameter
    guidance_scale=7.5,
).images[0]
```

### Standard img2img (FLUX)

```python
from diffusers import FluxImg2ImgPipeline

pipe = FluxImg2ImgPipeline.from_pretrained(
    "black-forest-labs/FLUX.1-dev",
    torch_dtype=torch.bfloat16
).to("cuda")

image = pipe(
    prompt="same character with surprised expression",
    image=reference_image,
    strength=0.5,
    num_inference_steps=50,
    guidance_scale=3.5,
).images[0]
```

### Denoising Strength Guide

| Strength | Effect | Use Case |
|---|---|---|
| 0.1-0.3 | Subtle changes | Minor color/lighting tweaks |
| 0.3-0.5 | Moderate changes | Expression changes while keeping composition |
| 0.5-0.7 | Significant changes | Pose changes, outfit changes |
| 0.7-0.9 | Major transformation | Style transfer, scene change |
| 0.9-1.0 | Near-complete regeneration | Almost text-to-image, reference barely visible |

**For expression changes**: 0.3-0.5 is the sweet spot. Lower preserves more of the original, higher allows more creativity.

### Inpainting for Expression Changes

The most precise approach for changing just the face/expression:

```python
from diffusers import AutoPipelineForInpainting

pipe = AutoPipelineForInpainting.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    torch_dtype=torch.float16
).to("cuda")

# mask_image: white over face area, black everywhere else
image = pipe(
    prompt="anime girl with happy smile, detailed eyes",
    image=original_image,
    mask_image=face_mask,
    strength=0.8,
    guidance_scale=7.5,
).images[0]
```

### FLUX Fill (Purpose-Built Inpainting)

```python
from diffusers import FluxFillPipeline

pipe = FluxFillPipeline.from_pretrained(
    "black-forest-labs/FLUX.1-Fill-dev",
    torch_dtype=torch.bfloat16
).to("cuda")

image = pipe(
    prompt="same character with surprised expression, wide eyes, open mouth",
    image=original_image,
    mask_image=face_mask,
).images[0]
```

**Model ID**: `black-forest-labs/FLUX.1-Fill-dev` -- specifically trained for inpainting/outpainting, generally better than using the base model's inpaint pipeline.

### Anime/Stylized Art Performance

- img2img works well with anime models (AnimagineXL, Illustrious-XL)
- The key is using an anime-tuned base model rather than the default SDXL
- For expression changes, combining img2img with inpainting masks gives the best targeted results
- Anime models to use as base:
  - `cagliostrolab/animagine-xl-4.0` -- latest AnimagineXL, 8.4M anime images
  - `OnomaAIResearch/Illustrious-XL-v1.0` -- up to 1536x1536 native resolution
  - Various community fine-tunes on CivitAI

---

## 5. ControlNet + Reference Image Combos

### The Power Combo: ControlNet (Pose) + IP-Adapter (Identity)

This is one of the most effective pipelines for character-consistent pose/expression variation:

1. **ControlNet** controls the spatial structure (pose, depth, edges)
2. **IP-Adapter** controls the visual identity (character appearance, style)

### SDXL ControlNet Models

**Best Union Model**: [xinsir/controlnet-union-sdxl-1.0](https://huggingface.co/xinsir/controlnet-union-sdxl-1.0)
- License: Apache 2.0
- Downloads: 107K+/month
- Supports 12+ control types in ONE model:
  - OpenPose, Depth, Canny, LineArt, AnimeLineArt, MLSD, Scribble, HED, PIDI/Softedge, TEED, Segment/SAM, Normal
- Multi-control combos: OpenPose+Canny, OpenPose+Depth, etc.
- Trained on 10M+ images with bucket training

**Individual SDXL ControlNet Models**:
| Type | Model ID |
|---|---|
| OpenPose (best) | `xinsir/controlnet-openpose-sdxl-1.0` |
| Canny | `diffusers/controlnet-canny-sdxl-1.0` |
| Depth | `diffusers/controlnet-depth-sdxl-1.0` |
| OpenPose (Thibaud) | `thibaud/controlnet-openpose-sdxl-1.0` |

### FLUX ControlNet Models

**InstantX Union**: [InstantX/FLUX.1-dev-Controlnet-Union](https://huggingface.co/InstantX/FLUX.1-dev-Controlnet-Union)

| Mode | Control Type | Quality |
|---|---|---|
| 0 | Canny | High |
| 1 | Tile | High |
| 2 | Depth | High |
| 3 | Blur | High |
| 4 | Pose | High |
| 5 | Gray | Low |
| 6 | Low Quality (upscale) | High |

**Individual FLUX ControlNets**:
| Type | Model ID |
|---|---|
| Canny | `InstantX/FLUX.1-dev-Controlnet-Canny` |
| Depth | `Shakker-Labs/FLUX.1-dev-ControlNet-Depth` |
| Canny (XLabs) | `XLabs-AI/flux-controlnet-canny-diffusers` |
| Depth (XLabs) | `XLabs-AI/flux-controlnet-depth-diffusers` |
| HED (XLabs) | `XLabs-AI/flux-controlnet-hed-diffusers` |

**Built-in FLUX Control Models** (channel-wise concatenation, NOT traditional ControlNet):
| Type | Model ID |
|---|---|
| Canny | `black-forest-labs/FLUX.1-Canny-dev` |
| Depth | `black-forest-labs/FLUX.1-Depth-dev` |
| Canny LoRA | `black-forest-labs/FLUX.1-Canny-dev-lora` |
| Depth LoRA | `black-forest-labs/FLUX.1-Depth-dev-lora` |

### Combined Pipeline: SDXL + ControlNet + IP-Adapter

```python
import torch
from diffusers import StableDiffusionXLControlNetPipeline, ControlNetModel
from diffusers.utils import load_image

# Load ControlNet for pose
controlnet = ControlNetModel.from_pretrained(
    "xinsir/controlnet-openpose-sdxl-1.0",
    torch_dtype=torch.float16
)

pipe = StableDiffusionXLControlNetPipeline.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    controlnet=controlnet,
    torch_dtype=torch.float16
).to("cuda")

# Load IP-Adapter for identity
pipe.load_ip_adapter(
    "h94/IP-Adapter",
    subfolder="sdxl_models",
    weight_name="ip-adapter-plus-face_sdxl_vit-h.safetensors"
)
pipe.set_ip_adapter_scale(0.6)

# Generate: pose from skeleton + identity from reference
image = pipe(
    prompt="anime character standing, full body",
    image=openpose_skeleton,             # pose control
    ip_adapter_image=character_reference, # identity
    controlnet_conditioning_scale=0.8,
).images[0]
```

### Combined Pipeline: FLUX + ControlNet + IP-Adapter

The `FluxControlNetPipeline` natively supports `ip_adapter_image` parameter:

```python
from diffusers import FluxControlNetPipeline, FluxControlNetModel

controlnet = FluxControlNetModel.from_pretrained(
    "InstantX/FLUX.1-dev-Controlnet-Union",
    torch_dtype=torch.bfloat16
)

pipe = FluxControlNetPipeline.from_pretrained(
    "black-forest-labs/FLUX.1-dev",
    controlnet=controlnet,
    torch_dtype=torch.bfloat16
).to("cuda")

pipe.load_ip_adapter(
    "XLabs-AI/flux-ip-adapter",
    weight_name="ip_adapter.safetensors",
    image_encoder_pretrained_model_name_or_path="openai/clip-vit-large-patch14"
)

image = pipe(
    prompt="anime character in action pose",
    control_image=depth_map,
    control_mode=2,  # depth
    ip_adapter_image=character_reference,
    controlnet_conditioning_scale=0.5,
).images[0]
```

### VRAM for Combined Pipelines

| Setup | Estimated VRAM (fp16) |
|---|---|
| SDXL + ControlNet | 10-14 GB |
| SDXL + ControlNet + IP-Adapter | 14-18 GB |
| FLUX + ControlNet | 24-32 GB |
| FLUX + ControlNet + IP-Adapter | 32+ GB |
| Any above with CPU offloading | ~50-60% of full |

### Anime/Stylized Art Notes

- `AnimeLineArt` mode in the SDXL union ControlNet is specifically designed for anime
- xinsir's models support anime line art extraction natively
- For anime pose control, OpenPose still works if the character has human proportions
- Best combo for anime: AnimagineXL/Illustrious + ControlNet Union + IP-Adapter Plus

---

## 6. Newer Models (2025-2026)

### FLUX.1 Redux (Image Variation Adapter)

**Model ID**: [black-forest-labs/FLUX.1-Redux-dev](https://huggingface.co/black-forest-labs/FLUX.1-Redux-dev)
**License**: FLUX.1 [dev] Non-Commercial

A **prior adapter** that generates image variations. Unlike Kontext (which edits), Redux produces new images inspired by the input.

```python
from diffusers import FluxPriorReduxPipeline, FluxPipeline

pipe_redux = FluxPriorReduxPipeline.from_pretrained(
    "black-forest-labs/FLUX.1-Redux-dev",
    torch_dtype=torch.bfloat16
).to("cuda")

pipe = FluxPipeline.from_pretrained(
    "black-forest-labs/FLUX.1-dev",
    text_encoder=None, text_encoder_2=None,
    torch_dtype=torch.bfloat16
).to("cuda")

pipe_prior_output = pipe_redux(reference_image)
images = pipe(
    guidance_scale=2.5,
    num_inference_steps=50,
    **pipe_prior_output,
).images
```

**Assessment**: Good for general image variations but less precise than Kontext for targeted edits. Useful as a "shuffle" tool for generating design alternatives.

### PuLID (Pure and Lightning ID Customization)

**Model ID**: [guozinan/PuLID](https://huggingface.co/guozinan/PuLID)
**Paper**: arXiv:2404.16022 (NeurIPS 2024)
**License**: Apache 2.0
**Developer**: ByteDance

PuLID uses **contrastive alignment** for identity-preserving generation -- a different approach from IP-Adapter's cross-attention injection.

**Variants**:
| Model | Base | Notes |
|---|---|---|
| `pulid_v1.bin` | SDXL | Original paper model |
| `pulid_v1.1.safetensors` | SDXL | Better compatibility, editability, naturalness |
| `PuLID-FLUX-v0.9.0.safetensors` | FLUX | Initial FLUX version |
| `PuLID-FLUX-v0.9.1.safetensors` | FLUX | +5% ID similarity improvement |

**VRAM**:
- FLUX version: Runs on 16GB GPU (fp8), 12GB GPU (with optimizations)
- SDXL version: Standard SDXL requirements (~10-12 GB)

**Anime support**: Not specifically designed for anime. Uses face identity embeddings, so same InsightFace limitations apply.

**Key advantage over IP-Adapter FaceID**: Better prompt editability while maintaining identity. The contrastive alignment approach means less "identity leakage" into non-face areas.

### OmniGen

**Model ID**: [Shitao/OmniGen-v1](https://huggingface.co/Shitao/OmniGen-v1)
**Paper**: arXiv:2409.11340
**License**: MIT

A **unified model** that handles text-to-image, subject-driven generation, identity preservation, editing, and image-conditioned generation WITHOUT requiring separate adapters (no ControlNet, no IP-Adapter, no Reference-Net).

```python
from OmniGen import OmniGenPipeline

pipe = OmniGenPipeline.from_pretrained("Shitao/OmniGen-v1")

# Reference-based generation with inline image references
images = pipe(
    prompt="A girl in a blue dress. The girl has the same face as the woman in <img><|image_1|></img>.",
    input_images=["./reference_face.jpg"],
    height=1024, width=1024,
    guidance_scale=2.5,
    img_guidance_scale=1.6,
)
```

**Key feature**: Image references are embedded directly in the prompt via `<img><|image_*|></img>` placeholders. No adapter loading, no separate face encoders. The model figures out what to extract from the reference based on the text context.

**Anime support**: Not specifically mentioned. General-purpose model.
**VRAM**: Significant; `offload_model=True` option for memory-constrained setups.

### InstantCharacter (Tencent Hunyuan)

**Developer**: Tencent
**Status**: Open source on GitHub
**Architecture**: Scalable diffusion transformer (DiT) with 12-layer Transformer encoder

Features:
- 92% feature retention rate from single reference image
- Dual-encoder separating style from content
- Supports multi-style adaptation (cyberpunk, watercolor, etc.)
- Integrates with FLUX and custom LoRA models
- Style LoRA for customization

**VRAM**: A100 recommended, 256GB RAM (this is a large model)
**Assessment**: Promising but resource-heavy. More suited for production pipelines than local development.

### StoryDiffusion

**Focus**: Video and multi-image consistency
**Key Innovation**: Consistent Self-Attention -- ensures character traits (height, clothing, features) remain consistent across frames
- Story splitting for multi-prompt narratives
- Videos up to 30 seconds with character consistency
- Open source

### VNCCS (Visual Novel Character Creation Suite)

**Platform**: ComfyUI-based workflow (not a standalone model)
**Designed for**: Visual novel character sprite generation
**4-Stage Pipeline**:
1. Character sheet generation
2. Costume creation
3. Emotion/expression generation
4. Final sprite production

**Assessment**: The most VN-specific tool found, but it's a ComfyUI workflow rather than a Python-callable model. Would need ComfyUI integration or workflow translation.

### Illustrious-XL

**Model ID**: [OnomaAIResearch/Illustrious-XL-v1.0](https://huggingface.co/OnomaAIResearch/Illustrious-XL-v1.0)
**Native resolution**: Up to 1536x1536 (within SDXL framework)
**Specialization**: Anime/illustration generation
**Tag system**: Danbooru-style + natural language

This is the base model of choice for anime generation. Spawned an ecosystem of fine-tunes (WAI-Illustrious, etc.) and FLUX LoRAs in late 2025.

### AnimagineXL 4.0

**Model ID**: [cagliostrolab/animagine-xl-4.0](https://huggingface.co/cagliostrolab/animagine-xl-4.0)
**Released**: January 2026
**Dataset**: 8.4M curated anime images
**Improvements**: Better hands, anatomy, booru tag comprehension

Both Illustrious-XL and AnimagineXL 4.0 serve as excellent **base models** for anime generation, but they are text-to-image models. They need IP-Adapter, ControlNet, or LoRA for reference-based consistency.

---

## 7. Comparison Matrix

### Identity Preservation from Single Reference

| Tool | Photo Identity | Anime Identity | Expression Change | Pose Change | Diffusers Support |
|---|---|---|---|---|---|
| IP-Adapter Plus Face (SDXL) | Good | Moderate | Yes (adjust scale) | With ControlNet | Native |
| IP-Adapter FaceID (SDXL) | Very Good | Poor | Yes | With ControlNet | Native |
| InstantID | Excellent | Poor | Limited | Via ControlNet kps | Custom pipeline |
| PuLID (SDXL/FLUX) | Very Good | Poor | Yes, good editability | Limited | Gradio/custom |
| FLUX Kontext | Good | Good | Yes (text instruction) | Yes (text instruction) | Native |
| FLUX Redux | Moderate | Moderate | Limited | No | Native |
| OmniGen | Moderate | Unknown | Via prompt | Via prompt | Custom |

### VRAM Requirements Summary

| Tool | Minimum | Comfortable | With Offloading |
|---|---|---|---|
| IP-Adapter + SDXL | 10 GB | 16 GB | 6-8 GB |
| IP-Adapter + FLUX | 20 GB | 32 GB | 12-16 GB |
| InstantID (SDXL) | 10 GB | 16 GB | 6-8 GB |
| PuLID (FLUX, fp8) | 12 GB | 16 GB | - |
| FLUX Kontext (bf16) | 24 GB | 24 GB | 12 GB (fp8) |
| FLUX Kontext (fp8) | 12 GB | 16 GB | 7 GB (fp4) |
| ControlNet + IP-Adapter (SDXL) | 14 GB | 20 GB | 8-10 GB |

### Anime/Stylized Art Suitability

| Tool | Rating | Notes |
|---|---|---|
| IP-Adapter Plus (SDXL) | B+ | Works well with anime base models, style-focused |
| IP-Adapter Face (SDXL) | B | Decent for anime face similarity, not pixel-perfect |
| IP-Adapter FaceID | D | InsightFace cannot reliably detect anime faces |
| InstantID | D | Same InsightFace limitation |
| PuLID | D | Same InsightFace limitation |
| FLUX Kontext | A- | Preserves input style including anime, good editing |
| FLUX Redux | B- | Generates variations, style somewhat preserved |
| OmniGen | C | General purpose, no anime specialization |
| img2img + anime base | B+ | Simple but effective with right strength |
| Inpainting + anime base | A- | Very precise expression control |

---

## 8. Recommendations

### For Anime/VN Character Expression Sheets

**Best approach (quality, 24GB+ VRAM)**:
1. Generate initial character art with AnimagineXL 4.0 or Illustrious-XL
2. Use **FLUX Kontext** for expression/pose variations via text instructions
3. Use **Kontext inpainting** for fine-tuning specific facial expressions

**Best approach (practical, 12-16GB VRAM)**:
1. Use AnimagineXL 4.0 or Illustrious-XL as base
2. Use **IP-Adapter Plus Face (SDXL)** for character identity
3. Use **ControlNet (OpenPose/AnimeLineArt)** for pose control
4. Use **inpainting** for expression-specific changes
5. Combine multiple IP-Adapters: style + face

**Budget approach (8-10GB VRAM)**:
1. Use AnimagineXL 4.0 with CPU offloading
2. Use **img2img** at strength 0.3-0.5 for expression variations
3. Use **inpainting** with face masks for targeted expression changes
4. No IP-Adapter or ControlNet (VRAM too limited)

### For Maximum Character Consistency

If you need the same character across dozens of images with minimal drift:

1. **Train a character LoRA** (15-30 diverse images of the character)
2. Use LoRA + IP-Adapter for maximum consistency
3. Use ControlNet for pose variation
4. This is the gold standard approach used by the VN/anime community

### Key Takeaways

1. **FLUX Kontext is the most capable single model** for reference-based editing, but requires 24GB VRAM (12GB with fp8) and has a non-commercial license.

2. **IP-Adapter Plus Face + SDXL** is the most practical diffusers-native approach for anime character consistency. Works well with anime base models. Does not require face detection (unlike FaceID/InstantID/PuLID).

3. **All InsightFace-based tools (InstantID, IP-Adapter FaceID, PuLID) fail with anime faces.** Do not use these for anime/stylized art workflows.

4. **Inpainting is the most precise tool for expression changes.** Mask the face area and regenerate with a new expression prompt.

5. **ControlNet + IP-Adapter is the most flexible pipeline** for simultaneous pose and identity control, but requires more VRAM and setup.

6. **For production anime VN workflows**, the community consensus is: anime base model + character LoRA + ControlNet for poses. IP-Adapter adds consistency without LoRA training time.

---

## Sources

- [IP-Adapter Diffusers Documentation](https://huggingface.co/docs/diffusers/using-diffusers/ip_adapter)
- [h94/IP-Adapter Model Hub](https://huggingface.co/h94/IP-Adapter)
- [h94/IP-Adapter-FaceID](https://huggingface.co/h94/IP-Adapter-FaceID)
- [InstantX/FLUX.1-dev-IP-Adapter](https://huggingface.co/InstantX/FLUX.1-dev-IP-Adapter)
- [black-forest-labs/FLUX.1-Kontext-dev](https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev)
- [FLUX Pipelines in Diffusers](https://huggingface.co/docs/diffusers/en/api/pipelines/flux)
- [InstantX/InstantID](https://huggingface.co/InstantX/InstantID)
- [FLUX ControlNet in Diffusers](https://huggingface.co/docs/diffusers/en/api/pipelines/controlnet_flux)
- [InstantX/FLUX.1-dev-Controlnet-Union](https://huggingface.co/InstantX/FLUX.1-dev-Controlnet-Union)
- [xinsir/controlnet-union-sdxl-1.0](https://huggingface.co/xinsir/controlnet-union-sdxl-1.0)
- [black-forest-labs/FLUX.1-Redux-dev](https://huggingface.co/black-forest-labs/FLUX.1-Redux-dev)
- [guozinan/PuLID](https://huggingface.co/guozinan/PuLID)
- [PuLID GitHub](https://github.com/ToTheBeginning/PuLID)
- [Shitao/OmniGen-v1](https://huggingface.co/Shitao/OmniGen-v1)
- [OnomaAIResearch/Illustrious-XL-v1.0](https://huggingface.co/OnomaAIResearch/Illustrious-XL-v1.0)
- [cagliostrolab/animagine-xl-4.0](https://huggingface.co/cagliostrolab/animagine-xl-4.0)
- [XLabs-AI/flux-ip-adapter](https://huggingface.co/XLabs-AI/flux-ip-adapter)
- [NVIDIA: Optimizing FLUX.1 Kontext with Quantization](https://developer.nvidia.com/blog/optimizing-flux-1-kontext-for-image-editing-with-low-precision-quantization/)
- [FLUX Kontext VRAM Analysis](https://www.aifreeapi.com/en/posts/flux-kontext-local-deployment)
- [Solving Character Consistency with Flux.1 Kontext](https://comfyui.org/en/solving-character-consistency-with-flux1-kontext)
- [Consistent Portraits with IP-Adapters for SDXL](https://mybyways.com/blog/consistent-portraits-using-ip-adapters-for-sdxl)
- [Stable Diffusion Art: IP-Adapters Guide](https://stable-diffusion-art.com/ip-adapter/)
- [thedeoxen/refcontrol-flux-kontext-reference-pose-lora](https://huggingface.co/thedeoxen/refcontrol-flux-kontext-reference-pose-lora)
- [InstantCharacter](https://www.xugj520.cn/en/archives/instantcharacter-personalized-generation-en.html)
- [VNCCS Visual Novel Character Suite](https://apatero.com/blog/vnccs-visual-novel-character-creation-suite-comfyui-2025)
