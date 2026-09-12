import json

from dotenv import load_dotenv
from langchain.messages import HumanMessage
from langfuse.langchain import CallbackHandler

from paths import ENV_FILE

load_dotenv(ENV_FILE)

from agent import agent

user_message = input("Enter your message.")

messages = [
    HumanMessage(user_message)
]

langfuse_handler = CallbackHandler()

result = agent.invoke(input={"messages": messages}, config={"callbacks": [langfuse_handler]})

print(json.dumps(result, indent=4, default=str))