"""
Version 1 CLI: Interactive terminal assistant with /debug mode for inspecting RAG steps.
Usage: python3 -m v1_scratch.app.cli
"""

import os
import sys
from typing import List
from dotenv import load_dotenv

# Ensure root and v1 directories are in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from v1_scratch.embeddings.embedder import EmbeddingModel
    from v1_scratch.retrieval.vector_store import VectorStore
    from v1_scratch.retrieval.retriever import Retriever, RetrievalResult
    from v1_scratch.generation.prompt import PromptBuilder
    from v1_scratch.generation.ollama import OllamaClient
except ImportError:
    from embeddings.embedder import EmbeddingModel
    from retrieval.vector_store import VectorStore
    from retrieval.retriever import Retriever, RetrievalResult
    from generation.prompt import PromptBuilder
    from generation.ollama import OllamaClient


def format_sources(results: List[RetrievalResult]) -> str:
    """Formats unique sources from retrieved chunks for citation display."""
    if not results:
        return "None"

    sources = []
    seen = set()
    for item in results:
        title = item.metadata.get("title", item.metadata.get("source", "Unknown"))
        src_file = item.metadata.get("source", "")
        key = (title, src_file)
        if key not in seen:
            seen.add(key)
            sources.append(f"- {title} ({src_file})")

    return "\n".join(sources)


def run_cli():
    """Runs the interactive PM Copilot CLI interface."""
    load_dotenv()
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    db_path = os.path.join(base_dir, "chroma_db")

    print("\n" + "=" * 60)
    print("🤖  PM Copilot — Jira Documentation RAG Assistant (Version 1)")
    print("=" * 60)
    print("Commands:")
    print("  /debug  : Toggle step-by-step pipeline inspection")
    print("  /help   : Display help message")
    print("  /exit   : Quit the application\n")

    # Initialize RAG components
    print("Initializing local RAG components...")
    embedder = EmbeddingModel(model_name=os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2"))
    vector_store = VectorStore(persist_directory=db_path, collection_name="jira_docs")
    retriever = Retriever(embedder=embedder, vector_store=vector_store, top_k=3, distance_threshold=0.75)
    ollama_client = OllamaClient(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        model=os.getenv("OLLAMA_MODEL", "llama3.1")
    )
    print(f"Connected to Ollama (Model: {ollama_client.model})")
    print("Ready to answer questions!\n")

    debug_mode = False

    while True:
        try:
            user_input = input("\nPM Copilot > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting PM Copilot. Goodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ["/exit", "exit", "quit"]:
            print("Exiting PM Copilot. Goodbye!")
            break

        if user_input.lower() == "/debug":
            debug_mode = not debug_mode
            status = "ENABLED" if debug_mode else "DISABLED"
            print(f"\n🔍 [DEBUG MODE] Pipeline step-by-step inspection is now {status}.")
            continue

        if user_input.lower() == "/help":
            print("\nExample Questions:")
            print("  - How do I create an Epic?")
            print("  - How do I create a custom workflow?")
            print("  - How do I create a Sprint?")
            print("  - How do I configure story points?")
            print("  - How do I create a Jira automation?")
            continue

        # Execute RAG Pipeline
        if debug_mode:
            print("\n" + "-" * 50)
            print("🔍 [DEBUG] STEP 1: Query Vector Embedding")
            query_emb = embedder.embed_text(user_input)
            print(f"   Query: '{user_input}'")
            print(f"   Embedding Vector Dim: {len(query_emb)}")
            print(f"   First 5 values: {query_emb[:5]}")

        retrieved_chunks = retriever.retrieve(user_input)

        if debug_mode:
            print("\n🔍 [DEBUG] STEP 2: Vector Similarity Search & Retrieval")
            print(f"   Retrieved Chunks Count: {len(retrieved_chunks)}")
            for idx, chunk in enumerate(retrieved_chunks, 1):
                doc_title = chunk.metadata.get("title", "Unknown")
                print(f"\n   --- Chunk #{idx} | Distance: {chunk.distance:.4f} | Source: {doc_title} ---")
                print(f"   {chunk.content[:200]}...")

        # Safeguard check if no chunks pass similarity threshold
        if not retrieved_chunks:
            answer = "I couldn't find enough information in the available Jira documentation to answer this."
            sources_text = "None"
            prompt = ""
        else:
            prompt = PromptBuilder.build_prompt(user_input, retrieved_chunks)

            if debug_mode:
                print("\n🔍 [DEBUG] STEP 3: Augmented Prompt sent to LLM")
                print(prompt)

            if debug_mode:
                print("\n🔍 [DEBUG] STEP 4: Calling Ollama LLM Inference...")

            answer = ollama_client.generate(prompt)
            sources_text = format_sources(retrieved_chunks)

        if debug_mode:
            print("-" * 50 + "\n")

        print("\nAnswer:")
        print(answer)
        print("\nSources:")
        print(sources_text)


if __name__ == "__main__":
    run_cli()
