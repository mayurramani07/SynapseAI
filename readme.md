#  SynapseAI

> An evidence-grounded AI research platform that turns a research topic into a structured analytical report through an 8-stage controlled AI pipeline.

SynapseAI combines real-time web search, deterministic source filtering, web scraping, LLM-based reasoning, evidence extraction, insight generation, report writing, critic review, and report improvement.

**Live Demo:** https://synapse-ai-green.vercel.app/  
**Repository:** https://github.com/mayurramani07/SynapseAI

---

##  Features

-  Real-time web search with Tavily
-  Domain-based source credibility filtering and URL ranking
-  Web content extraction with Requests + BeautifulSoup
-  LLM-based research reasoning
-  LLM-based evidence extraction
-  Insight generation from research and evidence
-  Structured research report generation
-  Critic-based report evaluation
-  Feedback-driven report improvement
-  FastAPI backend
-  React + Vite frontend
-  Search and scraping fallback with per-URL retry handling
-  Per-stage execution timing in the backend

---

#  Problem

A single LLM prompt can produce fluent research, but it may not provide a controlled research process or clearly separate source retrieval, factual evidence, reasoning, and quality review.

SynapseAI addresses this by splitting research into specialized stages. Web retrieval and source filtering are handled with deterministic tools, while six LLM chains handle reasoning and generation tasks.

The goal is not to make the LLM decide the entire workflow autonomously, but to provide a predictable and debuggable research pipeline.

---

#  Architecture

```text
┌──────────────────────┐
│        USER          │
│    Research Topic    │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   React + Vite UI    │
└──────────┬───────────┘
           │ HTTP POST
           ▼
┌──────────────────────┐
│    FastAPI Backend   │
│    POST /api/research│
└──────────┬───────────┘
           │
           ▼
┌────────────────────────────────────────────────────┐
│              8-STAGE RESEARCH PIPELINE             │
│                                                    │
│  1. Smart Search                                   │
│       └── Tavily Search                            │
│                 ↓                                  │
│  2. URL Ranking + Scraping                         │
│       ├── URL extraction                           │
│       ├── Domain scoring                           |
│       └── Requests + BeautifulSoup                 │
│                 ↓                                  │
│  3. Reasoning                                      │
│       └── Groq / Llama 3.1                         │
│                 ↓                                  │
│  4. Evidence Extraction                            │
│       └── Groq / Llama 3.1                         │
│                 ↓                                  │
│  5. Insight Generation                             │
│       └── Groq / Llama 3.1                         │
│                 ↓                                  │
│  6. Report Writer                                  │
│       └── Groq / Llama 3.1                         │
│                 ↓                                  │
│  7. Critic Review                                  │
│       └── Groq / Llama 3.1                         │
│                 ↓                                  │
│  8. Improver                                       │
│       └── Groq / Llama 3.1                         │
└──────────────────────┬─────────────────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │   Final Report  │
              └────────┬────────┘
                       │
                       ▼
              React Research UI
```

### State produced by the pipeline

The pipeline maintains a Python `state` dictionary and stores the output of each stage:

```text
search_results
      ↓
scraped_content
      ↓
reasoning
      ↓
evidence
      ↓
insights
      ↓
report
      ↓
feedback
      ↓
final_report
```

---

#  8-Stage Research Pipeline

## 1. Smart Search

The research topic is sent to Tavily using `max_results=10`.

The search tool:

1. Retrieves search results.
2. Removes results without a URL.
3. Calculates a deterministic domain credibility score.
4. Discards results with a score of `0`.
5. Keeps the highest-scoring 5 results.
6. Returns title, URL, summary, and score.

The current domain scoring rules include:

| Domain / Pattern | Score |
|---|---:|
| `.gov` | 5 |
| `.edu` | 5 |
| `worldbank` | 5 |
| `imf` | 5 |
| `reuters` | 4 |
| `bloomberg` | 4 |
| `cnbc` | 3 |
| `forbes` | 3 |
| `investopedia` | 3 |

This is a **heuristic credibility filter**, not semantic relevance ranking.

---

## 2. URL Ranking + Web Scraping

The pipeline extracts URLs from the Stage 1 output and applies a second deterministic ranking step.

The top **3 URLs** are selected for scraping.

The scraper uses:

- `requests.Session`
- `BeautifulSoup`
- HTTP status validation
- Two attempts per URL
- HTML noise removal
- Minimum-content validation

The following HTML elements are removed:

```text
script
style
nav
footer
header
aside
form
```

The scraper then:

1. Extracts paragraph text.
2. Normalizes whitespace.
3. Rejects content shorter than 400 characters.
4. Limits each successfully scraped source to 2500 characters.
5. Stores the source URL with the extracted text.

### Why filter before scraping?

Scraping only the selected sources reduces unnecessary network requests and keeps downstream LLM input smaller.

---

## 3. Research Reasoning

The cleaned search results and scraped content are passed to the reasoning chain.

The reasoning prompt asks the LLM to identify:

- Key themes
- Patterns
- Contradictions
- Strong sources
- Missing data / weak areas

Conceptually:

```text
Search Results + Scraped Content
              ↓
       Reasoning LLM
              ↓
Themes / Patterns / Contradictions
Strong Sources / Weak Areas
```

The reasoning stage is **analysis of the research landscape**. It is different from evidence extraction: reasoning identifies how the research fits together, while evidence extraction isolates concrete supporting facts.

---

## 4. Evidence Extraction

The scraped content is passed to a dedicated evidence-extraction chain.

The prompt asks for:

- Statistics
- Factual claims
- Projections

and instructs the model to ignore opinions and fluff.

```text
Scraped Content
      ↓
Evidence LLM
      ↓
Statistics
Factual Claims
Projections
```

### Evidence vs. Reasoning

**Evidence:**  
A source reports a particular statistic, fact, or projection.

**Reasoning:**  
The research material contains a broader pattern, contradiction, or gap.

The two outputs are later supplied to the report writer.

---

## 5. Insight Generation

The insight chain receives:

- Scraped research content
- Extracted evidence

It is instructed to focus on:

- Why trends exist
- Economic or technical reasoning
- Broader implications

It is explicitly instructed not to simply repeat facts.

```text
Research Data + Evidence
          ↓
    Insight LLM
          ↓
Deeper Research Insights
```

---

## 6. Report Writer

The writer receives:

- Topic
- Search results
- Scraped content
- Reasoning
- Evidence
- Insights

The writer prompt asks for a professional report with this structure:

1. Introduction
2. Methodology
3. Key Findings
4. Deep Analysis
5. Limitations
6. Conclusion
7. Sources

The writer is instructed to:

- Use reasoning, evidence, and insights
- Avoid fluff and repetition
- Be analytical rather than purely descriptive
- Compare sources
- Say `insufficient evidence` when the available data is weak

---

## 7. Critic Review

The initial report is sent to a separate critic chain.

The critic evaluates the report on:

- Depth
- Reasoning
- Evidence usage
- Structure

It returns:

```text
Score: X/10
Strengths:
Weaknesses:
Improvements:
Verdict:
```

### Important limitation

The current critic receives **only the generated report**. It does not receive the original evidence or scraped sources, so it is a report-quality evaluator rather than an independent claim-by-claim fact verifier.

---

## 8. Improver

The improver receives:

- The original report
- Critic feedback

It is instructed to:

- Fix weak parts only
- Improve reasoning
- Improve clarity
- Improve structure
- Avoid rewriting the entire report unnecessarily

```text
Initial Report + Critic Feedback
             ↓
        Improver LLM
             ↓
        Final Report
```

---

#  LLM Architecture

The project defines **six LangChain LLM chains**:

| Chain | Responsibility |
|---|---|
| `reasoning_chain` | Research analysis |
| `evidence_chain` | Evidence extraction |
| `insight_chain` | Insight generation |
| `writer_chain` | Report generation |
| `critic_chain` | Report evaluation |
| `improver_chain` | Final refinement |

All six chains use the same `ChatGroq` model configuration:

```text
Model: llama-3.1-8b-instant
Provider: Groq
Temperature: 0.2
```

The chains follow this pattern:

```text
ChatPromptTemplate
        ↓
ChatGroq
        ↓
StrOutputParser
```

### LLM calls per research run

In the normal successful path, the pipeline makes **6 LLM calls**:

```text
1. Reasoning
2. Evidence Extraction
3. Insight Generation
4. Report Writer
5. Critic
6. Improver
```

Tavily search and BeautifulSoup scraping are **not LLM calls**.

The current pipeline executes these six calls sequentially.

---

#  Why a Controlled Pipeline?

SynapseAI is intentionally implemented as a **controlled orchestration pipeline**, rather than a fully autonomous tool-calling agent.

The application decides the order:

```text
Search
  ↓
Rank + Scrape
  ↓
Reason
  ↓
Extract Evidence
  ↓
Generate Insights
  ↓
Write
  ↓
Critic
  ↓
Improve
```

