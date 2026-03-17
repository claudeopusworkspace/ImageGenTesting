"""Phase 2: Test game-art LoRAs on SDXL and FLUX."""

import os
import sys
import time
import json
import gc
import torch
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from test_prompts import GAME_ART_PROMPTS

OUTPUT_BASE = Path("/workspace/ImageGenTesting/outputs/phase2_loras")
RESULTS_FILE = Path("/workspace/ImageGenTesting/results/phase2_results.json")
OUTPUT_BASE.mkdir(parents=True, exist_ok=True)


def clear_gpu():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()


def get_gpu_mem():
    if torch.cuda.is_available():
        return torch.cuda.memory_allocated() / 1024**2
    return 0


def generate_all(pipe, model_name, gen_kwargs, supports_negative=True, prompt_prefix="", prompt_suffix=""):
    output_dir = OUTPUT_BASE / model_name
    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    for prompt_key, prompt_data in GAME_ART_PROMPTS.items():
        print(f"  Generating: {prompt_key}")
        start = time.time()
        prompt = f"{prompt_prefix}{prompt_data['prompt']}{prompt_suffix}"
        kwargs = {**gen_kwargs, "prompt": prompt,
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
        print(f"    -> {elapsed:.1f}s")
    return results


def test_sdxl_with_lora(lora_id, lora_name, trigger_word="", lora_scale=1.0):
    """Load SDXL base + a LoRA and run all prompts."""
    from diffusers import StableDiffusionXLPipeline

    print(f"\n{'='*60}")
    print(f"SDXL + {lora_name} ({lora_id})")
    print(f"{'='*60}")

    pipe = StableDiffusionXLPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        torch_dtype=torch.float16, variant="fp16", use_safetensors=True,
    )
    pipe = pipe.to("cuda")

    # Load LoRA
    print(f"  Loading LoRA: {lora_id}")
    try:
        pipe.load_lora_weights(lora_id)
        pipe.fuse_lora(lora_scale=lora_scale)
    except Exception as e:
        print(f"  Failed to load LoRA: {e}")
        # Try without fusing
        try:
            pipe.load_lora_weights(lora_id)
        except Exception as e2:
            print(f"  Also failed unfused: {e2}")
            del pipe
            clear_gpu()
            return None

    print(f"  Loaded. GPU: {get_gpu_mem():.0f}MB")

    prefix = f"{trigger_word}, " if trigger_word else ""
    results = generate_all(pipe, f"sdxl_{lora_name}", {
        "num_inference_steps": 30, "guidance_scale": 7.5,
        "height": 1024, "width": 1024,
    }, supports_negative=True, prompt_prefix=prefix)

    del pipe
    clear_gpu()
    return results


def test_sdxl_pixel_art_checkpoint():
    """Test nerijs/pixel-art-xl - it's a LoRA, not a full checkpoint."""
    from diffusers import StableDiffusionXLPipeline

    model_id = "nerijs/pixel-art-xl"
    print(f"\n{'='*60}")
    print(f"Pixel Art XL LoRA ({model_id})")
    print(f"{'='*60}")

    pipe = StableDiffusionXLPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        torch_dtype=torch.float16, variant="fp16", use_safetensors=True,
    )
    pipe = pipe.to("cuda")
    pipe.load_lora_weights(model_id)
    print(f"  Loaded. GPU: {get_gpu_mem():.0f}MB")

    results = generate_all(pipe, "sdxl_pixel_art_xl", {
        "num_inference_steps": 30, "guidance_scale": 7.5,
        "height": 1024, "width": 1024,
    }, supports_negative=True, prompt_prefix="pixel art, ")

    del pipe
    clear_gpu()
    return results


