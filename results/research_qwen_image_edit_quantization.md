# Qwen-Image-Edit-2511: Quantization & Memory Optimization Research

## Model Architecture Breakdown

The `QwenImageEditPlusPipeline` consists of these components:

| Component | Class | Library | Size (bf16) |
|-----------|-------|---------|-------------|
| **Transformer** | `QwenImageTransformer2DModel` | diffusers | **~40.9 GB** |
| **Text Encoder** | `Qwen2_5_VLForConditionalGeneration` | transformers | **~16.6 GB** |
| **VAE** | `AutoencoderKLQwenImage` | diffusers | ~0.25 GB |
| **Tokenizer** | `Qwen2Tokenizer` | transformers | negligible |
| **Processor** | `Qwen2VLProcessor` | transformers | negligible |
| **Scheduler** | `FlowMatchEulerDiscreteScheduler` | diffusers | negligible |
| **Total** | | | **~57.8 GB** |

The transformer is by far the largest component at 40.9 GB in bf16. The text encoder (Qwen2.5-VL 7B) is the second largest at 16.6 GB. Together they need ~57.5 GB, which explains why bf16 needs ~40 GB VRAM (the text encoder runs first and can be offloaded before the transformer runs, but with `pipeline.to('cuda')` both must fit).

---

## Option 1: BitsAndBytes NF4 Quantization (RECOMMENDED for diffusers)

BitsAndBytes is fully supported in diffusers for any model with `torch.nn.Linear` layers. You can quantize the transformer and text encoder independently while keeping the VAE in full precision.

### NF4 Quantization - Transformer Only (~10 GB for transformer)

```python
import torch
from diffusers import BitsAndBytesConfig as DiffusersBitsAndBytesConfig
from diffusers import AutoModel, QwenImageEditPlusPipeline

# Quantize transformer to NF4 (40.9 GB -> ~10 GB)
quant_config = DiffusersBitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
)

transformer_4bit = AutoModel.from_pretrained(
    "Qwen/Qwen-Image-Edit-2511",
    subfolder="transformer",
    quantization_config=quant_config,
    torch_dtype=torch.bfloat16,
)

# Load pipeline with quantized transformer, everything else in bf16
pipe = QwenImageEditPlusPipeline.from_pretrained(
    "Qwen/Qwen-Image-Edit-2511",
    transformer=transformer_4bit,
    torch_dtype=torch.bfloat16,
    device_map="auto",
)
```

**Estimated VRAM**: ~10 GB (transformer NF4) + ~16.6 GB (text encoder bf16) + ~0.25 GB (VAE) = **~27 GB peak** -- fits on 32 GB RTX 5090, but tight.

### NF4 Quantization - Both Transformer AND Text Encoder (~14 GB total)

```python
import torch
from diffusers import BitsAndBytesConfig as DiffusersBitsAndBytesConfig
from transformers import BitsAndBytesConfig as TransformersBitsAndBytesConfig
from diffusers import AutoModel, QwenImageEditPlusPipeline
from transformers import Qwen2_5_VLForConditionalGeneration

# Quantize text encoder to NF4 (16.6 GB -> ~4 GB)
text_encoder_quant = TransformersBitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
)

text_encoder_4bit = Qwen2_5_VLForConditionalGeneration.from_pretrained(
    "Qwen/Qwen-Image-Edit-2511",
    subfolder="text_encoder",
    quantization_config=text_encoder_quant,
    torch_dtype=torch.bfloat16,
)

# Quantize transformer to NF4 (40.9 GB -> ~10 GB)
transformer_quant = DiffusersBitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
)

transformer_4bit = AutoModel.from_pretrained(
    "Qwen/Qwen-Image-Edit-2511",
    subfolder="transformer",
    quantization_config=transformer_quant,
    torch_dtype=torch.bfloat16,
)

# Load pipeline with both quantized components
pipe = QwenImageEditPlusPipeline.from_pretrained(
    "Qwen/Qwen-Image-Edit-2511",
    transformer=transformer_4bit,
    text_encoder=text_encoder_4bit,
    torch_dtype=torch.bfloat16,
    device_map="auto",
)
```

