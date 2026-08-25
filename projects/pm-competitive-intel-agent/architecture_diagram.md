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
    subgraph Trigger Layer [Local Triggers & Actions]
        Local_Cron["🕒 macOS launchd / Linux cron<br/>(Scheduled execution)"]:::trigger
        Local_CLI["💻 Local Terminal Command<br/>(Manual execution)"]:::trigger
        User_Feed["👤 User Manual Edits<br/>(Writes feedback logs)"]:::trigger
    end

    %% --- AGENT CONTROL & PERCEPTION ---
    subgraph Agent Core [Perception & Ingestion]
        Orchestrator["🤖 Agent Orchestrator<br/>(run_agent.py)"]:::brain
        ConfigLoader["⚙️ Config Loader<br/>(config_loader.py + Pydantic Checks)"]:::guard
        BudgetCtrl["🛡️ Call Budget Manager<br/>(budget.py Limit Tracker)"]:::guard
        
        subgraph Perception Sensors
            SearchScraper["🔍 DDG HTML Search Scraper<br/>(Keyless Requests)"]:::sensor
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

    %% --- ACTUATORS & OUTPUTS ---
    subgraph Actuators [Action Delivery]
        ReportGen["📝 Report Formatter<br/>(report.py MD/HTML)"]:::actuator
        DeliveryRouter["📧 Delivery Router<br/>(deliver.py routing logic)"]:::actuator
        Dashboard["🖥️ Web Browser Dashboard<br/>(Auto-Opens HTML Report)"]:::actuator
        UserInbox["📬 User Email Inbox<br/>(SMTP Transmission)"]:::actuator
    end

    %% --- CONNECTIONS ---
    Local_Cron --> Orchestrator
    Local_CLI --> Orchestrator
    User_Feed -->|Manual YAML updates| MemoryStore
    
    %% Config & Guard checks
    Orchestrator --> ConfigLoader
    Orchestrator --> BudgetCtrl
    
    %% State initialization checks
    Orchestrator -.->|Load historical seen IDs| SeenStore
    Orchestrator -.->|Load user preferences| MemoryStore
    
    %% Perception flow
    Orchestrator --> Perception_Start["Start Discovery"]
    Perception_Start --> SearchScraper
    Perception_Start --> Crawler
    
    %% Quota guard checked
    BudgetCtrl -.->|Checks limits| SearchScraper
    
    %% Data -> Brain
    SearchScraper --> LLM_Extract
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
    ReportGen --> DeliveryRouter
    
    %% Delivery Routing (Browser or SMTP)
    DeliveryRouter -->|webbrowser.open| Dashboard
    DeliveryRouter -->|smtplib secure send| UserInbox
    
    %% Delivery confirmed sequence
    DeliveryRouter -->|Success: Save state| SeenStore
```

---

## 2. Component Reference Guide

This project implements the industry-standard **Autonomous AI Agent Architecture** divided into four clean boundaries:

### A. Perception Layer (Sensors)
*   **DuckDuckGo Search Scraper:** Queries the live web directly using DuckDuckGo's raw HTML interface to discover news, partnerships, and product launches within a timezone-bounded calendar window.
*   **Web Crawler:** Safely crawls custom source links by checking `robots.txt` permissions and extracting clean paragraph blocks, ensuring copyright compliance.

### B. Cognitive Engine (The Brain)
*   **Model Agnostic Abstractor:** Decodes messages using `litellm`. Swap models in `config.yaml` without changing logic.
*   **Structured Parsing Agent:** Extracts JSON lists of individual competitor items from raw unstructured search grounding blocks.
*   **Materiality Filter:** Evaluates updates against a verbatim business rubric, suppressing noise (such as general thought-leadership or bugfixes) at a strict, deterministic temperature of `0.0`.
*   **Preference-Weighted Ranker:** Summarizes user likes and dislikes as in-context prompt parameters to prioritize and sort updates, promoting the `focus_subdomain` matches to the top.

### C. Safety Guardrails (Control Systems)
*   **Pydantic Config Validator:** Fails fast on start if `config.yaml` values are invalid.
*   **Search Budget Tracker:** Stops making web searches if the `max_search_calls` safety cap is breached to prevent API runaway bills.
*   **Cold-Start Bounding:** Caps lookbacks to 48 hours when the run state is empty to prevent fetching massive historical search results.
*   **State-Commit Sequence:** Writes to `seen_items.yaml` only after confirmed email/dashboard delivery to avoid silently dropping updates on delivery failure.

### D. Action Layer (Actuators)
*   **Seen Store & Preference Memory:** Lightweight YAML state files stored locally on the host machine.
*   **Report Generator:** Formats primary featured updates and folds overflow items into a collapsed section to avoid information fatigue.
*   **Delivery Router:** Directs the generated HTML report to open automatically in your local web browser, or routes it via SMTP to your configured email inbox depending on your SMTP setup.
*   **Local Preference State Loop:** Loads user thumbs-up/down preferences from `preference_memory.yaml` to adjust rankings on subsequent pipeline runs.
