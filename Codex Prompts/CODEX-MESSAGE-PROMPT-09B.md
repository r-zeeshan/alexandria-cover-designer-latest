# Codex Message for PROMPT-09B

**Paste this into the Codex chatbox. Attach the file `PROMPT-09B-VERIFICATION-SUITE.md`.**

---

## Message to paste:

Read the attached `PROMPT-09B-VERIFICATION-SUITE.md` carefully. This installs an automated visual regression test suite that MUST pass before every compositor-related commit.

### What to implement
1. Replace `scripts/verify_composite.py` with the updated version from the prompt — it now supports **two modes**:
   - **PDF mode** (preferred): uses source PDF SMask for exact frame verification, includes SMask integrity check + frame pixel preservation check (7 total checks)
   - **JPG mode** (fallback): radial zone comparison against source JPG (5 checks)
2. Create `scripts/test_compositor_integration.sh` — convenience wrapper for end-to-end testing
3. Make the shell script executable: `chmod +x scripts/test_compositor_integration.sh`

### PDF mode adds 2 critical new checks
- **SMask integrity**: verifies the output PDF's SMask is bit-identical to the source PDF's SMask (the SMask must NEVER be modified)
- **Frame pixel preservation**: verifies that CMYK pixels in the frame ring (SMask 5–250) are byte-identical between source and output Im0 raster data

### Verification thresholds
Normal mode: ornament 99.5%, art 90%, centering 5px, transition <2%
Strict mode: ornament 99.9%, art 95%, centering 3px, transition <2%

### CRITICAL RULE
After this prompt is deployed, you MUST run `scripts/verify_composite.py` (with `--strict`) before every commit that touches compositor code. If any check fails, fix the issue first. This rule is permanent and non-negotiable.

### After implementing
Test that the script runs without errors:
```
python scripts/verify_composite.py --help
```
If test fixtures exist, run a real check and report the full output.

```
git add -A && git commit -m "PROMPT-09B: Automated visual regression test suite with PDF+JPG verification modes" && git push
```
