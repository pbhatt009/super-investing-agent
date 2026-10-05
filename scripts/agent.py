import json
import os
import re

from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph
from openai import OpenAI

from scripts.models import ResearchState

load_dotenv()

client = OpenAI(
    api_key=os.getenv('GROQ_API_KEY'),
    base_url='https://api.groq.com/openai/v1',
)
MODEL1 ="openai/gpt-oss-120b"
MODEL2 = "openai/gpt-oss-20b"
SYSTEM = '''You are an AI equity research assistant. Use ONLY the supplied documents.
Never browse or use outside knowledge. Never invent facts, numbers, dates, results,
company identities, or financial metrics. Do not give buy/sell recommendations.
Every factual claim in the final brief must have a numbered source citation.'''


def parse_json_response(response):
    cleaned = response.strip()
    cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', cleaned, flags=re.IGNORECASE)
    return json.loads(cleaned)



def ask(prompt, model):
    response = client.responses.create(
        input=SYSTEM + '\n\n' + prompt,
        model=model,
    )
    return response.output_text


def extract_evidence(state):
    evidence = []
    for document in state['documents']:
        response = ask(f'''Read this entire Markdown document once and extract every
useful fact relevant to an NSE stock research brief. Do not discard facts because
the user ticker is not explicitly written; flag identity uncertainty instead.
Return valid JSON only with these arrays:
snapshot, bull_case, bear_case, open_questions.
Each factual item must contain claim, source_name, url, published.
Use the supplied metadata when present. If a category has no evidence, use [].

USER TICKER: {state["ticker"]}
FILE: {document["file"]}
SOURCE NAME: {document["source"]}
URL: {document["url"]}
PUBLISHED: {document["published"]}
TYPE: {document["type"]}

FULL DOCUMENT:
{document["text"]}'''
,MODEL1)
        try:
            extracted = parse_json_response(response)
        except (TypeError, json.JSONDecodeError):
            extracted = {
                'snapshot': [],
                'bull_case': [],
                'bear_case': [],
                'open_questions': [{
                    'claim': 'Evidence extraction failed; review the original document directly.',
                    'source_name': document['source'] or document['file'],
                    'url': document['url'],
                    'published': document['published'],
                }],
            }
        extracted['_file'] = document['file']
        evidence.append(extracted)
    state['evidence'] = evidence
    return state


def finalise(state):
    state['final_brief'] = ask(f'''Create a short, polished Markdown research brief
for NSE ticker {state["ticker"]} using ONLY the merged evidence below.
This is written for a retail investor and should be about one page.

Use exactly these sections, in this order:
# {state["ticker"]} - Research Brief
## Snapshot
## Bull case
## Bear case
## Open questions
## Sources

Requirements:
- Snapshot must be 3-4 concise lines covering what the company does and its latest results.
- Use short bullets and simple language; do not use an Executive summary section.
- Every factual bullet must end with one or more citations like [1] or [2].
- Do not claim that information is unavailable if the evidence contains a relevant fact.
- If the document names a company but ticker identity is not confirmed, state that clearly in Open questions while still using the evidence.
- Put missing, uncertain, or conflicting information in Open questions.
- Sources must list every source name and URL used, with matching numbers.
- Do not use raw JSON, code fences, or unsupported facts.
- End Sources with: "This is an evidence summary, not investment advice."

MERGED EVIDENCE:
{json.dumps(state["evidence"], ensure_ascii=False)}''',
MODEL2

)
    return state


def build_graph():
    graph = StateGraph(ResearchState)
    graph.add_node('extract_evidence', extract_evidence)
    graph.add_node('finalise', finalise)
    graph.add_edge(START, 'extract_evidence')
    graph.add_edge('extract_evidence', 'finalise')
    graph.add_edge('finalise', END)
    return graph.compile()


research_agent = build_graph()
