# Image Generation for Game Development: Final Recommendations

**Date**: 2026-03-17
**Hardware**: RTX 5090 (32GB VRAM), 30GB system RAM, CUDA 12.8
**Models Tested**: 8 configurations across 3 base models + 5 LoRAs
**Total Images Generated**: ~130+

---

## Executive Summary

After extensive testing, **FLUX.1-dev (4-bit quantized)** is the best overall model for generating game art assets. It produces the most consistent, prompt-adherent, game-ready outputs across all categories. However, no single model/configuration solves everything — a practical pipeline requires combining multiple tools.

---

## Model Rankings

### For Pixel Art Game Assets
| Rank | Model | Avg Score | Speed | Notes |
|------|-------|-----------|-------|-------|
| 1 | FLUX.1-dev 4-bit (base) | 6.5/10 | 19.6s/img | Best prompt adherence, truest pixel art |
| 2 | SDXL + pixel-art-xl LoRA | 6.5/10 | 3.8s/img | Best SDXL config, much faster |
| 3 | SDXL + PixelArtRedmond | 6.4/10 | 3.1s/img | Similar quality, fastest option |
| 4 | PixArt-Sigma | 6.0/10 | 2.1s/img | Highest peaks but inconsistent |

### For Non-Pixel Game Art (Characters, Environments)
| Rank | Model | Best At |
|------|-------|---------|
| 1 | PixArt-Sigma | Characters, isometric buildings (9/10 peak!) |
| 2 | FLUX.1-dev 4-bit | Consistent quality across everything |
| 3 | SDXL Base | Environment backgrounds (8/10) |

### Speed vs Quality Tradeoff
| Model | Speed | Quality | Best For |
|-------|-------|---------|----------|
| PixArt-Sigma | 2.1s | Variable (3-9) | Rapid iteration, concept art |
| SDXL + LoRA | 3.1s | Consistent (5-8) | Pixel art batch production |
| FLUX.1-dev 4-bit | 19.6s | Consistent (5-7) | Final quality assets |

---

## What Works

### Background Removal (rembg)
- **Verdict: Viable for production.** ~1.5s per image, produces clean RGBA output.
- Best on: centered characters, clear subjects on light backgrounds
- Struggles with: small subjects in large canvases, foot shadows, semi-transparent elements
- **Recommendation**: Generate on white background, use rembg, manually clean up edges if needed.

### Multi-Pose Character Generation
- **FLUX wins decisively.** Produces single centered characters that actually change pose.
- SDXL generates scattered sprite sheets instead of single posed characters.
- Character identity drifts between poses (design elements change). Not yet reliable for animation frames.
- **Recommendation**: Use FLUX for individual pose generation, plan for manual cleanup.

### Downscaling to Game Resolution
- **FLUX output downscales beautifully.** Characters remain readable at 64x64 and even 48x48.
- Always use nearest-neighbor resampling for pixel art (Image.NEAREST in PIL).
- SDXL output downscales poorly because subjects are often small within large compositions.

---

## What Doesn't Work (Yet)

### Transparent Backgrounds
**No model generates true transparency.** All output solid/near-solid backgrounds. Background removal is a mandatory post-processing step.

### Tilesets
**Complete failure across all models.** Every model produces scenes instead of repeatable tile grids. Tileset generation requires either:
- Generating individual tiles separately and assembling
- Using ControlNet with a grid overlay
- A specialized tileset-trained model (none found that work well)

### UI Elements
**Universal weak spot.** Models don't understand "button" as a UI concept. Scores ranged 3-7/10. Game UI likely needs traditional design or specialized training data.

### Animation Sprite Sheets
**Not viable with current approaches.** Character identity drifts too much between poses for seamless animation. Multi-frame consistency requires:
- ControlNet pose guidance (not tested due to complexity)
- IP-Adapter reference images (not tested)
- Manual artist cleanup of each frame
- Potentially the SpriteSheetDiffusion research project

### Resolution Control
**Completely ignored.** Requests for 32x32 or 64x64 have zero effect. All models output at their native resolution (1024x1024). Post-processing downscale is mandatory.

---

## Recommended Production Pipeline

```
1. CONCEPT PHASE (fast iteration)
   ├── Use PixArt-Sigma (2.1s/image) for rapid concept exploration
   └── Use different seeds to explore design space

2. ASSET GENERATION (quality)
   ├── Characters/Sprites: FLUX.1-dev 4-bit, one pose at a time
   ├── Pixel Art Items: SDXL + pixel-art-xl LoRA (fast + good quality)
   ├── Buildings/Objects: PixArt-Sigma (best peaks) or FLUX
   └── Environments: SDXL Base (gorgeous backgrounds)

3. POST-PROCESSING (mandatory)
   ├── Background removal: rembg (automatic, ~1.5s)
   ├── Downscale: PIL nearest-neighbor to target resolution
   ├── Edge cleanup: Manual touch-up where needed
   └── Color palette enforcement: Optional, for strict pixel art

4. ASSEMBLY
   ├── Collect individual poses into sprite sheets manually
   ├── Ensure consistent scaling across all assets
   └── Test in-engine for final validation
```

---

## License Safety for Commercial Games

| Model | License | Commercial Safe? |
|-------|---------|-----------------|
| FLUX.1-dev | Non-commercial weights, commercial outputs | YES for generated art |
| SDXL | Open RAIL++ | YES |
| PixArt-Sigma | Open RAIL++ | YES |
| pixel-art-xl LoRA | SDXL derivative | YES |
| PixelArtRedmond LoRA | Check model card | Likely YES |

**Safest choice**: SDXL + SDXL-based LoRAs (fully open license chain).

---

## Hardware Notes

- **RTX 5090 (32GB VRAM)**: Can run any model tested, but FLUX.1-dev at full bf16 uses all 32GB and becomes unusably slow. 4-bit quantization is essential.
- **30GB System RAM**: Too tight for FLUX CPU offloading at full precision (OOM killed). Quantization solves this.
- **Disk Usage**: Models cached in `~/.cache/huggingface/`. FLUX.1-dev is ~24GB, SDXL is ~7GB, PixArt is ~2.5GB.
- **FLUX.1-schnell**: Gated on HuggingFace, requires authentication. Would be ideal (Apache 2.0, 4 steps) if accessible.

---

## Future Exploration

1. **ControlNet** for pose-guided generation (highest impact for animation)
2. **IP-Adapter** for style-locked multi-asset generation
3. **FLUX.1-schnell** if HuggingFace access can be arranged
4. **LayerDiffuse** for native transparency (eliminates rembg step)
5. **SpriteSheetDiffusion** research project for multi-frame consistency
6. **LoRA training** on a specific game's art style for perfect consistency
