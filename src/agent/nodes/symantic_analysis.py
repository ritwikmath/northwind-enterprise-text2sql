from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain_openai import ChatOpenAI

from llm.structured_output.symantic_analysis import QueryIR

load_dotenv()


system_prompt = ""
with open("prompts/symantic_analysis.txt", "r") as file:
    system_prompt = file.read()

current_datetime = datetime.now(
    ZoneInfo("Asia/Kolkata")
).strftime("%Y-%m-%d %H:%M:%S %Z")

model = ChatOpenAI(
    model="gpt-4o",
    temperature=0
)

symantic_analysis_agent = create_agent(
    model=model,
    response_format=QueryIR,
    system_prompt=system_prompt,
    
)

user_message = input("Enter your message.")

messages = [
    HumanMessage(user_message)
]

result = symantic_analysis_agent.invoke({"messages": messages})

print(result['messages'][-1].content)