# Stop vibe testing your AI product, start evaling

> Originally published on LinkedIn [Stop vibe testing your AI product, start evaling](https://www.linkedin.com/pulse/stop-vibe-testing-your-ai-product-start-evaling-yogita-suryawanshi-sgouf/)

Every chatbot and agent I've built has come with the same nagging question: will it always work the way I want it to?

My process used to be simple. Type in a bunch of prompts, read the outputs, tweak the system prompt, run it again. If it looked better, I published it. If a teammate hit a weird edge case later, I patched the prompt and repeated the ritual.

It felt productive. It was also flying by feel, not by instrument. I had no real answer to "how do you know it works?" beyond "I tried it a bunch and it seemed fine."

If that's you too — and I'd bet it is, for most of us — this article is for you.

I first came across evals last October, when the material to actually understand them was thin. Almost a year on, that's changed. And finally having gone deep, here's my honest take: evals aren't just another skill to add to the stack. They should be the first thing anyone building with AI learns — before frameworks, before prompting tricks, before which model to pick.

---

## AI Broke the Old Testing Contract

Traditional software testing runs on a deterministic contract: 

$$\text{input} \rightarrow \text{logic} \rightarrow \text{expected output}$$

Assert the actual result matches the expected one, exactly, every time. That's what a test suite, a QA sign-off, or a BDD "Then" step has always relied on.

AI breaks that contract. The same input can produce several different — and equally valid — outputs [1]. A response can be grammatically flawless and still be factually wrong. Two answers can use completely different words and still mean exactly the same thing.

So `expected_output == actual_output` testing isn't enough anymore. What you need instead is a way to keep answering one question, release after release: is my AI application doing what I expect, and did my latest change make it better or worse?

That question, asked systematically with evidence instead of a gut feeling, is what an eval is.

---

## An Eval Is Simpler Than It Sounds

Give an AI system an input. Capture what it produces. Grade whether that output meets a defined bar of quality [2]. That's it.

Run it at scale, and it stops being a one-off check. It becomes a score you can track — the way a test suite tracks whether your code still works after a change.

Here's the distinction I keep coming back to: traditional testing verifies correctness against a known, fixed answer. Evals measure the likelihood and quality of correct-enough behavior across variation. Different job entirely.

---

## Five Steps, No Shortcuts

Strip away the tooling and jargon, and every eval — no matter how sophisticated — comes down to the same five steps [3].

1.  **Build the dataset:** The inputs you'll test against, ideally with reference answers where they exist. A poor dataset gives you a poor eval, no matter how good your grading logic is.
2.  **Define what "good" looks like — the rubric:** *"The answer must use only information from the supplied context and not invent unsupported facts."* This, right here, is where you earn your seat at the table. Writing the rubric is a product decision. Not an engineering one.
3.  **Generate model responses:** Run your dataset through the actual system. Capture what comes back.
4.  **Evaluate the responses:** The rubric turns into a number. The evaluator applies the rubric, produces a metric — Groundedness = 0.92, Pass rate = 94%. Something has to be the evaluator [4]: a heuristic check (fast, consistent, blind to nuance), an LLM-as-judge (scales well, only as good as the rubric you give it), or a human rater (the gold standard, but slow and expensive). I don't think any one is sufficient alone — the mature teams I've seen combine all three.
5.  **Analyze and iterate:** Look at what failed, not just the aggregate score. Most teams skip this step. It's the one that actually makes evals useful.

Put together, it's a loop, not a one-time checklist:

```
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

Run that loop consistently, and you've got a team shipping AI features with confidence — not one shipping and hoping.

---

## Where the PM Lens Matters Most

Here's the part most PMs miss: writing the code for an eval is an engineering task. Deciding what "good" means is not. That's yours [4].

Every eval starts with a question only you can answer — what does ideal behavior look like here? What outcome are we actually driving? What failure modes are we trying to catch? 

An engineer can build the harness. Only you can say whether an AI tutor giving away homework answers is a release-blocker, or a verbose summary is a fine tradeoff for speed.

For others, don't mistake this for a PM-only problem. It's a team problem, and it shows up the moment things get real. A new model drops — do you upgrade? A prompt tweak fixes one complaint and silently breaks three other things. A release goes out and nobody can say, with evidence, whether it's actually better.

Without evals, every one of these is a guess dressed up as confidence. With them, they're same-day decisions backed by your own data.

That's my case for evals being the first thing anyone building with AI should learn. Not a framework. Not a prompting trick. Not whichever model is trending this month. It's the discipline that turns "I think it's better" into "I can show you it's better." Everything else is optimization on top of that foundation.

This article covered the fundamentals. For hands-on code, working examples, and the full breakdown in practice — I've written it all up here: [github.com/yogitas/AIforProductManagers](https://github.com/yogitas/AIforProductManagers)

---

## References

*   **[1]** Google Cloud, "Evaluation Overview," Gemini Enterprise Agent Platform. [Online]. Available: [docs.cloud.google.com/gemini-enterprise-agent-platform/models/evaluation-overview](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/evaluation-overview)
*   **[2]** Anthropic, "Demystifying evals for AI agents," Engineering at Anthropic. [Online]. Available: [anthropic.com/engineering/demystifying-evals-for-ai-agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
*   **[3]** Y. S., "Evals for LLM Applications: A Practical Guide to the Fundamentals," AIforProductManagers (GitHub repository). [Online]. Available: [github.com/yogitas/AIforProductManagers](https://github.com/yogitas/AIforProductManagers)
*   **[4]** Google Developers, "Evaluation best practices," Stax. [Online]. Available: [developers.google.com/stax/best-practices](https://developers.google.com/stax/best-practices)