"""
Version 1 Ingestion Script: Loads, chunks, embeds, and stores Jira docs in ChromaDB.
Usage: python3 -m v1_scratch.ingestion.ingest
"""

import os
import sys
from dotenv import load_dotenv

# Ensure root and v1 directories are in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from v1_scratch.ingestion.loader import DocumentLoader
    from v1_scratch.ingestion.chunker import DocumentChunker
    from v1_scratch.embeddings.embedder import EmbeddingModel
    from v1_scratch.retrieval.vector_store import VectorStore
except ImportError:
    from ingestion.loader import DocumentLoader
    from ingestion.chunker import DocumentChunker
    from embeddings.embedder import EmbeddingModel
    from retrieval.vector_store import VectorStore


def run_ingestion(
    data_dir: str = "data/raw",
    persist_dir: str = "./chroma_db",
    embedding_model_name: str = "all-MiniLM-L6-v2"
):
    """Loads documents from disk, splits into chunks, computes embeddings, and saves to ChromaDB."""
    load_dotenv()
    print("=" * 60)
    print("🚀 Starting PM Copilot Version 1 Ingestion Pipeline")
    print("=" * 60)

    # Step 1: Load documents
    print(f"📄 Step 1: Loading Jira documentation from '{data_dir}'...")
    loader = DocumentLoader(raw_data_dir=data_dir)
    documents = loader.load_documents()
    print(f"   --> Loaded {len(documents)} document(s).")

    # Step 2: Split into chunks
    print(f"\n✂️  Step 2: Splitting documents into smaller chunks...")
    chunker = DocumentChunker(chunk_size=450, chunk_overlap=60)
    chunks = chunker.split_documents(documents)
    print(f"   --> Created {len(chunks)} total text chunk(s).")

    # Step 3: Generate embeddings
    print(f"\n🧠 Step 3: Generating embeddings using '{embedding_model_name}'...")
    embedder = EmbeddingModel(model_name=embedding_model_name)
    texts = [chunk.content for chunk in chunks]
    embeddings = embedder.embed_documents(texts)
    print(f"   --> Generated {len(embeddings)} vector embedding(s) (Dim: {len(embeddings[0]) if embeddings else 0}).")

    # Step 4: Store in ChromaDB
    print(f"\n💾 Step 4: Persisting chunks and embeddings in ChromaDB ('{persist_dir}')...")
    vector_store = VectorStore(persist_directory=persist_dir, collection_name="jira_docs")
    vector_store.add_chunks(chunks, embeddings)
    print("   --> Successfully indexed all chunks into ChromaDB!")
    print("=" * 60)
    print("✅ Ingestion Pipeline Complete!\n")


if __name__ == "__main__":
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    raw_path = os.path.join(base_dir, "data", "raw")
    db_path = os.path.join(base_dir, "chroma_db")
    run_ingestion(data_dir=raw_path, persist_dir=db_path)
