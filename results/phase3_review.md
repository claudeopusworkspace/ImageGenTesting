# Phase 3 Review: Sprite Pipeline Consistency & Post-Processing

**Reviewer**: Claude Opus 4.6
**Date**: 2026-03-17
**Scope**: Background removal (rembg), seed consistency, multi-pose character generation (SDXL vs FLUX), and downscale quality for game target resolutions.

---

## 1. Background Removal Quality (rembg)

### Overall Assessment: MIXED -- some excellent, some problematic

#### Per-Image Breakdown

| Image | Quality | Notes |
|-------|---------|-------|
| **flux_character_nobg** | **Excellent** | Clean cutout of the chibi knight character. Edges follow the pixel-art stairstepping faithfully. No visible fringing or halo artifacts. The helmet, pauldrons, sword, and shield are all preserved with crisp boundaries. Ready to drop into a game engine as-is. |
| **flux_enemy_nobg** | **Good** | The green slime creature is cleanly separated. Minor issue: a faint gray shadow remnant persists beneath the tentacles/base. This would be visible on non-white game backgrounds. Easily fixable with a threshold pass on the alpha channel, but not perfect out of the box. |
| **flux_pixel_sword_nobg** | **Poor** | The sword is positioned awkwardly in the bottom-left quadrant with the majority of the canvas empty. More critically, the sword itself appears to be a low-detail, washed-out pixel item -- possibly the rembg model struggled with the small subject on a large canvas. The result is not directly usable; the subject would need to be cropped and the empty space trimmed. |
| **pixart_character_nobg** | **Very Good** | The PixArt warrior with red shield has a clean extraction. Slight gray fringe visible at the sword tip near the ground and faint shadow remnants at the feet. The character itself is well-isolated. The higher detail level of PixArt's output seems to have helped rembg find cleaner boundaries. |
| **pixart_isometric_nobg** | **Excellent** | Surprisingly strong result for a complex isometric building. The tavern/shop structure is cleanly extracted with the cobblestone base intact. Minor artifacts at the left edge near the small tree/bush element, but overall this is impressive given how challenging isometric scenes are for background removal. |
| **sdxl_pixelart_sword_nobg** | **Good (but wrong use case)** | This image contains a sprite sheet of ~12 swords with a shield, all on a white background. rembg correctly removed the white background from the entire sheet. However, for actual game use, you would need to slice this into individual sprites first. The extraction itself is clean with no fringing around the individual weapons. |
| **sdxl_pixelart_character_nobg** | **Very Good** | Small knight character cleanly extracted. The character is tiny relative to the canvas (centered in the lower-middle area), which means the actual sprite occupies maybe 15-20% of the image area. Clean edges on the character itself. Faint shadow remnant under the feet. Would need cropping to the bounding box for game use. |

#### Key Findings -- Background Removal

- **rembg handles pixel art well** when the subject is clearly defined and fills a reasonable portion of the frame. The algorithm correctly follows the hard pixel-art edges rather than trying to smooth them.
- **Shadow remnants are the most common artifact.** Almost every character has a faint gray puddle under their feet that survives the removal. This is a known weakness -- drop shadows are ambiguous to the model.
- **Small subjects on large canvases produce poor results.** The flux_pixel_sword is the clearest example. When the subject is tiny, rembg has less signal to work with.
- **Processing time is fast** (~1.1-1.5s per image) except for the first run (16s for flux_pixel_sword, likely model loading overhead).

---

## 2. Style Consistency Assessment

### 2a. Seed Consistency (SDXL, same prompt, different seeds)

**Assessment: HIGH VARIATION -- not usable for same-character consistency**

The five warrior images generated with seeds 42, 123, 456, 789, and 1024 show wildly inconsistent results:

- **seed42**: Produced a full sprite sheet with ~20+ tiny warrior variations in different sizes, poses, and proportions. Not a single character -- it interpreted the prompt as a reference sheet.
- **seed123**: A single character, front-facing, standing pose. Taller proportions, white/silver armor, green eyes, auburn hair. Clean pixel art aesthetic.
- **seed456**: A single character in an action pose with sword raised. Helmeted, blue-gray armor with teal accents. Completely different proportions and color scheme from seed123.
- **seed789**: Another multi-character sprite sheet, this time showing ~8 views of a warrior in white/brown armor with blue belt. More internally consistent than seed42 but still a sheet, not a single sprite.
- **seed1024**: A single chibi-style character. Shorter, stockier proportions than seed123/456. Red-brown hair, blue-gray armor. Different art style from all others.

**Verdict**: Changing seeds produces completely different interpretations of the same prompt -- different body proportions, different armor designs, different color palettes, different composition choices (single character vs. sprite sheet). Seeds alone cannot be relied upon for generating consistent character variants. The model treats each seed as an independent creative interpretation.

### 2b. Multi-Pose: SDXL (same character, different poses)

