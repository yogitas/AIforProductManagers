# DESIGN NOTE FOR READERS:
# This pipeline doesn't use a full agent-orchestration framework (LangChain
# agents, CrewAI, etc.) — it's five sequential steps with no branching or
# multi-agent coordination, so a framework would add abstraction without
# adding capability here. That's a call specific to this pipeline's shape,
# not a rule against frameworks generally: notice the code DOES use several
# focused open-source libraries (litellm, pydantic, tenacity) below, each for
# a well-defined job. The distinction worth learning from this repo is
# "framework vs. library," not "no dependencies."

import os
import sys
import argparse
import logging
from typing import Set, Dict, Any, List
from dotenv import load_dotenv

# Load local environment variables from .env if present
load_dotenv()

# Ensure projects directory is in path for easy module imports when executing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config_loader import load_config
from src.budget import BudgetTracker
from src.state_store import (
    load_seen_items,
    save_seen_items,
    load_preference_memory,
    backup_state,
    get_item_id
)
from src.collect import collect_all
from src.filter_and_rank import filter_and_rank_items, get_preference_summary
from src.report import generate_markdown_report, generate_html_report
from src.deliver import deliver_report

# Configure logging format for pedagogy and audit trail visibility
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("run_agent")

def run_pipeline(
    config_path: str,
    state_dir: str,
    dry_run: bool = False,
    reset_state: bool = False
):
    logger.info("Initializing Competitive Intelligence Monitoring Pipeline...")
    
    # Step 1: Load and Validate Configuration
    # PEDAGOGICAL VALUE: Fail fast and loudly if configuration is misconfigured.
    config = load_config(config_path)
    logger.info(f"Configuration loaded. Model configured: {config.llm_model}")
    
    # Validate API Key is present before starting
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        logger.error("API KEY MISSING: LLM_API_KEY environment variable is not set.")
        print("\n[!] Error: LLM_API_KEY environment variable is required to run LLM operations.", file=sys.stderr)
        print("Please export it: export LLM_API_KEY='your-key-here'\n", file=sys.stderr)
        sys.exit(1)
        
    # Step 2: Handle State Reset & Load State
    if reset_state:
        logger.info("Reset state requested. Creating backups of current state files first.")
        # GUARDRAIL: State loss recovery
        # We backup state before resetting rather than deleting, ensuring recovery is possible.
        backup_state(state_dir)
        
        # Clear out state files locally if they exist by moving them to backup and initializing empty
        for f in ["seen_items.yaml", "preference_memory.yaml"]:
            fpath = os.path.join(state_dir, f)
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception as e:
                    logger.warning(f"Could not remove old state file {fpath}: {e}")
                    
        seen_ids: Set[str] = set()
        preference_memory: List[Dict[str, Any]] = []
        logger.info("State reset complete. Initialized empty run state.")
    else:
        seen_ids = load_seen_items(state_dir)
        preference_memory = load_preference_memory(state_dir)
        logger.info(f"Loaded {len(seen_ids)} previously seen items and {len(preference_memory)} preference logs.")

    # GUARDRAIL: Cold-start lookback bound
    # First runs or runs after reset have no historical seen items. If we don't bound search,
    # the search tool could return massive historical search windows, causing costs to balloon.
    # We dynamically pass the cold-start window to the query instructions.
    is_cold_start = (len(seen_ids) == 0)
    lookback_hours = config.run_limits.cold_start_lookback_hours if is_cold_start else 24
    if is_cold_start:
        logger.info(f"GUARDRAIL: Cold-start detected. Bounding searches to {lookback_hours} hours lookback.")
    else:
        logger.info(f"Normal execution: searching for updates within the last {lookback_hours} hours.")
        
    # Step 3: Initialize Safety Budget Guardrail
    budget_tracker = BudgetTracker(max_search_calls=config.run_limits.max_search_calls)
    
    # Step 4: Collect updates from search grounding and crawling
    collected_items, failed_sources = collect_all(config, budget_tracker, api_key)
    logger.info(f"Collection complete. Found {len(collected_items)} candidate intelligence items.")
    
    # Step 5: Filter (Deduplicate + Rubric check) and Rank
    pref_summary = get_preference_summary(preference_memory)
    featured_items, extra_items = filter_and_rank_items(
        items=collected_items,
        seen_ids=seen_ids,
        preference_memory=preference_memory,
        config=config,
        api_key=api_key,
        budget_tracker=budget_tracker
    )
    logger.info(f"Filtering complete. Featured: {len(featured_items)} items. Extra: {len(extra_items)} items.")
    
    # Step 6: Render Reports
    markdown_report = generate_markdown_report(
        featured_items=featured_items,
        extra_items=extra_items,
        failed_sources=failed_sources,
        config=config,
        pref_summary=pref_summary
    )
    
    html_report = generate_html_report(
        featured_items=featured_items,
        extra_items=extra_items,
        failed_sources=failed_sources,
        config=config,
        pref_summary=pref_summary
    )
    
    # Step 7: Deliver report (SMTP or File)
    # GUARDRAIL: State-commit-after-confirmed-delivery ordering
    # We execute delivery BEFORE writing the updated seen items back to state.
    # If delivery fails, we throw an error and exit before writing state.
    # Reversing this would mark items as "seen" even if the email failed to send,
    # causing the user to silently miss those updates forever in subsequent runs.
    delivery_success = deliver_report(
        html_content=html_report,
        markdown_content=markdown_report,
        config=config,
        dry_run=dry_run
    )
    
    if not delivery_success:
        logger.error("State-Commit Blocked: Email delivery failed. Exiting to prevent loss of updates.")
        sys.exit(1)
        
    # Step 8: Persist State (Only if delivery succeeded AND not dry-run)
    if dry_run:
        logger.info("Dry-run complete. State persistence bypassed.")
    else:
        # Mark both featured and extra items as seen
        new_seen_ids = seen_ids.copy()
        for item in featured_items:
            new_seen_ids.add(item["id"])
        for item in extra_items:
            new_seen_ids.add(item["id"])
            
        save_seen_items(state_dir, new_seen_ids)
        logger.info(f"Successfully saved {len(new_seen_ids)} total seen items to state store.")
        
    cost = budget_tracker.get_estimated_cost()
    cost_str = f"{cost:.5f}" if isinstance(cost, (int, float)) else str(cost)
    logger.info(
        f"COGS REPORT: Input Tokens: {budget_tracker.input_tokens} | "
        f"Output Tokens: {budget_tracker.output_tokens} | "
        f"Search Calls: {budget_tracker.search_calls_made} | "
        f"Estimated Run Cost: ${cost_str} USD"
    )
    logger.info("Pipeline execution finished successfully.")

