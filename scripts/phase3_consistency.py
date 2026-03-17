"""Phase 3: Test sprite consistency, background removal, and IP-Adapter style transfer."""

import os
import sys
import time
import json
import gc
import torch
from pathlib import Path
from PIL import Image

OUTPUT_BASE = Path("/workspace/ImageGenTesting/outputs/phase3_consistency")
RESULTS_FILE = Path("/workspace/ImageGenTesting/results/phase3_results.json")
OUTPUT_BASE.mkdir(parents=True, exist_ok=True)
all_results = {}


def clear_gpu():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()


def get_gpu_mem():
    if torch.cuda.is_available():
        return torch.cuda.memory_allocated() / 1024**2
    return 0


# ============================================================
# TEST 1: Background Removal Pipeline
# ============================================================
def test_background_removal():
    """Test rembg on our best Phase 1/2 outputs to see if we can get clean transparency."""
    from rembg import remove

    print("=" * 60)
    print("TEST 1: Background Removal (rembg)")
    print("=" * 60)

    output_dir = OUTPUT_BASE / "bg_removal"
    output_dir.mkdir(exist_ok=True)

    # Test on a variety of our best outputs
    test_images = {
        "flux_pixel_sword": "/workspace/ImageGenTesting/outputs/phase1_baselines/flux1_dev_4bit/pixel_sword.png",
        "flux_character": "/workspace/ImageGenTesting/outputs/phase1_baselines/flux1_dev_4bit/character_front.png",
        "flux_enemy": "/workspace/ImageGenTesting/outputs/phase1_baselines/flux1_dev_4bit/enemy_creature.png",
        "pixart_character": "/workspace/ImageGenTesting/outputs/phase1_baselines/pixart_sigma/character_front.png",
        "pixart_isometric": "/workspace/ImageGenTesting/outputs/phase1_baselines/pixart_sigma/isometric_building.png",
        "sdxl_pixelart_sword": "/workspace/ImageGenTesting/outputs/phase2_loras/sdxl_pixel_art_xl/pixel_sword.png",
        "sdxl_pixelart_character": "/workspace/ImageGenTesting/outputs/phase2_loras/sdxl_pixel_art_xl/character_front.png",
    }

    results = {}
    for name, path in test_images.items():
        if not os.path.exists(path):
            print(f"  Skipping {name}: file not found")
            continue

        print(f"  Processing: {name}")
        start = time.time()
        img = Image.open(path)
        output = remove(img)
        elapsed = time.time() - start

        filepath = output_dir / f"{name}_nobg.png"
        output.save(filepath)

        results[name] = {
            "time_seconds": round(elapsed, 2),
            "file": str(filepath),
            "original": path,
            "has_alpha": output.mode == "RGBA",
        }
        print(f"    -> {filepath} ({elapsed:.1f}s, alpha={output.mode == 'RGBA'})")

    return results


# ============================================================
# TEST 2: Style Consistency via Seed Variation
# ============================================================
def test_seed_consistency():
    """Generate multiple characters with the same prompt but different seeds,
    then generate with same seed to show reproducibility."""
    from diffusers import StableDiffusionXLPipeline

    print("\n" + "=" * 60)
    print("TEST 2: Seed Consistency (SDXL + pixel-art-xl)")
    print("=" * 60)

    output_dir = OUTPUT_BASE / "seed_consistency"
    output_dir.mkdir(exist_ok=True)

    pipe = StableDiffusionXLPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        torch_dtype=torch.float16, variant="fp16", use_safetensors=True,
    )
    pipe = pipe.to("cuda")
    pipe.load_lora_weights("nerijs/pixel-art-xl")
    print(f"  Loaded. GPU: {get_gpu_mem():.0f}MB")

    base_prompt = "pixel art, pixel art character sprite, front-facing idle pose, fantasy warrior, game asset, white background"
    negative = "blurry, photorealistic, text, watermark"

    results = {}

    # Generate 5 variations with different seeds
    print("  Generating 5 character variations...")
    for seed in [42, 123, 456, 789, 1024]:
        start = time.time()
        image = pipe(
            prompt=base_prompt, negative_prompt=negative,
            num_inference_steps=30, guidance_scale=7.5,
            height=1024, width=1024,
            generator=torch.Generator("cuda").manual_seed(seed),
        ).images[0]
        elapsed = time.time() - start
        filepath = output_dir / f"warrior_seed{seed}.png"
        image.save(filepath)
        results[f"seed_{seed}"] = {"time": round(elapsed, 2), "file": str(filepath)}
        print(f"    -> seed={seed}: {elapsed:.1f}s")

    # Generate same character twice with same seed (reproducibility check)
    print("  Reproducibility check (same seed x2)...")
    for i in range(2):
        image = pipe(
            prompt=base_prompt, negative_prompt=negative,
            num_inference_steps=30, guidance_scale=7.5,
            height=1024, width=1024,
            generator=torch.Generator("cuda").manual_seed(42),
        ).images[0]
        filepath = output_dir / f"warrior_repro_{i}.png"
        image.save(filepath)
        results[f"repro_{i}"] = {"file": str(filepath)}

    del pipe
    clear_gpu()
    return results


