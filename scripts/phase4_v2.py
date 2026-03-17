"""Phase 4 v2: Image editing tests with Neko Cafe characters.

Tests: FLUX Kontext, Qwen-Image-Edit-2511, LongCat-Image-Edit-Turbo,
       OmniGen2, IP-Adapter+SDXL, SDXL Inpainting
All models: Clover (single), Clover+Sable (multi)
"""

import os
import sys
import time
import json
import gc
import torch
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0, "/workspace/OmniGen2")

OUTPUT_BASE = Path("/workspace/ImageGenTesting/outputs/phase4_editing")
RESULTS_FILE = Path("/workspace/ImageGenTesting/results/phase4_results.json")
OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

CLOVER_REF = "/workspace/NekoCafe/Art/References/Clover.png"
SABLE_REF = "/workspace/NekoCafe/Art/References/Sable.png"


def crop_front_view(img_path):
    """Crop front-facing view from turnaround sheet, ensure RGB."""
    img = Image.open(img_path).convert("RGB")
    w, h = img.size
    return img.crop((0, 0, w // 3, h))


def load_full_ref(img_path):
    return Image.open(img_path).convert("RGB")


def clear_gpu():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()


def gpu_mb():
    return torch.cuda.memory_allocated() / 1024**2 if torch.cuda.is_available() else 0


# ---- Test definitions ----

EXPR_EDITS = {
    "happy": "Make the character smile warmly with a happy expression",
    "sad": "Make the character look sad with downcast eyes and a slight frown",
    "angry": "Make the character look angry with furrowed brows and a scowl",
    "surprised": "Make the character look surprised with wide eyes and open mouth",
    "embarrassed": "Make the character look embarrassed with blushing cheeks and averted eyes",
    "determined": "Make the character look determined with a confident, focused expression",
}

SCENE_EDITS = {
    "winter_outfit": "Change the character's outfit to a cozy winter coat with a scarf",
    "cafe_scene": "Place the character in a cozy cafe setting behind a counter with coffee cups, warm lighting",
    "outdoor_scene": "Place the character in a sunny garden with flowers and trees",
}

CG_SINGLE = {
    "serving_coffee": "An anime catgirl with orange wavy hair, calico cat ears, and a brown apron, cheerfully serving coffee in a cozy cafe, warm lighting, visual novel illustration",
    "reading_book": "An anime catgirl with orange wavy hair, calico cat ears, sitting by a window reading a book, soft afternoon light, peaceful, visual novel illustration",
}

CG_MULTI = {
    "working_together": "Two anime catgirls in a cafe: one with orange wavy hair and calico ears in a brown apron, one with short black hair and black ears in a dark outfit. They prepare drinks together, friendly, warm lighting, visual novel illustration",
}

all_results = {}


def run_edit_suite(model_name, gen_fn, clover_front, clover_full=None,
                   sable_front=None, skip_scene=False, skip_cg=False):
    """Run the standard edit test suite."""
    out = OUTPUT_BASE / model_name
    out.mkdir(exist_ok=True)
    clover_front.save(out / "clover_front_crop.png")
    results = {}

    print("\n  --- Expression Edits ---")
    for name, instr in EXPR_EDITS.items():
        tag = f"expr_{name}"
        print(f"  {tag}...", end=" ", flush=True)
        t0 = time.time()
        try:
            img = gen_fn(clover_front, instr)
            dt = round(time.time() - t0, 2)
            fp = out / f"{tag}.png"
            img.save(fp)
            results[tag] = {"time": dt, "file": str(fp), "status": "success"}
            print(f"{dt:.1f}s")
        except Exception as e:
            results[tag] = {"status": "error", "error": str(e)[:300]}
            print(f"ERROR: {str(e)[:120]}")

    if not skip_scene:
        print("\n  --- Scene/Outfit Edits ---")
        for name, instr in SCENE_EDITS.items():
            tag = f"scene_{name}"
            print(f"  {tag}...", end=" ", flush=True)
            t0 = time.time()
            try:
                img = gen_fn(clover_front, instr)
                dt = round(time.time() - t0, 2)
                fp = out / f"{tag}.png"
                img.save(fp)
                results[tag] = {"time": dt, "file": str(fp), "status": "success"}
                print(f"{dt:.1f}s")
            except Exception as e:
                results[tag] = {"status": "error", "error": str(e)[:300]}
                print(f"ERROR: {str(e)[:120]}")

    if not skip_cg:
        ref_cg = clover_full if clover_full else clover_front
        print("\n  --- CG Single ---")
        for name, prompt in CG_SINGLE.items():
            tag = f"cg_{name}"
            print(f"  {tag}...", end=" ", flush=True)
            t0 = time.time()
            try:
                img = gen_fn(ref_cg, prompt)
                dt = round(time.time() - t0, 2)
                fp = out / f"{tag}.png"
                img.save(fp)
                results[tag] = {"time": dt, "file": str(fp), "status": "success"}
                print(f"{dt:.1f}s")
            except Exception as e:
                results[tag] = {"status": "error", "error": str(e)[:300]}
                print(f"ERROR: {str(e)[:120]}")

    return results


def save_progress():
    with open(RESULTS_FILE, "w") as f:
        json.dump(all_results, f, indent=2)


# ============================================================
# 1. FLUX.1 Kontext
# ============================================================
def test_flux_kontext():
    name = "flux_kontext"
    print(f"\n{'='*60}\n  FLUX.1 Kontext\n{'='*60}")

    from diffusers import FluxKontextPipeline, FluxTransformer2DModel, BitsAndBytesConfig

    model_id = "black-forest-labs/FLUX.1-Kontext-dev"

    print("  Loading with NF4 quantization...")
    qconfig = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    transformer = FluxTransformer2DModel.from_pretrained(
        model_id, subfolder="transformer",
        quantization_config=qconfig, torch_dtype=torch.bfloat16,
    )
    pipe = FluxKontextPipeline.from_pretrained(
        model_id, transformer=transformer, torch_dtype=torch.bfloat16,
    )
    pipe.enable_model_cpu_offload()
    print(f"  Loaded. GPU: {gpu_mb():.0f}MB")

    def gen_fn(image, prompt):
        img = image.copy()
        return pipe(
            image=img, prompt=prompt,
            guidance_scale=2.5, num_inference_steps=24,
            height=1024, width=1024,
            generator=torch.Generator("cpu").manual_seed(42),
        ).images[0]

    clover_front = crop_front_view(CLOVER_REF)
    clover_full = load_full_ref(CLOVER_REF)
    results = run_edit_suite(name, gen_fn, clover_front, clover_full)

    del pipe, transformer
    clear_gpu()
    return name, results


# ============================================================
# 2. Qwen-Image-Edit-2511
# ============================================================
def test_qwen_edit():
    name = "qwen_edit"
    print(f"\n{'='*60}\n  Qwen-Image-Edit-2511\n{'='*60}")

    from diffusers import QwenImageEditPlusPipeline

    pipe = QwenImageEditPlusPipeline.from_pretrained(
        "Qwen/Qwen-Image-Edit-2511", torch_dtype=torch.bfloat16,
    )
    pipe.enable_model_cpu_offload()
    print(f"  Loaded. GPU: {gpu_mb():.0f}MB")

    def gen_fn(image, prompt):
        img = image.copy()
        # Resize to keep generation manageable
        max_dim = 1024
        if max(img.size) > max_dim:
            ratio = max_dim / max(img.size)
            img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
        return pipe(
            image=img, prompt=prompt,
            num_inference_steps=28,
            generator=torch.Generator("cpu").manual_seed(42),
        ).images[0]

    clover_front = crop_front_view(CLOVER_REF)
    clover_full = load_full_ref(CLOVER_REF)
    results = run_edit_suite(name, gen_fn, clover_front, clover_full)

    del pipe
    clear_gpu()
    return name, results


# ============================================================
# 3. LongCat-Image-Edit-Turbo
# ============================================================
def test_longcat():
    name = "longcat_edit"
    print(f"\n{'='*60}\n  LongCat-Image-Edit-Turbo\n{'='*60}")

    from diffusers import LongCatImageEditPipeline

    pipe = LongCatImageEditPipeline.from_pretrained(
        "meituan-longcat/LongCat-Image-Edit-Turbo",
        torch_dtype=torch.bfloat16,
    )
    pipe.enable_model_cpu_offload()
    print(f"  Loaded. GPU: {gpu_mb():.0f}MB")

    def gen_fn(image, prompt):
        img = image.copy()
        max_dim = 1024
        if max(img.size) > max_dim:
            ratio = max_dim / max(img.size)
            img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
        return pipe(
            image=img, prompt=prompt,
            guidance_scale=1.0,  # Turbo: guidance_scale=1
            num_inference_steps=8,  # Turbo: only 8 steps
            generator=torch.Generator("cpu").manual_seed(42),
        ).images[0]

    clover_front = crop_front_view(CLOVER_REF)
    clover_full = load_full_ref(CLOVER_REF)
    results = run_edit_suite(name, gen_fn, clover_front, clover_full)

    del pipe
    clear_gpu()
    return name, results


# ============================================================
# 4. OmniGen2
# ============================================================
def test_omnigen2():
    name = "omnigen2"
    print(f"\n{'='*60}\n  OmniGen2\n{'='*60}")

    from omnigen2.pipelines.omnigen2.pipeline_omnigen2 import OmniGen2Pipeline
    from omnigen2.models.transformers.transformer_omnigen2 import OmniGen2Transformer2DModel

    model_id = "OmniGen2/OmniGen2"
    pipe = OmniGen2Pipeline.from_pretrained(
        model_id, torch_dtype=torch.bfloat16, trust_remote_code=True,
    )
    pipe.transformer = OmniGen2Transformer2DModel.from_pretrained(
        model_id, subfolder="transformer", torch_dtype=torch.bfloat16,
    )
    pipe.enable_model_cpu_offload()
    print(f"  Loaded. GPU: {gpu_mb():.0f}MB")

    def gen_fn(image, prompt):
        img = image.copy()
        max_dim = 1024
        if max(img.size) > max_dim:
            ratio = max_dim / max(img.size)
            img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
        result = pipe(
            prompt=f"<img><|image_1|></img> {prompt}",
            input_images=[img],
            num_inference_steps=30,
            max_sequence_length=1024,
            text_guidance_scale=5.0,
            image_guidance_scale=1.8,
            negative_prompt="(((deformed))), blurry, over saturation, bad anatomy",
            generator=torch.Generator("cpu").manual_seed(42),
        )
        return result.images[0]

    clover_front = crop_front_view(CLOVER_REF)
    clover_full = load_full_ref(CLOVER_REF)
    results = run_edit_suite(name, gen_fn, clover_front, clover_full)

    del pipe
    clear_gpu()
    return name, results


# ============================================================
# 5. IP-Adapter Plus + SDXL
# ============================================================
def test_ipadapter():
    name = "ipadapter_sdxl"
    print(f"\n{'='*60}\n  IP-Adapter Plus + SDXL\n{'='*60}")

    from transformers import CLIPVisionModelWithProjection
    from diffusers import AutoPipelineForText2Image

    # Load correct ViT-H encoder for Plus weights
    image_encoder = CLIPVisionModelWithProjection.from_pretrained(
        "h94/IP-Adapter", subfolder="models/image_encoder",
        torch_dtype=torch.float16,
    )
    pipe = AutoPipelineForText2Image.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        image_encoder=image_encoder,
        torch_dtype=torch.float16,
    ).to("cuda")

    pipe.load_ip_adapter(
        "h94/IP-Adapter", subfolder="sdxl_models",
        weight_name="ip-adapter-plus_sdxl_vit-h.safetensors",
    )
    pipe.set_ip_adapter_scale(0.6)
    print(f"  Loaded. GPU: {gpu_mb():.0f}MB")

    clover_front = crop_front_view(CLOVER_REF).resize((1024, 1024), Image.LANCZOS)
    sable_front = crop_front_view(SABLE_REF).resize((1024, 1024), Image.LANCZOS)

    base = "1girl, orange wavy hair, calico cat ears, cat tail, brown apron, cream blouse, anime style, masterpiece, best quality"
    neg = "lowres, bad anatomy, bad hands, text, error, worst quality, low quality, deformed"

    out = OUTPUT_BASE / name
    out.mkdir(exist_ok=True)
    results = {}

    # Expression variants
    exprs = {
        "happy": f"{base}, happy smile, warm expression",
        "sad": f"{base}, sad expression, downcast eyes, slight frown",
        "angry": f"{base}, angry expression, furrowed brows, scowl",
        "surprised": f"{base}, surprised expression, wide eyes, open mouth",
        "embarrassed": f"{base}, embarrassed, blushing cheeks, averted eyes",
        "determined": f"{base}, determined expression, confident look",
    }

    print("\n  --- Expression Variants ---")
    for ename, prompt in exprs.items():
        tag = f"expr_{ename}"
        print(f"  {tag}...", end=" ", flush=True)
        t0 = time.time()
        try:
            img = pipe(
                prompt=prompt, negative_prompt=neg,
                ip_adapter_image=clover_front,
                num_inference_steps=30, guidance_scale=7.0,
                height=1024, width=768,
                generator=torch.Generator("cuda").manual_seed(42),
            ).images[0]
            dt = round(time.time() - t0, 2)
            fp = out / f"{tag}.png"
            img.save(fp)
            results[tag] = {"time": dt, "file": str(fp), "status": "success"}
            print(f"{dt:.1f}s")
        except Exception as e:
            results[tag] = {"status": "error", "error": str(e)[:300]}
            print(f"ERROR: {str(e)[:120]}")

    # CG scenes
    print("\n  --- CG Scenes ---")
    for cname, prompt in CG_SINGLE.items():
        tag = f"cg_{cname}"
        print(f"  {tag}...", end=" ", flush=True)
        t0 = time.time()
        try:
            img = pipe(
                prompt=f"{prompt}, masterpiece, best quality",
                negative_prompt=neg,
                ip_adapter_image=clover_front,
                num_inference_steps=30, guidance_scale=7.0,
                height=1024, width=1024,
                generator=torch.Generator("cuda").manual_seed(42),
            ).images[0]
            dt = round(time.time() - t0, 2)
            fp = out / f"{tag}.png"
            img.save(fp)
            results[tag] = {"time": dt, "file": str(fp), "status": "success"}
            print(f"{dt:.1f}s")
        except Exception as e:
            results[tag] = {"status": "error", "error": str(e)[:300]}
            print(f"ERROR: {str(e)[:120]}")

    # Multi-character CG
    print("\n  --- CG Multi-Character ---")
    for cname, prompt in CG_MULTI.items():
        tag = f"cg_multi_{cname}"
        print(f"  {tag}...", end=" ", flush=True)
        t0 = time.time()
        try:
            img = pipe(
                prompt=f"{prompt}, masterpiece, best quality",
                negative_prompt=neg,
                ip_adapter_image=clover_front,
                num_inference_steps=30, guidance_scale=7.0,
                height=1024, width=1024,
                generator=torch.Generator("cuda").manual_seed(42),
            ).images[0]
            dt = round(time.time() - t0, 2)
            fp = out / f"{tag}.png"
            img.save(fp)
            results[tag] = {"time": dt, "file": str(fp), "status": "success"}
            print(f"{dt:.1f}s")
        except Exception as e:
            results[tag] = {"status": "error", "error": str(e)[:300]}
            print(f"ERROR: {str(e)[:120]}")

    del pipe, image_encoder
    clear_gpu()
    return name, results


# ============================================================
# 6. SDXL Inpainting (face region)
# ============================================================
def test_inpainting():
    name = "sdxl_inpaint"
    print(f"\n{'='*60}\n  SDXL Inpainting (face region)\n{'='*60}")

    from diffusers import AutoPipelineForInpainting

    pipe = AutoPipelineForInpainting.from_pretrained(
        "diffusers/stable-diffusion-xl-1.0-inpainting-0.1",
        torch_dtype=torch.float16, variant="fp16",
    ).to("cuda")
    print(f"  Loaded. GPU: {gpu_mb():.0f}MB")

    clover_front = crop_front_view(CLOVER_REF)
    clover_resized = clover_front.resize((768, 1024), Image.LANCZOS)

    out = OUTPUT_BASE / name
    out.mkdir(exist_ok=True)
    clover_resized.save(out / "clover_front_resized.png")

    # Create face mask
    face_mask = Image.new("L", (768, 1024), 0)
    draw = ImageDraw.Draw(face_mask)
    draw.ellipse([230, 20, 530, 350], fill=255)
    face_mask.save(out / "face_mask.png")

    base = "1girl, anime style, orange wavy hair, calico cat ears"
    neg = "lowres, bad anatomy, worst quality, low quality, deformed"
    results = {}

    exprs = {
        "happy": f"{base}, happy smile, warm eyes, masterpiece, best quality",
        "sad": f"{base}, sad expression, teary eyes, masterpiece, best quality",
        "angry": f"{base}, angry, furrowed brows, fierce eyes, masterpiece, best quality",
        "surprised": f"{base}, surprised, wide eyes, open mouth, masterpiece, best quality",
    }

    print("\n  --- Face Inpainting ---")
    for ename, prompt in exprs.items():
        tag = f"inpaint_{ename}"
        print(f"  {tag}...", end=" ", flush=True)
        t0 = time.time()
        try:
            img = pipe(
                prompt=prompt, negative_prompt=neg,
                image=clover_resized, mask_image=face_mask,
                num_inference_steps=30, guidance_scale=7.5,
                strength=0.65,
                generator=torch.Generator("cuda").manual_seed(42),
            ).images[0]
            dt = round(time.time() - t0, 2)
            fp = out / f"{tag}.png"
            img.save(fp)
            results[tag] = {"time": dt, "file": str(fp), "status": "success"}
            print(f"{dt:.1f}s")
        except Exception as e:
            results[tag] = {"status": "error", "error": str(e)[:300]}
            print(f"ERROR: {str(e)[:120]}")

    del pipe
    clear_gpu()
    return name, results


# ============================================================
# MAIN
# ============================================================
def main():
    tests = [
        test_flux_kontext,
        test_qwen_edit,
        test_longcat,
        test_omnigen2,
        test_ipadapter,
        test_inpainting,
    ]

    for fn in tests:
        try:
            mname, res = fn()
            all_results[mname] = {"results": res, "status": "success"}
        except Exception as e:
            print(f"\n  FATAL: {e}")
            import traceback; traceback.print_exc()
            all_results[fn.__name__] = {"status": "error", "error": str(e)[:500]}
        clear_gpu()
        save_progress()

    print(f"\n{'='*60}")
    print("PHASE 4 FINAL SUMMARY")
    print(f"{'='*60}")
    for m, d in all_results.items():
        if d.get("status") == "success" and "results" in d:
            s = sum(1 for v in d["results"].values() if isinstance(v, dict) and v.get("status") == "success")
            t = len(d["results"])
            times = [v["time"] for v in d["results"].values() if isinstance(v, dict) and "time" in v]
            avg = sum(times) / len(times) if times else 0
            print(f"  {m}: {s}/{t} succeeded, avg {avg:.1f}s/image")
        else:
            print(f"  {m}: FAILED - {d.get('error', 'unknown')[:80]}")


if __name__ == "__main__":
    main()