**Estimated VRAM**: ~10 GB (transformer NF4) + ~4 GB (text encoder NF4) + ~0.25 GB (VAE) = **~14.3 GB** -- very comfortable on 32 GB.

### INT8 Variant (Better Quality, More VRAM)

```python
# Same pattern, just use load_in_8bit=True instead
transformer_quant = DiffusersBitsAndBytesConfig(load_in_8bit=True)
text_encoder_quant = TransformersBitsAndBytesConfig(load_in_8bit=True)
```

**Estimated VRAM with INT8**: ~20 GB (transformer) + ~8 GB (text encoder) = **~28 GB** -- fits on 32 GB.

### Double Quantization (Extra Memory Savings)

```python
quant_config = DiffusersBitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,  # saves additional ~0.4 bits/param
)
```

---

## Option 2: Pre-Quantized FP8 Variants (Single-File Loading)

Several FP8 repos exist. The most popular is `drbaph/Qwen-Image-Edit-2511-FP8` (3.47M downloads).

**Key detail**: These FP8 files contain the **transformer only** (20.4 GB file = half of 40.9 GB bf16 transformer). You still need the original repo for the text encoder, VAE, etc.

### Loading FP8 Transformer via from_single_file

```python
import torch
from huggingface_hub import hf_hub_download
from diffusers import QwenImageTransformer2DModel, QwenImageEditPlusPipeline

ckpt_id = "Qwen/Qwen-Image-Edit-2511"

# Download FP8 transformer checkpoint
model_path = hf_hub_download(
    repo_id="drbaph/Qwen-Image-Edit-2511-FP8",
    filename="qwen_image_edit_2511_fp8_e4m3fn.safetensors",
)

# Load transformer from single file with config from original repo
transformer = QwenImageTransformer2DModel.from_single_file(
    model_path,
    config=ckpt_id,
    subfolder="transformer",
    torch_dtype=torch.float16,
)

# Enable layerwise casting for actual FP8 memory savings
transformer.enable_layerwise_casting(
    storage_dtype=torch.float8_e4m3fn,
    compute_dtype=torch.bfloat16,
)

# Load full pipeline, substituting the FP8 transformer
pipe = QwenImageEditPlusPipeline.from_pretrained(
    ckpt_id,
    transformer=transformer,
    torch_dtype=torch.bfloat16,
)
pipe.enable_model_cpu_offload()
```

**IMPORTANT**: Without `enable_layerwise_casting()`, the FP8 weights get upcast to float16 on load and you get zero memory savings. The layerwise casting keeps weights in FP8 storage and only upcasts during computation.

**Estimated VRAM**: ~20 GB (transformer FP8) + text encoder needs to be offloaded = works with `enable_model_cpu_offload()` but text encoder still needs to transit through VRAM.

### Available FP8 Repos

| Repo | Downloads | Notes |
|------|-----------|-------|
| `drbaph/Qwen-Image-Edit-2511-FP8` | 3.47M | Most popular, fp8_e4m3fn |
| `1038lab/Qwen-Image-Edit-2511-FP8` | 10.3K | fp8_e4m3fn |
| `xms991/Qwen-Image-Edit-2511-fp8-e4m3fn` | 41 | fp8_e4m3fn, verified in diffusers issue #12891 |

---

## Option 3: GGUF Quantization (Transformer Only)

`unsloth/Qwen-Image-Edit-2511-GGUF` provides the transformer in multiple GGUF quantization levels. Diffusers supports GGUF via `from_single_file` with `GGUFQuantizationConfig`.

### Available GGUF Quantizations

| Quant | File Size | Estimated VRAM |
|-------|-----------|----------------|
| Q2_K | 7.5 GB | ~8 GB |
| Q3_K_M | 9.9 GB | ~10 GB |
| Q4_K_M | 13.2 GB | ~14 GB |
| Q5_K_M | 15.0 GB | ~16 GB |
| Q6_K | 16.9 GB | ~17 GB |
| Q8_0 | 21.8 GB | ~22 GB |
| BF16 | 40.9 GB | ~41 GB |

### Loading GGUF in Diffusers

