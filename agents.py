from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Literal
import os

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def get_provider_llms():
    """Build prioritized list of available LLM providers and models for automatic fallback."""
    providers = []

    if GROQ_API_KEY:
        groq_models = [
            ("Groq (gpt-oss-20b)", "openai/gpt-oss-20b"),
            ("Groq (gpt-oss-120b)", "openai/gpt-oss-120b"),
            ("Groq (compound-mini)", "groq/compound-mini"),
            ("Groq (qwen-27b)", "qwen/qwen3.6-27b")
        ]
        for name, model_id in groq_models:
            try:
                providers.append({
                    "name": name,
                    "llm": ChatGroq(
                        model=model_id,
                        temperature=0.2,
                        api_key=GROQ_API_KEY,
                        max_retries=0
                    )
                })
            except Exception:
                pass

    google_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if google_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            providers.append({
                "name": "Gemini (gemini-1.5-flash)",
                "llm": ChatGoogleGenerativeAI(
                    model="gemini-1.5-flash",
                    temperature=0.2,
                    google_api_key=google_key
                )
            })
        except Exception:
            pass
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        try:
            from langchain_openai import ChatOpenAI
            providers.append({
                "name": "OpenRouter (llama-3.1-8b)",
                "llm": ChatOpenAI(
                    model="meta-llama/llama-3.1-8b-instruct:free",
                    openai_api_key=openrouter_key,
                    openai_api_base="https://openrouter.ai/api/v1",
                    temperature=0.2
                )
            })
        except Exception:
            pass

    return providers


provider_pool = get_provider_llms()
llm = provider_pool[0]["llm"] if provider_pool else None


def execute_prompt_with_fallback(prompt, input_dict):
    """Executes a prompt against LLM providers in order. Fails over immediately on rate-limit/TPD/404 errors."""
    last_error = None
    providers = get_provider_llms()

    for provider in providers:
        try:
            chain = prompt | provider["llm"] | StrOutputParser()
            result = chain.invoke(input_dict)
            return result
        except Exception as error:
            last_error = error
            error_text = str(error).lower()
            # If rate limit, quota, TPD, 404, or connection error, failover to next provider/model in pool
            if any(p in error_text for p in ["rate limit", "tpm", "tpd", "429", "404", "model_not_found", "quota", "503", "500"]):
                continue
            raise error

    if last_error:
        raise last_error
    raise RuntimeError("No LLM provider available.")


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

Think before writing.

Identify:
- themes
- patterns
- contradictions
- strongest sources
- missing data

Be precise.
No fluff.
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

Return NO MORE THAN 3 evidence items.

Each item MUST contain exactly these four fields:

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
9. evidence_type MUST be one of the allowed values.
10. Prefer strong statistics and directly stated factual claims.
11. Return at most 3 items.
12. If no strong evidence exists, return [].
13. Return ONLY valid JSON.
14. Do NOT use Markdown.
15. Do NOT use code fences.
16. Do NOT add explanations.
17. Keep claims short.
18. Keep supporting_text short.

Required JSON structure:

[
  {{
    "claim": "short claim",
    "supporting_text": "exact text from research",
    "source_url": "existing URL from research",
    "evidence_type": "statistic"
  }}
]

If there is no strong evidence:

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

evidence_chain = (
    evidence_prompt
    | llm
    | StrOutputParser()
)


grounding_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an evidence verification system.

Verify each evidence item ONLY against the provided source content.

Do NOT use outside knowledge.

For every supplied evidence item return one object.

Required fields:

evidence_index
verified
reason
confidence

Rules:

- evidence_index must match the supplied item number.
- verified must be true ONLY when the source directly supports the claim.
- confidence must be between 0 and 1.
- Do not invent information.
- Return ONLY valid JSON.
- Return a JSON array.
"""
    ),
    (
        "human",
        """SOURCE CONTENT:

{source_content}

EVIDENCE ITEMS:

{evidence_items}

Verify every evidence item.

Return ONLY the JSON array."""
    )
])

grounding_chain = (
    grounding_prompt
    | llm
    | StrOutputParser()
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
        """You are a strictly grounded, evidence-bound senior research analyst.

STRICT GROUNDING & EVIDENCE-BOUND RULES:

1. ABSOLUTE SOURCE OF TRUTH: The "Verified Evidence" section is your ONLY source of truth for factual claims, metrics, numbers, statistics, percentages, and citations.
2. CONTEXT VS FACTS: "Research Data", "Reasoning", and "Insights" provide background structure and analytical perspective ONLY. Do NOT extract any unverified facts, figures, or sources from them that do not appear in "Verified Evidence".
3. INSUFFICIENT EVIDENCE RULE: If there is no verified evidence supporting a specific metric, statement, or finding, you MUST explicitly state "Insufficient verified evidence available" for that point. Do NOT fill factual gaps with assumptions, unverified text, or prior knowledge.
4. ZERO HALLUCINATION:
   - Do NOT invent sources, URLs, domain names, or publishing dates.
   - Do NOT invent statistics, sample sizes, percentages, or metrics.
   - Do NOT invent studies, methodologies, or research entities.
5. CITATIONS: Every factual assertion or metric MUST explicitly cite its matching `source_url` from Verified Evidence.
6. SOURCES SECTION: In section "7. Sources", list ONLY the exact `source_url`s explicitly present in Verified Evidence. If no verified evidence is available, list "No verified sources available."
"""
    ),
    (
        "human",
        """Write a strictly grounded research report.

Topic:
{topic}

Verified Evidence (STRICT SOURCE OF TRUTH FOR ALL FACTS):
{evidence}

Contextual Insights:
{insights}

Strategic Reasoning (Context Only):
{reasoning}

Raw Research Context (Context Only - Do NOT extract unverified facts from here):
{research}

-------------------------------------

STRUCTURE:

1. Introduction

2. Methodology

3. Key Findings (ONLY facts supported by Verified Evidence)

4. Deep Analysis

5. Limitations (Explicitly highlight missing or weak verified evidence)

6. Conclusion

7. Sources (ONLY URLs from Verified Evidence)

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
        """You are an expert report refiner strictly bound by verified research evidence.

STRICT REFINEMENT RULES:

1. EVIDENCE GROUNDING: You MUST cross-check every claim in the report against the provided "Verified Evidence".
2. REMOVE UNSUPPORTED CLAIMS: If the Critic Feedback highlights any unsupported claims, hallucinated metrics, ungrounded statistics, or invalid sources, you MUST either:
   a. Remove the unsupported claim entirely, or
   b. Replace it with an explicit statement: "Insufficient verified evidence available."
3. DO NOT ADD UNGROUNDED FACTS:
   - Do NOT introduce new facts, metrics, statistics, or numbers.
   - Do NOT introduce new source URLs or references not found in Verified Evidence.
   - Do NOT attempt to "fix" an unsupported claim by inventing plausible details.
4. SOURCES INTEGRITY: Section "7. Sources" must strictly contain ONLY valid `source_url`s from Verified Evidence.
5. PRESERVE QUALITY: Keep the refined report clear, analytical, and professional while ensuring 100% strict adherence to Verified Evidence.
"""
    ),
    (
        "human",
        """Report:

{report}

Critic Feedback:

{feedback}

Verified Evidence (STRICT SOURCE OF TRUTH):

{evidence}

Return the refined, strictly grounded report."""
    )
])

improver_chain = (
    improver_prompt
    | llm
    | StrOutputParser()
)