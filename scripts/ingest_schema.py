import json
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

API_KEY=os.getenv("PINECONE_API_KEY")

if not API_KEY:
    raise RuntimeError("The PineCone API Key is not set")

embedding_client = OpenAIEmbeddings(model="text-embedding-3-large", dimensions=1024)

pc = Pinecone(api_key=API_KEY)

if not pc.has_index("texttosqlschemaindex"):
    pc.create_index(
        name="texttosqlschemaindex",
        dimension=1024,
        vector_type="dense",
        metric="dotproduct",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        )
    )

index = pc.Index("texttosqlschemaindex")

knowledge_directory = Path("./knowledge")

def get_sparse_embedding(chunk: str) -> list[int]:
    embedding = pc.inference.embed(
        model="pinecone-sparse-english-v0",
        inputs=chunk,
        parameters={"input_type": "passage", "truncate": "END"}
    )
    return embedding[0]

for file_path in knowledge_directory.rglob("*"):
    if not file_path.is_file():
        continue
    document_container = None
    with open(file_path, "r") as file:
        document_container = json.load(file)

    documents_to_insert = []
    for doc in document_container["documents"]:
        sparse_embeddings = get_sparse_embedding(doc["text"])
        documents_to_insert.append({
            "id": doc["id"],
            "values": embedding_client.embed_query(doc["text"]),
            "sparse_values": {"indices": sparse_embeddings["sparse_indices"], "values": sparse_embeddings["sparse_values"]},
            "metadata": doc
        })

    index.upsert(vectors=documents_to_insert, namespace="tableschema")

