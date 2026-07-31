# Database + document chatbot

Evidence-backed chatbot for business analysts across approved enterprise documents (Azure AI Search) and structured SQL tables.

## Quickstart

```bash
git clone https://github.com/affine-Nikhil-Sarwal/database-document-chatbot_v3.git
cd database-document-chatbot_v3
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with real Azure OpenAI, Azure Search, and SQL credentials
python main.py --health
python main.py --dry-run
python main.py --input-json examples/sample_input.json
```

## Run with HTTP

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
curl -s http://localhost:8000/health | jq
curl -s -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"user_question": "What were Q1 sales totals?", "session_context": {"allowed_document_ids": ["*"], "allowed_tables": ["*"]}}' | jq
```

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | Yes | Azure OpenAI resource URL (alias: `AZURE_OPENAI_API_BASE`) |
| `AZURE_OPENAI_API_KEY` | Yes | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | Yes | Chat deployment name (legacy: `GPT4_LLM_MODEL_DEPLOYMENT_NAME`) |
| `EMBEDDING_MODEL_DEPLOYMENT_NAME` | Yes | Embedding deployment for Eryl retrieval |
| `AZURE_SEARCH_SERVICE_ENDPOINT` | Yes | Azure AI Search endpoint |
| `AZURE_SEARCH_API_KEY` | Yes | Search admin/query key |
| `AZURE_SEARCH_INDEX_NAME` | No | Default `dupont_email_demo` |
| `AZURE_SEARCH_VECTOR_FIELD_NAME` | No | Default `content_vector` |
| `AZURE_SEARCH_DOCUMENT_ID_FIELD_NAME` | No | Default `id` |
| `DATABASE_URL` or `SQL_*` | Yes for SQL path | SQL Server connection for Quin |

Missing required variables raise `ConfigurationError` with the variable name — the app never substitutes placeholders.

## Workflow

1. **User question intake** — validates question and session context  
2. **Question routing** — classifies document / SQL / both paths  
3. **Document retrieval** (Eryl reuse) + **SQL query chain** (Quin reuse) in parallel when both enabled  
4. **Evidence reconciliation** — normalized citations `[Doc-n]` / `[SQL-n]`  
5. **Conflict detection** — flags cross-source disagreements  
6. **Answer consolidation** — grounded draft with citations  
7. **Evidence sufficiency gate** — approve or refuse  
8. **Response delivery** — final analyst-facing text  

## Tests

```bash
python scripts/check_placeholders.py
python -m pytest tests/ -q
python main.py --dry-run
```

## Project layout

| Path | Purpose |
|------|---------|
| `main.py` | CLI + FastAPI entry |
| `orchestrator/graph.py` | Workflow wiring (`run_workflow_from_node`) |
| `agents/generated/` | Build nodes |
| `agents/reused/` | Frozen Eryl + Quin agents |
| `agents/adapters/` | Pure I/O adapters |
| `integrations/` | Azure OpenAI, Search, SQL clients + health checks |
| `config/settings.py` | Pydantic settings from repo-root `.env` |
| `examples/sample_input.json` | Sample intake payload |
