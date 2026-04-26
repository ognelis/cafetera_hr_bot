# Admin Package Integration

<cite>
**Referenced Files in This Document**
- [README.md](file://README.md)
- [Dockerfile.admin](file://Dockerfile.admin)
- [docker-compose.yml](file://docker-compose.yml)
- [pyproject.toml](file://pyproject.toml)
- [packages/admin/pyproject.toml](file://packages/admin/pyproject.toml)
- [packages/admin/src/cafetera_admin/main.py](file://packages/admin/src/cafetera_admin/main.py)
- [packages/admin/src/cafetera_admin/server.py](file://packages/admin/src/cafetera_admin/server.py)
- [packages/admin/src/cafetera_admin/config.py](file://packages/admin/src/cafetera_admin/config.py)
- [packages/admin/src/cafetera_admin/indexer.py](file://packages/admin/src/cafetera_admin/indexer.py)
- [packages/admin/src/cafetera_admin/domain/document_service.py](file://packages/admin/src/cafetera_admin/domain/document_service.py)
- [packages/admin/src/cafetera_admin/api/documents.py](file://packages/admin/src/cafetera_admin/api/documents.py)
- [packages/admin/src/cafetera_admin/api/category_files.py](file://packages/admin/src/cafetera_admin/api/category_files.py)
- [packages/admin/src/cafetera_admin/api/deps.py](file://packages/admin/src/cafetera_admin/api/deps.py)
- [packages/admin/src/cafetera_admin/api/documents_upload.py](file://packages/admin/src/cafetera_admin/api/documents_upload.py)
- [packages/admin/src/cafetera_admin/parser.py](file://packages/admin/src/cafetera_admin/parser.py)
- [packages/admin/src/cafetera_admin/api/documents_helpers.py](file://packages/admin/src/cafetera_admin/api/documents_helpers.py)
- [tests/test_parser.py](file://tests/test_parser.py)
</cite>

## Update Summary
**Changes Made**
- Updated parser section to reflect complete rewrite using Docling for document processing
- Removed references to semantic chunking strategies and custom DOC parsing logic
- Updated dependency analysis to show simplified Docling-based architecture
- Revised text processing capabilities to focus on Docling integration
- Updated troubleshooting guide to reflect new error handling for unsupported formats
- Added comprehensive model caching and offline processing capabilities
- Updated supported file formats to reflect elimination of .doc format support

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Docling-Based Document Processing](#docling-based-document-processing)
7. [Dependency Analysis](#dependency-analysis)
8. [Performance Considerations](#performance-considerations)
9. [Troubleshooting Guide](#troubleshooting-guide)
10. [Conclusion](#conclusion)

## Introduction
This document explains how the Admin Package integrates with the broader Cafetera HR Bot ecosystem. It covers the FastAPI-based admin web UI, its routing, authentication, document lifecycle management, vector indexing, and integration with shared infrastructure (Qdrant, MinIO, PostgreSQL) through the core package. It also describes the Dockerized deployment and local development workflow.

## Project Structure
The project is organized as a uv workspace with three packages:
- cafetera-core: Shared domain logic, storage, RAG components, and services
- cafetera-admin: Admin web UI (FastAPI + HTMX) with document management and category file administration
- cafetera-vk-bot: VK bot implementation

The admin package exposes both HTML pages and JSON APIs, with HTMX partials for dynamic UI updates. It relies on the core package for shared services and models.

```mermaid
graph TB
subgraph "Workspace Packages"
CORE["cafetera-core<br/>Shared domain & storage"]
ADMIN["cafetera-admin<br/>FastAPI + HTMX UI"]
VKBOT["cafetera-vk-bot<br/>VK bot"]
end
subgraph "Infrastructure (via docker-compose)"
QDRANT["Qdrant<br/>Vector DB"]
MINIO["MinIO<br/>S3-compatible storage"]
PG["PostgreSQL<br/>Metadata DB"]
end
ADMIN --> CORE
CORE --> QDRANT
CORE --> MINIO
CORE --> PG
```

**Diagram sources**
- [pyproject.toml:22-28](file://pyproject.toml#L22-L28)
- [docker-compose.yml:56-84](file://docker-compose.yml#L56-L84)

**Section sources**
- [README.md:262-273](file://README.md#L262-L273)
- [pyproject.toml:22-28](file://pyproject.toml#L22-L28)

## Core Components
- Application factory and lifespan: Creates and configures the FastAPI app, mounts static assets and templates, and manages resource lifecycle (Qdrant, S3, embeddings, repositories).
- Settings: Extends core settings with admin-specific fields (e.g., API key).
- Domain service: Orchestrates document lifecycle across metadata, vector store, and file storage.
- Indexer: Handles chunk preparation, embedding computation, upsert to Qdrant, deletion, toggling search visibility, and collection optimization.
- API routers: Provide HTML pages, JSON endpoints, and HTMX partials for document management and category file administration.
- Authentication: Session cookie validation against the admin API key.
- Parser: Loads and chunks .pdf, .docx, and .xlsx files using Docling for advanced document processing.

**Section sources**
- [packages/admin/src/cafetera_admin/main.py:85-114](file://packages/admin/src/cafetera_admin/main.py#L85-L114)
- [packages/admin/src/cafetera_admin/config.py:6-20](file://packages/admin/src/cafetera_admin/config.py#L6-L20)
- [packages/admin/src/cafetera_admin/domain/document_service.py:38-374](file://packages/admin/src/cafetera_admin/domain/document_service.py#L38-L374)
- [packages/admin/src/cafetera_admin/indexer.py:25-251](file://packages/admin/src/cafetera_admin/indexer.py#L25-L251)
- [packages/admin/src/cafetera_admin/api/documents.py:1-539](file://packages/admin/src/cafetera_admin/api/documents.py#L1-L539)
- [packages/admin/src/cafetera_admin/api/category_files.py:1-347](file://packages/admin/src/cafetera_admin/api/category_files.py#L1-L347)
- [packages/admin/src/cafetera_admin/api/deps.py:77-121](file://packages/admin/src/cafetera_admin/api/deps.py#L77-L121)
- [packages/admin/src/cafetera_admin/parser.py:45-105](file://packages/admin/src/cafetera_admin/parser.py#L45-L105)

## Architecture Overview
The admin package runs as a FastAPI application with Hypercorn in production and supports local development. It authenticates requests via a session cookie validated against the admin API key. The app state holds shared resources built by the core package, including S3 storage, Qdrant client, embeddings, document repository, and QA service.

```mermaid
graph TB
CLIENT["Browser<br/>Admin UI"]
FADEP["FastAPI App<br/>cafetera_admin.main"]
DEPS["Dependencies<br/>cafetera_admin.api.deps"]
DOC_SVC["DocumentService<br/>domain/document_service.py"]
CAT_SVC["CategoryFileService<br/>core domain"]
INDEXER["Indexer<br/>indexer.py"]
QDRANT["AsyncQdrantClient<br/>Qdrant"]
S3["S3Storage<br/>MinIO"]
REPO["DocumentRepository<br/>SQLite"]
CLIENT --> FADEP
FADEP --> DEPS
DEPS --> DOC_SVC
DEPS --> CAT_SVC
DOC_SVC --> INDEXER
DOC_SVC --> QDRANT
DOC_SVC --> S3
DOC_SVC --> REPO
INDEXER --> QDRANT
```

**Diagram sources**
- [packages/admin/src/cafetera_admin/main.py:40-83](file://packages/admin/src/cafetera_admin/main.py#L40-L83)
- [packages/admin/src/cafetera_admin/api/deps.py:48-109](file://packages/admin/src/cafetera_admin/api/deps.py#L48-L109)
- [packages/admin/src/cafetera_admin/domain/document_service.py:38-60](file://packages/admin/src/cafetera_admin/domain/document_service.py#L38-L60)
- [packages/admin/src/cafetera_admin/indexer.py:51-134](file://packages/admin/src/cafetera_admin/indexer.py#L51-L134)

## Detailed Component Analysis

### Application Factory and Lifespan
The application factory creates a FastAPI app, resolves repository root for static and template paths, mounts static assets and templates, and registers routers. The lifespan builds shared resources from the core package and injects them into app state. It also constructs the DocumentService and QAService when dependencies are available, and initializes a concurrency semaphore for indexing.

```mermaid
sequenceDiagram
participant Client as "Client"
participant Main as "create_app()"
participant Lifespan as "lifespan()"
participant Core as "build_resources()"
participant App as "FastAPI app"
Client->>Main : Initialize app
Main->>Lifespan : Start lifespan
Lifespan->>Core : build_resources(with_s3, with_db)
Core-->>Lifespan : Resources (s3, qdrant, embeddings, repo)
Lifespan->>App : Inject resources into app.state
Lifespan->>App : Create DocumentService/QAService
Lifespan-->>Main : Yield to app
Main-->>Client : App ready
```

**Diagram sources**
- [packages/admin/src/cafetera_admin/main.py:85-114](file://packages/admin/src/cafetera_admin/main.py#L85-L114)
- [packages/admin/src/cafetera_admin/main.py:40-83](file://packages/admin/src/cafetera_admin/main.py#L40-L83)

**Section sources**
- [packages/admin/src/cafetera_admin/main.py:85-114](file://packages/admin/src/cafetera_admin/main.py#L85-L114)
- [packages/admin/src/cafetera_admin/main.py:40-83](file://packages/admin/src/cafetera_admin/main.py#L40-L83)

### Authentication and Dependencies
Authentication is enforced via a cookie validator that compares the incoming session cookie to the admin API key from settings. The dependency injection layer provides typed accessors for settings, templates, repositories, S3 storage, DocumentService, QAService, and a concurrency semaphore for indexing.

```mermaid
flowchart TD
Start([Request]) --> GetCookie["Extract admin_session cookie"]
GetCookie --> HasKey{"ADMIN_API_KEY set?"}
HasKey --> |No| Error503["HTTP 503: Admin not configured"]
HasKey --> |Yes| Compare["Compare digest with stored key"]
Compare --> Valid{"Digest matches?"}
Valid --> |No| Error403["HTTP 403: Forbidden"]
Valid --> |Yes| Proceed["Proceed to handler"]
```

**Diagram sources**
- [packages/admin/src/cafetera_admin/api/deps.py:77-89](file://packages/admin/src/cafetera_admin/api/deps.py#L77-L89)

**Section sources**
- [packages/admin/src/cafetera_admin/api/deps.py:77-121](file://packages/admin/src/cafetera_admin/api/deps.py#L77-L121)

### Document Management API
The documents router provides:
- HTML pages: login, logout, main documents table, and HTMX partials
- JSON API: list documents with filtering and pagination, get document details, update title, toggle search participation, reindex, delete, and download
- Background indexing via a semaphore to limit concurrent operations

```mermaid
sequenceDiagram
participant Client as "Admin UI"
participant Docs as "documents.py router"
participant Deps as "deps.py"
participant Svc as "DocumentService"
participant S3 as "S3Storage"
participant Qdrant as "AsyncQdrantClient"
participant Repo as "DocumentRepository"
Client->>Docs : POST /api/documents/{id}/reindex
Docs->>Deps : Resolve S3, Service, Repo, Semaphore, QA
Docs->>Repo : Update status to processing
Docs->>Svc : Background task _index_document_from_s3(...)
Svc->>S3 : Download file by s3_key
Svc->>Svc : Parse and chunk document
Svc->>Qdrant : Upsert chunks with dense/bm25/colbert vectors
Svc->>Repo : Update status to completed/failed
Docs-->>Client : Return status or HTMX partial
```

**Diagram sources**
- [packages/admin/src/cafetera_admin/api/documents.py:390-473](file://packages/admin/src/cafetera_admin/api/documents.py#L390-L473)
- [packages/admin/src/cafetera_admin/domain/document_service.py:109-171](file://packages/admin/src/cafetera_admin/domain/document_service.py#L109-L171)
- [packages/admin/src/cafetera_admin/indexer.py:51-134](file://packages/admin/src/cafetera_admin/indexer.py#L51-L134)

**Section sources**
- [packages/admin/src/cafetera_admin/api/documents.py:1-539](file://packages/admin/src/cafetera_admin/api/documents.py#L1-L539)
- [packages/admin/src/cafetera_admin/domain/document_service.py:109-171](file://packages/admin/src/cafetera_admin/domain/document_service.py#L109-L171)

### Category Files Administration
The category files router supports:
- Listing category slots and legal entities
- Uploading Word documents to specific category/subcategory/entity slots
- Downloading and deleting files
- Rendering HTMX partials for individual slot cells

```mermaid
sequenceDiagram
participant Client as "Admin UI"
participant Cat as "category_files.py router"
participant Deps as "deps.py"
participant Svc as "CategoryFileService"
participant S3 as "S3Storage"
Client->>Cat : POST /api/category-files/upload
Cat->>Deps : Validate slot/entity, parse file
Cat->>Svc : Upload file to slot
Svc->>S3 : Store file by s3_key
Cat-->>Client : Return HTMX partial for slot cell
```

**Diagram sources**
- [packages/admin/src/cafetera_admin/api/category_files.py:174-248](file://packages/admin/src/cafetera_admin/api/category_files.py#L174-L248)

**Section sources**
- [packages/admin/src/cafetera_admin/api/category_files.py:1-347](file://packages/admin/src/cafetera_admin/api/category_files.py#L1-L347)

### Vector Indexing Pipeline
The indexer prepares chunks with enriched metadata, computes dense, sparse (BM25), and optional ColBERT vectors, and upserts them into Qdrant. It also supports deleting chunks for a document, toggling search participation, and optimizing the collection to improve performance.

```mermaid
flowchart TD
Start([Prepare Chunks]) --> Enrich["Add document_id, chunk_id, filename, s3_key, is_search_enabled"]
Enrich --> Embed["Compute dense embeddings"]
Embed --> Sparse{"Sparse embeddings enabled?"}
Sparse --> |Yes| SparseEmb["Compute BM25 sparse vectors"]
Sparse --> |No| Next["Skip sparse"]
SparseEmb --> ColBERT{"ColBERT embeddings enabled?"}
Next --> ColBERT
ColBERT --> |Yes| ColEmb["Compute ColBERT vectors"]
ColBERT --> |No| Next2["Skip ColBERT"]
ColEmb --> Next2
Next2 --> Upsert["Upsert points to Qdrant"]
Upsert --> Optimize{"Optimize collection?"}
Optimize --> |Yes| Trigger["Set indexing_threshold=0"]
Trigger --> Wait["Poll until optimizer ok"]
Wait --> Restore["Restore original indexing_threshold"]
Optimize --> |No| End([Done])
Restore --> End
```

**Diagram sources**
- [packages/admin/src/cafetera_admin/indexer.py:25-251](file://packages/admin/src/cafetera_admin/indexer.py#L25-L251)

**Section sources**
- [packages/admin/src/cafetera_admin/indexer.py:25-251](file://packages/admin/src/cafetera_admin/indexer.py#L25-L251)

## Docling-Based Document Processing

### Advanced Document Parsing with Docling
The parser now provides enhanced text processing capabilities through Docling, a modern document processing library that supports multiple document formats with sophisticated layout analysis and table extraction.

#### Docling Integration
The parser uses Docling's `DoclingLoader` with `ExportType.DOC_CHUNKS` to process documents with intelligent chunking based on document structure and content hierarchy.

#### Supported Document Formats
The parser supports three document formats through Docling integration:
- **PDF files**: Full-text extraction with layout preservation and table detection
- **DOCX files**: Rich text processing with paragraph structure and table handling
- **XLSX files**: Spreadsheet conversion to structured markdown tables with column headers

#### Model Caching and Offline Processing
The system implements comprehensive model caching for optimal performance:
- **Tokenizer caching**: Ensures `Qwen/Qwen3-Embedding-0.6B` tokenizer is available offline
- **Docling model caching**: Downloads layout analysis and TableFormer models during startup
- **Offline mode**: Disables network requests after initial model downloads

```mermaid
flowchart TD
Load([Load Document]) --> Detect["Detect file type"]
Detect --> PDF[".pdf: Docling PDF processing"]
Detect --> DOCX[".docx: Docling DOCX processing"]
Detect --> XLSX[".xlsx: Docling XLSX processing"]
PDF --> Chunker["HybridChunker with cached tokenizer"]
DOCX --> Chunker
XLSX --> Chunker
Chunker --> Output([Chunked Documents])
```

**Diagram sources**
- [packages/admin/src/cafetera_admin/parser.py:45-105](file://packages/admin/src/cafetera_admin/parser.py#L45-L105)
- [packages/admin/src/cafetera_admin/parser.py:19-43](file://packages/admin/src/cafetera_admin/parser.py#L19-L43)

**Section sources**
- [packages/admin/src/cafetera_admin/parser.py:1-105](file://packages/admin/src/cafetera_admin/parser.py#L1-L105)
- [packages/admin/src/cafetera_admin/api/documents_upload.py:74-103](file://packages/admin/src/cafetera_admin/api/documents_upload.py#L74-L103)

### Enhanced Text Processing Pipeline
The Docling-based processing pipeline provides sophisticated document understanding:
- **Layout-aware chunking**: Preserves document structure and content hierarchy
- **Intelligent table extraction**: Converts spreadsheets to structured markdown tables
- **Multi-format support**: Unified processing pipeline for PDF, DOCX, and XLSX
- **Model caching**: Pre-downloads and caches all required ML models during Docker build

**Updated** Removed semantic chunking strategies and custom DOC parsing logic in favor of Docling's native capabilities.

**Section sources**
- [packages/admin/src/cafetera_admin/parser.py:45-105](file://packages/admin/src/cafetera_admin/parser.py#L45-L105)
- [packages/admin/src/cafetera_admin/api/documents_upload.py:74-103](file://packages/admin/src/cafetera_admin/api/documents_upload.py#L74-L103)

## Dependency Analysis
The admin package depends on cafetera-core for shared domain services, storage, and configuration. The simplified workspace configuration focuses on Docling-based document processing with essential dependencies.

```mermaid
graph LR
ADMIN["cafetera-admin"]
CORE["cafetera-core"]
FASTAPI["fastapi>=0.135.3"]
HYPERCORN["hypercorn>=0.18.0"]
JINJA["jinja2>=3.1.6"]
MULTIPART["python-multipart>=0.0.24"]
DOCING["docling>=2.0.0"]
LANGCHAIN_DOCLING["langchain-docling>=0.1.0"]
ADMIN --> CORE
ADMIN --> FASTAPI
ADMIN --> HYPERCORN
ADMIN --> JINJA
ADMIN --> MULTIPART
ADMIN --> DOCING
ADMIN --> LANGCHAIN_DOCLING
```

**Updated** Simplified dependencies focusing on Docling integration:
- `docling>=2.0.0`: Core document processing library with layout analysis
- `langchain-docling>=0.1.0`: LangChain integration for document loading
- Removed semantic chunking dependencies (`langchain-text-splitters`, `langchain-experimental`, `tiktoken`)
- Removed custom DOC parsing dependencies (`sharepoint-to-text`)

**Diagram sources**
- [packages/admin/pyproject.toml:6-14](file://packages/admin/pyproject.toml#L6-L14)
- [pyproject.toml:22-28](file://pyproject.toml#L22-L28)

**Section sources**
- [packages/admin/pyproject.toml:1-21](file://packages/admin/pyproject.toml#L1-L21)
- [pyproject.toml:22-28](file://pyproject.toml#L22-L28)

## Performance Considerations
- Concurrency control: A semaphore limits concurrent indexing tasks to prevent resource exhaustion.
- Collection optimization: Post-index optimization temporarily lowers the indexing threshold to merge segments, reducing storage overhead and improving query performance.
- Model caching: Dockerfile pre-downloads Docling models and tokenizer during build to speed up cold starts.
- HTTP/2: Production server uses Hypercorn with HTTP/2 enabled for improved throughput.
- Layout-aware processing: Docling's native chunking preserves document structure for better retrieval performance.

**Section sources**
- [packages/admin/src/cafetera_admin/main.py:78-79](file://packages/admin/src/cafetera_admin/main.py#L78-L79)
- [packages/admin/src/cafetera_admin/indexer.py:196-251](file://packages/admin/src/cafetera_admin/indexer.py#L196-L251)
- [Dockerfile.admin:51-57](file://Dockerfile.admin#L51-L57)
- [packages/admin/src/cafetera_admin/server.py:50-55](file://packages/admin/src/cafetera_admin/server.py#L50-L55)

## Troubleshooting Guide
- Admin not configured: If the admin API key is missing, authentication raises HTTP 503. Ensure the .env file contains ADMIN_API_KEY.
- Resource unavailability: If S3, Qdrant, or DocumentService is missing from app state, handlers return HTTP 503.
- Port conflicts: The admin server binds to port 8000 by default; override with ADMIN_PORT if needed.
- Docker services failing: Check health checks for Qdrant and MinIO; verify ports 6333 and 9000 are free.
- **Docling model issues**: If Docling models fail to load, check that the Docker build successfully cached models in `.cache/huggingface` and `.cache/fastembed`.
- **Format errors**: Legacy .doc format is no longer supported. Convert to .docx format before uploading.
- **Unsupported formats**: Only .pdf, .docx, and .xlsx files are supported. Other formats will raise ValueError.

**Updated** Added troubleshooting guidance for Docling model caching and format support.

**Section sources**
- [packages/admin/src/cafetera_admin/api/deps.py:82-89](file://packages/admin/src/cafetera_admin/api/deps.py#L82-L89)
- [packages/admin/src/cafetera_admin/api/deps.py:62-69](file://packages/admin/src/cafetera_admin/api/deps.py#L62-L69)
- [packages/admin/src/cafetera_admin/api/deps.py:52-59](file://packages/admin/src/cafetera_admin/api/deps.py#L52-L59)
- [packages/admin/src/cafetera_admin/parser.py:65-71](file://packages/admin/src/cafetera_admin/parser.py#L65-L71)
- [README.md:287-307](file://README.md#L287-L307)

## Conclusion
The Admin Package provides a cohesive FastAPI-based interface for managing documents and category files within the Cafetera HR Bot ecosystem. It leverages shared infrastructure and domain services from cafetera-core, integrates HTMX for responsive UI updates, and ensures secure access via cookie-based authentication. The enhanced Docling-based text processing capabilities provide sophisticated document parsing and chunking for PDF, DOCX, and XLSX formats, replacing the previous semantic chunking strategies with modern layout-aware processing. The simplified dependency structure and comprehensive model caching ensure reliable operation in production environments while maintaining the flexibility for future enhancements.