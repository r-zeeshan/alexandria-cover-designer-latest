# Codex Message for PROMPT-09A

**Paste this into the Codex chatbox. Attach the file `PROMPT-09A-PDF-COMPOSITOR.md`.**

---

## Message to paste:

Read the attached `PROMPT-09A-PDF-COMPOSITOR.md` carefully. This is a completely new approach that replaces the raster-based compositor with a PDF-based one.

### What happened
The previous raster pixel-manipulation approach (all 7+ iterations, 07A–07H) failed because detecting and reconstructing the ornamental frame boundary from a flat JPG is structurally impossible at the required fidelity. We analyzed the actual source PDF files from Google Drive and discovered that:

1. The PDFs store the ornamental frame as part of a raster image with a **soft mask (SMask)** that defines the exact frame boundary
2. The frame ring pixels and the illustration pixels are SEPARATE — distinguished by the SMask values
3. We can surgically replace just the illustration while preserving the frame pixel-for-pixel

### What to implement
1. Add `pikepdf>=10.0.0` and `PyMuPDF>=1.24.0` to `requirements.txt`
2. Create `src/pdf_compositor.py` — the new PDF-based compositor (full algorithm in the prompt)
3. Update the Drive module to also download `.pdf` files (note: PDF filenames have a trailing space before `.pdf`)
4. Update the iterate flow to prefer PDF compositing when a source PDF is available, falling back to old `cover_compositor.py` when only JPG exists
5. Generate all 3 output formats: `.pdf`, `.jpg` (rendered at 300 DPI via PyMuPDF), `.ai` (copy of PDF)

### Key technical points
- Source images are **DeviceCMYK** (4 channels) — AI art (RGB) must be converted to CMYK
- Image dimensions: **2480 × 2470** pixels
- The SMask at values 5–250 marks the ornamental frame ring — keep original pixels there
- The SMask at values >250 marks the inner circle — replace with AI art there
- The SMask at values <5 marks the outer area — replace with AI art (hidden by SMask anyway)
- Use `pikepdf` to replace the Im0 image stream while preserving the SMask reference
- Use `PyMuPDF` (fitz) to render the final PDF to JPG at 300 DPI
- After writing new Im0 data, remove `/DecodeParms` if present (simple FlateDecode, no prediction)

### DO NOT
- Do not modify the existing `cover_compositor.py` — keep it as fallback
- Do not change any vector content in the PDF (text, corners, spine ornaments)
- Do not modify the SMask — it must remain unchanged
- Do not change the Dockerfile or database schema

### MANDATORY: Verification before committing
After implementing, generate a test composite for at least 2 different books and run:
```
python scripts/verify_composite.py <output.jpg> <source_cover.jpg> --strict
```
ALL 5 checks must PASS. If any check FAILS, fix the issue and re-run. Report the full output of verify_composite.py in your response. Do NOT commit until all pass.

```
git add -A && git commit -m "PROMPT-09A: PDF-based compositor - replaces raster approach for pixel-perfect frame preservation" && git push
```
