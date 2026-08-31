from langchain_core.output_parsers import StrOutputParser
from models import EvidenceItem
from llm_config import (
    get_provider_llms,
    execute_prompt_with_fallback,
    provider_pool,
    llm
)
from prompts import (
    reasoning_prompt,
    evidence_prompt,
    grounding_prompt,
    insight_prompt,
    writer_prompt,
    critic_prompt,
    improver_prompt,
    qa_chat_prompt
)

# Instantiate chains with default primary LLM (or fallback when invoked via execute_prompt_with_fallback)
reasoning_chain = reasoning_prompt | llm | StrOutputParser() if llm else None
evidence_chain = evidence_prompt | llm | StrOutputParser() if llm else None
grounding_chain = grounding_prompt | llm | StrOutputParser() if llm else None
insight_chain = insight_prompt | llm | StrOutputParser() if llm else None
writer_chain = writer_prompt | llm | StrOutputParser() if llm else None
critic_chain = critic_prompt | llm | StrOutputParser() if llm else None
improver_chain = improver_prompt | llm | StrOutputParser() if llm else None
qa_chat_chain = qa_chat_prompt | llm | StrOutputParser() if llm else None

__all__ = [
    "EvidenceItem",
    "get_provider_llms",
    "execute_prompt_with_fallback",
    "provider_pool",
    "llm",
    "reasoning_prompt",
    "evidence_prompt",
    "grounding_prompt",
    "insight_prompt",
    "writer_prompt",
    "critic_prompt",
    "improver_prompt",
    "qa_chat_prompt",
    "reasoning_chain",
    "evidence_chain",
    "grounding_chain",
    "insight_chain",
    "writer_chain",
    "critic_chain",
    "improver_chain",
    "qa_chat_chain"
]