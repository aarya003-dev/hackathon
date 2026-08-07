# Development Plan: Application Development Code Review and Suggestion Agent

## 1. Project Overview
This project implements an AI-powered multi-agent system designed to streamline application development code reviews. The system will integrate with Git repositories and CI/CD pipelines to automate code analysis, issue detection (style, bugs, security), and suggestion generation. The solution features a web UI for inline comments, summary reports, and a dashboard for monitoring agent workflows.

## 2. Environment Setup & Version Control
*   **Version Control:** Initialize a Git repository for all source code. Ensure a comprehensive `.gitignore` is in place.
*   **Virtual Environment:** Use a Python virtual environment (`venv`) to isolate backend dependencies.
*   **Environment Variables:** Use a `.env` file to manage all sensitive credentials, API keys, and configuration variables (ensure this file is strictly excluded from version control).

## 3. AI Model Selection & API Strategy
All AI models are routed exclusively through the centralized API gateway (`https://genailab.tcs.in`) to maintain enterprise compliance and security.

| Agent Role / Component | Selected Model | Primary Function | Justification |
| :--- | :--- | :--- | :--- |
| **Triage & Orchestrator** | `azure/genailab-maas-gpt-4o-mini` | Diff classification and routing | High-speed JSON parsing and low latency for initial intent classification. |
| **Core Code Review** | `genailab-maas-gpt-5.3-codex` | Syntactic bug detection and inline patches | State-of-the-art coding capabilities for precise line-level code generation. |
| **Security & Vulnerability** | `azure_ai/genailab-maas-DeepSeek-R1` | Deep static analysis and exploit logic | Chain-of-Thought (CoT) reasoning ideal for identifying hidden race conditions and multi-file security vectors. |
| **PR Summarizer** | `gemini-2.5-pro` | High-level PR changelogs | Large context window capacity to process multi-file diff summaries cleanly. |
| **Vector RAG Pipeline** | `azure/genailab-maas-text-embedding-3-large` | Embedding repository history and guidelines | 3072-dimensional embeddings providing high retrieval accuracy for semantic search. |

## 4. Multi-Agent Architecture & Workflow
*   **Event Trigger:** Webhooks from Git repositories/CI-CD pipelines notify the system of new Pull Requests (PRs) or code commits.
*   **Data Ingestion:** Fetch PR metadata, git diffs, historical PR comments, and build/test results.
*   **Orchestration (Triage Agent):** The Orchestrator receives the diff, classifies the changes, and routes specific files or functions to the appropriate specialized agents (Core Review or Security).
*   **Analysis Execution:**
    *   **Core Code Review Agent:** Analyzes syntax, style, and functional logic. Generates inline patch suggestions.
    *   **Security Agent:** Performs deep static analysis for vulnerabilities. Flags high-risk issues.
*   **Synthesis (Summarizer Agent):** Aggregates findings from specialized agents and generates a comprehensive PR summary and changelog.
*   **Human-in-the-Loop (HITL):** If the Security agent flags a severe vulnerability or uncertainty is high, execution pauses for human approval/escalation.
*   **Output Delivery:** Publish inline comments and the overall summary back to the repository platform.

## 5. Real-Time Visual Dashboard & Tracker
A minimalistic, production-ready web UI built with React, Vite, and Tailwind CSS.

*   **Live DAG Execution View (Optional/Ideal):** Use React Flow to render the multi-agent Directed Acyclic Graph (DAG) visualizing agent transitions in real time via Server-Sent Events (SSE). Nodes dynamically shift colors based on status (Idle, Running, Success, Failed).
*   **Interactive HITL Checkpoint:** Pauses execution and highlights the Security Agent node when high-risk vulnerabilities are flagged, requiring explicit team lead approval to proceed.
*   **Code Diff Viewer:** Renders GitHub git diffs side-by-side, overlaying the generated AI suggestions as actionable inline comments.
*   **Summary & Metrics:** Displays the high-level PR summary and key performance metrics (e.g., automated defect detection rate, reduction in manual review time).

## 6. Data Architecture & RAG Pipeline
*   **Storage:** Implement suitable databases (e.g., PostgreSQL for relational metadata, a vector store like Pinecone/Chroma for embeddings).
*   **RAG Implementation:** Process and embed historical code review comments and proprietary coding guidelines to provide context-aware suggestions during the review.
*   **Data Privacy:** Ensure strict handling of proprietary code. Utilize synthetic or anonymized datasets for any necessary model fine-tuning or testing.

## 7. Quality Assurance & Evaluation
*   **Testing Strategy:** Validate the multi-agent system against varied test data, edge cases, and known failure scenarios (e.g., synthetic PRs with known bugs).
*   **Metrics:** Monitor and optimize for latency, cost, and hallucination control.
*   **Demo Readiness:** Prepare a realistic demo flow highlighting the speed, scale, and quality improvements over manual processes.