**Assessment: POOR character consistency, GOOD thematic consistency**

All five SDXL knight images (front, side, back, attack, hurt) share a common color palette (blue armor, red plume) and thematic elements, but they are clearly NOT the same character:

- **knight_front**: A scattered pattern of ~20+ tiny knight sprites, equipment pieces, and helmet icons. Not a single character at all -- it generated a tileset/icon sheet.
- **knight_side**: Similar scattered pattern, ~30+ tiny sprites of knights in various poses and equipment. Consistent blue/red color scheme but no single coherent character.
- **knight_back**: Same pattern, ~20+ small sprites now mixed with shields, torches, gravestones, and armor pieces. Looks more like RPG tileset elements than a character pose.
- **knight_attack**: Similar collection of small knight sprites, swords, shields, and equipment. Many different character proportions within the same image.
- **knight_hurt**: The most coherent of the set. Shows ~8 larger knight figures in various poses, front and side views. These share more consistent proportions (stocky, large helmet) but are still multiple figures, not one character in a hurt pose.

**Verdict**: SDXL fundamentally struggles with the "single character in a specific pose" instruction for pixel art. It gravitates heavily toward generating sprite sheets and tileset collections instead. While the color palette (blue armor, red accents) is remarkably consistent across all five images, the actual character design, proportions, and composition vary drastically. This is not usable for generating animation frames of a single character.

### 2c. Multi-Pose: FLUX (same character, different poses)

**Assessment: MUCH BETTER than SDXL -- genuinely promising**

The four FLUX knight images show dramatically better pose control and character consistency:

- **knight_front**: A single chibi knight, front-facing. Gray helmet with red plume, black visor, blue tunic, gray armor, brown belt with gold buckle. Clean, centered composition.
- **knight_side**: The same basic character design in a walking/side pose. Helmet, red plume, blue outfit, gray armor all present. Proportions are consistent. The face is now visible (small eyes peeking out from helmet). Slightly more detailed.
- **knight_back**: Back view showing blue armor from behind. Red plume visible. Brown belt. Proportions match. The color scheme shifts slightly (more blue, less gray) but the character is recognizably the same knight.
- **knight_attack**: Attack pose with sword drawn. The helmet now has a full face guard/cross visor, and a red cape/cloak has appeared that wasn't in other poses. The character is stockier/more armored looking. This is the weakest consistency-wise, but still clearly "the same character" in a way that SDXL never achieved.

**Verdict**: FLUX delivers single, centered characters as requested and maintains reasonable consistency across poses. The core design (gray helmet, red plume, blue tunic, small chibi proportions) persists across all four images. The attack pose introduces the most drift (added cape, changed visor style). For a game pipeline, this is a viable starting point -- you could use these as reference sketches and do light touch-up to harmonize the details. However, it is not perfect enough to use raw frames as animation sprites without manual editing.

---

## 3. Downscale Quality Assessment

### FLUX Source Images

| Target Size | Quality | Notes |
|-------------|---------|-------|
| **flux_sword_32** | **Decent** | The sword is recognizable as a sword at 32x32 via nearest-neighbor. The crossguard and blade shape survive. Color banding is noticeable but acceptable for a 32px icon. Usable for inventory icons. |
| **flux_sword_64** | **Good** | At 64x64, the sword reads clearly. The stairstepped blade edge, crossguard, and pommel are all legible. This is a comfortable size for the original's level of detail. |
| **flux_char_64** | **Very Good** | The chibi knight character retains its key features -- helmet, pauldrons, sword, shield, belt sash -- all clearly readable at 64x64. The face (simple dot eyes and smile) survives. This is an impressive result and demonstrates that FLUX pixel art is actually designed at a detail level that works well at 64px. |
| **flux_char_128** | **Excellent** | At 128x128, this is essentially the full-detail version. All pixel-art detail is preserved. The character looks like a polished game sprite at this size. Would work perfectly for a game targeting this resolution. |
| **flux_enemy_48** | **Good** | The green slime at 48x48 retains its shape, eyes, and highlight. The tentacle/base area loses some definition but the character reads well. Perfectly usable as a small enemy sprite. |

### SDXL Source Images (PixArt LoRA)

| Target Size | Quality | Notes |
|-------------|---------|-------|
| **sdxl_sword_32** | **Poor** | The SDXL sword sheet downscaled to 32x32 is a mess. With ~12 swords crammed into a 32x32 space, individual weapons become indistinguishable smudges of brown and gray. You would need to extract individual swords BEFORE downscaling. |
| **sdxl_char_64** | **Poor** | The SDXL character was already small in its source image (occupying maybe 20% of the frame). At 64x64, the knight is about 12x20 pixels against a large gray background with visible horizontal banding artifacts. Not usable. |
| **sdxl_char_128** | **Fair** | At 128x128, the SDXL character is visible but still small within the frame (maybe 30x50 pixels of actual character). The gray background with horizontal line artifacts persists. The character itself looks decent but needs significant cropping and background cleanup to be game-ready. |