This provides:

- Predictable execution
- Clear stage responsibilities
- Easier debugging
- Better observability
- Controlled API usage
- Simpler failure handling

The LLM is responsible for reasoning and generation tasks, while deterministic Python code handles URL extraction, domain scoring, filtering, and scraping.

> The code uses LangChain `@tool` wrappers for web search and scraping, but the current workflow does not let an LLM dynamically choose which tool to call or dynamically change the pipeline order.

---

#  Backend API

The FastAPI backend exposes:

```http
POST /api/research
```

### Request

```json
{
  "topic": "Impact of AI on healthcare in the next five years"
}
```

### Response shape

```json
{
  "success": true,
  "topic": "Impact of AI on healthcare in the next five years",
  "data": {
    "search_results": "...",
    "scraped_content": "...",
    "reasoning": "...",
    "evidence": "...",
    "insights": "...",
    "report": "...",
    "feedback": "...",
    "final_report": "..."
  }
}
```

The backend also exposes:

```http
GET /
```

which returns a simple backend health message.

The research endpoint validates that the topic is not empty and returns an HTTP 400 error when it is missing.

---

#  Frontend

The frontend is a React application built with Vite.

Current frontend dependencies include:

- React 19
- React DOM
- React Router
- Framer Motion
- Lucide React
- Vite

The application currently has three main routes:

```text
/              → Home
/research      → Research
/engineering   → Engineering
```

The frontend communicates with the FastAPI backend and provides the research experience and engineering/workflow views.

---

#  Project Structure

```text
SynapseAI/
│
├── Frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── ...
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── eslint.config.js
│
├── agents.py
├── main.py
├── pipeline.py
├── tools.py
├── requirements.txt
├── runtime.txt
├── .python-version
└── .gitignore
```

### Backend files

| File | Responsibility |
|---|---|
| `main.py` | FastAPI app, CORS, request model, API endpoints |
| `pipeline.py` | 8-stage pipeline orchestration and state management |
| `agents.py` | LLM prompts and six LangChain chains |
| `tools.py` | Tavily search, domain scoring, URL filtering, scraping |
| `requirements.txt` | Python dependencies |

---

#  Tech Stack

## AI / LLM

- Groq
- Llama 3.1 8B Instant
- LangChain
- Prompt Engineering
- LLM-based Reasoning
- Evidence Extraction
- Insight Generation
- Critic-based Evaluation

## Backend

- Python
- FastAPI
- Pydantic
- Uvicorn
- Gunicorn

## Web Retrieval

- Tavily Search API
- Requests
- BeautifulSoup
- lxml
- html5lib

## Frontend

- React 19
- Vite
- React Router
- Framer Motion
- Lucide React

## Utilities

- python-dotenv
- pandas
- tiktoken
- rich
- tenacity
- orjson
- aiohttp

---

#  Reliability and Failure Handling

### Tavily failure

Search exceptions are caught and converted into a fallback string.

### Scraping failure

Each URL gets up to **2 attempts**.

```text
Request
  ↓
Failure?
  ├── No → Validate content → Save
  └── Yes → Retry once
                  ↓
              Still fails
                  ↓
            Mark as failed
```

If scraping fails at the stage level, the pipeline falls back to the search results.

### Content validation

Scraped pages with fewer than 400 characters of extracted paragraph text are not accepted as successful content.

### LLM failure handling

Each LLM stage has its own exception handling. If a stage fails, an error string is stored in the corresponding state field and the pipeline continues to the next stage.

---

#  Key Engineering Decisions

### 1. Deterministic source filtering

The system uses domain-based scoring instead of asking an LLM to rank every source.

This makes the filtering:

- Fast
- Explainable
- Predictable
- Low-cost

### 2. Two-level URL selection

The search tool first filters and ranks Tavily results to the best 5 high-quality results.

The pipeline then extracts those URLs and applies a second domain-score ranking to select the top 3 URLs for scraping.

### 3. Specialized LLM stages

The project separates:

```text
Reasoning
Evidence
Insights
Writing
Criticism
Improvement
```

instead of using one large prompt for the entire task.

### 4. Low temperature

A temperature of `0.2` is used to encourage relatively consistent outputs for research-oriented generation.

### 5. Source preprocessing before LLM stages

Web content is cleaned and truncated before being passed downstream, reducing noise and context size.

### 6. Critic → Improver loop

The generated report goes through a dedicated review stage before the final version is returned.

---

#  End-to-End Data Flow

