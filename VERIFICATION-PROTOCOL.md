# Compositor Verification Protocol — MANDATORY

**This protocol is NON-NEGOTIABLE. Every compositor change must pass verification before committing.**

Both Claude Cowork and Codex MUST follow this protocol. No exceptions.

---

## The Problem This Solves

Neither Claude Cowork nor Codex can visually inspect composited cover output. Previous attempts (07A through 07H) were "correct" according to code review but failed when visually inspected by Tim. This protocol replaces human visual inspection with automated pixel-level verification.

---

## The Verification Script

**File:** `scripts/verify_composite.py`

**Usage:**
```bash
python scripts/verify_composite.py <composited_output.jpg> <source_cover.jpg>
```

**Exit codes:**
- `0` = ALL CHECKS PASSED — safe to commit
- `1` = ONE OR MORE CHECKS FAILED — DO NOT commit, fix the issue
- `2` = ERROR (missing files, wrong dimensions)

---

## What It Checks

### 1. Dimensions
Output must be 3784x2777 (matching source cover).

### 2. Ornament Zone (r > 480px from center)
Frame pixels must be **pixel-identical** to the source cover (within JPEG tolerance of 2 per channel). Threshold: 99.5% match.

**Why:** If ornament pixels differ, the compositor is damaging the frame.

### 3. Art Zone (r < 370px from center)
Pixels must **differ** from the source cover. Threshold: 90% different.

**Why:** If art zone pixels match the source, the original illustration is still showing through — the AI art was not properly composited.

### 4. Centering
The center of mass of art pixels must be within 5px of (2864, 1620).

**Why:** Off-center art is the most common visual bug.

### 5. Transition Quality
The transition zone (370-480px) must have less than 2% harsh gradient pixels.

**Why:** Artifacts at the frame/art boundary are visible at print quality.

---

## When to Run

### For Codex:
1. After ANY change to `src/cover_compositor.py`
2. After ANY change to `scripts/generate_frame_mask.py` or `config/frame_mask.png`
3. Before EVERY `git commit` that touches compositor code

**How Codex runs it:**
```bash
# Generate a test composite
python -c "
from src.cover_compositor import composite_single
from pathlib import Path
composite_single(
    cover_path=Path('config/covers/cover_001.jpg'),
    illustration_path=Path('test_fixtures/sample_illustration.png'),
    region={'region_type': 'circle'},
    output_path=Path('tmp/test_composite.jpg'),
)
"

# Verify it
python scripts/verify_composite.py tmp/test_composite.jpg config/covers/cover_001.jpg
```

If exit code is not 0, DO NOT commit. Fix the issue and re-run.

### For Claude Cowork:
1. When reviewing Codex's compositor changes, ask: "Did verify_composite.py pass?"
2. If Codex didn't run it, instruct Codex to run it before accepting the change
3. When writing compositor prompts, always include: "Run `python scripts/verify_composite.py` and report results before committing"

---

## Adding to Every Compositor Prompt

Every Codex prompt that touches the compositor MUST include this block at the end:

```
## MANDATORY: Run Verification Before Committing

After making changes, generate a test composite and verify:

    python scripts/verify_composite.py <output.jpg> <source_cover.jpg>

All 5 checks must PASS. If any check FAILS, do not commit.
Report the full output of verify_composite.py in your response.
```

---

## Strict Mode

For critical compositor changes, use strict mode:
```bash
python scripts/verify_composite.py output.jpg source.jpg --strict
```

Strict thresholds:
- Ornament match: 99.9% (instead of 99.5%)
- Art differ: 95% (instead of 90%)
- Centering tolerance: 3px (instead of 5px)

---

## Known Geometry Reference

| Parameter | Value | Notes |
|-----------|-------|-------|
| Cover size | 3784 x 2777 | All 99 covers |
| Medallion center | (2864, 1620) | 99 covers identical, 1 differs by 2px |
| Outer frame radius | 500 | Gold border outer edge |
| Frame inner edge | 378-480px | Varies by angle (irregular scrollwork) |
| Art zone | r < 370px | Always clear of frame |
| Ornament zone | r > 480px | Always frame |
| Transition | 370-480px | Scrollwork, beads, detail |
