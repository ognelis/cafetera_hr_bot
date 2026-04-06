# Document Management System

<cite>
**Referenced Files in This Document**
- [app/main.py](file://app/main.py)
- [app/config.py](file://app/config.py)
- [app/api/documents.py](file://app/api/documents.py)
- [app/api/deps.py](file://app/api/deps.py)
- [app/domain/document_service.py](file://app/domain/document_service.py)
- [app/storage/document_repo.py](file://app/storage/document_repo.py)
- [app/storage/models.py](file://app/storage/models.py)
- [app/storage/s3.py](file://app/storage/s3.py)
- [app/rag/indexer.py](file://app/rag/indexer.py)
- [app/rag/parser.py](file://app/rag/parser.py)
- [app/rag/retriever.py](file://app/rag/retriever.py)
- [app/integrations/vk/bot.py](file://app/integrations/vk/bot.py)
- [templates/documents.html](file://templates/documents.html)
- [scripts/ingest.py](file://scripts/ingest.py)
- [pyproject.toml](file://pyproject.toml)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [System Architecture](#system-architecture)
3. [Core Components](#core-components)
4. [Document Lifecycle Management](#document-lifecycle-management)
5. [RAG Pipeline](#rag-pipeline)
6. [Storage Layer](#storage-layer)
7. [API Endpoints](#api-endpoints)
8. [Admin Interface](#admin-interface)
9. [Integration Points](#integration-points)
10. [Configuration](#configuration)
11. [Testing Strategy](#testing-strategy)
12. [Deployment and Operations](#deployment-and-operations)

## Introduction

The Document Management System is a comprehensive RAG (Retrieval-Augmented Generation) platform built with FastAPI, designed to manage HR-related documents through a modern web interface. The system provides document ingestion, processing, storage, and retrieval capabilities with support for multiple AI providers and storage backends.

Key features include:
- Web-based administration interface for document management
- Support for Microsoft Word (.docx) documents
- Vector-based semantic search using Qdrant
- Multi-provider embedding support (Ollama, OpenAI, Llama.cpp)
- Asynchronous background processing for document indexing
- HTMX-powered dynamic user interface
- Comprehensive admin authentication and authorization

## System Architecture

The system follows a layered architecture pattern with clear separation of concerns:

```mermaid
graph TB
subgraph "Presentation Layer"
UI[Web Interface]
API[REST API]
end
subgraph "Application Layer"
Router[FastAPI Router]
Service[DocumentService]
Deps[Dependency Injection]
end
subgraph "Domain Layer"
Parser[Docx Parser]
Indexer[Indexer]
Retriever[Retriever]
end
subgraph "Persistence Layer"
SQLite[(SQLite Database)]
S3[(S3/MinIO Storage)]
Qdrant[(Qdrant Vector Store)]
end
subgraph "External Services"
LLM[LLM Provider]
VKBot[VK Bot]
end
UI --> API
API --> Router
Router --> Service
Service --> Parser
Service --> Indexer
Service --> Retriever
Service --> SQLite
Service --> S3
Service --> Qdrant
Parser --> LLM
Retriever --> LLM
VKBot --> Service
```

**Diagram sources**
- [app/main.py:98-119](file://app/main.py#L98-L119)
- [app/api/documents.py:59-59](file://app/api/documents.py#L59-L59)
- [app/domain/document_service.py:35-53](file://app/domain/document_service.py#L35-L53)

## Core Components

### Application Entry Point

The FastAPI application serves as the central orchestrator, managing application lifecycle and dependency injection:

```mermaid
classDiagram
class FastAPIApp {
+create_app(settings) FastAPI
+lifespan(app) asynccontextmanager
+state Settings
+state S3Storage
+state DocumentService
}
class Settings {
+vk_access_token : str
+vk_group_id : int
+qdrant_url : str
+llm_provider : str
+embedding_model : str
+db_path : str
+admin_api_key : str
}
FastAPIApp --> Settings : "uses"
```

**Diagram sources**
- [app/main.py:23-82](file://app/main.py#L23-L82)
- [app/config.py:4-33](file://app/config.py#L4-L33)

**Section sources**
- [app/main.py:1-119](file://app/main.py#L1-L119)
- [app/config.py:1-33](file://app/config.py#L1-L33)

### Document Service Orchestration

The DocumentService acts as the central coordinator for all document operations:

```mermaid
classDiagram
class DocumentService {
-DocumentRepository _repo
-QdrantClient _qdrant
-Embeddings _embeddings
-string _collection
+create_document() DocumentRecord
+index_document() DocumentRecord
+update_metadata() DocumentRecord
+toggle_search() DocumentRecord
+reindex_document() DocumentRecord
+delete_document() bool
}
class DocumentRepository {
+create() DocumentRecord
+get() DocumentRecord
+list_all() DocumentRecord[]
+update() DocumentRecord
+toggle_search() DocumentRecord
+delete() bool
}
class S3Storage {
+upload() void
+download() bytes
+delete() void
+exists() bool
}
DocumentService --> DocumentRepository : "manages"
DocumentService --> S3Storage : "uses"
```

**Diagram sources**
- [app/domain/document_service.py:35-280](file://app/domain/document_service.py#L35-L280)
- [app/storage/document_repo.py:61-202](file://app/storage/document_repo.py#L61-L202)
- [app/storage/s3.py:14-109](file://app/storage/s3.py#L14-L109)

**Section sources**
- [app/domain/document_service.py:1-280](file://app/domain/document_service.py#L1-L280)
- [app/storage/document_repo.py:1-202](file://app/storage/document_repo.py#L1-L202)
- [app/storage/s3.py:1-109](file://app/storage/s3.py#L1-L109)

## Document Lifecycle Management

The system manages document lifecycle through a structured process:

```mermaid
sequenceDiagram
participant User as User
participant API as API Router
participant Service as DocumentService
participant S3 as S3Storage
participant DB as DocumentRepository
participant Qdrant as QdrantClient
User->>API : Upload .docx file
API->>S3 : Upload file
API->>Service : create_document()
Service->>DB : Create metadata record
API->>Service : index_document()
Service->>Qdrant : Index chunks
Service->>DB : Update status/completed
API-->>User : Success response
Note over Service,Qdrant : Background processing handles parsing and indexing
```

**Diagram sources**
- [app/api/documents.py:265-352](file://app/api/documents.py#L265-L352)
- [app/domain/document_service.py:56-132](file://app/domain/document_service.py#L56-L132)

### Status Management

Documents progress through distinct states during processing:

```mermaid
stateDiagram-v2
[*] --> Pending
Pending --> Processing : Upload Complete
Processing --> Completed : Indexing Success
Processing --> Failed : Indexing Error
Completed --> Processing : Reindex Requested
Failed --> Processing : Retry Attempted
Completed --> [*] : Manual Deletion
Failed --> [*] : Manual Deletion
```

**Section sources**
- [app/storage/models.py:11-18](file://app/storage/models.py#L11-L18)
- [app/domain/document_service.py:83-132](file://app/domain/document_service.py#L83-L132)

## RAG Pipeline

The Retrieval-Augmented Generation pipeline processes documents through multiple stages:

```mermaid
flowchart TD
Start([Docx File Received]) --> Parse[Parse with python-docx]
Parse --> Extract[Extract Sections by Headings]
Extract --> Split[Split into Chunks]
Split --> Enrich[Enrich with Metadata]
Enrich --> Embed[Generate Embeddings]
Embed --> Index[Store in Qdrant]
Index --> Complete([Document Ready for Search])
Error[Processing Error] --> IndexError[Mark as Failed]
IndexError --> Complete
```

**Diagram sources**
- [app/rag/parser.py:23-83](file://app/rag/parser.py#L23-L83)
- [app/rag/indexer.py:23-72](file://app/rag/indexer.py#L23-L72)

### Chunk Processing

The system uses intelligent chunking strategies:

| Parameter | Value | Purpose |
|-----------|-------|---------|
| CHUNK_SIZE | 1000 | Maximum characters per chunk |
| CHUNK_OVERLAP | 200 | Characters shared between adjacent chunks |
| Separators | `\n\n`, `\n`, `. `, `" "` | Text splitting priorities |

**Section sources**
- [app/rag/parser.py:15-16](file://app/rag/parser.py#L15-L16)
- [app/rag/parser.py:60-64](file://app/rag/parser.py#L60-L64)

## Storage Layer

The storage architecture provides multiple persistence mechanisms:

```mermaid
erDiagram
DOCUMENTS {
string document_id PK
string filename
string title
string s3_key
string mime_type
int size_bytes
enum status
boolean is_search_enabled
string error
datetime created_at
datetime updated_at
datetime indexed_at
int chunk_count
}
S3_FILES {
string key PK
string filename
binary content
datetime uploaded_at
}
VECTORS {
string id PK
string document_id FK
vector embedding
text content
json metadata
}
DOCUMENTS ||--o{ VECTORS : "processed"
DOCUMENTS ||--|| S3_FILES : "stored_in"
```

**Diagram sources**
- [app/storage/models.py:20-36](file://app/storage/models.py#L20-L36)
- [app/storage/document_repo.py:14-28](file://app/storage/document_repo.py#L14-L28)

### S3 Integration

The S3Storage class provides asynchronous file operations:

```mermaid
classDiagram
class S3Storage {
-string _endpoint_url
-string _access_key
-string _secret_key
-string _bucket
-AioSession _session
-Any _client_ctx
+open() async void
+close() async void
+upload() async void
+download() async bytes
+delete() async void
+exists() async bool
}
S3Storage : "Async operations"
S3Storage : "MinIO/AWS S3 compatible"
```

**Diagram sources**
- [app/storage/s3.py:14-109](file://app/storage/s3.py#L14-L109)

**Section sources**
- [app/storage/s3.py:1-109](file://app/storage/s3.py#L1-L109)
- [app/storage/document_repo.py:1-202](file://app/storage/document_repo.py#L1-L202)

## API Endpoints

The system exposes a comprehensive REST API for document management:

### Authentication Endpoints
- `GET /login` - Admin login page
- `POST /login` - Authenticate and set session cookie
- `GET /logout` - Clear admin session

### Document Management Endpoints
- `GET /documents` - Main admin page with document table
- `POST /api/documents/upload` - Upload .docx files
- `GET /api/documents` - List all documents (JSON)
- `GET /api/documents/{id}` - Get document details
- `PATCH /api/documents/{id}/title` - Update document title
- `PATCH /api/documents/{id}/search` - Toggle search participation
- `POST /api/documents/{id}/reindex` - Re-index document
- `DELETE /api/documents/{id}` - Delete document
- `GET /api/documents/{id}/download` - Download original file

### HTMX Partial Endpoints
- `GET /partials/document-table` - Dynamic table updates
- `GET /partials/document-row/{id}` - Individual row updates
- `GET /partials/document-status/{id}` - Status badge updates

**Section sources**
- [app/api/documents.py:1-531](file://app/api/documents.py#L1-L531)

## Admin Interface

The web interface provides a modern, responsive experience powered by HTMX:

```mermaid
graph LR
subgraph "Admin Interface"
Login[Login Page]
Documents[Documents Table]
Upload[Drag & Drop Upload]
Actions[Action Buttons]
Modals[Dialog Modals]
end
subgraph "HTMX Features"
LiveUpdates[Live Table Updates]
Progress[Upload Progress]
Toast[Success/Error Messages]
Realtime[Real-time Status]
end
Login --> Documents
Documents --> Upload
Upload --> LiveUpdates
Actions --> Modals
Documents --> Progress
Documents --> Toast
Documents --> Realtime
```

**Diagram sources**
- [templates/documents.html:14-319](file://templates/documents.html#L14-L319)

### Key Interface Features

| Feature | Implementation | Purpose |
|---------|---------------|---------|
| Drag & Drop Upload | HTML5 API + JavaScript | User-friendly file upload |
| Real-time Updates | HTMX polling | Automatic table refresh |
| Progress Indicators | XMLHttpRequest | Upload progress feedback |
| Confirmation Dialogs | HTML5 Dialog | Prevent accidental deletions |
| Responsive Design | Tailwind CSS | Mobile/desktop compatibility |

**Section sources**
- [templates/documents.html:1-319](file://templates/documents.html#L1-L319)

## Integration Points

### VK Bot Integration

The system integrates with VKontakte through a sophisticated bot framework:

```mermaid
sequenceDiagram
participant User as VK User
participant Bot as VK Bot
participant Handler as Handler
participant Service as DocumentService
participant Qdrant as Qdrant
User->>Bot : Message/Command
Bot->>Handler : Route to appropriate handler
Handler->>Service : Process query
Service->>Qdrant : Retrieve relevant chunks
Qdrant-->>Service : Related documents
Service-->>Handler : Formatted response
Handler-->>User : Human-readable answer
```

**Diagram sources**
- [app/integrations/vk/bot.py:44-56](file://app/integrations/vk/bot.py#L44-L56)

### Handler Registration

The VK bot uses a hierarchical handler system:

| Handler | Priority | Function |
|---------|----------|----------|
| start | 1 | `/start` command and home screen |
| hr_request | 2 | HR request workflow with state management |
| ask | 3 | Free-text questions with conversation state |
| hire/fire/vacation/pay | 4-7 | Dedicated action handlers |
| sections | 8 | Stub handlers for future features |
| fallback | 9 | Catch-all handler for unknown commands |

**Section sources**
- [app/integrations/vk/bot.py:24-41](file://app/integrations/vk/bot.py#L24-L41)

## Configuration

The system uses a centralized configuration approach:

```mermaid
classDiagram
class Settings {
+vk_access_token : str
+vk_group_id : int
+qdrant_url : str
+qdrant_api_key : str
+qdrant_collection : str
+llm_provider : str
+llm_model : str
+llm_base_url : str
+embedding_model : str
+db_path : str
+s3_endpoint_url : str
+s3_access_key : str
+s3_secret_key : str
+s3_bucket : str
+admin_api_key : str
}
class Environment {
+ENV_FILE : ".env"
+ENCODING : "utf-8"
}
Settings --> Environment : "loads from"
```

**Diagram sources**
- [app/config.py:4-33](file://app/config.py#L4-L33)

### Configuration Categories

| Category | Required | Description |
|----------|----------|-------------|
| VK Integration | Optional | Bot token and group ID |
| Vector Database | Required | Qdrant connection details |
| LLM Providers | Required | Provider selection and credentials |
| Storage | Required | Database and S3 configuration |
| Admin Security | Required | API key for admin interface |

**Section sources**
- [app/config.py:1-33](file://app/config.py#L1-L33)

## Testing Strategy

The system employs comprehensive testing across all layers:

### Test Coverage Areas

| Component | Test Type | Coverage |
|-----------|-----------|----------|
| DocumentService | Unit Tests | Full lifecycle operations |
| API Endpoints | Integration Tests | All HTTP endpoints |
| Storage Layer | Unit Tests | CRUD operations |
| RAG Pipeline | Unit Tests | Parsing and indexing |
| Admin Interface | Integration Tests | HTMX functionality |

### Key Test Scenarios

```mermaid
flowchart TD
Setup[Test Setup] --> CRUD[CRUD Operations]
CRUD --> Lifecycle[Document Lifecycle]
Lifecycle --> RAG[RAG Processing]
RAG --> Integration[Integration Tests]
Integration --> Cleanup[Test Cleanup]
CRUD --> Auth[Authentication Tests]
Lifecycle --> Error[Error Handling]
RAG --> Edge[Edge Cases]
Integration --> Security[Security Tests]
```

**Section sources**
- [tests/test_document_service.py:1-341](file://tests/test_document_service.py#L1-L341)
- [tests/test_api_documents.py:1-542](file://tests/test_api_documents.py#L1-L542)

## Deployment and Operations

### System Requirements

The application requires the following external services:

| Service | Purpose | Version |
|---------|---------|---------|
| Python | Runtime | >=3.11 |
| FastAPI | Web Framework | Latest |
| Qdrant | Vector Database | Latest |
| SQLite | Local Storage | System |
| MinIO/S3 | File Storage | Compatible |
| LLM Provider | Embeddings | Configurable |

### Installation Dependencies

```mermaid
graph TB
subgraph "Required Dependencies"
FastAPI[fastapi]
LangChain[langchain]
Qdrant[qdrant-client]
SQLite[aiosqlite]
S3[aiobotocore]
end
subgraph "Optional Dependencies"
Ollama[langchain-ollama]
OpenAI[langchain-openai]
VK[vkbottle]
Telegram[aiogram]
end
subgraph "Development Tools"
Ruff[ruff]
Mypy[mypy]
PyTest[pytest]
end
```

**Diagram sources**
- [pyproject.toml:7-29](file://pyproject.toml#L7-L29)

### Operational Considerations

| Aspect | Recommendation |
|--------|----------------|
| File Size Limits | 50MB maximum per document |
| Concurrent Uploads | Limited by server resources |
| Background Processing | CPU-intensive operations |
| Memory Usage | Depends on document size and chunk count |
| Network Latency | Affects S3 and LLM provider performance |

**Section sources**
- [pyproject.toml:1-61](file://pyproject.toml#L1-L61)
- [app/api/documents.py:62-67](file://app/api/documents.py#L62-L67)