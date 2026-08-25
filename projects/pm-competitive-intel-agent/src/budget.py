"""
Implements the call budget tracker for the agent.

PEDAGOGICAL NOTE FOR READERS:
An autonomous agent running on a cron schedule is a potential source of unbounded API costs
if it hits a loop, or runs searches over an unexpectedly large list of targets.
Including a hard limit on API calls (e.g., search queries) is a vital safety guardrail
for any production system.
"""
import logging

logger = logging.getLogger(__name__)

class BudgetTracker:
    def __init__(self, max_search_calls: int):
        self.max_search_calls = max_search_calls
        self.search_calls_made = 0
        self.input_tokens = 0
        self.output_tokens = 0

    def increment_search_calls(self) -> bool:
        """
        Increments search calls and returns True if within budget, False if budget exceeded.
        """
        if self.search_calls_made >= self.max_search_calls:
            logger.warning(
                f"GUARDRAIL TRIGGERED: Search call limit of {self.max_search_calls} reached. "
                "Capping discovery here to prevent cost runaway."
            )
            return False
        
        self.search_calls_made += 1
        return True

    def has_search_budget(self) -> bool:
        """
        Returns True if we can make more search calls, False otherwise.
        """
        return self.search_calls_made < self.max_search_calls

    def add_tokens(self, input_tokens: int, output_tokens: int):
        """
        Logs input and output tokens consumed by LLM calls during this execution.
        """
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

    def get_estimated_cost(self) -> float:
        """
        Calculates estimated cost of execution in USD.
        Pricing model used:
        - Lightweight LLM Input: $0.075 / 1,000,000 tokens
        - Lightweight LLM Output: $0.30 / 1,000,000 tokens
        - Search Queries: $0.014 / call (standard API valuation)
        """
        token_input_cost = (self.input_tokens / 1_000_000) * 0.075
        token_output_cost = (self.output_tokens / 1_000_000) * 0.30
        search_grounding_cost = self.search_calls_made * 0.014
        
        return token_input_cost + token_output_cost + search_grounding_cost
