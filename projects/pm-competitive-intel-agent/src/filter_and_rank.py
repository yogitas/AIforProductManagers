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
import re
import json
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
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
        
    current_date = datetime.now().strftime("%Y-%m-%d")
    prompt = render_template(template, {
        "primary_domain": primary_domain,
        "competitor": item["competitor"],
        "title": item["title"],
        "description": item["description"],
        "url": item.get("url", ""),
        "current_date": current_date
    })
    
    response = litellm.completion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        api_key=api_key,
        temperature=0.0,  # Temperature 0.0 for deterministic classification in production/evals
        response_format={"type": "json_object"},
        timeout=90
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
            "description": item["description"],
            "url": item.get("url", "")
        })
        
    current_date = datetime.now().strftime("%Y-%m-%d")
    prompt = f"""
    You are an expert Competitive Intelligence analyst.
    You need to rank the following competitive updates for today's daily digest.
    
    Current Date: {current_date}
    
    Ranking Criteria (Apply in priority order):
    1. Focus Subdomain: {focus_subdomain or "None specified"}
       (Items matching or relevant to the focus subdomain should be prioritized and ranked at the top).
    2. Recency: Within sorting categories, updates MUST be ordered from most recent to least recent relative to the Current Date. Look at dates mentioned in the title, description, and source URL path to determine recency.
    3. User Preference History (Heuristic preference summary, NOT model fine-tuning):
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
        timeout=90
    )
    
    if budget_tracker and hasattr(response, "usage") and response.usage:
        budget_tracker.add_tokens(
            input_tokens=getattr(response.usage, "prompt_tokens", 0),
            output_tokens=getattr(response.usage, "completion_tokens", 0)
        )
    
    content = response.choices[0].message.content or ""
    data = json.loads(content)
    return data.get("ranked_ids", [])

def parse_date_from_item(item: Dict[str, Any]) -> Optional[datetime]:
    """
    Attempts to parse a publication or event date from the item's title, description, or source URL.
    Returns a datetime object if found, otherwise None.
    """
    text = f"{item['title']} {item.get('description', '')}"
    url = item.get("url", "")
    
    # 0. Check the extracted 'date' attribute from LLM collector if present
    extracted_date_str = item.get("date")
    if extracted_date_str and isinstance(extracted_date_str, str):
        date_clean = extracted_date_str.strip()
        
        # Check for relative indicators like "X days ago"
        match_days = re.search(r'\b(\d+)\s+days?\s+ago\b', date_clean, re.IGNORECASE)
        if match_days:
            try:
                days = int(match_days.group(1))
                return datetime.now() - timedelta(days=days)
            except ValueError:
                pass
                
        # Check for relative indicators like "X weeks ago"
        match_weeks = re.search(r'\b(\d+)\s+weeks?\s+ago\b', date_clean, re.IGNORECASE)
        if match_weeks:
            try:
                weeks = int(match_weeks.group(1))
                return datetime.now() - timedelta(weeks=weeks)
            except ValueError:
                pass

        # Try to parse YYYY-MM-DD from extracted date
        match_ymd = re.search(r'\b(\d{4})-(\d{2})-(\d{2})\b', date_clean)
        if match_ymd:
            try:
                return datetime(int(match_ymd.group(1)), int(match_ymd.group(2)), int(match_ymd.group(3)))
            except ValueError:
                pass
                
        # Append extracted date to text pool to run other month/year regex parses on it too
        text = date_clean + " | " + text
    
    # 1. Check for YYYY/MM/DD in URL path
    match_url_ymd = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
    if match_url_ymd:
        try:
            return datetime(int(match_url_ymd.group(1)), int(match_url_ymd.group(2)), int(match_url_ymd.group(3)))
        except ValueError:
            pass
            
    # 2. Check for YYYY/MM in URL path
    match_url_ym = re.search(r'/(\d{4})/(\d{2})/', url)
    if match_url_ym:
        try:
            return datetime(int(match_url_ym.group(1)), int(match_url_ym.group(2)), 1)
        except ValueError:
            pass

    months = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }
    
    def parse_month(m_str: str) -> int:
        return months.get(m_str.lower()[:3], 1)

    # 3. Check for "Month DD, YYYY" in text (e.g. Aug 26, 2026)
    match_month_dd_yyyy = re.search(
        r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* \d{1,2},? (\d{4})\b', 
        text, 
        re.IGNORECASE
    )
    if match_month_dd_yyyy:
        try:
            m = parse_month(match_month_dd_yyyy.group(1))
            d_match = re.search(r'\b\d{1,2}\b', match_month_dd_yyyy.group(0))
            d = int(d_match.group(0)) if d_match else 1
            y = int(match_month_dd_yyyy.group(2))
            return datetime(y, m, d)
        except ValueError:
            pass

    # 4. Check for "DD Month YYYY" in text (e.g. 26 Aug 2026)
    match_dd_month_yyyy = re.search(
        r'\b\d{1,2} (jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* (\d{4})\b', 
        text, 
        re.IGNORECASE
    )
    if match_dd_month_yyyy:
        try:
            m = parse_month(match_dd_month_yyyy.group(1))
            d_match = re.search(r'\b\d{1,2}\b', match_dd_month_yyyy.group(0))
            d = int(d_match.group(0)) if d_match else 1
            y = int(match_dd_month_yyyy.group(2))
            return datetime(y, m, d)
        except ValueError:
            pass

    # 5. Check for YYYY-MM-DD in text or URL
    match_ymd = re.search(r'\b(\d{4})-(\d{2})-(\d{2})\b', text + " " + url)
    if match_ymd:
        try:
            return datetime(int(match_ymd.group(1)), int(match_ymd.group(2)), int(match_ymd.group(3)))
        except ValueError:
            pass

    # 6. Fallback Year check: If a year is mentioned, check if it's strictly in the past
    years = re.findall(r'\b(19\d\d|20\d\d)\b', text + " " + url)
    if years:
        for y_str in years:
            try:
                y = int(y_str)
                # If the year is different from the current year, return it as mid-year (estimating age)
                if y != datetime.now().year:
                    return datetime(y, 6, 30)
            except ValueError:
                continue

    return None

def get_date_from_meta_tags(html: str) -> Optional[datetime]:
    """
    Scans HTML head meta tags and JSON-LD schema for publication dates.
    Returns datetime object if found, otherwise None.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return None
        
    meta_queries = [
        ("property", "article:published_time"),
        ("property", "og:published_time"),
        ("name", "pubdate"),
        ("name", "publish-date"),
        ("name", "date"),
        ("name", "dcterms.created"),
        ("name", "dcterms.date"),
        ("property", "og:updated_time")
    ]
    for attr, name in meta_queries:
        tag = soup.find("meta", attrs={attr: name})
        if tag and tag.get("content"):
            date_str = tag["content"]
            match_ymd = re.search(r'\b(\d{4})-(\d{2})-(\d{2})\b', date_str)
            if match_ymd:
                try:
                    return datetime(int(match_ymd.group(1)), int(match_ymd.group(2)), int(match_ymd.group(3)))
                except ValueError:
                    pass

    # Inspect JSON-LD schema
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            if not script.string:
                continue
            schema_text = script.string.strip()
            match_published = re.search(r'"datePublished"\s*:\s*"([^"]+)"', schema_text, re.IGNORECASE)
            if match_published:
                date_str = match_published.group(1)
                match_ymd = re.search(r'\b(\d{4})-(\d{2})-(\d{2})\b', date_str)
                if match_ymd:
                    return datetime(int(match_ymd.group(1)), int(match_ymd.group(2)), int(match_ymd.group(3)))
            
            match_modified = re.search(r'"dateModified"\s*:\s*"([^"]+)"', schema_text, re.IGNORECASE)
            if match_modified:
                date_str = match_modified.group(1)
                match_ymd = re.search(r'\b(\d{4})-(\d{2})-(\d{2})\b', date_str)
                if match_ymd:
                    return datetime(int(match_ymd.group(1)), int(match_ymd.group(2)), int(match_ymd.group(3)))
        except Exception:
            continue
            
    return None

