# Hands-On LLM Evals: Implementing Evaluations for Simple LLM and RAG Applications

This guide covers implementation patterns, dataset design, RAG evaluation, regression testing, and CI/CD automation patterns for evaluating LLM applications [1].

---

## 1. Implementing an Eval for a Simple LLM

### Step 1: Create the Dataset
Define a set of golden examples containing instructions, context, and reference answers [2]:
```python
eval_dataset = [
    {
        "instruction": "Summarize the article in 3 sentences.",
        "context": "...article text A...",
        "reference": "...golden summary A..."
    },
    {
        "instruction": "Summarize the article in 3 sentences.",
        "context": "...article text B...",
        "reference": "...golden summary B..."
    }
]
```

*Once response generation and evaluation are complete, the final evaluated dataset schema expands to append model outputs and scores:*

| Instruction | Context | Reference (Golden) | Model Response | Summarization Quality | Groundedness | Instruction Following |
|---|---|---|---|---|---|---|
| Summarize the article in 3 sentences. | ...article text A... | ...golden summary A... | *[Model Summary A]* | 4.5 / 5.0 | 1.0 | 1.0 |
| Summarize the article in 3 sentences. | ...article text B... | ...golden summary B... | *[Model Summary B]* | 3.8 / 5.0 | 0.8 | 1.0 |

---
### Step 2: Generate Responses
Loop through the dataset and collect model answers:
```python
for example in eval_dataset:
    prompt = f"{example['instruction']}\n\nArticle:\n{example['context']}"
    example["response"] = llm.generate(prompt)
```

### Step 3: Run the Evaluator
Compute metrics like summarization quality, instruction following, groundedness, and safety [2]:
```python
# Conceptual execution
result = evaluate(
    prompt=example["instruction"],
    context=example["context"],
    response=example["response"],
    reference=example["reference"],
    metrics=["summarization_quality", "groundedness", "instruction_following"]
)
```
*Expected evaluator output for a case:*
```text
summarization_quality = 4.5 / 5
instruction_following = 1.0
groundedness = 0.94
safety = 1.0
```

---

## 2. Implementing an Eval for a RAG Application

A RAG system has two main sources of failure:
1. **Retrieval failure**: The retriever failed to fetch the relevant context.
2. **Generation failure**: The retriever fetched the correct context, but the LLM hallucinated or answered incorrectly.

### Step 1: Build the RAG Evaluation Dataset
Ensure that you save the retrieved context alongside the question and the final response [3]:
```python
rag_eval_dataset = [
    {
        "question": "What is the refund policy?",
        "retrieved_context": "Customers can request a refund within 30 days...",
        "response": "You can get a refund within 30 days.",
        "reference": "Customers can request a refund within 30 days."
    }
]
```

### Step 2: Evaluate Retrieval
Calculate retrieval accuracy using standard search metrics [3]:
- **Hit Rate (Recall@K)**: Did the retriever fetch the relevant document?
- **Mean Reciprocal Rank (MRR)**: How high was the relevant document ranked?

### Step 3: Evaluate Generation
- **Groundedness**: Verify that the generated answer is supported *only* by the retrieved context (reference-free) [3].
  *Examples*:
  ```text
  Context: "Refunds are available within 30 days."
  Answer A: "Refunds are available within 30 days." (Grounded -> PASS)
  Answer B: "Refunds are available within 60 days." (Grounded -> FAIL)
  ```
  ```text
  Context: "The product has a 2-year warranty."
  Answer:  "The product has a 5-year warranty." (Hallucination -> Groundedness FAIL)
  ```
- **Relevance & Helpfulness**: Verify the answer directly solves the user question [1], [2].
- **QA Correctness**: Compare the response against the golden answer [3].

---

## 3. Separating Retrieval vs. Generation Failures

Separating these failure modes is crucial for debugging RAG pipelines [3].

