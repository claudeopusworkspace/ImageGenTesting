# PixelLab MCP Server - Detailed Research

**Date:** 2026-03-17
**Repository:** https://github.com/pixellab-code/pixellab-mcp
**Latest Release:** v1.1.0 (June 17, 2025)
**License:** Proprietary (Copyright 2025 PixelLab)

---

## 1. Overview

PixelLab MCP is a Model Context Protocol server that enables AI coding assistants to generate pixel art assets directly within development environments. It is marketed as a "Vibe Coding AI Toolkit" for game developers, allowing you to generate characters, animations, tilesets, and map objects through natural language prompts while coding.

The MCP server acts as a bridge between your AI assistant (Claude Code, Cursor, VS Code Copilot, etc.) and PixelLab's cloud-based pixel art generation API. All generation happens server-side on PixelLab's infrastructure.

---

## 2. Authentication & Account Requirements

**Yes, a PixelLab account is required.** Here is how it works:

- Sign up at https://pixellab.ai (free, no credit card required for initial access)
- Obtain an API token from https://pixellab.ai/account
- The token is passed as a Bearer token in the MCP configuration
- The API uses a **credit-based billing system** -- you pay per generation in USD
- A `/balance` endpoint lets you check remaining credits

**Authentication flow:**
```
Authorization: Bearer YOUR_API_TOKEN
```

There is no local/self-hosted option. All generation calls go to `api.pixellab.ai`.

---

## 3. MCP Server Setup

### For Claude Code (CLI):
```bash
claude mcp add pixellab https://api.pixellab.ai/mcp -t http -H "Authorization: Bearer YOUR_API_TOKEN"
```

### For any MCP-compatible client (manual JSON config):
```json
{
  "mcpServers": {
    "pixellab": {
      "url": "https://api.pixellab.ai/mcp",
      "transport": "http",
      "headers": {
        "Authorization": "Bearer YOUR_API_TOKEN"
      }
    }
  }
}
```

### Supported Clients (15+):
- **Featured:** VS Code (v1.102+), Cursor, Claude Code, Gemini CLI, Zed, Cline
- **Additional:** Claude Desktop, Windsurf, Continue, BoltAI, LM Studio, Perplexity Desktop, Kiro, Junie, Warp, and any STDIO-compatible MCP client

### Interactive Setup:
PixelLab provides a guided setup at https://www.pixellab.ai/vibe-coding (redirects to /mcp)

---

## 4. MCP Tools Exposed

The MCP server exposes tools via a **non-blocking async pattern**: creation tools return job IDs immediately, and you poll with `get_*` tools to check completion (typically 2-5 minutes).

### 4.1 Character Tools

| Tool | Description |
|------|-------------|
| `create_character` | Generate a pixel art character with 4 or 8 directional views |
| `get_character` | Retrieve character data, rotations, animations, download link |
| `animate_character` | Add animations (walk, run, idle, etc.) to an existing character |
| `list_characters` | List all created characters (paginated) |
| `delete_character` | Permanently delete a character and associated data |

**`create_character` parameters:**
- `description` (string) - Text description of the character
- `name` (string, optional)
- `body_type` - "humanoid" or "quadruped"
- `template` - Required for quadrupeds: bear, cat, dog, horse, lion
- `n_directions` - 4 (cardinal) or 8 (full rotation)
- `size` (int, default 48) - Canvas size in pixels (character is ~60% of height)
- `proportions` - Presets: default, chibi, cartoon, stylized, realistic_male, realistic_female, heroic
- `outline` - "single color black outline", "single color outline", "selective outline", "lineless"
- `shading` - "flat shading", "basic shading", "medium shading", "detailed shading", "highly detailed shading"
- `detail` - "low detail", "medium detail", "highly detailed"
- `view` - "side", "low top-down", "high top-down"
- `ai_freedom` (float, default 750)

**`animate_character` parameters:**
- `character_id` (string) - ID from create_character
- `template_animation_id` - Animation type (e.g., "walking")
- `action_description` - Optional customization text
- `animation_name` (optional)
- `directions` (optional)
- `confirm_cost` (bool, default false)

