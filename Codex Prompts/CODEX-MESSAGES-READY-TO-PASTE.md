# Codex Messages — Ready to Paste

> **Instructions**: After each Codex thread completes, start a NEW thread and paste the next message below. Go in order: 2B → 3A → 3B → 4A → 4B → 5.
>
> **1A and 1B are already complete.** 2A should be running (or about to run) with the updated prompt.

---

## Message for PROMPT 2B — Quality Gate

```
Read `Codex Prompts/PROMPT-2B-QUALITY-GATE.md` and `Project state Alexandria Cover designer.md` for full context.

Build `src/quality_gate.py` — the automated quality scoring and filtering system for generated images.

**What exists already (from previous prompts):**
- `src/cover_analyzer.py` (1A) — cover analysis with region detection
- `src/prompt_generator.py` (1B) — prompt engineering with book_prompts.json
- `src/image_generator.py` (2A) — image generation pipeline with multi-model support
- `src/config.py` (2A) — centralized configuration
- `src/prompt_library.py` (2A) — prompt library with style anchors
- `config/book_catalog.json` — all 99 books cataloged
- `config/book_prompts.json` — all prompts generated
- `config/prompt_templates.json` — 5 variant templates
- `config/prompt_library.json` — prompt library with style anchors

**Build this file:**

`src/quality_gate.py` with:

1. **Technical Quality**: Resolution check, aspect ratio, reject blank/solid-color images, noise detection
2. **Color Compatibility**: Check warm tones compatible with navy/gold cover palette
3. **AI Artifact Detection**: Flag common AI artifacts (text-like patterns, distorted features)
4. **Diversity Check**: Ensure variants for each book are sufficiently different from each other
5. **Scoring**: Aggregate score 0-1, configurable threshold (default 0.7 from config.py MIN_QUALITY_SCORE)
6. **Retry Strategy (Tim's decision D6)**: When image fails quality gate, re-generate using SAME model with TWEAKED prompt. Add/adjust style words, modify composition guidance, adjust negative prompt emphasis. Max 3 retries per image. After 3 failures, flag for manual review — do NOT switch to a different model. Log all retries.
7. **Multi-Model Ranking (Tim's decision D20)**: When all models generate for the same prompt, rank results across models. Score all outputs for the same book/prompt across every model. Rank by quality score grouped by model. Generate a "model leaderboard" per book showing which model scored highest.

**Outputs:**
- `data/quality_scores.json` — per-image scores and pass/fail (includes model name)
- `data/quality_report.md` — human-readable summary with model leaderboard
- `data/retry_log.json` — all retried images with original/tweaked prompts
- `data/model_rankings.json` — aggregated quality scores per model

**SCOPE: Build for 20 titles first (Tim's decision D23). Do NOT test with all 99 books.**

**Verification checklist:**
1. `py_compile` passes — PASS/FAIL
2. Score a known-good generated image → score ≥ 0.7 — PASS/FAIL
3. Score a blank/solid-color test image → score < 0.3 — PASS/FAIL
4. Score all images for one book (5 variants) → report generated — PASS/FAIL
5. Diversity check flags 5 identical images as "not diverse" — PASS/FAIL
6. `data/quality_scores.json` is valid JSON with all entries — PASS/FAIL
7. `data/quality_report.md` is readable and accurate — PASS/FAIL

Run every check. Report PASS/FAIL for each.
```

---

## Message for PROMPT 3A — Cover Composition