For example, given the question: *"What is our parental leave policy?"*
- **Retrieval Failure**: The retriever returns chunks about holiday policies, office locations, and parking. Because the context was bad, the LLM had no way of answering correctly. Fix this by tuning your chunk size, metadata filters, or embeddings.
- **Generation Failure**: The retriever successfully returns *"Parental leave is 26 weeks."* but the LLM responds *"You receive 12 weeks."* Here, retrieval worked, but generation failed. Fix this by updating the prompt or tuning the temperature.

---

## 4. Implementing a Custom RAG Correctness Metric

To enforce strict business rules, implement custom pointwise rubrics rather than generic metrics [3]:

```python
# Custom Pointwise Correctness Metric Prompt Template
custom_rubric_prompt = """
You are evaluating question-answering correctness.

CRITERIA:
The response must contain all important claims from the reference and must not introduce unsupported claims.

SCORE:
1 = Correct
0 = Incorrect

Reference: {reference}
Response: {response}

Return JSON: {"score": 0 or 1, "reason": "..."}
"""
```

---

## 5. Failure Analysis & Comparing Prompts/Models

Evaluating at scale requires both aggregate scores and deep-dive failure analysis [2], [3].

### A. Deep-Dive Failure Analysis
Aggregate scores can hide specific product flaws. When failures happen, look at individual cases:
```text
Example #17 (Groundedness = 0.0)

Question:   What caused the outage?
Context:    The database failed due to disk exhaustion.
Response:   The database failed because of a network issue.
Reason:     The model hallucinated a network issue that is unsupported by the context.
```
This loop tells you exactly what to fix in the prompt or document chunking.

### B. Comparing Two Prompts or Models
Before upgrading models or rewriting prompts, evaluate both against the **same test dataset** and compare [2]:
| Metric | Prompt A | Prompt B |
|---|---:|---:|
| Summarization quality | 4.1 | **4.5** |
| Groundedness | 91% | **96%** |
| Instruction following | **97%** | 94% |
| Safety | 99% | 99% |

This structured comparison highlights trade-offs (e.g., Prompt B has better quality and groundedness, but slightly worse instruction following).

### C. Level 1 Dashboard vs. Level 2 Failure Analysis
A production-ready evaluation system should produce two levels of reporting [1]:
- **Level 1 (Dashboard)**: High-level metric progression:
  ```text
                   Current    Baseline
  Correctness        94%        92%
  Groundedness       96%        95%
  Safety             99%        99%
  ```
- **Level 2 (Failure Logs)**: Complete inputs and outputs for failed test cases to let developers debug:
  ```text
  Example #47 (Groundedness: FAIL)
  Question:          "What is the refund period?"
  Retrieved context: "Refunds are available within 30 days."
  Response:          "Refunds are available within 60 days."
  Reason:            The generated answer contradicts the retrieved context.
  ```

---

## 6. Turning Evals into Regression Tests (CI/CD)

Integrate evaluations into your deployment pipeline as regression gates [1], [3]:

```text
Pull Request ──> Run Evaluation Suite ──> Compare against Baseline ──> Block / Deploy
```

### release criteria example:
- `Groundedness >= 95%`
- `QA Correctness >= 93%`
- `Safety = 100%`

### Codebase Organization Pattern
Keep evaluation code, datasets, and rubrics version-controlled alongside your application code:
```text
/evals
    /datasets
        simple_llm.jsonl
        rag_questions.jsonl
    /rubrics
        correctness.yaml
        groundedness.yaml
    /evaluators
        custom_rag_metrics.py
    /results
        baseline.json
```

---

## References

- [1] Google Cloud, "Evaluation Overview," Gemini Enterprise Agent Platform. [Online]. Available: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/evaluation-overview#metrics
- [2] Google Developers Codelab, "Evaluating Single LLM Outputs with Vertex AI Evaluation." [Online]. Available: https://codelabs.developers.google.com/codelabs/production-ready-ai-with-gc/6-ai-evaluation/evaluating-single-llm-outputs-with-vertex-ai-evaluation#0
- [3] Google Developers Codelab, "Evaluate RAG Systems with Vertex AI." [Online]. Available: https://codelabs.developers.google.com/codelabs/production-ready-ai-with-gc/6-ai-evaluation/evaluate-rag-systems-with-vertex-ai#3