```python
import torch
from huggingface_hub import hf_hub_download
from diffusers import (
    QwenImageTransformer2DModel,
    QwenImageEditPlusPipeline,
    GGUFQuantizationConfig,
)

# Download Q4_K_M GGUF (good quality/size balance)
gguf_path = hf_hub_download(
    repo_id="unsloth/Qwen-Image-Edit-2511-GGUF",
    filename="Qwen-Image-Edit-2511-Q4_K_M.gguf",
)

# Load transformer from GGUF
transformer = QwenImageTransformer2DModel.from_single_file(
    gguf_path,
    config="Qwen/Qwen-Image-Edit-2511",
    subfolder="transformer",
    quantization_config=GGUFQuantizationConfig(compute_dtype=torch.bfloat16),
    torch_dtype=torch.bfloat16,
)

# Build pipeline with quantized transformer
pipe = QwenImageEditPlusPipeline.from_pretrained(
    "Qwen/Qwen-Image-Edit-2511",
    transformer=transformer,
    torch_dtype=torch.bfloat16,
)
pipe.enable_model_cpu_offload()
```

**Note**: GGUF weights stay in low-memory dtype (torch.uint8) and are dynamically dequantized during forward pass. For faster inference, install optimized CUDA kernels:

```bash
pip install -U kernels
export DIFFUSERS_GGUF_CUDA_KERNELS=true
```

**Estimated VRAM with Q4_K_M**: ~14 GB (transformer) + text encoder via CPU offload = fits comfortably.

---

## Option 4: TorchAO Quantization (Native PyTorch)

TorchAO provides quantization built into PyTorch. Works with both the diffusers transformer and the transformers text encoder.

```python
import torch
from diffusers import QwenImageEditPlusPipeline, PipelineQuantizationConfig, TorchAoConfig
from torchao.quantization import Int4WeightOnlyConfig

pipeline_quant_config = PipelineQuantizationConfig(
    quant_mapping={
        "transformer": TorchAoConfig(Int4WeightOnlyConfig(group_size=128)),
    }
)

pipe = QwenImageEditPlusPipeline.from_pretrained(
    "Qwen/Qwen-Image-Edit-2511",
    quantization_config=pipeline_quant_config,
    torch_dtype=torch.bfloat16,
    device_map="cuda",
)
```

TorchAO also supports FP8 on GPUs with compute capability >= 8.9 (RTX 5090 qualifies):

```python
from torchao.quantization import Float8WeightOnlyConfig

pipeline_quant_config = PipelineQuantizationConfig(
    quant_mapping={
        "transformer": TorchAoConfig(Float8WeightOnlyConfig()),
    }
)
```

---

## Option 5: SDNQ (uint4 + SVD) for Diffusers

```python
# pip install sdnq
import torch
import diffusers
from sdnq.common import use_torch_compile as triton_is_available
from sdnq.loader import apply_sdnq_options_to_model

pipe = diffusers.QwenImageEditPlusPipeline.from_pretrained(
    "Disty0/Qwen-Image-Edit-2511-SDNQ-uint4-svd-r32",
    torch_dtype=torch.bfloat16,
)

if triton_is_available and torch.cuda.is_available():
    pipe.transformer = apply_sdnq_options_to_model(pipe.transformer, use_quantized_matmul=True)
    pipe.text_encoder = apply_sdnq_options_to_model(pipe.text_encoder, use_quantized_matmul=True)

pipe.enable_model_cpu_offload()
```

---

## Option 6: Distilled Lightning Model (Fewer Steps, Not Quantization)

`lightx2v/Qwen-Image-Edit-2511-Lightning` uses step distillation to reduce inference from 40 steps to 4 steps (~10x faster). This is complementary to quantization -- you can combine a quantized model with the Lightning LoRA for maximum speed.

**Available weights**: bf16, fp32, and fp8_e4m3fn_scaled variants.

---

## Recommended Strategy for RTX 5090 (32 GB)

### Best Balance: BitsAndBytes NF4 Transformer + CPU-Offloaded Text Encoder

