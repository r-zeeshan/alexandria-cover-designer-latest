# Codex Message for PROMPT-07E (Batch PNG Templates)

## What to paste in the Codex chat:

---

**CRITICAL: Preserve the current design/UI/UX exactly as it is.** Only create the specific files listed in PROMPT-07E.

Read `Codex Prompts/PROMPT-07E-BATCH-PNG-TEMPLATES.md` in the repo.

**GOAL:** Create `src/create_png_templates.py` — a standalone script that converts all 99 source cover JPGs into PNG templates with transparent medallion centers.

**WHAT THIS SCRIPT DOES:**

For each cover JPG in `config/covers/`:
1. Open the JPG, convert to RGBA
2. Create a white (opaque) grayscale mask at the cover's dimensions
3. Draw a filled black circle at center (2864, 1620) with radius 465px — using 4x supersampling for anti-aliased edges
4. Apply the mask as the alpha channel
5. Save as `config/templates/{stem}_template.png`

**KEY CONSTANTS:**
- `TEMPLATE_PUNCH_RADIUS = 465`
- `CENTER_X = 2864`, `CENTER_Y = 1620`
- `SUPERSAMPLE_FACTOR = 4`
- Output directory: `config/templates/`

**REQUIREMENTS:**
- Standalone module: `python -m src.create_png_templates`
- CLI args: `--punch-radius`, `--source-dir`, `--force`
- Idempotent: skip existing templates unless `--force`
- Read per-cover geometry from `config/cover_regions.json` (one cover differs by 2px)
- Log results: created/skipped/failed counts
- Uses only PIL/Pillow (already in requirements)
- Creates `config/templates/` directory if it doesn't exist

**CREATES:** `src/create_png_templates.py` + `config/templates/` directory
**DOES NOT MODIFY:** Any existing file

**HOW TO VERIFY:**
1. Run: `python -m src.create_png_templates`
2. Check: `ls config/templates/*.png | wc -l` → should be 99
3. Open any template PNG — should show full cover with clean transparent circle at medallion center
4. Zoom to circle edge at 100% — should be smooth, no jagged pixels

```bash
git add -A && git commit -m "feat: batch PNG template generator (PROMPT-07E)" && git push
```

---
