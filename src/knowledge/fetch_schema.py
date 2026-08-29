import os

from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone, EmbeddingsList

from database import get_vector_db_instance


def __convert_text_to_vector_embedding(texts: list[str]) -> list[list[int]]:
    client = OpenAIEmbeddings(model=os.getenv("EMBEDDING_MODEL_NAME"), dimensions=1024)
    embeddings = client.embed_documents(texts=texts)
    return embeddings

def __convert_text_to_sparse_embedding(texts: list[str]) -> EmbeddingsList:
    if not (api_key := os.getenv("PINECONE_API_KEY")):
        raise RuntimeError("Pinecone API Key is not set")
    pc = Pinecone(api_key=api_key)
    sparse_embeddings = pc.inference.embed(
        model="pinecone-sparse-english-v0",
        inputs=texts,
        parameters={"input_type": "query", "truncate": "END"}
    )
    return sparse_embeddings

def fetch_columns_tables_from_vectord_db(fields: list[str]) -> int:
    vector_embeddings = __convert_text_to_vector_embedding(fields)
    sparse_embeddings = __convert_text_to_sparse_embedding(fields)
    index = get_vector_db_instance().Index(os.getenv("SCHEMA_INDEX_NAME"))
    matches = {}
    for d, s in zip(vector_embeddings, sparse_embeddings):
        response = index.query(
            namespace="tableschema",
            top_k=2,
            vector=[value * 0.7 for value in d],
            sparse_vector={'indices': s['sparse_indices'], 'values': [value * 0.3 for value in s['sparse_values']]},
            include_values=False,
            include_metadata=True
        )
        for match in response["matches"]:
            print(f"{match['id']}:{match['score']}")
            # if match['score'] >= 4.0:
            matches[match["id"]] = match["metadata"]
    return list(matches.values())