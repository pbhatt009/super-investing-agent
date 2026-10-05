# AI Research Agent Architecture

## 1. System overview

This project is a FastAPI service that accepts an NSE ticker and a ZIP file of
Markdown research documents. It reads each Markdown document as a whole, sends only
that supplied content to Groq, and uses a two-stage LangGraph workflow to produce a
source-aware research brief.

The application deliberately does not browse the web or make buy/sell
recommendations. The language-model prompt requires factual claims to remain
traceable to the uploaded documents.

The browser page at `/` renders the Markdown brief as a styled report. The
JSON API remains available at `/research` for programmatic clients.

## 2. High-level architecture

```text
Client
  |
  | POST /research
  | ticker + ZIP of Markdown files
  v
FastAPI application (main.py)
  |
  | validate ZIP and GROQ_API_KEY
  v
Document ingestion (scripts/ingestion.py)
  |
  | parse optional front matter
  | preserve each Markdown file as one document
  v
ResearchState (scripts/models.py)
  |
  v
LangGraph workflow (scripts/agent.py)
  |
  +--> Extract evidence once per Markdown document
  +--> Merge all extracted evidence
  +--> Create final one-page brief
  |
  v
Groq OpenAI-compatible API
  model: openai/gpt-oss-20b
  |
  v
JSON response
  ticker
  documents_processed
  brief
```

## 3. Components

### `main.py`

Application entry point and HTTP API:

- `GET /health` returns service status.
- `POST /research` accepts:
  - `ticker`: form field containing the requested NSE ticker. It is trimmed and
    normalized to uppercase.
  - `file`: ZIP upload containing Markdown files.
- Validates the file extension and `GROQ_API_KEY`.
- Invokes the compiled LangGraph workflow.
- Returns the final brief and basic processing metadata.

Run the service with:

```powershell
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload
```

Open the Swagger UI at:

```text
http://127.0.0.1:8000/docs
```

### `scripts/ingestion.py`

The ingestion layer:

1. Reads the uploaded ZIP in memory.
2. Selects files whose names end with `.md`.
3. Reads optional front matter between `---` markers.
4. Preserves `source`, `url`, `published`, and `type` metadata.
5. Preserves the complete Markdown document so it is sent to the model once.

Each document has the following shape:

```python
{
    "file": "research.md",
    "text": "...",
    "source": "...",
    "url": "...",
    "published": "...",
    "type": "..."
}
```

### `scripts/models.py`

`ResearchState` is the shared LangGraph state. It carries the ticker, source
chunks, extracted evidence, draft, critique, conflict analysis, iteration
count, and final brief.

### `scripts/agent.py`

This module configures the Groq client through the OpenAI-compatible SDK:

```python
OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
```

The model is configured as `openai/gpt-oss-20b`.

The system prompt instructs the model to:

- Use only uploaded documents.
- Avoid invented facts, dates, numbers, and financial results.
- Identify conflicts between sources.
- Keep claims traceable.
- Avoid buy/sell recommendations.

## 4. LangGraph workflow

```text
START
  |
  v
extract_evidence (one call per Markdown file)
  |
  v
finalise (one call over merged evidence)
  |
  v
 END
```

### Workflow steps

1. **Extract evidence**: processes each complete Markdown document once and requests JSON
   containing snapshot, bull-case, bear-case, and open-question evidence.
2. **Finalise**: merges all extracted evidence and creates the final one-page Markdown brief with Snapshot, Bull
   case, Bear case, Open questions, and Sources sections.

## 5. Configuration

Create a `.env` file in the project root:

```text
GROQ_API_KEY=your_groq_api_key
```

Never commit `.env` or expose the API key in source control, logs, screenshots,
or client-side code.

Install dependencies:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 6. API examples

Health check:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health
```

Research request:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/research" `
  -F "ticker=SRVCABLE" `
  -F "file=@documents.zip"
```

Example response shape:

```json
{
  "ticker": "SRVCABLE",
  "documents_chunks": 4,
  "iterations": 3,
  "brief": "## Snapshot\n..."
}
```

## 7. Error behavior

- Non-ZIP uploads return HTTP 400.
- ZIP files without Markdown files return HTTP 400.
- Missing `GROQ_API_KEY` returns HTTP 500.
- Invalid or unreadable ZIP content is rejected by the ingestion layer.

## 8. Operational notes

- `0.0.0.0` is used only as the server bind address. Use
  `127.0.0.1` or `localhost` in a browser.
- The current implementation processes chunks sequentially, so large ZIP files
  may require multiple Groq requests and take longer to complete.
- The model output is treated as application content; callers should still
  review the cited evidence before relying on the brief.
