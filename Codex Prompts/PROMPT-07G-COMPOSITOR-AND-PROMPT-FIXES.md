# PROMPT-07G — Compositor Centering Fix + Book-Specific Prompt Variation

**Priority:** CRITICAL — Two fixes in one prompt.

**Branch:** `master`

---

## DESIGN PRESERVATION — DO NOT CHANGE

Do NOT touch `index.html`, sidebar, navigation, color scheme, page layouts, CSS, or any frontend files not explicitly listed here. Only modify the specific Python files listed below.

---

## Fix 1: Compositor Art Centering (PRIORITY 1)

### Problem

The PNG template pipeline (07E/07F) is structurally correct but has a centering mismatch. The template was punched at a fixed center (2864, 1620) by `create_png_templates.py`, but `_resolve_medallion_geometry()` at runtime uses dynamic detection that can return slightly different centers. When the art is pasted at a different center than the template's punch hole, the art doesn't align with the frame opening — causing visible original cover art on one side and a gap on the other.

### Solution

In the PNG template compositing path (the `else` branch in `composite_single()`, currently around lines 741-803 of `src/cover_compositor.py`), **do NOT use `_resolve_medallion_geometry()` for art placement**. Instead, read the center directly from the template's punch center, which is always the fixed known geometry: `FALLBACK_CENTER_X = 2864`, `FALLBACK_CENTER_Y = 1620`.

### Changes to `src/cover_compositor.py`

**In the `else` branch of `composite_single()` (the PNG template path, ~line 741):**

Replace the current geometry resolution for the template path. The art placement must use the SAME center coordinates that were used to punch the template. Since all templates are punched at (2864, 1620) by `create_png_templates.py`, hardcode these values for art placement:

```python
    else:
        # New medallion compositing pipeline: canvas + art + PNG template.
        # IMPORTANT: Art must be centered at the SAME coordinates the template
        # was punched at. Do NOT use _resolve_medallion_geometry() for art
        # placement — it uses dynamic detection that can return slightly
        # different centers, causing misalignment with the template hole.

        template_path = _find_template_for_cover(cover_path)
        if template_path is None:
            template_path = _create_template_for_cover(
                cover=cover,
                cover_path=cover_path,
                center_x=FALLBACK_CENTER_X,
                center_y=FALLBACK_CENTER_Y,
                punch_radius=TEMPLATE_PUNCH_RADIUS,
            )

        if template_path is None:
            logger.warning(
                "No PNG template found for %s. Falling back to legacy compositor pipeline.",
                cover_path.name,
            )
            # Use _resolve_medallion_geometry only for legacy fallback
            geometry = _resolve_medallion_geometry(cover=cover, cover_path=cover_path, region=region_obj)
            composited_rgb, validation_region = _legacy_medallion_composite(
                cover=cover,
                illustration=illustration,
                region_obj=region_obj,
                cover_w=cover_w,
                cover_h=cover_h,
                geometry=geometry,
                strict_window_mask=strict_window_mask,
            )
        else:
            logger.info("Using PNG template: %s", template_path.name)
            with Image.open(template_path) as template_raw:
                template = template_raw.convert("RGBA")
            if template.size != (cover_w, cover_h):
                template = template.resize((cover_w, cover_h), Image.LANCZOS)

            # Use FIXED center coordinates — must match template punch center
            center_x = FALLBACK_CENTER_X  # 2864
            center_y = FALLBACK_CENTER_Y  # 1620
            outer_radius = FALLBACK_RADIUS  # 500

            fill_rgb = _sample_cover_background(
                cover=cover,
                center_x=center_x,
                center_y=center_y,
                outer_radius=outer_radius,
            )
            canvas = Image.new("RGBA", (cover_w, cover_h), (*fill_rgb, 255))

            art_diameter = (TEMPLATE_PUNCH_RADIUS * 2) + 20  # 950px (10px bleed per side)
            art = _simple_center_crop(illustration)
            art = art.resize((art_diameter, art_diameter), Image.LANCZOS)

            art_layer = Image.new("RGBA", (cover_w, cover_h), (0, 0, 0, 0))
            paste_x = center_x - (art_diameter // 2)
            paste_y = center_y - (art_diameter // 2)
            art_layer.alpha_composite(art, (paste_x, paste_y))

            result = Image.alpha_composite(canvas, art_layer)
            result = Image.alpha_composite(result, template)
            composited_rgb = result.convert("RGB")
            validation_region = Region(
                center_x=center_x,
                center_y=center_y,
                radius=max(20, TEMPLATE_PUNCH_RADIUS),
                frame_bbox=region_obj.frame_bbox,
                region_type="circle",
            )
```

