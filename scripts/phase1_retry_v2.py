"""Retry failed Phase 1 models with proper memory management."""

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
    """Run all prompts through a pipeline."""
    output_dir = OUTPUT_BASE / model_name
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    for prompt_key, prompt_data in GAME_ART_PROMPTS.items():
        print(f"\n  Generating: {prompt_key} ({prompt_data['use_case']})")
        start = time.time()

        kwargs = {**gen_kwargs}
        kwargs["prompt"] = prompt_data["prompt"]
        kwargs["generator"] = torch.Generator("cuda").manual_seed(42)
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


def test_flux_dev():
    """FLUX.1-dev with CPU offloading to fit in VRAM."""
    from diffusers import FluxPipeline

    model_id = "camenduru/FLUX.1-dev-ungated"
    print(f"\n{'='*60}")
    print(f"Loading {model_id} (with CPU offload)...")
    print(f"{'='*60}")

    pipe = FluxPipeline.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
    )
    # CPU offload: moves components to GPU only when needed
    # Much better than .to("cuda") when model barely fits
    pipe.enable_model_cpu_offload()
    print(f"Model loaded with CPU offload. GPU memory: {get_gpu_mem():.0f} MB")

    results = generate_all(pipe, "flux1_dev", {
        "num_inference_steps": 20,
        "guidance_scale": 3.5,
        "height": 1024,
        "width": 1024,
    }, supports_negative=False)

    del pipe
    clear_gpu()
    return results


def test_flux_schnell():
    """Try to find and test FLUX.1-schnell."""
    from diffusers import FluxPipeline

    # Try ungated schnell sources
    model_ids = [
        "black-forest-labs/FLUX.1-schnell",
    ]

    for model_id in model_ids:
        print(f"\n{'='*60}")
        print(f"Trying {model_id} (with CPU offload)...")
        print(f"{'='*60}")
        try:
            pipe = FluxPipeline.from_pretrained(
                model_id,
                torch_dtype=torch.bfloat16,
            )
            pipe.enable_model_cpu_offload()
            print(f"Loaded! GPU memory: {get_gpu_mem():.0f} MB")

            results = generate_all(pipe, "flux1_schnell", {
                "num_inference_steps": 4,
                "guidance_scale": 0.0,
                "height": 1024,
                "width": 1024,
            }, supports_negative=False)

            del pipe
            clear_gpu()
            return results
        except Exception as e:
            print(f"  Failed: {e}")
            clear_gpu()

    print("  All schnell sources failed. Skipping.")
    return None


def test_pixart_sigma():
    """PixArt-Sigma with tiktoken now installed."""
    from diffusers import PixArtSigmaPipeline

    model_id = "PixArt-alpha/PixArt-Sigma-XL-2-1024-MS"
    print(f"\n{'='*60}")
    print(f"Loading {model_id}...")
    print(f"{'='*60}")

    pipe = PixArtSigmaPipeline.from_pretrained(
        model_id,
        torch_dtype=torch.float16,
        use_safetensors=True,
    )
    pipe = pipe.to("cuda")
    print(f"Model loaded. GPU memory: {get_gpu_mem():.0f} MB")

    results = generate_all(pipe, "pixart_sigma", {
        "num_inference_steps": 20,
        "guidance_scale": 4.5,
        "height": 1024,
        "width": 1024,
    }, supports_negative=True)

    del pipe
    clear_gpu()
    return results


def main():
    # PixArt-Sigma first (smallest, quickest)
    print("\n" + "="*60)
    print("TESTING PIXART-SIGMA")
    print("="*60)
    try:
        results = test_pixart_sigma()
        all_results["pixart_sigma"] = {"prompts": results, "status": "success"}
    except Exception as e:
        print(f"  PixArt-Sigma FAILED: {e}")
        import traceback; traceback.print_exc()
        clear_gpu()

    # FLUX.1-schnell
    print("\n" + "="*60)
    print("TESTING FLUX.1-SCHNELL")
    print("="*60)
    try:
        results = test_flux_schnell()
        if results:
            all_results["flux1_schnell"] = {"prompts": results, "status": "success"}
        else:
            all_results["flux1_schnell"] = {"status": "skipped", "reason": "gated, no ungated mirror found"}
    except Exception as e:
        print(f"  FLUX.1-schnell FAILED: {e}")
        clear_gpu()

    # FLUX.1-dev (largest, use CPU offload)
    print("\n" + "="*60)
    print("TESTING FLUX.1-DEV (CPU offload)")
    print("="*60)
    try:
        results = test_flux_dev()
        all_results["flux1_dev"] = {"prompts": results, "status": "success", "model_id": "camenduru/FLUX.1-dev-ungated"}
    except Exception as e:
        print(f"  FLUX.1-dev FAILED: {e}")
        import traceback; traceback.print_exc()
        clear_gpu()

    # Save
    with open(RESULTS_FILE, "w") as f:
        json.dump(all_results, f, indent=2)

    # Summary
    print(f"\n{'='*60}")
    print("UPDATED PHASE 1 SUMMARY")
    print(f"{'='*60}")
    for model, data in all_results.items():
        if data.get("status") == "success" and "prompts" in data:
            times = [p["time_seconds"] for p in data["prompts"].values()]
            avg = sum(times) / len(times)
            mem = max(p["gpu_mem_mb"] for p in data["prompts"].values())
            print(f"  {model}: avg {avg:.1f}s/image, peak {mem}MB VRAM")
        else:
            reason = data.get("error") or data.get("reason", "unknown")
            print(f"  {model}: {data.get('status', 'FAILED')} - {reason}")


if __name__ == "__main__":
    main()
