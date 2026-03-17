"""Retry: PixArt-Sigma (protobuf fix) and FLUX.1-dev (4-bit quantized)."""

import os
import sys
import time
import json
import gc
import torch
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from test_prompts import GAME_ART_PROMPTS

OUTPUT_BASE = Path("/workspace/ImageGenTesting/outputs/phase1_baselines")
RESULTS_FILE = Path("/workspace/ImageGenTesting/results/phase1_results.json")

with open(RESULTS_FILE) as f:
    all_results = json.load(f)


def clear_gpu():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()


def get_gpu_mem():
    if torch.cuda.is_available():
        return torch.cuda.memory_allocated() / 1024**2
    return 0


def generate_all(pipe, model_name, gen_kwargs, supports_negative=False):
    output_dir = OUTPUT_BASE / model_name
    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    for prompt_key, prompt_data in GAME_ART_PROMPTS.items():
        print(f"\n  Generating: {prompt_key} ({prompt_data['use_case']})")
        start = time.time()
        kwargs = {**gen_kwargs, "prompt": prompt_data["prompt"],
                  "generator": torch.Generator("cuda").manual_seed(42)}
        if supports_negative:
            kwargs["negative_prompt"] = prompt_data["negative"]
        image = pipe(**kwargs).images[0]
        elapsed = time.time() - start
        filepath = output_dir / f"{prompt_key}.png"
        image.save(filepath)
        results[prompt_key] = {
            "time_seconds": round(elapsed, 2),
            "file": str(filepath),
            "gpu_mem_mb": round(get_gpu_mem()),
        }
        print(f"  -> {filepath} ({elapsed:.1f}s, {get_gpu_mem():.0f}MB VRAM)")
    return results


def test_pixart_sigma():
    from diffusers import PixArtSigmaPipeline
    model_id = "PixArt-alpha/PixArt-Sigma-XL-2-1024-MS"
    print(f"\nLoading {model_id}...")
    pipe = PixArtSigmaPipeline.from_pretrained(
        model_id, torch_dtype=torch.float16, use_safetensors=True)
    pipe = pipe.to("cuda")
    print(f"Loaded. GPU memory: {get_gpu_mem():.0f} MB")
    return generate_all(pipe, "pixart_sigma", {
        "num_inference_steps": 20, "guidance_scale": 4.5,
        "height": 1024, "width": 1024}, supports_negative=True)


def test_flux_dev_quantized():
    from diffusers import FluxPipeline, BitsAndBytesConfig

    model_id = "camenduru/FLUX.1-dev-ungated"
    print(f"\nLoading {model_id} (4-bit quantized)...")

    # 4-bit quantization reduces ~24GB model to ~6-8GB
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )

    pipe = FluxPipeline.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
        quantization_config=quantization_config,
    )
    pipe.enable_model_cpu_offload()
    print(f"Loaded. GPU memory: {get_gpu_mem():.0f} MB")

    return generate_all(pipe, "flux1_dev_4bit", {
        "num_inference_steps": 20, "guidance_scale": 3.5,
        "height": 1024, "width": 1024}, supports_negative=False)


def main():
    # PixArt-Sigma
    print("=" * 60)
    print("PIXART-SIGMA")
    print("=" * 60)
    try:
        results = test_pixart_sigma()
        all_results["pixart_sigma"] = {"prompts": results, "status": "success"}
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback; traceback.print_exc()
    clear_gpu()

    # FLUX.1-dev 4-bit
    print("\n" + "=" * 60)
    print("FLUX.1-DEV (4-bit quantized)")
    print("=" * 60)
    try:
        results = test_flux_dev_quantized()
        all_results["flux1_dev_4bit"] = {
            "prompts": results, "status": "success",
            "model_id": "camenduru/FLUX.1-dev-ungated", "note": "4-bit NF4 quantized"
        }
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback; traceback.print_exc()
    clear_gpu()

    with open(RESULTS_FILE, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n{'='*60}")
    print("PHASE 1 SUMMARY (ALL MODELS)")
    print(f"{'='*60}")
    for model, data in all_results.items():
        if data.get("status") == "success" and "prompts" in data:
            times = [p["time_seconds"] for p in data["prompts"].values()]
            avg = sum(times) / len(times)
            mem = max(p["gpu_mem_mb"] for p in data["prompts"].values())
            note = data.get("note", "")
            print(f"  {model}: avg {avg:.1f}s/image, peak {mem}MB VRAM {f'({note})' if note else ''}")
        else:
            print(f"  {model}: {data.get('status', 'FAILED')}")


if __name__ == "__main__":
    main()