**Key changes from current code:**
1. `center_x = FALLBACK_CENTER_X` instead of `int(geometry["center_x"])`
2. `center_y = FALLBACK_CENTER_Y` instead of `int(geometry["center_y"])`
3. `outer_radius = FALLBACK_RADIUS` instead of `int(geometry["outer_radius"])`
4. `_resolve_medallion_geometry()` is no longer called in the template path (only in legacy fallback)
5. `_create_template_for_cover()` uses `FALLBACK_CENTER_X/Y` instead of detected geometry

This guarantees the art is pasted at EXACTLY the same center the template was punched at. No more misalignment.

---

## Fix 2: Book-Specific Prompt Variation

### Problem

The `_motif_for_book()` function in `src/prompt_generator.py` (around line 386) has hardcoded motifs for only ~25 specific books and ~6 authors. The remaining ~70+ books fall through to a completely generic motif:

```python
return BookMotif(
    iconic_scene="pivotal narrative tableau with period costume, emotional tension, and dramatic environmental storytelling",
    ...
)
```

This produces nearly identical illustrations for any book not in the hardcoded list — the user sees four near-identical images with generic "period costume" scenes.

### Solution

Replace the generic fallback with a function that builds book-specific motifs dynamically from the book's title, author, and any available metadata. The key insight: even without a hardcoded motif, we can extract meaningful imagery from a book's title and genre.

### Changes to `src/prompt_generator.py`

**Add this new function** before `_motif_for_book()`:

```python
def _build_dynamic_motif(title: str, author: str, book: dict[str, Any]) -> BookMotif:
    """Build a book-specific motif from title, author, and metadata.

    Instead of returning a generic 'period costume' prompt, this extracts
    meaningful imagery from the book's title and any available metadata
    (subtitle, genre, description, era).
    """
    # Use subtitle/description if available
    subtitle = _normalize(book.get("subtitle", ""))
    description = _normalize(book.get("description", ""))
    genre = _normalize(book.get("genre", ""))
    era = book.get("era", "")

    # Build a scene description from the title itself
    # The title is the single most identifying feature of any book
    title_clean = title.strip()
    author_clean = author.strip()

    # Combine available metadata into a rich context string
    context_parts = [title_clean]
    if subtitle:
        context_parts.append(subtitle)
    if description and len(description) > 10:
        context_parts.append(description[:200])

    context = ", ".join(context_parts)

    # Determine period/era from metadata or author's known era
    period = era if era else _guess_period(author_clean)

    # Build motif with title-specific imagery
    scene_core = f"a vivid scene inspired by '{title_clean}' by {author_clean}"
    if subtitle:
        scene_core += f" — {subtitle}"

    return BookMotif(
        iconic_scene=(
            f"{scene_core}, capturing the central narrative moment "
            f"with {period} period detail, rich environmental storytelling, "
            f"and emotionally resonant composition"
        ),
        character_portrait=(
            f"the protagonist of '{title_clean}' by {author_clean} "
            f"in authentic {period} attire, expressive face revealing inner conflict, "
            f"surrounded by objects and settings specific to the story's world"
        ),
        setting_landscape=(
            f"the key location from '{title_clean}' — "
            f"a {period} landscape with layered architecture, atmospheric depth, "
            f"and visual details that evoke the story's central themes and setting"
        ),
        dramatic_moment=(
            f"the climactic turning point of '{title_clean}' by {author_clean}, "
            f"rendered with {period} dramatic lighting, heightened emotion, "
            f"and visual tension that captures the story's most pivotal moment"
        ),
        symbolic_theme=(
            f"the core themes of '{title_clean}' represented through allegorical imagery — "
            f"{period} symbolism, contrasting light and shadow, "
            f"and visual metaphors drawn from the narrative's deepest meanings"
        ),
        style_specific_prefix=f"{period} mixed-media literary illustration",
    )


def _guess_period(author: str) -> str:
    """Guess the historical period from the author name."""
    author_lower = author.lower()
    # Ancient/Classical
    if any(name in author_lower for name in ["homer", "sophocles", "euripides", "virgil", "ovid", "aeschylus"]):
        return "ancient classical"
    # Medieval
    if any(name in author_lower for name in ["chaucer", "dante", "boccaccio"]):
        return "medieval"
    # Renaissance/Early Modern
    if any(name in author_lower for name in ["shakespeare", "cervantes", "marlowe", "milton"]):
        return "Renaissance"
    # 18th century
    if any(name in author_lower for name in ["swift", "defoe", "fielding", "voltaire", "sterne"]):
        return "18th-century Enlightenment"
    # Romantic era
    if any(name in author_lower for name in ["shelley", "byron", "keats", "poe", "brontë", "bronte", "hawthorne"]):
        return "Romantic era"
    # Victorian
    if any(name in author_lower for name in [
        "dickens", "austen", "eliot", "hardy", "trollope", "gaskell",
        "collins", "thackeray", "wilde", "stoker", "conan doyle",
        "stevenson", "carroll", "kipling", "twain", "verne",
        "wells", "dostoyev", "tolstoy", "hugo", "dumas", "balzac",
        "zola", "flaubert", "maupassant", "chekhov", "turgenev",
        "forster", "london", "conrad", "james"
    ]):
        return "Victorian-era"
    # Early 20th century
    if any(name in author_lower for name in [
        "fitzgerald", "hemingway", "woolf", "joyce", "kafka",
        "orwell", "huxley", "steinbeck", "faulkner", "camus",
        "beckett", "lawrence", "maugham", "chesterton"
    ]):
        return "early 20th-century"
    # Default
    return "classical literary"
```

