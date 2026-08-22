import json
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone

load_dotenv()

API_KEY=os.getenv("PINECONE_API_KEY")

if not API_KEY:
    raise RuntimeError("The PineCone API Key is not set")

embedding_client = OpenAIEmbeddings(model="text-embedding-3-small")

pc = Pinecone(api_key=API_KEY)

knowledge_directory = Path("./knowledge")

for file_path in knowledge_directory.rglob("*"):
    if not file_path.is_file():
        continue
    document_container = None
    with open(file_path, "r") as file:
        document_container = json.load(file)

    for doc in document_container["documents"]:
        print(doc)
        break
