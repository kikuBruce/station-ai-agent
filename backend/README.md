# AI Chat Service (FastAPI)

- Install dependencies:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

- Run server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- SSE endpoint: `POST /chat` with JSON body `{ "content": "你的问题" }`