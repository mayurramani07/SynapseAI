from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from typing import Literal
from langchain_core.runnables import RunnableLambda
import os
import json

load_dotenv()

llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0.2,
    api_key=os.getenv("GROQ_API_KEY")
)


class EvidenceItem(BaseModel):
    claim: str = Field(
        description="Claim directly supported by the research"
    )
    supporting_text: str = Field(
        description="Supporting information directly present in the research"
    )
    source_url: str = Field(
        description="Source URL associated with the evidence"
    )
    evidence_type: Literal[
        "statistic",
        "factual_claim",
        "projection"
    ] = Field(
        description="Type of evidence"
    )


reasoning_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a research strategist.

Think BEFORE writing.

Identify:
- themes
- patterns
- contradictions
- strongest sources
- missing data

Be precise. No fluff.
"""
    ),
    (
        "human",
        """Research Data:

{research}

Return:

Key Themes:
- ...

Patterns:
- ...

Contradictions:
- ...

Strong Sources:
- ...

Weak Areas:
- ...
"""
    )
])

reasoning_chain = (
    reasoning_prompt
    | llm
    | StrOutputParser()
)


evidence_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an evidence extraction system.

Extract ONLY the strongest evidence directly supported by the provided research.

IMPORTANT:
Return NO MORE THAN 3 evidence items.

Each item MUST contain exactly:

claim
supporting_text
source_url
evidence_type

Allowed evidence_type values:

statistic
factual_claim
projection

STRICT RULES:

1. Do NOT invent facts.
2. Do NOT use outside knowledge.
3. Do NOT combine unrelated information.
4. source_url MUST already exist in the research.
5. supporting_text MUST be copied directly from the research.
6. Do NOT rewrite supporting_text.
7. Do NOT create URLs.
8. Every item MUST contain all four fields.
9. evidence_type MUST be one of:
   statistic
   factual_claim
   projection
10. Prefer strong statistics and directly stated factual claims.
11. Return at most 3 items.
12. If no strong evidence exists, return an empty list.
13. Return ONLY JSON.
14. Do NOT use Markdown.
15. Do NOT use code fences.
16. Do NOT add explanations.
17. Keep each claim short.
18. Keep each supporting_text short.

The response MUST have this exact structure:

[
  {{
    "claim": "short claim",
    "supporting_text": "exact text from research",
    "source_url": "existing URL from research",
    "evidence_type": "statistic"
  }}
]

OR:

[]

Return ONLY the JSON array.
"""
    ),
    (
        "human",
        """Research:

{research}

Extract the strongest evidence.

Maximum 3 items.

Return ONLY the JSON array."""
    )
])


evidence_raw_chain = (
    evidence_prompt
    | llm
    | StrOutputParser()
)


def parse_and_validate_evidence(raw_output):

    if raw_output is None:
        raise ValueError(
            "Evidence extraction returned None"
        )

    text = str(raw_output).strip()

    if not text:
        raise ValueError(
            "Evidence extraction returned empty output"
        )

    if "```json" in text:
        text = text.replace(
            "```json",
            "",
            1
        )

    if "```" in text:
        text = text.replace(
            "```",
            ""
        )

    text = text.strip()

    start = text.find("[")

    if start == -1:
        raise ValueError(
            "Evidence extraction did not return a JSON array"
        )

    end = text.rfind("]")

    if end == -1:
        raise ValueError(
            "Evidence extraction returned incomplete JSON"
        )

    text = text[start:end + 1]

    try:
        parsed = json.loads(text)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid JSON returned by evidence extraction: {error}"
        )

    if isinstance(parsed, dict):

        parsed = parsed.get(
            "evidence",
            []
        )

    if not isinstance(parsed, list):
        raise ValueError(
            "Evidence output must be a list"
        )

    validated = []

    for index, item in enumerate(parsed[:3]):

        if not isinstance(item, dict):
            continue

        try:
            evidence_item = EvidenceItem.model_validate(
                item
            )

        except ValidationError as error:
            raise ValueError(
                f"Invalid evidence item {index + 1}: {error}"
            )

        if not evidence_item.claim.strip():
            continue

        if not evidence_item.supporting_text.strip():
            continue

        if not evidence_item.source_url.strip():
            continue

        validated.append(
            evidence_item.model_dump()
        )

    return validated


evidence_chain = (
    evidence_raw_chain
    | RunnableLambda(parse_and_validate_evidence)
)


# grounding_prompt = ChatPromptTemplate.from_messages([
#     (
#         "system",
#         """You are an evidence verification system.

# Verify each evidence item ONLY against the provided source content.

# Do NOT use outside knowledge.

