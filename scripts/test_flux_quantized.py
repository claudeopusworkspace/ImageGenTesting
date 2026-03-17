"""Test FLUX.1-dev with 4-bit quantized transformer."""

import os
import sys
import time
import json
import gc
import torch
from pathlib import Path
from diffusers import FluxPipeline, FluxTransformer2DModel, BitsAndBytesConfig

sys.path.insert(0, os.path.dirname(__file__))
from test_prompts import GAME_ART_PROMPTS

OUTPUT_BASE = Path("/workspace/ImageGenTesting/outputs/phase1_baselines")
RESULTS_FILE = Path("/workspace/ImageGenTesting/results/phase1_results.json")

model_id = "camenduru/FLUX.1-dev-ungated"

print(f"Loading transformer from {model_id} with 4-bit quantization...")

# Quantize just the transformer (the large component)
quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
)

transformer = FluxTransformer2DModel.from_pretrained(
    model_id,
    subfolder="transformer",
    quantization_config=quantization_config,
    torch_dtype=torch.bfloat16,
)

print(f"Transformer loaded. Building pipeline...")

pipe = FluxPipeline.from_pretrained(
    model_id,
    transformer=transformer,
    torch_dtype=torch.bfloat16,
)
pipe.enable_model_cpu_offload()

gpu_mem = torch.cuda.memory_allocated() / 1024**2
print(f"Pipeline ready. GPU memory: {gpu_mem:.0f} MB")

# Generate all test images
output_dir = OUTPUT_BASE / "flux1_dev_4bit"
output_dir.mkdir(parents=True, exist_ok=True)

results = {}
for prompt_key, prompt_data in GAME_ART_PROMPTS.items():
    print(f"\n  Generating: {prompt_key} ({prompt_data['use_case']})")
    start = time.time()

    image = pipe(
        prompt=prompt_data["prompt"],
        num_inference_steps=20,
        guidance_scale=3.5,
        height=1024,
        width=1024,
        generator=torch.Generator("cuda").manual_seed(42),
    ).images[0]

    elapsed = time.time() - start
    filepath = output_dir / f"{prompt_key}.png"
    image.save(filepath)
    mem = torch.cuda.memory_allocated() / 1024**2
    results[prompt_key] = {
        "time_seconds": round(elapsed, 2),
        "file": str(filepath),
        "gpu_mem_mb": round(mem),
    }
    print(f"  -> {filepath} ({elapsed:.1f}s, {mem:.0f}MB VRAM)")

# Save results
with open(RESULTS_FILE) as f:
    all_results = json.load(f)

all_results["flux1_dev_4bit"] = {
    "prompts": results,
    "status": "success",
    "model_id": model_id,
    "note": "4-bit NF4 quantized transformer, CPU offload",
}

with open(RESULTS_FILE, "w") as f:
    json.dump(all_results, f, indent=2)

times = [r["time_seconds"] for r in results.values()]
mems = [r["gpu_mem_mb"] for r in results.values()]
print(f"\nFLUX.1-dev 4-bit: avg {sum(times)/len(times):.1f}s/image, peak {max(mems)}MB VRAM")
