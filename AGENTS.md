# JARVIS 2.0 Agent Architecture & Multi-Agent Orchestration

JARVIS 2.0 adopts a true multi-agent system (MAS) architecture. Rather than relying on a single monolithic model call, the central **JARVIS Core Orchestrator** decomposes complex goals into specialized agent subtasks executed sequentially or concurrently across a Directed Acyclic Graph (DAG).

---

## 1. Agent Ecosystem Matrix

| Agent Name | Primary Responsibility | Associated Tools | Model Capability Tier |
| :--- | :--- | :--- | :--- |
| **`Orchestrator`** | Intent classification, task decomposition, context retrieval, verification loop. | ModelRouter, TaskGraph, EventBus | Fast / High Reasoning |
| **`Study Agent`** | Structured notes, definitions, formula sheets, MCQ quizzes, flashcards. | NotesGenerator, ExamPrep, RAG | Long-Context / High Reasoning |
| **`Research Agent`** | Multi-query web search, scraping, source verification, citation grounding. | WebSearch, WebReader, BeautifulSoup | High Reasoning / Fast |
| **`Document Agent`** | Publication generation for PDF, DOCX, PPTX, XLSX, CSV, Markdown. | ReportLab, python-docx, python-pptx, openpyxl | Structured Generation |
| **`Coding Agent`** | Code synthesis, error debugging, refactoring, test generation, sandbox testing. | PythonSandbox, SubprocessRuntime, AST | Coding / Sandbox |
| **`Math Agent`** | Step-by-step calculus, matrix determinants, statistics, algebra. | MathEngine, AST Evaluator | Symbolic Computation |
| **`Multi-Doc Agent`** | Cross-document reasoning, comparative synthesis, contradiction analysis. | MultiDocumentReasoner, RAG | Long-Context Reasoning |
| **`Computer Agent`** | App launching, workspace file management, system diagnostics. | LocalActions, FileTools, SystemInfo | System Bridge (Assisted) |
| **`Verification Agent`** | Output integrity checks, file existence, size checks, error correction loops. | OutputVerifier, FileCheckers | Deterministic Verifier |

---

## 2. Multi-Agent Task Dependency Graph (DAG)

Complex instructions trigger automated dependency graphs where independent branches execute concurrently:

```text
User: "Research AI hardware advancements, compare 3 uploaded PDFs, compute efficiency trends, and generate a 15-slide presentation."

                                 +-------------------------+
                                 |  Orchestrator (Planner) |
                                 +-------------------------+
                                              |
                     +------------------------+------------------------+
                     |                                                 |
                     v                                                 v
        +-------------------------+                       +-------------------------+
        |     Research Agent      |                       |    Multi-Doc Agent      |
        | (Live DuckDuckGo Search)|                       |  (Compare Uploaded PDFs)|
        +-------------------------+                       +-------------------------+
                     |                                                 |
                     +------------------------+------------------------+
                                              |
                                              v
                                 +-------------------------+
                                 |       Math Agent        |
                                 | (Calculate Trends/Stats)|
                                 +-------------------------+
                                              |
                                              v
                                 +-------------------------+
                                 |    Presentation Agent   |
                                 |   (Generate 16:9 Deck)  |
                                 +-------------------------+
                                              |
                                              v
                                 +-------------------------+
                                 |    Verification Agent   |
                                 | (Validate PPTX Content) |
                                 +-------------------------+
```

---

## 3. Self-Correction & Verification Loop

Every agent execution is governed by the verification loop:
1. **Execution**: The specialized agent executes tools and synthesizes the candidate output.
2. **Verification Check**: The `VerificationAgent` checks output validity (non-empty bytes, valid file structure, syntax integrity).
3. **Self-Correction**: If a stage fails (e.g., corrupted file or missing section), the Orchestrator repairs the parameter payload and executes a targeted retry before delivering results.
