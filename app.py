import os
import tempfile
import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

from src.document_processor import process_file
from src.vector_store import add_documents
from src.graph import rag_graph

st.set_page_config(page_title="PolicyChat", page_icon="📋", layout="wide")
st.title("📋 PolicyChat")
st.caption("Ask questions about your company policies")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "processed_files" not in st.session_state:
    st.session_state.processed_files = []

# Sidebar — document upload
with st.sidebar:
    st.header("Upload Policy Documents")
    uploaded_files = st.file_uploader(
        "Upload PDF or DOCX files",
        type=["pdf", "docx", "doc"],
        accept_multiple_files=True,
    )

    if st.button("Process Documents", disabled=not uploaded_files):
        new_files = [f for f in uploaded_files if f.name not in st.session_state.processed_files]
        if not new_files:
            st.info("All uploaded files have already been processed.")
        else:
            with st.spinner("Processing documents..."):
                for file in new_files:
                    suffix = os.path.splitext(file.name)[1]
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(file.read())
                        tmp_path = tmp.name
                    try:
                        chunks = process_file(tmp_path)
                        # Attach original filename to metadata
                        for chunk in chunks:
                            chunk.metadata["source"] = file.name
                        add_documents(chunks)
                        st.session_state.processed_files.append(file.name)
                    finally:
                        os.unlink(tmp_path)
            st.success(f"Processed {len(new_files)} file(s).")

    if st.session_state.processed_files:
        st.subheader("Processed Files")
        for name in st.session_state.processed_files:
            st.write(f"- {name}")

# Chat history
for msg in st.session_state.messages:
    role = "user" if isinstance(msg, HumanMessage) else "assistant"
    with st.chat_message(role):
        st.markdown(msg.content)
        if isinstance(msg, AIMessage) and hasattr(msg, "sources") and msg.sources:
            with st.expander("Sources"):
                for src in msg.sources:
                    st.write(f"- {src}")

# Chat input
if question := st.chat_input("Ask a policy question..."):
    if not st.session_state.processed_files:
        st.warning("Please upload and process at least one policy document first.")
    else:
        st.session_state.messages.append(HumanMessage(content=question))
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = rag_graph.invoke({
                    "question": question,
                    "chat_history": st.session_state.messages[:-1],
                    "retrieved_docs": [],
                    "answer": "",
                    "sources": [],
                })

            st.markdown(result["answer"])
            if result["sources"]:
                with st.expander("Sources"):
                    for src in result["sources"]:
                        st.write(f"- {src}")

        ai_msg = AIMessage(content=result["answer"])
        ai_msg.sources = result["sources"]
        st.session_state.messages.append(ai_msg)