```
Read `Codex Prompts/PROMPT-3A-COVER-COMPOSITION.md` and `Project state Alexandria Cover designer.md` for full context.

Build `src/cover_compositor.py` — composites generated illustrations into original covers.

**What exists already (from previous prompts):**
- `src/cover_analyzer.py` (1A) — cover analysis with region detection
- `src/prompt_generator.py` (1B) — prompt engineering
- `src/image_generator.py` (2A) — image generation with multi-model support
- `src/config.py` (2A) — centralized configuration
- `src/prompt_library.py` (2A) — prompt library with style anchors
- `src/quality_gate.py` (2B) — quality scoring and filtering
- `config/cover_regions.json` — detected circle regions per cover
- Generated images in `tmp/generated/`
- Original covers in `Input Covers/`

**Build this file:**

`src/cover_compositor.py` with:

1. **Load original cover JPG** (3784×2777, 300 DPI)
2. **Load generated illustration** (1024×1024 PNG)
3. **Resize illustration** to match detected circle diameter from cover_regions.json
4. **Apply circular mask** with feathered edges (default 15px) for smooth blending
5. **Composite** illustration into exact center of ornamental frame
6. **CRITICAL: The gold baroque frame OVERLAPS the edge of the illustration by ~15-20px** — the illustration sits UNDERNEATH the frame edge. This creates a natural seal. Do NOT paste over the frame.
7. **Color-match** illustration to cover's color temperature (optional but recommended)
8. **Save** result as JPG at 3784×2777, 300 DPI

**CRITICAL REQUIREMENTS:**
- Everything OUTSIDE the center circle must be PIXEL-PERFECT identical to the original
- The ornamental gold frame must NOT be affected
- Feathered edge should blend smoothly with frame's inner border
- The illustration should "sit inside" the frame naturally

**Fit Verification Overlay:**
- Function: `generate_fit_overlay(cover_path, region, output_path)` → overlay image
- Semi-transparent red highlight showing exact compositing boundary
- Frame edge overlay showing where ornamental frame meets illustration
- Used by Tim in webapp to visually confirm perfect fit

**Functions to implement:**
- `composite_single(cover_path, illustration_path, region, output_path, feather_px=15) -> Path`
- `composite_all_variants(book_number, input_dir, generated_dir, output_dir, regions) -> list[Path]`
- `batch_composite(input_dir, generated_dir, output_dir, regions_path) -> dict`
- `generate_fit_overlay(cover_path, region, output_path) -> Path`

**SCOPE: Build for 20 titles first (D23). Test with a single book first, then 5 books.**

**Verification checklist:**
1. `py_compile` passes — PASS/FAIL
2. Composite variant 1 of book #2 → output JPG saved — PASS/FAIL
3. Output is 3784×2777 at 300 DPI — PASS/FAIL
4. Compare back-cover pixel (x=200, y=200) between original and composite → identical RGB — PASS/FAIL
5. Compare title text pixel → identical — PASS/FAIL
6. Compare ornament pixel outside circle → identical — PASS/FAIL
7. Center illustration properly fills circular region — PASS/FAIL
8. No visible seam at circle edge — PASS/FAIL
9. Feathered edge blends smoothly with frame border — PASS/FAIL
10. All 5 variants for one book composited successfully — PASS/FAIL
11. Batch composite for 5 test books completes without error — PASS/FAIL
12. Fit verification overlay generates correctly — PASS/FAIL

Run every check. Report PASS/FAIL for each.
```

---

## Message for PROMPT 3B — Format Export

