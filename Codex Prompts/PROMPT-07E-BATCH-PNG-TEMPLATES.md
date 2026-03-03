# PROMPT-07E — Batch Preprocessing: Create PNG Templates

**Priority:** CRITICAL — This is Part 1 of a two-part architectural fix for the compositor. It creates the pre-processed PNG templates that PROMPT-07F will consume.

**Branch:** `master`

---

## Context

The compositor in `src/cover_compositor.py` has three persistent bugs that four consecutive fix attempts (07A–07D) failed to resolve. The root cause is architectural: two independent masking systems (geometric circles and `config/compositing_mask.png`) contradict each other at runtime.

The fix replaces runtime mask/detection logic with pre-processed PNG templates. This prompt creates the batch script that generates those templates.

**This prompt creates ONE new file:** `src/create_png_templates.py`
**This prompt creates ONE new directory:** `config/templates/`

---

## DESIGN PRESERVATION — DO NOT CHANGE

Only create the files listed in this prompt. Do NOT touch `index.html`, `src/cover_compositor.py`, sidebar, navigation, color scheme, page layouts, or any existing file.

---

## What This Script Does

For each of the 99 source cover JPGs, this script:

1. Opens the cover JPG and converts to RGBA (adds alpha channel, fully opaque)
2. Creates a grayscale mask (white = opaque, black = transparent)
3. Draws a filled black circle at the medallion center with radius = `TEMPLATE_PUNCH_RADIUS`
4. Anti-aliases the circle edge using 4x supersampling
5. Applies the mask as the alpha channel of the RGBA image
6. Saves as PNG (lossless, preserves alpha) to `config/templates/`

The result: a PNG identical to the source cover, except the medallion center is transparent. When composited as the TOP layer, this provides a perfect frame overlay — art beneath it CANNOT bleed through.

---

## File: `src/create_png_templates.py`

Create this file as a standalone module that can also be imported.

### Constants (top of file)

```python
"""Batch-generate PNG templates with transparent medallion centers.

Usage:
    python -m src.create_png_templates [--punch-radius 465] [--source-dir config/covers] [--force]

Each PNG template is a copy of the source cover JPG with the medallion
center punched out (made transparent). These templates are used by the
compositor as the topmost layer, ensuring the ornamental frame is always
on top of the AI-generated artwork.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

# --- Configuration ---
TEMPLATE_PUNCH_RADIUS = 465       # Radius of the transparent hole in pixels
CENTER_X = 2864                    # Medallion center X coordinate
CENTER_Y = 1620                    # Medallion center Y coordinate
SUPERSAMPLE_FACTOR = 4             # Anti-aliasing quality (4x is sufficient)
TEMPLATE_DIR = Path("config/templates")
SOURCE_DIR = Path("config/covers")  # Where source cover JPGs live
COVER_REGIONS_PATH = Path("config/cover_regions.json")
```

### Algorithm — Per Cover

Implement the following as the core processing function:

```python
def create_template(
    source_path: Path,
    output_path: Path,
    center_x: int = CENTER_X,
    center_y: int = CENTER_Y,
    punch_radius: int = TEMPLATE_PUNCH_RADIUS,
) -> bool:
    """Create a PNG template from a source cover JPG.

    Opens the source JPG, punches a transparent circle at the medallion
    center, and saves as PNG with alpha channel.

    Returns True if template was created, False if skipped or failed.
    """
```

Inside `create_template()`, follow these exact steps:

**Step 1: Open** the JPG and convert to RGBA (adds alpha channel, fully opaque).

```python
cover = Image.open(source_path).convert("RGBA")
width, height = cover.size
```

**Step 2: Create a mask** — a grayscale image same size as the cover, filled with white (255 = opaque).

```python
mask = Image.new("L", (width, height), 255)
```

**Step 3: Draw a filled black circle** on the mask at center (`center_x`, `center_y`) with radius = `punch_radius`. Black = transparent in the final PNG.

Use **4x supersampling** for anti-aliased edges:

```python
# Create mask at 4x resolution for anti-aliasing
SCALE = SUPERSAMPLE_FACTOR
mask_large = Image.new("L", (width * SCALE, height * SCALE), 255)
draw = ImageDraw.Draw(mask_large)
cx, cy, r = center_x * SCALE, center_y * SCALE, punch_radius * SCALE
draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=0)
mask = mask_large.resize((width, height), Image.LANCZOS)  # Downscale = AA
```

**Step 4: Apply the mask** as the alpha channel of the RGBA image.

```python
cover.putalpha(mask)
```

**Step 5: Save** as PNG (lossless, preserves alpha) to `config/templates/`.

```python
output_path.parent.mkdir(parents=True, exist_ok=True)
cover.save(str(output_path), "PNG")
```

### Per-Cover Geometry (Edge Case)

99 of 100 covers share identical geometry (cx=2864, cy=1620, r=500). One cover (ID 9) differs by 2px in center_x. The script should read per-cover geometry from `config/cover_regions.json` if it exists, falling back to the default center (2864, 1620) if not found.

```python
def _load_cover_geometry(cover_path: Path) -> tuple[int, int]:
    """Load per-cover center coordinates from cover_regions.json.

    Falls back to default CENTER_X, CENTER_Y if file not found
    or cover not in the JSON.
    """
    if not COVER_REGIONS_PATH.exists():
        return CENTER_X, CENTER_Y
    try:
        with open(COVER_REGIONS_PATH) as f:
            regions = json.load(f)
        # Try matching by filename stem (e.g., 'cover_001')
        stem = cover_path.stem
        for entry in regions.values() if isinstance(regions, dict) else regions:
            # Match by cover path or ID
            region = entry.get("consensus_region", entry)
            if stem in str(entry.get("cover_path", "")):
                return int(region.get("center_x", CENTER_X)), int(region.get("center_y", CENTER_Y))
    except Exception as e:
        logger.warning(f"Could not load cover geometry: {e}")
    return CENTER_X, CENTER_Y
```

