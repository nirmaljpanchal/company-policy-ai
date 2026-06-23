from dataclasses import asdict, dataclass, field
from typing import Optional
from uuid import UUID

from langgraph.graph import START, END, StateGraph
from openai import OpenAI
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.user import User
from app.rag.retriever import retrieve, get_allowed_departments
from app.security.injection import screen_input
from app.security.moderation import check_input
from app.security.prompt import build_messages


@dataclass
class RAGState:
    question: str
    chat_history: list[dict]
    user: User
    allowed_departments: Optional[list[str]]
    retrieved_docs: list[dict] = field(default_factory=list)
    answer: str = ""
    sources: list[str] = field(default_factory=list)
    blocked: bool = False
    block_reason: str = ""


class RAGGraph:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key)
        self.graph = self._create_graph()

    def _guard_node(self, state: RAGState) -> RAGState:
        """Screen input for injection and moderation."""
        injection_result = screen_input(state.question)
        if injection_result.blocked:
            state.blocked = True
            state.block_reason = f"Injection detected: {injection_result.reason}"
            return state

        mod_result = check_input(state.question)
        if mod_result.flagged:
            state.blocked = True
            state.block_reason = f"Input flagged by moderation: {', '.join(mod_result.categories)}"
            return state

        return state

    def _retrieve_node(self, state: RAGState) -> RAGState:
        """Embed question and retrieve chunks."""
        if state.blocked:
            return state

        embed_response = self.client.embeddings.create(
            model=self.settings.openai_embed_model,
            input=state.question
        )
        query_embedding = embed_response.data[0].embedding

        chunks = retrieve(
            self.db,
            query_embedding,
            allowed_departments=state.allowed_departments,
            top_k=5
        )

        state.retrieved_docs = [
            {
                "content": c.content,
                "source": c.source,
                "similarity_score": c.similarity_score
            }
            for c in chunks
        ]

        state.sources = list(dict.fromkeys([c["source"] for c in state.retrieved_docs]))

        return state

    def _generate_node(self, state: RAGState) -> RAGState:
        """Generate answer using OpenAI."""
        if state.blocked:
            return state

        messages = build_messages(
            state.question,
            state.retrieved_docs,
            state.chat_history
        )

        response = self.client.chat.completions.create(
            model=self.settings.openai_chat_model,
            messages=messages,
            temperature=0
        )

        state.answer = response.choices[0].message.content
        return state

    def _create_graph(self):
        """Create and compile the RAG graph."""
        graph = StateGraph(RAGState)

        graph.add_node("guard", self._guard_node)
        graph.add_node("retrieve", self._retrieve_node)
        graph.add_node("generate", self._generate_node)

        graph.add_edge(START, "guard")

        def should_skip_retrieval(state: RAGState) -> str:
            return "end" if state.blocked else "retrieve"

        graph.add_conditional_edges(
            "guard",
            should_skip_retrieval,
            {"retrieve": "retrieve", "end": END}
        )

        graph.add_edge("retrieve", "generate")
        graph.add_edge("generate", END)

        return graph.compile()

    def invoke(self, state: RAGState) -> RAGState:
        """Run the graph."""
        return self.graph.invoke(state)
