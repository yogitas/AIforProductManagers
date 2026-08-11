# Version 1 — Manual RAG Pipeline (From Scratch)

This directory contains the **Version 1 (From Scratch)** implementation of the PM Copilot RAG system.

## 🎯 Purpose for Product Managers
Frameworks like LangChain and LlamaIndex make building RAG fast, but they hide all the underlying machinery behind black-box classes. **Version 1 implements every single step in pure, readable Python** so you can see and understand:
1. Exactly how raw text is broken into semantic chunks.
2. How text is converted into mathematical vectors (embeddings).
3. How a Vector Database performs cosine distance similarity searches.
4. How distance thresholds act as safeguards against hallucinations.
5. How retrieved facts are injected into an augmented prompt for the LLM.

---

## 📂 Architecture & Directory Structure

```text
v1_scratch/
│
├── ingestion/
│   ├── loader.py        # STEP 1: Reads raw .md files from data/raw/
│   ├── chunker.py       # STEP 2: Splits documents into overlapping text chunks
│   └── ingest.py        # Standalone script to run the full ingestion pipeline
│
├── embeddings/
│   └── embedder.py      # STEP 3: Converts text into 384-dim vectors via SentenceTransformers
│
├── retrieval/
│   ├── vector_store.py  # STEP 4: Stores & queries vectors using local ChromaDB
│   └── retriever.py     # STEP 5: Executes similarity search with distance safeguards
│
├── generation/
│   ├── prompt.py        # STEP 6: Assembles augmented prompt (Instructions + Context + Question)
│   └── ollama.py        # STEP 7: Calls local Ollama (llama3.1) via HTTP
│
└── app/
    └── cli.py           # Interactive CLI with educational /debug mode
```

---

## 🚀 How to Run Version 1

### 1. Ingest Raw Jira Documentation
Run the ingestion pipeline to parse the Jira docs and populate ChromaDB:
```bash
python3 -m v1_scratch.ingestion.ingest
```

### 2. Launch Interactive CLI
Start the interactive command-line assistant:
```bash
python3 -m v1_scratch.app.cli
```

### 3. Inspect Pipeline Internals with `/debug`
Inside the CLI, type `/debug` and ask any question (e.g. *"How do I create a custom workflow?"*):
```text
PM Copilot > /debug
🔍 [DEBUG MODE] Pipeline step-by-step inspection is now ENABLED.

PM Copilot > How do I create a custom workflow?

🔍 [DEBUG] STEP 1: Query Vector Embedding
   Query: 'How do I create a custom workflow?'
   Embedding Vector Dim: 384
   First 5 values: [-0.0412, 0.0821, -0.0154, 0.0633, -0.0911]

🔍 [DEBUG] STEP 2: Vector Similarity Search & Retrieval
   Retrieved Chunks Count: 3
   --- Chunk #1 | Distance: 0.2814 | Source: Jira Documentation: Creating Custom Workflows ---

🔍 [DEBUG] STEP 3: Augmented Prompt sent to LLM
   You are a helpful PM Copilot...
   === RETRIEVED JIRA DOCUMENTATION CONTEXT ===
   ...

🔍 [DEBUG] STEP 4: Calling Ollama LLM Inference...
```
