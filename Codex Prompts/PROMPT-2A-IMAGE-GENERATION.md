# Prompt 2A — Image Generation Pipeline

**Priority**: HIGH — Core image generation
**Scope**: `src/image_generator.py`, `src/config.py`, `src/prompt_library.py`
**Depends on**: Prompt 1B (prompts must exist)
**Estimated time**: 60-90 minutes (code) + generation runtime

---

## Context

Read `Project state Alexandria Cover designer.md` for full context. Read `config/book_prompts.json` for all 495 prompts.

We need a robust image generation pipeline that supports TWO modes:
1. **Iteration mode (PRIMARY)**: Generate for ONE book, with ALL models simultaneously, configurable variation count (5, 10, 20+), prompt editing, and a prompt library system
2. **Batch mode**: Process all 99 books with proven model+prompt combos

---

## Task

Create `src/image_generator.py`, `src/config.py`, and `src/prompt_library.py`.

### Core Features

1. **API Integration (Provider Abstraction Layer)**:
   - Must support multiple providers behind a single interface: OpenRouter, fal.ai, Replicate, OpenAI direct, Google Cloud direct
   - Configurable via environment variables: `AI_PROVIDER` (openrouter/fal/replicate/openai/google) and `AI_MODEL`
   - **Must support running ALL models in parallel** (Tim's decision D20): fire every configured model simultaneously for the same prompt. During iteration, Tim wants to see outputs from FLUX 2 Pro, FLUX 2 Schnell, GPT Image 1 High, GPT Image 1 Medium, Imagen 4 Ultra, Imagen 4 Fast, Nano Banana Pro — all at once for the same book/prompt
   - API keys from environment variables (`OPENROUTER_API_KEY`, `FAL_API_KEY`, `REPLICATE_API_TOKEN`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`)

2. **All-Models-At-Once Mode (D20)**:
   - `generate_all_models(book, prompt, models_list)` fires every model in `models_list` concurrently
   - Each model generates the same prompt (or its own variant if using prompt library)
   - Results saved with model name in path: `tmp/generated/{book_number}/{model_name}/variant_{n}.png`
   - Track generation time, cost, and model for each image
   - This is the PRIMARY mode during iteration — Tim compares across models

3. **Configurable Variation Count (D22)**:
   - Not locked to 5 variants. Tim can request 5, 10, 20+ per prompt/model combo
   - CLI: `--variants 10` generates 10 images per model per prompt
   - Each model × prompt combo can produce N outputs: e.g., 8 models × 10 variants = 80 images for one book
   - Numbering: variant_1.png through variant_N.png per model folder

4. **Batch Processing** (for after iteration is complete):
   - Process books sequentially (or with configurable concurrency)
   - Save each generated image to `tmp/generated/{book_number}/variant_{n}.png`
   - Skip already-generated images (resume support)
   - Progress reporting: `[42/495] Generating Variant 3 for "Moby Dick"...`

5. **Error Handling**:
   - Retry on API errors (429, 500, 502, 503) with exponential backoff
   - Max 3 retries per image
   - Log failures and continue (don't abort entire batch)
   - Save failure log to `data/generation_failures.json`

6. **Rate Limiting**:
   - Configurable delay between requests (default 1 second)
   - Respect API rate limits
   - Per-provider rate limiting (different providers have different limits)

7. **Image Post-Processing**:
   - Ensure output is 1024×1024 PNG
   - Apply circular crop/mask (the illustration will be composited into a circle)
   - Basic quality check: reject blank/solid-color images

8. **Single-Cover Mode (ESSENTIAL — Tim's decision D19)**:
   - The PRIMARY initial workflow is single-cover iteration — generate variants for ONE book, review, tweak prompt/model, regenerate, repeat until happy
   - `generate_single_book()` must be a first-class entry point, not a wrapper around the batch function
   - Must support: choosing which model(s) to use per run, adjusting prompt text before generation, generating any number of variants (not locked to 5)
   - The webapp will call this directly for single-cover iteration mode
   - CLI: `python -m src.image_generator --book 2 --model openai/gpt-image-1 --variants 3`
   - CLI all-models: `python -m src.image_generator --book 2 --all-models --variants 10`

### Prompt Library System (`src/prompt_library.py` — Tim's decision D21)

Create a prompt library that stores reusable, proven prompts and style anchors:

```python
# src/prompt_library.py

@dataclass
class StyleAnchor:
    """A reusable style component that can be mixed into prompts."""
    name: str                    # e.g., "warm_sepia_sketch", "dramatic_oil", "gothic_moody"
    description: str             # Human-readable description
    style_text: str              # The actual style instruction text
    tags: list[str]              # e.g., ["sketch", "warm", "classical"]

@dataclass
class LibraryPrompt:
    """A saved prompt that worked well."""
    id: str                      # Unique identifier
    name: str                    # Human-readable name
    prompt_template: str         # The prompt text (with {title} placeholder for book-agnostic use)
    style_anchors: list[str]     # Which style anchors are included
    negative_prompt: str
    source_book: str             # Which book it was first tested on
    source_model: str            # Which model produced the best result
    quality_score: float         # Score from quality gate
    saved_by: str                # "tim" or "auto"
    created_at: str              # ISO timestamp
    notes: str                   # Tim's notes about why this prompt works

class PromptLibrary:
    """Manages the prompt library."""

    def __init__(self, library_path: Path):
        ...

    def get_style_anchors(self) -> list[StyleAnchor]:
        """Return all available style anchors."""
        ...

    def save_prompt(self, prompt: LibraryPrompt):
        """Save a successful prompt to the library."""
        ...

    def get_prompts(self, tags: list[str] = None) -> list[LibraryPrompt]:
        """Get prompts, optionally filtered by tags."""
        ...

    def build_prompt(self, book_title: str, style_anchors: list[str], custom_text: str = "") -> str:
        """Build a prompt from style anchors + book title + optional custom text."""
        ...

    def get_best_prompts_for_bulk(self, top_n: int = 5) -> list[LibraryPrompt]:
        """Get the top N prompts by quality score for bulk processing."""
        ...
```

**Key concept**: Prompts are **title-agnostic** — they describe a *style and approach* (e.g., "dramatic classical oil painting of the most iconic scene from {title}") rather than book-specific details. The AI model interprets what to depict based on the title. This means one great prompt can work across all 99 books.

**Style anchors** are mix-and-match building blocks:
- `warm_sepia_sketch`: "classical pen-and-ink sketch, sepia tones, crosshatching, 19th century illustration"
- `dramatic_oil`: "classical oil painting, dramatic chiaroscuro, rich golden lighting, masterpiece quality"
- `gothic_moody`: "dark atmospheric, moody shadows, dramatic lighting, gothic romantic style"
- `watercolor_soft`: "soft watercolor, gentle washes, delicate brushstrokes, pastoral warmth"
- `engraving_detailed`: "copper plate engraving, fine line work, ultra-detailed, etching quality"
- (Tim can add more via the webapp)

**Pre-seed the library** with 8-10 starter prompts based on the style groups from `prompt_templates.json`.

Storage: `config/prompt_library.json`

### Code Structure

```python
# src/image_generator.py

from pathlib import Path
from dataclasses import dataclass

@dataclass
class GenerationResult:
    book_number: int
    variant: int
    prompt: str
    model: str                   # Which model generated this
    image_path: Path | None
    success: bool
    error: str | None
    generation_time: float
    cost: float                  # Estimated cost for this generation

def generate_image(prompt: str, negative_prompt: str, model: str, params: dict) -> bytes:
    """Generate a single image via the specified model/provider."""
    ...

def generate_all_models(book_number: int, prompt: str, negative_prompt: str,
                        models: list[str], variants_per_model: int, output_dir: Path) -> list[GenerationResult]:
    """Fire ALL models concurrently for the same prompt. Returns results from every model."""
    ...

def generate_single_book(book_number: int, prompts_path: Path, output_dir: Path,
                         models: list[str] = None, variants: int = 5) -> list[GenerationResult]:
    """Generate variants for a single book. If models is None, use all configured models."""
    ...

def generate_batch(prompts_path: Path, output_dir: Path, resume: bool = True) -> list[GenerationResult]:
    """Generate all images from the prompts file (batch mode)."""
    ...
```

### Also Create `src/config.py`

```python
# src/config.py

from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
INPUT_DIR = PROJECT_ROOT / os.getenv("INPUT_DIR", "Input Covers")
OUTPUT_DIR = PROJECT_ROOT / os.getenv("OUTPUT_DIR", "Output Covers")
TMP_DIR = PROJECT_ROOT / "tmp"
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_DIR = PROJECT_ROOT / "config"

# AI Generation
AI_PROVIDER = os.getenv("AI_PROVIDER", "openrouter")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
FAL_API_KEY = os.getenv("FAL_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# All available models for iteration mode
ALL_MODELS = [m.strip() for m in os.getenv("ALL_MODELS",
    "flux-2-pro,flux-2-schnell,gpt-image-1-high,gpt-image-1-medium,imagen-4-ultra,imagen-4-fast,nano-banana-pro"
).split(",")]

VARIANTS_PER_COVER = int(os.getenv("VARIANTS_PER_COVER", "5"))
BATCH_CONCURRENCY = int(os.getenv("BATCH_CONCURRENCY", "1"))
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "1.0"))

# Quality
MIN_QUALITY_SCORE = float(os.getenv("MIN_QUALITY_SCORE", "0.6"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# Cost tracking
MAX_COST_USD = float(os.getenv("MAX_COST_USD", "200.00"))
```

---

## Verification Checklist

### Syntax
1. `py_compile` passes for `src/image_generator.py` — PASS/FAIL
2. `py_compile` passes for `src/config.py` — PASS/FAIL
3. `py_compile` passes for `src/prompt_library.py` — PASS/FAIL

### Prompt Library
4. Prompt library loads from `config/prompt_library.json` — PASS/FAIL
5. Library pre-seeded with 8-10 starter prompts and 5+ style anchors — PASS/FAIL
6. `build_prompt()` combines style anchors + book title correctly — PASS/FAIL
7. `save_prompt()` and `get_prompts()` round-trip correctly — PASS/FAIL

### Single Image
8. Generate 1 image for book #2 (Moby Dick), variant 1 — PASS/FAIL
9. Generated image is valid PNG, 1024×1024 — PASS/FAIL
10. Image visually depicts a whale/sea scene (manual check) — PASS/FAIL

### All-Models Mode
11. `generate_all_models()` fires all configured models concurrently — PASS/FAIL
12. Results saved with model name in path (e.g., `tmp/generated/2/flux-2-pro/variant_1.png`) — PASS/FAIL
13. Each model's results are tracked separately with cost and timing — PASS/FAIL

### Configurable Variants
14. `--variants 10` generates 10 images per model — PASS/FAIL
15. `--variants 1` generates just 1 image per model — PASS/FAIL

### Resume
16. Re-run generation for book #2 — skips existing images — PASS/FAIL
17. Progress output shows "Skipping..." for existing images — PASS/FAIL

### Error Handling
18. Set invalid API key → graceful error, logged to failures.json — PASS/FAIL
19. Generation failure doesn't abort the batch — PASS/FAIL

### Dry Run (if no API keys available)
20. `--dry-run` mode saves prompts and model assignments without generating — PASS/FAIL

---

## Notes

- **SCOPE: Build for 20 titles first (Tim's decision D23).** Do NOT test with all 99 books. Get everything working perfectly with 20, then scale later.
- Start with a SINGLE book to verify quality before running even the 20-book batch
- If no API key is available, implement a "dry run" mode that saves prompts without generating
- Generated images are intermediate — they'll be composited in Prompt 3A
- The prompt library is the KEY to scaling — invest time in making it robust
- During iteration, Tim will generate 80+ images for a single book (8 models × 10 variants) to find the best combo
