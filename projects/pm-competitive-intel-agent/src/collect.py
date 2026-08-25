"""
Handles data collection from DuckDuckGo HTML search and custom sources.

PROVIDER NOTE: Discovery queries the DuckDuckGo HTML search interface
anonymously, requiring no credentials or paid API keys. LiteLLM is used for the
provider-agnostic extraction step.
"""
import os
import json
import logging
import urllib.robotparser
from urllib.parse import urlparse, parse_qs
from typing import List, Dict, Any, Tuple
import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
import time

# LiteLLM is used for the provider-agnostic LLM extraction step
import litellm

# duckduckgo_search is used for free, local keyless web searches
from duckduckgo_search import DDGS

from src.budget import BudgetTracker

logger = logging.getLogger(__name__)

# Reusable retry configuration for network requests
network_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)

@network_retry
def run_litellm_completion(model: str, messages: list, api_key: str, budget_tracker: Any = None) -> str:
    """
    Executes a LiteLLM chat completion. Wrapped in tenacity to handle transient network errors.
    """
    response = litellm.completion(
        model=model,
        messages=messages,
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
    return response.choices[0].message.content

def check_robots_txt(url: str) -> bool:
    """
    Checks robots.txt for the given URL to ensure crawler compliance.
    
    GUARDRAIL: robots.txt / copyright compliance
    We check robots.txt before fetching external pages to respect site owners' policies.
    """
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = urllib.robotparser.RobotFileParser()
    try:
        # Wrap robots.txt fetch in a quick timeout
        response = requests.get(robots_url, timeout=5)
        if response.status_code == 404:
            return True
        rp.parse(response.text.splitlines())
        return rp.can_fetch("*", url)
    except Exception as e:
        logger.warning(f"Error checking robots.txt for {url}: {e}. Defaulting to allowed.")
        return True

@network_retry
def fetch_url_content(url: str) -> str:
    """
    Fetches raw HTML from a target URL. Wrapped in tenacity retry.
    """
    headers = {"User-Agent": "PMCompetitiveIntelAgent/1.0 (Portfolio Project)"}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.text

def parse_html_to_text(html: str) -> str:
    """
    Extracts text from raw HTML, skipping noise elements like navs, scripts, and footers.
    
    GUARDRAIL: copyright compliance
    We only extract text paragraphs to summarize/paraphrase rather than copy whole pages.
    """
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "nav", "header", "footer", "form"]):
        element.extract()
    text = soup.get_text(separator=" ")
    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    return "\n".join(chunk for chunk in chunks if chunk)

def collect_from_search(
    query: str,
    competitor_name: str,
    domain_primary: str,
    litellm_model: str,
    api_key: str,
    budget_tracker: Any = None
) -> List[Dict[str, Any]]:
    """
    Executes a keyless local search using DuckDuckGo's raw HTML interface.
    Robust, lightweight, and bypasses standard API rate blocks.
    """
    url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            logger.error(f"HTML Search request failed with status code {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Failed to fetch HTML search results for query '{query}': {e}")
        return []
        
    soup = BeautifulSoup(response.text, "html.parser")
    results = soup.find_all("div", class_="result")
    
    chunks = []
    for res in results:
        title_el = res.find("a", class_="result__a")
        snippet_el = res.find("a", class_="result__snippet")
        if title_el:
            title = title_el.text.strip()
            raw_url = title_el.get("href", "")
            
            # Parse destination URL from DDG redirect url
            parsed_url = raw_url
            if raw_url.startswith("//duckduckgo.com/l/"):
                parsed = urlparse(f"https:{raw_url}")
                queries = parse_qs(parsed.query)
                if "uddg" in queries and queries["uddg"]:
                    parsed_url = queries["uddg"][0]
            elif raw_url.startswith("/l/"):
                parsed = urlparse(f"https://duckduckgo.com{raw_url}")
                queries = parse_qs(parsed.query)
                if "uddg" in queries and queries["uddg"]:
                    parsed_url = queries["uddg"][0]
            
            snippet = snippet_el.text.strip() if snippet_el else ""
            chunks.append({
                "title": title,
                "url": parsed_url,
                "snippet": snippet
            })
            
    if not chunks:
        logger.info(f"No web search chunks found for query: {query}")
        return []
        
    # Use LiteLLM to extract structured items from the search output, grounded in real URLs
    prompt = f"""
    Analyze the following search snippets and list of verified source URLs about competitor '{competitor_name}' in the domain '{domain_primary}'.
    
    Search Snippets:
    {json.dumps(chunks, indent=2)}
    
    Extract a list of discrete updates/news items. Each item must have:
    1. "title": A short, descriptive title
    2. "description": A concise 1-2 sentence summary of the update
    3. "url": The exact source URL from the verified list that supports this update. This URL MUST be in the verified list.
    4. "competitor": The name '{competitor_name}'
    
    Respond ONLY with a JSON list of objects matching the schema:
    [
      {{
        "title": "string",
        "description": "string",
        "url": "string",
        "competitor": "string"
      }}
    ]
    Do not return any other text.
    """
    
    messages = [{"role": "user", "content": prompt}]
    json_str = run_litellm_completion(litellm_model, messages, api_key, budget_tracker)
    
    try:
        items = json.loads(json_str)
        if isinstance(items, dict):
            items = [items]
        if isinstance(items, list):
            valid_items = []
            for item in items:
                # GUARDRAIL: Grounding requirement
                if item.get("url") and item.get("title") and item.get("description"):
                    valid_items.append(item)
            return valid_items
    except Exception as e:
        logger.error(f"Failed to parse LLM structured output for competitor {competitor_name}: {e}")
        
    return []

