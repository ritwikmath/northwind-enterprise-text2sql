from langgraph.graph import END, START, StateGraph

from agent.graph_state import CustomAgentState
from agent.nodes.check_resolved import check_resolved_agent
from agent.nodes.feth_schema import fetch_schema_from_vector_db
from agent.nodes.generate_sql import generate_sql_agent
from agent.nodes.schema_coverage import schema_coverage_agent
from agent.nodes.symantic_analysis import symantic_analysis_agent

workflow = StateGraph(CustomAgentState)

workflow.add_node("symantic_analysis", symantic_analysis_agent)
workflow.add_node("fetch_schema", fetch_schema_from_vector_db)
workflow.add_node("schema_coverage_agent", schema_coverage_agent)
workflow.add_node("check_resolved_agent", check_resolved_agent)
workflow.add_node("generate_sql_agent", generate_sql_agent)

workflow.add_edge(START, "symantic_analysis")
workflow.add_edge("symantic_analysis", "fetch_schema")
workflow.add_edge("fetch_schema", "schema_coverage_agent")
workflow.add_conditional_edges(
    "schema_coverage_agent",
    check_resolved_agent,
    {
        True: "generate_sql_agent",
        False: END
    }
)
workflow.add_edge("generate_sql_agent", END)

agent = workflow.compile()