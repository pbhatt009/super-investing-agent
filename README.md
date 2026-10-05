# AI Research Agent

FastAPI + OpenAI + LangGraph document-to-research-brief agent.

## Setup
python -m venv venv
venv\\Scripts\\activate
pip install -r requirements.txt

Add GROQ_API_KEY to .env, then run:
uvicorn main:app --reload

Open http://127.0.0.1:8000/ for the formatted research page, or
http://127.0.0.1:8000/docs for the API explorer.

POST /research with ticker SRVCABLE and a ZIP containing Markdown documents.

The response `brief` is formatted Markdown with structured sections, evidence
references, source links, and risk callouts. Groq is accessed through its
official Python SDK using the `llama-3.1-8b-instant` model.
