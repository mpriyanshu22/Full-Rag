from langgraph.graph import StateGraph, START, END
from .state import AnalysisState
from .nodes import fetch_resume_node, rewrite_jd_node, generate_report_node


def build_graph():
    workflow = StateGraph(AnalysisState)
    
    # ADD nodes
    workflow.add_node("fetch_resume", fetch_resume_node)
    workflow.add_node("rewrite_jd", rewrite_jd_node)
    workflow.add_node("generate_report", generate_report_node)
    
    # Add sequential edges
    workflow.add_edge(START,"fetch_resume")
    workflow.add_edge("fetch_resume","rewrite_jd")
    workflow.add_edge("rewrite_jd","generate_report")
    workflow.add_edge("generate_report",END)
    
    return workflow.compile()

resume_analysis_graph = build_graph()

    
    