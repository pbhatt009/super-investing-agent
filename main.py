import os
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
import uvicorn
from scripts.ingestion import load_zip
from scripts.agent import research_agent

app = FastAPI(title='AI Research Agent')
WEB_INDEX = Path(__file__).parent / 'web' / 'index.html'


@app.get('/', include_in_schema=False)
def home():
    return FileResponse(WEB_INDEX)


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.post('/research')
async def research(ticker: str = Form(...), file: UploadFile = File(...)):
    # Validate the request before reading the upload or calling the language model.
    ticker = ticker.strip().upper()
    if not ticker:
        raise HTTPException(400, 'NSE ticker is required')
    if not file.filename.lower().endswith('.zip'):
        raise HTTPException(400, 'Only ZIP files are allowed')
    if not os.getenv('GROQ_API_KEY'):
        raise HTTPException(500, 'GROQ_API_KEY is missing')

    # Ingestion keeps each Markdown file whole so it is sent to the model once.
    documents = load_zip(await file.read())
    if not documents:
        raise HTTPException(400, 'No Markdown files found')

    # LangGraph extracts evidence per document and then creates one final brief.
    result = research_agent.invoke({'ticker': ticker, 'documents': documents})
    return {
        'ticker': ticker,
        'documents_processed': len(documents),
        'brief': result['final_brief'],
    }
