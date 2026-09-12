import json

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from agent.graph_state import CustomAgentState
from prompts import get_prompt
from llm.structured_output.schema_coverage import SQLQueryIR


def schema_coverage_agent(state: CustomAgentState):
    system_prompt = PromptTemplate.from_template(get_prompt("schema_coverage"))
    formatted_prompt = system_prompt.format(
        symantic_analysis_json_string=state["symantic_analysis"].model_dump_json(),
        tables_columns=json.dumps(state["columns"], default=str)
    )

    model = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.2
    )

    current_agent = create_agent(
        model=model,
        system_prompt=formatted_prompt,
        response_format=SQLQueryIR
    )

    response = current_agent.invoke({"messages": state["messages"]})

    return {
        "schema_enough": response["structured_response"]
    }
