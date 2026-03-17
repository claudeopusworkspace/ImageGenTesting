"""Run Qwen-Image-Edit-2511 tests via ComfyUI API.

Prerequisites:
  - ComfyUI server running at localhost:8188
  - Model files: qwen_image_edit_2511_fp8_e4m3fn.safetensors,
    qwen_2.5_vl_7b_fp8_scaled.safetensors, qwen_image_vae.safetensors
"""

import json
import time
import uuid
import urllib.request
import urllib.parse
from pathlib import Path
from PIL import Image
import io as sysio

SERVER = "127.0.0.1:8188"
OUTPUT_BASE = Path("/workspace/ImageGenTesting/outputs/phase4_editing/qwen_edit_comfyui")
OUTPUT_BASE.mkdir(parents=True, exist_ok=True)


def upload_image(filepath, name=None):
    """Upload an image to ComfyUI input directory."""
    if name is None:
        name = Path(filepath).name
    img = Image.open(filepath).convert("RGB")
    buf = sysio.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    boundary = uuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{name}"\r\n'
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


def build_qwen_edit_workflow(image_name, prompt, seed=42, steps=20, cfg=4.0):
    """Build a Qwen-Image-Edit-2511 API workflow."""
    return {
        # CLIPLoader - text encoder
        "1": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
                "type": "qwen_image",
            },
        },
        # VAELoader
        "2": {
            "class_type": "VAELoader",
            "inputs": {
                "vae_name": "qwen_image_vae.safetensors",
            },
        },
        # UNETLoader - diffusion model (FP8)
        "3": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": "qwen_image_edit_2511_fp8_e4m3fn.safetensors",
                "weight_dtype": "fp8_e4m3fn",
            },
        },
        # ModelSamplingAuraFlow
        "4": {
            "class_type": "ModelSamplingAuraFlow",
            "inputs": {
                "model": ["3", 0],
                "shift": 3.1,
            },
        },
        # CFGNorm
        "5": {
            "class_type": "CFGNorm",
            "inputs": {
                "model": ["4", 0],
                "strength": 1.0,
            },
        },
        # LoadImage
        "6": {
            "class_type": "LoadImage",
            "inputs": {
                "image": image_name,
            },
        },
        # FluxKontextImageScale (resize input)
        "7": {
            "class_type": "FluxKontextImageScale",
            "inputs": {
                "image": ["6", 0],
            },
        },
        # TextEncodeQwenImageEditPlus (positive - with image and prompt)
        "8": {
            "class_type": "TextEncodeQwenImageEditPlus",
            "inputs": {
                "clip": ["1", 0],
                "vae": ["2", 0],
                "image1": ["7", 0],
                "prompt": prompt,
            },
        },
        # FluxKontextMultiReferenceLatentMethod (positive)
        "9": {
            "class_type": "FluxKontextMultiReferenceLatentMethod",
            "inputs": {
                "conditioning": ["8", 0],
                "reference_latents_method": "index_timestep_zero",
            },
        },
        # TextEncodeQwenImageEditPlus (negative - empty prompt, same image)
        "10": {
            "class_type": "TextEncodeQwenImageEditPlus",
            "inputs": {
                "clip": ["1", 0],
                "vae": ["2", 0],
                "image1": ["7", 0],
                "prompt": "",
            },
        },
        # FluxKontextMultiReferenceLatentMethod (negative)
        "11": {
            "class_type": "FluxKontextMultiReferenceLatentMethod",
            "inputs": {
                "conditioning": ["10", 0],
                "reference_latents_method": "index_timestep_zero",
            },
        },
        # VAEEncode (input image to latent)
        "12": {
            "class_type": "VAEEncode",
            "inputs": {
                "pixels": ["7", 0],
                "vae": ["2", 0],
            },
        },
        # KSampler
        "13": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["5", 0],
                "positive": ["9", 0],
                "negative": ["11", 0],
                "latent_image": ["12", 0],
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,
            },
        },
        # VAEDecode
        "14": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["13", 0],
                "vae": ["2", 0],
            },
        },
        # SaveImage
        "15": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "qwen_edit",
                "images": ["14", 0],
            },
        },
    }


