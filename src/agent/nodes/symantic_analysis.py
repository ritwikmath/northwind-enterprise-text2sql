from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.messages import HumanMessage

from llm.structured_output.symantic_analysis import QueryIR

load_dotenv()


system_prompt_template = ""
with open("prompts/symantic_analysis.txt", "r") as file:
    system_prompt_template = file.read()

current_datetime = datetime.now(
    ZoneInfo("Asia/Kolkata")
).strftime("%Y-%m-%d %H:%M:%S %Z")

system_prompt = system_prompt_template.format(
    current_datetime=current_datetime
)

symantic_analysis_agent = create_agent(
    model='openai:gpt-4o',
    response_format=QueryIR,
    system_prompt=system_prompt
)

user_message = input("Enter your message.")

messages = [
    HumanMessage(user_message)
]

result = symantic_analysis_agent.invoke({"messages": messages})

print(result['messages'][-1].content)