```
Read `Codex Prompts/PROMPT-3B-FORMAT-EXPORT.md` and `Project state Alexandria Cover designer.md` for full context.

Build `src/output_exporter.py` — exports composited covers to .ai, .jpg, and .pdf formats.

**What exists already (from previous prompts):**
- `src/cover_analyzer.py` (1A), `src/prompt_generator.py` (1B)
- `src/image_generator.py` (2A), `src/config.py` (2A), `src/prompt_library.py` (2A)
- `src/quality_gate.py` (2B), `src/cover_compositor.py` (3A)
- Composited JPG covers in output directory

**Build this file:**

`src/output_exporter.py` that exports each composited cover to 3 formats:

1. **JPG Export**: Verify 3784×2777, 300 DPI, RGB, quality 95. Re-save if needed.
2. **PDF Export**: Single-page PDF at print quality. Page size 12.613" × 9.257" at 300 DPI. Embedded image at full resolution, no compression artifacts. Use reportlab.
3. **AI (Adobe Illustrator) Export**:
   - FIRST: Check what format the original .ai files actually are (many are PDFs with .ai extension)
   - If originals are PDF-based: create PDF with Illustrator-compatible metadata, save with .ai extension
   - Document your findings about the original .ai format

**Output Folder Structure:**
```
Output Covers/{folder_name}/
├── Variant-1/
│   ├── {file_base}.ai
│   ├── {file_base}.jpg
│   └── {file_base}.pdf
├── Variant-2/
│   └── ...
└── ...
```

Where `{folder_name}` is the input folder name WITHOUT the " copy" suffix, and `{file_base}` matches the input filename base.

**SCOPE: Build for 20 titles first (D23).**

**Verification checklist:**
1. `py_compile` passes — PASS/FAIL
2. Check original `.ai` file format (is it actually a PDF internally?) — documented — PASS/FAIL
3. Export book #2 variant 1 → 3 files created (.ai, .jpg, .pdf) — PASS/FAIL
4. JPG: 3784×2777, 300 DPI, RGB — PASS/FAIL
5. PDF: opens correctly, single page, full resolution image — PASS/FAIL
6. .AI: valid PDF with AI metadata (or equivalent) — PASS/FAIL
7. Filenames match input pattern — PASS/FAIL
8. Folder name matches (no " copy" suffix) — PASS/FAIL
9. Export all 5 variants for one book → 15 files total — PASS/FAIL
10. Batch export for 5 test books → all files correct — PASS/FAIL

Run every check. Report PASS/FAIL for each.
```

---

## Message for PROMPT 4A — Batch Orchestration

```
Read `Codex Prompts/PROMPT-4A-BATCH-ORCHESTRATION.md` and `Project state Alexandria Cover designer.md` for full context.

Build `src/pipeline.py` and `scripts/run_pipeline.sh` — the master orchestrator that runs the entire pipeline end-to-end.

**What exists already (from previous prompts):**
- `src/cover_analyzer.py` (1A), `src/prompt_generator.py` (1B)
- `src/image_generator.py` (2A), `src/config.py` (2A), `src/prompt_library.py` (2A)
- `src/quality_gate.py` (2B), `src/cover_compositor.py` (3A), `src/output_exporter.py` (3B)

**Build these files:**

`src/pipeline.py` — the master orchestrator with:

1. **Single-Cover Mode (ESSENTIAL — D19)**: This is the PRIMARY workflow. Full end-to-end for one book: analyze → prompt → generate → quality gate → composite → export → review.
   - Model selection per run: `--model openai/gpt-image-1` or `--models flux-2-pro,gpt-image-1`
   - Prompt override: `--prompt-override "custom prompt text here"`
   - Side-by-side output of new variants alongside previous ones
   - CLI: `python -m src.pipeline --book 2 --model openai/gpt-image-1 --variants 3`
   - All-models: `python -m src.pipeline --book 2 --all-models --variants 10`

2. **All-Models Mode (D20)**: `--all-models` fires every configured model simultaneously. N models × M variants per book. Results grouped by model.

3. **Prompt Library Integration (D21)**:
   - `--use-library` selects top-rated prompts from library
   - `--prompt-id my_prompt_id` uses a specific saved prompt
   - `--style-anchors warm_sepia_sketch,dramatic_oil` builds from style anchor components

4. **Incremental processing**: Track completed books, skip on re-run
5. **Progress dashboard**: `[42/99 books complete, 210/495 images]`
6. **Error isolation**: One book failure doesn't abort batch
7. **Summary report**: Successes/failures/quality scores at completion
8. **Selective re-run (D8)**: `--book 2 --variant 3` regenerates only that specific variant
9. **Configurable batch size (D13)**: `--batch-size 500` with review point between batches
10. **Dry run**: `--dry-run` shows what would happen without API calls

**Full CLI:**
`python -m src.pipeline [--books 1-10] [--book 2] [--variants 1-3] [--variant 3] [--batch-size 500] [--dry-run] [--resume] [--all-models] [--use-library] [--prompt-id ID] [--style-anchors LIST] [--prompt-override TEXT] [--model MODEL] [--models LIST]`

Also create `scripts/run_pipeline.sh` as a convenience wrapper.

**IMPORTANT: Build for 20 titles first (D23). Do NOT build or test at 99-book scale.**

**Verification checklist:**
1. `py_compile` passes — PASS/FAIL
2. Dry run mode works (no API calls, shows what would be generated) — PASS/FAIL
3. Process single book (book #2) end-to-end → variants, files — PASS/FAIL
4. Resume after partial run skips completed books — PASS/FAIL
5. Process books 1-5 → variants and files — PASS/FAIL
6. Summary report generated with pass/fail counts — PASS/FAIL
7. Failed book doesn't abort the batch — PASS/FAIL

Run every check. Report PASS/FAIL for each.
```

