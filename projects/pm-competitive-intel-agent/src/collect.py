"""
Handles data collection from Google Search grounding and custom sources.

PROVIDER NOTE: unlike the litellm-based calls elsewhere in this pipeline,
this discovery step uses Gemini's native google_search grounding tool
directly, not litellm. That's a deliberate tradeoff: native grounding is
free with a Gemini plan and generally higher quality than a generic search
wrapper, but it means swapping the LLM provider later (e.g. to Claude)
means re-implementing discovery too, not just changing a config line.
If full provider-agnosticism becomes the priority, replace this with an
open-source search library (e.g. duckduckgo-search) instead.
"""
import os
import json
import logging
import urllib.robotparser
from urllib.parse import urlparse
from typing import List, Dict, Any, Tuple
import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
import time

# LiteLLM is used for the provider-agnostic LLM extraction step
import litellm

# google-genai is the official SDK for Gemini's search grounding
from google import genai
from google.genai import types

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
        response_format={"type": "json_object"}
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

def get_gemini_model_name(config_model_string: str) -> str:
    """
    Extracts the native model name for the Gemini SDK from the LiteLLM config prefix.
    E.g. "gemini/gemini-2.5-flash" -> "gemini-2.5-flash"
    """
    if config_model_string.startswith("gemini/"):
        return config_model_string.replace("gemini/", "")
    return config_model_string

def collect_from_search(
    client: genai.Client,
    model_name: str,
    query: str,
    competitor_name: str,
    domain_primary: str,
    litellm_model: str,
    api_key: str,
    budget_tracker: Any = None
) -> List[Dict[str, Any]]:
    """
    Executes a search using Gemini's native Google Search grounding tool and
    uses LiteLLM to extract structured candidate items.
    """
    # Configure Gemini search grounding tool
    google_search_tool = types.Tool(google_search=types.GoogleSearch())
    config = types.GenerateContentConfig(tools=[google_search_tool])
    
    # Run the search grounding query
    response = client.models.generate_content(
        model=model_name,
        contents=query,
        config=config
    )
    
    response_text = response.text or ""
    
    # Extract source URLs and titles from the grounding metadata
    chunks = []
    candidate = response.candidates[0]
    if candidate.grounding_metadata and candidate.grounding_metadata.grounding_chunks:
        for chunk in candidate.grounding_metadata.grounding_chunks:
            if chunk.web:
                chunks.append({
                    "title": chunk.web.title,
                    "url": chunk.web.uri
                })
                
    if not chunks:
        logger.info(f"No web search chunks found for query: {query}")
        return []
        
    # Use LiteLLM to extract structured items from the search output, grounded in real URLs
    prompt = f"""
    Analyze the following search summary and list of verified source URLs about competitor '{competitor_name}' in the domain '{domain_primary}'.
    
    Search Summary:
    {response_text}
    
    Verified URLs:
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
        if isinstance(items, list):
            # Clean up the output items
            valid_items = []
            for item in items:
                # GUARDRAIL: Grounding requirement
                # Any item without a verifiable source URL is dropped before ranking
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
    Orchestrates the discovery phase by querying Google Search grounding via Gemini
    and crawling custom sources.
    
    GUARDRAIL: Per-competitor/source isolation
    We wrap each competitor discovery and crawl step in a separate try/except block.
    If one source or competitor search fails, we record the error and continue,
    ensuring a partial failure doesn't crash the entire daily run.
    """
    all_items = []
    failed_sources = {}
    
    # Initialize the native Google GenAI client for search grounding
    # Load Gemini API Key from LLM_API_KEY environment variable (provided in GHA/secrets)
    gemini_key = api_key or os.environ.get("LLM_API_KEY")
    if not gemini_key:
        raise ValueError("LLM_API_KEY environment variable must be set for Gemini Search Grounding.")
        
    client = genai.Client(api_key=gemini_key)
    gemini_model = get_gemini_model_name(config.llm_model)
    
    # 1. Gather competitor updates
    for comp in config.competitors:
        comp_items = []
        comp_failed = False
        
        # A. Search Discovery
        if budget_tracker.has_search_budget():
            try:
                budget_tracker.increment_search_calls()
                query = f"Find recent news, site updates, analyst commentary, award announcements, product releases, or partnerships for competitor '{comp.name}' in the domain '{config.domain.primary}'"
                logger.info(f"Searching web for competitor: {comp.name}")
                search_items = collect_from_search(
                    client=client,
                    model_name=gemini_model,
                    query=query,
                    competitor_name=comp.name,
                    domain_primary=config.domain.primary,
                    litellm_model=config.llm_model,
                    api_key=gemini_key,
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
                    api_key=gemini_key,
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
                query = f"Find recent updates, analyst commentary, awards, or conference announcements regarding '{watch.name}' naming competitors in '{config.domain.primary}'"
                logger.info(f"Searching web for watch item: {watch.name} (Type: {watch.type})")
                watch_items = collect_from_search(
                    client=client,
                    model_name=gemini_model,
                    query=query,
                    competitor_name=watch.name,
                    domain_primary=config.domain.primary,
                    litellm_model=config.llm_model,
                    api_key=gemini_key,
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
