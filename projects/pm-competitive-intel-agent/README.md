# Competitive Intelligence Monitoring Agent (`pm-competitive-intel-agent`)

This project is a reference implementation of a production-minded AI agent built using plain, widely-available open-source tools. It is designed to demonstrate best practices in building LLM-powered applications with explicit attention to evals, guardrails, and failure handling, rather than just a simple working demo.

---

## 1. The Product Problem

As a Product Manager, staying relevant in the market means keeping a constant, watchful eye on domain movements, technological trends, and competitor releases. In highly active sectors (such as premium electric vehicles, clean-energy, or charging infrastructure), this translates to manually checking dozens of blogs, newsrooms, press releases, regulatory filings, and conference keynotes every single day. 

This manual check is:
*   **Time-Consuming:** Spending 30–60 minutes daily visiting disjointed sites is an expensive operational overhead that distracts from strategic product execution.
*   **Noisy:** Most updates are PR announcements, minor bugfixes, or social posts that do not represent material business pivots.
*   **Hard to Share:** Disseminating the right updates to engineering, sales, and executive teams requires manual copy-pasting and formatting.

### Our Solution
**The Competitive Intelligence Monitoring Agent** is our product. It acts as an automated, customized competitive intelligence analyst. It tracks configured industry domains, extracts recent updates, filters out unimportant noise (like general marketing posts or minor bugfixes) using a clear set of decision rules, prioritizes them based on user-defined sub-domains and historical feedback, and emails a consolidated daily digest—saving hours of manual tracking every week.

---

## 2. v1 Strategic Tradeoffs & Design Decisions

To deliver a high-quality MVP that demonstrates production-grade engineering without unnecessary complexity, we made several deliberate trade-offs:

### A. LLM Provider-Agnosticism vs. Vendor Lock-in
*   **Decision:** We use **`litellm`** as our LLM invocation layer.
*   **Trade-off & Rationale:** The LLM model is configured via a single line in `config.yaml` (e.g. `llm_model: "ollama/llama3.1"`). A PM or developer can swap in commercial cloud APIs (Gemini, Claude, OpenAI) or other local open-weights models in seconds. By avoiding proprietary vendor SDKs, we future-proof our core intelligence pipeline and prevent vendor lock-in.

### B. Keyless Local Search vs. Commercial Grounding APIs
*   **Decision:** We use a custom, keyless local scraper targeting DuckDuckGo's raw HTML interface for competitor discovery.
*   **Trade-off & Rationale:** Commercial search grounding APIs (like Google or Bing) require credit card registrations, billing configurations, and paid API keys, creating a significant barrier to setup. Even open-source search library wrappers frequently trigger bot rate-limiting. To ensure a zero-barrier, private, and cost-free setup for PMs, developers, and testers, we built a raw HTML requests-based scraper. It runs completely free, requires zero credentials, and retrieves high-quality snippet text out of the box. *Trade-off:* While this is 100% free and has zero external package dependencies, future structural updates to DuckDuckGo's HTML could require minor parser updates.

### C. Frameworks (LangChain/CrewAI) vs. Focused Libraries
*   **Decision:** We chose **not** to use heavy agent frameworks (LangChain agents, CrewAI, AutoGen). Instead, we orchestrate the pipeline using standard Python, Pydantic, and Tenacity.
*   **Trade-off & Rationale:** Frameworks add layers of abstraction that obscure runtime errors and increase latency. Because the pipeline is a linear sequence of 5 steps, a framework adds abstraction without adding capability. Furthermore, since a primary goal of this repository is to teach how AI agents actually work under the hood, building the orchestration with plain Python, Pydantic, and LiteLLM exposes the mechanics of each step clearly, rather than hiding this key educational complexity behind high-level framework wrappers. Instead, we use focused, single-purpose open-source libraries: `pydantic` for config schema validation on startup, and `tenacity` for exponential backoff retries on network calls.

### D. File-Based State Store vs. Dedicated Databases
*   **Decision:** Seen item hashes and user preference logs are stored locally in PyYAML files (`seen_items.yaml`, `preference_memory.yaml`).
*   **Trade-off & Rationale:** Hosting and managing a database (PostgreSQL, Redis) introduces infrastructure cost and maintenance. A file-based local store keeps the agent lightweight, simple, and self-contained on the host machine.

### E. In-Context Preference Memory vs. Fine-tuning
*   **Decision:** User feedback (thumbs up/down) is summarized as a short text block and injected into the ranking prompt, rather than fine-tuning model weights or managing vector databases.
*   **Trade-off & Rationale:** Model fine-tuning is slow, expensive, and black-box. Vector search (RAG) adds embedding latency. Prompt-based preference summary is cheap, executes in milliseconds, and is easily auditable.