**Then update the generic fallback at the end of `_motif_for_book()`** (currently around line 659):

Replace:
```python
    return BookMotif(
        iconic_scene="pivotal narrative tableau with period costume, emotional tension, and dramatic environmental storytelling",
        character_portrait="central protagonist in historically grounded attire, expressive face, and purposeful posture",
        setting_landscape="key story environment with layered architecture, atmospheric depth, and symbolic objects",
        dramatic_moment="climactic turning point under turbulent light, motion, and heightened emotional stakes",
        symbolic_theme="core themes represented by allegorical objects, contrasting light, and recursive geometry",
        style_specific_prefix="period-inspired mixed-media engraving",
    )
```

With:
```python
    return _build_dynamic_motif(title, author, book)
```

Note: `_motif_for_book` receives `book` as its argument (the full dict). The `title` and `author` variables are already extracted at the top of the function (lines 387-388). Just change the final return to call `_build_dynamic_motif(title, author, book)`.

---

## Fix 3: Book Titles in Dropdown (Minor)

### Problem

The iterate page book dropdown shows most books as "Untitled" (see user screenshot). The iterate page loads book data but isn't pulling titles from the enriched catalog.

### Investigation

Check how the iterate page's book dropdown is populated. It likely reads from `/api/iterate-data` which may return a book list without titles. The enriched catalog is at `config/book_catalog_enriched.json` and has all 99 titles. Ensure the API endpoint returns the enriched titles.

### Changes

In whatever API handler serves `/api/iterate-data` (likely in `scripts/quality_review.py`), ensure the book list includes titles from `config/book_catalog_enriched.json`. If the endpoint currently reads from a different source that lacks titles, update it to use the enriched catalog.

Look at how the books list is constructed in the iterate-data response. If books are coming from `config/book_catalog.json` or a bare list, switch to using `config/book_catalog_enriched.json` which has full title/author data.

---

## Validation

### Compositor centering
1. Generate a cover for Book #1 (A Room with a View)
2. Zoom into the medallion edge at 100% — there should be ZERO visible original cover art
3. The AI art should be perfectly centered within the frame opening
4. Generate 3 covers for the same book — all should have IDENTICAL centering

### Prompt variation
1. Generate 4 variants for Book #1 (A Room with a View)
2. Each variant should show DIFFERENT scenes related to the actual book:
   - Variant 1: A vivid scene from the novel
   - Variant 2: Character portrait of the protagonist
   - Variant 3: Italian/English countryside setting
   - Variant 4: Dramatic moment
3. The images should NOT all look like generic "period costume" scenes

### Book titles
1. Open the iterate page
2. Open the book dropdown
3. All 99 books should show their actual titles, not "Untitled"

---

## Commit and Push

```bash
git add -A && git commit -m "fix: compositor centering alignment + book-specific prompt variation (PROMPT-07G)

1. Compositor: Use fixed center coordinates (2864, 1620) for art placement
   in the PNG template path instead of dynamic detection. Guarantees art
   aligns perfectly with the pre-punched template hole. Eliminates visible
   original cover art at medallion edges.

2. Prompts: Replace generic 'period costume' fallback with dynamic motif
   builder that uses the book's actual title, author, and metadata to
   generate book-specific illustration prompts. Adds _guess_period() for
   era-appropriate styling based on author.

3. Book dropdown: Ensure iterate page shows actual book titles from
   enriched catalog instead of 'Untitled'." && git push
```