### 4.2 Top-Down Tileset Tools (Wang System)

| Tool | Description |
|------|-------------|
| `create_topdown_tileset` | Generate a Wang tileset (16 tiles) for seamless terrain transitions |
| `get_topdown_tileset` | Retrieve tileset data and generation status |
| `list_topdown_tilesets` | List all created tilesets (paginated) |
| `delete_topdown_tileset` | Delete a tileset |

**`create_topdown_tileset` parameters:**
- `lower_description` - Bottom terrain (e.g., "ocean water")
- `upper_description` - Top terrain (e.g., "sandy beach")
- `transition_size` (float, 0.0-0.5) - 0=sharp edge, 0.25=medium blend, 0.5=wide
- `transition_description` (optional)
- `tile_size` (dict, default {width: 16, height: 16})
- `view` - "high top-down" (RTS) or "low top-down" (RPG)
- `lower_base_tile_id` / `upper_base_tile_id` - Chain from previous tilesets for visual continuity
- `tileset_adherence` (float, default 100.0)
- `text_guidance_scale` (float, 1.0-20.0, default 8.0)
- Standard outline/shading/detail parameters

**Chaining example:**
```
t1 = create_topdown_tileset("ocean water", "sandy beach")
t2 = create_topdown_tileset("sandy beach", "green grass", lower_base_tile_id=t1.beach_base_id)
```

### 4.3 Sidescroller Tileset Tools

| Tool | Description |
|------|-------------|
| `create_sidescroller_tileset` | Generate platform tilesets for 2D platformers (16 tiles, transparent BG) |
| `get_sidescroller_tileset` | Retrieve with optional example map preview |
| `list_sidescroller_tilesets` | List all (paginated) |
| `delete_sidescroller_tileset` | Delete |

**Key parameters:**
- `lower_description` - Platform material (stone, wood, metal, ice)
- `transition_description` - Top decoration (grass, snow, moss, rust)
- `transition_size` (0.0-0.5) - 0=no top layer, 0.25=light, 0.5=heavy
- `tile_size`, outline, shading, detail, `base_tile_id` for chaining

### 4.4 Isometric Tile Tools

| Tool | Description |
|------|-------------|
| `create_isometric_tile` | Create individual isometric tiles |
| `get_isometric_tile` | Retrieve tile data or processing status |
| `list_isometric_tiles` | List all (paginated) |
| `delete_isometric_tile` | Delete |

**Key parameters:**
- `description` - What the tile looks like
- `size` (int, default 32) - 32px recommended; sizes above 24px produce better quality
- `tile_shape` - "thin" (~10% height), "thick" (~25%), "block" (~50%)
- `outline` - Default "lineless" for modern look
- `seed` - Use same seed for consistent style across tiles

### 4.5 Map Object Tools

| Tool | Description |
|------|-------------|
| `create_map_object` | Create pixel art objects with transparent backgrounds for game maps |
| `get_map_object` | Get object info and status |

**Key parameters:**
- `description`, `width`, `height`, `view`
- `background_image` - For style matching
- `inpainting` (optional)
- Note: Auto-deletes after 8 hours

### 4.6 Tiles Pro Tools

| Tool | Description |
|------|-------------|
| `create_tiles_pro` | Advanced tile generation supporting hex, isometric, octagon, square |
| `get_tiles_pro` | Retrieve status/data |
| `list_tiles_pro` | List all (paginated) |
| `delete_tiles_pro` | Delete |

**Key parameters:**
- `tile_type` - isometric, hex, hex_pointy, octagon, square_topdown
- `tile_size`, `tile_height`, `n_tiles`
- `style_images`, `style_options`

---

## 5. Full API Capabilities (Beyond MCP)

The MCP server exposes a curated subset of the full PixelLab API. The complete API (v1 + v2) offers additional endpoints not directly available through MCP tools:

### Direct API Endpoints (v1)