---

## Message for PROMPT 4B — Google Drive Sync

```
Read `Codex Prompts/PROMPT-4B-GDRIVE-SYNC.md` and `Project state Alexandria Cover designer.md` for full context.

Build `src/gdrive_sync.py` — uploads output covers to Google Drive.

**What exists already (from previous prompts):**
- All src modules (1A through 4A) — the full pipeline
- Output covers generated locally in `Output Covers/`

**Build this file:**

`src/gdrive_sync.py` with:

1. **Authentication**: Google Drive API via OAuth2 or service account. Store credentials securely.
2. **Create subfolder structure** in Drive matching local output:
   ```
   Output Covers/{book_folder}/Variant-{n}/{files}
   ```
3. **Upload** all variant files (.ai, .jpg, .pdf) per book
4. **Resume support**: Skip already-uploaded files
5. **Progress reporting**: Show upload status and any failures

**Target Drive folder**: https://drive.google.com/drive/folders/1Vr184ZsX3k38xpmZkd8g2vwB5y9LYMRC

**Alternative**: If Google API OAuth setup is too complex for the current environment, provide a rclone-based approach with clear setup instructions as a fallback.

**Verification checklist:**
1. `py_compile` passes — PASS/FAIL
2. Authentication works (OAuth flow or service account) — PASS/FAIL
3. Upload 1 test file to the target Drive folder — PASS/FAIL
4. Create subfolder structure for 1 book (5 variants) — PASS/FAIL
5. Resume mode skips existing files — PASS/FAIL
6. Upload progress reported — PASS/FAIL

Run every check. Report PASS/FAIL for each.
```

---

## Message for PROMPT 5 — Visual QA + Review Grid + Catalog