def submit_and_wait(workflow, timeout=600):
    """Submit workflow and poll for completion."""
    prompt_id = str(uuid.uuid4())
    client_id = str(uuid.uuid4())
    payload = json.dumps({
        "prompt": workflow,
        "client_id": client_id,
    }).encode()

    req = urllib.request.Request(
        f"http://{SERVER}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    actual_prompt_id = resp.get("prompt_id", prompt_id)

    # Poll for completion
    start = time.time()
    while time.time() - start < timeout:
        try:
            hist_resp = urllib.request.urlopen(
                f"http://{SERVER}/history/{actual_prompt_id}"
            ).read()
            history = json.loads(hist_resp)
            if actual_prompt_id in history:
                return history[actual_prompt_id]
        except Exception:
            pass
        time.sleep(2)

    raise TimeoutError(f"Workflow did not complete within {timeout}s")


def download_image(filename, subfolder="", folder_type="output"):
    """Download an output image from ComfyUI."""
    params = urllib.parse.urlencode({
        "filename": filename,
        "subfolder": subfolder,
        "type": folder_type,
    })
    resp = urllib.request.urlopen(f"http://{SERVER}/view?{params}")
    return resp.read()


def run_test(image_path, prompt, output_name, seed=42, steps=20, cfg=4.0):
    """Run a single Qwen edit test."""
    # Upload input image
    uploaded_name = upload_image(image_path, f"test_input_{output_name}.png")

    # Build and submit workflow
    workflow = build_qwen_edit_workflow(uploaded_name, prompt, seed, steps, cfg)

    t0 = time.time()
    result = submit_and_wait(workflow)
    dt = round(time.time() - t0, 2)

    # Find and download output image
    for node_id, node_output in result.get("outputs", {}).items():
        if "images" in node_output:
            for img_info in node_output["images"]:
                img_data = download_image(
                    img_info["filename"],
                    img_info.get("subfolder", ""),
                    img_info.get("type", "output"),
                )
                out_path = OUTPUT_BASE / f"{output_name}.png"
                with open(out_path, "wb") as f:
                    f.write(img_data)
                return {"time": dt, "file": str(out_path), "status": "success"}

    return {"status": "error", "error": "No output image found"}


def main():
    CLOVER_REF = "/workspace/NekoCafe/Art/References/Clover.png"

    # Crop front view
    img = Image.open(CLOVER_REF).convert("RGB")
    w, h = img.size
    front = img.crop((0, 0, w // 3, h))
    front_path = OUTPUT_BASE / "clover_front_crop.png"
    front.save(front_path)

    TESTS = {
        "expr_happy": "Make the character smile warmly with a happy expression",
        "expr_sad": "Make the character look sad with downcast eyes and a slight frown",
        "expr_angry": "Make the character look angry with furrowed brows and a scowl",
        "expr_surprised": "Make the character look surprised with wide eyes and open mouth",
        "expr_embarrassed": "Make the character look embarrassed with blushing cheeks and averted eyes",
        "expr_determined": "Make the character look determined with a confident, focused expression",
        "scene_winter_outfit": "Change the character's outfit to a cozy winter coat with a scarf",
        "scene_cafe_scene": "Place the character in a cozy cafe setting behind a counter with coffee cups, warm lighting",
        "scene_outdoor_scene": "Place the character in a sunny garden with flowers and trees",
        "cg_serving_coffee": "An anime catgirl with orange wavy hair, calico cat ears, and a brown apron, cheerfully serving coffee in a cozy cafe, warm lighting, visual novel illustration",
        "cg_reading_book": "An anime catgirl with orange wavy hair, calico cat ears, sitting by a window reading a book, soft afternoon light, peaceful, visual novel illustration",
    }

    results = {"backend": "comfyui", "quantization": "fp8_e4m3fn"}
    for tag, prompt in TESTS.items():
        ref = str(front_path) if not tag.startswith("cg_") else CLOVER_REF
        print(f"  {tag}...", end=" ", flush=True)
        try:
            r = run_test(ref, prompt, tag)
            results[tag] = r
            print(f"{r.get('time', '?')}s")
        except Exception as e:
            results[tag] = {"status": "error", "error": str(e)[:300]}
            print(f"ERROR: {str(e)[:120]}")

    # Save results
    results_file = Path("/workspace/ImageGenTesting/results/phase4_results.json")
    with open(results_file) as f:
        all_results = json.load(f)
    all_results["qwen_edit_comfyui"] = {"results": results, "status": "success"}
    with open(results_file, "w") as f:
        json.dump(all_results, f, indent=2)

    s = sum(1 for v in results.values() if isinstance(v, dict) and v.get("status") == "success")
    times = [v["time"] for v in results.values() if isinstance(v, dict) and "time" in v]
    avg = sum(times) / len(times) if times else 0
    print(f"\nDONE: {s}/{len(TESTS)} succeeded, avg {avg:.1f}s/image")


if __name__ == "__main__":
    main()
