# Evals for LLM Applications: A Practical Guide to the Fundamentals

This guide explains the foundational concepts, terminology, datasets, rubrics, metrics, and evaluation types used to systematically measure LLM application quality [1].

---

## 1. Why Evals Are Different for GenAI

Traditional software testing relies on deterministic inputs and outputs:
- **Traditional Software**: `Input -> deterministic logic -> expected output`. Tests assert exact matches.
- **LLM Applications**: The same input can produce multiple semantically valid answers. Outputs are probabilistic, open-ended, and sensitive to context. A response can be grammatically perfect but factually incorrect, or use entirely different words to mean the same thing.

Therefore, traditional `expected_output == actual_output` testing is insufficient. Evaluations (Evals) provide a systematic way to answer:
> **"Is my AI application doing what I expect, and did my latest change make it better or worse?"**

### The Feedback Loop
Treat an Eval suite as the **AI equivalent of a regression test suite** to guide model selection, prompt improvement, model migration, and fine-tuning [1]:

```text
Change prompt/model/RAG
          ↓
       Run Evals
          ↓
     Measure quality
          ↓
    Analyze failures
          ↓
     Accept / improve
```

---

## 2. The Evaluation Mental Model

An evaluation has five fundamental pieces:

```text
                        EVALUATION
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
      DATASET            RUBRICS            METRICS
         │                  │                  │
  What do we test?    How we judge?       The Grade
  (Inputs/Gold)     (Grading Criteria)   (Quantified)
         │                  │                  │
         └──────────────────┼──────────────────┘
                            ↓
                       MODEL OUTPUT
                            ↓
                        EVALUATOR
                     (LLM/Heuristic)
                            ↓
                     SCORE / PASS-FAIL
                            ↓
                     ANALYZE FAILURES
```

The five-step evaluation workflow is:
1. **Create the evaluation dataset** (defining inputs and reference answers)
2. **Define what good looks like (rubrics)** (specifying the grading criteria)
3. **Generate model responses** (running prompts against the LLM)
4. **Evaluate the responses** (matching outputs to rubrics using the evaluator to compute metrics)
5. **Analyze results and iterate** (identifying regressions and fixing bugs)

---

## 3. Step 1 — Build the Evaluation Dataset

The dataset is the foundation of your Eval. A poor dataset produces a poor evaluation, even if your metrics are excellent.

### What should an evaluation example contain?
For a simple LLM:
```text
{
    prompt,
    context,       # optional
    reference      # optional
}
```

*Example schema mapping:*
| Prompt | Context | Reference (Golden Answer) |
|---|---|---|
| Summarize this article | Article text | Expected summary |
| What is the refund policy? | Policy text | Expected answer |
| Convert this into 3 bullets | Input text | Optional |

For a RAG application, you should preserve the retrieved context to distinguish between **retrieval** or **generation** failures [3]:
```text
{
    question,
    retrieved_context,
    response,
    reference       # optional
}
```

### Dataset Sources [1]
1. **Curated Examples**: Manually created scenarios covering critical business flows, edge cases, known failure modes, and safety-critical prompts.
   *Example curated queries for a support bot:*
   - *"What is our refund policy?"*
   - *"What if I bought the product 31 days ago?"*
   - *"What if the product is damaged?"*
2. **Production Data**: Sampled real user queries from logs to evaluate unexpected usage patterns.
3. **Synthetic Data**: LLM-generated variations to scale dataset size or create adversarial edge cases.

**Recommended dataset mix**:
- 70% representative real-world queries
- 20% difficult/edge cases
- 10% known failure/regression cases

---

## 4. Reference-Free vs. Referenced Evaluation

### Reference-Free Evaluation
Evaluating responses without a predefined golden answer [2], [3].
```text
Prompt ──> Model response ──> Judge ──> Score
```
*Example prompt*: 
> *"Explain the benefits of electric vehicles."*
Since there are many valid answers, the judge evaluates standard dimensions:
- Relevance
- Coherence / Helpfulness
- Safety [1]
- Instruction following
- Groundedness (comparing answer directly against context) [3]

### Referenced Evaluation
Evaluating responses by comparing them directly against a predefined golden/reference answer [2], [3].
```text
Prompt ──> Model response ───┐
                             ├──> Compare ──> Score
Reference (Golden Answer) ───┘
```
*Example prompt & reference comparison*:
- **Question**: *"What is the capital of France?"*
- **Reference**: *"Paris"*
- **Model Output**: *"Paris is the capital of France."*

Allows measuring:
- Factual correctness / accuracy [1]
- Completeness
- Semantic similarity [3]
- Traditional text overlap (BLEU, ROUGE) [2]

---

## 5. Step 2 — Define What "Good" Means (Rubrics vs. Metrics)

- **Rubric (Grading Rule)**: Defines the criteria used to judge an answer.
  *Example*: *"The answer must use only information from the supplied context and not invent unsupported facts."*
- **Metric (Grade)**: The score produced when the response is evaluated against the rubric.
  *Example*: `Groundedness = 0.92`, `Pass rate = 94%`.

> [!IMPORTANT]
> **Your Role as a PM: Defining the Criteria**  
> Implementing the code for evaluations is an engineering task, but **defining what "good" looks like is 100% your job** [1]. To write crisp rubrics, define:
> 1. **Ideal Behavior**: How should the AI interact? (e.g., *"Our AI tutor must guide students, never just give away homework answers."*)
> 2. **Business Goals**: What outcomes are you driving? (e.g., *"Resolve support queries with zero safety violations."*)
> 3. **Failure Cases**: What mistakes must we catch? (e.g., *"Summaries are too verbose; tone is not creative enough."*)

