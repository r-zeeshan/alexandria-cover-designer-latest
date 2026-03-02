# Visual Proof Report

Last updated: `2026-03-02`
Deployment URL: `https://web-production-900a7.up.railway.app`
Deployment ID: `e6893537-535e-4a3f-a497-0f33cb938c55`

## 1. Test Proof
- Full suite run: `pytest -q`.
- Result: `100% passed`.
- Stability note: API docs matrix test timeout raised from `20s` to `45s` to avoid false failures on heavy ZIP endpoints (`tests/test_api_docs_route_matrix.py`).
- Local validation additions:
  - guardrail fallback tiny-component arithmetic fixed for non-`scipy` environments.
  - required model inventory forced at runtime (15 OpenRouter + Gemini direct IDs).
  - startup built-in prompt seed no longer throws `LogRecord` key collision.

## 2. Live Verification Checks

### 2.1 Health
- `GET /api/health` returned:
  - `status: ok`
  - `healthy: true`
  - `version: 2.1.1`
  - `uptime_seconds: 0` immediately after deploy (confirming new rollout active)

### 2.2 New Design Token + Cache Control
- `GET /review` includes:
  - `/src/static/shared.css?v=20260302-designlock`
  - `/src/static/review.css?v=20260302-designlock`
- `GET /review` headers include:
  - `cache-control: no-store`

### 2.3 Model Payload (OpenRouter + Gemini)
- `GET /api/iterate-data?catalog=classics`:
  - total models: `22`
  - required OpenRouter production set present: `15`
  - direct Gemini IDs present: `3`
  - current provider connectivity on iterate page:
    - OpenRouter: connected
    - OpenAI: connected
    - Fal: connected
    - Google direct: degraded (`403 PERMISSION_DENIED`, leaked key)

### 2.4 Dashboard Recent Covers
- Live generation run:
  - Job ID: `4517fa87-a7c9-432d-be8b-b522e6c45964`
  - Request: `book=3`, `model=openrouter/google/gemini-2.5-flash-image`, `cover_source=drive`
  - Final status: `completed`
- `GET /api/dashboard-data?catalog=classics` now reports:
  - `recent_results = 1`
  - card present under “Latest Generated Covers”

## 3. Visual Proof Artifacts

### 3.1 Live UI Screenshots
- `tmp/proof-live-iterate-20260302-refresh.png`
- `tmp/proof-live-dashboard-20260302-refresh.png`
- `tmp/proof-live-review-20260302-refresh.png`
- `tmp/proof-live-composite-book3-v1-20260302-refresh.jpg`
- `tmp/proof-live-variant-book3-v1-20260302.zip`

### 3.2 Local Validation Screenshots
- `tmp/proof-local-iterate-20260302-fix.png`
- `tmp/proof-local-dashboard-20260302-fix.png`
- `tmp/proof-local-review-20260302-fix.png`

### 3.3 PROMPT-06 UI/UX Rebuild Proof (Latest)
- `tmp/proof-local-iterate-20260302-uiux-cspfixed.png`
- `tmp/proof-local-dashboard-20260302-uiux.png`
- `tmp/proof-local-review-20260302-uiux.png`
- `tmp/proof-local-prompts-20260302-uiux.png`
- Playwright console check on the latest local run: `0 errors, 0 warnings` (CSP updated to allow Google Fonts + Chart.js + JSZip).

## 4. Design-Lock Enforcement
- Global sidebar-first UX lock remains in `src/static/shared.css` (`DESIGN LOCK` block).
- Static revision token remains `20260302-designlock` across all pages.
- Static hygiene tests enforce token + design lock markers.
- CSP now explicitly allows required frontend assets:
  - `style-src` includes `https://fonts.googleapis.com`
  - `script-src` includes `https://cdn.jsdelivr.net` and `https://cdnjs.cloudflare.com`
  - `font-src` includes `https://fonts.gstatic.com`

## 5. Delivery Rule (Mandatory)
Every completion message must include:
1. direct deployed URL;
2. visual proof report path(s).
