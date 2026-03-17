"""Standard test prompts for game art evaluation across all models."""

# Each prompt targets a different common game art use case
GAME_ART_PROMPTS = {
    "pixel_sword": {
        "prompt": "pixel art sword icon, 32x32 sprite, transparent background, fantasy RPG game item, clean pixel art, no anti-aliasing",
        "negative": "blurry, photorealistic, 3d render, smooth gradients, noisy",
        "use_case": "Item icons / inventory sprites",
    },
    "character_front": {
        "prompt": "pixel art character sprite, front-facing idle pose, fantasy warrior with sword and shield, 64x64 sprite, game asset, clean lines, transparent background",
        "negative": "blurry, photorealistic, multiple characters, text, watermark",
        "use_case": "Character sprites",
    },
    "tileset_topdown": {
        "prompt": "top-down RPG tileset, grass tiles, dirt path, water edge, stone floor, 16x16 tile grid, pixel art, seamless, game asset",
        "negative": "3d, photorealistic, perspective view, blurry",
        "use_case": "Tileset generation",
    },
    "platformer_character": {
        "prompt": "hand-drawn cartoon character, side view, platformer game style, colorful adventurer character, clean cel-shaded art, white background, game asset",
        "negative": "photorealistic, blurry, dark, complex background",
        "use_case": "Hand-drawn platformer art",
    },
    "isometric_building": {
        "prompt": "isometric game building, medieval fantasy tavern, pixel art style, clean edges, white background, game asset, detailed",
        "negative": "photorealistic, blurry, flat 2d side view",
        "use_case": "Isometric game assets",
    },
    "ui_button": {
        "prompt": "game UI button, ornate fantasy style, golden border, rectangular shape, clean vector art, transparent background, game interface element",
        "negative": "photorealistic, blurry, text, 3d render",
        "use_case": "UI elements",
    },
    "enemy_creature": {
        "prompt": "pixel art monster sprite, slime creature, green, front-facing, idle animation frame, 48x48, game enemy, transparent background, retro game style",
        "negative": "photorealistic, blurry, multiple creatures, complex background",
        "use_case": "Enemy sprites",
    },
    "environment_bg": {
        "prompt": "2D side-scrolling game background, fantasy forest scene, layered parallax style, vibrant colors, hand-painted digital art, game environment",
        "negative": "photorealistic, blurry, dark, noisy",
        "use_case": "Environment backgrounds",
    },
}