```
Read `Codex Prompts/PROMPT-5-VISUAL-QA.md` and `Project state Alexandria Cover designer.md` for full context.

This is the final prompt. Build the Visual QA webapp pages, review tools, archiver, and catalog PDF generator.

**What exists already (from previous prompts):**
- All src modules (1A through 4B) — the complete pipeline
- The webapp framework should already exist from the pipeline module

**Build these files:**

### Part 0: `/iterate` — Single-Cover Iteration Mode (HIGHEST PRIORITY — D19)

This is the PRIMARY page Tim will use first. Create a dedicated webapp page at `/iterate`:

- **Book picker**: Dropdown/search for any of the 99 titles (loaded from book_catalog.json)
- **Model selector (D20)**: Checkboxes for ALL configured models. "Select All" button to fire all 7+ models at once
- **Variation count selector (D22)**: Choose 1, 3, 5, 10, or 20 variations per model
- **Prompt editor**: Show auto-generated prompt, allow live editing before generating
- **Prompt library panel (D21)**: Browse saved prompts and style anchors. Click to load saved prompt. Mix-and-match style anchors as toggleable chips/tags. "Save this prompt" button. Star rating. Filter by tags.
- **Style anchor mixer**: Visual panel of style anchors as toggleable chips. Clicking adds/removes style text from prompt. Real-time prompt preview.
- **Generate button**: Kick off generation with selected book/models/prompt
- **Live results**: Show generated illustrations as they complete, grouped by model
- **Composited preview**: Auto-composite each result into the cover template
- **History panel**: All previous generations for this book (model, prompt, timestamp, cost)
- **Side-by-side compare**: Select 2-6 results for full-size comparison
- **Fit verification overlay**: Toggle to show/hide frame overlay on composited previews
- **Quick actions**: "Regenerate with tweaked prompt", "Try different model", "Save prompt to library", "Keep", "Discard"

### Part 1: `/review` — Batch Review Grid

- Scrollable grid of all processed books
- Per book: original cover + all variant thumbnails side-by-side
- Click to zoom/enlarge
- **Simple checkbox to mark winner** (D10) — not star ratings
- Filter by: book number, reviewed/unreviewed, quality score
- Progress bar
- Export selections as JSON
- **No authentication** (D12)

### Part 2: Static HTML Gallery (Fallback)

- `data/review_gallery.html` — standalone, works without webapp
- Embedded thumbnails, JavaScript for checkbox persistence (localStorage)
- Export button saves selections as JSON download

### Part 3: Archive Non-Winners (`src/archiver.py`)

- Archive non-winning variants to `Output Covers/Archive/{book_folder}/Variant-{n}/`
- Keep winners in place
- NEVER delete files — only move (D9)
- Log to `data/archive_log.json`
- Support "undo" — restore archived variants

### Part 4: Catalog PDF (`scripts/generate_catalog.py`)

- Cover page with project title and date
- Grid layout: 4-6 covers per page with book number, title, author
- Full-bleed images at readable size
- Table of contents
- Summary statistics
- Save to `Output Covers/Alexandria-Cover-Catalog.pdf`

**SCOPE: Build for 20 titles first (D23).**

**Verification checklist:**

Single-Cover Iteration (/iterate):
1. `py_compile` passes for all files — PASS/FAIL
2. `/iterate` page loads with book picker, model selector, prompt editor — PASS/FAIL
3. Selecting a book populates prompt editor — PASS/FAIL
4. Model selector shows all configured models — PASS/FAIL
5. Generate button triggers generation (or dry-run) — PASS/FAIL
6. History panel shows previous generations — PASS/FAIL
7. Side-by-side compare works for 2+ results — PASS/FAIL

Review Grid (/review):
8. Review page loads for 5 test books — PASS/FAIL
9. All images visible (original + variants) per book — PASS/FAIL
10. Checkbox selection works — PASS/FAIL
11. Selections saved to `data/variant_selections.json` — PASS/FAIL
12. Filter by reviewed/unreviewed works — PASS/FAIL

Archive:
13. Archive moves non-winners to Archive/ — PASS/FAIL
14. Winners remain in place — PASS/FAIL
15. No files deleted (only moved) — PASS/FAIL
16. `data/archive_log.json` records operations — PASS/FAIL
17. Undo restores archived variants — PASS/FAIL

Catalog:
18. Catalog PDF generated — PASS/FAIL
19. PDF has cover page, TOC, grid layout — PASS/FAIL
20. All titles and authors correct — PASS/FAIL
21. Saved to `Output Covers/Alexandria-Cover-Catalog.pdf` — PASS/FAIL

Run every check. Report PASS/FAIL for each.
```

---

## Quick Reference: Execution Order

| Order | Prompt | Thread Title | Status |
|-------|--------|-------------|--------|
| 1 | 1A — Cover Analysis | ✅ COMPLETE | Done |
| 2 | 1B — Prompt Engineering | ✅ COMPLETE | Done |
| 3 | 2A — Image Generation | 🔄 Running/Restarted | Updated with D19-D22 |
| 4 | 2B — Quality Gate | ⏳ Next | Paste after 2A completes |
| 5 | 3A — Cover Composition | ⏳ Waiting | Paste after 2B completes |
| 6 | 3B — Format Export | ⏳ Waiting | Paste after 3A completes |
| 7 | 4A — Batch Orchestration | ⏳ Waiting | Paste after 3B completes |
| 8 | 4B — Google Drive Sync | ⏳ Waiting | Paste after 4A completes |
| 9 | 5 — Visual QA + Review | ⏳ Waiting | Paste after 4B completes |