```text
User Topic
    │
    ▼
Tavily Search
    │
    ▼
Up to 10 Search Results
    │
    ▼
Filter + Domain Score
    │
    ▼
Top 5 Search Results
    │
    ▼
Extract URLs + Re-rank
    │
    ▼
Top 3 URLs
    │
    ▼
Requests + BeautifulSoup
    │
    ▼
Cleaned / Truncated Web Content
    │
    ├──────────────► Reasoning LLM
    │                       │
    │                       ▼
    │                  Reasoning
    │
    └──────────────► Evidence LLM
                            │
                            ▼
                         Evidence
                            │
              Research + Evidence
                            │
                            ▼
                    Insight LLM
                            │
                            ▼
                         Insights
                            │
    Topic + Research + Reasoning + Evidence + Insights
                            │
                            ▼
                       Writer LLM
                            │
                            ▼
                     Initial Report
                            │
                            ▼
                       Critic LLM
                            │
                            ▼
                       Feedback
                            │
                            ▼
                      Improver LLM
                            │
                            ▼
                      Final Report
```

---

#  Example

### Input

```text
What will be the impact of AI on healthcare in the next five years?
```

### Pipeline execution

```text
1. Search the web
        ↓
2. Filter and rank credible domains
        ↓
3. Select top URLs and scrape their content
        ↓
4. Analyze themes, patterns, contradictions and weak areas
        ↓
5. Extract statistics, factual claims and projections
        ↓
6. Generate deeper insights
        ↓
7. Write a structured research report
        ↓
8. Critique the report
        ↓
9. Improve weak areas
        ↓
10. Return final report
```

---

#  Getting Started

## Prerequisites

- Python 3.10+ recommended
- Node.js and npm
- Groq API key
- Tavily API key

## 1. Clone the repository

```bash
git clone https://github.com/mayurramani07/SynapseAI.git
cd SynapseAI
```

## 2. Create and activate a Python environment

```bash
python -m venv venv
```

### Windows

```bash
venv\Scripts\activate
```

### macOS / Linux

```bash
source venv/bin/activate
```

## 3. Install backend dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure environment variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key
FRONTEND_URL=http://localhost:5173
```

## 5. Start the backend

```bash
uvicorn main:app --reload
```

Backend:

```text
http://localhost:8000
```

Swagger documentation:

```text
http://localhost:8000/docs
```

## 6. Start the frontend

```bash
cd Frontend
npm install
npm run dev
```

Use the Vite development URL shown in the terminal.

---

#  Environment Variables

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` | Groq LLM API authentication |
| `TAVILY_API_KEY` | Tavily web search authentication |
| `FRONTEND_URL` | Frontend origin allowed by FastAPI CORS |

Never commit API keys or `.env` files.

---

#  Current Limitations

- Domain scoring is heuristic and does not perform semantic relevance ranking.
- Search results are limited to the sources that Tavily returns.
- Some websites may block automated requests or expose limited content.
- The scraper only extracts paragraph text and truncates each successful source to 2500 characters.
- The critic currently receives only the generated report, so it is not an independent claim-by-claim fact checker.
- LLM outputs can still require human validation, especially for high-stakes research.
- The pipeline is stateless between requests; research sessions are not persisted as conversational memory.
- The six LLM stages run sequentially in the current implementation.

---

#  Future Improvements

- [ ] Semantic URL relevance reranking
- [ ] Source-level citation mapping
- [ ] Claim-to-evidence verification
- [ ] Structured JSON outputs from LLM stages
- [ ] Parallelize independent preprocessing/retrieval work
- [ ] Redis caching for repeated research
- [ ] Persistent research history
- [ ] User-specific memory
- [ ] LangGraph-based orchestration
- [ ] More robust extraction for difficult websites
- [ ] Automated report-quality evaluation datasets
- [ ] Better source diversity and deduplication

---

#  What This Project Demonstrates

SynapseAI demonstrates practical experience with:

- LLM application development
- Prompt engineering
- LangChain
- AI workflow orchestration
- Web search and retrieval
- Deterministic source filtering
- Web scraping
- Evidence extraction
- LLM reasoning
- Insight generation
- Structured report generation
- Critic-based evaluation
- FastAPI REST APIs
- React frontend integration
- Error handling and fallbacks
- AI system architecture
- Reliability and cost-aware design

---

#  Author

**Mayur Ramani**

Built independently to explore reliable, source-grounded AI research workflows.

---

##  Links

- Live Demo: https://synapse-ai-green.vercel.app/
- GitHub Repository: https://github.com/mayurramani07/SynapseAI
