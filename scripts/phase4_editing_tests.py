"""Phase 4: Reference-based image editing tests with Neko Cafe characters.

Tests 4 models on expression changes, pose variations, and CG scene generation
using Clover and Sable reference images.
"""

import os
import sys
import time
import json
import gc
import torch
from pathlib import Path
from PIL import Image

OUTPUT_BASE = Path("/workspace/ImageGenTesting/outputs/phase4_editing")
RESULTS_FILE = Path("/workspace/ImageGenTesting/results/phase4_results.json")
OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

# Reference images
CLOVER_REF = "/workspace/NekoCafe/Art/References/Clover.png"
SABLE_REF = "/workspace/NekoCafe/Art/References/Sable.png"

# Crop the front-facing view from the turnaround sheets
def crop_front_view(img_path, save_path=None):
    """Crop the leftmost (front-facing) character from a 3-view turnaround sheet."""
    img = Image.open(img_path)
    w, h = img.size
    # Front view is roughly the left third
    front = img.crop((0, 0, w // 3, h))
    if save_path:
        front.save(save_path)
    return front


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
# EDITING TEST DEFINITIONS
# ============================================================

# Expression edits (face-only changes)
EXPRESSION_EDITS = {
    "happy": "Make the character smile warmly with a happy expression",
    "sad": "Make the character look sad with downcast eyes and a slight frown",
    "angry": "Make the character look angry with furrowed brows and a scowl",
    "surprised": "Make the character look surprised with wide eyes and open mouth",
    "embarrassed": "Make the character look embarrassed with blushing cheeks and averted eyes",
    "determined": "Make the character look determined with a confident, focused expression",
}

# Larger changes (outfit, pose, setting)
SCENE_EDITS = {
    "winter_outfit": "Change the character's outfit to a cozy winter coat with a scarf, keep everything else the same",
    "formal_outfit": "Change the character's outfit to an elegant formal dress, keep the same face and hairstyle",
    "cafe_scene": "Place the character in a cozy cafe setting, standing behind a counter with coffee cups, warm lighting",
    "outdoor_scene": "Place the character in a sunny garden with flowers and trees, daytime outdoor setting",
    "night_scene": "Place the character under a starry night sky with moonlight, atmospheric lighting",
}

# CG event scene prompts (using character description)
CG_SINGLE = {
    "serving_coffee": "An anime girl with orange wavy hair, calico cat ears, and a brown apron over a cream blouse, cheerfully serving a cup of coffee with a warm smile, cozy cafe interior, warm lighting, visual novel CG, detailed anime illustration",
    "reading_book": "An anime girl with orange wavy hair, calico cat ears, and a brown apron, sitting in a window seat reading a book, soft afternoon light streaming in, peaceful expression, visual novel CG, detailed anime illustration",
    "looking_at_stars": "An anime girl with orange wavy hair, calico cat ears, wearing casual clothes, looking up at a starry night sky from a rooftop, her calico tail visible, wonder in her eyes, visual novel CG, detailed anime illustration",
}

CG_MULTI = {
    "working_together": "Two anime catgirls working in a cafe: one with orange wavy hair, calico ears, brown apron (Clover) and one with short black hair, black cat ears, dark gray outfit (Sable). They are preparing drinks together behind a counter, friendly atmosphere, warm lighting, visual novel CG, detailed anime illustration",
    "conversation": "Two anime catgirls sitting at a table facing each other: one with orange wavy hair and calico cat ears (Clover) and one with short black hair and black cat ears (Sable). They are having a friendly conversation over tea, cozy cafe setting, visual novel CG, detailed anime illustration",
}


all_results = {}


# ============================================================
# MODEL 1: FLUX.1 Kontext
# ============================================================
def test_flux_kontext():
    """Test FLUX.1 Kontext for reference-based editing."""
    from diffusers import FluxKontextPipeline
    from diffusers import BitsAndBytesConfig

    model_id = "black-forest-labs/FLUX.1-Kontext-dev"
    model_name = "flux_kontext"
    print(f"\n{'='*60}")
    print(f"MODEL: FLUX.1 Kontext ({model_id})")
    print(f"{'='*60}")

    output_dir = OUTPUT_BASE / model_name
    output_dir.mkdir(exist_ok=True)

    # Try loading with quantization to fit in VRAM
    print("Loading with 4-bit quantization...")
    try:
        from diffusers import FluxTransformer2DModel
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
        pipe = FluxKontextPipeline.from_pretrained(
            model_id,
            transformer=transformer,
            torch_dtype=torch.bfloat16,
        )
        pipe.enable_model_cpu_offload()
    except Exception as e:
        print(f"  Quantized load failed: {e}")
        print("  Trying standard load with CPU offload...")
        pipe = FluxKontextPipeline.from_pretrained(
            model_id,
            torch_dtype=torch.bfloat16,
        )
        pipe.enable_model_cpu_offload()

    print(f"  Loaded. GPU: {get_gpu_mem():.0f}MB")

    # Prepare reference images
    clover_front = crop_front_view(CLOVER_REF, output_dir / "clover_front_crop.png")
    clover_full = Image.open(CLOVER_REF)
    sable_front = crop_front_view(SABLE_REF, output_dir / "sable_front_crop.png")

    results = {}

    # --- Expression edits ---
    print("\n  --- Expression Edits (Clover front crop) ---")
    for name, instruction in EXPRESSION_EDITS.items():
        print(f"  Generating: expression_{name}")
        start = time.time()
        try:
            image = pipe(
                image=clover_front,
                prompt=instruction,
                guidance_scale=2.5,
                num_inference_steps=24,
                height=clover_front.height,
                width=clover_front.width,
                generator=torch.Generator("cuda").manual_seed(42),
            ).images[0]
            elapsed = time.time() - start
            fp = output_dir / f"expr_{name}.png"
            image.save(fp)
            results[f"expr_{name}"] = {"time": round(elapsed, 2), "file": str(fp), "status": "success"}
            print(f"    -> {elapsed:.1f}s")
        except Exception as e:
            results[f"expr_{name}"] = {"status": "error", "error": str(e)}
            print(f"    -> ERROR: {e}")

    # --- Scene/outfit edits ---
    print("\n  --- Scene/Outfit Edits (Clover front crop) ---")
    for name, instruction in SCENE_EDITS.items():
        print(f"  Generating: scene_{name}")
        start = time.time()
        try:
            image = pipe(
                image=clover_front,
                prompt=instruction,
                guidance_scale=2.5,
                num_inference_steps=24,
                height=1024,
                width=1024,
                generator=torch.Generator("cuda").manual_seed(42),
            ).images[0]
            elapsed = time.time() - start
            fp = output_dir / f"scene_{name}.png"
            image.save(fp)
            results[f"scene_{name}"] = {"time": round(elapsed, 2), "file": str(fp), "status": "success"}
            print(f"    -> {elapsed:.1f}s")
        except Exception as e:
            results[f"scene_{name}"] = {"status": "error", "error": str(e)}
            print(f"    -> ERROR: {e}")

    # --- CG single character (using full turnaround as reference) ---
    print("\n  --- CG Single Character Scenes ---")
    for name, prompt in CG_SINGLE.items():
        print(f"  Generating: cg_{name}")
        start = time.time()
        try:
            image = pipe(
                image=clover_full,
                prompt=prompt,
                guidance_scale=2.5,
                num_inference_steps=28,
                height=1024,
                width=1024,
                generator=torch.Generator("cuda").manual_seed(42),
            ).images[0]
            elapsed = time.time() - start
            fp = output_dir / f"cg_{name}.png"
            image.save(fp)
            results[f"cg_{name}"] = {"time": round(elapsed, 2), "file": str(fp), "status": "success"}
            print(f"    -> {elapsed:.1f}s")
        except Exception as e:
            results[f"cg_{name}"] = {"status": "error", "error": str(e)}
            print(f"    -> ERROR: {e}")

    del pipe
    if 'transformer' in dir():
        del transformer
    clear_gpu()
    return model_name, results


# ============================================================
# MODEL 2: Qwen-Image-Edit-2511
# ============================================================
def test_qwen_edit():
    """Test Qwen-Image-Edit-2511 for reference-based editing."""
    model_name = "qwen_edit"
    print(f"\n{'='*60}")
    print(f"MODEL: Qwen-Image-Edit-2511")
    print(f"{'='*60}")

    output_dir = OUTPUT_BASE / model_name
    output_dir.mkdir(exist_ok=True)

    # Try loading the model
    print("Loading Qwen-Image-Edit-2511...")
    try:
        from diffusers import QwenImageEditPlusPipeline
        pipe = QwenImageEditPlusPipeline.from_pretrained(
            "Qwen/Qwen-Image-Edit-2511",
            torch_dtype=torch.bfloat16,
        )
        pipe.enable_model_cpu_offload()
    except ImportError:
        print("  QwenImageEditPlusPipeline not available, trying QwenImageEditPipeline...")
        try:
            from diffusers import QwenImageEditPipeline
            pipe = QwenImageEditPipeline.from_pretrained(
                "Qwen/Qwen-Image-Edit-2511",
                torch_dtype=torch.bfloat16,
            )
            pipe.enable_model_cpu_offload()
        except Exception as e:
            print(f"  Failed to load Qwen edit model: {e}")
            return model_name, {"status": "error", "error": str(e)}

    print(f"  Loaded. GPU: {get_gpu_mem():.0f}MB")

    clover_front = crop_front_view(CLOVER_REF, output_dir / "clover_front_crop.png")
    clover_full = Image.open(CLOVER_REF)

    results = {}

    # --- Expression edits ---
    print("\n  --- Expression Edits ---")
    for name, instruction in EXPRESSION_EDITS.items():
        print(f"  Generating: expression_{name}")
        start = time.time()
        try:
            image = pipe(
                image=clover_front,
                prompt=instruction,
                num_inference_steps=28,
                generator=torch.Generator("cuda").manual_seed(42),
            ).images[0]
            elapsed = time.time() - start
            fp = output_dir / f"expr_{name}.png"
            image.save(fp)
            results[f"expr_{name}"] = {"time": round(elapsed, 2), "file": str(fp), "status": "success"}
            print(f"    -> {elapsed:.1f}s")
        except Exception as e:
            results[f"expr_{name}"] = {"status": "error", "error": str(e)}
            print(f"    -> ERROR: {e}")

    # --- Scene/outfit edits ---
    print("\n  --- Scene/Outfit Edits ---")
    for name, instruction in SCENE_EDITS.items():
        print(f"  Generating: scene_{name}")
        start = time.time()
        try:
            image = pipe(
                image=clover_front,
                prompt=instruction,
                num_inference_steps=28,
                generator=torch.Generator("cuda").manual_seed(42),
            ).images[0]
            elapsed = time.time() - start
            fp = output_dir / f"scene_{name}.png"
            image.save(fp)
            results[f"scene_{name}"] = {"time": round(elapsed, 2), "file": str(fp), "status": "success"}
            print(f"    -> {elapsed:.1f}s")
        except Exception as e:
            results[f"scene_{name}"] = {"status": "error", "error": str(e)}
            print(f"    -> ERROR: {e}")

    # --- CG scenes ---
    print("\n  --- CG Single Character Scenes ---")
    for name, prompt in CG_SINGLE.items():
        print(f"  Generating: cg_{name}")
        start = time.time()
        try:
            image = pipe(
                image=clover_full,
                prompt=prompt,
                num_inference_steps=28,
                generator=torch.Generator("cuda").manual_seed(42),
            ).images[0]
            elapsed = time.time() - start
            fp = output_dir / f"cg_{name}.png"
            image.save(fp)
            results[f"cg_{name}"] = {"time": round(elapsed, 2), "file": str(fp), "status": "success"}
            print(f"    -> {elapsed:.1f}s")
        except Exception as e:
            results[f"cg_{name}"] = {"status": "error", "error": str(e)}
            print(f"    -> ERROR: {e}")

    del pipe
    clear_gpu()
    return model_name, results


# ============================================================
# MODEL 3: LongCat-Image-Edit-Turbo
# ============================================================
def test_longcat_edit():
    """Test LongCat-Image-Edit-Turbo for reference-based editing."""
    model_name = "longcat_edit"
    print(f"\n{'='*60}")
    print(f"MODEL: LongCat-Image-Edit-Turbo")
    print(f"{'='*60}")

    output_dir = OUTPUT_BASE / model_name
    output_dir.mkdir(exist_ok=True)

    print("Loading LongCat-Image-Edit-Turbo...")
    try:
        # LongCat uses a custom pipeline - try diffusers first
        from diffusers import AutoPipelineForImage2Image
        pipe = AutoPipelineForImage2Image.from_pretrained(
            "meituan-longcat/LongCat-Image-Edit-Turbo",
            torch_dtype=torch.bfloat16,
        )
        pipe.enable_model_cpu_offload()
    except Exception as e1:
        print(f"  AutoPipeline failed: {e1}")
        try:
            from diffusers import FluxImg2ImgPipeline
            pipe = FluxImg2ImgPipeline.from_pretrained(
                "meituan-longcat/LongCat-Image-Edit-Turbo",
                torch_dtype=torch.bfloat16,
            )
            pipe.enable_model_cpu_offload()
        except Exception as e2:
            print(f"  FluxImg2Img also failed: {e2}")
            return model_name, {"status": "error", "error": f"Load failed: {e1} / {e2}"}

    print(f"  Loaded. GPU: {get_gpu_mem():.0f}MB")

    clover_front = crop_front_view(CLOVER_REF, output_dir / "clover_front_crop.png")

    results = {}

    # --- Expression edits ---
    print("\n  --- Expression Edits ---")
    for name, instruction in EXPRESSION_EDITS.items():
        print(f"  Generating: expression_{name}")
        start = time.time()
        try:
            image = pipe(
                image=clover_front,
                prompt=instruction,
                num_inference_steps=8,
                strength=0.5,
                generator=torch.Generator("cuda").manual_seed(42),
            ).images[0]
            elapsed = time.time() - start
            fp = output_dir / f"expr_{name}.png"
            image.save(fp)
            results[f"expr_{name}"] = {"time": round(elapsed, 2), "file": str(fp), "status": "success"}
            print(f"    -> {elapsed:.1f}s")
        except Exception as e:
            results[f"expr_{name}"] = {"status": "error", "error": str(e)}
            print(f"    -> ERROR: {e}")

    # --- Scene edits ---
    print("\n  --- Scene/Outfit Edits ---")
    for name, instruction in SCENE_EDITS.items():
        print(f"  Generating: scene_{name}")
        start = time.time()
        try:
            image = pipe(
                image=clover_front,
                prompt=instruction,
                num_inference_steps=8,
                strength=0.7,
                generator=torch.Generator("cuda").manual_seed(42),
            ).images[0]
            elapsed = time.time() - start
            fp = output_dir / f"scene_{name}.png"
            image.save(fp)
            results[f"scene_{name}"] = {"time": round(elapsed, 2), "file": str(fp), "status": "success"}
            print(f"    -> {elapsed:.1f}s")
        except Exception as e:
            results[f"scene_{name}"] = {"status": "error", "error": str(e)}
            print(f"    -> ERROR: {e}")

    del pipe
    clear_gpu()
    return model_name, results


# ============================================================
# MODEL 4: OmniGen2
# ============================================================
def test_omnigen2():
    """Test OmniGen2 for reference-based editing."""
    model_name = "omnigen2"
    print(f"\n{'='*60}")
    print(f"MODEL: OmniGen2")
    print(f"{'='*60}")

    output_dir = OUTPUT_BASE / model_name
    output_dir.mkdir(exist_ok=True)

    print("Loading OmniGen2...")
    try:
        # OmniGen2 has its own pipeline
        sys.path.insert(0, "/workspace/ImageGenTesting")
        from OmniGen2 import OmniGen2Pipeline
        pipe = OmniGen2Pipeline("OmniGen2/OmniGen2")
        pipe.enable_model_cpu_offload()
    except ImportError:
        # Try pip install
        print("  OmniGen2 not installed, trying pip...")
        os.system("pip install omnigen2 2>/dev/null")
        try:
            from OmniGen2 import OmniGen2Pipeline
            pipe = OmniGen2Pipeline("OmniGen2/OmniGen2")
            pipe.enable_model_cpu_offload()
        except Exception as e:
            print(f"  Failed to load OmniGen2: {e}")
            # Try diffusers auto pipeline as fallback
            try:
                from diffusers import AutoPipelineForImage2Image
                pipe = AutoPipelineForImage2Image.from_pretrained(
                    "OmniGen2/OmniGen2",
                    torch_dtype=torch.bfloat16,
                    trust_remote_code=True,
                )
                pipe.enable_model_cpu_offload()
            except Exception as e2:
                print(f"  All load attempts failed: {e2}")
                return model_name, {"status": "error", "error": str(e2)}

    print(f"  Loaded. GPU: {get_gpu_mem():.0f}MB")

    clover_front = crop_front_view(CLOVER_REF, output_dir / "clover_front_crop.png")

    results = {}

    # --- Expression edits ---
    print("\n  --- Expression Edits ---")
    for name, instruction in EXPRESSION_EDITS.items():
        print(f"  Generating: expression_{name}")
        start = time.time()
        try:
            # OmniGen2 uses input_images parameter
            image = pipe(
                prompt=f"<img><|image_1|></img> {instruction}",
                input_images=[clover_front],
                num_inference_steps=20,
                guidance_scale=2.5,
                img_guidance_scale=1.5,
                seed=42,
            )[0]
            elapsed = time.time() - start
            fp = output_dir / f"expr_{name}.png"
            image.save(fp)
            results[f"expr_{name}"] = {"time": round(elapsed, 2), "file": str(fp), "status": "success"}
            print(f"    -> {elapsed:.1f}s")
        except Exception as e:
            results[f"expr_{name}"] = {"status": "error", "error": str(e)}
            print(f"    -> ERROR: {e}")

    # --- Scene edits ---
    print("\n  --- Scene/Outfit Edits ---")
    for name, instruction in SCENE_EDITS.items():
        print(f"  Generating: scene_{name}")
        start = time.time()
        try:
            image = pipe(
                prompt=f"<img><|image_1|></img> {instruction}",
                input_images=[clover_front],
                num_inference_steps=20,
                guidance_scale=2.5,
                img_guidance_scale=1.5,
                seed=42,
            )[0]
            elapsed = time.time() - start
            fp = output_dir / f"scene_{name}.png"
            image.save(fp)
            results[f"scene_{name}"] = {"time": round(elapsed, 2), "file": str(fp), "status": "success"}
            print(f"    -> {elapsed:.1f}s")
        except Exception as e:
            results[f"scene_{name}"] = {"status": "error", "error": str(e)}
            print(f"    -> ERROR: {e}")

    del pipe
    clear_gpu()
    return model_name, results


# ============================================================
# WORKFLOW 5: IP-Adapter + AnimagineXL (adapter-based approach)
# ============================================================
def test_ipadapter_animagine():
    """Test IP-Adapter with an anime model for reference-based generation."""
    from diffusers import StableDiffusionXLPipeline

    model_name = "ipadapter_animagine"
    print(f"\n{'='*60}")
    print(f"WORKFLOW: IP-Adapter + AnimagineXL 4.0")
    print(f"{'='*60}")

    output_dir = OUTPUT_BASE / model_name
    output_dir.mkdir(exist_ok=True)

    print("Loading AnimagineXL 4.0...")
    try:
        pipe = StableDiffusionXLPipeline.from_pretrained(
            "cagliostrolab/animagine-xl-4.0",
            torch_dtype=torch.float16,
            variant="fp16",
        )
        pipe = pipe.to("cuda")
    except Exception:
        print("  AnimagineXL 4.0 not available, falling back to SDXL...")
        pipe = StableDiffusionXLPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            torch_dtype=torch.float16,
            variant="fp16",
        )
        pipe = pipe.to("cuda")

    print("  Loading IP-Adapter...")
    try:
        pipe.load_ip_adapter(
            "h94/IP-Adapter",
            subfolder="sdxl_models",
            weight_name="ip-adapter-plus_sdxl_vit-h.safetensors",
        )
        pipe.set_ip_adapter_scale(0.7)
    except Exception as e:
        print(f"  IP-Adapter load failed: {e}")
        del pipe
        clear_gpu()
        return model_name, {"status": "error", "error": str(e)}

    print(f"  Loaded. GPU: {get_gpu_mem():.0f}MB")

    clover_front = crop_front_view(CLOVER_REF)
    # Resize for IP-Adapter
    clover_front = clover_front.resize((1024, 1024), Image.LANCZOS)

    results = {}
    base_desc = "1girl, orange wavy hair, calico cat ears, cat tail, brown apron, cream blouse, anime style, masterpiece, best quality"

    # --- Expression variants via prompt ---
    print("\n  --- Expression Variants (IP-Adapter reference + prompt) ---")
    expressions = {
        "happy": f"{base_desc}, happy smile, warm expression, looking at viewer",
        "sad": f"{base_desc}, sad expression, downcast eyes, slight frown, looking down",
        "angry": f"{base_desc}, angry expression, furrowed brows, scowl",
        "surprised": f"{base_desc}, surprised expression, wide eyes, open mouth",
        "embarrassed": f"{base_desc}, embarrassed expression, blushing, averted eyes",
        "determined": f"{base_desc}, determined expression, confident look, focused eyes",
    }
    negative = "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark"

    for name, prompt in expressions.items():
        print(f"  Generating: expression_{name}")
        start = time.time()
        try:
            image = pipe(
                prompt=prompt,
                negative_prompt=negative,
                ip_adapter_image=clover_front,
                num_inference_steps=28,
                guidance_scale=7.0,
                height=1024,
                width=768,
                generator=torch.Generator("cuda").manual_seed(42),
            ).images[0]
            elapsed = time.time() - start
            fp = output_dir / f"expr_{name}.png"
            image.save(fp)
            results[f"expr_{name}"] = {"time": round(elapsed, 2), "file": str(fp), "status": "success"}
            print(f"    -> {elapsed:.1f}s")
        except Exception as e:
            results[f"expr_{name}"] = {"status": "error", "error": str(e)}
            print(f"    -> ERROR: {e}")

    # --- CG scenes with IP-Adapter reference ---
    print("\n  --- CG Single Character Scenes ---")
    for name, prompt in CG_SINGLE.items():
        print(f"  Generating: cg_{name}")
        start = time.time()
        try:
            image = pipe(
                prompt=f"{prompt}, masterpiece, best quality, absurdres",
                negative_prompt=negative,
                ip_adapter_image=clover_front,
                num_inference_steps=28,
                guidance_scale=7.0,
                height=1024,
                width=1024,
                generator=torch.Generator("cuda").manual_seed(42),
            ).images[0]
            elapsed = time.time() - start
            fp = output_dir / f"cg_{name}.png"
            image.save(fp)
            results[f"cg_{name}"] = {"time": round(elapsed, 2), "file": str(fp), "status": "success"}
            print(f"    -> {elapsed:.1f}s")
        except Exception as e:
            results[f"cg_{name}"] = {"status": "error", "error": str(e)}
            print(f"    -> ERROR: {e}")

    del pipe
    clear_gpu()
    return model_name, results


# ============================================================
# WORKFLOW 6: SDXL img2img inpainting (expression swap via mask)
# ============================================================
def test_sdxl_inpainting():
    """Test SDXL inpainting for face-only expression changes."""
    from diffusers import StableDiffusionXLInpaintPipeline

    model_name = "sdxl_inpaint"
    print(f"\n{'='*60}")
    print(f"WORKFLOW: SDXL Inpainting (face region)")
    print(f"{'='*60}")

    output_dir = OUTPUT_BASE / model_name
    output_dir.mkdir(exist_ok=True)

    print("Loading SDXL Inpaint...")
    pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        torch_dtype=torch.float16,
        variant="fp16",
    )
    pipe = pipe.to("cuda")
    print(f"  Loaded. GPU: {get_gpu_mem():.0f}MB")

    # Prepare: crop front view and create a face mask
    clover_front = crop_front_view(CLOVER_REF)
    w, h = clover_front.size

    # Resize to 1024x1024 for the model
    clover_resized = clover_front.resize((1024, 1024), Image.LANCZOS)
    clover_resized.save(output_dir / "clover_front_resized.png")

    # Create a face mask (upper portion of the image where the face is)
    # For Clover's front view, the face is roughly in the upper-center
    face_mask = Image.new("RGB", (1024, 1024), (0, 0, 0))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(face_mask)
    # Face region - approximate oval covering the head area
    draw.ellipse([350, 30, 650, 380], fill=(255, 255, 255))
    face_mask.save(output_dir / "face_mask.png")

    results = {}
    base_prompt = "1girl, anime style, orange wavy hair, calico cat ears"

    print("\n  --- Face Inpainting Expression Changes ---")
    expressions = {
        "happy": f"{base_prompt}, happy smile, warm eyes, cheerful expression, masterpiece, best quality",
        "sad": f"{base_prompt}, sad expression, teary eyes, slight frown, masterpiece, best quality",
        "angry": f"{base_prompt}, angry expression, furrowed brows, fierce eyes, masterpiece, best quality",
        "surprised": f"{base_prompt}, surprised expression, wide eyes, open mouth, masterpiece, best quality",
    }
    negative = "lowres, bad anatomy, bad hands, text, error, worst quality, low quality"

    for name, prompt in expressions.items():
        print(f"  Generating: inpaint_{name}")
        start = time.time()
        try:
            image = pipe(
                prompt=prompt,
                negative_prompt=negative,
                image=clover_resized,
                mask_image=face_mask,
                num_inference_steps=30,
                guidance_scale=7.5,
                strength=0.6,
                height=1024,
                width=1024,
                generator=torch.Generator("cuda").manual_seed(42),
            ).images[0]
            elapsed = time.time() - start
            fp = output_dir / f"inpaint_{name}.png"
            image.save(fp)
            results[f"inpaint_{name}"] = {"time": round(elapsed, 2), "file": str(fp), "status": "success"}
            print(f"    -> {elapsed:.1f}s")
        except Exception as e:
            results[f"inpaint_{name}"] = {"status": "error", "error": str(e)}
            print(f"    -> ERROR: {e}")

    del pipe
    clear_gpu()
    return model_name, results


