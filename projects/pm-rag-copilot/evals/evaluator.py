"""
Automated Evaluation Graders for RAG Pipeline Metrics.
"""

import json
import re
from typing import Dict, Any, List
from v1_scratch.generation.ollama import OllamaClient


class RAGEvaluator:
    """Evaluates RAG pipeline performance using Heuristics and LLM-as-a-Judge."""

    def __init__(self, model_name: str = "llama3.1"):
        self.ollama = OllamaClient(model=model_name)

    def evaluate_retrieval_hit_rate(self, retrieved_chunks: List[Any], expected_source: str) -> float:
        """Measures if the correct source file was retrieved."""
        if expected_source is None:
            # For out-of-domain/missing context, we expect no retrieval
            return 1.0 if not retrieved_chunks else 0.0

        for chunk in retrieved_chunks:
            source = chunk.metadata.get("source", "")
            # Check if expected filename is a substring of the retrieved source path
            if expected_source.lower() in source.lower():
                return 1.0
        return 0.0

    def evaluate_groundedness(self, context_text: str, answer_text: str) -> Dict[str, Any]:
        """Uses LLM-as-a-Judge to grade if the answer is grounded in retrieved context."""
        # Safeguard fallback is grounded by definition
        if "couldn't find enough information" in answer_text.lower():
            return {"score": 1.0, "reason": "Safeguard fallback triggered correctly."}

        judge_prompt = (
            "You are an impartial AI evaluation judge assessing RAG responses for hallucinations.\n"
            "Task: Decide if the Generated Response is strictly supported by the Provided Context.\n\n"
            f"=== PROVIDED CONTEXT ===\n{context_text}\n\n"
            f"=== GENERATED RESPONSE ===\n{answer_text}\n\n"
            "Grading Criteria:\n"
            "- Score 1.0: Every claim in the generated response is directly supported by the context.\n"
            "- Score 0.0: The response contains unsupported details, assumptions, or hallucinations not in the context.\n\n"
            "Your output must be a single JSON object matching this exact format:\n"
            '{"score": 1.0 or 0.0, "reason": "a brief explanation of your decision"}'
        )

        try:
            response = self.ollama.generate(judge_prompt, temperature=0.0)
            # Find the JSON block in LLM output
            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                score = float(data.get("score", 0.0))
                reason = data.get("reason", "No reason provided by LLM.")
                return {"score": score, "reason": reason}
        except Exception as e:
            return {"score": 0.0, "reason": f"Evaluator failed to parse judge response: {str(e)}"}

        return {"score": 0.0, "reason": "LLM failed to output JSON format."}

    def evaluate_qa_correctness(self, answer_text: str, key_facts: List[str]) -> float:
        """Heuristic check: measures the fraction of key facts present in the response."""
        if not key_facts:
            return 1.0

        matched = 0
        for fact in key_facts:
            if fact.lower() in answer_text.lower():
                matched += 1
        return matched / len(key_facts)

    def evaluate_safeguard_compliance(self, answer_text: str, is_in_domain: bool, has_context: bool) -> float:
        """Verifies if the agent correctly triggered safety fallback for out-of-domain/missing context."""
        triggered = "couldn't find enough information" in answer_text.lower()
        if not is_in_domain or not has_context:
            return 1.0 if triggered else 0.0
        # For valid in-domain queries with context, we expect no safeguard to trigger
        return 1.0 if not triggered else 0.0
