from langgraph.graph import END, START, StateGraph

from agent.graph_state import CustomAgentState
from agent.nodes.symantic_analysis import symantic_analysis_agent
from agent.nodes.feth_schema import fetch_schema_from_vector_db
from agent.nodes.schema_coverage import schema_coverage_agent

workflow = StateGraph(CustomAgentState)

workflow.add_node("symantic_analysis", symantic_analysis_agent)
workflow.add_node("fetch_schema", fetch_schema_from_vector_db)
workflow.add_node("schema_coverage_agent", schema_coverage_agent)

workflow.add_edge(START, "symantic_analysis")
workflow.add_edge("symantic_analysis", "fetch_schema")
workflow.add_edge("fetch_schema", "schema_coverage_agent")
workflow.add_edge("schema_coverage_agent", END)

agent = workflow.compile()