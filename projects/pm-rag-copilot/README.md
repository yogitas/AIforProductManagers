# PM Copilot — Hands-on RAG Demo for Product Managers

Welcome to **PM Copilot**, a hands-on learning project demonstrating **Retrieval-Augmented Generation (RAG) end-to-end** using a real Product Manager use case: answering questions about Jira software documentation.

This project is built 100% with free, open-source local components:
- **Python 3**
- **Ollama** (Local LLM inference using `llama3.1`)
- **Sentence Transformers** (`all-MiniLM-L6-v2` for open vector embeddings)
- **ChromaDB** (Local vector database)
- **pytest** (Testing framework)

---

## 🎯 What Problem Are We Solving?

Product Managers frequently navigate complex SaaS documentation (workflows, sprint setup, estimation, automation rules). Standard LLMs hallucinate specific configuration steps. RAG solves this by retrieving exact, curated documentation passages and providing them directly to the LLM to generate verifiable answers with source citations.

```text
User Question ──> Vector Search ──> Relevant Jira Chunks ──> LLM Prompt ──> Answer + Citations
```

---

## 📂 Project Structure Overview

This repository is intentionally structured into two side-by-side versions so anyone can easily compare **how RAG works under the hood** versus **how frameworks simplify it**:

```text
pm-rag-copilot/
│
├── 📁 v1_scratch/          <-- VERSION 1: Pure Python manual RAG (No frameworks)
│   ├── ingestion/         # Document loading & text chunking
│   ├── embeddings/        # Vector generation via SentenceTransformers
│   ├── retrieval/         # Vector database (ChromaDB) & cosine distance search
│   ├── generation/        # Prompt augmentation & local Ollama LLM calling
│   └── app/cli.py         # Interactive CLI with educational /debug mode
│
├── 📁 v2_langchain/        <-- VERSION 2: Rebuilt using LangChain abstractions
│   ├── pipeline.py        # Complete pipeline in ~60 lines of LangChain code
│   └── cli.py             # LangChain CLI interface
│
├── 📁 data/raw/            <-- Curated Jira documentation (Epics, Workflows, Sprints, etc.)
├── 📁 tests/               <-- Automated pytest suite
├── verify_rag.py          <-- Automated end-to-end verification script
├── requirements.txt       <-- Dependencies
└── README.md              <-- This guide
```

---

## ⚖️ Version 1 vs. Version 2 Comparison

| Feature | [Version 1 (v1_scratch/)](file:///Users/yogitas/AIportfolio/AIforProductManagers/projects/pm-rag-copilot/v1_scratch) | [Version 2 (v2_langchain/)](file:///Users/yogitas/AIportfolio/AIforProductManagers/projects/pm-rag-copilot/v2_langchain) |
| :--- | :--- | :--- |
| **Concept** | Built from scratch without frameworks. | Built using LangChain abstractions. |
| **Code Visibility** | Every loop, embedding vector, and prompt string is visible. | Encapsulated in standard `DocumentLoader`, `Chroma`, and `LCEL` chains. |
| **Educational Debug**| Interactive `/debug` mode inspects vectors & prompt injection. | Standard LCEL stream/invoke execution. |
| **Code Size** | ~350 lines across modular Python files. | ~60 lines leveraging LangChain. |
| **Best For** | **Understanding what RAG actually does step-by-step.** | **Understanding how production frameworks accelerate dev speed.** |

---

## 🧩 Step-by-Step RAG Breakdown

| Major RAG Step | What is it? | Why do we need it? | Where to see it in Code |
| :--- | :--- | :--- | :--- |
| **1. Document Loading** | Reads raw `.md` files from disk. | Converts unstructured files into structured `Document` objects with metadata. | [v1_scratch/ingestion/loader.py](file:///Users/yogitas/AIportfolio/AIforProductManagers/projects/pm-rag-copilot/v1_scratch/ingestion/loader.py) |
| **2. Text Chunking** | Breaks large documents into small overlapping passages. | Enables precise semantic retrieval and prevents exceeding LLM context limits. | [v1_scratch/ingestion/chunker.py](file:///Users/yogitas/AIportfolio/AIforProductManagers/projects/pm-rag-copilot/v1_scratch/ingestion/chunker.py) |
| **3. Embedding Generation** | Converts text into 384-dimensional mathematical vectors. | Translates words into coordinates where similar meanings land close together. | [v1_scratch/embeddings/embedder.py](file:///Users/yogitas/AIportfolio/AIforProductManagers/projects/pm-rag-copilot/v1_scratch/embeddings/embedder.py) |
| **4. Vector Storage** | Persists vectors and metadata in ChromaDB. | Enables sub-second nearest-neighbor vector similarity lookups. | [v1_scratch/retrieval/vector_store.py](file:///Users/yogitas/AIportfolio/AIforProductManagers/projects/pm-rag-copilot/v1_scratch/retrieval/vector_store.py) |
| **5. Vector Retrieval** | Finds closest chunks using Cosine Distance with safeguards. | Retrieves top $K$ relevant facts and rejects out-of-domain queries to prevent hallucinations. | [v1_scratch/retrieval/retriever.py](file:///Users/yogitas/AIportfolio/AIforProductManagers/projects/pm-rag-copilot/v1_scratch/retrieval/retriever.py) |
| **6. Augmented Prompting** | Injects retrieved chunks into a system prompt. | Forces the LLM to answer strictly using provided documentation. | [v1_scratch/generation/prompt.py](file:///Users/yogitas/AIportfolio/AIforProductManagers/projects/pm-rag-copilot/v1_scratch/generation/prompt.py) |
| **7. LLM Generation** | Calls local Ollama model to synthesize final answer. | Produces clean natural language answers citing exact source files. | [v1_scratch/generation/ollama.py](file:///Users/yogitas/AIportfolio/AIforProductManagers/projects/pm-rag-copilot/v1_scratch/generation/ollama.py) |

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.9+
- [Ollama](https://ollama.com/) running locally (`ollama serve`).
- Pull the local model:
  ```bash
  ollama pull llama3.1
  ```

### 2. Setup Dependencies
```bash
cd projects/pm-rag-copilot
pip install -r requirements.txt
```

### 3. Run Version 1 (From Scratch)
```bash
# Step A: Ingest Jira documentation into ChromaDB
python3 -m v1_scratch.ingestion.ingest

# Step B: Launch interactive CLI
python3 -m v1_scratch.app.cli
```

> **Tip for PMs**: Inside the CLI, type `/debug` and ask any question to inspect the raw embedding vectors, distance scores, retrieved chunks, and prompt injection in real time!

### 4. Run Version 2 (LangChain)
```bash
python3 -m v2_langchain.cli
```

### 5. Run Automated Tests & End-to-End Verification
```bash
# Run unit tests
python3 -m pytest tests/

# Run automated end-to-end verification
python3 verify_rag.py
```

### 6. Run RAG Quality Evaluations (LLM-as-a-Judge)
Measure your retrieval hit rate, groundedness/faithfulness (via local LLM judge), QA completeness, and compliance with safety safeguards:
```bash
python3 -m evals.run_evals
```
