import os

from pinecone import Pinecone


def get_vector_db_instance() -> Pinecone:
    if not (api_key := os.getenv("PINECONE_API_KEY")):
        raise RuntimeError("Pinecone API Key is not set")
    pc = Pinecone(api_key=api_key)
    return pc