def fetch_date_from_webpage_metadata(url: str) -> Optional[datetime]:
    """
    Fetches the webpage HTML and attempts to parse publication date from meta tags and JSON-LD.
    """
    if not url or not url.startswith("http"):
        return None
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        # Fetch only first 100KB to make this request super fast
        response = requests.get(url, headers=headers, timeout=5, stream=True)
        if response.status_code != 200:
            return None
            
        html_chunks = []
        bytes_read = 0
        for chunk in response.iter_content(chunk_size=2048, decode_unicode=True):
            if not chunk:
                break
            html_chunks.append(chunk)
            bytes_read += len(chunk)
            if bytes_read > 102400: # 100KB limit
                break
                
        html = "".join(html_chunks)
        return get_date_from_meta_tags(html)
    except Exception as e:
        logger.debug(f"Failed to fetch metadata date for {url}: {e}")
        return None

def is_item_outdated_heuristic(item: Dict[str, Any], current_date: datetime) -> bool:
    """
    Determines if an item is outdated by checking if its parsed date is older than 28 days (4 weeks).
    """
    parsed_date = parse_date_from_item(item)
    
    # If no date was parsed from URL/snippet, try fetching webpage metadata directly (deterministic guardrail)
    if not parsed_date:
        url = item.get("url", "")
        metadata_date = fetch_date_from_webpage_metadata(url)
        if metadata_date:
            parsed_date = metadata_date
            # Cache the parsed date back onto the item so we don't fetch it again
            item["date"] = metadata_date.strftime("%Y-%m-%d")
            logger.info(f"Retrieved publication date from metadata for {url}: {item['date']}")
            
    if parsed_date:
        age_days = (current_date - parsed_date).days
        # If the article is more than 28 days old relative to execution time, it is outdated
        if age_days > 28:
            return True
    return False

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
    current_date = datetime.now()
    for item in filtered_items:
        # Heuristic check: Filter out outdated updates older than 28 days (4 weeks)
        if is_item_outdated_heuristic(item, current_date):
            logger.info(f"Heuristically filtered out outdated item: {item['title']}")
            continue
            
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
