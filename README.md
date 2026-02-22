# Python Background Remover Web App

Clean architecture web app using:
- Python (FastAPI)
- `rembg` for background removal
- Vanilla JavaScript
- Tailwind CSS

## Project Structure

```text
app/
  domain/          # Core abstractions
  application/     # Use cases
  infrastructure/  # External implementations (rembg)
  presentation/    # API layer
static/
  index.html       # Tailwind UI
  app.js           # Vanilla JS client logic
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

Prerequisites:
- Vercel account
- Vercel CLI installed (`npm i -g vercel`)

Deploy:

```bash
vercel
```

Production deploy:

```bash
vercel --prod
```

This repo is configured for Vercel with:
- `app.py` as FastAPI entrypoint
- `vercel.json` function settings
- static assets included from `static/**`

## Run With Docker

Build and run with Docker:

```bash
docker build -t rmbg-web .
docker run --rm -p 8000:8000 rmbg-web
```

Or with Docker Compose:

```bash
docker compose up --build
```

Open: http://127.0.0.1:8000

## API

- `POST /api/remove-bg`
  - form-data: `file` (image)
  - returns: PNG bytes