# ============================================================
# TEST 3: Multi-pose generation (same character, different poses)
# ============================================================
def test_multipose():
    """Generate the same character in different poses/views to test style consistency."""
    from diffusers import StableDiffusionXLPipeline

    print("\n" + "=" * 60)
    print("TEST 3: Multi-Pose Generation (SDXL + pixel-art-xl)")
    print("=" * 60)

    output_dir = OUTPUT_BASE / "multi_pose"
    output_dir.mkdir(exist_ok=True)

    pipe = StableDiffusionXLPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        torch_dtype=torch.float16, variant="fp16", use_safetensors=True,
    )
    pipe = pipe.to("cuda")
    pipe.load_lora_weights("nerijs/pixel-art-xl")

    character_desc = "pixel art knight character with blue armor and red plume helmet"
    poses = {
        "front": f"pixel art, {character_desc}, front-facing, idle pose, game sprite, white background",
        "side": f"pixel art, {character_desc}, side view, walking pose, game sprite, white background",
        "back": f"pixel art, {character_desc}, rear view, standing, game sprite, white background",
        "attack": f"pixel art, {character_desc}, front-facing, sword attack pose, game sprite, white background",
        "hurt": f"pixel art, {character_desc}, front-facing, damaged hurt pose, game sprite, white background",
    }
    negative = "blurry, photorealistic, text, watermark, multiple characters"

    results = {}
    for pose_name, prompt in poses.items():
        print(f"  Generating: {pose_name}")
        start = time.time()
        image = pipe(
            prompt=prompt, negative_prompt=negative,
            num_inference_steps=30, guidance_scale=7.5,
            height=1024, width=1024,
            generator=torch.Generator("cuda").manual_seed(42),
        ).images[0]
        elapsed = time.time() - start
        filepath = output_dir / f"knight_{pose_name}.png"
        image.save(filepath)
        results[pose_name] = {"time": round(elapsed, 2), "file": str(filepath)}
        print(f"    -> {elapsed:.1f}s")

    del pipe
    clear_gpu()
    return results


# ============================================================
# TEST 4: FLUX multi-pose (same approach)
# ============================================================
def test_flux_multipose():
    """Generate same character in different poses with FLUX."""
    from diffusers import FluxPipeline, FluxTransformer2DModel, BitsAndBytesConfig

    print("\n" + "=" * 60)
    print("TEST 4: Multi-Pose Generation (FLUX.1-dev 4-bit)")
    print("=" * 60)

    output_dir = OUTPUT_BASE / "flux_multi_pose"
    output_dir.mkdir(exist_ok=True)

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

    character_desc = "pixel art knight character with blue armor and red plume helmet"
    poses = {
        "front": f"{character_desc}, front-facing, idle pose, game sprite, white background, single character",
        "side": f"{character_desc}, side view, walking pose, game sprite, white background, single character",
        "back": f"{character_desc}, rear view, standing, game sprite, white background, single character",
        "attack": f"{character_desc}, front-facing, sword attack pose, game sprite, white background, single character",
    }

    results = {}
    for pose_name, prompt in poses.items():
        print(f"  Generating: {pose_name}")
        start = time.time()
        image = pipe(
            prompt=prompt,
            num_inference_steps=20, guidance_scale=3.5,
            height=1024, width=1024,
            generator=torch.Generator("cuda").manual_seed(42),
        ).images[0]
        elapsed = time.time() - start
        filepath = output_dir / f"knight_{pose_name}.png"
        image.save(filepath)
        results[pose_name] = {"time": round(elapsed, 2), "file": str(filepath)}
        print(f"    -> {elapsed:.1f}s")

    del pipe, transformer
    clear_gpu()
    return results


