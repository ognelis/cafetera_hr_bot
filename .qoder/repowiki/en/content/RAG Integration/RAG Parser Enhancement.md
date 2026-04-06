# RAG Parser Enhancement

<cite>
**Referenced Files in This Document**
- [parser.py](file://app/rag/parser.py)
- [indexer.py](file://app/rag/indexer.py)
- [retriever.py](file://app/rag/retriever.py)
- [chain.py](file://app/rag/chain.py)
- [prompts.py](file://app/rag/prompts.py)
- [ingest.py](file://scripts/ingest.py)
- [document_service.py](file://app/domain/document_service.py)
- [document_repo.py](file://app/storage/document_repo.py)
- [config.py](file://app/config.py)
- [documents.py](file://app/api/documents.py)
- [qa_service.py](file://app/domain/qa_service.py)
- [main.py](file://app/main.py)
- [test_rag_block6.py](file://tests/test_rag_block6.py)
- [test_indexer.py](file://tests/test_indexer.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)

## Introduction
This document describes the RAG (Retrieval-Augmented Generation) Parser Enhancement for the Cafetera HR Bot. The enhancement focuses on improving the document ingestion pipeline for .docx files, including structured section extraction, intelligent chunking, metadata enrichment, and robust integration with Qdrant vector storage. The system supports multiple LLM providers and provides both batch ingestion and live admin upload flows.

## Project Structure
The RAG system is organized into cohesive modules:
- app/rag: Core RAG components (parser, indexer, retriever, chain, prompts)
- scripts: Batch ingestion utilities
- app/domain: Business services orchestrating document lifecycle
- app/storage: Metadata persistence and S3 integration
- app/api: Admin endpoints for document management
- app/config: Environment-driven configuration
- tests: Comprehensive unit and integration tests

```mermaid
graph TB
subgraph "RAG Core"
P["parser.py<br/>Docx parsing & chunking"]
I["indexer.py<br/>Chunk prep & Qdrant ops"]
R["retriever.py<br/>Embeddings & retriever"]
C["chain.py<br/>RAG chain builder"]
PR["prompts.py<br/>System prompts"]
end
subgraph "Application Layer"
DS["document_service.py<br/>Document lifecycle"]
DR["document_repo.py<br/>SQLite metadata"]
API["documents.py<br/>Admin API"]
QA["qa_service.py<br/>QA handler"]
CFG["config.py<br/>Settings"]
MAIN["main.py<br/>App lifecycle"]
end
subgraph "External Systems"
QD["Qdrant"]
S3["S3 Storage"]
LLM["LLM Provider"]
end
P --> I
I --> QD
R --> QD
C --> LLM
API --> DS
DS --> DR
DS --> QD
DS --> S3
QA --> R
QA --> C
MAIN --> DS
MAIN --> QA
CFG --> R
CFG --> C
```

**Diagram sources**
- [parser.py:1-83](file://app/rag/parser.py#L1-L83)
- [indexer.py:1-152](file://app/rag/indexer.py#L1-L152)
- [retriever.py:1-103](file://app/rag/retriever.py#L1-L103)
- [chain.py:1-95](file://app/rag/chain.py#L1-L95)
- [prompts.py:1-19](file://app/rag/prompts.py#L1-L19)
- [document_service.py:1-280](file://app/domain/document_service.py#L1-L280)
- [document_repo.py:1-202](file://app/storage/document_repo.py#L1-L202)
- [documents.py:1-531](file://app/api/documents.py#L1-L531)
- [qa_service.py:1-120](file://app/domain/qa_service.py#L1-L120)
- [config.py:1-33](file://app/config.py#L1-L33)
- [main.py:1-119](file://app/main.py#L1-L119)

**Section sources**
- [parser.py:1-83](file://app/rag/parser.py#L1-L83)
- [indexer.py:1-152](file://app/rag/indexer.py#L1-L152)
- [retriever.py:1-103](file://app/rag/retriever.py#L1-L103)
- [chain.py:1-95](file://app/rag/chain.py#L1-L95)
- [prompts.py:1-19](file://app/rag/prompts.py#L1-L19)
- [ingest.py:1-181](file://scripts/ingest.py#L1-L181)
- [document_service.py:1-280](file://app/domain/document_service.py#L1-L280)
- [document_repo.py:1-202](file://app/storage/document_repo.py#L1-L202)
- [config.py:1-33](file://app/config.py#L1-L33)
- [documents.py:1-531](file://app/api/documents.py#L1-L531)
- [qa_service.py:1-120](file://app/domain/qa_service.py#L1-L120)
- [main.py:1-119](file://app/main.py#L1-L119)

## Core Components
This section outlines the primary components of the RAG Parser Enhancement and their responsibilities.

- Docx Parser and Chunker
  - Extracts structured sections from .docx files using heading styles
  - Splits content into overlapping chunks with configurable size and overlap
  - Preserves metadata (source filename, nearest section heading)
  - Returns LangChain Document objects ready for embedding

- Indexer
  - Enriches chunk metadata with document-level identifiers and unique chunk IDs
  - Adds chunks to Qdrant vector collection
  - Supports deletion, toggling search availability, and counting chunks per document

- Retriever
  - Builds embeddings based on provider configuration (OpenAI-compatible, Llama.cpp, Ollama)
  - Wraps Qdrant collection as a LangChain vector store
  - Constructs a dense retriever with filters for searchable chunks

- RAG Chain Builder
  - Composes retriever, formatted context, system prompt, LLM, and output parser
  - Supports multiple LLM providers with provider-specific configuration
  - Provides a unified interface for QA queries

- QA Service
  - Initializes the RAG chain at application startup
  - Handles runtime errors gracefully and truncates long answers to platform limits
  - Offers a simple ask() API for transport handlers

**Section sources**
- [parser.py:23-82](file://app/rag/parser.py#L23-L82)
- [indexer.py:23-151](file://app/rag/indexer.py#L23-L151)
- [retriever.py:22-102](file://app/rag/retriever.py#L22-L102)
- [chain.py:25-94](file://app/rag/chain.py#L25-L94)
- [prompts.py:5-18](file://app/rag/prompts.py#L5-L18)
- [qa_service.py:51-105](file://app/domain/qa_service.py#L51-L105)

## Architecture Overview
The RAG Parser Enhancement integrates ingestion, storage, retrieval, and generation into a cohesive pipeline. The flow begins with document ingestion (batch or admin upload), continues through chunk preparation and vector indexing, and concludes with retrieval augmented generation for answering questions.

```mermaid
sequenceDiagram
participant Admin as "Admin UI/API"
participant API as "Documents API"
participant Service as "DocumentService"
participant S3 as "S3 Storage"
participant Parser as "Docx Parser"
participant Indexer as "Indexer"
participant Qdrant as "Qdrant"
Admin->>API : Upload .docx
API->>S3 : Store file
API->>Service : Create metadata record
API->>Service : Schedule background indexing
Service->>S3 : Download file
Service->>Parser : Parse and chunk
Parser-->>Service : List of Documents
Service->>Indexer : Enrich metadata + prepare chunks
Indexer->>Qdrant : Add vectors
Service-->>API : Update status to completed
API-->>Admin : Show indexed document
```

**Diagram sources**
- [documents.py:265-351](file://app/api/documents.py#L265-L351)
- [document_service.py:56-132](file://app/domain/document_service.py#L56-L132)
- [document_repo.py:69-99](file://app/storage/document_repo.py#L69-L99)
- [parser.py:54-82](file://app/rag/parser.py#L54-L82)
- [indexer.py:23-71](file://app/rag/indexer.py#L23-L71)

**Section sources**
- [documents.py:109-128](file://app/api/documents.py#L109-L128)
- [document_service.py:83-132](file://app/domain/document_service.py#L83-L132)
- [ingest.py:49-155](file://scripts/ingest.py#L49-L155)

## Detailed Component Analysis

### Docx Parser and Chunking
The parser extracts structured sections from .docx files and produces chunked LangChain documents suitable for embedding. It identifies headings by style name and groups subsequent paragraphs under the most recent heading. Chunks are generated using a recursive character splitter with multiple separator strategies and overlap to preserve context across boundaries.

```mermaid
flowchart TD
Start(["load_docx(path)"]) --> Extract["_extract_sections(path)"]
Extract --> ForEach["For each (heading, body)"]
ForEach --> Split["RecursiveCharacterTextSplitter.split_text(body)"]
Split --> Append["Create LCDocument with metadata"]
Append --> Return["Return list of Documents"]
subgraph "Helper Function"
ExtractSections["_extract_sections(path)"]
ExtractSections --> Iterate["Iterate paragraphs"]
Iterate --> IsHeading{"Style starts with 'Heading'?"}
IsHeading --> |Yes| Flush["Flush previous paragraphs as section"]
IsHeading --> |No| Accumulate["Accumulate paragraph"]
Flush --> SetHeading["Set current heading"]
SetHeading --> Accumulate
Accumulate --> Iterate
end
```

**Diagram sources**
- [parser.py:23-51](file://app/rag/parser.py#L23-L51)
- [parser.py:54-82](file://app/rag/parser.py#L54-L82)

**Section sources**
- [parser.py:15-20](file://app/rag/parser.py#L15-L20)
- [parser.py:23-51](file://app/rag/parser.py#L23-L51)
- [parser.py:54-82](file://app/rag/parser.py#L54-L82)

### Indexer Operations
The indexer enriches raw chunks with document-level metadata and unique identifiers, then adds them to Qdrant. It supports bulk indexing, deletion by document ID, toggling search availability, and counting chunks per document. These operations maintain consistency between SQLite metadata and Qdrant payloads.

```mermaid
classDiagram
class Indexer {
+prepare_chunks(chunks, document_id, filename, s3_key, is_search_enabled) Document[]
+index_chunks(client, embeddings, collection_name, chunks) int
+delete_document_chunks(client, collection_name, document_id) void
+set_search_enabled(client, collection_name, document_id, enabled) void
+count_document_chunks(client, collection_name, document_id) int
}
```

**Diagram sources**
- [indexer.py:23-151](file://app/rag/indexer.py#L23-L151)

**Section sources**
- [indexer.py:23-46](file://app/rag/indexer.py#L23-L46)
- [indexer.py:49-71](file://app/rag/indexer.py#L49-L71)
- [indexer.py:74-97](file://app/rag/indexer.py#L74-L97)
- [indexer.py:100-131](file://app/rag/indexer.py#L100-L131)
- [indexer.py:134-151](file://app/rag/indexer.py#L134-L151)

### Retriever and Embeddings
The retriever builds embeddings based on provider configuration and wraps Qdrant as a vector store. It constructs a retriever that filters out chunks where search is disabled, ensuring only relevant content participates in retrieval.

```mermaid
sequenceDiagram
participant Settings as "Settings"
participant Retriever as "build_retriever"
participant Embeddings as "build_embeddings"
participant Qdrant as "QdrantVectorStore"
Settings->>Retriever : llm_provider, embedding_model, urls
Retriever->>Embeddings : Select provider and create embeddings
Embeddings-->>Retriever : Embeddings instance
Retriever->>Qdrant : Wrap collection
Qdrant-->>Retriever : VectorStore
Retriever-->>Retriever : Filtered retriever (k, filter)
```

**Diagram sources**
- [retriever.py:22-102](file://app/rag/retriever.py#L22-L102)
- [config.py:10-22](file://app/config.py#L10-L22)

**Section sources**
- [retriever.py:22-62](file://app/rag/retriever.py#L22-L62)
- [retriever.py:65-102](file://app/rag/retriever.py#L65-L102)
- [config.py:10-22](file://app/config.py#L10-L22)

### RAG Chain Composition
The RAG chain composes a retriever, formatted context, system prompt, LLM, and output parser. It supports multiple providers and ensures consistent formatting and output handling.

```mermaid
classDiagram
class RAGChain {
+build_llm(settings) BaseChatModel
+build_rag_chain(retriever, llm) Runnable
-_format_docs(docs) str
}
```

**Diagram sources**
- [chain.py:30-94](file://app/rag/chain.py#L30-L94)
- [prompts.py:5-18](file://app/rag/prompts.py#L5-L18)

**Section sources**
- [chain.py:25-27](file://app/rag/chain.py#L25-L27)
- [chain.py:30-73](file://app/rag/chain.py#L30-L73)
- [chain.py:76-94](file://app/rag/chain.py#L76-L94)
- [prompts.py:5-18](file://app/rag/prompts.py#L5-L18)

### QA Service Integration
The QA service initializes the RAG chain at application startup, handles runtime failures gracefully, and truncates long answers to platform limits. It exposes a simple ask() API for downstream handlers.

```mermaid
sequenceDiagram
participant App as "FastAPI App"
participant QA as "qa_service.init_qa"
participant Chain as "build_rag_chain"
participant Retriever as "build_retriever"
participant LLM as "build_llm"
App->>QA : init_qa(settings)
QA->>Retriever : Build retriever
QA->>LLM : Build LLM
QA->>Chain : Compose chain
Chain-->>QA : Runnable
QA-->>App : Ready
App->>QA : ask(question)
QA->>Chain : ainvoke(question)
Chain-->>QA : answer
QA-->>App : Truncated answer or fallback
```

**Diagram sources**
- [qa_service.py:51-105](file://app/domain/qa_service.py#L51-L105)
- [main.py:23-82](file://app/main.py#L23-L82)
- [chain.py:76-94](file://app/rag/chain.py#L76-L94)
- [retriever.py:78-102](file://app/rag/retriever.py#L78-L102)

**Section sources**
- [qa_service.py:51-105](file://app/domain/qa_service.py#L51-L105)
- [main.py:23-82](file://app/main.py#L23-L82)

### Document Lifecycle Service
The DocumentService orchestrates the full document lifecycle: creating metadata, indexing chunks, toggling search participation, reindexing, and deletion. It maintains consistency between SQLite metadata and Qdrant payloads.

```mermaid
flowchart TD
Create["create_document(...)"] --> Register["Register in SQLite"]
Index["index_document(document_id, chunks)"] --> Prepare["prepare_chunks(...)"]
Prepare --> Enrich["Enrich metadata + chunk_id"]
Enrich --> Add["index_chunks(client, embeddings, collection, chunks)"]
Add --> Update["Update status to completed"]
Toggle["toggle_search(document_id, enabled)"] --> QdrantUpdate["set_search_enabled(client, ...)"]
QdrantUpdate --> SQLiteUpdate["Update SQLite"]
Reindex["reindex_document(document_id, chunks)"] --> DeleteOld["delete_document_chunks(client, ...)"]
DeleteOld --> Index
Delete["delete_document(document_id, file_deleter)"] --> Cleanup["Delete chunks + file + metadata"]
```

**Diagram sources**
- [document_service.py:56-132](file://app/domain/document_service.py#L56-L132)
- [document_service.py:146-177](file://app/domain/document_service.py#L146-L177)
- [document_service.py:181-231](file://app/domain/document_service.py#L181-L231)
- [document_service.py:235-279](file://app/domain/document_service.py#L235-L279)

**Section sources**
- [document_service.py:35-53](file://app/domain/document_service.py#L35-L53)
- [document_service.py:83-132](file://app/domain/document_service.py#L83-L132)
- [document_service.py:146-177](file://app/domain/document_service.py#L146-L177)
- [document_service.py:181-231](file://app/domain/document_service.py#L181-L231)
- [document_service.py:235-279](file://app/domain/document_service.py#L235-L279)

### Admin Upload Flow
The admin upload flow validates file types and sizes, uploads to S3, creates metadata records, and schedules background indexing. It supports both JSON API responses and HTMX partial updates.

```mermaid
sequenceDiagram
participant Client as "Admin Client"
participant API as "documents.py"
participant S3 as "S3Storage"
participant Service as "DocumentService"
participant BG as "Background Task"
Client->>API : POST /api/documents/upload
API->>API : Validate file type/size
API->>S3 : Upload file
API->>Service : create_document(...)
API->>BG : Schedule _index_in_background
BG->>S3 : Download file
BG->>Service : index_document(document_id, chunks)
Service-->>BG : Status updated
BG-->>API : Background indexing complete
API-->>Client : JSON or HTMX response
```

**Diagram sources**
- [documents.py:265-351](file://app/api/documents.py#L265-L351)
- [documents.py:109-128](file://app/api/documents.py#L109-L128)

**Section sources**
- [documents.py:61-86](file://app/api/documents.py#L61-L86)
- [documents.py:265-351](file://app/api/documents.py#L265-L351)
- [documents.py:109-128](file://app/api/documents.py#L109-L128)

## Dependency Analysis
The RAG Parser Enhancement exhibits clear separation of concerns with minimal coupling between modules. The following diagram highlights key dependencies:

```mermaid
graph TB
CFG["config.py"] --> RET["retriever.py"]
CFG --> CHAIN["chain.py"]
PARSER["parser.py"] --> INDEXER["indexer.py"]
INDEXER --> QDRANT["Qdrant"]
INDEXER --> REPO["document_repo.py"]
SERVICE["document_service.py"] --> INDEXER
SERVICE --> REPO
API["documents.py"] --> SERVICE
API --> PARSER
QA["qa_service.py"] --> RET
QA --> CHAIN
MAIN["main.py"] --> SERVICE
MAIN --> QA
```

**Diagram sources**
- [config.py:10-22](file://app/config.py#L10-L22)
- [retriever.py:22-62](file://app/rag/retriever.py#L22-L62)
- [chain.py:30-73](file://app/rag/chain.py#L30-L73)
- [parser.py:54-82](file://app/rag/parser.py#L54-L82)
- [indexer.py:23-46](file://app/rag/indexer.py#L23-L46)
- [document_repo.py:69-99](file://app/storage/document_repo.py#L69-L99)
- [document_service.py:17-22](file://app/domain/document_service.py#L17-L22)
- [documents.py:53-55](file://app/api/documents.py#L53-L55)
- [qa_service.py:63-77](file://app/domain/qa_service.py#L63-L77)
- [main.py:58-68](file://app/main.py#L58-L68)

**Section sources**
- [config.py:10-22](file://app/config.py#L10-L22)
- [retriever.py:22-62](file://app/rag/retriever.py#L22-L62)
- [chain.py:30-73](file://app/rag/chain.py#L30-L73)
- [parser.py:54-82](file://app/rag/parser.py#L54-L82)
- [indexer.py:23-46](file://app/rag/indexer.py#L23-L46)
- [document_repo.py:69-99](file://app/storage/document_repo.py#L69-L99)
- [document_service.py:17-22](file://app/domain/document_service.py#L17-L22)
- [documents.py:53-55](file://app/api/documents.py#L53-L55)
- [qa_service.py:63-77](file://app/domain/qa_service.py#L63-L77)
- [main.py:58-68](file://app/main.py#L58-L68)

## Performance Considerations
- Chunking Strategy
  - The parser uses overlapping chunks to preserve context across boundaries, balancing recall and storage costs. Adjust chunk size and overlap based on document complexity and retrieval accuracy needs.
- Provider Selection
  - Embedding and LLM providers impact latency and quality. Choose providers aligned with deployment constraints and enable caching where supported.
- Batch vs. Streaming
  - Batch ingestion (scripts/ingest.py) is optimized for throughput; admin uploads leverage background tasks to avoid blocking requests.
- Vector Store Efficiency
  - Qdrant filtering excludes non-searchable chunks efficiently. Maintain collection indices and consider sharding for large-scale deployments.
- Memory and Concurrency
  - Background tasks handle file downloads and indexing; ensure adequate concurrency limits and resource allocation for sustained ingestion rates.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and resolutions:
- Missing Provider Modules
  - The system raises import errors when required extras are not installed. Install the appropriate extras for OpenAI-compatible or Ollama providers as indicated by error messages.
- Qdrant Connectivity
  - Verify Qdrant URL, API key, and collection name in settings. Ensure the collection exists or allow the ingestion process to recreate it.
- Document Status Failures
  - Indexing failures update metadata to failed state with error details. Inspect logs and retry after resolving underlying issues.
- Large Responses
  - QA responses are truncated to platform limits. If answers are frequently truncated, consider adjusting chunk size or prompt to improve conciseness.
- Background Task Errors
  - Background indexing and reindexing log exceptions but do not block the API. Monitor logs for persistent failures and ensure temporary file cleanup occurs.

**Section sources**
- [retriever.py:28-31](file://app/rag/retriever.py#L28-L31)
- [retriever.py:56-58](file://app/rag/retriever.py#L56-L58)
- [chain.py:36-39](file://app/rag/chain.py#L36-L39)
- [chain.py:66-68](file://app/rag/chain.py#L66-L68)
- [ingest.py:144-151](file://scripts/ingest.py#L144-L151)
- [qa_service.py:98-100](file://app/domain/qa_service.py#L98-L100)

## Conclusion
The RAG Parser Enhancement delivers a robust, extensible pipeline for processing HR documents into a searchable knowledge base. By structuring content around headings, intelligently chunking text, enriching metadata, and integrating seamlessly with Qdrant and multiple LLM providers, the system supports both automated batch ingestion and interactive admin workflows. The modular design, comprehensive tests, and clear separation of concerns facilitate maintenance, scaling, and future enhancements.