"""
STEP 6: Prompt Augmentation
Combines system rules, retrieved Jira context chunks, and user questions into a single grounded prompt.
"""

from typing import List

try:
    from v1_scratch.retrieval.retriever import RetrievalResult
except ImportError:
    from retrieval.retriever import RetrievalResult


class PromptBuilder:
    """Builds the final grounded prompt sent to the LLM."""

    DEFAULT_SYSTEM_INSTRUCTION = (
        "You are a helpful PM Copilot assisting product managers with Jira documentation.\n"
        "Answer the user's question using ONLY the provided Jira documentation context below.\n"
        "If the context does not contain enough information to answer the question accurately, "
        "state: 'I couldn't find enough information in the available Jira documentation to answer this.'\n"
        "Do NOT make up information or rely on external knowledge not present in the context."
    )

    @classmethod
    def build_prompt(cls, query: str, context_results: List[RetrievalResult]) -> str:
        """Formats retrieved chunks and user question into an augmented prompt."""
        if not context_results:
            formatted_context = "[No relevant documentation found.]"
        else:
            context_blocks = []
            for i, item in enumerate(context_results, 1):
                source_name = item.metadata.get("title", item.metadata.get("source", "Unknown"))
                context_blocks.append(f"--- Context Chunk {i} (Source: {source_name}) ---\n{item.content}")
            formatted_context = "\n\n".join(context_blocks)

        prompt = (
            f"{cls.DEFAULT_SYSTEM_INSTRUCTION}\n\n"
            f"=== RETRIEVED JIRA DOCUMENTATION CONTEXT ===\n"
            f"{formatted_context}\n"
            f"===========================================\n\n"
            f"User Question: {query}\n\n"
            f"Answer:"
        )

        return prompt