# ============================================================
# TEST 5: Downscale test - do pixel art outputs look good at target res?
# ============================================================
def test_downscale():
    """Downscale generated pixel art to target game resolutions and evaluate."""
    from PIL import Image

    print("\n" + "=" * 60)
    print("TEST 5: Downscale Quality Test")
    print("=" * 60)

    output_dir = OUTPUT_BASE / "downscale"
    output_dir.mkdir(exist_ok=True)

    # Test downscaling our best pixel art outputs to game-appropriate sizes
    test_cases = [
        # (source, target_size, name)
        ("/workspace/ImageGenTesting/outputs/phase1_baselines/flux1_dev_4bit/pixel_sword.png", (32, 32), "flux_sword_32"),
        ("/workspace/ImageGenTesting/outputs/phase1_baselines/flux1_dev_4bit/pixel_sword.png", (64, 64), "flux_sword_64"),
        ("/workspace/ImageGenTesting/outputs/phase1_baselines/flux1_dev_4bit/character_front.png", (64, 64), "flux_char_64"),
        ("/workspace/ImageGenTesting/outputs/phase1_baselines/flux1_dev_4bit/character_front.png", (128, 128), "flux_char_128"),
        ("/workspace/ImageGenTesting/outputs/phase1_baselines/flux1_dev_4bit/enemy_creature.png", (48, 48), "flux_enemy_48"),
        ("/workspace/ImageGenTesting/outputs/phase2_loras/sdxl_pixel_art_xl/pixel_sword.png", (32, 32), "sdxl_sword_32"),
        ("/workspace/ImageGenTesting/outputs/phase2_loras/sdxl_pixel_art_xl/pixel_sword.png", (64, 64), "sdxl_sword_64"),
        ("/workspace/ImageGenTesting/outputs/phase2_loras/sdxl_pixel_art_xl/character_front.png", (64, 64), "sdxl_char_64"),
        ("/workspace/ImageGenTesting/outputs/phase2_loras/sdxl_pixel_art_xl/character_front.png", (128, 128), "sdxl_char_128"),
    ]

    results = {}
    for source_path, target_size, name in test_cases:
        if not os.path.exists(source_path):
            continue

        img = Image.open(source_path)

        # Nearest-neighbor downscale (preserves pixel art crispness)
        nn_path = output_dir / f"{name}_nearest.png"
        img.resize(target_size, Image.NEAREST).save(nn_path)

        # Lanczos downscale (smooth, for comparison)
        lanczos_path = output_dir / f"{name}_lanczos.png"
        img.resize(target_size, Image.LANCZOS).save(lanczos_path)

        # Also save a 4x upscale of the nearest-neighbor version for easier viewing
        nn_up = img.resize(target_size, Image.NEAREST).resize(
            (target_size[0] * 8, target_size[1] * 8), Image.NEAREST
        )
        nn_up_path = output_dir / f"{name}_nearest_8x.png"
        nn_up.save(nn_up_path)

        results[name] = {
            "nearest": str(nn_path),
            "lanczos": str(lanczos_path),
            "nearest_8x": str(nn_up_path),
            "target_size": target_size,
        }
        print(f"  {name}: {img.size} -> {target_size}")

    return results


def main():
    # Test 1: Background removal
    try:
        all_results["bg_removal"] = {"data": test_background_removal(), "status": "success"}
    except Exception as e:
        print(f"  BG removal FAILED: {e}")
        import traceback; traceback.print_exc()
        all_results["bg_removal"] = {"status": "error", "error": str(e)}

    # Test 2: Seed consistency
    try:
        all_results["seed_consistency"] = {"data": test_seed_consistency(), "status": "success"}
    except Exception as e:
        print(f"  Seed consistency FAILED: {e}")
        import traceback; traceback.print_exc()
        all_results["seed_consistency"] = {"status": "error", "error": str(e)}
    clear_gpu()

    # Test 3: Multi-pose SDXL
    try:
        all_results["sdxl_multipose"] = {"data": test_multipose(), "status": "success"}
    except Exception as e:
        print(f"  Multi-pose FAILED: {e}")
        import traceback; traceback.print_exc()
        all_results["sdxl_multipose"] = {"status": "error", "error": str(e)}
    clear_gpu()

    # Test 4: Multi-pose FLUX
    try:
        all_results["flux_multipose"] = {"data": test_flux_multipose(), "status": "success"}
    except Exception as e:
        print(f"  FLUX multi-pose FAILED: {e}")
        import traceback; traceback.print_exc()
        all_results["flux_multipose"] = {"status": "error", "error": str(e)}
    clear_gpu()

    # Test 5: Downscale quality
    try:
        all_results["downscale"] = {"data": test_downscale(), "status": "success"}
    except Exception as e:
        print(f"  Downscale FAILED: {e}")
        all_results["downscale"] = {"status": "error", "error": str(e)}

    # Save results
    with open(RESULTS_FILE, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n{'='*60}")
    print("PHASE 3 COMPLETE")
    print(f"{'='*60}")
    for test, data in all_results.items():
        print(f"  {test}: {data['status']}")


if __name__ == "__main__":
    main()
