# Autonomous Financial Advisor Chat Agent

<img width="1219" height="703" alt="Screenshot 2026-05-10 at 1 18 43 AM" src="https://github.com/user-attachments/assets/45a1b9ee-aef9-44ba-bdc6-82f82233a5eb" />

## Run The Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
.venv/bin/uvicorn backend.app.main:app --reload --port 8000
```

## Run The Frontend

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

Open:

```bash
http://localhost:3000
```

The frontend calls `http://localhost:8000` by default. To override:

```bash
NEXT_PUBLIC_API_URL=http://localhost:{PORT} npm --prefix frontend run dev
```

## Optional Environment Variables

```bash
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_OUTPUT_TOKENS=220
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_BASE_URL=
LANGFUSE_ENABLED=true
LANGFUSE_FLUSH_ON_REQUEST=true
LOG_LEVEL=INFO
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Backend logs are emitted as structured JSON to stdout.
