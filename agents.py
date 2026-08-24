from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()

llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0.2,
    api_key=os.getenv("GROQ_API_KEY")
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

reasoning_chain = reasoning_prompt | llm | StrOutputParser()


evidence_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an evidence extraction system.

Extract ONLY evidence that is directly supported by the provided research.

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
2. Do NOT add information that is not present in the research.
3. Do NOT combine unrelated information from different sources.
4. Preserve the source URL associated with the evidence.
5. Ignore opinions, assumptions, interpretations, and unsupported statements.
6. Only extract evidence that can be directly traced to the provided research.
7. If there is no strong evidence, return an empty JSON array.
8. Return ONLY valid JSON.
9. Do NOT return Markdown.
10. Do NOT use code fences.
11. Do NOT add explanations before or after the JSON.
"""
    ),

    (
        "human",
        """Research:

{research}

Return ONLY a JSON array.

Use exactly this structure:

[
  {{
    "claim": "claim directly supported by the research",
    "supporting_text": "supporting information from the research",
    "source_url": "source URL associated with the evidence",
    "evidence_type": "statistic"
  }}
]

If there is no strong evidence, return:

[]

Return ONLY the JSON array."""
    )
])

evidence_chain = evidence_prompt | llm | JsonOutputParser()


insight_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You generate insights.

Focus on:
- WHY trends exist
- economic/technical reasoning
- implications

DO NOT repeat facts.
"""
    ),

    (
        "human",
        """Research Data:

{research}

Evidence:

{evidence}

Generate insights:

- Insight 1
- Insight 2
- Insight 3
"""
    )
])

insight_chain = insight_prompt | llm | StrOutputParser()


writer_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a senior research analyst.

STRICT RULES:
- Use reasoning, evidence, and insights
- No fluff
- No repetition
- Be analytical, not descriptive
- Do not invent sources, studies, statistics, searches, or research methods
- Only claim that something was researched if it exists in the provided research data
- If data is weak → say "insufficient evidence"
"""
    ),

    (
        "human",
        """Write a professional report.

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
])

writer_chain = writer_prompt | llm | StrOutputParser()


improver_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You improve reports.

Rules:
- Fix ONLY weak parts
- Do NOT rewrite everything
- Improve reasoning, clarity, and structure
- Do NOT introduce new facts
- Do NOT introduce new sources
- Do NOT claim that additional research was performed
- Keep all factual claims grounded in the provided report and feedback
"""
    ),

    (
        "human",
        """Report:

{report}

Feedback:

{feedback}

Return improved report.
"""
    )
])

improver_chain = improver_prompt | llm | StrOutputParser()


critic_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a strict evaluator.

Focus on:
- depth
- reasoning
- evidence usage
- structure
- unsupported claims

Be critical.
"""
    ),

    (
        "human",
        """Evaluate:

{report}

Return:

Score: X/10

Strengths:
- ...

Weaknesses:
- ...

Improvements:
- ...

Verdict:
...
"""
    )
])

critic_chain = critic_prompt | llm | StrOutputParser()