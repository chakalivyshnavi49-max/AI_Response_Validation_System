# AI Response Validation System — Milestones 1–4

A professional, end-to-end Streamlit platform for evaluating AI-generated responses across **Relevance, Accuracy, Hallucination Detection, Completeness**, and a weighted **Verdict**.

## Included scope

### Milestone 1 — Foundation
- Evaluation input module: question, AI response, optional reference answer/source document.
- Local reference knowledge base with CSV/JSON/text ingestion.
- Cleaning, chunking, TF-IDF embedding, semantic retrieval.
- SQLite persistence for evaluation records.
- Architecture, scoring definitions, data models, and technical documentation.

### Milestone 2 — Judge Agents
- Relevance Judge Agent.
- Accuracy Judge Agent with evidence.
- Hallucination Detection Agent with claim-level flags.
- Shared Evaluation Orchestrator.
- Consistency-oriented benchmark tests.

### Milestone 3 — Completeness, Verdict, Batch
- Completeness Judge Agent.
- Weighted Verdict Agent with configurable weights and critical-failure rules.
- Per-dimension result display.
- CSV batch upload, validation, progress, partial-failure handling, aggregation.

### Milestone 4 — Dashboard, PDF, Testing, Documentation
- Executive dashboard with interactive charts and filters.
- PDF batch report export.
- End-to-end tests.
- Technical architecture, scoring methodology, CSV schema, demonstration guide, and project report template.

## Quick start (Windows)

```powershell
cd AI_Response_Validation_System_M1_M4
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501`.

## Quick start (Command Prompt)

```bat
cd AI_Response_Validation_System_M1_M4
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Demo data

- `data/reference_knowledge.csv` — small source KB used by the RAG retriever.
- `data/sample_batch.csv` — sample multi-record evaluation file.

## Important implementation note

This package is intentionally **offline-first** so it can run without an API key. The judge agents use transparent deterministic scoring rules and are structured behind a common interface. For a production LLM-as-a-Judge deployment, replace the scoring internals with an LLM provider while keeping the same structured output contracts.

## Project structure

```text
AI_Response_Validation_System_M1_M4/
├── app.py
├── requirements.txt
├── README.md
├── src/
│   ├── core/
│   │   ├── models.py
│   │   └── orchestrator.py
│   ├── agents/
│   │   ├── relevance_agent.py
│   │   ├── accuracy_agent.py
│   │   ├── hallucination_agent.py
│   │   ├── completeness_agent.py
│   │   └── verdict_agent.py
│   ├── rag/
│   │   └── retriever.py
│   ├── storage/
│   │   └── database.py
│   └── reporting/
│       └── pdf_report.py
├── data/
├── docs/
└── tests/
```

## Fixes for the import errors you previously saw

All agent functions are now named consistently and accept the same `question, response, ...` pattern where applicable. In particular:

```python
from src.agents.accuracy_agent import evaluate_accuracy
from src.agents.hallucination_agent import detect_hallucination
from src.agents.relevance_agent import evaluate_relevance
from src.agents.completeness_agent import evaluate_completeness
```

The orchestrator calls them with their defined signatures, so the earlier `ImportError` and `takes 2 positional arguments but 3 were given` mismatch is removed.
