# Codex Message for PROMPT-07G (Compositor Centering + Prompt Variation)

## What to paste in the Codex chat:

---

**CRITICAL: Preserve the current design/UI/UX exactly as it is.** Only modify the specific files listed in PROMPT-07G.

Read `Codex Prompts/PROMPT-07G-COMPOSITOR-AND-PROMPT-FIXES.md` in the repo.

**THREE FIXES:**

### Fix 1 (PRIORITY 1): Compositor Art Centering

In `src/cover_compositor.py`, in the `else` branch of `composite_single()` (the PNG template path, ~line 741):

**Stop using `_resolve_medallion_geometry()` for art placement in the template path.** The templates were punched at fixed coordinates (2864, 1620), but `_resolve_medallion_geometry()` uses dynamic detection that returns slightly different centers. This mismatch causes the art to not align with the template's hole.

Change the template path to use:
```python
center_x = FALLBACK_CENTER_X  # 2864
center_y = FALLBACK_CENTER_Y  # 1620
outer_radius = FALLBACK_RADIUS  # 500
```

Instead of:
```python
center_x = int(geometry["center_x"])
center_y = int(geometry["center_y"])
outer_radius = int(geometry["outer_radius"])
```

Remove the `_resolve_medallion_geometry()` call from the template path entirely. Only keep it for the legacy fallback path. Also update `_create_template_for_cover()` to use `FALLBACK_CENTER_X/Y` instead of detected geometry.

### Fix 2: Book-Specific Prompt Variation

In `src/prompt_generator.py`, the generic fallback at the end of `_motif_for_book()` (~line 659) returns a vague "period costume" motif for any book not in the hardcoded list (~70+ books).

**Replace the generic fallback** with a new `_build_dynamic_motif(title, author, book)` function that incorporates the book's actual title, author, and metadata into the prompt. Add `_guess_period(author)` to determine era-appropriate styling. See the prompt file for complete function code.

Change the final return of `_motif_for_book()` from the hardcoded generic BookMotif to:
```python
return _build_dynamic_motif(title, author, book)
```

### Fix 3: Book Titles in Dropdown

The iterate page dropdown shows most books as "Untitled". Ensure the `/api/iterate-data` endpoint returns titles from `config/book_catalog_enriched.json` which has all 99 titles with full title/author data.

**DO NOT TOUCH:** Frontend HTML/CSS/JS, sidebar, navigation, color scheme, any file not explicitly listed.

```bash
git add -A && git commit -m "fix: compositor centering + book-specific prompts + dropdown titles (PROMPT-07G)" && git push
```

---