| Endpoint | Description | Max Size |
|----------|-------------|----------|
| `POST /generate-image-pixflux` | Text-to-pixel-art generation | 400x400px |
| `POST /generate-image-bitforge` | Style-referenced generation | 200x200px |
| `POST /animate-with-skeleton` | Skeleton-based animation (4 frames) | 256x256px |
| `POST /animate-with-text` | Text-prompted animation (4 frames) | 64x64px |
| `POST /rotate` | Rotate characters/objects | 128x128px |
| `POST /inpaint` | Edit existing pixel art with masks | 200x200px |
| `POST /estimate-skeleton` | Extract skeleton keypoints from images | 256x256px |
| `GET /balance` | Check account balance | N/A |

### Additional v2 Endpoints (not all exposed via MCP)

| Endpoint | Description |
|----------|-------------|
| `POST /generate-image-v2` | Enhanced generation (up to 792x688px) |
| `POST /generate-with-style-v2` | Style-matched generation (up to 512x512px) |
| `POST /generate-ui-v2` | UI element generation (buttons, health bars, menus) |
| `POST /edit-images-v2` | Multi-image editing via text or reference |
| `POST /edit-animation-v2` | Modify animation frames (2-16 frames) |
| `POST /interpolation-v2` | Generate transitional frames between keyframes |
| `POST /transfer-outfit-v2` | Transfer outfit/appearance across frames |
| `POST /animate-with-text-v2` | Pro animation (32-256px, variable dimensions) |
| `POST /image-to-pixelart` | Convert regular images to pixel art style |
| `POST /resize` | Intelligent pixel art scaling |
| `POST /inpaint-v3` | Pro inpainting |
| `POST /generate-8-rotations-v2` | Generate all 8 rotational views at once |
| `POST /create-object-with-4-directions` | 4-direction object rotations |
| `POST /create-object-with-8-directions` | 8-direction object rotations |

### Style/Aesthetic Parameters Available Across Most Endpoints:
- **Outline:** single color black outline, single color outline, selective outline, lineless
- **Shading:** flat, basic, medium, detailed, highly detailed
- **Detail:** low, medium, highly detailed
- **View:** side, low top-down, high top-down
- **Direction:** 8 compass directions (N, NE, E, SE, S, SW, W, NW)
- **Projection:** isometric, oblique
- **No background:** transparent background toggle
- **Color palette:** force colors from a reference image
- **Init image:** start from an existing image with controllable strength (1-999)
- **Seed:** for reproducible results

---

## 6. Pricing

PixelLab uses a **pay-per-generation credit system** denominated in USD. There is a free tier with no credit card required. All prices are estimates that vary based on GPU processing time.

### Per-Generation Costs (v1 API):

| Operation | 32x32 | 64x64 | 128x128 | 200x200 | 320x320 | 400x400 |
|-----------|-------|-------|---------|---------|---------|---------|
| Generate (Pixflux) | - | $0.00793 | $0.00793 | - | $0.0101 | $0.0132 |
| Generate (Pixflux, transparent) | - | $0.0084 | $0.00848 | - | - | - |
| Generate (Bitforge) | $0.0071 | $0.00716 | $0.00797 | $0.01122 | - | - |
| Inpaint | - | - | - | Same as Bitforge | - | - |
| Rotate | - | $0.01057 | $0.01091 | - | - | - |
| Animate (Skeleton) | $0.0136 | $0.01433 | $0.01572 | - | - | - |
| Estimate Skeleton | $0.00511 | $0.00513 | - | - | - | $0.00516 (256px) |

**Key takeaway:** Most generations cost roughly **$0.007 - $0.016 per call** (less than 2 cents). A character with 8 directions would cost multiple generation calls. Animations are slightly more expensive than static images.

### Subscription Plans:
The website mentions subscription plans with "generations" allotments vs. credit-based billing, but specific tier names and monthly costs are not publicly documented on any page I could access. The v2 API response format includes both `remaining_credits` and `remaining_generations`, suggesting a dual system where subscriptions give you bundled generations and credits can be purchased separately.

