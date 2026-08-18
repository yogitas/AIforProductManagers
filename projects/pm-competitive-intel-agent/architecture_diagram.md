# System Architecture Diagram - `pm-competitive-intel-agent`

This document details the system design, components, and task flow of the Competitive Intelligence Monitoring Agent.

---

## 1. System Flowchart

The following diagram outlines the sequential flow of the agent, highlighting where safety guardrails, state stores, perception sensors, and cognitive LLM operations interact:

```mermaid
graph TB
    %% Core Theme & Style definitions
    classDef trigger fill:#FCE8E6,stroke:#C5221F,stroke-width:2px,color:#000;
    classDef sensor fill:#E8F0FE,stroke:#1A73E8,stroke-width:2px,color:#000;
    classDef brain fill:#E6F4EA,stroke:#137333,stroke-width:2px,color:#000;
    classDef actuator fill:#FEF7E0,stroke:#B06000,stroke-width:2px,color:#000;
    classDef store fill:#F1F3F4,stroke:#5F6368,stroke-width:2px,color:#000;
    classDef guard fill:#F3E8FD,stroke:#8430E8,stroke-width:2px,color:#000;

    %% --- TRIGGER LAYER ---
    subgraph Trigger Layer [Triggers / Actions]
        GHA_Cron["🕒 GitHub Actions daily_run.yml<br/>(Daily Cron Schedule)"]:::trigger
        GHA_Manual["🖱️ GHA Workflow Dispatch<br/>(Manual Trigger)"]:::trigger
        GHA_Feedback["💬 GHA process_feedback.yml<br/>(GitHub Issue Opened)"]:::trigger
    end

    %% --- AGENT CONTROL & PERCEPTION ---
    subgraph Agent Core [Perception & Ingestion]
        Orchestrator["🤖 Agent Orchestrator<br/>(run_agent.py)"]:::brain
        ConfigLoader["⚙️ Config Loader<br/>(config_loader.py + Pydantic)"]:::guard
        BudgetCtrl["🛡️ Call Budget Manager<br/>(budget.py Limit Tracker)"]:::guard
        
        subgraph Perception Sensors
            GroundingTool["🔍 Gemini Search Grounding<br/>(google-genai SDK)"]:::sensor
            Crawler["🕸️ Web Crawler<br/>(BeautifulSoup + robots.txt check)"]:::sensor
        end
    end

    %% --- COGNITIVE / BRAIN LAYER ---
    subgraph Cognitive Engine [LiteLLM Brain]
        LLM_Extract["1. Structured Extractor<br/>(Parsing Search text into items)"]:::brain
        LLM_Filter["2. Materiality Classifier<br/>(Materiality Rubric Prompt)"]:::brain
        LLM_Ranker["3. Prioritized Ranker<br/>(Subdomain & Heuristic Preferences)"]:::brain
    end

    %% --- STATE & PERSISTENCE ---
    subgraph Memory & State [Knowledge / Storage]
        SeenStore[("💾 Seen Store<br/>seen_items.yaml")]:::store
        MemoryStore[("🧠 Preference Memory<br/>preference_memory.yaml")]:::store
    end

    %% --- ACTUATORS ---
    subgraph Actuators [Action Delivery]
        ReportGen["📝 Report Formatter<br/>(report.py MD/HTML)"]:::actuator
        MailSender["📧 Email Delivery<br/>(deliver.py + smtplib / GHA)"]:::actuator
    end

    %% --- CONNECTIONS ---
    GHA_Cron --> Orchestrator
    GHA_Manual --> Orchestrator
    
    %% Config & Guard checks
    Orchestrator --> ConfigLoader
    Orchestrator --> BudgetCtrl
    
    %% Perception flow
    Orchestrator --> Perception_Start["Start Discovery"]
    Perception_Start --> GroundingTool
    Perception_Start --> Crawler
    
    %% Quota guard checked
    BudgetCtrl -.->|Checks limits| GroundingTool
    
    %% Data -> Brain
    GroundingTool --> LLM_Extract
    Crawler --> LLM_Extract
    
    %% Deduplication & Classification
    LLM_Extract --> DedupCheck{"Deduplicate?"}
    SeenStore -->|Read seen hashes| DedupCheck
    DedupCheck -->|New items| LLM_Filter
    
    %% Memory-weighted Ranking
    MemoryStore -->|Read in-context pref summary| LLM_Ranker
    LLM_Filter -->|Only Material Items| LLM_Ranker
    
    %% Report & Delivery
    LLM_Ranker --> ReportGen
    ReportGen --> MailSender
    
    %% Delivery confirmed sequence
    MailSender -->|Success: Save state| SeenStore
    
    %% Feedback Loop
    GHA_Feedback --> FeedbackScript["🔧 process_feedback.py"]:::actuator
    FeedbackScript -->|Append check logs| MemoryStore
```

---

## 2. Component Reference Guide

This project implements the industry-standard **Autonomous AI Agent Architecture** divided into four clean boundaries:

### A. Perception Layer (Sensors)
*   **Google Search Grounding:** Queries the live web directly using Gemini's search capabilities to discover news, partnerships, and product launches within a timezone-bounded calendar window.
*   **Web Crawler:** Safely crawls custom source links by checking `robots.txt` permissions and extracting clean paragraph blocks, ensuring copyright compliance.

### B. Cognitive Engine (The Brain)
*   **Model Agnostic Abstractor:** decodes messages using `litellm`. Swap models in `config.yaml` without changing logic.
*   **Structured Parsing Agent:** extracts JSON lists of individual competitor items from raw unstructured search grounding blocks.
*   **Materiality Filter:** evaluates updates against a verbatim business rubric, suppressing noise (such as general thought-leadership or bugfixes) at a strict, deterministic temperature of `0.0`.
*   **Preference-Weighted Ranker:** summarizes user likes and dislikes as in-context prompt parameters to prioritize and sort updates, promoting the `focus_subdomain` matches to the top.

### C. Safety Guardrails (Control Systems)
*   **Pydantic Config Validator:** fails fast on start if `config.yaml` values are invalid.
*   **Search Budget Tracker:** stops making web searches if the `max_search_calls` safety cap is breached to prevent API runaway bills.
*   **Cold-Start Bounding:** caps lookbacks to 48 hours when the run state is empty to prevent fetching massive historical search results.
*   **State-Commit Sequence:** writes to `seen_items.yaml` only after confirmed email delivery to avoid silently dropping updates on delivery failure.

### D. Action Layer (Actuators)
*   **Seen Store & Preference Memory:** lightweight YAML state files committed back to git by the cron workflow.
*   **Report Generator:** formats primary featured updates and folds overflow items into a collapsed section to avoid information fatigue.
*   **GitHub Feedback Loop:** process issue titles (`feedback:{item_id}:useful`) opened by the user, updates memory, and automatically closes the issue.
