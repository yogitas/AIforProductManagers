import os
import sys
import pytest

# Ensure parent directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from v1_scratch.ingestion.loader import DocumentLoader, Document
from v1_scratch.ingestion.chunker import DocumentChunker, TextChunk
from v1_scratch.embeddings.embedder import EmbeddingModel
from v1_scratch.retrieval.vector_store import VectorStore
from v1_scratch.retrieval.retriever import Retriever, RetrievalResult
from v1_scratch.generation.prompt import PromptBuilder


@pytest.fixture
def sample_documents(tmp_path):
    """Creates temporary markdown test files."""
    doc1 = tmp_path / "test_epics.md"
    doc1.write_text("# Jira Epics\nEpics are large bodies of work. Click Create Epic in Jira.", encoding="utf-8")

    doc2 = tmp_path / "test_sprints.md"
    doc2.write_text("# Jira Sprints\nSprints are time-boxed iterations. Click Create Sprint in Backlog.", encoding="utf-8")

    return str(tmp_path)


def test_document_loader(sample_documents):
    loader = DocumentLoader(raw_data_dir=sample_documents)
    docs = loader.load_documents()
    assert len(docs) == 2
    sources = [doc.metadata["source"] for doc in docs]
    assert "test_epics.md" in sources
    assert "test_sprints.md" in sources


def test_document_chunker():
    doc = Document(
        page_content="Paragraph 1 content.\n\nParagraph 2 content.\n\nParagraph 3 content.",
        metadata={"source": "test.md", "title": "Test Document"}
    )
    chunker = DocumentChunker(chunk_size=50, chunk_overlap=10)
    chunks = chunker.split_documents([doc])
    assert len(chunks) >= 1
    assert isinstance(chunks[0], TextChunk)
    assert chunks[0].metadata["source"] == "test.md"


def test_embedding_model():
    embedder = EmbeddingModel(model_name="all-MiniLM-L6-v2")
    vector = embedder.embed_text("How do I create an Epic in Jira?")
    assert isinstance(vector, list)
    assert len(vector) == 384  # Dimension for all-MiniLM-L6-v2


def test_vector_store_and_retriever(tmp_path):
    embedder = EmbeddingModel(model_name="all-MiniLM-L6-v2")
    db_path = str(tmp_path / "test_chroma")
    vector_store = VectorStore(persist_directory=db_path, collection_name="test_collection")

    chunk1 = TextChunk(
        chunk_id="chunk_1",
        content="To create an Epic in Jira, click the + Create button and select Issue Type = Epic.",
        metadata={"source": "epics.md", "title": "Creating Epics"}
    )
    chunk2 = TextChunk(
        chunk_id="chunk_2",
        content="To create a Sprint, go to the Backlog view and click Create Sprint.",
        metadata={"source": "sprints.md", "title": "Creating Sprints"}
    )

    embeddings = embedder.embed_documents([chunk1.content, chunk2.content])
    vector_store.add_chunks([chunk1, chunk2], embeddings)

    retriever = Retriever(embedder=embedder, vector_store=vector_store, top_k=2, distance_threshold=0.8)

    # Test high-relevance match
    results = retriever.retrieve("How do I create an Epic?")
    assert len(results) >= 1
    assert "Epic" in results[0].content

    # Test safeguard trigger (out-of-domain query with strict threshold)
    strict_retriever = Retriever(embedder=embedder, vector_store=vector_store, top_k=1, distance_threshold=0.1)
    no_results = strict_retriever.retrieve("What is the recipe for baking chocolate cake?")
    assert len(no_results) == 0


def test_prompt_builder():
    doc = Document(
        page_content="To create a workflow...",
        metadata={"title": "Custom Workflows", "source": "workflows.md"}
    )
    res = RetrievalResult(content="To create a workflow...", metadata=doc.metadata, distance=0.2)

    prompt = PromptBuilder.build_prompt("How do I create a workflow?", [res])
    assert "Custom Workflows" in prompt
    assert "User Question: How do I create a workflow?" in prompt
    assert "Answer:" in prompt
