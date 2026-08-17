"""Analysis-type router for the database and document chatbot.

After chat intake validates the user question, this module classifies it into
one of four analysis routing paths. Each path determines which downstream
retrieval chains run and how the workflow orchestrator fans out before evidence
reconciliation.

Routing paths
-------------

1. **Semantic-based** — document-only questions answerable from indexed
   enterprise documents (policies, emails, memos). Sets ``run_document=True``,
   ``run_sql=False``, and dispatches solely to the Eryl semantic RAG
   document-retrieval chain.

2. **SQL-based** — structured questions requiring tabular or database evidence
   (aggregates, counts, inventory, sales). Sets ``run_document=False``,
   ``run_sql=True``, and dispatches solely to the Quin SQL answering chain.

3. **Both-dependent** — hybrid questions where SQL and document evidence must
   be correlated; the final answer depends on merging interdependent structured
   query results with document context. Sets ``run_document=True``,
   ``run_sql=True``, fans out to both chains, and merges outputs at evidence
   reconciliation.

4. **Both-independent** — hybrid questions where SQL and document branches
   can run in parallel without strict ordering; both chains execute concurrently
   and reconciliation synthesizes whichever sources return grounded evidence.
   The current classifier maps the ``both`` route to this analysis type.

Output contract
---------------

The router emits a ``routing_decision`` dict consumed by the orchestrator:

- ``run_document`` / ``run_sql`` — booleans gating each retrieval branch
- ``initial_question`` — normalized user question forwarded to reuse chains
- ``analysis_type`` — one of the four path labels above
- ``rationale`` — classifier explanation for auditability
- ``refusal_reason`` — set to ``permission_denied`` when session scope disables
  both paths (via ``allowed_document_ids`` / ``allowed_tables``)

Classification uses Azure OpenAI in live mode and keyword heuristics in dry-run
mode. Classifier failures default to the ``both`` route when permissions allow.
"""

from agents.generated.question_routing.agent import execute, run

__all__ = ["execute", "run"]
