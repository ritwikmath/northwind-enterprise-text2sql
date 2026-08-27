from dotenv import load_dotenv
from langchain.messages import HumanMessage

from paths import ENV_FILE

load_dotenv(ENV_FILE)

from agent import agent

user_message = input("Enter your message.")

messages = [
    HumanMessage(user_message)
]

result = agent.invoke({"messages": messages})

print(result["symantic_analysis"].model_dump())