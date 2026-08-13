# Internal employees need a chatbot that can answer analyst-style questions by combining information from structured databases and documents in one natural-language response, without requiring users to manually search dashboards, run queries, or read source files.

Agentic workflow architecture exported from **[Agentic LaunchPad](https://github.com)** by Affine Analytics.

> This repository is a scaffold generated from an interactive architecture interview and visual workflow builder. Implement each agent step per the plan below.

## At a glance

- **Session:** `session-1786614384962-jczp69`
- **Steps:** 7
- **Connections:** 15
- **Exported:** 2026-08-13 10:16 UTC

## Problem statement

Internal employees need a chatbot that can answer analyst-style questions by combining information from structured databases and documents in one natural-language response, without requiring users to manually search dashboards, run queries, or read source files.

## Requirements

### Interview summary

Provide a single internal chatbot that routes questions to the right data path, merges database and document results, and returns concise answers with warnings when confidence is low.

## Architecture summary

This architecture implements an internal-only hybrid analyst chatbot with a true parallel orchestration model: intake and safety screening, intent-based routing, structured SQL answering, document retrieval, evidence reconciliation, confidence evaluation, and final answer generation. The flow follows the provided spec closely and preserves the requirement that users receive only a concise natural-language answer, without raw evidence rows or document snippets.

The router fans out to both the SQL and document branches whenever the question requires hybrid reasoning (`Both-dependent` or `Both-independent`), satisfying the required hybrid retrieval pattern. Structured evidence is produced by the SQL chain, while document evidence is produced by the semantic RAG chain. These outputs join at a shared reconciliation step using the reusable Evidence Checker, which handles conflict detection and source-priority logic before a dedicated quality-evaluation pass determines whether the final response should include a low-confidence warning.

Reuse is high: all 7 processing steps use Affine catalog assets, with one light adaptation for the quality-evaluation output contract. This exceeds the catalog-first target and uses 6 distinct catalog agents across intake, routing, SQL, retrieval, validation, and delivery. No eval persistence node is included because the spec does not indicate that evaluation or audit results must be persisted.

Primary risks are capability gaps around the exact SQL agent selected and the need to configure routing labels consistently across the UI and orchestration layer. In particular, the higher-scoring `text_to_sql_analytics_agent` could not be used because its catalog capabilities are unspecified, so `quin_sql_agent_chain` is the compliant choice. Another implementation consideration is ensuring the Evidence Checker emits both merge decisions and confidence metadata in a schema the final answer agent can consume reliably.

## Workflow overview

This architecture has **7** step(s) and **15** connection(s).

### Execution flow

- **Chat Intake & Safety Gate** → *validated user question* → **Analysis Type Router**
- **Analysis Type Router** → *route to structured path* → **SQL Answering Chain**
- **Analysis Type Router** → *route to document path* → **Document Retrieval Chain**
- **Analysis Type Router** → *fan-out structured path* → **SQL Answering Chain**
- **Analysis Type Router** → *fan-out document path* → **Document Retrieval Chain**
- **Analysis Type Router** → *fan-out structured path* → **SQL Answering Chain**
- **Analysis Type Router** → *fan-out document path* → **Document Retrieval Chain**
- **SQL Answering Chain** → *structured evidence* → **Evidence Reconciliation & Confidence Gate**
- **Document Retrieval Chain** → *document evidence* → **Evidence Reconciliation & Confidence Gate**
- **SQL Answering Chain** → *structured evidence for hybrid merge* → **Evidence Reconciliation & Confidence Gate**
- **Document Retrieval Chain** → *document evidence for hybrid merge* → **Evidence Reconciliation & Confidence Gate**
- **SQL Answering Chain** → *structured evidence for hybrid merge* → **Evidence Reconciliation & Confidence Gate**
- **Document Retrieval Chain** → *document evidence for hybrid merge* → **Evidence Reconciliation & Confidence Gate**
- **Evidence Reconciliation & Confidence Gate** → *merged evidence and conflict flags* → **Answer Quality Evaluation**
- **Answer Quality Evaluation** → *quality score and warning flag* → **Final Natural-Language Answer**

## Agents & steps

### Chat Intake & Safety Gate

*agent* · **build**

Receives the internal user question and performs intake prechecks before orchestration.

*Rationale:* catalog match Intake Gateway (intake_gateway) has no seedable package in agent library

**Purpose:** Chat Intake & Safety Gate

**Role:** Chat Intake & Safety Gate is a agent step. Receives from Workflow entry. Passes to Analysis Type Router.

**Execution:** Receives the internal user question and performs intake prechecks before orchestration.

**Consumes from:**
- Workflow entry

**Feeds into:**
- Analysis Type Router

### Analysis Type Router

*gateway* · **build**

Classifies the question into SQL-based, Semantic-based, Both-dependent, or Both-independent paths.

*Rationale:* catalog match Pipeline Intent Classifier (pipeline_intent_classifier) has no seedable package in agent library

**Purpose:** Analysis Type Router

**Role:** Analysis Type Router is a gateway step. Receives from Chat Intake & Safety Gate. Passes to SQL Answering Chain, Document Retrieval Chain, SQL Answering Chain, Document Retrieval Chain, SQL Answering Chain, Document Retrieval Chain.

**Execution:** Classifies the question into SQL-based, Semantic-based, Both-dependent, or Both-independent paths.

**Consumes from:**
- Chat Intake & Safety Gate

**Feeds into:**
- SQL Answering Chain
- Document Retrieval Chain
- SQL Answering Chain
- Document Retrieval Chain
- SQL Answering Chain
- Document Retrieval Chain

### SQL Answering Chain

*agent* · catalog `quin_sql_agent_chain` · **reuse** · Quin SQL Agent Chain

Generates and executes SQL against structured sources to return analyst-ready structured evidence.

*Rationale:* matched Quin SQL Agent Chain

**Purpose:** SQL Answering Chain

**Role:** SQL Answering Chain is a agent step. Receives from Analysis Type Router, Analysis Type Router, Analysis Type Router. Passes to Evidence Reconciliation & Confidence Gate, Evidence Reconciliation & Confidence Gate, Evidence Reconciliation & Confidence Gate.

**Execution:** Generates and executes SQL against structured sources to return analyst-ready structured evidence.

**Consumes from:**
- Analysis Type Router
- Analysis Type Router
- Analysis Type Router

**Feeds into:**
- Evidence Reconciliation & Confidence Gate
- Evidence Reconciliation & Confidence Gate
- Evidence Reconciliation & Confidence Gate

### Document Retrieval Chain

*agent* · catalog `eryl_semantic_rag_agent_chain` · **adapt** · Eryl Semantic RAG Agent Chain

Retrieves relevant indexed document content for the user question from the document corpus.

*Rationale:* matched Eryl Semantic RAG Agent Chain

**Purpose:** Document Retrieval Chain

**Role:** Document Retrieval Chain is a agent step. Receives from Analysis Type Router, Analysis Type Router, Analysis Type Router. Passes to Evidence Reconciliation & Confidence Gate, Evidence Reconciliation & Confidence Gate, Evidence Reconciliation & Confidence Gate.

**Execution:** Retrieves relevant indexed document content for the user question from the document corpus.

**Consumes from:**
- Analysis Type Router
- Analysis Type Router
- Analysis Type Router

**Feeds into:**
- Evidence Reconciliation & Confidence Gate
- Evidence Reconciliation & Confidence Gate
- Evidence Reconciliation & Confidence Gate

### Evidence Reconciliation & Confidence Gate

*agent* · **build**

Reconciles SQL and document evidence, applies source-priority logic, and flags conflicts or weak support.

*Rationale:* catalog match Evidence Checker (evidence_checker) has no seedable package in agent library

**Purpose:** Evidence Reconciliation & Confidence Gate

**Role:** Evidence Reconciliation & Confidence Gate is a agent step. Receives from SQL Answering Chain, Document Retrieval Chain, SQL Answering Chain, Document Retrieval Chain, SQL Answering Chain, Document Retrieval Chain. Passes to Answer Quality Evaluation.

**Execution:** Reconciles SQL and document evidence, applies source-priority logic, and flags conflicts or weak support.

**Consumes from:**
- SQL Answering Chain
- Document Retrieval Chain
- SQL Answering Chain
- Document Retrieval Chain
- SQL Answering Chain
- Document Retrieval Chain

**Feeds into:**
- Answer Quality Evaluation

### Answer Quality Evaluation

*agent* · **build**

Scores groundedness and completeness to determine whether a low-confidence warning is needed.

*Rationale:* catalog match Evidence Checker (evidence_checker) has no seedable package in agent library

**Purpose:** Answer Quality Evaluation

**Role:** Answer Quality Evaluation is a agent step. Receives from Evidence Reconciliation & Confidence Gate. Passes to Final Natural-Language Answer.

**Execution:** Scores groundedness and completeness to determine whether a low-confidence warning is needed.

**Consumes from:**
- Evidence Reconciliation & Confidence Gate

**Feeds into:**
- Final Natural-Language Answer

### Final Natural-Language Answer

*agent* · **build**

Produces a concise natural-language response that merges results and includes a warning when confidence is low.

*Rationale:* catalog match Final Answer Consolidation Agent (final_answer_consolidation_agent) has no seedable package in agent library

**Purpose:** Final Natural-Language Answer

**Role:** Final Natural-Language Answer is a agent step. Receives from Answer Quality Evaluation. Passes to Workflow outcome.

**Execution:** Produces a concise natural-language response that merges results and includes a warning when confidence is low.

**Consumes from:**
- Answer Quality Evaluation

**Feeds into:**
- Workflow outcome

## Reuse decisions

- **Chat Intake & Safety Gate** — `build` → custom
  - catalog match Intake Gateway (intake_gateway) has no seedable package in agent library
- **Analysis Type Router** — `build` → custom
  - catalog match Pipeline Intent Classifier (pipeline_intent_classifier) has no seedable package in agent library
- **SQL Answering Chain** — `reuse` → Quin SQL Agent Chain
  - matched Quin SQL Agent Chain
- **Document Retrieval Chain** — `adapt` → Eryl Semantic RAG Agent Chain
  - matched Eryl Semantic RAG Agent Chain
- **Evidence Reconciliation & Confidence Gate** — `build` → custom
  - catalog match Evidence Checker (evidence_checker) has no seedable package in agent library
- **Answer Quality Evaluation** — `build` → custom
  - catalog match Evidence Checker (evidence_checker) has no seedable package in agent library
- **Final Natural-Language Answer** — `build` → custom
  - catalog match Final Answer Consolidation Agent (final_answer_consolidation_agent) has no seedable package in agent library

## Catalog matches

- **Text-to-SQL Analytics Agent** (`text_to_sql_analytics_agent`) — score 0.95
  - Matched for: Internal employees need a chatbot that can answer analyst-style questions by com
  - Translates a natural-language analytics question into a validated SQL query, runs it against the target database, and returns the result set with a short explanation.
- **Eryl Semantic RAG Agent Chain** (`eryl_semantic_rag_agent_chain`) — score 0.95
  - Matched for: User submits question through chat UI, Intent classifier determines whether the
  - Retrieves and answers from indexed retail policy and unstructured documents (Chocolate_Confectionery_Retail_Policy.docx, emails, guidelines) using Azure AI Search vector + semantic retrieval.
- **Final Answer Consolidation Agent** (`final_answer_consolidation_agent`) — score 0.95
  - Matched for: Provide a single internal chatbot that routes questions to the right data path,
  - Consolidates count and generic row-level analyses into a single natural-language answer based on task_type routing.
- **RAG Document Retriever** (`rag_document_retriever`) — score 0.81
  - Matched for: User submits question through chat UI → Intent classifier determines whether the
  - Retrieves the most relevant passages from an indexed document corpus for a user query, returning ranked chunks with source citations for grounded answering.
- **Answer Summarizer** (`answer_summarizer`) — score 0.58
  - Matched for: Internal employees need a chatbot that can answer analyst-style questions by com
  - Condenses retrieved context, long documents, or transcripts into a concise grounded answer or summary, citing the supporting sources.
- **Final Answer Rewriter** (`final_answer_rewriter`) — score 0.58
  - Matched for: User submits question through chat UI → Intent classifier determines whether the
  - Post-processes combined vision+SQL+semantic draft answers into concise structured user-facing text without adding new facts.
- **Shelf Understanding Agent** (`shelf_understanding_agent`) — score 0.50
  - Matched for: Provide a single internal chatbot that routes questions to the right data path,
  - Answers descriptive, price, promotion, and stock-out questions from cropped row images and full shelf context.
- **Web Research Agent** (`web_research_agent`) — score 0.42
  - Matched for: Provide a single internal chatbot that routes questions to the right data path,
  - Searches the public web for a question, reads the top results, and returns a synthesized answer with linked sources.
- **Intent Classifier & Router** (`intent_classifier_router`) — score 0.42
  - Matched for: User submits question through chat UI, Intent classifier determines whether the
  - Classifies an incoming request into one of a configurable set of intents and routes it to the correct downstream branch or agent.
- **GraphRAG Index & Query Agent** (`graphrag_index_query_agent`) — score 0.35
  - Matched for: Internal employees need a chatbot that can answer analyst-style questions by com
  - Indexes per-project KYC documents into a knowledge graph with entity/community extraction and embeddings; answers analyst questions via local, global, drift, or basic search methods.
- **GraphRAG Index & Query Pipeline** (`graphrag-index-query-pipeline`) — score 0.35
  - Matched for: Internal employees need a chatbot that can answer analyst-style questions by com
  - Converts project documents to text, indexes a per-project knowledge graph with entities, communities, and embeddings, and answers analyst questions. It takes project documents plus a query string and search method as input and returns index artifacts and natural-language answers.
- **Document Ingestion Agent** (`document-ingestion-agent`) — score 0.35
  - Matched for: Internal employees need a chatbot that can answer analyst-style questions by com
  - Corporate KYC document ingestion entry point: accepts uploaded PDF, DOCX, TXT, or XLSX via file path or blob storage, detects file type, extracts and normalizes text (with OCR for scanned PDFs), chunks content, and emits document_id and text_content for downstream entity extraction and policy valida
- **Pipeline Intent Classifier** (`pipeline_intent_classifier`) — score 0.35
  - Matched for: Internal employees need a chatbot that can answer analyst-style questions by com
  - Classifies each user question into vision_only, vision_then_unified, or unified_only and flags multi-shelf comparisons for SQL-only routing.
- **Quin SQL Agent Chain** (`quin_sql_agent_chain`) — score 0.35
  - Matched for: Internal employees need a chatbot that can answer analyst-style questions by com
  - AutoGen multi-agent chain that generates, executes, and critiques SQL Server queries on mars schema tables (Mars_Sales_Data, shelf_visit, retail_planogram_stocks, etc.) and returns structured sales/inventory insights.
- **Semantic Image Search & Validator** (`semantic_image_search_validator`) — score 0.35
  - Matched for: Internal employees need a chatbot that can answer analyst-style questions by com
  - Embeds text queries with Azure AI Vision, retrieves similar shelf images from Azure AI Search, and filters results with GPT vision relevance scoring.
- **Main Entity Inference Agent** (`main_entity_inference_agent`) — score 0.35
  - Matched for: Internal employees need a chatbot that can answer analyst-style questions by com
  - Infers the primary corporate entity described in a project's latest document to center the radial ownership visualization.
- **Entity Extraction Agent** (`entity-extraction-agent`) — score 0.35
  - Matched for: Internal employees need a chatbot that can answer analyst-style questions by com
  - Extracts entities, ownership relationships, and UBO registry records from uploaded corporate KYC documents into structured JSON for SQL persistence.
- **Email & Message Drafter** (`email_message_drafter`) — score 0.35
  - Matched for: Internal employees need a chatbot that can answer analyst-style questions by com
  - Drafts professional outbound emails or chat messages from a brief, context, and tone, ready for human review before sending.
- **Planogram Vision LLM Suite** (`planogram-vision-llm-suite`) — score 0.35
  - Matched for: Internal employees need a chatbot that can answer analyst-style questions by com
  - Azure OpenAI vision functions for shelf-level product extraction, row counting, generic row description, daily KPI JSON, and final natural-language shelf answers after Roboflow cropping.
- **Generation Prompt Author** (`generation-prompt-author-v2-1-0`) — score 0.35
  - Matched for: Internal employees need a chatbot that can answer analyst-style questions by com
  - Azure vision+text agent that writes per-PDP-image-type multimodal prompts (or per-role directives) from reference photos and PDF excerpts before image generation.
- **Risk Reasoning Generator** (`risk_reasoning_generator`) — score 0.35
  - Matched for: Internal employees need a chatbot that can answer analyst-style questions by com
  - Generates explainable AI narratives for the final risk score and each of four risk dimensions (Geography, Ownership, Industry, Sanctions) for UI display and DOCX reports.
- **Generation Prompt Author** (`generation_prompt_author`) — score 0.35
  - Matched for: Internal employees need a chatbot that can answer analyst-style questions by com
  - Azure vision+text agent that writes per-PDP-image-type multimodal prompts (or per-role directives) from reference photos and PDF excerpts before image generation.
- **Missing Information Email Drafter** (`missing_information_email_drafter`) — score 0.35
  - Matched for: Internal employees need a chatbot that can answer analyst-style questions by com
  - Drafts professional client-facing emails requesting missing KYC details with structured bullet lists and Compliance Team sign-off.
- **KYC Risk Report Generator** (`kyc_risk_report_generator`) — score 0.35
  - Matched for: Internal employees need a chatbot that can answer analyst-style questions by com
  - Generates downloadable Word (.docx) KYC risk assessment reports with KPI summary table, section scores, UBO details, override status, and AI reasoning narratives.
- **Policy & Schema Validator** (`policy_schema_validator`) — score 0.35
  - Matched for: Provide a single internal chatbot that routes questions to the right data path,
  - Validates extracted or submitted data against a configurable policy or schema, blocking incomplete or non-compliant payloads and listing the specific gaps.
- **ML Risk Classifier (Rule Stub)** (`ml-risk-classifier-rule-stub`) — score 0.35
  - Matched for: Provide a single internal chatbot that routes questions to the right data path,
  - Classifies a preliminary Low, Medium, or High risk tier from engineered KYC risk features before weighted scoring. It takes geographic, industry, ownership, PEP, sanctions, and circular ownership features as input and returns a risk tier with confidence.
- **Executive Action Card Writer** (`executive_action_card_writer`) — score 0.35
  - Matched for: Provide a single internal chatbot that routes questions to the right data path,
  - Generates short action-oriented title and subtitle text for field executive promo, compliance, and recommended action cards.
- **ML Risk Classifier Stub** (`ml_risk_classifier_stub`) — score 0.35
  - Matched for: Provide a single internal chatbot that routes questions to the right data path,
  - Rule-based classifier that assigns Low/Medium/High risk tier from engineered geographic, industry, ownership, PEP, and sanctions features.
- **Azure AI Search Catalog Vector Retrieval** (`azure_ai_search_catalog_vector_retrieval`) — score 0.35
  - Matched for: User submits question through chat UI, Intent classifier determines whether the
  - Maintains and queries the vto-accessories HNSW vector index for cosine-similarity ranking of catalog items from text or image-derived embeddings.
- **Planogram Image Semantic Search** (`planogram_image_semantic_search`) — score 0.35
  - Matched for: User submits question through chat UI, Intent classifier determines whether the
  - Embeds shelf images with Azure AI Vision, vector-searches Azure AI Search by supermarket, and validates matches with GPT before returning blob hits.
- **Executive Brief Generator** (`executive_brief_generator_agent_chain`) — score 0.17
  - Matched for: full_catalog:Internal employees need a chatbot that can answer analyst-st
  - Turns an uploaded PDF into a one-page structured executive brief: PyMuPDF text extraction (no LLM) plus a Brief_Writer agent that returns title, key_points, executive_summary, and word_count grounded only in the source text.
- **Planogram Vision Agent Chain** (`planogram_vision_agent_chain`) — score 0.17
  - Matched for: full_catalog:Internal employees need a chatbot that can answer analyst-st
  - AutoGen multi-agent vision chain that routes shelf queries to counting or generic understanding over row-crop images, then consolidates into a final natural-language shelf answer with reasoning.
- **Evidence Checker** (`evidence_checker`) — score 0.16
  - Matched for: full_catalog:Internal employees need a chatbot that can answer analyst-st
  - Reconciles structured (SQL) and semantic (document) evidence, flags material conflicts, scores groundedness/completeness/faithfulness, and gates whether grounded answer synthesis may proceed.
- **Intake Gateway** (`intake_gateway`) — score 0.14
  - Matched for: full_catalog:Internal employees need a chatbot that can answer analyst-st
  - Receives the user question, runs a deterministic Azure Content Safety-style pre-check (toxicity, PII, prompt injection), then an LLM Responsible AI agent for governance and business-rule blocking before routing or retrieval.
- **Azure AI Vision Catalog Embedder** (`azure_ai_vision_catalog_embedder`) — score 0.12
  - Matched for: full_catalog:Internal employees need a chatbot that can answer analyst-st
  - Generates 1024-dimensional multimodal embeddings for catalog accessory images and natural-language search queries to power semantic garment discovery.
- **PDF In-Place Instruction Updater** (`document_generation`) — score 0.12
  - Matched for: full_catalog:Internal employees need a chatbot that can answer analyst-st
  - Edits an existing PDF from natural-language change instructions via exact old→new substring patches applied in-place with overlay masking (PyMuPDF). Preserves images, layout, and vectors — no rebuild, no paraphrasing, no from-scratch document authoring.
- **Intent Router** (`intent_router`) — score 0.12
  - Matched for: full_catalog:Internal employees need a chatbot that can answer analyst-st
  - Classifies a user question into configurable analysis_type categories (SQL-based, Semantic-based, Both-dependent, Both-independent) for graph-level conditional dispatch. Emits analysis_type; does not execute Quin/Eryl handoffs.
- **Competitive Shelf Intelligence Scorer** (`competitive_shelf_intelligence_scorer`) — score 0.11
  - Matched for: full_catalog:Internal employees need a chatbot that can answer analyst-st
  - Computes Mars visibility, competitor pressure, promo and shelf position scores from vision-extracted brand facings using weighted shelf-level rules.
- **GPT Image Relevance Validator** (`gpt_image_relevance_validator`) — score 0.09
  - Matched for: full_catalog:Internal employees need a chatbot that can answer analyst-st
  - Strict vision-based filter that approves or rejects blob images against a user's semantic search query.
- **PDP Compliance Checker** (`pdp_compliance_checker`) — score 0.08
  - Matched for: full_catalog:Internal employees need a chatbot that can answer analyst-st
  - Vision LLM scores a generated PDP image against guardrails-only excerpts and returns pass/fail rules, warnings, suggestions, and compliance_score 0-100.
- **Risk Scoring Agent** (`risk_scoring_agent`) — score 0.08
  - Matched for: full_catalog:Internal employees need a chatbot that can answer analyst-st
  - Aggregates geography (30), ownership (30), regulatory/sanctions (20), and industry (20) scores into a final 0–100 risk score with hard override rules for FATF blacklist, sanctions, circular ownership, and PEP exposure.
- **Gemini Image Compositor** (`gemini_image_compositor`) — score 0.08
  - Matched for: full_catalog:Internal employees need a chatbot that can answer analyst-st
  - Synthesizes the final virtual try-on image from person photo, accessory references, and the GPT-generated editing prompt using Gemini image output modality with aspect ratio matching and up to three retries.
- **PDP Image Generator (Gemini)** (`pdp_image_generator_gemini`) — score 0.07
  - Matched for: full_catalog:Internal employees need a chatbot that can answer analyst-st
  - Generates Amazon-style PDP PNGs from reference images plus authored prompts, one variant per parallel task.
- **GPT-4o Fashion Vision Analyzer** (`gpt4o_fashion_vision_analyzer`) — score 0.06
  - Matched for: full_catalog:Internal employees need a chatbot that can answer analyst-st
  - Analyzes person and garment reference images with a fashion/computational-photography system prompt and outputs a single precise image-editing instruction for virtual try-on, including layering, lighting, and full-frame preservation.
- **PDP Image Generator (Azure GPT Image)** (`pdp_image_generator_azure_gpt_image`) — score 0.06
  - Matched for: full_catalog:Internal employees need a chatbot that can answer analyst-st
  - Azure images/edits endpoint generates PDP variants from first reference image and per-slot prompt.
- **Amazon PDP Video Prompt Author** (`amazon_pdp_video_prompt_author`) — score 0.05
  - Matched for: full_catalog:Internal employees need a chatbot that can answer analyst-st
  - Produces a full Amazon PDP video ad script (reference block, compliance checklist, scenes, generation prompts) from product spec, guardrails, optional user script, and reference image.
- **UBO Analysis Engine** (`ubo_analysis_engine`) — score 0.05
  - Matched for: full_catalog:Internal employees need a chatbot that can answer analyst-st
  - Computes UBO-specific risk score from ownership concentration, identification transparency, structural complexity, and PEP/sanctions/geo flags.
- **Roboflow Product Detector** (`roboflow_product_detector`) — score 0.04
  - Matched for: full_catalog:Internal employees need a chatbot that can answer analyst-st
  - Runs YOLO product detection on each shelf row crop and writes annotated images with per-class counts.
- **Sora Image-to-Video Generator** (`sora_image_to_video_generator`) — score 0.03
  - Matched for: full_catalog:Internal employees need a chatbot that can answer analyst-st
  - Submits image-to-video jobs to Azure Sora, polls until complete, returns MP4 for PDP video ads.
- **Roboflow Shelf Row Detector** (`roboflow_shelf_row_detector_merchandising`) — score 0.02
  - Matched for: full_catalog:Internal employees need a chatbot that can answer analyst-st
  - Detects shelf rows as polygons, produces masked row crops and a polygon-overlay summary image.
- **Roboflow Shelf Row Detector** (`roboflow_shelf_row_detector_mars`) — score 0.02
  - Matched for: full_catalog:Internal employees need a chatbot that can answer analyst-st
  - Segments shelf rows and detects product bounding boxes; writes cropped and annotated artifacts to Azure Blob for downstream vision LLMs.
- **Mars Sales Order Simulator** (`mars_sales_order_simulator`) — score 0.02
  - Matched for: full_catalog:Internal employees need a chatbot that can answer analyst-st
  - CatBoost/sklearn regression predicts demand and realized sales under promotion, price, and stock constraints for Snickers/Mars/Twix SKUs.

## Open questions

- Should the document corpus already be indexed, or is an explicit indexing pipeline needed outside the runtime graph?
- What are the exact source-priority rules when SQL and document evidence conflict?
- Should low-confidence responses include a generic disclaimer only, or a more specific warning category such as missing data versus conflicting sources?
- Which structured data platform will back the SQL branch, and does it require dialect-specific query constraints?

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
*Generated by Agentic LaunchPad on 2026-08-13 10:16 UTC*