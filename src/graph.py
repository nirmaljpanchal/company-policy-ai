from typing import TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from src.vector_store import get_retriever


class RAGState(TypedDict):
    question: str
    chat_history: list
    retrieved_docs: list
    answer: str
    sources: list


def retrieve(state: RAGState) -> RAGState:
    retriever = get_retriever(top_k=5)
    docs = retriever.invoke(state["question"])
    return {**state, "retrieved_docs": docs}


def generate(state: RAGState) -> RAGState:
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)

    context = "\n\n".join(
        f"[Source: {doc.metadata.get('source', 'unknown')}]\n{doc.page_content}"
        for doc in state["retrieved_docs"]
    )

    history_text = ""
    for msg in state["chat_history"]:
        role = "User" if isinstance(msg, HumanMessage) else "Assistant"
        history_text += f"{role}: {msg.content}\n"

    prompt = f"""You are a helpful assistant that answers questions about company policies.
Answer ONLY using the provided context. If the answer is not in the context, say so clearly.
Always cite the source document for each piece of information you provide.

Context:
{context}

Conversation history:
{history_text}
User: {state["question"]}

Answer:"""

    response = llm.invoke([HumanMessage(content=prompt)])

    sources = list({
        doc.metadata.get("source", "unknown")
        for doc in state["retrieved_docs"]
    })

    return {**state, "answer": response.content, "sources": sources}


def build_graph():
    graph = StateGraph(RAGState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("generate", generate)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)
    return graph.compile()


rag_graph = build_graph()
