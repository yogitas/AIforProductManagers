# AI Portfolio for Product Managers (`AIforProductManagers`)

Hey, I'm **Yogita Suryawanshi** — Product Manager & AI Builder. 

This repository is a collection of hands-on reference tutorials created as I learn and experiment with AI. It is designed to explain complex concepts (RAG, Agents, Evals, and Memory) in a simple, non-technical way for PMs, developers, and QA testers with the help of day to day usecases for them.

---

## 🎯 About the Repo
*   **Production-Minded:** Focuses on what matters in the real world: evaluations, safety guardrails, COGS cost-control, and memory management.
*   **Framework-Free to Framework-First:** Shows side-by-side implementations built from scratch in plain Python vs. built using orchestrators like LangChain.
*   **Zero-Infrastructure:** Run everything locally using open-source models (Ollama, SentenceTransformers) or lightweight SQLite DBs.

---

## 🧩 AI Concepts, Explained Simply

*   **RAG (Retrieval-Augmented Generation):** Like an *open-book exam* for LLMs. Instead of guessing answers from memory (hallucination), the agent looks up the exact facts in private documents and uses only those facts to write the response.
*   **AI Agents:** Virtual analysts that execute multi-step processes (crawling, filtering, ranking, mailing) on autopilot under strict safety guardrails.
*   **LLM Evals:** Unit testing for prompts. We run the agent against a "golden set" of test cases to programmatically verify that it classifies relevance accurately and doesn't crash.
*   **Preference Memory:** A *style cheat-sheet* injected into the prompt context so the agent adapts dynamically to user feedback without expensive retraining.

---

## 📂 Active Projects

| Project | Concept | Tech Stack | Link |
| :--- | :--- | :--- | :--- |
| **Competitive Intel Agent** | Automated news collector & ranker | Gemini Grounding, LiteLLM, COGS Tracking, Few-Shots | [Setup Guide](projects/pm-competitive-intel-agent#7-how-to-configure-this-agent-for-yourself) |
| **PM Copilot RAG Search** | Jira docs question-answering assistant | Scratch vs. LangChain, Ollama, ChromaDB, Evals | [Setup Guide](projects/pm-rag-copilot#8-how-to-configure-this-agent-for-yourself) |

---
*Created and maintained by **Yogita Suryawanshi** — Building practical, production-ready AI products.*
