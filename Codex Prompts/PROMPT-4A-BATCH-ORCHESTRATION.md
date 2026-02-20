# Prompt 4A — Batch Orchestration (End-to-End Pipeline)

**Priority**: HIGH — Ties everything together
**Scope**: `src/pipeline.py`, `scripts/run_pipeline.sh`
**Depends on**: All previous prompts (1A, 1B, 2A, 2B, 3A, 3B)
**Estimated time**: 30-45 minutes

---

## Context

Read `Project state Alexandria Cover designer.md`. All individual components exist. Now we need a single orchestrator that runs the entire pipeline end-to-end: analyze → generate → quality-check → composite → export.

---

## Task

Create `src/pipeline.py` — the master orchestrator:

1. **Incremental processing**: Track which books are done, skip completed ones on re-run
2. **Progress dashboard**: Show overall progress (e.g., `[42/99 books complete, 210/495 images]`)
3. **Error isolation**: If one book fails, continue with the rest
4. **Summary report**: At completion, generate a summary of successes/failures/quality scores
5. **Selective re-run (ESSENTIAL — Tim's decision)**: Must support re-generating specific books or specific variants without re-running the entire pipeline. E.g., `--book 2 --variant 3` regenerates only variant 3 for Moby Dick.
6. **Configurable batch size (Tim's decision)**: Support processing in configurable batches (100, 250, 500, or all). Set via `--batch-size` flag. Review point between batches.
7. **CLI interface**: `python -m src.pipeline [--books 1-10] [--book 2] [--variants 1-3] [--variant 3] [--batch-size 500] [--dry-run] [--resume]`

8. **Single-Cover Mode (ESSENTIAL — Tim's decision D19)**: This is the PRIMARY workflow initially. Tim wants to iterate on a single cover — pick a title, generate variants with different models/prompts, review the composited output, tweak, and regenerate — until the design is dialed in. Only then does batch processing begin. The pipeline must support:
   - Full end-to-end for one book: analyze → prompt → generate → quality gate → composite → export → review
   - Model selection per run: `--model openai/gpt-image-1` or `--models flux-2-pro,gpt-image-1`
   - Prompt override: `--prompt-override "custom prompt text here"` to test prompt tweaks without editing book_prompts.json
   - Side-by-side output of new variants alongside any previously generated ones
   - CLI: `python -m src.pipeline --book 2 --model openai/gpt-image-1 --variants 3`
   - CLI all-models iteration: `python -m src.pipeline --book 2 --all-models --variants 10`

9. **Prompt Library Integration (D21)**: Use prompts from the prompt library (`config/prompt_library.json`) for batch runs. The library is populated during single-cover iteration. For bulk processing:
   - `--use-library` flag selects the top-rated prompts from the library
   - `--prompt-id my_prompt_id` uses a specific saved prompt for all books
   - `--style-anchors warm_sepia_sketch,dramatic_oil` builds prompts from style anchor components
   - The library prompts are title-agnostic (contain `{title}` placeholder) so they work for any book

10. **All-Models Mode (D20)**: `--all-models` fires every configured model simultaneously. During iteration this produces N models × M variants per book. Results grouped by model in the output.

Also create `scripts/run_pipeline.sh` as a convenience wrapper.

---

## Important: Build for 20 Titles First (D23)

Do NOT build or test at 99-book scale. Focus on making everything work perfectly for 20 titles first. The pipeline must work flawlessly for single-cover iteration and a 20-book batch before we even consider scaling to 99 or 2,500.

---

## Verification Checklist

1. `py_compile` passes — PASS/FAIL
2. Dry run mode works (no API calls, shows what would be generated) — PASS/FAIL
3. Process single book (book #2) end-to-end → variants, files — PASS/FAIL
4. Resume after partial run skips completed books — PASS/FAIL
5. Process books 1-5 → variants and files — PASS/FAIL
6. Summary report generated with pass/fail counts — PASS/FAIL
7. Failed book doesn't abort the batch — PASS/FAIL
