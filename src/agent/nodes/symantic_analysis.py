from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from agent.graph_state import CustomAgentState
from llm.structured_output.symantic_analysis import QueryIR
from paths import PROMPTS_DIR


def symantic_analysis_agent(state: CustomAgentState):
    system_prompt = ""
    with open(PROMPTS_DIR / "symantic_analysis.txt", "r") as file:
        system_prompt = file.read()

    model = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0
    )

    current_agent = create_agent(
        model=model,
        response_format=QueryIR,
        system_prompt=system_prompt,
        
    )

    result = current_agent.invoke({"messages": state["messages"]})

    return {"messages": result["messages"], "symantic_analysis": result["structured_response"]}