def test_flux_with_lora(lora_id, lora_name, trigger_word="", lora_scale=1.0):
    """Load FLUX.1-dev (4-bit) + a LoRA."""
    from diffusers import FluxPipeline, FluxTransformer2DModel, BitsAndBytesConfig

    print(f"\n{'='*60}")
    print(f"FLUX.1-dev 4-bit + {lora_name} ({lora_id})")
    print(f"{'='*60}")

    flux_id = "camenduru/FLUX.1-dev-ungated"
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    transformer = FluxTransformer2DModel.from_pretrained(
        flux_id, subfolder="transformer",
        quantization_config=quantization_config,
        torch_dtype=torch.bfloat16,
    )
    pipe = FluxPipeline.from_pretrained(
        flux_id, transformer=transformer, torch_dtype=torch.bfloat16,
    )
    pipe.enable_model_cpu_offload()

    print(f"  Loading LoRA: {lora_id}")
    try:
        pipe.load_lora_weights(lora_id)
    except Exception as e:
        print(f"  Failed to load LoRA: {e}")
        del pipe, transformer
        clear_gpu()
        return None

    print(f"  Loaded. GPU: {get_gpu_mem():.0f}MB")

    prefix = f"{trigger_word}, " if trigger_word else ""
    results = generate_all(pipe, f"flux_{lora_name}", {
        "num_inference_steps": 20, "guidance_scale": 3.5,
        "height": 1024, "width": 1024,
    }, supports_negative=False, prompt_prefix=prefix)

    del pipe, transformer
    clear_gpu()
    return results


def main():
    all_results = {}

    # ---- SDXL LoRAs ---- #

    # 1. PixelArtRedmond (SDXL LoRA)
    r = test_sdxl_with_lora(
        "artificialguybr/PixelArtRedmond",
        "pixelart_redmond", trigger_word="Pixel Art", lora_scale=0.9)
    if r:
        all_results["sdxl_pixelart_redmond"] = {"prompts": r, "status": "success"}

    # 2. Pixel Art XL (full checkpoint)
    try:
        r = test_sdxl_pixel_art_checkpoint()
        if r:
            all_results["sdxl_pixel_art_xl"] = {"prompts": r, "status": "success"}
    except Exception as e:
        print(f"  pixel-art-xl FAILED: {e}")
        clear_gpu()

    # ---- FLUX LoRAs ---- #

    # 3. Game Assets LoRA v2 (FLUX)
    r = test_flux_with_lora(
        "gokaygokay/Flux-Game-Assets-LoRA-v2",
        "game_assets_v2", trigger_word="wbgmsst, white background", lora_scale=1.0)
    if r:
        all_results["flux_game_assets_v2"] = {"prompts": r, "status": "success"}

    # 4. 2D Game Assets LoRA (FLUX)
    r = test_flux_with_lora(
        "gokaygokay/Flux-2D-Game-Assets-LoRA",
        "2d_game_assets", trigger_word="", lora_scale=1.0)
    if r:
        all_results["flux_2d_game_assets"] = {"prompts": r, "status": "success"}

    # 5. Modern Pixel Art (FLUX)
    r = test_flux_with_lora(
        "UmeAiRT/FLUX.1-dev-LoRA-Modern_Pixel_art",
        "modern_pixel_art", trigger_word="umempart", lora_scale=1.0)
    if r:
        all_results["flux_modern_pixel_art"] = {"prompts": r, "status": "success"}

    # Save results
    with open(RESULTS_FILE, "w") as f:
        json.dump(all_results, f, indent=2)

    # Summary
    print(f"\n{'='*60}")
    print("PHASE 2 SUMMARY")
    print(f"{'='*60}")
    for model, data in all_results.items():
        if data.get("status") == "success":
            times = [p["time_seconds"] for p in data["prompts"].values()]
            avg = sum(times) / len(times)
            mem = max(p["gpu_mem_mb"] for p in data["prompts"].values())
            print(f"  {model}: avg {avg:.1f}s/image, peak {mem}MB VRAM")
        else:
            print(f"  {model}: FAILED")


if __name__ == "__main__":
    main()
