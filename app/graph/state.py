from typing import TypedDict, Optional, Dict, Any

class AnalysisState(TypedDict):
    """
    Represents the state of an analysis in the graph.
    """
    file_id: str
    job_description: str
    resume_text: Optional[str]
    rewritten_jd: Optional[str]
    report: Optional[Dict[str, Any]]
    error: Optional[str]