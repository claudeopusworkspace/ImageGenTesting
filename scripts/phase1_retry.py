"""Retry failed Phase 1 models: FLUX (via ungated mirrors) and PixArt-Sigma."""

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

# Load existing results
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


def run_model(model_id, model_name, pipeline_cls, pipe_kwargs, gen_kwargs):
    """Generic model runner."""
    output_dir = OUTPUT_BASE / model_name
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"Loading {model_id}...")
    print(f"{'='*60}")

    pipe = pipeline_cls.from_pretrained(model_id, **pipe_kwargs)
    pipe = pipe.to("cuda")
    print(f"Model loaded. GPU memory: {get_gpu_mem():.0f} MB")

    results = {}
    for prompt_key, prompt_data in GAME_ART_PROMPTS.items():
        print(f"\n  Generating: {prompt_key} ({prompt_data['use_case']})")
        start = time.time()

        # Build generation args
        kwargs = {**gen_kwargs}
        kwargs["prompt"] = prompt_data["prompt"]
        kwargs["generator"] = torch.Generator("cuda").manual_seed(42)

        # Only add negative_prompt if the pipeline supports it
        if hasattr(pipe, '_execution_device') or 'negative_prompt' not in str(type(pipe)):
            # Check if it's a FLUX pipeline (no negative prompt support)
            if "Flux" not in type(pipe).__name__:
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
        print(f"  -> Saved to {filepath} ({elapsed:.1f}s)")

    del pipe
    clear_gpu()
    return results


def main():
    from diffusers import FluxPipeline, PixArtSigmaPipeline

    # --- FLUX.1 schnell (try official, fall back to mirror) ---
    schnell_ids = [
        "black-forest-labs/FLUX.1-schnell",
        "ostris/FLUX.1-schnell-fp8",  # FP8 quantized, ungated
    ]
    for model_id in schnell_ids:
        try:
            results = run_model(
                model_id, "flux1_schnell", FluxPipeline,
                {"torch_dtype": torch.bfloat16},
                {"num_inference_steps": 4, "guidance_scale": 0.0,
                 "height": 1024, "width": 1024},
            )
            all_results["flux1_schnell"] = {"prompts": results, "status": "success", "model_id": model_id}
            break
        except Exception as e:
            print(f"  Failed with {model_id}: {e}")
            clear_gpu()

    # --- FLUX.1 dev (try official, fall back to ungated mirror) ---
    dev_ids = [
        "black-forest-labs/FLUX.1-dev",
        "camenduru/FLUX.1-dev-ungated",
    ]
    for model_id in dev_ids:
        try:
            results = run_model(
                model_id, "flux1_dev", FluxPipeline,
                {"torch_dtype": torch.bfloat16},
                {"num_inference_steps": 28, "guidance_scale": 3.5,
                 "height": 1024, "width": 1024},
            )
            all_results["flux1_dev"] = {"prompts": results, "status": "success", "model_id": model_id}
            break
        except Exception as e:
            print(f"  Failed with {model_id}: {e}")
            clear_gpu()

    # --- PixArt-Sigma (now with tiktoken installed) ---
    try:
        results = run_model(
            "PixArt-alpha/PixArt-Sigma-XL-2-1024-MS", "pixart_sigma",
            PixArtSigmaPipeline,
            {"torch_dtype": torch.float16, "use_safetensors": True},
            {"num_inference_steps": 20, "guidance_scale": 4.5,
             "height": 1024, "width": 1024},
        )
        all_results["pixart_sigma"] = {"prompts": results, "status": "success"}
    except Exception as e:
        print(f"  Failed PixArt-Sigma: {e}")
        import traceback
        traceback.print_exc()

    # Save updated results
    with open(RESULTS_FILE, "w") as f:
        json.dump(all_results, f, indent=2)

    # Print summary
    print(f"\n{'='*60}")
    print("UPDATED PHASE 1 SUMMARY")
    print(f"{'='*60}")
    for model, data in all_results.items():
        if data.get("status") == "success" and "prompts" in data:
            times = [p["time_seconds"] for p in data["prompts"].values()]
            avg = sum(times) / len(times)
            mem = max(p["gpu_mem_mb"] for p in data["prompts"].values())
            mid = data.get("model_id", "")
            print(f"  {model}: avg {avg:.1f}s/image, peak {mem}MB VRAM {f'({mid})' if mid else ''}")
        else:
            print(f"  {model}: FAILED - {data.get('error', 'unknown')}")


if __name__ == "__main__":
    main()
