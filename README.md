# Database + document chatbot

Agentic workflow architecture exported from **[Agentic LaunchPad](https://github.com)** by Affine Analytics.

> This repository is a scaffold generated from an interactive architecture interview and visual workflow builder. Implement each agent step per the plan below.

## At a glance

- **Session:** `session-1784805317987-jldkil`
- **Steps:** 9
- **Connections:** 8
- **Exported:** 2026-07-31 09:52 UTC

## Problem statement

Business analysts need a chatbot that can answer questions across approved enterprise documents and structured database tables without relying on general model knowledge, while preserving trust through evidence-backed responses.

## Requirements

### Key requirements

- **Use case:** Provide a single natural-language chatbot experience that combines document retrieval and database querying into one grounded answer, flags conflicts between sources, and refuses to answer when evidence is insufficient.
- **Human-in-the-loop:** No human review step is currently required. The system is expected to serve analysts directly and refuse unsupported answers rather than route them for manual validation.
- **Data flow:** Business analysts submit a question through the chatbot UI. The system interprets the request and determines whether it needs document evidence, database evidence, or both. It retrieves relevant passages from approved documents and generates then executes constrained SQL against approved tables using the analyst's access scope. Retrieved passages and query results are normalized into a common evidence set, checked for conflicts, and passed to the answer generation step. The model produces one grounded natural-language response with citations only if the evidence is sufficient. If evidence is missing or weak, the system refuses to answer. The final response exits through the chatbot interface to the analyst.
- **Core components:** User question intake, Question understanding and intent routing, Access-aware document retrieval, Access-aware SQL generation and database query execution, Evidence normalization across document and table results, Conflict detection across sources, Answer synthesis with citations, Evidence sufficiency check and refusal handling, Response delivery to analyst
- **Architectural flow:** User question intake → Question understanding and intent routing → Access-aware document retrieval → Access-aware SQL generation and database query execution → Evidence normalization across document and table results → Conflict detection across sources → Answer synthesis with citations → Evidence sufficiency check and refusal handling → Response delivery to analyst

### Interview summary

Provide a single natural-language chatbot experience that combines document retrieval and database querying into one grounded answer, flags conflicts between sources, and refuses to answer when evidence is insufficient.

### Architecture blueprint

## Provide a single natural-language chatbot experience that combines document retrieval and database querying into one grounded answer, flags conflicts between sources, and refuses to answer when evidence is insufficient.

Business analysts need a chatbot that can answer questions across approved enterprise documents and structured database tables without relying on general model knowledge, while preserving trust through evidence-backed responses.

### Integrations

### HITL
No human review step is currently required. The system is expected to serve analysts directly and refuse unsupported answers rather than route them for manual validation.

## Architecture summary

This architecture implements a grounded hybrid QA chatbot for business analysts using a true parallel orchestration model: after intake and routing, the flow fans out into document retrieval and SQL generation/execution simultaneously, then rejoins for evidence reconciliation, conflict detection, answer synthesis, sufficiency gating, and response delivery. Because the spec requires answers to combine approved enterprise documents and structured tables without relying on general model knowledge, the design keeps all reasoning anchored to retrieved passages and executed query results.

The strongest reuse opportunities come from the Affine catalog: Pipeline Intent Classifier handles routing, Eryl Semantic RAG Agent Chain covers document retrieval, Quin SQL Agent Chain covers structured query generation/execution, Final Answer Consolidation Agent synthesizes the grounded response, and Final Answer Rewriter formats the final chatbot output. This yields 5 of 9 nodes as catalog reuse, satisfying the catalog-first requirement while preserving a clean left-to-right graph. Custom build is reserved only for capabilities not present in the catalog: intake, evidence reconciliation, conflict detection, and the evidence sufficiency/refusal gate.

No human-in-the-loop step is included because the spec explicitly states that analysts should be served directly and unsupported questions should be refused rather than routed for manual review. Key implementation risk areas are access-aware enforcement across both retrieval paths, robust normalization of heterogeneous SQL and document evidence, and precise refusal logic so the system declines unsupported questions instead of hallucinating. If document indexing is not already available in the target environment, GraphRAG Index & Query Agent could be added in a future phase as a preprocessing/index maintenance component, but it is not required in the runtime graph as currently specified.

## Workflow overview

This architecture has **9** step(s) and **8** connection(s).

### Execution flow

- **User Question Intake** → *user question and session context* → **Question Understanding and Intent Routing**
- **Question Understanding and Intent Routing** → *document evidence route* → **Access-Aware Document Retrieval**
- **Question Understanding and Intent Routing** → *structured data route* → **Access-Aware SQL Generation and Execution**
- **Access-Aware Document Retrieval** → *retrieved passages with citations* → **Evidence Normalization and Reconciliation**
- **Access-Aware SQL Generation and Execution** → *query results and provenance* → **Evidence Normalization and Reconciliation**
- **Evidence Normalization and Reconciliation** → *normalized cross-source evidence set* → **Conflict Detection Across Sources**
- **Conflict Detection Across Sources** → *evidence plus conflict annotations* → **Grounded Answer Synthesis with Citations**
- **Evidence Sufficiency and Refusal Gate** → *approved answer or refusal payload* → **Response Delivery to Analyst**

## Agents & steps

### User Question Intake

*tool* · **build**

Receives the analyst's question and session context from the chatbot interface.

*Rationale:* No catalog match provides intake capability, so the chatbot entrypoint should be implemented as a custom UI/API node.

**Purpose:** Capture the analyst's natural-language question and session context as the trusted starting point for the workflow.

**Role:** This is the entry step where the chatbot receives the user's request, identity, and any session metadata needed for downstream access-aware processing. It establishes the exact question that will be routed into document retrieval, SQL querying, or both.

**Execution:** Receives the analyst's question and session context from the chatbot interface.

**Feeds into:**
- Question Understanding and Intent Routing
- user question and session context

### Question Understanding and Intent Routing

*agent* · catalog `pipeline_intent_classifier` · **build** · Pipeline Intent Classifier

Classifies the question and routes it to the document path, SQL path, or both.

*Rationale:* This agent directly matches routing capability and is well suited to classify whether the question needs document, SQL, or unified handling.

**Purpose:** Determine whether the question needs document evidence, database evidence, or both, and route it accordingly.

**Role:** After intake, this step interprets the user's request and decides which grounded evidence paths should run. It can trigger the document retrieval path, the SQL path, or both in parallel so the system can produce one combined answer.

**Execution:** Classifies the question and routes it to the document path, SQL path, or both.

**Consumes from:**
- User Question Intake
- user question and session context

**Feeds into:**
- Access-Aware Document Retrieval
- Access-Aware SQL Generation and Execution
- document evidence route
- structured data route

### Access-Aware Document Retrieval

*agent* · catalog `eryl_semantic_rag_agent_chain` · **reuse** · Eryl Semantic RAG Agent Chain

Finds relevant approved document passages and returns them with citations.

*Rationale:* This agent already provides document retrieval over indexed enterprise content and fits the approved-document evidence path.

**Purpose:** Retrieve relevant evidence passages from approved enterprise documents within the analyst's access scope.

**Role:** When the router determines that unstructured evidence is needed, this step searches the approved document corpus and returns the most relevant passages with citation metadata. Its output becomes one half of the evidence base used for the final grounded answer.

**Execution:** Finds relevant approved document passages and returns them with citations.

**Consumes from:**
- Question Understanding and Intent Routing
- document evidence route

**Feeds into:**
- Evidence Normalization and Reconciliation
- retrieved passages with citations

### Access-Aware SQL Generation and Execution

*agent* · catalog `quin_sql_agent_chain` · **reuse** · Quin SQL Agent Chain

Creates and runs access-controlled SQL queries to return structured evidence from approved tables.

*Rationale:* This chain explicitly supports SQL generation and execution against approved tables, matching the structured evidence path.

**Purpose:** Generate and execute constrained SQL against approved tables to produce structured evidence for the answer.

**Role:** When the router determines that structured data is needed, this step translates the user's question into safe SQL, runs it against approved tables, and returns results with provenance. Its output supplies the database-backed evidence stream that can be combined with document findings.

**Execution:** Creates and runs access-controlled SQL queries to return structured evidence from approved tables.

**Consumes from:**
- Question Understanding and Intent Routing
- structured data route

**Feeds into:**
- Evidence Normalization and Reconciliation
- query results and provenance

### Evidence Normalization and Reconciliation

*custom* · **build**

Transforms document and SQL outputs into one normalized evidence set with citations and provenance.

*Rationale:* No catalog agent exposes evidence_reconciliation capability, so a custom merge layer is needed to normalize SQL and document outputs.

**Purpose:** Normalize document passages and SQL outputs into a single comparable evidence set with source metadata.

**Role:** This step sits after both retrieval branches and converts their different output formats into a common evidence structure. It prepares citations, provenance, and normalized facts so downstream conflict detection and answer synthesis can reason across sources consistently.

**Execution:** Transforms document and SQL outputs into one normalized evidence set with citations and provenance.

**Consumes from:**
- Access-Aware Document Retrieval
- Access-Aware SQL Generation and Execution
- retrieved passages with citations
- query results and provenance

**Feeds into:**
- Conflict Detection Across Sources
- normalized cross-source evidence set

### Conflict Detection Across Sources

*custom* · **build**

Checks the unified evidence for cross-source disagreements and adds conflict annotations.

*Rationale:* Conflict detection is a required trust feature and no catalog match includes conflict_detection capability.

**Purpose:** Identify disagreements or mismatches between document evidence and database evidence before answering.

**Role:** Using the normalized evidence set, this step checks whether the two source types support the same conclusion or whether they diverge. It annotates conflicts so the answer can surface them explicitly instead of silently choosing one source.

**Execution:** Checks the unified evidence for cross-source disagreements and adds conflict annotations.

**Consumes from:**
- Evidence Normalization and Reconciliation
- normalized cross-source evidence set

**Feeds into:**
- Grounded Answer Synthesis with Citations
- evidence plus conflict annotations

### Grounded Answer Synthesis with Citations

*agent* · catalog `final_answer_consolidation_agent` · **build** · Final Answer Consolidation Agent

Builds one cited, grounded answer draft from the reconciled evidence and conflict annotations.

*Rationale:* This agent is the best direct fit for composing a single grounded response from multiple evidence streams.

**Purpose:** Compose a single natural-language answer grounded in the collected evidence and include citations and any conflict flags.

**Role:** After evidence has been normalized and checked for conflicts, this step turns the evidence set into one coherent response draft. It preserves source citations and conflict annotations so the answer remains transparent and evidence-backed.

**Execution:** Builds one cited, grounded answer draft from the reconciled evidence and conflict annotations.

**Consumes from:**
- Conflict Detection Across Sources
- evidence plus conflict annotations

**Feeds into:**
- Evidence Sufficiency and Refusal Gate
- draft grounded answer with citations

### Evidence Sufficiency and Refusal Gate

*gateway* · **build**

Approves well-supported answers or triggers a refusal when evidence is insufficient.

*Rationale:* A custom gateway is needed to enforce refusal behavior based on evidence sufficiency because no catalog agent provides quality_evaluation.

**Purpose:** Decide whether the drafted answer is sufficiently supported by evidence or must be refused.

**Role:** This gateway evaluates the grounded answer and its supporting evidence before anything is shown to the analyst. If support is strong enough, it passes the answer forward; if evidence is weak, missing, or insufficiently grounded, it converts the outcome into a refusal payload.

**Execution:** Approves well-supported answers or triggers a refusal when evidence is insufficient.

**Consumes from:**
- Grounded Answer Synthesis with Citations
- draft grounded answer with citations

**Feeds into:**
- Response Delivery to Analyst
- approved answer or refusal payload

### Response Delivery to Analyst

*agent* · catalog `final_answer_rewriter` · **build** · Final Answer Rewriter

Formats and returns the final supported answer or refusal to the analyst.

*Rationale:* This agent can format the approved answer or refusal into concise user-facing chatbot text without introducing unsupported content.

**Purpose:** Present the approved answer or refusal to the analyst in concise chatbot form without adding new facts.

**Role:** This is the final user-facing step that formats the approved payload into a clean chatbot response. It preserves the grounded content, citations, and any refusal or conflict messaging while ensuring the final wording stays concise and safe.

**Execution:** Formats and returns the final supported answer or refusal to the analyst.

**Consumes from:**
- Evidence Sufficiency and Refusal Gate
- approved answer or refusal payload

## Reuse decisions

- **User Question Intake** — `build` → custom
  - No catalog match provides intake capability, so the chatbot entrypoint should be implemented as a custom UI/API node.
- **Question Understanding and Intent Routing** — `build` → Pipeline Intent Classifier
  - This agent directly matches routing capability and is well suited to classify whether the question needs document, SQL, or unified handling.
- **Access-Aware Document Retrieval** — `reuse` → Eryl Semantic RAG Agent Chain
  - This agent already provides document retrieval over indexed enterprise content and fits the approved-document evidence path.
- **Access-Aware SQL Generation and Execution** — `reuse` → Quin SQL Agent Chain
  - This chain explicitly supports SQL generation and execution against approved tables, matching the structured evidence path.
- **Evidence Normalization and Reconciliation** — `build` → custom
  - No catalog agent exposes evidence_reconciliation capability, so a custom merge layer is needed to normalize SQL and document outputs.
- **Conflict Detection Across Sources** — `build` → custom
  - Conflict detection is a required trust feature and no catalog match includes conflict_detection capability.
- **Grounded Answer Synthesis with Citations** — `build` → Final Answer Consolidation Agent
  - This agent is the best direct fit for composing a single grounded response from multiple evidence streams.
- **Evidence Sufficiency and Refusal Gate** — `build` → custom
  - A custom gateway is needed to enforce refusal behavior based on evidence sufficiency because no catalog agent provides quality_evaluation.
- **Response Delivery to Analyst** — `build` → Final Answer Rewriter
  - This agent can format the approved answer or refusal into concise user-facing chatbot text without introducing unsupported content.

## Catalog matches

- **Eryl Semantic RAG Agent Chain** (`eryl_semantic_rag_agent_chain`) — score 0.90
  - Matched for: capability_slot:document_retrieval
  - Retrieves and answers from indexed retail policy and unstructured documents (Chocolate_Confectionery_Retail_Policy.docx, emails, guidelines) using Azure AI Search vector + semantic retrieval.
- **GraphRAG Index & Query Agent** (`graphrag_index_query_agent`) — score 0.86
  - Matched for: capability_slot:document_retrieval
  - Indexes per-project KYC documents into a knowledge graph with entity/community extraction and embeddings; answers analyst questions via local, global, drift, or basic search methods.
- **Final Answer Consolidation Agent** (`final_answer_consolidation_agent`) — score 0.85
  - Matched for: capability_slot:answer_synthesis
  - Consolidates count and generic row-level analyses into a single natural-language answer based on task_type routing.
- **Pipeline Intent Classifier** (`pipeline_intent_classifier`) — score 0.85
  - Matched for: capability_slot:intent_routing
  - Classifies each user question into vision_only, vision_then_unified, or unified_only and flags multi-shelf comparisons for SQL-only routing.
- **Quin SQL Agent Chain** (`quin_sql_agent_chain`) — score 0.85
  - Matched for: capability_slot:structured_sql
  - AutoGen multi-agent chain that generates, executes, and critiques SQL Server queries on mars schema tables (Mars_Sales_Data, shelf_visit, retail_planogram_stocks, etc.) and returns structured sales/inventory insights.
- **Final Answer Rewriter** (`final_answer_rewriter`) — score 0.85
  - Matched for: capability_slot:answer_synthesis
  - Post-processes combined vision+SQL+semantic draft answers into concise structured user-facing text without adding new facts.

## Open questions

- Are enterprise documents already indexed and access-filtered, or should a separate indexing pipeline be added before runtime retrieval?
- Should the SQL path support only read-only approved views, or can it query broader warehouse tables under row-level security?
- What citation format is required in the chatbot response for document passages versus SQL-derived facts?
- What threshold or policy defines evidence sufficiency for refusal when only one source returns support but the other is silent?

## Validation notes

Overall status: **warn**

- [warn] Spec requires human-in-the-loop but no 'human' step appears on the graph.
- [warn] Are enterprise documents already indexed and access-filtered, or should a separate indexing pipeline be added before runtime retrieval?
- [warn] Should the SQL path support only read-only approved views, or can it query broader warehouse tables under row-level security?
- [warn] What citation format is required in the chatbot response for document passages versus SQL-derived facts?
- [warn] What threshold or policy defines evidence sufficiency for refusal when only one source returns support but the other is silent?

## Repository contents

| Path | Description |
|------|-------------|
| `README.md` | This overview |
| `workflow.json` | Full architecture graph, reuse decisions, and layout |
| `session.json` | Interview spec and session metadata (when available) |
| `agents/*.json` | Per-step scaffold files for implementation |

## Next steps

1. Review the architecture summary and agent steps above
2. Open `workflow.json` for the complete graph and reuse decisions
3. Implement each step under `agents/` using your runtime of choice
4. Wire integrations and HITL paths described in the requirements

---
*Generated by Agentic LaunchPad on 2026-07-31 09:52 UTC*