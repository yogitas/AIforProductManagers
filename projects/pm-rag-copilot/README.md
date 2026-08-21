# PM Copilot: Local RAG Search Agent (`pm-rag-copilot`)

This project is a reference implementation of a production-minded Retrieval-Augmented Generation (RAG) agent built completely with local, open-source tools. It is designed to teach other Product Managers (PMs) how RAG operates under the hood by showing a side-by-side comparison of manual RAG built in plain Python vs. RAG built using LangChain.

---

## 1. The Product Problem

As a Product Manager, customer success manager, or developer, navigating complex corporate documentation (workflows, sprint rules, setup configurations, and automation guides) is a massive time sink. Teams spend hours looking up configuration guidelines inside Jira, Confluence, and internal wikis.

This information bottleneck leads to:
*   **Customer Support Delay:** Support agents take longer to resolve tickets due to search latency across internal wikis.
*   **Operational Errors:** Setup mistakes happen when engineers configure complex sprint rules based on memory.
*   **Hallucination Risks:** Off-the-shelf commercial LLMs (like ChatGPT or Claude) do not have access to private company wikis and hallucinate specific workflow steps.

### Our Solution
**PM Copilot** is our product. It is a locally hosted, privacy-first RAG agent that ingests raw Jira markdown documentation, stores it in a semantic vector database, and answers user queries with verifiable citations. Because it retrieves real text chunks and is restricted by safety prompts, it cannot make up answers, ensuring 100% compliance with your documentation.

---

## 2. v1 Strategic Tradeoffs & Design Decisions

To demonstrate how RAG actually operates and prove production viability, we made several key trade-offs in our architecture:

### A. Local Open-Source Models (Ollama) vs. Commercial APIs
*   **Decision:** We run Ollama locally using `llama3.1` and `SentenceTransformers` (`all-MiniLM-L6-v2`) for embeddings.
*   **Trade-off & Rationale:** Relying on commercial APIs (like OpenAI or Anthropic) introduces token costs and data privacy concerns—private Jira documentation is sent to external servers. Running a local stack keeps the agent free to execute and ensures zero data leaks.

### B. Framework-Free Python (v1) vs. Orchestrator Abstractions (v2)
*   **Decision:** We built two side-by-side versions of RAG: Version 1 built completely from scratch using standard Python loops, and Version 2 built using LangChain.
*   **Trade-off & Rationale:** Frameworks like LangChain hide the core components (chunking, vector math, prompt injection) behind high-level wrappers. Building Version 1 in plain Python is essential to teach the core concepts (how text becomes coordinate vectors, how cosine similarity measures distance, and how prompts are augmented). Version 2 is built to demonstrate developer velocity.

### C. Local Vector Database (ChromaDB) vs. Enterprise Cloud Indexes
*   **Decision:** We persist embeddings locally using ChromaDB in client-server mode.
*   **Trade-off & Rationale:** Cloud vector databases (like Pinecone or Milvus) add setup complexity, api-key management, and monthly costs. Persisting ChromaDB locally keeps the setup lightweight and fully functional offline.

### D. RAG (In-Context Injection) vs. Model Fine-Tuning
*   **Decision:** We use vector similarity search to inject context chunks into the LLM prompt.
*   **Trade-off & Rationale:** Fine-tuning a model on company documentation is slow, expensive, suffers from catastrophic forgetting, and cannot supply real-time source citations. RAG is cheap, auditable, updates instantly when documents change, and cites its sources.

### E. Guardrails & Failure Handling (Control Systems)
*   **Decision:** We built system constraints to handle out-of-domain queries and search failures:
    *   *Overlap Chunks:* Chunks have a 100-character overlap to prevent losing semantic context at boundaries.
    *   *Similarity Score Rejection:* Chunks with a cosine distance greater than `0.75` are rejected. If no chunks pass the threshold, the LLM outputs a pre-defined fallback: *"I do not have enough information to answer this query,"* preventing hallucinations.
    *   *Out-of-Domain Query Rejection:* The prompt restricts the LLM from answering general-knowledge questions.