### Categories of Metrics
Google classifies evaluation metrics into three major categories [1]:

#### 1. Rubric-Based (Model-Based) Metrics
These metrics use another LLM (acting as a judge) to evaluate subjective quality dimensions against a specified rubric [1], [2].
- **Static Rubrics**: A fixed rubric applied consistently across all prompts in the dataset [1].
  *Example*: Grading safety, fluency, or coherence on a static 1–5 scale.
- **Adaptive Rubrics**: Rubrics dynamically generated by the model for each prompt, tailored to specific instructions [2].
  *Example*: For the prompt *"Summarize this in exactly 3 sentences using an optimistic tone"*, the judge dynamically validates: (1) Summarizes article, (2) Exactly 3 sentences, (3) Optimistic tone.

#### 2. Computation-Based Metrics
These metrics use deterministic mathematical algorithms to compare model outputs directly against golden reference answers without calling another LLM [1], [2]:
- **Exact Match**: Character-by-character check for 100% identical outputs.
  *Example*:
  ```text
  Reference: "Paris"
  Output A:  "Paris" (Score = 1)
  Output B:  "Paris is the capital of France." (Score = 0)
  ```
- **BLEU**: Measures precision-oriented n-gram overlap with the reference summary or translation [2].
- **ROUGE**: Measures recall-oriented n-gram overlap with the reference answer [2].

#### 3. Custom Metrics
Custom-defined evaluation criteria created to fit specific business logic that standard metrics do not cover (e.g., verifying if a customer support bot referenced a specific policy clause or database link) [3].
  *Example*: Creating a custom pointwise evaluator that returns `1` if all required steps are present in the response and `0` if any are missing.

---

## 6. Evaluators (Graders): Methods of Evaluation

Once you have defined your metrics, you need to choose an **evaluator** (also referred to by Anthropic as a **grader**) to execute the grade [4]. Both Google and Anthropic define three core methods of evaluation:

| Evaluator / Grader Type | Pros | Cons | Best Used For |
| :--- | :--- | :--- | :--- |
| **1. Deterministic / Heuristic**<br>(Code-based rule checks) | Extremely fast, free, and 100% consistent. | Cannot grade semantic quality, tone, or style. | Structured formats (e.g., valid JSON checks, keyword presence, length constraints). |
| **2. Model-Based**<br>(LLM-as-a-Judge) | Excellent at grading semantic meaning, tone, and reasoning. | Probabilistic (can hallucinate) and incurs model costs. | Groundedness, relevance, summarization quality, and instruction following [2], [3]. |
| **3. Human Evaluation**<br>(Human-in-the-loop experts) | The ultimate gold standard for truth and context. | Extremely slow, expensive, and completely unscalable. | Initial prompt calibration, auditing edge cases, and safety compliance checks [4]. |

> [!TIP]
> **PM Application Tip**: For production systems, combine **heuristic** checks (e.g., verifying response latency and formatting) with **model-based** evaluation (e.g., LLM-as-a-judge for groundedness). Calibrate your LLM judge against a small golden dataset labeled by **human** experts.

---

## 7. Avoid the Trap of a Single "AI Quality" Metric

Do not consolidate your results into a single aggregate score (e.g., `AI Quality = 87%`). Instead, measure and track individual metrics separately.

*Why?* An aggregate score hides critical failures. For example:
- **Model A**: Correctness = 95%, Groundedness = 70% (Overall = 82.5%)
- **Model B**: Correctness = 82%, Groundedness = 83% (Overall = 82.5%)

Model A sounds extremely confident and correct but frequently hallucinates facts. Having separate metrics makes this immediately actionable, whereas an overall score obscures the problem.

---

## 8. What Should a PM Own?

Product Managers should own the **definition of quality** rather than the codebase implementation:
1. **What success means**: Define detailed requirements (e.g., *"Must avoid unsupported claims and follow format guidelines"*).
2. **What can go wrong**: List failure modes (e.g., hallucination, wrong retrieval, unsafe output).
3. **How to measure it**: Map failure modes to metrics (e.g., hallucination $\rightarrow$ groundedness).
4. **The release threshold**: Establish baseline requirements (e.g., `Groundedness >= 95%`, `Safety = 100%`).

---

## 9. Simple LLM vs. RAG Cheat Sheet

| Metric | Simple LLM | RAG |
|---|---|---|
| **Dataset** | Prompt + optional context/reference | Question + retrieved context + reference |
| **Main Concern** | Answer generation quality | Retrieval ranking + answer generation quality |
| **Groundedness** | Optional | **Critical** [3] |
| **Relevance & Safety**| Yes | Yes [1] |
| **Retrieval Metrics** | No | Hit Rate / Recall@K, MRR [3] |
| **BLEU / ROUGE** | Yes (with reference) | Yes (with reference) [2] |

---

## References

- [1] Google Cloud, "Evaluation Overview," Gemini Enterprise Agent Platform. [Online]. Available: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/evaluation-overview#metrics
- [2] Google Developers Codelab, "Evaluating Single LLM Outputs with Vertex AI Evaluation." [Online]. Available: https://codelabs.developers.google.com/codelabs/production-ready-ai-with-gc/6-ai-evaluation/evaluating-single-llm-outputs-with-vertex-ai-evaluation#0
- [3] Google Developers Codelab, "Evaluate RAG Systems with Vertex AI." [Online]. Available: https://codelabs.developers.google.com/codelabs/production-ready-ai-with-gc/6-ai-evaluation/evaluate-rag-systems-with-vertex-ai#3
- [4] Google Developers / Anthropic, "Best practices for making good evaluations & grading." [Online]. Available: https://developers.google.com/stax/best-practices#how_to_make_good_evals