### F. Guardrails & Failure Handling (Control Systems)
*   **Decision:** We built robust software constraints to protect the pipeline against cost runaway, data loss, and API rate limits.
*   **Trade-off & Rationale:**
    *   *Cold-Start Bounding:* Caps search lookbacks to 48 hours when state files are empty, preventing huge token and search quota consumption on the first run.
    *   *Call Budget Tracker & COGS Reporting:* Automatically stops discovery once `max_search_calls` is breached to prevent loop runaway costs. Additionally, it intercepts all LiteLLM completion responses to track total input/output tokens and calculate/log the estimated run cost (based on configured token rates) at the end of every execution. This treats API usage as a measurable operational cost (COGS), which is crucial for managing real product profitability.
    *   *Try/Except Isolation:* Wraps each crawler and search loop individually so that a timeout on one competitor site does not crash the entire pipeline run.
    *   *Grounding URL check:* Automatically drops items that lack verifiable source URLs before they reach the LLM.
    *   *Commit Sequencing:* Commits seen hashes to `seen_items.yaml` only *after* email delivery is verified as successful, ensuring no updates are lost in transit.
    *   *Inference Timeout Protection:* Injects a `timeout=30` parameter into all LiteLLM completion queries, preventing the local Python process from freezing indefinitely if the local Ollama model server experiences latency or hangs.
    *   *Format-Resilient Parsing Fallback:* Automatically detects and wraps single JSON dict objects `{}` returned by local models (which sometimes ignore array instructions in prompts) into standard JSON lists `[{}]` to prevent format-related classification drops.
    *   *Rate Limit Sleeper:* Includes a 5-second delay between sequential search queries to comply with search engine rate limits and prevent IP blocks.

### G. Automated Prompt Evaluation (Evals Suite)
*   **Decision:** We use the open-source **Promptfoo** library to test prompt accuracy against a hand-labeled "golden set" of 17 test cases, which can be run locally or integrated into GitHub Actions CI.
*   **Trade-off & Rationale:** Hand-testing prompts on every change is slow and subjective. Instead, promptfoo runs our exact same relevance prompt file (`src/prompts/materiality_prompt.txt`) using a custom test provider (`evals/provider.py`) to verify that the classification outputs conform to schemas and expected labels. This can be integrated into GHA CI (`.github/workflows/ci.yml`) to automatically catch prompt regressions on repository pushes.
*   **What "Proper Behavior" Looks Like (Our Evaluation Focus):**
    For this agent to remain valuable and function reliably in a production environment, it must meet two key quality criteria, which we actively target and verify through our evaluations:
    *   *1. Crash-Free Output Parsing:* Since the agent crawls unstructured data from various sources across the web, we must ensure that the model output consistently conforms to the structured layout required by our parsing engine. This prevents system crashes and guarantees the reader always receives a clean, readable, and well-formatted digest.
    *   *2. Spam-Free Relevance Checking:* If the agent is too lenient, the daily report becomes filled with noise (such as general cleaning guides or social media milestones), leading to email fatigue and a loss of user trust. If it is too strict, the PM misses critical updates (like OTA OS rollouts or 5G connectivity partnerships). The evaluation suite verifies the agent's decisions against our business rules to keep the daily report highly focused and actionable.

---

## 3. What v1 / MVP Does

*   **Configured Tracking:** Monitors primary industry domains, named competitors, and focus sub-domains (which get flagged with a ⭐).
*   **Search & Crawl Discovery:** Queries DuckDuckGo HTML search locally to discover updates, and crawls custom competitor blogs (checking `robots.txt` beforehand).
*   **Deduplication:** Automatically hashes URLs or titles to prevent reporting items discovered in prior executions.
*   **Relevance Filtering:** Classifies discovered items as "important" (launches, pricing, leadership, M&A) vs. "noise" (bug fixes, general marketing) via an LLM classification step.
*   **Preference-Weighted Ranking:** Re-orders the daily digest utilizing a historical preference summary block in the prompt.
*   **Daily Digest Generation:** Emails a markdown and HTML report grouped by competitor with source URLs.
*   **Lightweight Feedback Loop:** Customizes rankings dynamically based on your likes/dislikes recorded in the local preference memory state file.

---

## 4. Deliberately Cut from v1 (Roadmap)

To maintain a lean codebase, the following features were deliberately deferred from the initial MVP:

*   **Per-Source-Type Check Cadence:** Adjusting fetch frequency (e.g., daily checks for primary competitors, but weekly checks for analysts/awards/conferences).
*   **Two-Tier Subdomain Weighting:** Lowering the importance threshold for items relevant to the focus subdomain compared to the general domain.
*   **New-Entrant Detection:** Automatically flagging and alerting on untracked companies that repeatedly appear in search discovery.
*   **Non-English Source Support:** Restructuring discovery and parsing prompts to support translations and multi-language crawling.
*   **Confidence Scoring:** Calculating a source credibility score separate from the basic relevance check.
*   **Recall / Miss-Reporting:** Implementing a feedback path to report updates that the agent missed (false negatives).

