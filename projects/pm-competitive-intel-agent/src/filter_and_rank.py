"""
Filters and ranks candidate intelligence items.

Materiality Rubric:

Report:
- Product launches or major feature releases
- Pricing or packaging changes
- Funding, M&A, or major partnerships
- Leadership changes (C-suite, VP and above)
- Regulatory actions or compliance news
- Public statements on strategy or roadmap direction
- Award nominations/wins or conference announcements naming a tracked competitor

Suppress:
- Routine thought-leadership content with no news
- Minor UI tweaks or bug-fix release notes
- Generic marketing or social engagement posts
- Anything without a verifiable source URL — no URL, no inclusion, no exceptions
"""
import os
import json
import logging
from typing import List, Dict, Any, Tuple, Set, Optional
import litellm
from tenacity import retry, stop_after_attempt, wait_exponential

from src.state_store import get_item_id

logger = logging.getLogger(__name__)

# Reusable tenacity configuration for LLM classification calls
llm_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)

def render_template(template_str: str, context: dict) -> str:
    """
    Renders simple double-brace templates without external template-engine dependencies.
    Supports both {{ var }} and {{var}} syntax.
    """
    rendered = template_str
    for k, v in context.items():
        rendered = rendered.replace(f"{{{{ {k} }}}}", str(v))
        rendered = rendered.replace(f"{{{{{k}}}}}", str(v))
    return rendered

@llm_retry
def check_materiality_with_llm(
    item: Dict[str, Any],
    primary_domain: str,
    model: str,
    api_key: str,
    budget_tracker: Any = None
) -> Tuple[bool, str]:
    """
    Uses LiteLLM and the shared prompt template to classify an item as material or noise.
    
    PROVIDER NOTE: Uses LiteLLM for model-agnostic classification. Swap model/provider easily in config.yaml.
    """
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "materiality_prompt.txt")
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Materiality prompt template not found at {prompt_path}")
        
    with open(prompt_path, "r", encoding="utf-8") as f:
        template = f.read()
        
    prompt = render_template(template, {
        "primary_domain": primary_domain,
        "competitor": item["competitor"],
        "title": item["title"],
        "description": item["description"]
    })
    
    response = litellm.completion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        api_key=api_key,
        temperature=0.0,  # Temperature 0.0 for deterministic classification in production/evals
        response_format={"type": "json_object"},
        timeout=30
    )
    
    if budget_tracker and hasattr(response, "usage") and response.usage:
        budget_tracker.add_tokens(
            input_tokens=getattr(response.usage, "prompt_tokens", 0),
            output_tokens=getattr(response.usage, "completion_tokens", 0)
        )
    
    content = response.choices[0].message.content or ""
    try:
        data = json.loads(content)
        return bool(data.get("is_material", False)), data.get("reason", "No reason provided")
    except Exception as e:
        logger.error(f"Failed to parse materiality classification JSON output: {content}. Error: {e}")
        # Default to False (suppress) in case of system parsing failures
        return False, "Failed to parse classification output"

def get_preference_summary(preference_memory: List[Dict[str, Any]]) -> str:
    """
    Summarizes historical user feedback into an in-context string representation.
    
    PEDAGOGICAL NOTE FOR READERS:
    This preference summary is injected directly into the prompt context for the ranking step.
    This is an in-context learning heuristic, NOT model fine-tuning. Model weights are unchanged.
    This provides lightweight adaptation to user choices without retraining overhead.
    """
    if not preference_memory:
        return "No user preference history recorded yet."
        
    useful_count = 0
    not_useful_count = 0
    reasons_freq = {}
    
    for entry in preference_memory:
        vote = entry.get("vote")
        if vote == "useful":
            useful_count += 1
        elif vote == "not-useful":
            not_useful_count += 1
            for reason in entry.get("reasons", []):
                reasons_freq[reason] = reasons_freq.get(reason, 0) + 1
                
    summary_parts = [
        f"The user has reviewed {len(preference_memory)} reports.",
        f"- Marked as useful (thumbs-up): {useful_count} items.",
        f"- Marked as not-useful (thumbs-down): {not_useful_count} items."
    ]
    
    if reasons_freq:
        summary_parts.append("Specific reasons for marking items as not-useful:")
        for r, freq in sorted(reasons_freq.items(), key=lambda x: x[1], reverse=True):
            summary_parts.append(f"  * \"{r}\": disliked {freq} times")
            
    return "\n".join(summary_parts)

def fallback_ranking(items: List[Dict[str, Any]], focus_subdomain: Optional[str]) -> List[Dict[str, Any]]:
    """
    A deterministic fallback sorting heuristic.
    Pushes focus subdomain items to the top, maintaining insertion order otherwise.
    """
    if not focus_subdomain:
        # Default flag focus subdomain as False
        for item in items:
            item["is_focus"] = False
        return items
        
    subdomain_items = []
    other_items = []
    
    for item in items:
        # Simple text matching for subdomain relevance
        text = f"{item['title']} {item['description']}".lower()
        if focus_subdomain.lower() in text:
            item["is_focus"] = True
            subdomain_items.append(item)
        else:
            item["is_focus"] = False
            other_items.append(item)
            
    return subdomain_items + other_items

