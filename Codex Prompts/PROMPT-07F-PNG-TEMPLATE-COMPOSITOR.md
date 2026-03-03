# PROMPT-07F — Compositor Pipeline Replacement: PNG Template Three-Layer Composite

**Priority:** CRITICAL — This is Part 2 of the two-part architectural fix. PROMPT-07E must be completed first (it creates the PNG templates this prompt consumes).

**Branch:** `master`

**Prerequisite:** PROMPT-07E has been deployed and `config/templates/` contains 99 PNG template files.

---

## Context

The compositor has three persistent bugs caused by two independent masking systems fighting each other at runtime. PROMPT-07E created pre-processed PNG templates — copies of each cover with transparent medallion centers. This prompt replaces the medallion compositing pipeline to use those templates.

**The new pipeline is three layers:**

| Layer | Content | Z-Order |
|-------|---------|---------|
| Layer 1 (bottom) | Solid color canvas (navy/dark sampled from cover) | Lowest |
| Layer 2 (middle) | AI-generated artwork, center-cropped, scaled to fill medallion | Middle |
| Layer 3 (top) | PNG template of original cover with transparent medallion center | Highest |

Because the frame is ALWAYS the topmost layer, art CANNOT bleed through. This eliminates all three bugs structurally.

---

## DESIGN PRESERVATION — DO NOT CHANGE

Only modify `src/cover_compositor.py` as specified below. Do NOT touch:

- `index.html`, sidebar, navigation, color scheme, page layouts
- `src/static/js/compositor.js` (frontend — will be updated separately)
- `config/compositing_mask.png` (kept for backward compatibility)
- `config/cover_regions.json` (read-only reference)
- Any file not explicitly listed in this prompt

---

## CRITICAL: What to Keep UNCHANGED in `src/cover_compositor.py`

- **Rectangle branch** (lines 679-696) — Keep as-is
- **Custom mask branch** (lines 697-714) — Keep as-is
- **All validation logic** (`validate_composite_output`, etc.) — Keep as-is
- **All functions not in the medallion else-branch** — Keep as-is
- **Do NOT delete** `_load_global_compositing_mask`, `_combine_masks`, `_build_cover_overlay_with_punch`, `_smart_square_crop`, `_build_circle_feather_mask` — They may still be used by the rectangle and custom_mask branches, or by other callers. Only remove their invocation from the medallion compositing path.

---

## Change 1: Add `TEMPLATE_PUNCH_RADIUS` Constant

At the top of `src/cover_compositor.py`, near the existing constants (around line 30-36), add:

```python
TEMPLATE_PUNCH_RADIUS = 465  # Must match create_png_templates.py
```

---

## Change 2: Add `_find_template_for_cover()` Function

Add this new function to `src/cover_compositor.py`. Place it near the other helper functions (around line 490-500, before `_smart_square_crop`):

```python
def _find_template_for_cover(cover_path: Path) -> Path | None:
    """Find the PNG template matching a cover source file.

    Looks in config/templates/ for a file matching the cover's filename
    pattern. Returns None if no template exists (triggers fallback to
    old pipeline).
    """
    stem = cover_path.stem  # e.g., 'cover_001' or 'book_042'
    template_dir = config.CONFIG_DIR / "templates"
    # Try exact stem match
    candidate = template_dir / f"{stem}_template.png"
    if candidate.exists():
        return candidate
    # Try matching by number extraction
    import re
    nums = re.findall(r'\d+', stem)
    if nums:
        for f in template_dir.glob("*_template.png"):
            if nums[-1] in re.findall(r'\d+', f.stem):
                return f
    return None
```

**Note:** `config.CONFIG_DIR` should reference however the existing code references the config directory. Check the existing imports and config references at the top of the file and use the same pattern.

---

## Change 3: Add `_simple_center_crop()` Function

Add this new function near `_smart_square_crop()` (around line 499-532). Do NOT delete `_smart_square_crop()` — it may be used by other branches.

```python
def _simple_center_crop(image: Image.Image) -> Image.Image:
    """Center crop to square. No foreground detection."""
    src = image.convert("RGBA")
    w, h = src.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return src.crop((left, top, left + side, top + side))
```

---

## Change 4: Replace the Medallion Branch in `composite_single()`

