# Prompt 5 — Visual QA Tool + Review Grid + Catalog PDF

**Priority**: HIGH — Essential for Tim's review workflow and final deliverable
**Scope**: `scripts/quality_review.py`, `src/static/review.html`, `scripts/generate_catalog.py`, `src/archiver.py`
**Depends on**: Prompt 3B (exported covers must exist)
**Estimated time**: 60-90 minutes

---

## Context

Read `Project state Alexandria Cover designer.md`. Tim needs to review all 99 books × 5 variants and pick the best design for each. The review grid is deployed as part of the Railway webapp. After Tim picks winners, non-winners are archived (never deleted) and a final catalog/lookbook PDF is generated.

---

## Task

### Part 0: Single-Cover Iteration Mode (HIGHEST PRIORITY — Tim's decision D19)

This is the PRIMARY initial workflow. Before any batch processing, Tim needs to iterate on one cover at a time to nail down the right model, prompt style, and quality settings. Create a dedicated page at `/iterate` that provides:

- **Book picker**: Dropdown or search to select any of the 99 titles
- **Model selector**: Checkboxes for ALL configured models (D20). "Select All" button to fire all 7+ models at once. Tim wants to see outputs from every model simultaneously for the same prompt.
- **Variation count selector (D22)**: Dropdown or input to choose how many variations per model: 1, 3, 5, 10, 20. e.g., 7 models × 10 variants = 70 images from one click.
- **Prompt editor**: Show the auto-generated prompt for the selected book/variant, allow Tim to edit it live before generating
- **Prompt library panel (D21)**: Browse saved prompts and style anchors. Click to load a saved prompt into the editor. Mix-and-match style anchors by checking/unchecking them. "Save this prompt" button to add the current prompt to the library with notes. Star rating on saved prompts. Filter by tags (sketch, oil, gothic, etc.)
- **Style anchor mixer**: Visual panel showing all available style anchors as toggleable chips/tags. Clicking them adds/removes the style text from the current prompt. Preview the assembled prompt in real-time.
- **Generate button**: Kick off generation for the selected book with chosen model(s) and prompt
- **Live results**: Show generated illustrations as they complete (real-time updates). Group by model so Tim can compare model quality.
- **Composited preview**: Automatically composite each result into the cover template and show the final cover (not just the raw illustration)
- **History panel**: Show ALL previous generations for this book (with model name, prompt used, timestamp, cost) so Tim can compare across iterations
- **Quick actions**: "Regenerate with tweaked prompt", "Try different model", "Save prompt to library", "Keep this one", "Discard"
- **Side-by-side compare**: Select any 2-6 previous results and view them side-by-side at full size. Grouped by model for easy comparison.
- **Fit verification overlay**: Toggle button to show/hide the ornamental frame overlay on any composited preview, confirming the illustration fits perfectly within the medallion
- This page is the FIRST thing Tim will use — it must be polished, fast, and intuitive

### Part 1: Webapp Review Grid (for batch review — after single-cover iteration is complete)

Create a review page at `/review` in the webapp that shows:
- All 99 books in a scrollable grid
- For each book: the original cover + all variant thumbnails side-by-side
- Click to zoom/enlarge any cover
- **Simple checkbox to mark the "winner"** per book (Tim's decision: checkboxes, not star ratings)
- Filter by: book number, reviewed/unreviewed status, quality score
- Progress bar showing how many books have been reviewed
- Export selections as JSON
- **No authentication required** (Tim's decision: private Railway URL, no auth)

### Part 2: Static HTML Gallery (Fallback)

Also generate a standalone static HTML page (`data/review_gallery.html`) that works without the webapp:
- Same layout as above but self-contained
- Embedded thumbnail images (base64 or relative paths)
- JavaScript for checkbox state persistence (localStorage)
- Export button saves selections as JSON download

### Part 3: Archive Non-Winners (`src/archiver.py`)

After Tim confirms selections via the review grid:
- **Archive non-winning variants** to `Output Covers/Archive/{book_folder}/Variant-{n}/`
- Keep winning variants in place in the main output folder
- NEVER delete any files — only move to Archive folder (Tim's decision)
- Log all archive operations to `data/archive_log.json`
- Support "undo" — move archived variants back if Tim changes mind

### Part 4: Catalog/Lookbook PDF (`scripts/generate_catalog.py`)

**Essential deliverable** (Tim's decision): Generate a beautiful PDF showing all 99 winning covers:
- Cover page with project title and date
- Grid layout: 4-6 covers per page, each with book number, title, and author
- Full-bleed cover images at readable size
- Table of contents with book list
- Summary statistics (total covers, model breakdown, quality scores)
- Save to `Output Covers/Alexandria-Cover-Catalog.pdf`

### Output
- `data/variant_selections.json`: Tim's picks per book
- `data/review_gallery.html`: Standalone review page
- `data/archive_log.json`: Record of archived files
- `Output Covers/Archive/`: Archived non-winning variants
- `Output Covers/Alexandria-Cover-Catalog.pdf`: Final lookbook

---

## Verification Checklist

### Single-Cover Iteration Mode (/iterate)
1. `py_compile` passes for all new/modified files — PASS/FAIL
2. `/iterate` page loads with book picker, model selector, prompt editor — PASS/FAIL
3. Selecting a book populates the prompt editor with auto-generated prompt — PASS/FAIL
4. Model selector shows all configured models from .env — PASS/FAIL
5. Generate button triggers single-book generation (or dry-run if no API key) — PASS/FAIL
6. History panel shows previous generations for the selected book — PASS/FAIL
7. Side-by-side compare mode works for 2+ results — PASS/FAIL

### Review Grid (/review — batch mode)
8. Generate review page/tool for 5 test books — PASS/FAIL
9. All 6 images (original + 5 variants) visible per book — PASS/FAIL
10. Checkbox selection works (click to select winner) — PASS/FAIL
11. Selections saved to `data/variant_selections.json` — PASS/FAIL
12. Full 99-book review tool loads without errors — PASS/FAIL
13. Filter by reviewed/unreviewed works — PASS/FAIL

### Archive
14. Archive function moves non-winners to Archive/ folder — PASS/FAIL
15. Winning variants remain in place — PASS/FAIL
16. No files are deleted (only moved) — PASS/FAIL
17. `data/archive_log.json` records all operations — PASS/FAIL
18. Undo function restores archived variants — PASS/FAIL

### Catalog PDF
19. Catalog PDF generated with all winning covers — PASS/FAIL
20. PDF has cover page, table of contents, grid layout — PASS/FAIL
21. All book titles and authors displayed correctly — PASS/FAIL
22. PDF saved to `Output Covers/Alexandria-Cover-Catalog.pdf` — PASS/FAIL