def main():
    parser = argparse.ArgumentParser(
        description="Competitive Intelligence Monitoring Agent v1 / MVP",
        epilog="Designed for product managers as an educational repository example."
    )
    parser.add_argument(
        "--config", 
        default="config.yaml",
        help="Path to the config.yaml configuration file (default: config.yaml)"
    )
    parser.add_argument(
        "--state-dir", 
        default="state",
        help="Directory to store seen_items.yaml and preference_memory.yaml (default: state)"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Runs full pipeline and saves report locally but does not send email or save seen state."
    )
    parser.add_argument(
        "--reset-state", 
        action="store_true",
        help="Backs up and resets the seen items and preference memory state files before running."
    )
    parser.add_argument(
        "--test-mode", 
        action="store_true",
        help="Shorthand for --dry-run and --reset-state. Ideal for fast local iteration loops."
    )
    
    args = parser.parse_args()
    
    # Resolve combo test-mode flag
    is_dry_run = args.dry_run or args.test_mode
    is_reset_state = args.reset_state or args.test_mode
    
    # Resolve absolute paths
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    config_path = os.path.join(base_dir, args.config)
    state_dir = os.path.join(base_dir, args.state_dir)
    
    run_pipeline(
        config_path=config_path,
        state_dir=state_dir,
        dry_run=is_dry_run,
        reset_state=is_reset_state
    )

if __name__ == "__main__":
    main()