# ============================================================
# MAIN
# ============================================================
def main():
    models_to_test = [
        ("flux_kontext", test_flux_kontext),
        ("qwen_edit", test_qwen_edit),
        ("longcat_edit", test_longcat_edit),
        ("omnigen2", test_omnigen2),
        ("ipadapter_animagine", test_ipadapter_animagine),
        ("sdxl_inpaint", test_sdxl_inpainting),
    ]

    for name, test_fn in models_to_test:
        try:
            model_name, results = test_fn()
            all_results[model_name] = {"results": results, "status": "success"}
        except Exception as e:
            print(f"\n  FATAL ERROR in {name}: {e}")
            import traceback; traceback.print_exc()
            all_results[name] = {"status": "error", "error": str(e)}
        clear_gpu()

        # Save intermediate results
        with open(RESULTS_FILE, "w") as f:
            json.dump(all_results, f, indent=2)

    # Final summary
    print(f"\n{'='*60}")
    print("PHASE 4 SUMMARY")
    print(f"{'='*60}")
    for model, data in all_results.items():
        status = data.get("status", "unknown")
        if status == "success" and "results" in data:
            successes = sum(1 for v in data["results"].values() if isinstance(v, dict) and v.get("status") == "success")
            total = len(data["results"])
            times = [v["time"] for v in data["results"].values() if isinstance(v, dict) and v.get("time")]
            avg_time = sum(times) / len(times) if times else 0
            print(f"  {model}: {successes}/{total} succeeded, avg {avg_time:.1f}s/image")
        else:
            print(f"  {model}: {status} - {data.get('error', '')[:80]}")


if __name__ == "__main__":
    main()