In `composite_single()` (starts at line 655), there is an if/elif/else chain:

- `if region_obj.get("shape") == "rectangle":` — lines 679-696 — **KEEP AS-IS**
- `elif region_obj.get("custom_mask"):` — lines 697-714 — **KEEP AS-IS**
- `else:` — lines 715-766 — **THIS IS THE MEDALLION BRANCH — REPLACE IT**

Replace the entire `else` block (lines 715-766) with the new three-layer pipeline:

```python
    else:
        # --- NEW MEDALLION COMPOSITING PIPELINE (PNG Template) ---
        # Uses pre-processed PNG templates instead of runtime mask detection.
        # The template has a transparent circle where the medallion opens.
        # Three-layer composite: canvas + art + template (frame on top).

        template_path = _find_template_for_cover(cover_path)
        if template_path is None:
            logger.warning(
                f"No PNG template found for {cover_path.name}. "
                f"Falling back to legacy compositor pipeline."
            )
            # --- FALLBACK: old pipeline (keep for safety) ---
            # Copy the old else-branch code here as fallback.
            # This ensures the compositor doesn't crash if a template
            # is missing. The old code goes here unchanged.
            # (Codex: paste the CURRENT else-branch code here as the fallback)
            raise NotImplementedError(
                f"Legacy fallback not yet wired — template missing for {cover_path.name}"
            )

        logger.info(f"Using PNG template: {template_path.name}")

        # Load the pre-processed PNG template (cover with transparent medallion)
        template = Image.open(template_path).convert("RGBA")

        # Resolve medallion geometry (reuse existing function)
        geometry = _resolve_medallion_geometry(cover, cover_path, region_obj)
        center_x = int(geometry["center_x"])
        center_y = int(geometry["center_y"])
        outer_radius = int(geometry["outer_radius"])
        cover_w, cover_h = cover.size

        # 1. Sample background color from cover (reuse existing function)
        fill_rgb = _sample_cover_background(
            cover=cover,
            center_x=center_x,
            center_y=center_y,
            outer_radius=outer_radius,
        )

        # 2. Create solid canvas with sampled background color
        canvas = Image.new("RGBA", (cover_w, cover_h), (*fill_rgb, 255))

        # 3. Prepare art: SIMPLE CENTER CROP (not smart crop)
        art_diameter = TEMPLATE_PUNCH_RADIUS * 2 + 20  # 10px bleed each side
        art = _simple_center_crop(illustration)
        art = art.resize((art_diameter, art_diameter), Image.LANCZOS)

        # 4. Paste art centered on medallion
        art_layer = Image.new("RGBA", (cover_w, cover_h), (0, 0, 0, 0))
        paste_x = center_x - art_diameter // 2
        paste_y = center_y - art_diameter // 2
        art_layer.paste(art, (paste_x, paste_y))

        # 5. Composite: canvas + art + template (frame always on top)
        result = Image.alpha_composite(canvas, art_layer)
        result = Image.alpha_composite(result, template)
        composited_rgb = result.convert("RGB")
```

### Important Implementation Notes:

1. **The `illustration` variable** — This is the AI-generated artwork, already loaded earlier in `composite_single()`. Use whatever variable name the existing code uses for the loaded illustration image.

2. **The `cover` variable** — This is the source cover JPG, already loaded earlier. Use the existing variable name.

3. **The `cover_path` variable** — Path to the source cover, already available in the function signature.

4. **`_resolve_medallion_geometry()`** — This function already exists in the codebase. Reuse it to get center_x, center_y, outer_radius.

5. **`_sample_cover_background()`** — This function already exists. Reuse it to sample the background fill color.

6. **`composited_rgb`** — This is what the rest of `composite_single()` expects. Make sure the variable name matches whatever the subsequent code (validation, saving) uses. Check the existing code after line 766 to see what variable name the JPEG save operation expects.

7. **Fallback behavior** — If no template PNG exists for a cover, the compositor must NOT crash. Log a warning and fall back to the old pipeline. The safest approach: move the current else-branch code into a helper function `_legacy_medallion_composite()` and call it from the fallback.

---

## Change 5: Wire Up the Fallback (Defensive Coding)

To implement the fallback properly, extract the CURRENT else-branch (lines 715-766, the code being replaced) into a helper function before replacing it:

