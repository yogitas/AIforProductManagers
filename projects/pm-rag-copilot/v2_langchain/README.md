# Version 2 — Rebuilt with LangChain

This directory contains the **Version 2** implementation of the PM Copilot RAG system built using the **LangChain** framework.

---

## 🎯 Purpose for Product Managers

In **Version 1**, we manually implemented every step: loading files with `os.walk`, chunking text with sliding loops, generating vector arrays with `SentenceTransformer`, managing collections with `chromadb.PersistentClient`, and building custom prompt strings.

**Version 2 rebuilds the identical application in ~60 lines of code** using LangChain's standard abstractions.

---

## 🔍 What LangChain Abstracts Away

| Version 1 (Manual / Scratch) | Version 2 (LangChain Component) | What LangChain Does Under the Hood |
| :--- | :--- | :--- |
| `DocumentLoader` (`os.walk` + file reading) | `DirectoryLoader` + `TextLoader` | Recursively finds files, handles encoding, and parses documents into standard `Document` objects. |
| `DocumentChunker` (character sliding window) | `RecursiveCharacterTextSplitter` | Recursively splits text along paragraphs (`\n\n`), sentences (`\n`), and spaces (` `). |
| `EmbeddingModel` (`SentenceTransformer.encode`) | `HuggingFaceEmbeddings` | Automatically downloads and manages local embedding model weights. |
| `VectorStore` (`chromadb.PersistentClient`) | `Chroma.from_documents` | Automatically creates collection, computes embeddings, and persists indices to disk in one line. |
| `Retriever` (custom distance filtering) | `vector_store.as_retriever()` | Wraps vector store in standard Runnable interface with `similarity_score_threshold`. |
| `PromptBuilder` + `OllamaClient` | **LCEL Chain** (`retriever \| prompt \| llm \| StrOutputParser`) | Chains together retrieval, prompt injection, LLM calling, and output parsing using standard Unix-like pipe syntax (`\|`). |

---

## 🚀 How to Run Version 2

Start the LangChain version of PM Copilot:
```bash
python3 -m v2_langchain.cli
```