```python
import torch
from PIL import Image
from diffusers import BitsAndBytesConfig as DiffusersBitsAndBytesConfig
from diffusers import AutoModel, QwenImageEditPlusPipeline

# NF4 quantize the transformer (40.9 GB -> ~10 GB)
quant_config = DiffusersBitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
)

transformer_4bit = AutoModel.from_pretrained(
    "Qwen/Qwen-Image-Edit-2511",
    subfolder="transformer",
    quantization_config=quant_config,
    torch_dtype=torch.bfloat16,
)

# Load pipeline - text encoder in bf16, transformer in NF4, VAE in bf16
pipe = QwenImageEditPlusPipeline.from_pretrained(
    "Qwen/Qwen-Image-Edit-2511",
    transformer=transformer_4bit,
    torch_dtype=torch.bfloat16,
)

# CPU offload moves components to GPU only when needed
# Text encoder runs first (brief GPU time), then transformer takes over
pipe.enable_model_cpu_offload()

# Generate
image = Image.open("input.png")
inputs = {
    "image": [image],
    "prompt": "Change the background to a sunset",
    "generator": torch.manual_seed(42),
    "true_cfg_scale": 4.0,
    "negative_prompt": " ",
    "num_inference_steps": 40,
    "guidance_scale": 1.0,
}
with torch.inference_mode():
    output = pipe(**inputs)
    output.images[0].save("output.png")
```

**Why this works**: With `enable_model_cpu_offload()`, only one component is on GPU at a time. The text encoder (~16.6 GB bf16) runs first, gets offloaded, then the NF4 transformer (~10 GB) runs the diffusion loop entirely on GPU. Since the transformer is the component that runs iteratively (40 steps), keeping it quantized on GPU avoids the slow CPU<->GPU transfer problem. The text encoder only runs once, so its brief CPU->GPU->CPU transfer is negligible.

**Expected speedup vs full bf16 + cpu_offload**: Massive. The current 25-minute runtime is because the full 40.9 GB transformer gets transferred between CPU and GPU every step. With NF4, the 10 GB transformer stays on GPU permanently.

### Alternative: Quantize BOTH for Maximum VRAM Headroom

If you also quantize the text encoder to NF4, total peak VRAM drops to ~14 GB, leaving massive headroom for larger images or batch generation.

### If Quality is Critical: INT8 or FP8

- **INT8 transformer**: ~20 GB, better quality than NF4, still fits with CPU offload for text encoder
- **FP8 pre-quantized** (drbaph repo): ~20 GB transformer, requires `enable_layerwise_casting()`, good quality

---

## Summary Comparison

| Method | Transformer VRAM | Text Encoder | Total Peak VRAM | Speed | Quality | Complexity |
|--------|-----------------|--------------|-----------------|-------|---------|------------|
| bf16 (baseline) | 40.9 GB | 16.6 GB | ~57 GB | N/A (doesn't fit) | Best | Low |
| bf16 + cpu_offload | 40.9 GB (shared) | 16.6 GB (shared) | ~41 GB shared | 25 min | Best | Low |
| **BnB NF4 transformer + offload** | **~10 GB** | **16.6 GB (offloaded)** | **~17 GB peak** | **Fast** | **Good** | **Medium** |
| BnB NF4 both | ~10 GB | ~4 GB | ~14 GB | Fast | Good | Medium |
| BnB INT8 transformer + offload | ~20 GB | 16.6 GB (offloaded) | ~21 GB peak | Fast | Better | Medium |
| FP8 single-file + layerwise | ~20 GB | 16.6 GB (offloaded) | ~21 GB peak | Fast | Better | Medium |
| GGUF Q4_K_M + offload | ~14 GB | 16.6 GB (offloaded) | ~17 GB peak | Fast* | Good | Medium |
| TorchAO int4wo | ~10 GB | 16.6 GB (offloaded) | ~17 GB peak | Fast | Good | Low |
| SDNQ uint4 | Small | Small | Small | Fast | Good | Medium |

*GGUF is dynamically dequantized per-layer; install `kernels` package for CUDA-accelerated dequant.

## Dependencies

```bash
pip install -U diffusers transformers accelerate bitsandbytes
# For GGUF:
pip install -U gguf kernels
# For TorchAO:
pip install -U torch torchao
# For SDNQ:
pip install -U sdnq
```

Requires diffusers >= 0.36.0 (for `QwenImageEditPlusPipeline` support). Install from main for latest fixes:
```bash
pip install git+https://github.com/huggingface/diffusers
```
