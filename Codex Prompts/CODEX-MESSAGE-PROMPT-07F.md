# Codex Message for PROMPT-07F (Compositor Pipeline Replacement)

## What to paste in the Codex chat:

---

**CRITICAL: Preserve the current design/UI/UX exactly as it is.** Only modify `src/cover_compositor.py` as specified in PROMPT-07F.

Read `Codex Prompts/PROMPT-07F-PNG-TEMPLATE-COMPOSITOR.md` in the repo.

**PREREQUISITE:** PROMPT-07E must be complete. `config/templates/` must contain 99 PNG template files.

**GOAL:** Replace the medallion branch of `composite_single()` in `src/cover_compositor.py` with the three-layer PNG template pipeline.

**THE NEW PIPELINE (replaces the `else` branch at line 715):**

1. Look up the pre-processed PNG template for this cover (`_find_template_for_cover()`)
2. If no template found → log warning, fall back to old pipeline
3. Sample background color from cover (reuse existing `_sample_cover_background()`)
4. Create solid canvas with sampled background color
5. Prepare art: `_simple_center_crop()` (NOT `_smart_square_crop`), resize to `TEMPLATE_PUNCH_RADIUS * 2 + 20`
6. Paste art centered at (2864, 1620) on a transparent layer
7. Composite: canvas + art_layer + template → `Image.alpha_composite()` x2
8. Convert to RGB for JPEG save

**FOUR CHANGES TO `src/cover_compositor.py`:**

1. **Add constant:** `TEMPLATE_PUNCH_RADIUS = 465` near other constants (line ~30)
2. **Add function:** `_find_template_for_cover(cover_path)` → looks up `config/templates/{stem}_template.png`, returns Path or None
3. **Add function:** `_simple_center_crop(image)` → center crop to square, NO foreground detection
4. **Replace the `else` branch** (lines 715-766) in `composite_single()` with the 3-layer pipeline. Extract the OLD else-branch into `_legacy_medallion_composite()` for fallback.

**DO NOT TOUCH:**
- Rectangle branch (lines 679-696) — keep as-is
- Custom mask branch (lines 697-714) — keep as-is
- All validation logic — keep as-is
- Do NOT delete `_smart_square_crop`, `_load_global_compositing_mask`, `_combine_masks`, `_build_cover_overlay_with_punch`, or `_build_circle_feather_mask` — they may be used by other branches. Only remove their calls from the medallion path.

**HOW TO VERIFY:**

1. Deploy and check Railway logs for `"Using PNG template: cover_XXX_template.png"`
2. Generate cover for Book #1 — art should FILL the medallion, be CENTERED, with ZERO original cover art visible
3. Generate covers for Books #1, #9, #25 — all should have IDENTICAL circle size, centering, and edge ratios
4. Test a rectangle-path cover still works (regression check)
5. Compare output frame with source cover JPG at 100% zoom — frame should be pixel-identical

```bash
git add -A && git commit -m "feat: PNG template compositor pipeline (PROMPT-07F)" && git push
```

---
