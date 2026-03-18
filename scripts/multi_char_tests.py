"""Multi-character tests: Clover + Sable together.

Tests Qwen-Image-Edit (via ComfyUI) and FLUX Kontext with two reference images.
"""

import json
import time
import uuid
import gc
import urllib.request
import urllib.parse
import io as sysio
import torch
from pathlib import Path
from PIL import Image

OUTPUT_BASE = Path("/workspace/ImageGenTesting/outputs/phase4_editing/multi_character")
OUTPUT_BASE.mkdir(parents=True, exist_ok=True)
RESULTS_FILE = Path("/workspace/ImageGenTesting/results/phase4_results.json")

CLOVER_REF = "/workspace/NekoCafe/Art/References/Clover.png"
SABLE_REF = "/workspace/NekoCafe/Art/References/Sable.png"

MULTI_PROMPTS = {
    "working_together": "Two catgirl baristas working together in a cozy cafe. The first has orange wavy hair with calico ears and a brown apron. The second has short dark brown hair with dark brown ears, darker skin, and a black apron. They prepare drinks together behind the counter, warm lighting, visual novel illustration.",
    "studying_together": "Two catgirls studying together at a table. The first has orange wavy hair and calico cat ears, wearing a cream blouse. The second has short dark brown hair and dark brown cat ears, with darker skin. Books and papers between them, cozy library setting, visual novel illustration.",
    "arguing_playfully": "Two catgirls in a playful argument. The first (orange wavy hair, calico ears, brown apron) looks flustered and embarrassed. The second (short dark hair, dark ears, darker skin, black apron) has a smug teasing expression. Cafe interior, visual novel illustration.",
}


