"""
Version 2 CLI: Interactive terminal interface for LangChain-powered PM Copilot.
Usage: python3 -m v2_langchain.cli
"""

import os
import sys
from dotenv import load_dotenv

# Ensure parent directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from v2_langchain.pipeline import LangChainRAGPipeline


def run_cli_v2():
    """Runs the Version 2 LangChain PM Copilot CLI."""
    load_dotenv()
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    raw_path = os.path.join(base_dir, "data", "raw")
    db_path = os.path.join(base_dir, "chroma_db_langchain")

    print("\n" + "=" * 60)
    print("🦜🔗 PM Copilot — Version 2 (Built with LangChain)")
    print("=" * 60)
    print("Demonstrating framework abstractions for Document Loading,")
    print("Splitting, VectorStore, LCEL Chains, and Retrieval.\n")

    pipeline = LangChainRAGPipeline(
        data_dir=raw_path,
        persist_dir=db_path,
        embedding_model_name=os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1")
    )

    if not os.path.exists(db_path):
        print("Initializing & ingesting vector store for LangChain V2...")
        pipeline.ingest_documents()

    pipeline.build_chain()
    print("Ready to answer questions using LangChain!\n")

    while True:
        try:
            user_input = input("\nPM Copilot V2 > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting Version 2 CLI. Goodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ["/exit", "exit", "quit"]:
            print("Exiting Version 2 CLI. Goodbye!")
            break

        result = pipeline.answer_question(user_input)

        print("\nAnswer:")
        print(result["answer"])
        print("\nSources:")
        print(result["sources"])


if __name__ == "__main__":
    run_cli_v2()
