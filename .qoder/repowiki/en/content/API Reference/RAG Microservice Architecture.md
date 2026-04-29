# RAG Microservice Architecture

<cite>
**Referenced Files in This Document**
- [README.md](file://README.md)
- [pyproject.toml](file://pyproject.toml)
- [docker-compose.yml](file://docker-compose.yml)
- [Dockerfile.rag_service](file://Dockerfile.rag_service)
- [packages/core/pyproject.toml](file://packages/core/pyproject.toml)
- [packages/admin/pyproject.toml](file://packages/admin/pyproject.toml)
- [packages/rag_service/pyproject.toml](file://packages/rag_service/pyproject.toml)
- [packages/vk_bot/pyproject.toml](file://packages/vk_bot/pyproject.toml)
- [packages/core/src/cafetera_core/config.py](file://packages/core/src/cafetera_core/config.py)
- [packages/core/src/cafetera_core/rag_client.py](file://packages/core/src/cafetera_core/rag_client.py)
- [packages/rag_service/src/cafetera_rag_service/main.py](file://packages/rag_service/src/cafetera_rag_service/main.py)
- [packages/rag_service/src/cafetera_rag_service/server.py](file://packages/rag_service/src/cafetera_rag_service/server.py)
- [packages/rag_service/src/cafetera_rag_service/api/health.py](file://packages/rag_service/src/cafetera_rag_service/api/health.py)
- [packages/rag_service/src/cafetera_rag_service/api/qa.py](file://packages/rag_service/src/cafetera_rag_service/api/qa.py)
- [packages/rag_service/src/cafetera_rag_service/api/indexing.py](file://packages/rag_service/src/cafetera_rag_service/api/indexing.py)
- [packages/rag_service/src/cafetera_rag_service/api/ingest.py](file://packages/rag_service/src/cafetera_rag_service/api/ingest.py)
- [packages/rag_service/src/cafetera_rag_service/api/deps.py](file://packages/rag_service/src/cafetera_rag_service/api/deps.py)
- [packages/rag_service/src/cafetera_rag_service/rag/chain.py](file://packages/rag_service/src/cafetera_rag_service/rag/chain.py)
- [packages/rag_service/src/cafetera_rag_service/rag/retriever.py](file://packages/rag_service/src/cafetera_rag_service/rag/retriever.py)
- [packages/rag_service/src/cafetera_rag_service/rag/reranker.py](file://packages/rag_service/src/cafetera_rag_service/rag/reranker.py)
- [packages/rag_service/src/cafetera_rag_service/qa_service.py](file://packages/rag_service/src/cafetera_rag_service/qa_service.py)
- [packages/rag_service/src/cafetera_rag_service/models.py](file://packages/rag_service/src/cafetera_rag_service/models.py)
- [packages/rag_service/src/cafetera_rag_service/config.py](file://packages/rag_service/src/cafetera_rag_service/config.py)
- [packages/rag_service/src/cafetera_rag_service/resources.py](file://packages/rag_service/src/cafetera_rag_service/resources.py)
- [packages/rag_service/src/cafetera_rag_service/parser.py](file://packages/rag_service/src/cafetera_rag_service/parser.py)
- [packages/admin/src/cafetera_admin/config.py](file://packages/admin/src/cafetera_admin/config.py)
- [packages/admin/src/cafetera_admin/server.py](file://packages/admin/src/cafetera_admin/server.py)
- [packages/admin/src/cafetera_admin/api/documents.py](file://packages/admin/src/cafetera_admin/api/documents.py)
- [packages/vk_bot/src/cafetera_vk_bot/main.py](file://packages/vk_bot/src/cafetera_vk_bot/main.py)
- [packages/vk_bot/src/cafetera_vk_bot/bot.py](file://packages/vk_bot/src/cafetera_vk_bot/bot.py)
- [scripts/rag_server.py](file://scripts/rag_server.py)
- [scripts/admin_server.py](file://scripts/admin_server.py)
- [scripts/polling_vk.py](file://scripts/polling_vk.py)
</cite>

## Update Summary
**Changes Made**
- Enhanced LLM configuration system with dynamic sampling parameter management
- Implemented provider-aware parameter handling for OpenAI, Ollama, and llama.cpp
- Added comprehensive sampling parameter support including temperature, top_p, top_k, and presence_penalty
- Improved LLM initialization with conditional parameter forwarding based on provider capabilities
- Added graceful degradation for unsupported parameters across different providers

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Security Enhancements](#security-enhancements)
9. [Troubleshooting Guide](#troubleshooting-guide)
10. [Conclusion](#conclusion)

## Introduction
This document describes the RAG (Retrieval-Augmented Generation) microservice architecture for the Cafetera HR Bot system. The system consists of three primary parts:
- Admin Panel: Web interface for uploading and managing documents
- VK Bot: A chatbot responding to employee questions in VKontakte groups
- RAG Service: Internal microservice handling AI queries and knowledge base operations

The RAG Service operates on port 8001 and communicates with the Admin Panel and VK Bot via HTTP. It integrates with Qdrant for vector similarity search, supports multiple AI providers (Ollama, OpenAI, llama.cpp), and manages document ingestion and retrieval workflows with enhanced hybrid search capabilities. The service now includes complete document ingestion pipelines with S3 integration, comprehensive error handling, and advanced search control mechanisms.

## Project Structure
The project follows a monorepo workspace structure with four main packages:
- `packages/core`: Shared domain logic, storage abstractions, and cross-package utilities
- `packages/admin`: Admin web UI built with FastAPI and HTMX
- `packages/vk_bot`: VKontakte bot integration
- `packages/rag_service`: RAG microservice implementing the QA pipeline with hybrid search

```mermaid
graph TB
subgraph "Workspace Packages"
CORE["packages/core<br/>Shared utilities"]
ADMIN["packages/admin<br/>Admin UI"]
VKBOT["packages/vk_bot<br/>VK Bot"]
RAG["packages/rag_service<br/>RAG Microservice"]
end
subgraph "Infrastructure"
QDRANT["Qdrant Vector DB<br/>Port 6333"]
MINIO["MinIO S3 Storage<br/>Port 9000"]
PG["PostgreSQL DB<br/>Port 5432"]
end
ADMIN --> RAG
VKBOT --> RAG
RAG --> QDRANT
RAG --> MINIO
RAG --> PG
CORE -. shared .-> ADMIN
CORE -. shared .-> VKBOT
CORE -. shared .-> RAG
```

**Diagram sources**
- [docker-compose.yml:56-133](file://docker-compose.yml#L56-L133)
- [pyproject.toml:35-42](file://pyproject.toml#L35-L42)

**Section sources**
- [README.md:652-665](file://README.md#L652-L665)
- [pyproject.toml:35-42](file://pyproject.toml#L35-L42)

## Core Components
The core components enable cross-package communication and infrastructure integration:

- **Core Settings**: Centralized configuration for RAG service URL, storage endpoints, and indexing concurrency
- **RAG Client**: Async HTTP client for the RAG microservice with support for streaming and document operations
- **Storage Layer**: Database and S3 abstractions used by Admin Panel and RAG Service
- **Domain Services**: Category file management and error handling utilities

Key implementation patterns:
- Asynchronous HTTP client with configurable timeouts and API key authentication
- Environment-driven configuration with backward compatibility aliases
- Shared models and repositories for consistent data access across services

**Section sources**
- [packages/core/src/cafetera_core/config.py:14-40](file://packages/core/src/cafetera_core/config.py#L14-L40)
- [packages/core/src/cafetera_core/rag_client.py:15-151](file://packages/core/src/cafetera_core/rag_client.py#L15-L151)

## Architecture Overview
The system architecture centers around the RAG microservice as the AI and knowledge processing engine. The Admin Panel and VK Bot act as clients that communicate with the RAG Service over HTTP.

```mermaid
graph TB
subgraph "External Clients"
ADMIN_UI["Admin Panel<br/>Web UI"]
VK_CLIENT["VK Bot<br/>Chat Client"]
end
subgraph "RAG Microservice"
API["FastAPI Endpoints"]
QA["QA Service"]
RAG_CHAIN["RAG Chain"]
RETRIEVER["Vector Retriever"]
RERANKER["Re-ranking Component"]
RESOURCES["Resource Manager"]
PARSER["Document Parser"]
INGEST["Ingestion Pipeline"]
INDEX["Indexing Engine"]
LLM_CONFIG["LLM Configuration System"]
SAMPLING_PARAMS["Dynamic Sampling Parameters"]
PROVIDER_AWARE["Provider-Aware Parameter Handling"]
end
subgraph "Infrastructure"
QDRANT["Qdrant<br/>Vector DB"]
S3["MinIO S3<br/>File Storage"]
DB["PostgreSQL<br/>Metadata DB"]
end
ADMIN_UI --> API
VK_CLIENT --> API
API --> QA
QA --> RAG_CHAIN
RAG_CHAIN --> RETRIEVER
RETRIEVER --> QDRANT
QA --> S3
QA --> DB
RESOURCES --> PARSER
RESOURCES --> INGEST
RESOURCES --> INDEX
RESOURCES --> LLM_CONFIG
LLM_CONFIG --> SAMPLING_PARAMS
SAMPLING_PARAMS --> PROVIDER_AWARE
RESOURCES --> LLM_CONFIG
INGEST --> PARSER
INGEST --> INDEX
INDEX --> QDRANT
```

**Diagram sources**
- [packages/rag_service/src/cafetera_rag_service/server.py](file://packages/rag_service/src/cafetera_rag_service/server.py)
- [packages/rag_service/src/cafetera_rag_service/qa_service.py](file://packages/rag_service/src/cafetera_rag_service/qa_service.py)
- [packages/rag_service/src/cafetera_rag_service/rag/chain.py](file://packages/rag_service/src/cafetera_rag_service/rag/chain.py)
- [packages/rag_service/src/cafetera_rag_service/rag/retriever.py](file://packages/rag_service/src/cafetera_rag_service/rag/retriever.py)
- [packages/rag_service/src/cafetera_rag_service/rag/reranker.py](file://packages/rag_service/src/cafetera_rag_service/rag/reranker.py)
- [packages/rag_service/src/cafetera_rag_service/resources.py](file://packages/rag_service/src/cafetera_rag_service/resources.py)
- [packages/rag_service/src/cafetera_rag_service/parser.py](file://packages/rag_service/src/cafetera_rag_service/parser.py)

## Detailed Component Analysis

### Enhanced LLM Configuration System
The RAG Service now features a sophisticated LLM configuration system with dynamic sampling parameter management and provider-aware parameter handling:

```mermaid
flowchart TD
Start(["LLM Configuration Request"]) --> LoadSettings["Load RagServiceSettings"]
LoadSettings --> CheckProvider{"Check LLM Provider"}
CheckProvider --> |OpenAI| OpenAIParams["Apply OpenAI-Compatible Parameters"]
CheckProvider --> |Ollama| OllamaParams["Apply Ollama Parameters"]
CheckProvider --> |Llama.cpp| LlamaParams["Apply Llama.cpp Parameters"]
OpenAIParams --> OpenAIValidation["Validate OpenAI Parameters"]
OllamaParams --> OllamaValidation["Validate Ollama Parameters"]
LlamaParams --> LlamaValidation["Validate Llama.cpp Parameters"]
OpenAIValidation --> ForwardParams["Forward Parameters to LLM"]
OllamaValidation --> ForwardParams
LlamaValidation --> ForwardParams
ForwardParams --> BuildLLM["Build LLM Instance"]
BuildLLM --> End(["LLM Ready for Use"])
```

**Diagram sources**
- [packages/rag_service/src/cafetera_rag_service/config.py:34-44](file://packages/rag_service/src/cafetera_rag_service/config.py#L34-L44)
- [packages/rag_service/src/cafetera_rag_service/rag/chain.py:53-86](file://packages/rag_service/src/cafetera_rag_service/rag/chain.py#L53-L86)

**Updated** Enhanced with comprehensive sampling parameter support and provider-aware handling

Key configuration parameters:
- **Temperature Control**: Primary randomness control with default 0.3 for balanced responses
- **Top-p Sampling**: Nucleus sampling for diverse yet coherent responses
- **Top-k Sampling**: Limited vocabulary sampling for focused responses
- **Presence Penalty**: OpenAI-specific parameter for controlling repetition
- **Provider-Specific Handling**: Graceful parameter forwarding based on provider capabilities

**Section sources**
- [packages/rag_service/src/cafetera_rag_service/config.py:34-44](file://packages/rag_service/src/cafetera_rag_service/config.py#L34-L44)
- [packages/rag_service/src/cafetera_rag_service/rag/chain.py:53-86](file://packages/rag_service/src/cafetera_rag_service/rag/chain.py#L53-L86)

### Provider-Aware Parameter Handling
The system implements intelligent parameter forwarding based on the selected LLM provider:

```mermaid
sequenceDiagram
participant Client as "Client Code"
participant Settings as "RagServiceSettings"
participant OpenAIHandler as "_openai_sampling_kwargs"
participant OllamaHandler as "_ollama_sampling_kwargs"
participant LLM as "LLM Instance"
Client->>Settings : Access sampling parameters
alt OpenAI Provider
Client->>OpenAIHandler : Call with settings
OpenAIHandler->>OpenAIHandler : Check llm_top_p, llm_presence_penalty, llm_top_k
OpenAIHandler->>LLM : Forward compatible parameters
else Ollama Provider
Client->>OllamaHandler : Call with settings
OllamaHandler->>OllamaHandler : Check llm_top_p, llm_top_k
OllamaHandler->>OllamaHandler : Skip unsupported presence_penalty
OllamaHandler->>LLM : Forward supported parameters
else Llama.cpp Provider
Client->>OpenAIHandler : Call with settings
OpenAIHandler->>OpenAIHandler : Check llm_top_p, llm_presence_penalty, llm_top_k
OpenAIHandler->>LLM : Forward compatible parameters
end
```

**Diagram sources**
- [packages/rag_service/src/cafetera_rag_service/rag/chain.py:53-86](file://packages/rag_service/src/cafetera_rag_service/rag/chain.py#L53-L86)
- [packages/rag_service/src/cafetera_rag_service/rag/chain.py:89-135](file://packages/rag_service/src/cafetera_rag_service/rag/chain.py#L89-L135)

**Updated** Enhanced with provider-specific parameter validation and forwarding logic

Provider-specific behaviors:
- **OpenAI Compatibility**: Supports all sampling parameters including presence_penalty
- **Ollama Native**: Supports top_p and top_k, ignores presence_penalty (uses repeat_penalty)
- **Llama.cpp Compatibility**: Treats as OpenAI-compatible for parameter forwarding

**Section sources**
- [packages/rag_service/src/cafetera_rag_service/rag/chain.py:53-86](file://packages/rag_service/src/cafetera_rag_service/rag/chain.py#L53-L86)
- [packages/rag_service/src/cafetera_rag_service/rag/chain.py:89-135](file://packages/rag_service/src/cafetera_rag_service/rag/chain.py#L89-L135)

### Dynamic Sampling Parameter Management
The system provides dynamic sampling parameter management with conditional forwarding:

```mermaid
flowchart TD
Config["Sampling Parameters in .env"] --> Temperature["llm_temperature"]
Config --> TopP["llm_top_p"]
Config --> TopK["llm_top_k"]
Config --> Presence["llm_presence_penalty"]
Temperature --> CheckTemp{"Is None?"}
TopP --> CheckTopP{"Is None?"}
TopK --> CheckTopK{"Is None?"}
Presence --> CheckPresence{"Is None?"}
CheckTemp --> |No| ForwardTemp["Forward to LLM"]
CheckTemp --> |Yes| SkipTemp["Skip Parameter"]
CheckTopP --> |No| ForwardTopP["Forward to LLM"]
CheckTopP --> |Yes| SkipTopP["Skip Parameter"]
CheckTopK --> |No| ForwardTopK["Forward to LLM"]
CheckTopK --> |Yes| SkipTopK["Skip Parameter"]
CheckPresence --> |No| ForwardPresence["Forward to LLM"]
CheckPresence --> |Yes| SkipPresence["Skip Parameter"]
ForwardTemp --> BuildLLM["Build LLM with Parameters"]
ForwardTopP --> BuildLLM
ForwardTopK --> BuildLLM
ForwardPresence --> BuildLLM
SkipTemp --> BuildLLM
SkipTopP --> BuildLLM
SkipTopK --> BuildLLM
SkipPresence --> BuildLLM
```

**Diagram sources**
- [packages/rag_service/src/cafetera_rag_service/rag/chain.py:53-86](file://packages/rag_service/src/cafetera_rag_service/rag/chain.py#L53-L86)

**Updated** Enhanced with comprehensive parameter validation and conditional forwarding logic

Parameter forwarding strategy:
- **Conditional Forwarding**: Only parameters with non-None values are forwarded
- **Provider Compatibility**: Unsupported parameters are automatically filtered out
- **Default Preservation**: Unset parameters preserve provider defaults
- **Model Recommendations**: Environment variables allow model-specific parameter tuning

**Section sources**
- [packages/rag_service/src/cafetera_rag_service/rag/chain.py:53-86](file://packages/rag_service/src/cafetera_rag_service/rag/chain.py#L53-L86)

### RAG Microservice API Endpoints
The RAG Service exposes several HTTP endpoints for health checks, document indexing, ingestion, and question answering:

```mermaid
sequenceDiagram
participant Admin as "Admin Panel"
participant RAG as "RAG Service"
participant Qdrant as "Qdrant"
participant S3 as "MinIO"
participant DB as "PostgreSQL"
Admin->>RAG : POST /api/qa/ask
RAG->>Qdrant : Vector similarity search
Qdrant-->>RAG : Retrieved chunks
RAG->>RAG : Apply re-ranking
RAG->>S3 : Load document content
RAG->>DB : Fetch metadata
RAG-->>Admin : Generated answer
Admin->>RAG : POST /api/index/ingest
RAG->>S3 : Download document
RAG->>RAG : Parse & chunk
RAG->>RAG : Generate vectors
RAG->>Qdrant : Batch upsert vectors
RAG->>DB : Update document status
RAG-->>Admin : Ingestion complete
Admin->>RAG : POST /api/index/chunks
RAG->>RAG : Generate UUID for each point
RAG->>RAG : Build PointStruct with payload
RAG->>Qdrant : Batch upsert vectors
RAG->>DB : Update document status
RAG-->>Admin : Chunks indexed count
```

**Diagram sources**
- [packages/rag_service/src/cafetera_rag_service/api/qa.py](file://packages/rag_service/src/cafetera_rag_service/api/qa.py)
- [packages/rag_service/src/cafetera_rag_service/api/ingest.py](file://packages/rag_service/src/cafetera_rag_service/api/ingest.py)
- [packages/rag_service/src/cafetera_rag_service/api/indexing.py](file://packages/rag_service/src/cafetera_rag_service/api/indexing.py)
- [packages/rag_service/src/cafetera_rag_service/rag/chain.py](file://packages/rag_service/src/cafetera_rag_service/rag/chain.py)

Key endpoint categories:
- Health monitoring: `/api/health`
- Question answering: `/api/qa/ask`, `/api/qa/stream`, `/api/qa/ask-document`, `/api/qa/stream-document`
- Document ingestion: `/api/index/ingest`
- Document indexing: `/api/index/chunks`, `/api/index/documents/{id}`, `/api/index/documents/{id}/search`, `/api/index/cache/invalidate`

**Section sources**
- [packages/rag_service/src/cafetera_rag_service/api/health.py](file://packages/rag_service/src/cafetera_rag_service/api/health.py)
- [packages/rag_service/src/cafetera_rag_service/api/qa.py](file://packages/rag_service/src/cafetera_rag_service/api/qa.py)
- [packages/rag_service/src/cafetera_rag_service/api/indexing.py](file://packages/rag_service/src/cafetera_rag_service/api/indexing.py)
- [packages/rag_service/src/cafetera_rag_service/api/ingest.py](file://packages/rag_service/src/cafetera_rag_service/api/ingest.py)

### Complete Document Ingestion Pipeline
The ingestion pipeline now provides a complete end-to-end workflow from S3 storage to vector indexing:

```mermaid
flowchart TD
Start(["Ingest Request Received"]) --> Validate["Validate Resources & Parameters"]
Validate --> DeleteExisting["Delete Existing Chunks (Idempotent)"]
DeleteExisting --> Download["Download from S3 Storage"]
Download --> TempFile["Write to Temporary File"]
TempFile --> Parse["Parse with Docling Loader"]
Parse --> Chunk["Chunk with HybridChunker"]
Chunk --> Enrich["Enrich Metadata & Generate IDs"]
Enrich --> Embed["Generate Dense Vectors"]
Embed --> SparseCheck{"Sparse Embeddings Available?"}
SparseCheck --> |Yes| Sparse["Generate Sparse Vectors (BM25)"]
SparseCheck --> |No| SkipSparse["Skip Sparse Vectors"]
Sparse --> BuildPoints["Build PointStruct Objects"]
SkipSparse --> BuildPoints
BuildPoints --> UUIDGen["Generate UUID for Each Point"]
UUIDGen --> BatchSize{"Batch Size Reached?"}
BatchSize --> |No| Continue["Continue Building Points"]
BatchSize --> |Yes| BatchUpsert["Batch Upsert to Qdrant"]
BatchUpsert --> Continue
Continue --> More{"More Points?"}
More --> |Yes| BatchSize
More --> |No| InvalidateCache["Invalidate QA Cache"]
InvalidateCache --> Complete["Ingestion Complete"]
Complete --> Log["Log Success Metrics"]
Log --> End(["Ready for Retrieval"])
```

**Diagram sources**
- [packages/rag_service/src/cafetera_rag_service/api/ingest.py:64-188](file://packages/rag_service/src/cafetera_rag_service/api/ingest.py#L64-L188)

Key enhancements:
- **End-to-End Pipeline**: Complete workflow from S3 download to vector indexing
- **S3 Integration**: Direct integration with MinIO for document storage
- **Docling Parsing**: Advanced document parsing with layout preservation
- **Hybrid Vector Support**: Automatic detection and handling of both dense and sparse vectors
- **Batch Processing**: Configurable batch size (`qdrant_upsert_batch_size`) for efficient vector upsert operations
- **UUID Generation**: Each indexed point receives a unique UUID for reliable identification
- **Metadata Enrichment**: Comprehensive metadata extraction and enrichment
- **Error Handling**: Comprehensive error handling with detailed logging

**Section sources**
- [packages/rag_service/src/cafetera_rag_service/api/ingest.py:64-188](file://packages/rag_service/src/cafetera_rag_service/api/ingest.py#L64-L188)
- [packages/rag_service/src/cafetera_rag_service/parser.py:48-111](file://packages/rag_service/src/cafetera_rag_service/parser.py#L48-L111)
- [packages/rag_service/src/cafetera_rag_service/config.py:54-58](file://packages/rag_service/src/cafetera_rag_service/config.py#L54-L58)

### Enhanced Indexing Pipeline
The indexing pipeline now supports batch processing with configurable batch sizes and generates unique UUIDs for each indexed point:

```mermaid
flowchart TD
Start(["Document Received"]) --> Split["Split into Chunks"]
Split --> Prepare["Prepare Texts & Metadata"]
Prepare --> Embed["Generate Dense Vectors"]
Embed --> SparseCheck{"Sparse Embeddings Available?"}
SparseCheck --> |Yes| Sparse["Generate Sparse Vectors (BM25)"]
SparseCheck --> |No| SkipSparse["Skip Sparse Vectors"]
Sparse --> BuildPoints["Build PointStruct Objects"]
SkipSparse --> BuildPoints
BuildPoints --> UUIDGen["Generate UUID for Each Point"]
UUIDGen --> BatchSize{"Batch Size Reached?"}
BatchSize --> |No| Continue["Continue Building Points"]
BatchSize --> |Yes| BatchUpsert["Batch Upsert to Qdrant"]
BatchUpsert --> Continue
Continue --> More{"More Points?"}
More --> |Yes| BatchSize
More --> |No| Complete["Indexing Complete"]
Complete --> UpdateDB["Update Document Status"]
UpdateDB --> End(["Ready for Retrieval"])
```

**Diagram sources**
- [packages/rag_service/src/cafetera_rag_service/api/indexing.py:26-110](file://packages/rag_service/src/cafetera_rag_service/api/indexing.py#L26-L110)

Key enhancements:
- **Batch Processing**: Configurable batch size (`qdrant_upsert_batch_size`) for efficient vector upsert operations
- **UUID Generation**: Each indexed point receives a unique UUID for reliable identification
- **PointStruct Construction**: Proper payload formatting with `page_content` and `metadata` fields
- **Hybrid Vector Support**: Automatic detection and handling of both dense and sparse vectors

**Section sources**
- [packages/rag_service/src/cafetera_rag_service/api/indexing.py:26-110](file://packages/rag_service/src/cafetera_rag_service/api/indexing.py#L26-L110)
- [packages/rag_service/src/cafetera_rag_service/config.py:27](file://packages/rag_service/src/cafetera_rag_service/config.py#L27)

### Document Search Control and Management
The system now provides comprehensive search control at the document level:

```mermaid
flowchart TD
Document(["Document Indexed"]) --> SearchEnabled["is_search_enabled = True"]
SearchEnabled --> Query["User Query"]
Query --> Filter["Filter by is_search_enabled"]
Filter --> Results["Return Matching Documents"]
SearchEnabled --> Toggle["Admin Toggle Search"]
Toggle --> UpdatePayload["Update Payload in Qdrant"]
UpdatePayload --> InvalidateCache["Invalidate QA Cache"]
InvalidateCache --> ApplyChange["New Retrievals Reflect Change"]
ApplyChange --> Query
```

**Diagram sources**
- [packages/rag_service/src/cafetera_rag_service/api/indexing.py:150-199](file://packages/rag_service/src/cafetera_rag_service/api/indexing.py#L150-L199)

Key features:
- **Document-Level Control**: Individual documents can be enabled/disabled for search
- **Payload Indexing**: Efficient filtering using Qdrant payload indexes
- **Cache Invalidation**: Automatic cache clearing when search status changes
- **Granular Access Control**: Fine-grained control over document visibility

**Section sources**
- [packages/rag_service/src/cafetera_rag_service/api/indexing.py:150-199](file://packages/rag_service/src/cafetera_rag_service/api/indexing.py#L150-L199)

### Hybrid Search Implementation
The retriever now supports hybrid search combining dense and sparse embeddings:

```mermaid
flowchart TD
Query["Incoming Query"] --> DenseVec["Generate Dense Vector"]
DenseVec --> HybridCheck{"Sparse Embeddings Enabled?"}
HybridCheck --> |Yes| SparseVec["Generate Sparse Vector (BM25)"]
HybridCheck --> |No| DenseOnly["Dense-Only Search"]
SparseVec --> HybridSearch["Hybrid Search: Dense + BM25 Prefetch"]
DenseOnly --> DenseSearch["Dense Vector Search"]
HybridSearch --> RRFFusion["Reciprocal Rank Fusion (RRF)"]
RRFFusion --> Results["Combined Results"]
DenseSearch --> Results
Results --> Limit["Apply K-Value Limit"]
Limit --> Docs["Convert to Documents"]
Docs --> End(["Retrieved Documents"])
```

**Diagram sources**
- [packages/rag_service/src/cafetera_rag_service/rag/retriever.py:48-93](file://packages/rag_service/src/cafetera_rag_service/rag/retriever.py#L48-L93)

Core hybrid search features:
- **Dense + Sparse Prefetch**: Combines semantic similarity with lexical matching
- **RRF Fusion**: Reciprocal Rank Fusion combines results from both search modes
- **Adaptive k-values**: Different retrieval depths based on question complexity
- **Graceful Degradation**: Falls back to dense-only search if sparse embeddings unavailable

**Section sources**
- [packages/rag_service/src/cafetera_rag_service/rag/retriever.py:48-93](file://packages/rag_service/src/cafetera_rag_service/rag/retriever.py#L48-L93)
- [packages/rag_service/src/cafetera_rag_service/rag/retriever.py:183-196](file://packages/rag_service/src/cafetera_rag_service/rag/retriever.py#L183-L196)

### RAG Pipeline Implementation
The RAG pipeline combines vector retrieval with re-ranking and contextual generation:

```mermaid
flowchart TD
Start(["Question Received"]) --> Parse["Parse Question"]
Parse --> EstimateK["Estimate K-Value Based on Complexity"]
EstimateK --> Retrieve["Vector Similarity Search"]
Retrieve --> HasResults{"Results Found?"}
HasResults --> |No| GenerateDefault["Generate Default Response"]
HasResults --> |Yes| Rerank["Apply Re-ranking"]
Rerank --> Context["Build Context Window"]
Context --> Generate["Generate Answer"]
Generate --> Stream{"Stream Response?"}
Stream --> |Yes| StreamTokens["Stream Token by Token"]
Stream --> |No| ReturnAnswer["Return Complete Answer"]
GenerateDefault --> ReturnAnswer
StreamTokens --> End(["Response Complete"])
ReturnAnswer --> End
```

**Diagram sources**
- [packages/rag_service/src/cafetera_rag_service/rag/chain.py](file://packages/rag_service/src/cafetera_rag_service/rag/chain.py)
- [packages/rag_service/src/cafetera_rag_service/rag/retriever.py](file://packages/rag_service/src/cafetera_rag_service/rag/retriever.py)
- [packages/rag_service/src/cafetera_rag_service/rag/reranker.py](file://packages/rag_service/src/cafetera_rag_service/rag/reranker.py)

Core pipeline components:
- Vector retriever: Uses Qdrant for semantic similarity search with hybrid capabilities
- Re-ranking: Improves relevance of retrieved chunks
- Context builder: Assembles relevant document segments
- Streaming generator: Provides real-time response tokens

**Section sources**
- [packages/rag_service/src/cafetera_rag_service/rag/chain.py](file://packages/rag_service/src/cafetera_rag_service/rag/chain.py)
- [packages/rag_service/src/cafetera_rag_service/rag/retriever.py](file://packages/rag_service/src/cafetera_rag_service/rag/retriever.py)
- [packages/rag_service/src/cafetera_rag_service/rag/reranker.py](file://packages/rag_service/src/cafetera_rag_service/rag/reranker.py)

### Resource Management and Caching
The system implements comprehensive resource management and caching strategies:

```mermaid
classDiagram
class RagResources {
+settings : RagServiceSettings
+qdrant_client : AsyncQdrantClient
+embeddings : Embeddings
+llm : BaseChatModel
+sparse_embeddings : object
+reranker : CrossEncoderReranker
+s3_storage : S3Storage
}
class QAService {
+_chain : Runnable
+_qdrant_client : AsyncQdrantClient
+_embeddings : Embeddings
+_llm : BaseChatModel
+_settings : RagServiceSettings
+_document_chains_cache : OrderedDict
+_max_cache_size : int
+ask(question, category) str
+stream_ask(question, category) AsyncGenerator
+invalidate_document_chain_cache(document_id)
}
class ResourceFactory {
+build_rag_resources(settings) RagResources
+close_rag_resources(res) None
+build_qa_service(res, system_prompt, include_metadata) QAService
}
RagResources --> QAService : "provides"
ResourceFactory --> RagResources : "creates"
ResourceFactory --> QAService : "creates"
```

**Diagram sources**
- [packages/rag_service/src/cafetera_rag_service/resources.py](file://packages/rag_service/src/cafetera_rag_service/resources.py)
- [packages/rag_service/src/cafetera_rag_service/qa_service.py](file://packages/rag_service/src/cafetera_rag_service/qa_service.py)

Key features:
- **Resource Factory**: Centralized resource initialization and cleanup
- **LRU Cache**: Document-specific chain caching with size limits
- **Graceful Degradation**: Optional components (sparse embeddings, reranker) with fallback
- **Collection Management**: Automatic Qdrant collection creation and configuration

**Section sources**
- [packages/rag_service/src/cafetera_rag_service/resources.py](file://packages/rag_service/src/cafetera_rag_service/resources.py)
- [packages/rag_service/src/cafetera_rag_service/qa_service.py](file://packages/rag_service/src/cafetera_rag_service/qa_service.py)

### Client Integration Patterns
Both Admin Panel and VK Bot integrate with the RAG Service through the shared RAG Client:

```mermaid
classDiagram
class RAGClient {
+ask(question, system_prompt, category, include_metadata) str
+stream_ask(question, system_prompt, category, include_metadata) AsyncIterator[str]
+ask_about_document(question, document_id) str
+stream_about_document(question, document_id) AsyncIterator[str]
+index_chunks(document_id, filename, chunks, is_search_enabled) int
+delete_document(document_id) None
+invalidate_cache(document_id) None
+health() dict[str, str]
+aclose() None
}
class AdminPanel {
+upload_document(file)
+monitor_processing()
+manage_categories()
}
class VKBot {
+handle_message(message)
+process_question(question)
}
AdminPanel --> RAGClient : "HTTP requests"
VKBot --> RAGClient : "HTTP requests"
```

**Diagram sources**
- [packages/core/src/cafetera_core/rag_client.py:15-151](file://packages/core/src/cafetera_core/rag_client.py#L15-L151)

Integration patterns:
- Authentication via API key header with constant-time comparison
- Configurable timeouts for normal and indexing operations
- Support for both synchronous answers and streaming responses
- Document lifecycle management (index, delete, cache invalidation)

**Section sources**
- [packages/core/src/cafetera_core/rag_client.py:15-151](file://packages/core/src/cafetera_core/rag_client.py#L15-L151)

### Infrastructure Dependencies
The system relies on three core infrastructure services managed via Docker Compose:

```mermaid
graph TB
subgraph "Docker Compose Services"
QDRANT["Qdrant Service<br/>ports 6333-6334"]
MINIO["MinIO Service<br/>ports 9000-9001"]
PG["PostgreSQL Service<br/>port 5432"]
RAG["RAG Service<br/>port 8001"]
ADMIN["Admin Service<br/>port 8000"]
VK["VK Bot Service"]
end
RAG --> QDRANT
RAG --> MINIO
RAG --> PG
ADMIN --> RAG
VK --> RAG
```

**Diagram sources**
- [docker-compose.yml:1-139](file://docker-compose.yml#L1-L139)

Infrastructure characteristics:
- Health checks for automatic service readiness
- Persistent volumes for data durability
- Environment variable overrides for external AI providers
- Host gateway configuration for local AI model access
- Dedicated RAG service container with separate build process

**Section sources**
- [docker-compose.yml:1-139](file://docker-compose.yml#L1-L139)
- [Dockerfile.rag_service:1-98](file://Dockerfile.rag_service#L1-L98)

## Dependency Analysis
The workspace uses a Python monorepo with explicit package dependencies:

```mermaid
graph TB
subgraph "Workspace Dependencies"
CORE["cafetera-core"]
ADMIN["cafetera-admin"]
VKBOT["cafetera-vk-bot"]
RAG["cafetera-rag-service"]
end
ADMIN --> CORE
VKBOT --> CORE
RAG --> CORE
subgraph "External Dependencies"
FASTAPI["fastapi"]
LANGCHAIN["langchain-*"]
QDRANT["qdrant-client"]
HTTPX["httpx"]
PYDANTIC["pydantic-settings"]
SECRETS["secrets (Python stdlib)"]
DOCLING["docling"]
FASTEMBED["fastembed"]
END
ADMIN --> FASTAPI
ADMIN --> PYDANTIC
RAG --> FASTAPI
RAG --> LANGCHAIN
RAG --> QDRANT
RAG --> HTTPX
RAG --> SECRETS
RAG --> DOCLING
RAG --> FASTEMBED
CORE --> HTTPX
CORE --> PYDANTIC
```

**Diagram sources**
- [packages/admin/pyproject.toml:6-18](file://packages/admin/pyproject.toml#L6-L18)
- [packages/rag_service/pyproject.toml:6-16](file://packages/rag_service/pyproject.toml#L6-L16)
- [packages/core/pyproject.toml:6-12](file://packages/core/pyproject.toml#L6-L12)

Key dependency patterns:
- Core package provides shared utilities and storage abstractions
- Admin and VK Bot depend on Core for configuration and HTTP client
- RAG Service depends on Core plus AI/ML libraries (LangChain, Qdrant, Docling, FastEmbed)
- Security enhancements rely on Python standard library `secrets` module
- Workspace configuration ensures consistent Python version and tooling

**Section sources**
- [pyproject.toml:35-42](file://pyproject.toml#L35-L42)
- [packages/admin/pyproject.toml:6-18](file://packages/admin/pyproject.toml#L6-L18)
- [packages/rag_service/pyproject.toml:6-16](file://packages/rag_service/pyproject.toml#L6-L16)
- [packages/core/pyproject.toml:6-12](file://packages/core/pyproject.toml#L6-L12)

## Performance Considerations
Performance characteristics and optimization opportunities:

- **Indexing Concurrency**: Configurable maximum concurrent indexing operations to balance throughput and resource usage
- **Batch Processing**: Configurable batch size for efficient vector upsert operations with reduced network overhead
- **Streaming Responses**: Real-time token streaming reduces perceived latency for long answers
- **Vector Search Efficiency**: Qdrant provides optimized similarity search with configurable filters and limits
- **Hybrid Search Optimization**: Dense + sparse search fusion improves retrieval quality while maintaining performance
- **Model Provider Flexibility**: Support for multiple AI providers allows selection based on deployment constraints
- **Caching Strategy**: Document content caching reduces repeated retrieval overhead
- **Timeout Management**: Separate timeouts for regular operations vs. indexing accommodate different performance profiles
- **Resource Pooling**: Shared embeddings and LLM instances reduce memory footprint
- **Collection Optimization**: INT8 scalar quantization and payload indexing improve query performance
- **Sampling Parameter Optimization**: Dynamic parameter forwarding reduces unnecessary parameter overhead

Best practices:
- Monitor Qdrant performance metrics and adjust collection configuration
- Tune chunk sizes and overlap for optimal retrieval quality
- Implement connection pooling for high-concurrency scenarios
- Use appropriate embedding models for target language and domain
- Configure batch sizes based on available memory and network bandwidth
- Enable sparse embeddings for better keyword matching
- Leverage provider-specific parameter tuning for optimal model performance

## Security Enhancements
The RAG Service now includes enhanced security measures:

- **Constant-Time Authentication**: API key validation uses `secrets.compare_digest` to prevent timing attacks
- **Configurable API Keys**: Optional API key enforcement for production environments
- **Environment-Based Security**: Development mode allows unauthenticated access while production requires keys
- **Secure Payload Handling**: Proper serialization of metadata and vector payloads
- **Resource Validation**: Comprehensive validation of external service availability
- **Error Containment**: Graceful degradation when critical services are unavailable

Security features:
- API key verification with constant-time comparison prevents timing attacks
- Graceful degradation when no API key is configured (development mode)
- Secure handling of sensitive configuration data
- Proper error handling without exposing internal details
- Resource initialization with comprehensive error handling

**Section sources**
- [packages/rag_service/src/cafetera_rag_service/api/deps.py:13-31](file://packages/rag_service/src/cafetera_rag_service/api/deps.py#L13-L31)
- [packages/rag_service/src/cafetera_rag_service/main.py:16-24](file://packages/rag_service/src/cafetera_rag_service/main.py#L16-L24)

## Troubleshooting Guide
Common issues and resolution strategies:

**Service Connectivity**
- Verify RAG Service health endpoint responds successfully
- Check Docker network connectivity between services
- Confirm proper environment variable configuration for AI providers
- Validate Qdrant collection existence and configuration

**Document Processing Issues**
- Review indexing operation logs for chunk processing failures
- Validate document format compatibility with parser components
- Monitor Qdrant availability and vector upsert operations
- Check batch size configuration for large document processing
- Verify S3 credentials and bucket accessibility

**Performance Problems**
- Adjust max_concurrent_indexing setting based on hardware capabilities
- Monitor memory usage during embedding generation
- Optimize chunk size and re-ranking parameters
- Configure appropriate batch sizes for network efficiency
- Enable sparse embeddings for better keyword matching

**Hybrid Search Issues**
- Verify sparse embedding model installation and availability
- Check BM25 model configuration and loading
- Monitor hybrid search performance compared to dense-only mode
- Validate vector dimension compatibility between dense and sparse embeddings

**LLM Configuration Issues**
- **Sampling Parameter Errors**: Verify environment variables are properly set (LLM_TEMPERATURE, LLM_TOP_P, LLM_TOP_K, LLM_PRESENCE_PENALTY)
- **Provider Mismatch**: Ensure selected provider supports desired parameters (presence_penalty only supported by OpenAI)
- **Parameter Validation**: Check that parameter values are within acceptable ranges for the selected model
- **Fallback Behavior**: Verify graceful degradation when parameters are unsupported by the provider

**Authentication Problems**
- Ensure API key is properly configured in .env file
- Verify X-API-Key header is included in all requests
- Check for timing attack prevention in authentication logs
- Confirm development vs production authentication modes

**Resource Initialization Failures**
- Verify Qdrant connection parameters and service availability
- Check embedding model availability and network connectivity
- Validate S3 credentials and bucket permissions
- Monitor resource factory initialization logs for detailed error information

**Integration Failures**
- Verify API key authentication for client services
- Check CORS configuration for Admin Panel integration
- Validate webhook endpoints for VK Bot integration
- Monitor Docker service dependencies and health checks

**Section sources**
- [packages/core/src/cafetera_core/config.py:34-36](file://packages/core/src/cafetera_core/config.py#L34-L36)
- [packages/core/src/cafetera_core/rag_client.py:26-32](file://packages/core/src/cafetera_core/rag_client.py#L26-L32)

## Conclusion
The RAG Microservice Architecture provides a scalable, modular foundation for AI-powered document retrieval and question answering. The recent enhancements significantly improve functionality and security:

- **Complete Ingestion Pipeline**: Full end-to-end document processing from S3 to vector indexing
- **Enhanced Indexing**: Batch processing with configurable batch sizes and UUID generation for reliable point identification
- **Hybrid Search Capabilities**: Dense + sparse embeddings with BM25 support for improved retrieval quality
- **Comprehensive Search Control**: Document-level search enable/disable functionality with cache invalidation
- **Advanced Resource Management**: Sophisticated caching, resource pooling, and graceful degradation
- **Security Improvements**: Constant-time authentication and configurable API key enforcement
- **Robust Error Handling**: Comprehensive error handling with detailed logging throughout the pipeline
- **Containerized Deployment**: Dedicated RAG service container with optimized build process
- **Flexible AI Integration**: Support for multiple AI providers with graceful fallback mechanisms
- **Production-Ready Features**: S3 integration, comprehensive caching, and resource management
- **Enhanced LLM Configuration**: Dynamic sampling parameter management with provider-aware parameter handling

The architecture supports both development and production deployments while maintaining extensibility for future enhancements such as additional AI providers, custom retrieval strategies, or expanded document formats. The enhanced indexing pipeline, hybrid search capabilities, complete ingestion workflow, and sophisticated LLM configuration system provide superior performance and accuracy for enterprise document retrieval systems.

**Updated** Enhanced with comprehensive LLM configuration system featuring dynamic sampling parameter management and provider-aware parameter handling, enabling fine-grained control over AI model behavior across different providers while maintaining backward compatibility and graceful degradation.