### Free Tier:
- Sign up with no credit card required
- Some initial credits/generations are provided (exact amount not publicly documented)
- HTTP 402 error returned when credits are exhausted

---

## 7. Rate Limits

Rate limits are confirmed but exact thresholds are not publicly documented:
- **HTTP 429:** "Too many requests" - client-side rate limiting
- **HTTP 529:** "Rate limit exceeded" - server-side rate limiting
- The async/non-blocking design of the MCP tools (job queue with polling) suggests the system is designed for moderate throughput, not rapid-fire bulk generation

---

## 8. Developer Experience with Claude Code

### Setup Experience:
Setup with Claude Code is a **single command:**
```bash
claude mcp add pixellab https://api.pixellab.ai/mcp -t http -H "Authorization: Bearer YOUR_TOKEN"
```

After this, Claude Code automatically discovers all available tools via the MCP protocol.

### Workflow:
1. You describe what you want in natural language: "Create a knight character with 8 directions"
2. Claude Code calls `create_character` via MCP, gets back a job ID
3. Claude Code polls `get_character` until the job completes (2-5 min)
4. The result includes download URLs and base64 image data
5. Claude Code can save the assets to your project and integrate them into code

### Framework Integration:
PixelLab provides MCP resource documentation for integrating generated assets with:
- **Godot** (Wang tilesets, sidescroller tilesets, isometric tiles) - highlighted as especially effective since Claude can run Godot headless
- **Unity** (isometric tilemaps, 2D)
- **Python/Pygame**
- Also works with: Unreal Engine, GameMaker Studio, Raylib, MonoGame, Defold, Love2D

### What Works Well:
- Natural language asset generation integrated directly into the coding workflow
- Chaining tilesets together for visual consistency (passing base_tile_id between calls)
- Style matching across multiple sprites using reference images
- The non-blocking async pattern means you can continue coding while assets generate

### Limitations:
- Generation takes 2-5 minutes per asset (not instant)
- Map objects auto-delete after 8 hours
- Maximum image sizes are relatively small (400x400 for Pixflux, 200x200 for Bitforge)
- The MCP exposes a curated subset of the full API -- some v2 endpoints are not available through MCP
- Costs accumulate with complex characters (8 directions + multiple animations = many API calls)

---

## 9. Python Client Library

For direct API access outside of MCP:

```bash
pip install pixellab
```

```python
import pixellab

client = pixellab.Client.from_env_file(".env.development.secrets")

response = client.generate_image_pixflux(
    description="cute dragon",
    image_size={"width": 64, "height": 64},
)

response.image.pil_image()
```

Repository: https://github.com/pixellab-code/pixellab-python

---

## 10. Support & Community

- **Discord:** https://discord.gg/pBeyTBF8T7
- **Email:** support@pixellab.ai
- **GitHub Issues:** https://github.com/pixellab-code/pixellab-mcp/issues
- **API v1 Docs:** https://api.pixellab.ai/v1/docs
- **API v2 Docs:** https://api.pixellab.ai/v2/docs
- **MCP Tool Docs:** https://api.pixellab.ai/mcp/docs

---

## 11. Summary Assessment

**What it is:** A cloud-based pixel art generation service accessible via MCP protocol, enabling AI coding assistants to generate game-ready sprite sheets, animations, and tilesets through natural language.

**Best for:** Indie game developers using AI coding assistants who need pixel art assets generated on-the-fly during development. Particularly strong for top-down RPGs, platformers, and isometric games.

**Cost reality:** At ~$0.01 per generation, a full character with 8 directions + walk/run/idle animations might cost $0.15-0.50 depending on complexity. For a small game with 10-20 characters plus tilesets, you might spend $5-20 total on generation.

**Key differentiator:** The MCP integration is the main selling point -- no other pixel art generator offers this level of integration with AI coding assistants. The ability to chain tilesets and maintain visual consistency across assets is also notable.

**Limitations to be aware of:** Small maximum image sizes, 2-5 minute generation times, no offline/self-hosted option, limited to pixel art style only, and the MCP tools are a subset of the full API capabilities.
