"""Phase 1: Test baseline models with standard game art prompts."""

import os
import sys
import time
import json
import gc
import torch
from pathlib import Path

# Add scripts dir to path
sys.path.insert(0, os.path.dirname(__file__))
from test_prompts import GAME_ART_PROMPTS

OUTPUT_BASE = Path("/workspace/ImageGenTesting/outputs/phase1_baselines")
RESULTS_FILE = Path("/workspace/ImageGenTesting/results/phase1_results.json")

# Ensure output dirs exist
OUTPUT_BASE.mkdir(parents=True, exist_ok=True)
RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)


def clear_gpu():
    """Free GPU memory between model loads."""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()


def get_gpu_mem():
    """Return current GPU memory usage in MB."""
    if torch.cuda.is_available():
        return torch.cuda.memory_allocated() / 1024**2
    return 0


def test_flux_schnell():
    """Test FLUX.1 schnell - Apache 2.0, fast, high quality."""
    from diffusers import FluxPipeline

    model_id = "black-forest-labs/FLUX.1-schnell"
    model_name = "flux1_schnell"
    output_dir = OUTPUT_BASE / model_name
    output_dir.mkdir(exist_ok=True)

    print(f"\n{'='*60}")
    print(f"Loading {model_id}...")
    print(f"{'='*60}")

    pipe = FluxPipeline.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
    )
    pipe = pipe.to("cuda")

    print(f"Model loaded. GPU memory: {get_gpu_mem():.0f} MB")

    results = {}
    for prompt_key, prompt_data in GAME_ART_PROMPTS.items():
        print(f"\n  Generating: {prompt_key} ({prompt_data['use_case']})")
        start = time.time()

        # FLUX schnell uses 4 steps, no negative prompt support in base pipeline
        image = pipe(
            prompt=prompt_data["prompt"],
            num_inference_steps=4,
            guidance_scale=0.0,  # schnell uses guidance_scale=0
            height=1024,
            width=1024,
            generator=torch.Generator("cuda").manual_seed(42),
        ).images[0]

        elapsed = time.time() - start
        filepath = output_dir / f"{prompt_key}.png"
        image.save(filepath)

        results[prompt_key] = {
            "time_seconds": round(elapsed, 2),
            "file": str(filepath),
            "gpu_mem_mb": round(get_gpu_mem()),
        }
        print(f"  -> Saved to {filepath} ({elapsed:.1f}s)")

    del pipe
    clear_gpu()
    return model_name, results


def test_flux_dev():
    """Test FLUX.1 dev - higher quality, more steps."""
    from diffusers import FluxPipeline

    model_id = "black-forest-labs/FLUX.1-dev"
    model_name = "flux1_dev"
    output_dir = OUTPUT_BASE / model_name
    output_dir.mkdir(exist_ok=True)

    print(f"\n{'='*60}")
    print(f"Loading {model_id}...")
    print(f"{'='*60}")

    pipe = FluxPipeline.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
    )
    pipe = pipe.to("cuda")

    print(f"Model loaded. GPU memory: {get_gpu_mem():.0f} MB")

    results = {}
    for prompt_key, prompt_data in GAME_ART_PROMPTS.items():
        print(f"\n  Generating: {prompt_key} ({prompt_data['use_case']})")
        start = time.time()

        image = pipe(
            prompt=prompt_data["prompt"],
            num_inference_steps=28,
            guidance_scale=3.5,
            height=1024,
            width=1024,
            generator=torch.Generator("cuda").manual_seed(42),
        ).images[0]

        elapsed = time.time() - start
        filepath = output_dir / f"{prompt_key}.png"
        image.save(filepath)

        results[prompt_key] = {
            "time_seconds": round(elapsed, 2),
            "file": str(filepath),
            "gpu_mem_mb": round(get_gpu_mem()),
        }
        print(f"  -> Saved to {filepath} ({elapsed:.1f}s)")

    del pipe
    clear_gpu()
    return model_name, results


