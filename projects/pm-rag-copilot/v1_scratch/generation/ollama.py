"""
STEP 7: Local LLM Calling (Ollama)
Sends the augmented prompt to a local Ollama model (e.g. llama3.1) via HTTP API.
"""

import os
import requests
from typing import Dict, Any


class OllamaClient:
    """HTTP client for local Ollama inference."""

    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.1")

    def generate(self, prompt: str, temperature: float = 0.1) -> str:
        """Sends prompt to local Ollama and returns the answer text."""
        endpoint = f"{self.base_url.rstrip('/')}/api/generate"
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }

        try:
            response = requests.post(endpoint, json=payload, timeout=90)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(
                f"Failed to communicate with Ollama at {endpoint}. "
                f"Ensure Ollama is running locally (`ollama serve`). Error: {str(e)}"
            )
