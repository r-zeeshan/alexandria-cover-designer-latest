# Alexandria Cover Designer — Project State

> **Purpose**: This is the living source of truth for the entire project. When a conversation compacts or a new chat starts, paste or reference this file to restore full context instantly. Update this file after every completed phase.
>
> **Last updated**: 2026-02-20 — **Planning & Scoping COMPLETE. Phase 0 done. Master Execution Report generated. All Tim decisions captured (18 decisions). Provider abstraction layer designed. Multi-model wildcard strategy finalized. Codex Prompts updated. Ready for Phase 1A development.**
>
> **OWNERSHIP: This file may ONLY be edited by Claude (Cowork) or Tim. Codex must NEVER edit, modify, or overwrite this file. Codex should READ it for context only.**

---

## Project Summary

**Goal**: Replace the AI-generated center illustrations on 99 existing book covers with 5 higher-quality artistic variants per cover, producing 495 total variant covers. The ornamental borders, text, and layout remain untouched — only the circular medallion illustration in the center-right of the front cover changes.

**Why**: The current center illustrations look "too AI-generated." We want classical oil painting / renaissance illustration quality that feels hand-painted, not machine-made.

---

## Architecture (Final Design)

```
Input Cover (.ai/.jpg/.pdf)
    → [src/cover_analyzer.py] → Extract design region coordinates + metadata
    → [src/prompt_generator.py] → Generate 5 book-specific art prompts per title
    → [src/image_generator.py] → Generate 5 variant illustrations via AI model
    → [src/cover_compositor.py] → Composite new illustrations into cover template
    → [src/output_exporter.py] → Export as .ai/.jpg/.pdf (matching input formats)
    → 5 variant folders per cover, each with 3 files
```

**Stack**: Python + Pillow/OpenCV (image processing) → FLUX.1 or SDXL (AI generation via API or local) → ReportLab/pypdf (PDF export) → svglib or Illustrator scripting (.ai export)

---

## Phase Status

| Phase | Description | Status | Notes |
|-------|-------------|--------|-------|
| **0. Project Setup** | Folder structure, Project state Alexandria Cover designer.md, CLAUDE.md, prompts | ✅ COMPLETE | This document |
| **1A. Cover Analysis** | Analyze input covers: extract center design region, detect ornament boundaries | ⏳ PLANNED | |
| **1B. Prompt Engineering** | Build title→prompt mapping for all 99 books, 5 style variants each | ⏳ PLANNED | |
| **2A. Image Generation Pipeline** | Batch generate 495 illustrations via chosen AI model | ⏳ PLANNED | |
| **2B. Quality Gate** | Auto-filter bad generations, score quality, flag for review | ⏳ PLANNED | |
| **3A. Cover Composition** | Composite new illustrations into existing cover templates | ⏳ PLANNED | |
| **3B. Format Export** | Export each variant as .ai, .jpg, .pdf matching input specs | ⏳ PLANNED | |
| **4A. Batch Orchestration** | End-to-end pipeline: input folder → output folder structure | ⏳ PLANNED | |
| **4B. Google Drive Sync** | Upload output to Google Drive folder structure | ⏳ PLANNED | |
| **5. Visual QA** | Side-by-side comparison tool, Tim picks best variants | ⏳ PLANNED | |

---

## Critical Technical Facts