def test_sdxl():
    """Test SDXL - huge LoRA ecosystem, commercial-friendly."""
    from diffusers import StableDiffusionXLPipeline

    model_id = "stabilityai/stable-diffusion-xl-base-1.0"
    model_name = "sdxl_base"
    output_dir = OUTPUT_BASE / model_name
    output_dir.mkdir(exist_ok=True)

    print(f"\n{'='*60}")
    print(f"Loading {model_id}...")
    print(f"{'='*60}")

    pipe = StableDiffusionXLPipeline.from_pretrained(
        model_id,
        torch_dtype=torch.float16,
        variant="fp16",
        use_safetensors=True,
    )
    pipe = pipe.to("cuda")

    print(f"Model loaded. GPU memory: {get_gpu_mem():.0f} MB")

    results = {}
    for prompt_key, prompt_data in GAME_ART_PROMPTS.items():
        print(f"\n  Generating: {prompt_key} ({prompt_data['use_case']})")
        start = time.time()

        image = pipe(
            prompt=prompt_data["prompt"],
            negative_prompt=prompt_data["negative"],
            num_inference_steps=30,
            guidance_scale=7.5,
            height=1024,
            width=1024,
            generator=torch.Generator("cuda").manual_seed(42),
        ).images[0]

        elapsed = time.time() - start
        filepath = output_dir / f"{prompt_key}.png"
        image.save(filepath)

        results[prompt_key] = {
            "time_seconds": round(elapsed, 2),
            "file": str(filepath),
            "gpu_mem_mb": round(get_gpu_mem()),
        }
        print(f"  -> Saved to {filepath} ({elapsed:.1f}s)")

    del pipe
    clear_gpu()
    return model_name, results


def test_pixart_sigma():
    """Test PixArt-Sigma - ultra lightweight, commercial-friendly."""
    from diffusers import PixArtSigmaPipeline

    model_id = "PixArt-alpha/PixArt-Sigma-XL-2-1024-MS"
    model_name = "pixart_sigma"
    output_dir = OUTPUT_BASE / model_name
    output_dir.mkdir(exist_ok=True)

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

    results = {}
    for prompt_key, prompt_data in GAME_ART_PROMPTS.items():
        print(f"\n  Generating: {prompt_key} ({prompt_data['use_case']})")
        start = time.time()

        image = pipe(
            prompt=prompt_data["prompt"],
            negative_prompt=prompt_data["negative"],
            num_inference_steps=20,
            guidance_scale=4.5,
            height=1024,
            width=1024,
            generator=torch.Generator("cuda").manual_seed(42),
        ).images[0]

        elapsed = time.time() - start
        filepath = output_dir / f"{prompt_key}.png"
        image.save(filepath)

        results[prompt_key] = {
            "time_seconds": round(elapsed, 2),
            "file": str(filepath),
            "gpu_mem_mb": round(get_gpu_mem()),
        }
        print(f"  -> Saved to {filepath} ({elapsed:.1f}s)")

    del pipe
    clear_gpu()
    return model_name, results


def main():
    all_results = {}

    # Run all four baseline models
    test_functions = [
        test_flux_schnell,
        test_flux_dev,
        test_sdxl,
        test_pixart_sigma,
    ]

    for test_fn in test_functions:
        try:
            model_name, results = test_fn()
            all_results[model_name] = {
                "prompts": results,
                "status": "success",
            }
        except Exception as e:
            print(f"\n  ERROR in {test_fn.__name__}: {e}")
            import traceback
            traceback.print_exc()
            all_results[test_fn.__name__] = {
                "status": "error",
                "error": str(e),
            }
            clear_gpu()

    # Save results
    with open(RESULTS_FILE, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n\nResults saved to {RESULTS_FILE}")

    # Print summary
    print(f"\n{'='*60}")
    print("PHASE 1 SUMMARY")
    print(f"{'='*60}")
    for model, data in all_results.items():
        if data["status"] == "success":
            times = [p["time_seconds"] for p in data["prompts"].values()]
            avg = sum(times) / len(times)
            mem = max(p["gpu_mem_mb"] for p in data["prompts"].values())
            print(f"  {model}: avg {avg:.1f}s/image, peak {mem}MB VRAM")
        else:
            print(f"  {model}: FAILED - {data.get('error', 'unknown')}")


if __name__ == "__main__":
    main()
