# Alexandria Cover Designer

AI-powered book cover illustration generator for 25,000+ classic manuscripts.

## Quick Start

```bash
pip install -r requirements.txt
python -m src.pipeline
```

## Production

- Live app: https://web-production-900a7.up.railway.app/#iterate
- Deploy: push to `master` and Railway deploys the `web` service

## Key Files

| File | Purpose |
|------|---------|
| `src/image_generator.py` | Backend prompt assembly and AI provider calls |
| `src/static/js/pages/iterate.js` | Frontend variant, scene, and style logic |
| `src/static/js/style-diversifier.js` | Style pool and diversified prompts |
| `config/prompt_library.json` | Base and wildcard prompt templates |
| `src/cover_compositor.py` | Circular crop and frame overlay pipeline |
| `scripts/regression_check.py` | Regression guardian; run before every deploy |

## Before Every Deploy

```bash
python scripts/regression_check.py
python scripts/regression_check.py --prod https://web-production-900a7.up.railway.app
```

Both commands must show 0 failures before deploying.

## Architecture

See `Codex Prompts/ARCHITECTURE-GUARDRAILS.md` for ownership rules and banned patterns.
