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
| **Competitive Intel Agent** | Automated news collector & ranker | Ollama/Local DDG, LiteLLM, COGS Tracking, Few-Shots | [Setup Guide](projects/pm-competitive-intel-agent#7-how-to-configure-this-agent-for-yourself) |
| **PM Copilot RAG Search** | Jira docs question-answering assistant | Scratch vs. LangChain, Ollama, ChromaDB, Evals | [Setup Guide](projects/pm-rag-copilot#8-how-to-configure-this-agent-for-yourself) |

## ✍️ AI Articles & Perspectives (LinkedIn)

Along with hands-on code, I regularly publish write-ups sharing my views and analysis on current movements in the AI industry:

*   **[Agent Skills: Why This Changes Everything](articles/Agent%20Skills.md)** — *LinkedIn Link: [2025 Was About MCP. 2026 Will Be About Skills](https://www.linkedin.com/pulse/2025-mcp-2026-skills-yogita-suryawanshi-6ojtc/)*. Discussing Anthropic's Agent Skills specification and why reusable procedural standards are crucial for agent scaling.
*   **[Loop Engineering: The Next Rename, Explained for PMs](articles/Loop%20Engineering.md)** — *LinkedIn Link: [The New Buzz on the AI Block: Loop Engineering](https://www.linkedin.com/pulse/new-buzz-ai-block-loop-engineering-yogita-suryawanshi-zauce/)*. Cutting through the industry buzzwords to explain prompt engineering, context engineering, skills, and loop orchestration in a non-technical way.
*   **[Stop vibe testing your AI product, start evaling](articles/Stop%20vibe%20Testing,%20Start%20Evaling.md)** — *LinkedIn Link: [Stop vibe testing your AI product, start evaling](https://www.linkedin.com/pulse/stop-vibe-testing-your-ai-product-start-evaling-yogita-suryawanshi-sgouf/)*. Explaining why traditional deterministic software testing fails with LLMs, and how to build a robust, metrics-driven evaluation system for AI features.

---
*Created and maintained by **Yogita Suryawanshi** — Building practical, production-ready AI products.*