### Input Covers
- **Count**: 99 covers (numbered 1–100, #12 missing)
- **Location**: `Input Covers/` (local) + [Google Drive](https://drive.google.com/drive/folders/1ybFYDJk7Y3VlbsEjRAh1LOfdyVsHM_cS?usp=sharing)
- **Formats per cover**: `.ai`, `.jpg`, `.pdf` (3 files each)
- **JPG specs**: 3784×2777 pixels, 300 DPI, RGB, ~4.8MB each
- **Layout**: Full wraparound cover (front + spine + back)
  - Front cover is RIGHT side of the image
  - Spine is the narrow center strip
  - Back cover is LEFT side of the image

### Cover Design Anatomy
```
┌─────────────────┬──────┬─────────────────────┐
│   BACK COVER    │SPINE │    FRONT COVER       │
│                 │      │                      │
│  Quote          │ Title│   TITLE              │
│  Author quote   │(vert)│   Subtitle           │
│  Description    │      │                      │
│                 │      │   ┌──────────┐       │
│                 │      │   │ORNAMENTAL│       │
│                 │      │   │ FRAME    │       │
│                 │      │   │          │       │
│                 │      │   │ ●CENTER● │       │
│                 │      │   │ ●IMAGE●  │       │
│                 │      │   │          │       │
│                 │      │   └──────────┘       │
│  Alexandria     │      │                      │
│  logo           │      │   AUTHOR NAME        │
│                 │      │                      │
│  Gold ornaments │      │   Gold ornaments     │
└─────────────────┴──────┴─────────────────────┘
```

### Design Constants (DO NOT CHANGE)
- **Background**: Navy blue (#1a2744 approximately)
- **Ornaments**: Gold/bronze decorative corner pieces + frame around center image
- **Center frame**: Circular/medallion with ornate gold baroque border
- **Typography**: Gold text, serif font (likely Garamond or similar)
- **Spine**: Title vertical, small Alexandria logo at bottom

### Center Illustration (THE PART WE'RE REPLACING)
- **Shape**: Circular, sits inside the ornamental frame
- **Position**: Center-right of full cover (on front cover)
- **Approximate region**: ~1100px diameter circle
- **Current style**: AI-generated scenes relating to book content
- **Target style**: Classical oil painting / renaissance illustration feel
- **Must depict**: Scene or motif directly relevant to the specific book title

### Output Specifications
- **Per cover**: 5 variant folders (Variant-1 through Variant-5)
- **Per variant**: 3 files (.ai, .jpg, .pdf) — same filenames as input
- **Folder naming**: Match input folder name exactly (without " copy" suffix)
- **Resolution**: Must match input (3784×2777, 300 DPI)
- **Output location**: Google Drive folder: https://drive.google.com/drive/folders/1Vr184ZsX3k38xpmZkd8g2vwB5y9LYMRC?usp=sharing

### Output Folder Structure
```
Output Covers/
├── 1. A Room with a View - E. M. Forster/
│   ├── Variant-1/
│   │   ├── A Room with a View - E. M. Forster.ai
│   │   ├── A Room with a View - E. M. Forster.jpg
│   │   └── A Room with a View - E. M. Forster.pdf
│   ├── Variant-2/
│   │   └── ...
│   ├── Variant-3/
│   │   └── ...
│   ├── Variant-4/
│   │   └── ...
│   └── Variant-5/
│       └── ...
├── 2. Moby Dick; Or, The Whale - Herman Melville/
│   ├── Variant-1/
│   └── ...
└── ...
```

---

## AI Image Generation Strategy

### Multi-Model Strategy via Provider Abstraction Layer
- **Primary providers**: OpenRouter (unified), fal.ai, OpenAI direct, Google Cloud direct
- **Pilot**: Test 6 models simultaneously on 5 books (150 images, ~$10)
- **Scale**: 2-3 winning models used in parallel (wildcard strategy)
- **Retry on quality failure**: Same model, tweaked prompt (up to 3 retries)
- **Cost range**: $0.003/image (FLUX Schnell) to $0.167/image (GPT Image 1 High)
- **Budget for 99 covers**: ~$50-200 depending on model mix
- **Budget for 2,500 covers**: ~$1,800-3,800 depending on model mix and variant count

### Prompt Strategy (5 variants per book — 3 Sketch + 2 Wildcard)

Tim's preferred style: **Cossacks & Sevastopol Sketches** from Sample Output folder.
These have a hand-drawn, classical engraving/sketch aesthetic — NOT photorealistic, NOT generic AI.

Each book gets 5 different illustration approaches:

**Variants 1-3: Sketch/Engraving Style (modeled on Cossacks & Sevastopol samples)**
1. **Iconic Scene (Sketch)** — The most famous scene, rendered as a classical pen-and-ink sketch with warm sepia tones
2. **Character Portrait (Sketch)** — Main character in period-appropriate setting, engraving/etching style
3. **Setting/Landscape (Sketch)** — Key location from the story, rendered as a detailed classical illustration

**Variants 4-5: Alternative Styles (still classical, book-relevant, bestseller-worthy)**
4. **Dramatic Oil Painting** — A pivotal scene in rich oil painting style, different from the sketch variants but still classical and hand-crafted feeling
5. **Symbolic/Allegorical** — Abstract/symbolic representation using a distinct artistic style (watercolor, woodcut, or period-specific art) that still fits the navy/gold cover aesthetic

### Style Reference: Cossacks & Sevastopol (PRIMARY — Variants 1-3)
```
"classical pen-and-ink sketch, detailed engraving illustration, sepia tones,
hand-drawn crosshatching, 19th century book illustration style,
warm parchment tones, fine line work, copper plate etching quality,
circular vignette composition, no text, no letters, no watermarks"
```

### Style Reference: Alternative (Variants 4-5)
```
Variant 4: "classical oil painting, masterpiece quality, warm golden lighting,
renaissance art style, detailed brushwork, gallery-quality illustration,
circular vignette composition, rich color palette, dramatic chiaroscuro"

Variant 5: "period-appropriate artistic style, hand-crafted aesthetic,
classical composition, warm tones matching navy-and-gold cover design,
unique artistic interpretation, circular vignette composition"
```

### Negative Prompt (ALL variants)
```
"text, letters, words, watermark, signature, photorealistic, 3d render,
cartoon, anime, comic, digital art, modern, neon, flat colors, low quality,
blurry, deformed, ugly, bad anatomy, distorted hands, extra fingers, mutated,
obviously AI-generated, stock photo, generic"
```

---

## Folder Structure

```
Alexandria Cover designer/
├── Input Covers/           ← 99 folders with .ai/.jpg/.pdf (READ ONLY)
├── Sample Output style covers/  ← Tim's approved style examples
├── Output Covers/          ← Generated variants (→ synced to Google Drive)
├── src/                    ← Source code
│   ├── cover_analyzer.py       ← Phase 1A: Extract design region
│   ├── prompt_generator.py     ← Phase 1B: Book→prompt mapping
│   ├── image_generator.py      ← Phase 2A: AI image generation
│   ├── quality_gate.py         ← Phase 2B: Quality scoring/filtering
│   ├── cover_compositor.py     ← Phase 3A: Composite into template
│   ├── output_exporter.py      ← Phase 3B: Export .ai/.jpg/.pdf
│   ├── pipeline.py             ← Phase 4A: End-to-end orchestrator
│   ├── gdrive_sync.py          ← Phase 4B: Google Drive upload
│   └── config.py               ← Configuration + env vars
├── config/
│   ├── book_catalog.json       ← All 99 books: number, title, author, genre, themes
│   └── prompt_templates.json   ← 5 variant prompt templates
├── scripts/
│   ├── run_pipeline.sh         ← Main execution script
│   ├── generate_catalog.py     ← Build book_catalog.json from folder names
│   └── quality_review.py       ← Side-by-side comparison tool
├── tests/
│   └── test_unit.py            ← Unit tests
├── Codex Prompts/          ← Per-phase build instructions for Codex
├── Codex Output Answers/   ← Codex responses saved after each phase
├── data/                   ← Runtime data (gitignored)
├── logs/                   ← Logs (gitignored)
├── tmp/                    ← Temp files (gitignored)
├── Project state Alexandria Cover designer.md        ← THIS FILE
├── CLAUDE.md               ← Codex instructions
├── QA-CHECKLIST.md         ← Quality assurance checklist
├── .gitignore
├── .env.example            ← Environment variable template
└── requirements.txt        ← Python dependencies
```

---

## Google Drive Links

| Resource | URL |
|----------|-----|
| **Input Covers** | https://drive.google.com/drive/folders/1ybFYDJk7Y3VlbsEjRAh1LOfdyVsHM_cS?usp=sharing |
| **Output Destination** | https://drive.google.com/drive/folders/1Vr184ZsX3k38xpmZkd8g2vwB5y9LYMRC?usp=sharing |

---

## Tim's Decisions (Complete — Feb 20, 2026)

| # | Decision | Tim's Choice |
|---|----------|-------------|
| D1 | Preferred illustration style | Cossacks/Sevastopol painting style |
| D2 | Variant strategy | 3 sketch + 2 wildcard per book |
| D3 | Cover text handling | Text is OUTSIDE the medallion — won't be affected by compositing |
| D4 | Prompt approach | AI interprets freely from title (no curated scene descriptions) |
| D5 | .ai file output | Essential — all 3 formats required (.ai + .jpg + .pdf) |
| D6 | Quality gate retry | Same model, tweaked prompt (up to 3 retries) |
| D7 | Pilot output | Final composited covers only (not raw illustrations) |
| D8 | Selective re-run | Essential — must target individual books/variants for re-generation |
| D9 | Post-selection | Archive non-winners to separate folder (never delete) |
| D10 | Review method | Simple checkbox (pick winner) in webapp grid |
| D11 | Catalog/lookbook PDF | Essential deliverable — all 99 winning covers in a visual grid |
| D12 | Webapp auth | No auth needed — private Railway URL |
| D13 | Batch strategy at scale | Configurable batch size (100, 250, 500, or all) |
| D14 | Deployment platform | Railway from day one |
| D15 | Budget approach | Quality first, budget flexible |
| D16 | Scale target | 99 covers now, 2,500 covers later |
| D17 | API accounts | None yet — will sign up per recommendation |
| D18 | Multi-model wildcard | Each model generates 1-3 images per slot, best wins |
| D19 | Single-cover iteration | Webapp and pipeline must support processing a single cover/title end-to-end. This is the PRIMARY workflow initially — iterate on one cover to nail design, model selection, and prompt quality before any batch processing. The webapp must have a dedicated single-cover mode. |
| D20 | All models simultaneously | During iteration, fire ALL configured models at once for the same prompt/book. Tim compares outputs across models and picks the best. This is how we determine which models work best. |
| D21 | Prompt library system | Save successful prompts to a reusable library (`config/prompt_library.json`). Library contains style anchors, prompt templates, and full prompts that worked well. Mix-and-match style anchors during iteration. Prompts must be title-agnostic (work for any book) while producing title-relevant output. Select from library for bulk processing. |
| D22 | Configurable variation count | During iteration, generate 5, 10, 20+ variations per prompt/model combo. Not locked to 5 variants. Each prompt × model combination can produce multiple outputs. This helps determine which prompt+model combos produce the best results. |
| D23 | Start with 20 titles | Build and test everything with 20 titles first. Get a fully working tool with real outputs before scaling to 99 or 2,500. Optimize for rapid single-cover iteration, not bulk throughput. Scale later. |

---

## AI Provider Strategy

### Provider Abstraction Layer
The image generation module wraps multiple API backends behind a single interface. Switch providers with one config change.

### Recommended API Signups (in order)
1. **OpenRouter** (openrouter.ai) — Single API key for FLUX 2, Nano Banana Pro, Seedream, Riverflow
2. **fal.ai** — 600+ models, 30-50% cheaper than Replicate, fast inference
3. **OpenAI** (platform.openai.com) — Direct access to GPT Image 1 (all tiers)
4. **Google Cloud** (console.cloud.google.com) — Imagen 4 and Nano Banana Pro with batch discounts

### Pilot Models (test all 6, under $10 total)
- FLUX 2 Pro ($0.055/img) — Dramatic scenes, lighting
- GPT Image 1 Medium ($0.04/img) — Conceptual compositions
- GPT Image 1 High ($0.167/img) — Premium quality ceiling test
- Imagen 4 Ultra ($0.06/img) — Fine detail, classical art
- Nano Banana Pro ($0.067/img batch) — Theme interpretation
- FLUX 2 Schnell ($0.003/img) — Speed/cost baseline

---

## Golden Rules (Apply to ALL Phases)

1. **NEVER modify the ornamental borders, text, or layout** — only the center illustration changes
2. **NEVER modify Input Covers** — they are read-only source material
3. **Output filenames MUST match input filenames exactly** (minus " copy" suffix on folders)
4. **All outputs must be 300 DPI, 3784×2777 pixels**
5. **Each illustration must be directly relevant to the specific book title**
6. **Style must be classical oil painting — NOT photorealistic, NOT cartoonish, NOT obviously AI**
7. **Do NOT modify Project state Alexandria Cover designer.md** (Codex reads only; Cowork/Tim updates)
8. **Text on covers is OUTSIDE the medallion** — compositing only touches the circular illustration area
9. **AI interprets freely from title** — no curated scene descriptions needed, the AI decides what to depict
10. **Must support selective re-runs** — regenerate individual books/variants without re-running entire pipeline
11. **Archive non-winners** — move rejected variants to Archive/ folder after Tim picks winners (never delete)
12. **Single-cover first** — the webapp and pipeline must support processing one cover at a time. Iterate on design/model/prompt quality with a single title before batch processing.
13. **All models at once** — during iteration, fire all configured models simultaneously and compare outputs side-by-side
14. **Prompt library** — save successful prompts to a reusable library. Style anchors are mix-and-match components. Prompts are title-agnostic but produce title-relevant output.
15. **Variable variation count** — generate 5, 10, 20+ variations during iteration. Not locked to 5.
