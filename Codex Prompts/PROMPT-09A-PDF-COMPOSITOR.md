# PROMPT-09A: PDF-Based Cover Compositor

> **Priority**: P0 — Critical  
> **Repo**: `ltvspot/alexandria-cover-designer` (branch: `master`)  
> **Depends on**: Current codebase  
> **What**: Replace the entire raster-based compositor with a PDF-based compositor that edits source PDFs directly, with mandatory automated verification before every commit

---

## Background & Problem

The current `cover_compositor.py` uses raster pixel manipulation on flat JPGs to:
1. Detect the medallion opening via edge/gradient analysis
2. Punch out the medallion center
3. Paste the AI-generated art
4. Re-apply a ring mask to approximate the ornamental frame

**This approach has failed through 7+ iterations (07A–07H)** because:
- The ornamental frame ring has semi-transparent edges, sub-pixel detail, and irregular boundaries
- Raster-level detection of the frame boundary is inherently imprecise
- No mask can perfectly separate "frame pixels" from "illustration pixels" in a flat JPG

## The Discovery

**The source PDF/AI files for every cover have a fundamentally different structure than the JPGs.** Analysis of the actual PDF files from Google Drive reveals:

### PDF Internal Structure
Each source cover PDF (and its .ai counterpart, which is the same file format) contains:

1. **Vector content stream** (~4500 lines of PDF operators):
   - Background fill (navy blue rectangle)
   - All text (title, author, subtitle, back cover description, spine text)
   - Corner ornamental flourishes (vector paths with gold fill)
   - Spine decorations (vector paths)
   
2. **One raster image** (`Im0`, xref 19):
   - Size: **2480 × 2470 pixels**, CMYK colorspace, 8 bits/component
   - Contains the **complete medallion artwork**: ornamental frame ring + illustration scene
   - Compressed with FlateDecode (zlib)
   
3. **One soft mask** (`SMask`, xref 24):
   - Size: **2480 × 2470 pixels**, Grayscale
   - Defines where `Im0` is visible on the page
   - **White (>250)** = fully opaque = inner circle where illustration shows
   - **Black (<5)** = fully transparent = outer area (hidden by page background)
   - **Gray (5–250)** = semi-transparent = **the ornamental frame ring itself**
   - This mask IS the exact boundary information from the original designer

4. **Image placement** in the content stream:
   - Position: x=526.134, y=107.627 (PDF points from bottom-left)
   - Transform: `323.15 × 321.85` points = ~1346 × 1341 pixels at 300 DPI
   - Center: approximately (2865, 1657) in full-page pixel coordinates
   - The image is clipped to a rectangle and rendered with SMask transparency

### Key Insight
The ornamental frame is preserved PIXEL-PERFECTLY in the raster image. The SMask provides **sub-pixel-accurate** transparency blending from the original designer. We don't need to detect, approximate, or reconstruct anything — we just need to replace the illustration pixels while keeping the frame pixels.

## New Approach: PDF Image Replacement

### Algorithm

For each cover composite:

1. **Download the source PDF** from Google Drive (same folder as JPG, same base name + `.pdf`)
2. **Open the PDF** with `pikepdf`
3. **Extract the raster image** (`Im0`) — decompress the CMYK data into a numpy array (h × w × 4)
4. **Extract the soft mask** (`SMask`) — decompress into a numpy array (h × w)
5. **Generate or load the AI art** at the same dimensions (2480 × 2470) in CMYK
6. **Composite**:
   ```python
   # SMask values:
   # > 250 → inner circle (fully visible) → use AI art
   # < 5   → outer area (fully hidden) → use AI art (won't be visible anyway)
   # 5-250 → ornamental frame ring → keep ORIGINAL pixels
   
   composite = ai_art_cmyk.copy()
   frame_ring_mask = (smask >= 5) & (smask <= 250)
   composite[frame_ring_mask] = original_cmyk[frame_ring_mask]
   ```
7. **Replace `Im0`** in the PDF with the compressed composite data
8. **Keep `SMask` unchanged** — it already defines the perfect boundary
9. **Save as PDF** → render as JPG for the web app

### Critical Technical Details

#### Image colorspace
- Source images are **DeviceCMYK** (4 channels: C, M, Y, K)
- AI-generated images come as **RGB** — must convert to CMYK before compositing
- Use this conversion:
  ```python
  def rgb_to_cmyk(rgb_array):
      """Convert RGB numpy array (h,w,3) uint8 to CMYK (h,w,4) uint8."""
      r, g, b = rgb_array[:,:,0].astype(float), rgb_array[:,:,1].astype(float), rgb_array[:,:,2].astype(float)
      c = 255 - r
      m = 255 - g
      y = 255 - b
      k = np.minimum(np.minimum(c, m), y)
      safe = k < 255
      c_out = np.zeros_like(c, dtype=np.uint8)
      m_out = np.zeros_like(m, dtype=np.uint8)
      y_out = np.zeros_like(y, dtype=np.uint8)
      k_out = k.astype(np.uint8)
      c_out[safe] = ((c[safe] - k[safe]) / (255 - k[safe]) * 255).astype(np.uint8)
      m_out[safe] = ((m[safe] - k[safe]) / (255 - k[safe]) * 255).astype(np.uint8)
      y_out[safe] = ((y[safe] - k[safe]) / (255 - k[safe]) * 255).astype(np.uint8)
      return np.stack([c_out, m_out, y_out, k_out], axis=-1)
  ```