@llm_retry
def run_llm_ranking(
    items: List[Dict[str, Any]],
    focus_subdomain: Optional[str],
    pref_summary: str,
    model: str,
    api_key: str,
    budget_tracker: Any = None
) -> List[str]:
    """
    Invokes LiteLLM to rank the list of items based on focus subdomain and user preferences.
    Returns a list of ranked item IDs.
    """
    # Create simplified representation of items for prompt size efficiency
    items_to_rank = []
    for item in items:
        items_to_rank.append({
            "id": item["id"],
            "competitor": item["competitor"],
            "title": item["title"],
            "description": item["description"]
        })
        
    prompt = f"""
    You are an expert Competitive Intelligence analyst.
    You need to rank the following competitive updates for today's daily digest.
    
    Focus Subdomain: {focus_subdomain or "None specified"}
    (Items matching or relevant to the focus subdomain should be prioritized and ranked at the very top).
    
    User Preference History (Heuristic preference summary, NOT model fine-tuning):
    {pref_summary}
    (Use these preferences to adjust ranking. Demote types of updates the user historically marked as not-useful).
    
    Items to rank:
    {json.dumps(items_to_rank, indent=2)}
    
    Respond with a JSON object containing a single key "ranked_ids" mapping to a list of the item IDs in order from highest priority to lowest priority.
    Respond ONLY with valid, parseable JSON. Do not output anything else.
    """
    
    response = litellm.completion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        api_key=api_key,
        temperature=0.1,
        response_format={"type": "json_object"},
        timeout=30
    )
    
    if budget_tracker and hasattr(response, "usage") and response.usage:
        budget_tracker.add_tokens(
            input_tokens=getattr(response.usage, "prompt_tokens", 0),
            output_tokens=getattr(response.usage, "completion_tokens", 0)
        )
    
    content = response.choices[0].message.content or ""
    data = json.loads(content)
    return data.get("ranked_ids", [])

def filter_and_rank_items(
    items: List[Dict[str, Any]],
    seen_ids: Set[str],
    preference_memory: List[Dict[str, Any]],
    config: Any,
    api_key: str,
    budget_tracker: Any = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Orchestrates the filtering and ranking pipeline steps:
    1. Deduplicates against seen items. If item was already seen previous day, removes it
    2. Performs LLM materiality classification. Check the rubric in prompts/materiality_promt.txt
    3. Runs preference-weighted ranking.Preference are given by user.
    4. Segregates items into primary featured items and excess items based on config caps.
    """
    filtered_items = []
    
    # --- Step 1: Deduplication ---
    for item in items:
        # Generate item ID based on URL or title
        item_id = get_item_id(item.get("url", ""), item["title"])
        item["id"] = item_id
        
        if item_id in seen_ids:
            logger.info(f"Filtered out duplicate item: {item['title']} (ID: {item_id})")
            continue
            
        filtered_items.append(item)
        
    if not filtered_items:
        return [], []
        
    # --- Step 2: Materiality Filtering ---
    material_items = []
    for item in filtered_items:
        is_material, reason = check_materiality_with_llm(
            item=item,
            primary_domain=config.domain.primary,
            model=config.llm_model,
            api_key=api_key,
            budget_tracker=budget_tracker
        )
        item["materiality_reason"] = reason
        if is_material:
            logger.info(f"Item classified as MATERIAL: {item['title']}")
            material_items.append(item)
        else:
            logger.info(f"Item classified as NOISE: {item['title']} (Reason: {reason})")
            
    if not material_items:
        return [], []
        
    # --- Step 3: Preference-Weighted Ranking ---
    pref_summary = get_preference_summary(preference_memory)
    focus_subdomain = config.domain.focus_subdomain
    
    # Initialize focus flag on all material items
    for item in material_items:
        text = f"{item['title']} {item['description']}".lower()
        item["is_focus"] = bool(focus_subdomain and focus_subdomain.lower() in text)
        
    try:
        ranked_ids = run_llm_ranking(
            items=material_items,
            focus_subdomain=focus_subdomain,
            pref_summary=pref_summary,
            model=config.llm_model,
            api_key=api_key,
            budget_tracker=budget_tracker
        )
        
        # Reorder items based on LLM ranked_ids
        ranked_map = {item["id"]: item for item in material_items}
        final_ranked = []
        for rid in ranked_ids:
            if rid in ranked_map:
                final_ranked.append(ranked_map.pop(rid))
                
        # Append any items that the LLM forgot to return in its ranking
        final_ranked.extend(ranked_map.values())
        logger.info("LLM ranking completed successfully.")
    except Exception as e:
        logger.exception("LLM ranking failed. Falling back to deterministic subdomain-priority sorting.")
        final_ranked = fallback_ranking(material_items, focus_subdomain)
        
    # --- Step 4: Cap Report Sizes ---
    # GUARDRAIL: Report size cap
    # Unbounded reports lead to information fatigue for readers and high mail sizes.
    # We enforce a max_report_items cap, summarizing extra items at the bottom.
    max_items = config.run_limits.max_report_items
    featured_items = final_ranked[:max_items]
    extra_items = final_ranked[max_items:]
    
    return featured_items, extra_items
