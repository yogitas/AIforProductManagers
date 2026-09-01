"""
Mock test to verify the end-to-end flow of the agent pipeline.
Allows verification of code correctness without requiring active network connections or live API keys.
"""
import os
import sys
from unittest.mock import MagicMock, patch

# Add src to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Define mock search response objects matching the Gemini SDK types
mock_grounding_metadata = MagicMock()
mock_chunk1 = MagicMock()
mock_chunk1.web = MagicMock(title="OmniPort Universal Charger Launch", uri="https://example.com/omniport")
mock_grounding_metadata.grounding_chunks = [mock_chunk1]

mock_candidate = MagicMock()
mock_candidate.grounding_metadata = mock_grounding_metadata

mock_search_response = MagicMock()
mock_search_response.text = "ChargePoint announced the universal OmniPort charger today."
mock_search_response.candidates = [mock_candidate]

# Mock LiteLLM Completion responses
mock_extract_completion = MagicMock()
mock_extract_completion.choices = [
    MagicMock(message=MagicMock(content='''[
        {
            "title": "ChargePoint launches OmniPort universal charger",
            "description": "ChargePoint announced OmniPort, a new universal connector solution supporting both Tesla NACS and CCS plugs.",
            "url": "https://example.com/omniport",
            "competitor": "ChargePoint"
        }
    ]'''))
]

mock_materiality_completion = MagicMock()
mock_materiality_completion.choices = [
    MagicMock(message=MagicMock(content='{"is_material": true, "reason": "Universal charger connector hardware launch"}'))
]

mock_ranking_completion = MagicMock()
from src.state_store import get_item_id
item_id = get_item_id("https://example.com/omniport", "ChargePoint launches OmniPort universal charger")
mock_ranking_completion.choices = [
    MagicMock(message=MagicMock(content=f'{{"ranked_ids": ["{item_id}"]}}'))
]

def dynamic_litellm_mock(model, messages, **kwargs):
    """
    Dynamically returns mock LLM responses based on the prompt content.
    Prevents StopIteration errors when running against multiple items.
    """
    prompt = messages[0]["content"]
    
    if "Extract a list of discrete updates" in prompt:
        return mock_extract_completion
    elif "Classify the following competitor update" in prompt:
        return mock_materiality_completion
    elif "rank the following competitive updates" in prompt:
        return mock_ranking_completion
        
    # Default fallback
    return mock_materiality_completion

def dynamic_get_mock(url, *args, **kwargs):
    """
    Dynamically mocks network requests.
    Returns valid HTML snippets for DDG search results, and 404 for crawl checks.
    """
    mock_response = MagicMock()
    if "duckduckgo.com" in url:
        mock_response.status_code = 200
        mock_response.text = """
        <div class="result">
            <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fomniport">OmniPort Universal Charger Launch</a>
            <a class="result__snippet">ChargePoint announced the universal OmniPort charger today.</a>
        </div>
        """
    else:
        mock_response.status_code = 404
    return mock_response

@patch("litellm.completion")
@patch("requests.get")
def run_mock_verification_test(mock_get, mock_litellm):
    print("Initializing mock objects...")
    
    # 1. Apply the dynamic side-effects to request and LLM mocks
    mock_get.side_effect = dynamic_get_mock
    mock_litellm.side_effect = dynamic_litellm_mock
    
    # Map required environment variables for mock run
    os.environ["LLM_API_KEY"] = "mock-key-value"
    
    # Import and run orchestrator
    from src.run_agent import run_pipeline
    
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    config_path = os.path.join(project_root, "config.yaml")
    state_dir = os.path.join(project_root, "state")
    
    print("Executing run_pipeline with dry-run and reset-state...")
    run_pipeline(
        config_path=config_path,
        state_dir=state_dir,
        dry_run=True,
        reset_state=True
    )
    print("\nMOCK PIPELINE INTEGRATION VERIFICATION: PASSED SUCCESSFULLY!")

def run_date_heuristic_unit_tests():
    print("\nRunning unit tests for date filtering heuristic...")
    from src.filter_and_rank import parse_date_from_item, is_item_outdated_heuristic
    from datetime import datetime
    
    # Test case 1: YYYY/MM/DD in URL path
    item = {"title": "Test Title", "url": "https://example.com/2026/08/20/page"}
    parsed = parse_date_from_item(item)
    assert parsed == datetime(2026, 8, 20), f"Expected 2026-08-20, got {parsed}"
    
    # Test case 2: "Month DD, YYYY" in text
    item = {"title": "Updated on Aug 26, 2026", "url": "https://example.com/page"}
    parsed = parse_date_from_item(item)
    assert parsed == datetime(2026, 8, 26), f"Expected 2026-08-26, got {parsed}"
    
    # Test case 3: "date" field check
    item = {"title": "Title", "url": "https://example.com/page", "date": "2 days ago"}
    parsed = parse_date_from_item(item)
    assert parsed is not None
    assert (datetime.now() - parsed).days in [1, 2, 3], f"Expected 2 days age, got parsed: {parsed}"
    
    # Test case 4: Outdated item check
    current_date = datetime(2026, 8, 29)
    item = {"title": "Title", "url": "https://example.com/page", "date": "2025-06-30"}
    is_outdated = is_item_outdated_heuristic(item, current_date)
    assert is_outdated is True, "Expected item from 2025 to be outdated"
    
    # Test case 5: Recent item check
    item = {"title": "Title", "url": "https://example.com/page", "date": "2026-08-25"}
    is_outdated = is_item_outdated_heuristic(item, current_date)
    assert is_outdated is False, "Expected item from 2026-08-25 to be recent"

    print("All date heuristic unit tests PASSED!")

if __name__ == "__main__":
    try:
        run_date_heuristic_unit_tests()
        run_mock_verification_test()
    except Exception as e:
        print(f"\nVerification test failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