def collect_from_crawl(
    source_url: str,
    competitor_name: str,
    litellm_model: str,
    api_key: str,
    budget_tracker: Any = None
) -> List[Dict[str, Any]]:
    """
    Crawls a specific competitor URL (if allowed by robots.txt) and extracts structured items.
    """
    if not check_robots_txt(source_url):
        logger.warning(f"Crawling disallowed by robots.txt for: {source_url}")
        return []
        
    try:
        html = fetch_url_content(source_url)
        content_text = parse_html_to_text(html)
    except Exception as e:
        logger.error(f"Failed to fetch content from {source_url}: {e}")
        return []
        
    prompt = f"""
    We crawled a webpage from competitor '{competitor_name}' source URL: {source_url}.
    Here is the raw text content:
    
    {content_text[:3000]}
    
    Extract any recent, major news updates or feature releases from this text.
    For each update, provide:
    1. "title": A short, descriptive title
    2. "description": A concise 1-2 sentence summary (paraphrased to comply with copyright).
    3. "url": The exact source URL: "{source_url}"
    4. "competitor": The name '{competitor_name}'
    
    Respond ONLY with a JSON list of objects matching the schema:
    [
      {{
        "title": "string",
        "description": "string",
        "url": "{source_url}",
        "competitor": "{competitor_name}"
      }}
    ]
    If there are no material updates, return an empty list: [].
    Do not return any other text.
    """
    
    messages = [{"role": "user", "content": prompt}]
    json_str = run_litellm_completion(litellm_model, messages, api_key, budget_tracker)
    
    try:
        items = json.loads(json_str)
        if isinstance(items, dict):
            items = [items]
        if isinstance(items, list):
            valid_items = []
            for item in items:
                # GUARDRAIL: Grounding requirement
                if item.get("url") and item.get("title") and item.get("description"):
                    valid_items.append(item)
            return valid_items
    except Exception as e:
        logger.error(f"Failed to parse LLM crawling output for {competitor_name} source {source_url}: {e}")
        
    return []

def collect_all(
    config: Any,
    budget_tracker: BudgetTracker,
    api_key: str
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Orchestrates the discovery phase by querying DuckDuckGo HTML search
    and crawling custom sources.
    
    GUARDRAIL: Per-competitor/source isolation
    We wrap each competitor discovery and crawl step in a separate try/except block.
    If one source or competitor search fails, we record the error and continue,
    ensuring a partial failure doesn't crash the entire daily run.
    """
    all_items = []
    failed_sources = {}
    
    # Initialize keys
    api_key_str = api_key or os.environ.get("LLM_API_KEY", "")
    # Note: For local models like Ollama, API key is not required
    if not api_key_str and not config.llm_model.startswith("ollama"):
        raise ValueError("LLM_API_KEY environment variable must be set for non-local models.")
        
    # 1. Gather competitor updates
    for comp in config.competitors:
        comp_items = []
        comp_failed = False
        
        # A. Search Discovery
        if budget_tracker.has_search_budget():
            try:
                budget_tracker.increment_search_calls()
                query = f"'{comp.name}' {config.domain.focus_subdomain or config.domain.primary} news"
                logger.info(f"Searching web for competitor: {comp.name}")
                search_items = collect_from_search(
                    query=query,
                    competitor_name=comp.name,
                    domain_primary=config.domain.primary,
                    litellm_model=config.llm_model,
                    api_key=api_key_str,
                    budget_tracker=budget_tracker
                )
                comp_items.extend(search_items)
                # Rate limit protection: sleep briefly between search queries to respect API quotas
                time.sleep(5)
            except Exception as e:
                logger.exception(f"Error during search discovery for competitor {comp.name}")
                failed_sources[comp.name] = f"Search discovery failed: {str(e)}"
                comp_failed = True
        else:
            logger.info("Skipping search discovery: no search call budget remaining.")
            
        # B. Direct Crawling of Competitor Sources
        for source_url in comp.sources:
            try:
                logger.info(f"Crawling source URL for competitor {comp.name}: {source_url}")
                crawl_items = collect_from_crawl(
                    source_url=source_url,
                    competitor_name=comp.name,
                    litellm_model=config.llm_model,
                    api_key=api_key_str,
                    budget_tracker=budget_tracker
                )
                comp_items.extend(crawl_items)
            except Exception as e:
                logger.exception(f"Error crawling source {source_url} for competitor {comp.name}")
                failed_sources[f"{comp.name} ({source_url})"] = f"Crawl failed: {str(e)}"
                comp_failed = True
                
        all_items.extend(comp_items)
        
    # 2. Gather watchlist updates
    for watch in config.watchlist:
        # For watchlist items, search general industry mentions
        if budget_tracker.has_search_budget():
            try:
                budget_tracker.increment_search_calls()
                query = f"'{watch.name}' {config.domain.focus_subdomain or config.domain.primary}"
                logger.info(f"Searching web for watch item: {watch.name} (Type: {watch.type})")
                watch_items = collect_from_search(
                    query=query,
                    competitor_name=watch.name,
                    domain_primary=config.domain.primary,
                    litellm_model=config.llm_model,
                    api_key=api_key_str,
                    budget_tracker=budget_tracker
                )
                # Map to watch category
                for item in watch_items:
                    item["competitor"] = f"{watch.name} ({watch.type.capitalize()})"
                all_items.extend(watch_items)
                # Rate limit protection: sleep briefly between search queries to respect API quotas
                time.sleep(5)
            except Exception as e:
                logger.exception(f"Error during search discovery for watch item {watch.name}")
                failed_sources[watch.name] = f"Watch search failed: {str(e)}"
        else:
            logger.info("Skipping watch item search: no search call budget remaining.")
            
    return all_items, failed_sources