#### pikepdf usage
```python
import pikepdf
import zlib
import numpy as np

pdf = pikepdf.Pdf.open("source.pdf")
page = pdf.pages[0]
xobjects = page.get("/Resources").get("/XObject")
im0 = xobjects["/Im0"]

# Extract original CMYK data
w = int(im0.get("/Width"))
h = int(im0.get("/Height"))
raw = zlib.decompress(bytes(im0.read_raw_bytes()))
cmyk = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 4)

# Extract SMask
smask_obj = im0.get("/SMask")
smask_raw = zlib.decompress(bytes(smask_obj.read_raw_bytes()))
smask = np.frombuffer(smask_raw, dtype=np.uint8).reshape(h, w)

# ... composite as described above ...

# Replace image data
compressed = zlib.compress(composite.tobytes())
smask_ref = im0.get("/SMask")  # Save reference
im0.write(compressed, filter=pikepdf.Name("/FlateDecode"))
im0["/SMask"] = smask_ref  # Restore SMask reference
if "/DecodeParms" in im0:
    del im0["/DecodeParms"]  # Remove prediction params (simple deflate now)

pdf.save("output.pdf")
```

#### AI art sizing
- The embedded image is **2480 × 2470** pixels
- AI art must be generated at this exact size, or resized to fit
- The art should fill the ENTIRE 2480 × 2470 canvas (not just the inner circle)
- The SMask handles hiding the outer edges — no need for circular cropping
- Making the art slightly larger than the visible area ensures no gaps at the frame boundary

#### Downloading source PDFs from Google Drive
Each book folder in Drive contains 3 files:
- `{Book Title} — {Author}.jpg` (current source, ~5MB)
- `{Book Title} — {Author} .pdf` (source PDF, ~30MB, **note the space before .pdf**)
- `{Book Title} — {Author}.ai` (same as PDF, ~30MB)

To find the PDF: list the folder contents, find the file with `.pdf` extension, download via `files.get` with `alt=media`.

**IMPORTANT**: The PDF filename has a **trailing space** before `.pdf` — e.g., `"Fairy Tales... .pdf"` not `"Fairy Tales....pdf"`. Handle this when searching/matching filenames.

### Required Dependencies
Add to `requirements.txt`:
```
pikepdf>=10.0.0
PyMuPDF>=1.24.0
```
`numpy` and `Pillow` are already present.

### Changes to Make

#### 1. New file: `src/pdf_compositor.py`
The new PDF-based compositor. Core function:

```python
def composite_cover_pdf(
    source_pdf_path: str,
    ai_art_path: str,
    output_pdf_path: str,
    output_jpg_path: str,
) -> dict:
    """Replace the illustration in a source PDF with AI-generated art.
    
    Args:
        source_pdf_path: Path to the original cover PDF from Google Drive
        ai_art_path: Path to the AI-generated illustration (RGB, any size)
        output_pdf_path: Where to save the modified PDF
        output_jpg_path: Where to save the rendered JPG
        
    Returns:
        dict with keys: success, center_x, center_y, image_width, image_height
    """
```

#### 2. Update `src/drive.js` (or equivalent)
Add ability to download `.pdf` files from Google Drive in addition to `.jpg`:
- When fetching a cover, also check for and download the `.pdf` version
- Store the PDF alongside the JPG in the local cache
- The PDF is ~30MB per cover — consider streaming/chunked downloads

#### 3. Update the iterate flow
When compositing:
1. If source PDF is available → use `pdf_compositor.py` (new approach)
2. If only JPG is available → fall back to old `cover_compositor.py` (existing approach)

#### 4. Update output generation
After compositing via PDF:
- Save the modified PDF as the `.pdf` output
- Render the PDF to JPG at 300 DPI for the `.jpg` output
- The `.ai` output can be the same as the PDF (rename extension — .ai IS a PDF)

### Rendering PDF to JPG
```python
import fitz  # PyMuPDF

doc = fitz.open("output.pdf")
page = doc[0]
mat = fitz.Matrix(300/72, 300/72)  # 300 DPI
pix = page.get_pixmap(matrix=mat)
pix.save("output.jpg")
doc.close()
```

## File Outputs

The compositor should produce three output files per cover:
1. **`.pdf`** — The modified PDF with replaced illustration
2. **`.jpg`** — High-quality render of the PDF at 300 DPI
3. **`.ai`** — Copy of the PDF with .ai extension (for Illustrator compatibility)

All three use the same naming convention as the source files.

---

## MANDATORY: Run Verification Before Committing

**This is NON-NEGOTIABLE. Do not skip this step under any circumstances.**

After implementing the PDF compositor, you MUST:

1. Generate a test composite for at least 2 different books
2. Run the automated verification suite on each output:
   ```bash
   python scripts/verify_composite.py <output.jpg> <source_cover.jpg> --strict
   ```
3. ALL 5 checks must PASS:
   - Dimensions (3784 × 2777)
   - Ornament zone pixel-identity (99.9% in strict mode)
   - Art zone pixel-difference (95% in strict mode)
   - Centering (within 3px of medallion center in strict mode)
   - Transition quality (<2% harsh pixels)
4. Report the full output of `verify_composite.py` in your response
5. If any check FAILS, fix the issue and re-run verification. Do NOT commit until all pass.

```
git add -A && git commit -m "PROMPT-09A: PDF-based compositor replacing raster approach with mandatory verification" && git push
```

---

## Summary

This approach works at the **PDF object level** rather than the pixel level. Instead of trying to detect and approximate the ornamental frame boundary in a flat JPG, we:

1. Open the source PDF (which preserves the original layer structure)
2. Extract the exact frame pixels and transparency mask from the designer's original file
3. Composite: AI art base + original frame overlay (using the exact SMask boundary)
4. Write the result back into the PDF

The ornamental frame is preserved **pixel-for-pixel** from the original. The SMask provides **sub-pixel-accurate** transparency. The vector content (text, corners, spine) is completely untouched. This makes the boundary problem *structurally impossible* — there is no edge detection, no approximation, and no reconstruction.
