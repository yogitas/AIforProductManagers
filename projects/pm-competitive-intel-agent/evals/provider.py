"""
Custom promptfoo provider that leverages litellm to call LLMs.
Allows the eval suite to run against the exact same provider configuration
and environment variables as the production pipeline.
"""
import os
import sys

# Ensure project root is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import litellm

def call_api(prompt, options, context):
    """
    Called by promptfoo.
    prompt: The rendered prompt string (variables substituted by promptfoo).
    options: Config parameters passed from the promptfoo yaml file.
    context: Test case details.
    """
    model = os.environ.get("LLM_MODEL", "ollama/llama3.1")
    api_key = os.environ.get("LLM_API_KEY")
    
    if not api_key and not model.startswith("ollama"):
        return {
            "error": "LLM_API_KEY environment variable is not set. Evals require a valid key."
        }
        
    try:
        response = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            api_key=api_key,
            temperature=0.0,  # 0.0 temperature ensures tests are deterministic
            response_format={"type": "json_object"},
            timeout=90
        )
        output = response.choices[0].message.content or ""
        return {
            "output": output
        }
    except Exception as e:
        return {
            "error": f"LiteLLM call failed: {str(e)}"
        }