### F. Automated Prompt & RAG Quality Evaluation (Evals Suite)
*   **Decision:** We run [`evals/run_evals.py`](file:///Users/yogitas/AIportfolio/AIforProductManagers/projects/pm-rag-copilot/evals/run_evals.py) using an LLM-as-a-judge approach to measure accuracy against a JSON test dataset.
*   **Trade-off & Rationale:** Traditional software tests cannot measure LLM output quality. Our evaluation suite programmatically scores the pipeline on key metrics before release.

---

## 3. What "Proper Behavior" Looks Like (Our Evaluation Focus)

For the PM Copilot to be release-ready, it must meet two critical metrics tracked by our automated evaluation scorecard:

*   **1. Retrieval Hit Rate (Target: >=90%):** Measures whether the vector search successfully retrieves the exact document chunk containing the answer. If the hit rate is low, the LLM will not have the correct context to answer the question.
*   **2. LLM Groundedness (Target: >=90%):** Evaluates if the LLM's final answer is derived *only* from the retrieved chunks. If the model introduces external information, it fails the groundedness check (faithfulness), indicating a hallucination.

---

## 4. What v1 / Scratch MVP Does

*   **Raw Markdown Ingestion:** Parses local Jira documentation `.md` files.
*   **Character Split Chunking:** Splits documents into 500-character passages with 100-character overlaps.
*   **Local Embedding Generation:** Converts text passages into 384-dimensional coordinates using SentenceTransformers.
*   **Cosine Distance Search:** Programmatically computes the nearest neighbors to locate the most relevant facts.
*   **Interactive CLI with /debug Mode:** Includes a command-line interface where entering `/debug` displays the raw embedding coordinates, cosine distances, and prompt injection parameters.

---

## 5. What v2 / LangChain Integration Does

*   Replicates the exact functionality of v1 in under 60 lines of code.
*   Uses standard LangChain abstractions: `DirectoryLoader`, `RecursiveCharacterTextSplitter`, `Chroma`, and LCEL (`LangChain Expression Language`) chains.
*   Shows how production frameworks simplify ingestion and retrieval.

---

## 6. Deliberately Cut from MVP (Roadmap)

To maintain a lean codebase, the following features were deliberately deferred from the initial MVP:

*   **Dynamic Chunk Sizing:** Splitting documents semantically based on markdown headers instead of static character counts.
*   **Hybrid Search:** Combining vector similarity search with BM25 keyword search to capture exact terms (like bug numbers).
*   **Multi-Query Expansion:** Generating variations of user queries to retrieve a wider range of relevant documents.
*   **Cross-Encoder Re-ranking:** Re-ordering search results using a secondary model to ensure the absolute best chunks are placed in the prompt.

---

## 7. Known Limitations

*   **Ollama Hardware Dependency:** Running LLMs locally depends on the host machine's CPU/GPU. Responses may have latency on older hardware.
*   **Static Split Boundaries:** Character-based chunking can occasionally split code blocks or tables in half, degrading context quality.

---

## 8. How to Configure This Agent for Yourself

If you download this repository, follow these steps to configure and run the RAG agent locally:

### Step 1: Install Ollama & Pull the Model
Download [Ollama](https://ollama.com/) on your local machine, run the application, and pull the model:
```bash
ollama pull llama3.1
```

### Step 2: Install Python Dependencies
Set up your virtual environment and install requirements:
```bash
# Navigate to projects/pm-rag-copilot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Run Ingestion and Launch Version 1 (Scratch)
```bash
# Ingest raw documentation into local ChromaDB
python3 -m v1_scratch.ingestion.ingest

# Launch the interactive CLI
python3 -m v1_scratch.app.cli
```
*   *Tip:* Type `/debug` inside the CLI to inspect vectors, distance scores, and prompt injections!

### Step 4: Run Version 2 (LangChain)
To execute the LangChain-based version:
```bash
python3 -m v2_langchain.cli
```

### Step 5: Run Automated Tests and Quality Evaluations
```bash
# Run unit tests
python3 -m pytest tests/

# Run the end-to-end evaluation scorecard (Groundedness & Hit Rate checks)
python3 -m evals.run_evals
```
