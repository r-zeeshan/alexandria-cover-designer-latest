# Prompt 2B — Quality Gate (Scoring + Filtering)

**Priority**: MEDIUM — Ensures only good images proceed
**Scope**: `src/quality_gate.py`
**Depends on**: Prompt 2A (generated images must exist)
**Estimated time**: 30-45 minutes

---

## Context

Read `Project state Alexandria Cover designer.md`. After Prompt 2A, we have ~495 generated images in `tmp/generated/`. Some may be low quality (artifacts, wrong content, blank images, etc.). We need an automated quality gate to score and filter before compositing.

---

## Task

Create `src/quality_gate.py` with automated quality checks:

1. **Technical Quality**: Resolution, aspect ratio, no blank/solid images, no extreme noise
2. **Color Compatibility**: The illustration should have warm tones compatible with the navy/gold cover palette
3. **AI Artifact Detection**: Flag images with common AI artifacts (text-like patterns, distorted features)
4. **Diversity Check**: Ensure the 5 variants for each book are sufficiently different from each other
5. **Scoring**: Aggregate score 0-1, with configurable threshold (default 0.7)

### Retry Strategy (Tim's decision: same model, tweaked prompt)
- When an image fails the quality gate, re-generate using the **same model** with a **tweaked prompt**
- Tweaks: add/adjust style words, modify composition guidance, adjust negative prompt emphasis
- Max 3 retries per image. After 3 failures, flag for manual review (do NOT switch to a different model)
- Log all retries with the original and tweaked prompts for analysis

6. **Multi-Model Ranking (D20)**: When all models generate for the same prompt, rank results across models:
   - Score all outputs for the same book/prompt across every model
   - Rank by quality score, grouped by model
   - Generate a "model leaderboard" per book showing which model scored highest
   - This helps Tim identify the best models during iteration

### Output
- `data/quality_scores.json`: Per-image scores and pass/fail (includes model name for each)
- `data/quality_report.md`: Human-readable summary with model leaderboard
- `data/retry_log.json`: All retried images with original/tweaked prompts
- `data/model_rankings.json`: Aggregated quality scores per model across all evaluated images
- Images below threshold after 3 retries flagged for manual review

---

## Verification Checklist

1. `py_compile` passes — PASS/FAIL
2. Score a known-good generated image → score ≥ 0.7 — PASS/FAIL
3. Score a blank/solid-color test image → score < 0.3 — PASS/FAIL
4. Score all images for one book (5 variants) → report generated — PASS/FAIL
5. Diversity check flags 5 identical images as "not diverse" — PASS/FAIL
6. `data/quality_scores.json` is valid JSON with all entries — PASS/FAIL
7. `data/quality_report.md` is readable and accurate — PASS/FAIL