def crop_front_view(path):
    img = Image.open(path).convert("RGB")
    w, h = img.size
    return img.crop((0, 0, w // 3, h))


# ============================================================
# Qwen via ComfyUI (supports image1, image2, image3)
# ============================================================
def test_qwen_multi():
    SERVER = "127.0.0.1:8188"
    name = "qwen_multi"
    out = OUTPUT_BASE / name
    out.mkdir(exist_ok=True)

    print(f"\n{'='*60}\n  Qwen-Image-Edit Multi-Character (ComfyUI)\n{'='*60}")

    # Check server is running
    try:
        urllib.request.urlopen(f"http://{SERVER}/system_stats", timeout=5)
    except Exception:
        print("  ERROR: ComfyUI server not running at localhost:8188")
        return name, {"status": "error", "error": "ComfyUI server not running"}

    def upload_image(filepath, upload_name):
        img = Image.open(filepath).convert("RGB")
        buf = sysio.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        boundary = uuid.uuid4().hex
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="image"; filename="{upload_name}"\r\n'
            f"Content-Type: image/png\r\n\r\n"
        ).encode() + buf.read() + (
            f"\r\n--{boundary}\r\n"
            f'Content-Disposition: form-data; name="overwrite"\r\n\r\n'
            f"true\r\n--{boundary}--\r\n"
        ).encode()
        req = urllib.request.Request(
            f"http://{SERVER}/upload/image",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        resp = json.loads(urllib.request.urlopen(req).read())
        return resp["name"]

    # Upload both character references
    clover_front = crop_front_view(CLOVER_REF)
    sable_front = crop_front_view(SABLE_REF)
    clover_front.save("/tmp/clover_front_multi.png")
    sable_front.save("/tmp/sable_front_multi.png")

    clover_name = upload_image("/tmp/clover_front_multi.png", "clover_front.png")
    sable_name = upload_image("/tmp/sable_front_multi.png", "sable_front.png")
    print(f"  Uploaded: {clover_name}, {sable_name}")

    def build_workflow(prompt, seed=42, steps=20, cfg=4.0):
        return {
            "1": {"class_type": "CLIPLoader", "inputs": {
                "clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "type": "qwen_image"}},
            "2": {"class_type": "VAELoader", "inputs": {
                "vae_name": "qwen_image_vae.safetensors"}},
            "3": {"class_type": "UNETLoader", "inputs": {
                "unet_name": "qwen_image_edit_2511_fp8_e4m3fn.safetensors", "weight_dtype": "fp8_e4m3fn"}},
            "4": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["3", 0], "shift": 3.1}},
            "5": {"class_type": "CFGNorm", "inputs": {"model": ["4", 0], "strength": 1.0}},
            "6": {"class_type": "LoadImage", "inputs": {"image": clover_name}},
            "7": {"class_type": "LoadImage", "inputs": {"image": sable_name}},
            "8": {"class_type": "FluxKontextImageScale", "inputs": {"image": ["6", 0]}},
            # Positive: both images + prompt
            "9": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {
                "clip": ["1", 0], "vae": ["2", 0],
                "image1": ["8", 0], "image2": ["7", 0],
                "prompt": prompt}},
            "10": {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {
                "conditioning": ["9", 0], "reference_latents_method": "index_timestep_zero"}},
            # Negative: both images, empty prompt
            "11": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {
                "clip": ["1", 0], "vae": ["2", 0],
                "image1": ["8", 0], "image2": ["7", 0],
                "prompt": ""}},
            "12": {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {
                "conditioning": ["11", 0], "reference_latents_method": "index_timestep_zero"}},
            # Encode + Sample + Decode
            "13": {"class_type": "VAEEncode", "inputs": {"pixels": ["8", 0], "vae": ["2", 0]}},
            "14": {"class_type": "KSampler", "inputs": {
                "model": ["5", 0], "positive": ["10", 0], "negative": ["12", 0],
                "latent_image": ["13", 0], "seed": seed, "steps": steps, "cfg": cfg,
                "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
            "15": {"class_type": "VAEDecode", "inputs": {"samples": ["14", 0], "vae": ["2", 0]}},
            "16": {"class_type": "SaveImage", "inputs": {"filename_prefix": "qwen_multi", "images": ["15", 0]}},
        }

    results = {}
    for tag, prompt in MULTI_PROMPTS.items():
        print(f"  {tag}...", end=" ", flush=True)
        t0 = time.time()
        try:
            workflow = build_workflow(prompt, seed=42)
            payload = json.dumps({"prompt": workflow, "client_id": str(uuid.uuid4())}).encode()
            req = urllib.request.Request(f"http://{SERVER}/prompt", data=payload,
                                         headers={"Content-Type": "application/json"})
            resp = json.loads(urllib.request.urlopen(req).read())
            prompt_id = resp["prompt_id"]

            # Poll for completion
            for _ in range(300):
                time.sleep(2)
                hist = json.loads(urllib.request.urlopen(f"http://{SERVER}/history/{prompt_id}").read())
                if prompt_id in hist:
                    break

            dt = round(time.time() - t0, 2)

            # Download output
            outputs = hist[prompt_id].get("outputs", {})
            saved = False
            for nid, nout in outputs.items():
                if "images" in nout:
                    for img_info in nout["images"]:
                        params = urllib.parse.urlencode({
                            "filename": img_info["filename"],
                            "subfolder": img_info.get("subfolder", ""),
                            "type": img_info.get("type", "output")})
                        img_data = urllib.request.urlopen(f"http://{SERVER}/view?{params}").read()
                        fp = out / f"{tag}.png"
                        with open(fp, "wb") as f:
                            f.write(img_data)
                        results[tag] = {"time": dt, "file": str(fp), "status": "success"}
                        saved = True
                        break
                if saved:
                    break
            if not saved:
                results[tag] = {"status": "error", "error": "No output image"}
            print(f"{dt:.1f}s")
        except Exception as e:
            results[tag] = {"status": "error", "error": str(e)[:300]}
            print(f"ERROR: {str(e)[:120]}")

    return name, results


# ============================================================
# FLUX Kontext (supports multi-image via list)
# ============================================================
def test_kontext_multi():
    name = "kontext_multi"
    out = OUTPUT_BASE / name
    out.mkdir(exist_ok=True)

    print(f"\n{'='*60}\n  FLUX Kontext Multi-Character\n{'='*60}")

    from diffusers import FluxKontextPipeline, FluxTransformer2DModel, BitsAndBytesConfig

    model_id = "black-forest-labs/FLUX.1-Kontext-dev"
    qconfig = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16)
    transformer = FluxTransformer2DModel.from_pretrained(
        model_id, subfolder="transformer", quantization_config=qconfig, torch_dtype=torch.bfloat16)
    pipe = FluxKontextPipeline.from_pretrained(
        model_id, transformer=transformer, torch_dtype=torch.bfloat16)
    pipe.enable_model_cpu_offload()
    print("  Loaded.")

    clover_front = crop_front_view(CLOVER_REF)
    sable_front = crop_front_view(SABLE_REF)

    # Composite both characters side by side as input
    cw, ch = clover_front.size
    sw, sh = sable_front.size
    composite = Image.new("RGB", (cw + sw, max(ch, sh)), (255, 255, 255))
    composite.paste(clover_front, (0, 0))
    composite.paste(sable_front, (cw, 0))
    composite.save(out / "composite_input.png")

    results = {}
    for tag, prompt in MULTI_PROMPTS.items():
        print(f"  {tag}...", end=" ", flush=True)
        t0 = time.time()
        try:
            # Use composite as single reference
            result = pipe(
                image=composite,
                prompt=f"Using the two characters shown in the reference image: {prompt}",
                guidance_scale=2.5, num_inference_steps=24,
                height=1024, width=1472,
                generator=torch.Generator("cpu").manual_seed(42),
            ).images[0]
            dt = round(time.time() - t0, 2)
            fp = out / f"{tag}.png"
            result.save(fp)
            results[tag] = {"time": dt, "file": str(fp), "status": "success"}
            print(f"{dt:.1f}s")
        except Exception as e:
            results[tag] = {"status": "error", "error": str(e)[:300]}
            print(f"ERROR: {str(e)[:120]}")

    del pipe, transformer
    gc.collect()
    torch.cuda.empty_cache()
    return name, results


# ============================================================
# MAIN
# ============================================================
def main():
    with open(RESULTS_FILE) as f:
        all_results = json.load(f)

    # Qwen first (ComfyUI server should already be running)
    mname, res = test_qwen_multi()
    all_results[mname] = {"results": res, "status": "success"} if isinstance(res, dict) and "status" not in res else res if isinstance(res, dict) and "status" in res and res["status"] == "error" else {"results": res, "status": "success"}
    with open(RESULTS_FILE, "w") as f:
        json.dump(all_results, f, indent=2)

    # FLUX Kontext
    mname, res = test_kontext_multi()
    all_results[mname] = {"results": res, "status": "success"}
    with open(RESULTS_FILE, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n{'='*60}")
    print("MULTI-CHARACTER SUMMARY")
    print(f"{'='*60}")
    for m in ["qwen_multi", "kontext_multi"]:
        d = all_results.get(m, {})
        r = d.get("results", d)
        if isinstance(r, dict):
            s = sum(1 for v in r.values() if isinstance(v, dict) and v.get("status") == "success")
            t = sum(1 for v in r.values() if isinstance(v, dict) and "status" in v)
            times = [v["time"] for v in r.values() if isinstance(v, dict) and "time" in v]
            avg = sum(times) / len(times) if times else 0
            print(f"  {m}: {s}/{t} succeeded, avg {avg:.1f}s/image")


if __name__ == "__main__":
    main()