---

## 5. Known Limitations

*   **Local Scheduling:** Running the agent on a schedule requires a local task scheduler (such as macOS `launchd` or Linux `cron`) configured on the host machine.
*   **Local Host Dependency:** Since the agent runs locally, the host machine must be turned on and connected to the internet during the scheduled execution window for DDG search query scraping to complete.

---

## 6. Testing This Locally

You do not need to wait for a daily cron to iterate. The agent supports flags to run safely and repeatedly:

### 1. Configure Credentials (Optional)
If running locally using **Ollama**, no credentials or API keys are required! 

If you prefer to run a commercial cloud model (e.g. Gemini, OpenAI, Claude), create a local `.env` file and define `LLM_API_KEY`:
```env
LLM_API_KEY="your-api-key-here"
```

### 2. Execute Local Test Runs
```bash
# SCRIPT LOCATION: Run from projects/pm-competitive-intel-agent/

# A. Test Mode (Simulates run, prints cost, and automatically opens the HTML dashboard in your browser)
../../.venv/bin/python src/run_agent.py --test-mode

# B. Dry Run (Simulates run against existing state, writes outputs to state/, skips email and git commit)
../../.venv/bin/python src/run_agent.py --dry-run

# C. Reset State (Backs up seen_items.yaml/preference_memory.yaml, starts run with clean state, sends email)
../../.venv/bin/python src/run_agent.py --reset-state
```

---

## 7. How to Configure This Agent for Yourself

If you download this repository, follow these steps to configure and run the competitive intelligence agent for your own domain and competitors:

### Step 1: Install Dependencies
Ensure you have Python 3.9+ installed, then activate your virtual environment and install the required libraries:
```bash
# From the project root folder (pm-competitive-intel-agent)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Configure Your API Key & SMTP Settings (Optional)
If you are running the agent locally using **Ollama**, you do not need any LLM API keys! Simply ensure Ollama is running (`ollama serve`) and the model is pulled (`ollama pull llama3.1`).

If you prefer to run a commercial cloud model (e.g. Gemini, GPT, Claude):
1.  Copy the template `.env.example` to a new file named `.env`:
    ```bash
    cp .env.example .env
    ```
2.  Open `.env` and fill in your details:
    *   **`LLM_API_KEY`**: Paste your provider's API key.
    *   **SMTP Variables (Optional)**: If you want reports delivered to your inbox instead of auto-opening in your browser:
        *   `SMTP_USERNAME`: Your sender email address.
        *   `SMTP_PASSWORD`: Your 16-character App Password (generated in Google Account Security).
        *   `REPORT_TO_EMAIL`: The recipient email address.

### Step 3: Customize Targeting in `config.yaml`
Open [`config.yaml`](config.yaml) and customize it for your product domain:
1.  **`domain`**: Update the `primary` domain (e.g. *"corporate fitness software"*) and `focus_subdomain` (e.g. *"wearable integration"*).
2.  **`competitors`**: Update the list with the names of companies you want to track, along with any optional blog or news feed URLs in their `sources` list.
3.  **`watchlist`**: Define industry publications, awards, or conferences (like *"Gartner"*, *"CES"*) to watch.
4.  **`schedule`**: Adjust the delivery time and timezone.

### Step 4: Run the Agent & View Results
Execute the main orchestrator script locally in test mode. This simulates the run, checks the web, prints the cost analysis, and writes the output reports to `state/` without committing state or sending emails:
```bash
python src/run_agent.py --test-mode
```
*   **Where to see the results:**
    *   **Auto-Open Dashboard:** On local desktop runs, your default web browser will automatically open to display the formatted HTML report dashboard.
    *   **Generated Files:** The outputs are written directly to your workspace:
        *   HTML Dashboard: [`state/latest_report.html`](state/latest_report.html)
        *   Markdown Digest: [`state/latest_report.md`](state/latest_report.md)

Once you are ready to persist states and send the daily digest report to your email, run:
```bash
python src/run_agent.py
```

### Step 5: How to Use Preference Memory (Local Loop)
The agent utilizes an in-context **Preference Memory** to prioritize or demote updates dynamically based on your feedback. Since the agent executes locally, you can record your preferences by simply editing your local state file:

1.  **Open the local preference file:** Open [`state/preference_memory.yaml`](state/preference_memory.yaml) (if it doesn't exist, you can create it).
2.  **Add your preference votes:** Add structured feedback entries using the following YAML format:
    ```yaml
    - competitor: "Tesla"
      vote: "useful"
    - competitor: "Xiaomi"
      vote: "not-useful"
      reasons:
        - "Routine thought-leadership content with no news"
    ```
3.  **LLM Integration:** On the next pipeline run, the agent will load these feedback logs, compile them into a preference summary, and inject them into the local model prompt context during the ranking step to dynamically adjust priority.