### Key Findings -- Downscaling

- **FLUX dramatically outperforms SDXL for downscale quality.** FLUX generates subjects that fill the frame and are designed at a detail level appropriate for game sprite sizes. SDXL often generates subjects that are small within a larger composition, leaving wasted canvas.
- **Nearest-neighbor is the correct resampling method for pixel art.** The 8x upscaled previews confirm that nearest-neighbor preserves the crisp pixel edges, while Lanczos would introduce anti-aliasing blur.
- **64x64 is the sweet spot.** For character sprites generated by FLUX, 64x64 retains almost all meaningful detail while being a practical game resolution. 32x32 works for simple items (swords, potions) but loses character detail. 128x128 is essentially lossless.
- **SDXL output needs pre-processing before downscaling.** You must crop to the subject bounding box, remove the background, and possibly adjust framing before downscaling makes sense.

---

## 4. Practical Recommendations for a Game Development Pipeline

### What Works Today

1. **FLUX for single-character generation**: FLUX reliably produces single, centered, well-framed characters that fill the canvas. This is the model to use for character sprites.
2. **rembg for background removal**: Fast (~1.5s/image) and generally effective for pixel art. Budget a quick manual pass to clean up foot shadows.
3. **FLUX at 64x64 target**: Generate at high resolution, remove background, crop to bounding box, then nearest-neighbor downscale to 64x64. This pipeline produces clean, game-ready sprites.
4. **FLUX multi-pose for reference art**: While not pixel-perfect consistent, FLUX multi-pose output is good enough to use as concept art / reference for manual sprite work.

### What Does Not Work

1. **SDXL for single-character poses**: SDXL overwhelmingly generates sprite sheets and tilesets when asked for pixel art characters. It cannot be controlled to produce a single character in a specific pose without significant prompt engineering or ControlNet.
2. **Seed variation for character consistency**: Different seeds produce completely different character interpretations. This is not a viable strategy for generating a consistent character across multiple frames.
3. **Raw multi-pose output as animation frames**: Even FLUX's best multi-pose results have too much inter-frame drift to use as raw animation frames. Helmet details change, accessories appear/disappear, proportions shift slightly.
4. **SDXL downscaling without pre-processing**: The small-subject-on-large-canvas problem makes raw SDXL output unsuitable for direct downscaling.

### Recommended Pipeline for a Game Jam / Indie Project

```
1. Generate base character with FLUX (front-facing, centered)
2. Run rembg to remove background
3. Crop to bounding box with small padding
4. Nearest-neighbor downscale to target resolution (64x64 recommended)
5. Manual touch-up: clean shadow remnants, adjust palette if needed

For multiple poses:
6. Generate each pose separately with FLUX using the same detailed prompt
7. Repeat steps 2-4 for each pose
8. Manual harmonization pass: unify color palette, match proportions,
   ensure consistent pixel density across all frames
```

### Areas for Further Investigation

- **ControlNet / IP-Adapter for pose consistency**: These tools could dramatically improve multi-pose consistency by conditioning on the base character's appearance.
- **img2img for pose variants**: Generate the front pose, then use img2img with pose-specific prompts to create variants that inherit more visual DNA from the base.
- **LoRA fine-tuning on a single character**: For a game with a specific protagonist, fine-tuning a LoRA on a handful of manually-created reference sprites could solve the consistency problem entirely.
- **Sprite sheet slicing automation**: SDXL's tendency to generate sprite sheets could be turned into a feature if paired with reliable automatic slicing/extraction tools.

---

## Summary Scores

| Test | Score (1-5) | Game-Readiness |
|------|-------------|----------------|
| BG Removal (rembg) -- FLUX sources | 4/5 | Usable with minor cleanup |
| BG Removal (rembg) -- SDXL sources | 3/5 | Needs cropping + cleanup |
| BG Removal (rembg) -- PixArt sources | 4/5 | Clean extraction on detailed subjects |
| Seed Consistency (SDXL) | 1/5 | Not usable for character consistency |
| Multi-Pose (SDXL) | 1/5 | Generates sheets, not posed characters |
| Multi-Pose (FLUX) | 3/5 | Promising but needs manual harmonization |
| Downscale (FLUX sources) | 4/5 | Clean results at 64x64 and above |
| Downscale (SDXL sources) | 2/5 | Requires pre-processing to be usable |

**Bottom line**: FLUX is the clear winner for a practical game art pipeline. It generates well-framed, appropriately-detailed pixel art characters that survive background removal and downscaling with minimal post-processing. SDXL has its strengths (fast generation, good color palettes) but its inability to produce single posed characters makes it impractical for sprite work without heavy manual intervention. The biggest remaining gap in the pipeline is multi-pose/animation consistency -- this is where ControlNet, IP-Adapter, or LoRA fine-tuning would provide the most value.
