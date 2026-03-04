# Codex Message for PROMPT-09C

**Paste this into the Codex chatbox. Attach the file `PROMPT-09C-DOWNLOAD-NAMING.md`.**

---

## Message to paste:

Read the attached `PROMPT-09C-DOWNLOAD-NAMING.md` carefully. This updates the download naming and ZIP structure to match source cover naming exactly, and adds PDF/AI files to the download ZIP.

### What to implement
1. Update `resolveBookMetadataForJob()` in `src/static/js/pages/iterate.js` to use `file_base` from the book catalog when available (instead of constructing from title + author)
2. Update the `downloadComposite` method to:
   - Use folder structure inside the ZIP: `{number}. {baseName}/`
   - Include `.pdf` and `.ai` output files in the ZIP when available (from the PDF compositor in 09A)
3. Update the `downloadGenerated` (Raw) button to prefix the number: `{number}. {baseName} (illustration).jpg`

### Key points
- The `file_base` field is already in the frontend DB from the catalog sync
- PDF and AI URLs may be available as `job.composite_pdf_url` / `job.pdf_url` and `job.composite_ai_url` / `job.ai_url`
- If PDF/AI files aren't available (JPG-only fallback compositor), the ZIP just contains the JPG files as before
- The ZIP folder structure mirrors the source cover folder naming convention

### How to verify
1. Sync the catalog
2. Generate a cover for any book
3. Click Download — check that the ZIP name is `{number}. {file_base}.zip`
4. Extract — verify folder + file naming matches the expected pattern in the prompt
5. Click Raw — verify filename is `{number}. {file_base} (illustration).jpg`

```
git add -A && git commit -m "PROMPT-09C: Download naming matches source covers + PDF/AI in ZIP" && git push
```
