from langchain.agents import create_agent
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from agent.graph_state import CustomAgentState
from llm.binding import resolve_against_schema
from llm.render import render_query_ir, render_schema
from llm.structured_output.schema_coverage import SQLQueryIR
from prompts import get_prompt


def schema_coverage_agent(state: CustomAgentState):
    system_prompt = PromptTemplate.from_template(get_prompt("schema_coverage"))
    formatted_prompt = system_prompt.format(
        symantic_analysis_description=render_query_ir(state["symantic_analysis"]),
        tables_columns=render_schema(state["columns"])
    )

    model = ChatOpenAI(
        model="gpt-5.4-mini",
        temperature=0.2
    )

    current_agent = create_agent(
        model=model,
        system_prompt=formatted_prompt,
        response_format=SQLQueryIR
    )

    response = current_agent.invoke({"messages": state["messages"]})
    sql_query_ir, unresolved = resolve_against_schema(
        response["structured_response"], state["columns"]
    )

    return {
        "sql_query_ir": sql_query_ir,
        "unresolved": unresolved,
        "schema_ir": not unresolved,
    }
