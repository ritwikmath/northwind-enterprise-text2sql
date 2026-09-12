from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from agent.graph_state import CustomAgentState
from llm.structured_output.symantic_analysis import QueryIR
from prompts import get_prompt


def symantic_analysis_agent(state: CustomAgentState):
    system_prompt = get_prompt("symantic_analysis")

    model = ChatOpenAI(
        model="gpt-5.4-mini",
        temperature=0.2
    )

    current_agent = create_agent(
        model=model,
        response_format=QueryIR,
        system_prompt=system_prompt,
        
    )

    result = current_agent.invoke({"messages": state["messages"]})

    return {"symantic_analysis": result["structured_response"]}
