# ImageGenTesting

## Purpose
Research and evaluate open-source image generation models for game development use cases.
Focus areas: consistent game art styles, sprite generation, sprite sheets, clean outputs for engine integration.

## Structure
- `outputs/` - Generated images organized by model and test
- `models/` - Downloaded model files (gitignored)
- `scripts/` - Generation and evaluation scripts
- `results/` - Test result summaries and comparisons

## Environment
- Python venv at `.venv/`
- CUDA 12.8 toolkit, RTX 5090 (32GB VRAM)
- Primary framework: diffusers (CLI-oriented)

## Conventions
- Each model test gets its own output subdirectory
- Use fresh sub-agent for unbiased image quality review
- Document findings in results/
