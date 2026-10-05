from typing import TypedDict, List, Dict, Any
class ResearchState(TypedDict, total=False):
    ticker: str
    documents: List[Dict[str, Any]]
    evidence: List[Dict[str, Any]]
    final_brief: str