```python
def _legacy_medallion_composite(
    cover, illustration, cover_path, region_obj, geometry, ...
) -> Image.Image:
    """Legacy medallion compositing pipeline.

    Kept as fallback for covers that don't have PNG templates.
    This is the original else-branch from composite_single().
    """
    # ... paste the current else-branch code here ...
```

Then in the fallback section of the new else-branch:

```python
        if template_path is None:
            logger.warning(
                f"No PNG template found for {cover_path.name}. "
                f"Falling back to legacy compositor pipeline."
            )
            composited_rgb = _legacy_medallion_composite(
                cover, illustration, cover_path, region_obj, ...
            )
```

This ensures zero-downtime deployment even if some templates are missing.

---

## What Gets Removed from the Medallion Path

In the medallion branch ONLY (not rectangle or custom_mask), the following function calls are no longer needed:

- `_load_global_compositing_mask()` — not called; template IS the mask
- `_combine_masks()` — not needed; template replaces mask combination
- `_build_cover_overlay_with_punch()` — not needed; template replaces it
- `_smart_square_crop()` — replaced by `_simple_center_crop()`
- `_build_circle_feather_mask()` — not needed; no circle masking

**Do NOT delete these functions from the file.** They may still be used by the rectangle and custom_mask branches, or by other callers. Only remove their invocation in the medallion compositing path.

---

## Validation After Deploying

### 1. Template loading check

After deploying, check Railway logs for:
```
Using PNG template: cover_001_template.png
```
You should NOT see "No PNG template found" warnings.

### 2. Bug 1 check — Art fills the medallion

Generate a cover. The AI art should fill the medallion opening edge-to-edge. No visible gap between art edge and frame inner edge.

### 3. Bug 2 check — Art is centered

The center of the art should coincide with (2864, 1620) in the output image. Generate 3 covers — all should have identical centering.

### 4. Bug 3 check — Zero original cover art visible

The frame's ornamental detail (scrollwork, beads, gold borders) should be intact, but there should be NO "ghost" or bleed-through of the original cover's medallion content.

### 5. Frame integrity

Compare the output cover with the source cover JPG side by side at 100% zoom. The frame border area should be pixel-identical. Only the medallion interior should differ.

### 6. Edge quality

The art/frame boundary should be a clean, anti-aliased transition. No hard edges, no halo artifacts, no color banding.

### 7. Regression check

Test at least one cover with the rectangle compositing path and one with custom_mask path (if applicable). Both should still work correctly.

### 8. Multi-cover test

Generate covers for at least 5 different books. Compare: same circle size, same centering, same edge ratios. Only the art content should differ.

---

## File Change Summary

| File | Action | Description |
|------|--------|-------------|
| `src/cover_compositor.py` | **ADD constant** | `TEMPLATE_PUNCH_RADIUS = 465` at top |
| `src/cover_compositor.py` | **ADD function** | `_find_template_for_cover()` — template lookup |
| `src/cover_compositor.py` | **ADD function** | `_simple_center_crop()` — simple center crop |
| `src/cover_compositor.py` | **ADD function** | `_legacy_medallion_composite()` — extracted old code for fallback |
| `src/cover_compositor.py` | **REPLACE else-branch** | Lines 715-766 in `composite_single()` — new 3-layer pipeline |

---

## Commit and Push

```bash
git add -A && git commit -m "feat: PNG template compositor pipeline (PROMPT-07F)

Replaces the medallion compositing branch in composite_single() with
the three-layer PNG template pipeline:
  Layer 1: solid canvas (sampled background color)
  Layer 2: AI art (simple center crop, scaled to fill)
  Layer 3: PNG template (cover with transparent medallion center)

Frame is ALWAYS the topmost layer, structurally eliminating:
  - Bug 1: art too small (no compositing_mask restriction)
  - Bug 2: art off-center (simple center crop, no foreground detection)
  - Bug 3: original art visible (no punch/clip mismatch possible)

- Adds _find_template_for_cover() for template lookup
- Adds _simple_center_crop() replacing _smart_square_crop() in this path
- Extracts old pipeline into _legacy_medallion_composite() as fallback
- Rectangle and custom_mask branches remain UNCHANGED
- TEMPLATE_PUNCH_RADIUS = 465 (matches create_png_templates.py)" && git push
```