### File Naming Convention

Output files must match the existing cover numbering pattern. If the source is `cover_001.jpg`, the template is `cover_001_template.png`. Use the stem of the source file:

```python
output_name = f"{source_path.stem}_template.png"
output_path = TEMPLATE_DIR / output_name
```

### Batch Processing Function

```python
def process_all_covers(
    source_dir: Path = SOURCE_DIR,
    template_dir: Path = TEMPLATE_DIR,
    punch_radius: int = TEMPLATE_PUNCH_RADIUS,
    force: bool = False,
) -> dict:
    """Process all cover JPGs into PNG templates.

    Args:
        source_dir: Directory containing source cover JPGs.
        template_dir: Output directory for PNG templates.
        punch_radius: Radius of the transparent circle.
        force: If True, regenerate even if template already exists.

    Returns:
        Dict with counts: {'created': N, 'skipped': N, 'failed': N}
    """
```

Requirements for `process_all_covers()`:

- Find all `.jpg` and `.jpeg` files in `source_dir`
- For each cover, check if the template already exists (idempotent) — skip if it does, unless `--force` is passed
- Load per-cover geometry from `cover_regions.json`
- Call `create_template()` for each
- Log processing results: created, skipped (already exists), failed
- Return summary dict

### CLI Entry Point

```python
def main():
    parser = argparse.ArgumentParser(
        description="Generate PNG templates with transparent medallion centers."
    )
    parser.add_argument(
        "--punch-radius", type=int, default=TEMPLATE_PUNCH_RADIUS,
        help=f"Radius of transparent circle (default: {TEMPLATE_PUNCH_RADIUS})"
    )
    parser.add_argument(
        "--source-dir", type=Path, default=SOURCE_DIR,
        help=f"Directory with source cover JPGs (default: {SOURCE_DIR})"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Regenerate templates even if they already exist"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    results = process_all_covers(
        source_dir=args.source_dir,
        punch_radius=args.punch_radius,
        force=args.force,
    )

    logger.info(
        f"Done: {results['created']} created, "
        f"{results['skipped']} skipped, "
        f"{results['failed']} failed"
    )

    if results["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Google Drive Fallback

The source covers may be in the repo at `config/covers/` or may need to be downloaded from Google Drive (folder ID: `1ybFYDJk7Y3VlbsEjRAh1LOfdyVsHM_cS`). The script should:

1. First check if `config/covers/` exists and has JPG files
2. If not, log a warning: `"No covers found in config/covers/. Download source covers from Google Drive folder 1ybFYDJk7Y3VlbsEjRAh1LOfdyVsHM_cS or specify --source-dir"`
3. Do NOT implement Google Drive download in this script — that's handled by existing infrastructure

---

## Directory Structure After Running

```
config/
  covers/            (existing — source cover JPGs)
    cover_001.jpg
    cover_002.jpg
    ...
    cover_099.jpg
  templates/          (NEW — created by this script)
    cover_001_template.png
    cover_002_template.png
    ...
    cover_099_template.png
  cover_regions.json  (existing — read-only reference)
  compositing_mask.png (existing — NOT touched, kept for backward compat)
```

---

## Validation After Running

### 1. Count check

```bash
ls config/templates/*.png | wc -l
# Expected: 99 (one per cover)
```

### 2. Dimensions check

```bash
python3 -c "
from PIL import Image
import glob
for f in sorted(glob.glob('config/templates/*.png'))[:3]:
    img = Image.open(f)
    print(f'{f}: {img.size} mode={img.mode}')
"
# Expected: Each is (3784, 2777) mode=RGBA
```

### 3. Alpha channel check

```bash
python3 -c "
from PIL import Image
import numpy as np
img = Image.open('config/templates/cover_001_template.png')
alpha = np.array(img.split()[-1])
transparent = np.sum(alpha < 128)
opaque = np.sum(alpha > 128)
print(f'Transparent pixels: {transparent:,}')
print(f'Opaque pixels: {opaque:,}')
print(f'Transparent ratio: {transparent / alpha.size:.2%}')
# Transparent should be ~6-8% (the medallion circle area)
"
```

### 4. Visual check

Open any template PNG in an image viewer. You should see the full cover with a clean circular transparent hole at the medallion center. The frame (scrollwork, beads, gold border) should be fully intact. The hole should have smooth, anti-aliased edges.

### 5. Anti-aliasing check

Zoom to 100% at the circle edge. There should be NO visible jagged/staircase pixels. The edge should have a 2-3px gradient from fully opaque to fully transparent.

---

## Commit and Push

```bash
git add -A && git commit -m "feat: batch PNG template generator (PROMPT-07E)

Creates src/create_png_templates.py that converts all 99 source cover
JPGs into PNG templates with transparent medallion centers. These
templates will be used by the compositor (PROMPT-07F) as the topmost
layer, structurally eliminating art bleed-through.

- TEMPLATE_PUNCH_RADIUS = 465 (preserves 95%+ ornamental detail)
- 4x supersampled anti-aliased circle edges
- Per-cover geometry from cover_regions.json
- Idempotent: skips existing templates unless --force
- Output: config/templates/cover_XXX_template.png (x99)" && git push
```
