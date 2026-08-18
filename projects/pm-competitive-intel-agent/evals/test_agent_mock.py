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

@patch("google.genai.Client")
@patch("litellm.completion")
@patch("requests.get")
def run_mock_verification_test(mock_get, mock_litellm, mock_genai_client):
    print("Initializing mock objects...")
    
    # 1. Mock the Google GenAI Client
    mock_client_instance = MagicMock()
    mock_client_instance.models.generate_content.return_value = mock_search_response
    mock_genai_client.return_value = mock_client_instance
    
    # 2. Mock requests.get for robots.txt files (returning 404 so we bypass checking)
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response
    
    # 3. Apply the dynamic side-effect to LiteLLM completion mock
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

if __name__ == "__main__":
    try:
        run_mock_verification_test()
    except Exception as e:
        print(f"\nVerification test failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
