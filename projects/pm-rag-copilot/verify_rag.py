"""
Automated end-to-end verification script testing both Version 1 and Version 2 against Ollama.
Usage: python3 verify_rag.py
"""

import os
import sys
from dotenv import load_dotenv

# Ensure parent directory is in python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from v1_scratch.embeddings.embedder import EmbeddingModel
from v1_scratch.retrieval.vector_store import VectorStore
from v1_scratch.retrieval.retriever import Retriever
from v1_scratch.generation.prompt import PromptBuilder
from v1_scratch.generation.ollama import OllamaClient
from v1_scratch.app.cli import format_sources
from v2_langchain.pipeline import LangChainRAGPipeline


def verify_v1():
    """Verifies Version 1 from-scratch RAG pipeline."""
    print("\n" + "=" * 60)
    print("🧪 Verifying Version 1 (From Scratch RAG)")
    print("=" * 60)
    base_dir = os.path.dirname(__file__)
    db_path = os.path.join(base_dir, "chroma_db")

    embedder = EmbeddingModel(model_name="all-MiniLM-L6-v2")
    vector_store = VectorStore(persist_directory=db_path, collection_name="jira_docs")
    retriever = Retriever(embedder=embedder, vector_store=vector_store, top_k=3, distance_threshold=0.75)
    ollama_client = OllamaClient(model="llama3.1")

    test_questions = [
        "How do I create an Epic?",
        "How do I create a custom workflow?",
        "How do I create a Sprint?",
        "How do I configure story points?",
        "How do I create a Jira automation?",
        "What is the capital of France?"  # Out-of-domain safeguard test
    ]

    for q in test_questions:
        print(f"\n❓ Question: {q}")
        chunks = retriever.retrieve(q)
        if not chunks:
            print("Answer: I couldn't find enough information in the available Jira documentation to answer this.")
            print("Sources: None")
        else:
            prompt = PromptBuilder.build_prompt(q, chunks)
            answer = ollama_client.generate(prompt)
            sources = format_sources(chunks)
            print(f"Answer:\n{answer}")
            print(f"Sources:\n{sources}")


def verify_v2():
    """Verifies Version 2 LangChain RAG pipeline."""
    print("\n" + "=" * 60)
    print("🧪 Verifying Version 2 (LangChain RAG)")
    print("=" * 60)
    base_dir = os.path.dirname(__file__)
    raw_path = os.path.join(base_dir, "data", "raw")
    db_path = os.path.join(base_dir, "chroma_db_langchain")

    pipeline = LangChainRAGPipeline(
        data_dir=raw_path,
        persist_dir=db_path,
        embedding_model_name="all-MiniLM-L6-v2",
        ollama_model="llama3.1"
    )
    if not os.path.exists(db_path):
        pipeline.ingest_documents()

    pipeline.build_chain()

    test_questions = [
        "How do I create a custom workflow?",
        "What is the capital of France?"
    ]

    for q in test_questions:
        print(f"\n❓ Question: {q}")
        res = pipeline.answer_question(q)
        print(f"Answer:\n{res['answer']}")
        print(f"Sources:\n{res['sources']}")


if __name__ == "__main__":
    load_dotenv()
    verify_v1()
    verify_v2()