# For every evidence item return:

# {{
#   "evidence_index": 1,
#   "verified": true,
#   "reason": "short reason",
#   "confidence": 0.95
# }}

# STRICT RULES:

# - evidence_index must match the supplied evidence item number.
# - verified must be true only when the source directly supports the claim.
# - confidence must be between 0 and 1.
# - Do not invent information.
# - Return ONLY a JSON array.
# - Return one result for every supplied evidence item.
# """
#     ),
#     (
#         "human",
#         """SOURCE CONTENT:

# {source_content}

# EVIDENCE ITEMS:

# {evidence_items}

# Verify every evidence item.

# Return ONLY the JSON array."""
#     )
# ])


# grounding_chain = (
#     grounding_prompt
#     | llm
#     | JsonOutputParser()
# )
grounding_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an evidence verification system.

Verify the supplied evidence item ONLY against the provided source content.

Do NOT use outside knowledge.

STRICT RULES:

- verified must be true only when the source directly supports the claim.
- verified must be false when the source does not directly support the claim.
- confidence must be between 0 and 1.
- reason must briefly explain the verification result.
- Do not invent information.
- Do not modify the evidence.
- Return ONLY one JSON object.
- Do NOT return a JSON array.
- Do NOT use Markdown.
- Do NOT use code fences.
- Do NOT add explanations.

Return exactly:

{{
  "verified": true,
  "reason": "The source directly supports the claim.",
  "confidence": 0.95
}}
"""
    ),
    (
        "human",
        """SOURCE CONTENT:

{source_content}

EVIDENCE ITEM:

{evidence_items}

Verify whether this evidence item is directly supported by the source content.

Return ONLY the JSON object."""
    )
])

grounding_chain = (
    grounding_prompt
    | llm
    | JsonOutputParser()
)


insight_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You generate research insights.

Focus on:

- WHY trends exist
- technical reasoning
- economic reasoning
- implications

Do NOT simply repeat facts.

Use ONLY the provided verified evidence.

Do NOT introduce:

- new statistics
- new sources
- unsupported claims
- outside knowledge
"""
    ),
    (
        "human",
        """Research Data:

{research}

Verified Evidence:

{evidence}

Generate:

- Insight 1
- Insight 2
- Insight 3
"""
    )
])

insight_chain = (
    insight_prompt
    | llm
    | StrOutputParser()
)


writer_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a senior research analyst.

STRICT RULES:

- Use reasoning, evidence, and insights.
- No fluff.
- No repetition.
- Be analytical.
- Do not invent sources.
- Do not invent statistics.
- Do not invent studies.
- Do not invent research methods.
- Only use verified evidence for factual claims.
- If evidence is weak, say "insufficient evidence".
"""
    ),
    (
        "human",
        """Write a professional research report.

Topic:

{topic}

Research Data:

{research}

Reasoning:

{reasoning}

Verified Evidence:

{evidence}

Insights:

{insights}

-------------------------------------

STRUCTURE:

1. Introduction

2. Methodology

3. Key Findings

4. Deep Analysis

5. Limitations

6. Conclusion

7. Sources

-------------------------------------
"""
    )
])

writer_chain = (
    writer_prompt
    | llm
    | StrOutputParser()
)


critic_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a strict research evaluator.

Evaluate the report against the provided verified evidence.

Focus on:

- depth
- reasoning
- evidence usage
- source grounding
- unsupported claims
- structure

STRICT RULES:

- Do NOT assume unsupported claims are true.
- Identify unsupported claims.
- Identify hallucinated statistics.
- Identify hallucinated sources.
- Identify incorrectly used evidence.
- Be critical.
"""
    ),
    (
        "human",
        """Evaluate the following research report.

Report:

{report}

Verified Evidence:

{evidence}

Return:

Score: X/10

Strengths:
- ...

Weaknesses:
- ...

Unsupported Claims:
- ...

Evidence Issues:
- ...

Improvements:
- ...

Verdict:
...
"""
    )
])

critic_chain = (
    critic_prompt
    | llm
    | StrOutputParser()
)


improver_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You improve research reports.

Rules:

- Fix ONLY weak parts.
- Do NOT rewrite everything unnecessarily.
- Improve reasoning, clarity, and structure.
- Do NOT introduce new facts.
- Do NOT introduce new sources.
- Do NOT introduce new statistics.
- Do NOT claim additional research was performed.
- Keep factual claims grounded in the provided report and feedback.
"""
    ),
    (
        "human",
        """Report:

{report}

Feedback:

{feedback}

Return the improved report."""
    )
])

improver_chain = (
    improver_prompt
    | llm
    | StrOutputParser()
)