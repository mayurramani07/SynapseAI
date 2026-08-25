from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from typing import Literal
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


class EvidenceExtraction(BaseModel):

    evidence: list[EvidenceItem] = Field(
        default_factory=list,
        description="List of directly supported evidence items"
    )


class GroundingResult(BaseModel):

    evidence_index: int = Field(
        description="Position of the evidence item starting from 1"
    )

    verified: bool = Field(
        description="Whether the evidence is directly supported"
    )

    reason: str = Field(
        description="Reason for the verification result"
    )

    confidence: float = Field(
        description="Confidence between 0 and 1"
    )


reasoning_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are a research strategist.

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
            """
Research Data:

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
    ]
)


reasoning_chain = (
    reasoning_prompt
    | llm
    | StrOutputParser()
)


evidence_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are an evidence extraction system.

Extract ONLY evidence directly supported by the provided research.

For every evidence item identify:

- claim
- supporting_text
- source_url
- evidence_type

Allowed evidence_type values:

- statistic
- factual_claim
- projection

STRICT RULES:

1. Do NOT invent facts.
2. Do NOT use outside knowledge.
3. Do NOT combine unrelated information from different sources.
4. source_url MUST come directly from the provided research.
5. supporting_text MUST be directly supported by the provided research.
6. Every evidence item MUST contain all four fields.
7. evidence_type MUST be exactly one of:
   statistic
   factual_claim
   projection
8. Ignore opinions and unsupported statements.
9. If no strong evidence exists, return an empty evidence list.
10. Extract a maximum of 8 evidence items.
11. Keep supporting_text concise.
12. Do not add explanations.
"""
        ),

        (
            "human",
            """
Research:

{research}

Extract only strong, directly supported evidence.
"""
        )
    ]
)


evidence_structured_llm = llm.with_structured_output(
    EvidenceExtraction
)


def validate_structured_evidence(result):

    if result is None:
        raise ValueError(
            "Evidence extraction returned None"
        )

    if isinstance(result, EvidenceExtraction):
        evidence_items = result.evidence

    elif isinstance(result, dict):

        if "evidence" not in result:
            raise ValueError(
                "Evidence extraction missing 'evidence' field"
            )

        evidence_items = result["evidence"]

    else:
        raise ValueError(
            "Evidence extraction returned invalid structure"
        )

    if not isinstance(evidence_items, list):
        raise ValueError(
            "Evidence field must be a list"
        )

    validated = []

    for index, item in enumerate(evidence_items):

        try:

            if isinstance(item, EvidenceItem):
                evidence_item = item

            else:
                evidence_item = EvidenceItem.model_validate(
                    item
                )

        except ValidationError as error:

            raise ValueError(
                f"Invalid evidence item {index + 1}: {error}"
            )

        if not evidence_item.claim.strip():

            raise ValueError(
                f"Evidence item {index + 1} has empty claim"
            )

        if not evidence_item.supporting_text.strip():

            raise ValueError(
                f"Evidence item {index + 1} has empty supporting_text"
            )

        if not evidence_item.source_url.strip():

            raise ValueError(
                f"Evidence item {index + 1} has empty source_url"
            )

        validated.append(
            evidence_item.model_dump()
        )

    return validated


evidence_chain = (
    evidence_prompt
    | evidence_structured_llm
    | RunnableLambda(
        validate_structured_evidence
    )
)


grounding_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are an evidence verification system.

Your job is to verify MULTIPLE extracted evidence items against the provided source content.

Verify every evidence item independently.

STRICT RULES:

1. Verify each claim ONLY against the provided source content.
2. Do NOT use outside knowledge.
3. Do NOT assume missing information.
4. The claim must be directly supported by the source content.
5. The supporting_text must actually support the claim.
6. If the source does not support the claim, mark it as false.
7. Do not treat similar wording as sufficient evidence.
8. Do not modify the original evidence.
9. Verify each evidence item independently.
10. Return exactly one verification result for every evidence item.
11. evidence_index MUST correspond to the position of the evidence item in the provided list.
12. evidence_index starts from 1.
13. verified MUST be true or false.
14. confidence MUST be between 0 and 1.
15. Return ONLY valid JSON.
16. Do NOT return Markdown.
17. Do NOT use code fences.
18. Do NOT add explanations before or after the JSON.

Return exactly:

[
  {{
    "evidence_index": 1,
    "verified": true,
    "reason": "...",
    "confidence": 0.95
  }}
]

Return one object for every evidence item.

If there are no evidence items, return:

[]
"""
        ),

        (
            "human",
            """
SOURCE CONTENT:

{source_content}

EXTRACTED EVIDENCE ITEMS:

{evidence_items}

Verify every evidence item independently.

