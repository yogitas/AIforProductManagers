"""
RAG Evaluation Runner: Executes automated test suite and prints Level 1 and Level 2 scorecards.
Usage: python3 -m evals.run_evals
"""

import os
import sys
import json
from dotenv import load_dotenv

# Ensure parent directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from v1_scratch.embeddings.embedder import EmbeddingModel
from v1_scratch.retrieval.vector_store import VectorStore
from v1_scratch.retrieval.retriever import Retriever
from v1_scratch.generation.prompt import PromptBuilder
from v1_scratch.generation.ollama import OllamaClient
from evals.evaluator import RAGEvaluator


def run_evals():
    """Runs all evaluation test cases against the RAG pipeline."""
    load_dotenv()
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    db_path = os.path.join(base_dir, "chroma_db")
    dataset_path = os.path.join(base_dir, "evals", "eval_dataset.json")

    # Load dataset
    with open(dataset_path, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    # Initialize RAG components
    embedder = EmbeddingModel(model_name="all-MiniLM-L6-v2")
    vector_store = VectorStore(persist_directory=db_path, collection_name="jira_docs")
    retriever = Retriever(embedder=embedder, vector_store=vector_store, top_k=3, distance_threshold=0.75)
    ollama_client = OllamaClient(model="llama3.1")

    # Initialize Evaluator
    evaluator = RAGEvaluator(model_name="llama3.1")

    print("\n" + "=" * 80)
    print("🚀 RUNNING AUTOMATED RAG EVALUATION SUITE")
    print("=" * 80)

    results = []

    for case in test_cases:
        cid = case["id"]
        question = case["question"]
        expected_source = case.get("expected_source")
        key_facts = case.get("key_facts", [])
        is_in_domain = case.get("is_in_domain", True)

        print(f"\n[{cid}] Question: '{question}'")

        # 1. Retrieval Layer
        retrieved_chunks = retriever.retrieve(question)
        hit_rate = evaluator.evaluate_retrieval_hit_rate(retrieved_chunks, expected_source, is_in_domain)

        # 2. Generation Layer
        has_context = len(retrieved_chunks) > 0
        if not has_context:
            response = "I couldn't find enough information in the available Jira documentation to answer this."
            context_text = ""
        else:
            prompt = PromptBuilder.build_prompt(question, retrieved_chunks)
            response = ollama_client.generate(prompt)
            context_text = "\n\n".join(chunk.content for chunk in retrieved_chunks)

        # 3. Evaluator Layer
        groundedness_res = evaluator.evaluate_groundedness(context_text, response)
        groundedness_score = groundedness_res.get("score", 0.0)
        groundedness_reason = groundedness_res.get("reason", "No details.")

        qa_correctness = evaluator.evaluate_qa_correctness(response, key_facts)
        safeguard_score = evaluator.evaluate_safeguard_compliance(response, is_in_domain, has_context)

        # Overall Status
        passed = (hit_rate >= 0.8) and (groundedness_score >= 0.8) and (qa_correctness >= 0.5)

        results.append({
            "id": cid,
            "question": question,
            "expected_source": expected_source,
            "retrieved": [chunk.metadata.get("source", "") for chunk in retrieved_chunks],
            "response": response,
            "hit_rate": hit_rate,
            "groundedness": groundedness_score,
            "groundedness_reason": groundedness_reason,
            "qa_correctness": qa_correctness,
            "safeguard": safeguard_score,
            "passed": passed
        })

        status_str = "✅ PASS" if passed else "❌ FAIL"
        print(f"      Status: {status_str} | Hit Rate: {hit_rate:.1f} | Groundedness: {groundedness_score:.1f} | QA Correctness: {qa_correctness:.1f}")

    # Compute Averages
    avg_hit_rate = sum(r["hit_rate"] for r in results) / len(results)
    avg_groundedness = sum(r["groundedness"] for r in results) / len(results)
    avg_correctness = sum(r["qa_correctness"] for r in results) / len(results)
    avg_safeguard = sum(r["safeguard"] for r in results) / len(results)

    # Threshold Check
    pipeline_passed = (avg_groundedness >= 0.90) and (avg_hit_rate >= 0.90)

    # Output Level 1: Dashboard
    print("\n" + "=" * 80)
    print("📈 LEVEL 1: AGGREGATE EVALUATION SCORECARD")
    print("=" * 80)
    print(f"Retrieval Hit Rate:     {avg_hit_rate * 100:.1f}%")
    print(f"LLM Groundedness:       {avg_groundedness * 100:.1f}%")
    print(f"QA Correctness:         {avg_correctness * 100:.1f}%")
    print(f"Safeguard Compliance:   {avg_safeguard * 100:.1f}%")
    print("-" * 80)
    if pipeline_passed:
        print("OVERALL RAG STATUS: ✅ PASSED (Meets release criteria of >= 90% Groundedness & Hit Rate)")
    else:
        print("OVERALL RAG STATUS: ❌ FAILED (Below release criteria of >= 90% Groundedness & Hit Rate)")
    print("=" * 80)

    # Output Level 2: Failure Analysis
    failures = [r for r in results if not r["passed"]]
    if failures:
        print("\n" + "=" * 80)
        print("🔍 LEVEL 2: DETAILED FAILURE LOGS")
        print("=" * 80)
        for idx, f in enumerate(failures, 1):
            print(f"Failure #{idx}: Case [{f['id']}] - '{f['question']}'")
            print(f"Expected Source:    {f['expected_source']}")
            print(f"Retrieved Sources:  {f['retrieved']}")
            print(f"Model Response:     {f['response']}")
            print(f"Groundedness Reason:{f['groundedness_reason']}")
            print(f"QA Correctness:     {f['qa_correctness']:.1f}")
            print("-" * 80)
    else:
        print("\nNo failures detected. Excellent RAG quality!")


if __name__ == "__main__":
    run_evals()
