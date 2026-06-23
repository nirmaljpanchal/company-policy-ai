import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone


def get_embeddings():
    return GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")


def get_vector_store() -> PineconeVectorStore:
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index_name = os.environ["PINECONE_INDEX_NAME"]
    embeddings = get_embeddings()
    return PineconeVectorStore(index=pc.Index(index_name), embedding=embeddings)


def add_documents(docs: list) -> None:
    vector_store = get_vector_store()
    vector_store.add_documents(docs)


def get_retriever(top_k: int = 5):
    vector_store = get_vector_store()
    return vector_store.as_retriever(search_kwargs={"k": top_k})
