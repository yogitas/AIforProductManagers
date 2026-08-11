# Loop Engineering: The Next Rename, Explained for PMs
> Originally published on LinkedIn [The New Buzz on the AI Block: Loop Engineering](https://www.linkedin.com/pulse/new-buzz-ai-block-loop-engineering-yogita-suryawanshi-zauce/)
By now, there's a good chance you've heard the term *loop engineering* — and there's an equally good chance an AI influencer somewhere has used it to convince you that there's yet another thing you urgently need to learn or risk falling behind. If you haven't heard it yet, don't worry, you're not alone — I only came across it myself a few weeks ago.

This article is my attempt to cut through that noise: what loop engineering actually is, where it fits with everything that came before it, and whether it's worth your attention — written so it makes sense whether or not you have a technical background.

## How we got here

Before loop engineering, there was a clean timeline of "the one skill that matters now" — although in reality, each new layer built on the previous one rather than replacing it.

**Prompt engineering (2022–2023).** *Primary question: How should I ask the model?* Early models were rigid, so wording was the highest-leverage skill you had. It unlocked getting a genuinely good, reliable output from a single instruction. Google's TCREI framework (Task, Context, References, Evaluate, Iterate) came out of this era and still holds up.

**Context engineering (2024).** *Primary question: What information does the model need?* A well-worded prompt still wasn't enough on its own — the model had no memory and no access to real data: customer records, internal docs, live systems. This unlocked giving the model the information it needed to act on, not just an instruction. RAG, memory systems, and tool calling became increasingly common, while MCP later standardised how models connect to external tools and data.

**Skills (October–December 2025).** *Primary question: What procedures should the model already know?* Repeating the same procedural rules in every prompt was wasteful, and buried rules got ignored. Skills unlocked a permanent, reusable procedure — a folder of instructions the agent consults when a matching situation comes up, instead of one more paragraph the model might skim past.

Then, in mid-2026, came the next rename.

## So what actually is a "loop"?

The term came out of developer Twitter, not a paper or product launch, gaining traction after Boris Cherny (head of Claude Code) and Peter Steinberger (creator of OpenClaw) both talked about it and their posts went viral. Since then, others have added their own spin: Andrew Ng frames it as three nested loops — an agentic coding loop, a developer feedback loop, and an external feedback loop connecting user response back to product direction. Shubham Saboo, a Senior AI PM at Google, has talked about it more in terms of designing the feedback and verification steps around the model rather than the wording of a single prompt.

Of all the interpretations floating around, the one I found clearest is the one the Claude Code team put out themselves: a loop is simply agents repeating cycles of work until a stop condition is met. That's it. The "engineering" part is just deciding how the loop gets triggered and when it's allowed to stop.

What was still missing, connecting back to that progression, was a stop condition — a way to tell the model not to just execute the procedure once, but to keep iterating, evaluate the output against a real bar, and stop only when that bar is actually met. In practice, that usually means verifying progress with something measurable — tests, scores, validations, or human review — before deciding whether another iteration is needed. This automatically means moving the judgment call upstream: instead of managing the work manually, across multiple prompts, you define the success criteria and the exit condition in the very first prompt. The model then owns much of the iteration loop end-to-end, while the surrounding software orchestrates the workflow, which cuts down the back-and-forth and lets it operate with far less hand-holding. In other words, the loop used to live in you — prompt, review, repeat. Now you design the loop once and let the agent execute it before coming back to you.

The Claude Code team breaks this into four patterns:

- **Turn-based loops** — you prompt, Claude gathers context, acts, checks its own work, and hands the result back for you to review. This is just the normal back-and-forth most of us already do.
- **Goal-based loops (`/goal`)** — you define what "done" looks like up front (e.g., "get the Lighthouse score to 90, stop after 5 tries"), and the agent keeps iterating against that bar instead of guessing when to stop.
- **Time-based loops (`/loop`, `/schedule`)** — the agent re-runs a task on an interval, useful for recurring or externally-dependent work like checking a PR for new review comments.
- **Proactive loops** — event-triggered, no human in the room in real time, meant for high-volume recurring work like bug triage.

## My honest take

Strip away the branding, and this is a systems design pattern we've had in computer science forever — retry logic, control loops, polling, watchdog timers, CI pipelines that re-run until tests pass. None of that is new. What's actually new is that the reasoning inside the loop increasingly happens in natural language rather than entirely in code. The orchestration is still software, but the model is now responsible for much of the decision-making within that workflow instead of every branch being hard-coded.

The other real change is where the human effort moves to. Before, you were the loop — prompt, check, re-prompt, check again — and every round cost you attention. Now the work is upfront: spend real thought on the first prompt or provide a skill, spell out the goal and the stop condition clearly, and let the agent run the retry cycle itself instead of you doing it manually turn by turn. Done well, that genuinely cuts down how many times you have to step in. Done badly — vague goal, no real stop condition — you just get a more expensive, less supervised version of the same back-and-forth, burning tokens on attempts nobody's checking.

So is it a new discipline? Not really. Is it a real shift in who (or what) is running the loop, and when your judgment gets used? Yes. I'd file loop engineering under "an old, well-understood pattern, now being done the AI way" — worth knowing the vocabulary for, and worth actually practicing the upfront goal-setting skill, but not worth treating as the next skill you must master or fall behind on.

## Should you worry about it?

No. Learn the underlying skill — writing a clear success condition and a sane stop condition for an agent — because that's useful regardless of what it's called next month. Don't feel obligated to relearn your job every time a new label trends on X.

---

### Sources

- Peter Steinberger (steipete), X post that helped popularize the term "loop engineering" — https://x.com/steipete/status/2063697162748260627
- Boris Cherny, "I Don't Prompt Claude Anymore" (covered by The Pragmatic Engineer) — https://newsletter.pragmaticengineer.com/p/what-is-loop-engineering
- Andrew Ng, X post on the three nested feedback loops — https://x.com/AndrewYNg/status/2071988145667928442
- Andrew Ng, The Batch – "Loop Engineering" — https://www.deeplearning.ai/the-batch/three-key-loops-for-building-great-software
- Anthropic, "Loop Engineering: Getting Started with Loops" — https://claude.com/blog/getting-started-with-loops
- Anthropic, Introducing the Model Context Protocol (MCP) — https://www.anthropic.com/news/model-context-protocol
- Shubham Saboo, "Stop Prompting, Start Looping" (Product Faculty) — https://youtu.be/ew6gBJNzC5w?si=6E_341X1wRvyK_lv
- ADTmag, "Loop Engineering Emerges as Developers Put AI Coding Agents on Repeat" — https://adtmag.com/articles/2026/07/01/loop-engineering-emerges-as-developers-put-ai-coding-agents-on-repeat.aspx