Return ONLY the JSON array.
"""
        )
    ]
)


grounding_raw_chain = (
    grounding_prompt
    | llm
    | StrOutputParser()
)


def parse_and_validate_grounding(raw_output):

    if raw_output is None:
        raise ValueError(
            "Grounding extraction returned None"
        )

    if not isinstance(raw_output, str):
        raw_output = str(raw_output)

    text = raw_output.strip()

    if not text:
        raise ValueError(
            "Grounding output is empty"
        )

    if text.startswith("```"):

        if text.startswith("```json"):
            text = text[7:]

        else:
            text = text[3:]

        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

    try:

        parsed = json.loads(text)

    except json.JSONDecodeError as error:

        raise ValueError(
            f"Invalid grounding JSON: {error}"
        )

    if isinstance(parsed, dict):

        if "grounding" in parsed:
            parsed = parsed["grounding"]

        elif "results" in parsed:
            parsed = parsed["results"]

        else:
            parsed = [parsed]

    if not isinstance(parsed, list):

        raise ValueError(
            "Grounding output must be a JSON list"
        )

    validated = []

    for index, item in enumerate(parsed):

        if not isinstance(item, dict):

            raise ValueError(
                f"Grounding item {index + 1} must be an object"
            )

        required_fields = [
            "evidence_index",
            "verified",
            "reason",
            "confidence"
        ]

        for field in required_fields:

            if field not in item:

                raise ValueError(
                    f"Grounding item {index + 1} missing {field}"
                )

        evidence_index = item["evidence_index"]

        if not isinstance(
            evidence_index,
            int
        ) or evidence_index < 1:

            raise ValueError(
                f"Grounding item {index + 1} has invalid evidence_index"
            )

        if not isinstance(
            item["verified"],
            bool
        ):

            raise ValueError(
                f"Grounding item {index + 1} has invalid verified value"
            )

        confidence = item["confidence"]

        if not isinstance(
            confidence,
            (int, float)
        ):

            raise ValueError(
                f"Grounding item {index + 1} has invalid confidence"
            )

        if not 0 <= confidence <= 1:

            raise ValueError(
                f"Grounding item {index + 1} confidence must be between 0 and 1"
            )

        validated.append(
            {
                "evidence_index": evidence_index,
                "verified": item["verified"],
                "reason": str(item["reason"]),
                "confidence": float(confidence)
            }
        )

    return validated


grounding_chain = (
    grounding_raw_chain
    | RunnableLambda(
        parse_and_validate_grounding
    )
)


insight_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You generate insights.

Focus on:
- WHY trends exist
- economic/technical reasoning
- implications

DO NOT repeat facts.
"""
        ),

        (
            "human",
            """
Research Data:

{research}

Evidence:

{evidence}

Generate insights:

- Insight 1
- Insight 2
- Insight 3
"""
        )
    ]
)


insight_chain = (
    insight_prompt
    | llm
    | StrOutputParser()
)


writer_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are a senior research analyst.

STRICT RULES:

- Use reasoning, evidence, and insights.
- No fluff.
- No repetition.
- Be analytical, not descriptive.
- Do not invent sources, studies, statistics, searches, or research methods.
- Only claim that something was researched if it exists in the provided research data.
- If data is weak, say "insufficient evidence".
"""
        ),

        (
            "human",
            """
Write a professional report.

Topic:

{topic}

Research Data:

{research}

Reasoning:

{reasoning}

Evidence:

{evidence}

Insights:

{insights}

-------------------------------------

STRUCTURE:

1. Introduction

2. Methodology

3. Key Findings
- MUST use evidence
- MUST compare sources

4. Deep Analysis
- MUST use insights

5. Limitations

6. Conclusion

7. Sources

-------------------------------------
"""
        )
    ]
)


writer_chain = (
    writer_prompt
    | llm
    | StrOutputParser()
)


improver_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You improve reports.

Rules:

- Fix ONLY weak parts.
- Do NOT rewrite everything.
- Improve reasoning, clarity, and structure.
- Do NOT introduce new facts.
- Do NOT introduce new sources.
- Do NOT claim that additional research was performed.
- Keep all factual claims grounded in the provided report and feedback.
"""
        ),

        (
            "human",
            """
Report:

{report}

Feedback:

{feedback}

Return improved report.
"""
        )
    ]
)


improver_chain = (
    improver_prompt
    | llm
    | StrOutputParser()
)


critic_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are a strict research evaluator.

Evaluate the report against the provided evidence.

Focus on:

- depth
- reasoning
- evidence usage
- source grounding
- unsupported claims
- structure

STRICT RULES:

- Do NOT assume unsupported claims are true.
- Identify claims that are not supported by the provided evidence.
- Identify hallucinated statistics or sources.
- Identify evidence that is used incorrectly.
- Be critical.
"""
        ),

        (
            "human",
            """
Evaluate the following research report.

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
    ]
)


critic_chain = (
    critic_prompt
    | llm
    | StrOutputParser()
)