from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.2,
    api_key=os.getenv("GROQ_API_KEY")
)


reasoning_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a research strategist.

Think BEFORE writing.

Identify:
- themes
- patterns
- contradictions
- strongest sources
- missing data

Be precise. No fluff.
"""),

    ("human", """Research Data:
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
""")
])

reasoning_chain = reasoning_prompt | llm | StrOutputParser()



evidence_prompt = ChatPromptTemplate.from_messages([
    ("system", """Extract ONLY strong evidence.

Include:
- statistics
- factual claims
- projections

Ignore opinions and fluff.
"""),

    ("human", """Extract key evidence from:

{research}

Return bullet points:
- ...
""")
])

evidence_chain = evidence_prompt | llm | StrOutputParser()



insight_prompt = ChatPromptTemplate.from_messages([
    ("system", """You generate insights.

Focus on:
- WHY trends exist
- economic/technical reasoning
- implications

DO NOT repeat facts.
"""),

    ("human", """Research Data:
{research}

Evidence:
{evidence}

Generate insights:

- Insight 1
- Insight 2
- Insight 3
""")
])

insight_chain = insight_prompt | llm | StrOutputParser()


writer_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a senior research analyst.

STRICT RULES:
- Use reasoning, evidence, and insights
- No fluff
- No repetition
- Be analytical, not descriptive

If data is weak → say "insufficient evidence"
"""),

    ("human", """Write a professional report.

Topic: {topic}

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
""")
])

writer_chain = writer_prompt | llm | StrOutputParser()


improver_prompt = ChatPromptTemplate.from_messages([
    ("system", """You improve reports.

Rules:
- Fix ONLY weak parts
- Do NOT rewrite everything
- Improve reasoning, clarity, and structure
"""),

    ("human", """Report:
{report}

Feedback:
{feedback}

Return improved report.
""")
])

improver_chain = improver_prompt | llm | StrOutputParser()


critic_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a strict evaluator.

Focus on:
- depth
- reasoning
- evidence usage
- structure

Be critical.
"""),

    ("human", """Evaluate:

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
""")
])

critic_chain = critic_prompt | llm | StrOutputParser()