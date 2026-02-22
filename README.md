# Background Remover Studio

Clean architecture web app using:
- Python (FastAPI)
- `rembg` for AI background removal
- Vanilla JavaScript + Tailwind CSS

## Features

1. Manual erase/restore tools (brush)
2. Selection tools (magic wand + polygon select)
3. Edge refinement (feather + alpha boost)
4. Background composer (transparent / color / gradient / image)
5. Batch processing to ZIP
6. Reliability basics (model session caching, request size limits, rate limit, controlled concurrency)

## Project Structure

```text
app/
  domain/          # Core abstractions
  application/     # Use cases + edge refinement
  infrastructure/  # rembg implementation
  presentation/    # API layer
static/
  index.html       # UI
  app.js           # Editor + tool logic
app.py             # Vercel + ASGI entry point
main.py            # Local ASGI entry point
Dockerfile
vercel.json
```

## Run Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Open: http://127.0.0.1:8000

## Deploy to Vercel

```bash
npm i -g vercel
vercel
vercel --prod
```

Configured with:
- `app.py` as entrypoint
- `vercel.json` function settings
- static assets included from `static/**`

## Run With Docker

```bash
docker build -t rmbg-web .
docker run --rm -p 8000:8000 rmbg-web
```

or

```bash
docker compose up --build
```

## API

- `POST /api/remove-bg`
  - form-data: `file`
  - returns raw PNG bytes

- `POST /api/remove-bg-refined`
  - form-data: `file`, `feather_radius` (0-8), `alpha_boost` (0.4-2.5)
  - returns raw PNG bytes

- `POST /api/remove-bg-batch`
  - form-data: `files[]`, `feather_radius`, `alpha_boost`
  - returns ZIP (`removed-backgrounds.zip`)

- `GET /api/health`
  - returns service status
