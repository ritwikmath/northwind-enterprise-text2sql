from dotenv import load_dotenv
from langchain.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

from agent.graph_state import CustomAgentState
from agent.nodes.symantic_analysis import symantic_analysis_agent

load_dotenv()

workflow = StateGraph(CustomAgentState)

workflow.add_node("symantic_analysis", symantic_analysis_agent)
workflow.add_edge(START, "symantic_analysis")
workflow.add_edge("symantic_analysis", END)

agent = workflow.compile()


user_message = input("Enter your message.")

messages = [
    HumanMessage(user_message)
]

result = agent.invoke({"messages": messages})

print(result["symantic_analysis"].model_dump())