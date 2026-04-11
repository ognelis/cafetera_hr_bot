# Deployment and Operations

<cite>
**Referenced Files in This Document**
- [Dockerfile.admin](file://Dockerfile.admin)
- [Dockerfile.polling_vk](file://Dockerfile.polling_vk)
- [docker-compose.yml](file://docker-compose.yml)
- [.dockerignore](file://.dockerignore)
- [pyproject.toml](file://pyproject.toml)
- [app/config.py](file://app/config.py)
- [app/main.py](file://app/main.py)
- [app/resources.py](file://app/resources.py)
- [app/storage/database.py](file://app/storage/database.py)
- [app/storage/category_repo.py](file://app/storage/category_repo.py)
- [app/storage/document_repo.py](file://app/storage/document_repo.py)
- [scripts/admin_server.py](file://scripts/admin_server.py)
- [scripts/polling_vk.py](file://scripts/polling_vk.py)
- [scripts/run_admin.sh](file://scripts/run_admin.sh)
- [scripts/run_llama_embeddings.sh](file://scripts/run_llama_embeddings.sh)
- [scripts/run_llama_llm.sh](file://scripts/run_llama_llm.sh)
- [scripts/run_llama_qwen.sh](file://scripts/run_llama_qwen.sh)
- [scripts/run_ollama_embeddings.sh](file://scripts/run_ollama_embeddings.sh)
- [scripts/run_ollama_llm.sh](file://scripts/run_ollama_llm.sh)
- [app/integrations/vk/bot.py](file://app/integrations/vk/bot.py)
- [app/integrations/vk/handlers/start.py](file://app/integrations/vk/handlers/start.py)
- [app/integrations/vk/handlers/ask.py](file://app/integrations/vk/handlers/ask.py)
- [app/integrations/vk/states.py](file://app/integrations/vk/states.py)
- [app/rag/retriever.py](file://app/rag/retriever.py)
- [app/rag/chain.py](file://app/rag/chain.py)
- [app/rag/indexer.py](file://app/rag/indexer.py)
- [app/rag/parser.py](file://app/rag/parser.py)
- [tests/conftest.py](file://tests/conftest.py)
- [AGENTS.md](file://AGENTS.md)
- [PLAN.md](file://PLAN.md)
- [README.md](file://README.md)
</cite>

## Update Summary
**Changes Made**
- Updated VK bot startup process documentation to reflect enhanced resource management with proper event loop integration using loop_wrapper.on_startup/on_shutdown hooks
- Added comprehensive coverage of centralized resource initialization patterns and proper event loop binding
- Enhanced production deployment documentation with improved resource lifecycle management
- Updated operational procedures to include proper resource cleanup and graceful shutdown handling

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Monitoring and Logging](#monitoring-and-logging)
9. [Security Considerations](#security-considerations)
10. [Scaling Approaches](#scaling-approaches)
11. [Production Deployment Playbooks](#production-deployment-playbooks)
12. [Containerization and Docker Support](#containerization-and-docker-support)
13. [Troubleshooting Guide](#troubleshooting-guide)
14. [Conclusion](#conclusion)

## Introduction
This document provides comprehensive guidance for deploying and operating cafetera_hr_bot in production. It covers containerized infrastructure using Docker Compose, operational controls for VK bot long-polling versus webhook-based production operation, planned Telegram integration, and future webhook deployment. The system now features a PostgreSQL database for storing document metadata alongside the existing Qdrant vector database and MinIO object storage. The production server utilizes Hypercorn with HTTP/2 support, replacing Uvicorn for improved performance and modern protocol support. It also documents monitoring and logging strategies, secrets management, scaling approaches, performance optimization, disaster recovery planning, and practical deployment playbooks.

**Updated**: The system now includes comprehensive Docker containerization support with multi-stage Docker builds for admin server and VK polling bot, environment variable configuration, and container networking setup for production deployments. The containerization includes pre-downloading FastEmbed sparse embedding models during build process, comprehensive cleanup optimizations for reduced image size and improved security, and enhanced Docker networking documentation with service discovery guidance. **Enhanced**: The VK bot startup process now features improved resource management with proper event loop integration using loop_wrapper.on_startup/on_shutdown hooks, ensuring all resources bind to the same event loop that handlers will use for optimal performance and resource lifecycle management.

## Project Structure
The repository organizes runtime concerns into layered modules with a new centralized orchestration approach and PostgreSQL database integration:
- Integrations: VK bot adapter and handlers with enhanced resource management
- Domain: States and navigation helpers
- Config: Pydantic-based settings loader with multiple LLM provider support and PostgreSQL database configuration
- Scripts: Centralized orchestration via run_admin.sh with specialized deployment scripts for individual components
- Infrastructure: Docker Compose services for Qdrant, MinIO, and PostgreSQL with health checking
- Storage: PostgreSQL database initialization and repository pattern implementation
- Containerization: Multi-stage Docker builds for admin server and VK polling bot with uv package manager and FastEmbed sparse embeddings

```mermaid
graph TB
subgraph "Runtime"
VKBot["VK Bot Adapter<br/>app/integrations/vk/bot.py"]
Handlers["Handlers<br/>app/integrations/vk/handlers/*"]
States["States<br/>app/integrations/vk/states.py"]
Config["Settings Loader<br/>app/config.py"]
Embeddings["Embedding Models<br/>app/rag/retriever.py"]
Hypercorn["Hypercorn Server<br/>scripts/admin_server.py"]
Orchestrator["Centralized Orchestrator<br/>scripts/run_admin.sh"]
EventLoop["Event Loop Integration<br/>loop_wrapper.on_startup/on_shutdown"]
ResourceMgr["Resource Management<br/>AppResources, build_resources"]
end
subgraph "Infrastructure"
Qdrant["Qdrant Vector DB<br/>docker-compose.yml"]
MinIO["MinIO Object Storage<br/>docker-compose.yml"]
PostgreSQL["PostgreSQL Database<br/>docker-compose.yml"]
LlamaLLM["llama.cpp LLM Server<br/>scripts/run_llama_llm.sh"]
LlamaEmbed["llama.cpp Embedding Server<br/>scripts/run_llama_embeddings.sh"]
OllamaLLM["Ollama LLM Server<br/>scripts/run_ollama_llm.sh"]
OllamaEmbed["Ollama Embedding Server<br/>scripts/run_ollama_embeddings.sh"]
end
subgraph "Containerization"
AdminDocker["Admin Server Dockerfile<br/>Dockerfile.admin"]
VKDocker["VK Polling Dockerfile<br/>Dockerfile.polling_vk"]
DockerCompose["Docker Compose<br/>docker-compose.yml"]
DockerIgnore[".dockerignore<br/>.dockerignore"]
FastEmbedCache["FastEmbed Cache<br/>Pre-downloaded during build"]
end
subgraph "Operations"
DevPoll["Dev Long Poll Script<br/>scripts/polling_vk.py"]
Compose["Docker Compose<br/>docker-compose.yml"]
Env["Environment Variables<br/>.env"]
DBInit["Database Initialization<br/>app/storage/database.py"]
end
VKBot --> Handlers
VKBot --> States
VKBot --> Config
Handlers --> States
Embeddings --> Qdrant
Config --> Env
Config --> PostgreSQL
LlamaLLM --> Embeddings
LlamaEmbed --> Embeddings
OllamaLLM --> Embeddings
OllamaEmbed --> Embeddings
Compose --> Qdrant
Compose --> MinIO
Compose --> PostgreSQL
Hypercorn --> VKBot
Orchestrator --> VKBot
Orchestrator --> LlamaLLM
Orchestrator --> LlamaEmbed
Orchestrator --> OllamaLLM
Orchestrator --> OllamaEmbed
DBInit --> PostgreSQL
AdminDocker --> Hypercorn
AdminDocker --> FastEmbedCache
VKDocker --> DevPoll
DockerCompose --> AdminDocker
DockerCompose --> VKDocker
DockerIgnore --> AdminDocker
DockerIgnore --> VKDocker
EventLoop --> ResourceMgr
ResourceMgr --> VKBot
```

**Diagram sources**
- [app/integrations/vk/bot.py:1-56](file://app/integrations/vk/bot.py#L1-L56)
- [app/integrations/vk/handlers/start.py:1-42](file://app/integrations/vk/handlers/start.py#L1-L42)
- [app/integrations/vk/handlers/ask.py:1-90](file://app/integrations/vk/handlers/ask.py#L1-L90)
- [app/integrations/vk/states.py:1-14](file://app/integrations/vk/states.py#L1-L14)
- [app/config.py:1-62](file://app/config.py#L1-L62)
- [app/storage/database.py:1-58](file://app/storage/database.py#L1-L58)
- [scripts/polling_vk.py:1-73](file://scripts/polling_vk.py#L1-L73)
- [scripts/run_llama_embeddings.sh:1-77](file://scripts/run_llama_embeddings.sh#L1-L77)
- [scripts/run_llama_llm.sh:1-75](file://scripts/run_llama_llm.sh#L1-L75)
- [scripts/run_ollama_embeddings.sh:1-73](file://scripts/run_ollama_embeddings.sh#L1-L73)
- [scripts/run_ollama_llm.sh:1-74](file://scripts/run_ollama_llm.sh#L1-L74)
- [docker-compose.yml:1-53](file://docker-compose.yml#L1-L53)
- [scripts/admin_server.py:1-74](file://scripts/admin_server.py#L1-L74)
- [scripts/run_admin.sh:1-464](file://scripts/run_admin.sh#L1-L464)
- [app/resources.py:1-365](file://app/resources.py#L1-L365)
- [Dockerfile.admin:1-77](file://Dockerfile.admin#L1-L77)
- [Dockerfile.polling_vk:1-71](file://Dockerfile.polling_vk#L1-L71)
- [.dockerignore:1-17](file://.dockerignore#L1-L17)

**Section sources**
- [docker-compose.yml:1-53](file://docker-compose.yml#L1-L53)
- [pyproject.toml:1-62](file://pyproject.toml#L1-L62)
- [app/config.py:1-62](file://app/config.py#L1-L62)
- [app/storage/database.py:1-58](file://app/storage/database.py#L1-L58)
- [scripts/polling_vk.py:1-73](file://scripts/polling_vk.py#L1-L73)
- [scripts/run_llama_embeddings.sh:1-77](file://scripts/run_llama_embeddings.sh#L1-L77)
- [scripts/run_llama_llm.sh:1-75](file://scripts/run_llama_llm.sh#L1-L75)
- [scripts/run_ollama_embeddings.sh:1-73](file://scripts/run_ollama_embeddings.sh#L1-L73)
- [scripts/run_ollama_llm.sh:1-74](file://scripts/run_ollama_llm.sh#L1-L74)
- [app/integrations/vk/bot.py:1-56](file://app/integrations/vk/bot.py#L1-L56)
- [app/integrations/vk/handlers/start.py:1-42](file://app/integrations/vk/handlers/start.py#L1-L42)
- [app/integrations/vk/handlers/ask.py:1-90](file://app/integrations/vk/handlers/ask.py#L1-L90)
- [app/integrations/vk/states.py:1-14](file://app/integrations/vk/states.py#L1-L14)
- [app/rag/retriever.py:1-103](file://app/rag/retriever.py#L1-L103)
- [scripts/admin_server.py:1-74](file://scripts/admin_server.py#L1-L74)
- [scripts/run_admin.sh:1-464](file://scripts/run_admin.sh#L1-L464)
- [app/resources.py:1-365](file://app/resources.py#L1-L365)
- [AGENTS.md:1-88](file://AGENTS.md#L1-L88)
- [PLAN.md:1-207](file://PLAN.md#L1-L207)
- [Dockerfile.admin:1-77](file://Dockerfile.admin#L1-L77)
- [Dockerfile.polling_vk:1-71](file://Dockerfile.polling_vk#L1-L71)
- [.dockerignore:1-17](file://.dockerignore#L1-L17)

## Core Components
- VK Bot Adapter: Creates a fully wired vkbottle Bot with registered labelers and logging, now with enhanced resource management through event loop integration.
- Handlers: Start/main menu/navigation and fallback handlers with centralized service access.
- States: Multi-step dialog states for HR request scenario.
- Config: Pydantic Settings with environment file support and multiple LLM provider configuration including PostgreSQL database URL.
- Dev Long Poll Script: Local development entry-point for VK bot using long polling with proper event loop integration.
- Hypercorn Server: Production-grade ASGI server with HTTP/2 support and configurable worker classes.
- Centralized Orchestrator: run_admin.sh manages provider selection, dependency installation, infrastructure provisioning, service coordination with enhanced error handling and PostgreSQL health checking.
- Specialized Deployment Scripts: Separate scripts for LLM and embedding servers for llama.cpp and Ollama providers with automated model downloading and verification.
- Modular Infrastructure: Docker Compose services with comprehensive health checking for Qdrant, MinIO, and PostgreSQL.
- Database Layer: PostgreSQL database initialization with table creation for document metadata storage and category file management.
- **Updated**: Containerization Layer: Multi-stage Docker builds using uv package manager with non-root user execution, pre-downloaded FastEmbed sparse embeddings cache, and optimized runtime images.
- **Enhanced**: Resource Management: Centralized AppResources container with build_resources() and close_resources() functions for consistent resource lifecycle management across all deployment modes.

**Updated**: The centralized orchestrator (run_admin.sh) provides interactive provider selection, automated dependency management, comprehensive service startup with health checks including PostgreSQL readiness, and robust error handling with detailed fix suggestions for seamless deployment across different LLM providers and database configurations.

**Section sources**
- [app/integrations/vk/bot.py:24-56](file://app/integrations/vk/bot.py#L24-L56)
- [app/integrations/vk/handlers/start.py:23-42](file://app/integrations/vk/handlers/start.py#L23-L42)
- [app/integrations/vk/handlers/ask.py:14-90](file://app/integrations/vk/handlers/ask.py#L14-L90)
- [app/integrations/vk/states.py:4-14](file://app/integrations/vk/states.py#L4-L14)
- [app/config.py:15-62](file://app/config.py#L15-L62)
- [scripts/polling_vk.py:23-73](file://scripts/polling_vk.py#L23-L73)
- [scripts/admin_server.py:55-68](file://scripts/admin_server.py#L55-L68)
- [scripts/run_llama_embeddings.sh:39-77](file://scripts/run_llama_embeddings.sh#L39-L77)
- [scripts/run_llama_llm.sh:39-75](file://scripts/run_llama_llm.sh#L39-L75)
- [scripts/run_ollama_embeddings.sh:26-73](file://scripts/run_ollama_embeddings.sh#L26-L73)
- [scripts/run_ollama_llm.sh:26-74](file://scripts/run_ollama_llm.sh#L26-L74)
- [scripts/run_admin.sh:51-70](file://scripts/run_admin.sh#L51-L70)
- [scripts/run_admin.sh:275-281](file://scripts/run_admin.sh#L275-L281)
- [app/resources.py:106-365](file://app/resources.py#L106-L365)
- [AGENTS.md:16-18](file://AGENTS.md#L16-L18)
- [PLAN.md:132-135](file://PLAN.md#L132-L135)

## Architecture Overview
The system runs a VK bot with optional RAG capabilities backed by PostgreSQL for document metadata storage, Qdrant for vector search, and MinIO for document storage. The RAG system supports multiple embedding providers including llama.cpp with optimized server flags for document embedding tasks. In production, the VK bot operates via FastAPI webhook transport with Hypercorn server supporting HTTP/2; long polling is for local development only. The centralized orchestrator manages all deployment aspects and provider-specific configurations with enhanced error handling, verification, and PostgreSQL database initialization.

**Updated**: The architecture now features modular deployment scripts that separate LLM and embedding server responsibilities, enabling more flexible and maintainable deployment configurations with automated model management, comprehensive verification, and PostgreSQL database integration for persistent document metadata storage. Containerization support enables production-ready deployments with multi-stage Docker builds, optimized runtime environments, pre-downloaded FastEmbed sparse embeddings cache, and enhanced security through non-root user execution. **Enhanced**: The VK bot now integrates with vkbottle's loop_wrapper system for proper event loop management, ensuring all resources bind to the same event loop that handlers will use, preventing resource binding issues and improving performance.

```mermaid
graph TB
Client["VK Client"]
Webhook["FastAPI Webhook Endpoint<br/>Production Transport"]
Bot["VK Bot<br/>app/integrations/vk/bot.py"]
Handlers["Handlers<br/>start/sections/fallback"]
States["States<br/>HR request dialogs"]
Config["Settings<br/>app/config.py"]
PostgreSQL["PostgreSQL Database<br/>Document Metadata"]
Qdrant["Qdrant Vector DB"]
MinIO["MinIO Object Storage"]
Embeddings["Embedding Models<br/>llama.cpp/Ollama"]
LlamaLLM["llama.cpp LLM Server<br/>--embedding flag disabled"]
LlamaEmbed["llama.cpp Embedding Server<br/>--embedding flag enabled"]
OllamaLLM["Ollama LLM Server"]
OllamaEmbed["Ollama Embedding Server"]
Hypercorn["Hypercorn Server<br/>HTTP/2 Enabled"]
Orchestrator["run_admin.sh<br/>Centralized Orchestration"]
AdminDocker["Admin Server Container<br/>Dockerfile.admin"]
VKDocker["VK Polling Container<br/>Dockerfile.polling_vk"]
DockerCompose["Docker Compose<br/>docker-compose.yml"]
FastEmbedCache["FastEmbed Cache<br/>Pre-downloaded Models"]
EventLoop["Event Loop Integration<br/>loop_wrapper.on_startup/on_shutdown"]
ResourceMgr["Resource Management<br/>AppResources, build_resources"]
Client --> Webhook
Webhook --> Bot
Bot --> Handlers
Bot --> States
Bot --> Config
Handlers --> States
Config --> PostgreSQL
Config --> Qdrant
Config --> MinIO
Embeddings --> Qdrant
LlamaLLM --> Embeddings
LlamaEmbed --> Embeddings
OllamaLLM --> Embeddings
OllamaEmbed --> Embeddings
Hypercorn --> Webhook
Orchestrator --> Webhook
Orchestrator --> LlamaLLM
Orchestrator --> LlamaEmbed
Orchestrator --> OllamaLLM
Orchestrator --> OllamaEmbed
Orchestrator --> PostgreSQL
AdminDocker --> Hypercorn
AdminDocker --> FastEmbedCache
AdminDocker --> DockerCompose
VKDocker --> DevPoll
VKDocker --> FastEmbedCache
VKDocker --> DockerCompose
EventLoop --> ResourceMgr
ResourceMgr --> Bot
```

**Diagram sources**
- [app/integrations/vk/bot.py:24-56](file://app/integrations/vk/bot.py#L24-L56)
- [app/integrations/vk/handlers/start.py:23-42](file://app/integrations/vk/handlers/start.py#L23-L42)
- [app/integrations/vk/handlers/ask.py:14-90](file://app/integrations/vk/handlers/ask.py#L14-L90)
- [app/integrations/vk/states.py:4-14](file://app/integrations/vk/states.py#L4-L14)
- [app/config.py:15-62](file://app/config.py#L15-L62)
- [docker-compose.yml:30-47](file://docker-compose.yml#L30-L47)
- [scripts/run_llama_embeddings.sh:68-77](file://scripts/run_llama_embeddings.sh#L68-L77)
- [scripts/run_llama_llm.sh:68-75](file://scripts/run_llama_llm.sh#L68-L75)
- [app/rag/retriever.py:22-62](file://app/rag/retriever.py#L22-L62)
- [scripts/admin_server.py:55-68](file://scripts/admin_server.py#L55-L68)
- [scripts/run_admin.sh:223-356](file://scripts/run_admin.sh#L223-L356)
- [app/resources.py:106-365](file://app/resources.py#L106-L365)
- [Dockerfile.admin:1-77](file://Dockerfile.admin#L1-L77)
- [Dockerfile.polling_vk:1-71](file://Dockerfile.polling_vk#L1-L71)

**Section sources**
- [AGENTS.md:16-18](file://AGENTS.md#L16-L18)
- [PLAN.md:132-135](file://PLAN.md#L132-L135)
- [docker-compose.yml:30-47](file://docker-compose.yml#L30-L47)
- [scripts/run_llama_embeddings.sh:68-77](file://scripts/run_llama_embeddings.sh#L68-L77)
- [scripts/run_llama_llm.sh:68-75](file://scripts/run_llama_llm.sh#L68-L75)
- [app/rag/retriever.py:22-62](file://app/rag/retriever.py#L22-L62)
- [scripts/admin_server.py:55-68](file://scripts/admin_server.py#L55-L68)
- [scripts/run_admin.sh:223-356](file://scripts/run_admin.sh#L223-L356)
- [app/resources.py:106-365](file://app/resources.py#L106-L365)

## Detailed Component Analysis

### Enhanced VK Bot Startup Process with Event Loop Integration
The VK bot now features improved resource management through proper event loop integration using vkbottle's loop_wrapper.on_startup/on_shutdown hooks, ensuring all resources bind to the same event loop that handlers will use.

```mermaid
flowchart TD
Start(["VK Bot Startup"]) --> CreateBot["create_bot(settings)<br/>app/integrations/vk/bot.py"]
CreateBot --> RegisterHandlers["Register Labelers<br/>_HANDLER_LABELERS order"]
RegisterHandlers --> SetupEventLoop["Setup loop_wrapper<br/>on_startup/on_shutdown"]
SetupEventLoop --> OnStartup["_setup(bot) coroutine<br/>scripts/polling_vk.py"]
OnStartup --> BuildResources["await build_resources()<br/>app/resources.py"]
BuildResources --> StoreResources["Store on bot._app_resources"]
StoreResources --> SetServices["set_qa_service()<br/>set_category_file_service()"]
SetServices --> Ready["Bot Ready<br/>Event Loop Bound Resources"]
Ready --> ShutdownHook["_cleanup(bot) coroutine<br/>on shutdown"]
ShutdownHook --> CloseResources["await close_resources()<br/>Graceful Cleanup"]
CloseResources --> End(["Shutdown Complete"])
```

**Diagram sources**
- [app/integrations/vk/bot.py:42-56](file://app/integrations/vk/bot.py#L42-L56)
- [scripts/polling_vk.py:23-73](file://scripts/polling_vk.py#L23-L73)
- [app/resources.py:130-316](file://app/resources.py#L130-L316)

**Section sources**
- [app/integrations/vk/bot.py:42-56](file://app/integrations/vk/bot.py#L42-L56)
- [scripts/polling_vk.py:23-73](file://scripts/polling_vk.py#L23-L73)
- [app/resources.py:130-316](file://app/resources.py#L130-L316)

### Centralized Resource Management System
The AppResources container provides centralized resource initialization and cleanup across all deployment modes, ensuring consistent resource lifecycle management.

```mermaid
flowchart TD
Start(["build_resources(settings)"]) --> InitS3["Initialize S3 Storage<br/>if with_s3=True"]
InitS3 --> InitQdrant["Initialize Qdrant Client<br/>and Embeddings"]
InitQdrant --> InitSparse["Initialize Sparse Embeddings<br/>(hybrid search)"]
InitSparse --> InitDB["Initialize Database<br/>if with_db=True"]
InitDB --> InitDocRepo["Initialize DocumentRepository<br/>and DocumentService"]
InitDocRepo --> InitQA["Initialize QA Services<br/>QAServices for RAG"]
InitQA --> ReturnRes["Return AppResources"]
ReturnRes --> CloseResources["close_resources(res)<br/>Graceful Cleanup"]
CloseResources --> CloseS3["Close S3 Client"]
CloseS3 --> CloseQdrant["Close Qdrant Client"]
CloseQdrant --> CloseDB["Disconnect Database"]
CloseDB --> ResetFields["Reset All Fields to None"]
ResetFields --> Done(["Cleanup Complete"])
```

**Diagram sources**
- [app/resources.py:130-316](file://app/resources.py#L130-L316)
- [app/resources.py:319-365](file://app/resources.py#L319-L365)

**Section sources**
- [app/resources.py:106-365](file://app/resources.py#L106-L365)

### PostgreSQL Database Integration and Schema Management
The system now includes PostgreSQL database integration for persistent document metadata storage with comprehensive table creation and indexing.

```mermaid
flowchart TD
Start(["PostgreSQL Integration"]) --> DBInit["Database Initialization<br/>app/storage/database.py"]
DBInit --> CreateDocs["Create Documents Table<br/>documents table with metadata"]
DBInit --> CreateCategories["Create Category Files Table<br/>category_files table"]
DBInit --> CreateIndex["Create Unique Index<br/>uq_cat_sub_entity index"]
CreateDocs --> Ready["Tables Ready<br/>Document Metadata Storage"]
CreateCategories --> Ready
CreateIndex --> Ready
Ready --> Connection["Database Connection<br/>databases.Database"]
Connection --> ResourceInit["Resource Initialization<br/>app/resources.py"]
ResourceInit --> DocumentRepo["DocumentRepository<br/>app/storage/document_repo.py"]
ResourceInit --> CategoryRepo["CategoryFileRepository<br/>app/storage/category_repo.py"]
DocumentRepo --> ServiceInit["Service Initialization<br/>DocumentService"]
CategoryRepo --> ServiceInit
ServiceInit --> QAService["QAService<br/>RAG Operations"]
```

**Diagram sources**
- [app/storage/database.py:11-58](file://app/storage/database.py#L11-L58)
- [app/storage/document_repo.py:64-70](file://app/storage/document_repo.py#L64-L70)
- [app/storage/category_repo.py:48-61](file://app/storage/category_repo.py#L48-L61)
- [app/resources.py:208-252](file://app/resources.py#L208-L252)

**Section sources**
- [app/storage/database.py:1-58](file://app/storage/database.py#L1-L58)
- [app/storage/document_repo.py:64-70](file://app/storage/document_repo.py#L64-L70)
- [app/storage/category_repo.py:48-61](file://app/storage/category_repo.py#L48-L61)
- [app/resources.py:208-252](file://app/resources.py#L208-L252)

### Centralized Orchestrator and Enhanced Provider Management
The run_admin.sh script serves as the central orchestration point, providing interactive provider selection, automated dependency management, comprehensive service startup with health checks including PostgreSQL readiness, and robust error handling with detailed fix suggestions.

```mermaid
flowchart TD
Start(["run_admin.sh"]) --> PrereqCheck["Check Prerequisites<br/>docker, uv, .env<br/>Enhanced Error Handling"]
PrereqCheck --> ProviderSelection["Interactive Provider Selection<br/>LLM & Embedding Providers"]
ProviderSelection --> DependencySync["Sync Dependencies<br/>uv sync with extras<br/>Automated Verification"]
DependencySync --> StartInfra["Start Infrastructure<br/>docker compose up -d<br/>Health Checks Enabled"]
StartInfra --> HealthChecks["Health Checks<br/>Qdrant, MinIO, PostgreSQL<br/>Comprehensive Monitoring"]
HealthChecks --> ProviderSetup["Setup Providers<br/>Ollama or llama.cpp<br/>Enhanced Verification Steps"]
ProviderSetup --> ModelManagement["Model Management<br/>Pull/Pull if needed<br/>Automated Download Capabilities"]
ModelManagement --> StartupInfo["Display Startup Info<br/>UI URLs & Service Status<br/>Detailed Logs"]
StartupInfo --> AdminServer["Start Admin Server<br/>uv run python scripts/admin_server.py<br/>Robust Error Handling"]
```

**Diagram sources**
- [scripts/run_admin.sh:69-98](file://scripts/run_admin.sh#L69-L98)
- [scripts/run_admin.sh:100-181](file://scripts/run_admin.sh#L100-L181)
- [scripts/run_admin.sh:183-200](file://scripts/run_admin.sh#L183-L200)
- [scripts/run_admin.sh:202-221](file://scripts/run_admin.sh#L202-L221)
- [scripts/run_admin.sh:275-281](file://scripts/run_admin.sh#L275-L281)
- [scripts/run_admin.sh:365-385](file://scripts/run_admin.sh#L365-L385)

**Section sources**
- [scripts/run_admin.sh:1-464](file://scripts/run_admin.sh#L1-L464)

### Enhanced Error Handling and Verification in Administration Scripts
The administration scripts now feature comprehensive error handling, model verification, automated cleanup procedures, and PostgreSQL health checking to ensure reliable deployment and operation.

**Updated**: The run_admin.sh script includes enhanced error handling with detailed fix suggestions, comprehensive health checks including PostgreSQL readiness, and automated model verification for both Ollama and llama.cpp providers.

**Section sources**
- [scripts/run_admin.sh:243-321](file://scripts/run_admin.sh#L243-L321)
- [scripts/run_admin.sh:323-347](file://scripts/run_admin.sh#L323-L347)
- [scripts/run_ollama_embeddings.sh:26-73](file://scripts/run_ollama_embeddings.sh#L26-L73)
- [scripts/run_ollama_llm.sh:26-74](file://scripts/run_ollama_llm.sh#L26-L74)
- [scripts/run_llama_embeddings.sh:39-77](file://scripts/run_llama_embeddings.sh#L39-L77)
- [scripts/run_llama_llm.sh:39-75](file://scripts/run_llama_llm.sh#L39-L75)

### Automated Model Downloading Capabilities for llama.cpp Providers
The llama.cpp deployment scripts now include intelligent model downloading with fallback mechanisms and progress indicators for improved user experience.

**Updated**: Both run_llama_embeddings.sh and run_llama_llm.sh scripts now feature automated model downloading capabilities with curl/wget fallback support, progress indicators, and comprehensive error handling for model acquisition failures.

```mermaid
flowchart TD
ModelCheck["Check Model File<br/>run_llama_embeddings.sh"] --> ModelExists{"Model Exists?"}
ModelExists --> |Yes| StartServer["Start llama-server<br/>with embedding flags"]
ModelExists --> |No| DownloadModel["Download Model<br/>curl/wget fallback"]
DownloadModel --> DownloadSuccess{"Download Success?"}
DownloadSuccess --> |Yes| StartServer
DownloadSuccess --> |No| ErrorExit["Error: Download Failed<br/>Exit with detailed message"]
StartServer --> ServerReady["Server Ready<br/>Verification Steps"]
```

**Diagram sources**
- [scripts/run_llama_embeddings.sh:39-77](file://scripts/run_llama_embeddings.sh#L39-L77)
- [scripts/run_llama_llm.sh:39-75](file://scripts/run_llama_llm.sh#L39-L75)

**Section sources**
- [scripts/run_llama_embeddings.sh:39-77](file://scripts/run_llama_embeddings.sh#L39-L77)
- [scripts/run_llama_llm.sh:39-75](file://scripts/run_llama_llm.sh#L39-L75)

### Enhanced Provider Verification Steps for Ollama and llamacpp
Both Ollama and llama.cpp providers now include comprehensive verification steps with health checks, model validation, and smoke tests to ensure reliable operation.

**Updated**: The provider verification system now includes health checks, model validation, and smoke tests for both Ollama and llama.cpp providers, with detailed error reporting and fix suggestions.

```mermaid
flowchart TD
ProviderCheck["Provider Check<br/>start_ollama_providers"] --> OllamaCheck{"Ollama Running?"}
OllamaCheck --> |No| StartOllama["Start Ollama Server<br/>Background Process"]
StartOllama --> HealthCheck["Health Check<br/>wait_for_service"]
HealthCheck --> ModelPull["Pull Models<br/>LLM & Embedding"]
ModelPull --> VerifyModels["Verify Models<br/>ollama list validation"]
VerifyModels --> ModelsReady["Models Ready<br/>Detailed Logging"]
ProviderCheck2["Provider Check<br/>start_llamacpp_providers"] --> LlamaCheck{"llama-server Available?"}
LlamaCheck --> |No| ErrorLlama["Error: llama-server not found<br/>Exit with fix suggestion"]
LlamaCheck --> |Yes| CheckServers["Check LLM & Embedding Servers"]
CheckServers --> VerifyLLM["Verify LLM Server<br/>curl -sf /v1/models"]
VerifyLLM --> VerifyEmbed["Verify Embedding Server<br/>curl -sf /v1/models"]
VerifyEmbed --> ServersReady["Servers Ready<br/>Model Verification"]
```

**Diagram sources**
- [scripts/run_admin.sh:223-286](file://scripts/run_admin.sh#L223-L286)
- [scripts/run_admin.sh:288-347](file://scripts/run_admin.sh#L288-L347)

**Section sources**
- [scripts/run_admin.sh:223-286](file://scripts/run_admin.sh#L223-L286)
- [scripts/run_admin.sh:288-347](file://scripts/run_admin.sh#L288-L347)

### VK Bot Factory and Handler Registration
The VK bot factory constructs a Bot instance and loads labelers in a specific order to ensure the fallback handler captures unmatched messages last.

```mermaid
classDiagram
class BotFactory {
+create_bot(settings) Bot
}
class VKBot {
+labeler
+run_polling()
+loop_wrapper.on_startup
+loop_wrapper.on_shutdown
}
class Handlers {
+start_bl
+sections_bl
+fallback_bl
}
class States {
+HR_REQUEST_* states
}
class Settings {
+vk_access_token : string
+vk_group_id : int
+llm_provider : string
+llm_base_url : string
+embedding_provider : string
+embedding_base_url : string
+database_url : string
}
BotFactory --> VKBot : "creates"
VKBot --> Handlers : "loads labelers"
VKBot --> States : "uses"
BotFactory --> Settings : "reads"
```

**Diagram sources**
- [app/integrations/vk/bot.py:24-56](file://app/integrations/vk/bot.py#L24-L56)
- [app/integrations/vk/handlers/start.py:12-42](file://app/integrations/vk/handlers/start.py#L12-L42)
- [app/integrations/vk/states.py:4-14](file://app/integrations/vk/states.py#L4-L14)
- [app/config.py:15-62](file://app/config.py#L15-L62)

**Section sources**
- [app/integrations/vk/bot.py:14-56](file://app/integrations/vk/bot.py#L14-L56)
- [app/integrations/vk/handlers/start.py:12-42](file://app/integrations/vk/handlers/start.py#L12-L42)
- [app/integrations/vk/states.py:4-14](file://app/integrations/vk/states.py#L4-L14)
- [app/config.py:15-62](file://app/config.py#L15-L62)

### Enhanced Resource Lifecycle Management
The VK bot now implements proper resource lifecycle management through event loop integration, ensuring all resources bind to the same event loop that handlers will use.

```mermaid
sequenceDiagram
participant Bot as "VK Bot"
participant LoopWrapper as "loop_wrapper"
participant Setup as "_setup(bot)"
participant Resources as "AppResources"
participant Cleanup as "_cleanup(bot)"
Bot->>LoopWrapper : "register on_startup"
LoopWrapper->>Setup : "call _setup(bot)"
Setup->>Resources : "await build_resources()"
Resources-->>Setup : "AppResources instance"
Setup->>Bot : "store on bot._app_resources"
Setup-->>LoopWrapper : "resources initialized"
LoopWrapper->>LoopWrapper : "event loop running"
LoopWrapper->>LoopWrapper : "handlers use resources"
LoopWrapper->>LoopWrapper : "shutdown signal"
LoopWrapper->>Cleanup : "call _cleanup(bot)"
Cleanup->>Resources : "await close_resources()"
Resources-->>Cleanup : "cleanup complete"
Cleanup-->>LoopWrapper : "shutdown complete"
```

**Diagram sources**
- [scripts/polling_vk.py:23-73](file://scripts/polling_vk.py#L23-L73)
- [app/resources.py:130-316](file://app/resources.py#L130-L316)
- [app/resources.py:319-365](file://app/resources.py#L319-L365)

**Section sources**
- [scripts/polling_vk.py:23-73](file://scripts/polling_vk.py#L23-L73)
- [app/resources.py:130-316](file://app/resources.py#L130-L316)
- [app/resources.py:319-365](file://app/resources.py#L319-L365)

### Hypercorn Server Configuration and HTTP/2 Support
The production server uses Hypercorn with HTTP/2 support, providing improved performance and modern protocol features compared to Uvicorn.

```mermaid
flowchart TD
Start(["admin_server.py"]) --> ImportConfig["Import Hypercorn Config"]
ImportConfig --> CreateConfig["Create Config Instance"]
CreateConfig --> BindAddress["Set bind address<br/>host:port"]
BindAddress --> WorkerClass["Set worker_class<br/>asyncio"]
WorkerClass --> Http2Streams["Configure h2_max_concurrent_streams<br/>100"]
Http2Streams --> CreateApp["Create FastAPI App"]
CreateApp --> RegisterCleanup["Register cleanup handlers"]
RegisterCleanup --> ServeHTTP2["Serve with HTTP/2 support"]
ServeHTTP2 --> Ready(["Ready for production"])
```

**Diagram sources**
- [scripts/admin_server.py:28-68](file://scripts/admin_server.py#L28-L68)

**Section sources**
- [scripts/admin_server.py:1-74](file://scripts/admin_server.py#L1-L74)

### Modular Llama.cpp Deployment Architecture with Enhanced Features
The llama.cpp deployment now uses specialized scripts for LLM and embedding servers, each with optimized configurations, automated model downloading, and comprehensive verification capabilities.

**Updated**: The llama.cpp deployment scripts now include automated model downloading with curl/wget fallback support, progress indicators, and comprehensive error handling for improved user experience and reliability.

```mermaid
flowchart TD
Start(["run_llama_qwen.sh"]) --> SplitScripts["Split into Specialized Scripts"]
SplitScripts --> Embeddings["run_llama_embeddings.sh<br/>--embedding --pooling mean<br/>Automated Model Download"]
SplitScripts --> LLM["run_llama_llm.sh<br/>--no-embedding<br/>Automated Model Download"]
Embeddings --> ModelCheck["Check Model File<br/>Download if Missing"]
ModelCheck --> DownloadSuccess{"Download Success?"}
DownloadSuccess --> |Yes| EmbeddingFlag["--embedding flag enabled"]
DownloadSuccess --> |No| ErrorExit["Error: Download Failed"]
EmbeddingFlag --> PoolingMean["--pooling mean for document embeddings"]
LLM --> NoEmbedding["--no-embedding flag for inference"]
NoEmbedding --> ModelCheck2["Check Model File<br/>Download if Missing"]
PoolingMean --> Ready(["Ready for RAG operations"])
ModelCheck2 --> Ready
```

**Diagram sources**
- [scripts/run_llama_qwen.sh:1-11](file://scripts/run_llama_qwen.sh#L1-L11)
- [scripts/run_llama_embeddings.sh:39-77](file://scripts/run_llama_embeddings.sh#L39-L77)
- [scripts/run_llama_llm.sh:39-75](file://scripts/run_llama_llm.sh#L39-L75)

**Section sources**
- [scripts/run_llama_qwen.sh:1-11](file://scripts/run_llama_qwen.sh#L1-L11)
- [scripts/run_llama_embeddings.sh:1-77](file://scripts/run_llama_embeddings.sh#L1-L77)
- [scripts/run_llama_llm.sh:1-75](file://scripts/run_llama_llm.sh#L1-L75)

### Modular Ollama Deployment Architecture with Comprehensive Verification
The Ollama deployment uses specialized scripts for LLM and embedding servers, with automatic model management, verification, and comprehensive error handling.

**Updated**: The Ollama deployment scripts now include comprehensive model verification, health checks, and detailed error reporting with fix suggestions for improved reliability and user experience.

```mermaid
flowchart TD
Start(["run_ollama_qwen.sh"]) --> SplitScripts["Split into Specialized Scripts"]
SplitScripts --> Embeddings["run_ollama_embeddings.sh<br/>Model: qwen3-embedding:4b-q4_K_M<br/>Health Check & Verification"]
SplitScripts --> LLM["run_ollama_llm.sh<br/>Model: qwen3.5:4b-q4_K_M<br/>Health Check & Verification"]
Embeddings --> CheckOllama["Check Ollama Server<br/>wait_for_ollama Function"]
CheckOllama --> PullModel["Pull Embedding Model if needed<br/>ollama pull"]
PullModel --> VerifyEmbedding["Verify Embedding Model<br/>ollama list validation"]
LLM --> CheckOllama2["Check Ollama Server<br/>wait_for_ollama Function"]
CheckOllama2 --> PullModel2["Pull LLM Model if needed<br/>ollama pull"]
PullModel2 --> VerifyLLM["Verify LLM Model<br/>ollama list validation"]
VerifyEmbedding --> Ready(["Ready for RAG operations<br/>Detailed Logging"])
VerifyLLM --> Ready
```

**Diagram sources**
- [scripts/run_ollama_qwen.sh:1-11](file://scripts/run_ollama_qwen.sh#L1-L11)
- [scripts/run_ollama_embeddings.sh:12-73](file://scripts/run_ollama_embeddings.sh#L12-L73)
- [scripts/run_ollama_llm.sh:12-74](file://scripts/run_ollama_llm.sh#L12-L74)

**Section sources**
- [scripts/run_ollama_qwen.sh:1-11](file://scripts/run_ollama_qwen.sh#L1-L11)
- [scripts/run_ollama_embeddings.sh:1-73](file://scripts/run_ollama_embeddings.sh#L1-L73)
- [scripts/run_ollama_llm.sh:1-74](file://scripts/run_ollama_llm.sh#L1-L74)

### LLM Provider Configuration and Enhanced Embedding Selection
The system supports multiple LLM providers with automatic embedding model selection based on configuration. The default embedding model is now 'qwen3-embedding:4b-q4_K_M' with enhanced verification capabilities.

**Updated**: The embedding configuration now includes enhanced verification steps and comprehensive error handling for model validation and provider compatibility. The system supports hybrid search mode with FastEmbed sparse embeddings for improved retrieval performance.

```mermaid
classDiagram
class Settings {
+llm_provider : string
+embedding_provider : string
+embedding_model : string
+llm_base_url : string
+embedding_base_url : string
+llm_api_key : string
+embedding_api_key : string
+database_url : string
+retrieval_mode : string
+sparse_embedding_model : string
}
class EmbeddingFactory {
+build_embeddings(settings) Embeddings
+enhanced_verification(settings) Embeddings
}
class SparseEmbeddingFactory {
+build_sparse_embeddings(settings) FastEmbedSparse
}
class LlamaCppProvider {
+OpenAIEmbeddings with llama.cpp
+Custom base_url http : //localhost : 8090/v1
+Default model : qwen3-embedding
+Enhanced Error Handling
}
class OllamaProvider {
+OllamaEmbeddings with custom base_url
+Default model : qwen3-embedding : 4b-q4_K_M
+Health Checks & Verification
}
class OpenAIProvider {
+OpenAIEmbeddings with API key
+Default model : text-embedding-3-small
+Import Error Handling
}
class FastEmbedSparse {
+model_name : Qdrant/bm25
+pre_downloaded_cache
}
Settings --> EmbeddingFactory : "provides config"
Settings --> SparseEmbeddingFactory : "provides config"
EmbeddingFactory --> LlamaCppProvider : "when embedding_provider='llamacpp'"
EmbeddingFactory --> OllamaProvider : "when embedding_provider='ollama'"
EmbeddingFactory --> OpenAIProvider : "when embedding_provider='openai'"
SparseEmbeddingFactory --> FastEmbedSparse : "when retrieval_mode='hybrid'"
```

**Diagram sources**
- [app/config.py:15-62](file://app/config.py#L15-L62)
- [app/rag/retriever.py:22-62](file://app/rag/retriever.py#L22-L62)

**Section sources**
- [app/config.py:15-62](file://app/config.py#L15-L62)
- [app/rag/retriever.py:22-62](file://app/rag/retriever.py#L22-L62)

### VK Long Polling Development Flow with Enhanced Resource Management
Local development uses a script that loads settings, creates the bot, registers event loop hooks, and starts the VK bot in long-polling mode with proper resource lifecycle management.

```mermaid
sequenceDiagram
participant Dev as "Developer"
participant Script as "scripts/polling_vk.py"
participant Config as "app/config.py"
participant Bot as "app/integrations/vk/bot.py"
participant LoopWrapper as "vkbottle.loop_wrapper"
participant Resources as "app/resources.py"
Dev->>Script : "Run long poll"
Script->>Config : "Load settings"
Script->>Bot : "create_bot(settings)"
Script->>LoopWrapper : "register on_startup/_setup"
Script->>LoopWrapper : "register on_shutdown/_cleanup"
LoopWrapper->>Resources : "await build_resources()"
Resources-->>LoopWrapper : "AppResources ready"
LoopWrapper->>Bot : "bot.run_forever()"
Note over Script,Bot : "Long polling loop with proper resource management"
```

**Diagram sources**
- [scripts/polling_vk.py:53-73](file://scripts/polling_vk.py#L53-L73)
- [app/config.py:15-62](file://app/config.py#L15-L62)
- [app/integrations/vk/bot.py:24-56](file://app/integrations/vk/bot.py#L24-L56)

**Section sources**
- [scripts/polling_vk.py:1-73](file://scripts/polling_vk.py#L1-L73)
- [app/config.py:15-62](file://app/config.py#L15-L62)
- [app/integrations/vk/bot.py:24-56](file://app/integrations/vk/bot.py#L24-L56)

### Enhanced Containerized Infrastructure Setup
Docker Compose provisions Qdrant, MinIO, and PostgreSQL with comprehensive health checks and persistent volumes.

**Updated**: The Docker Compose configuration now includes PostgreSQL service definition with proper environment variables, volume mounting, health checks, and credentials, along with comprehensive health checking for all infrastructure components. The containerization includes pre-downloaded FastEmbed sparse embeddings cache for improved startup performance.

```mermaid
flowchart TD
Start(["Compose Up"]) --> Services["Start qdrant, minio, postgres"]
Services --> Health["Health checks enabled<br/>Qdrant: /healthz<br/>MinIO: /minio/health/live<br/>PostgreSQL: pg_isready<br/>Retry Mechanisms"]
Health --> Ports["Expose ports:<br/>Qdrant 6333,6334<br/>MinIO 9000,9001<br/>PostgreSQL 5432"]
Ports --> Volumes["Bind volumes:<br/>qdrant_storage<br/>minio_data<br/>pg_data"]
Volumes --> Ready(["Infra Ready<br/>Comprehensive Monitoring"])
```

**Diagram sources**
- [docker-compose.yml:2-53](file://docker-compose.yml#L2-L53)

**Section sources**
- [docker-compose.yml:1-53](file://docker-compose.yml#L1-L53)

### PostgreSQL Database Initialization and Schema Management
The PostgreSQL database is initialized with comprehensive table creation and indexing for document metadata storage.

**Updated**: The database initialization process now includes proper table creation for documents and category_files, unique indexing for category file management, and asyncpg driver configuration for production deployments.

```mermaid
flowchart TD
DBInit["Database Initialization<br/>app/storage/database.py"] --> CreateDocs["Create Documents Table<br/>documents table with metadata"]
DBInit --> CreateCategories["Create Category Files Table<br/>category_files table"]
DBInit --> CreateIndex["Create Unique Index<br/>uq_cat_sub_entity index"]
CreateDocs --> Ready["Tables Ready<br/>Document Metadata Storage"]
CreateCategories --> Ready
CreateIndex --> Ready
Ready --> Connection["Database Connection<br/>databases.Database"]
Connection --> ResourceInit["Resource Initialization<br/>app/resources.py"]
ResourceInit --> DocumentRepo["DocumentRepository<br/>app/storage/document_repo.py"]
ResourceInit --> CategoryRepo["CategoryFileRepository<br/>app/storage/category_repo.py"]
DocumentRepo --> ServiceInit["Service Initialization<br/>DocumentService"]
CategoryRepo --> ServiceInit
ServiceInit --> QAService["QAService<br/>RAG Operations"]
```

**Diagram sources**
- [app/storage/database.py:11-58](file://app/storage/database.py#L11-L58)
- [app/storage/document_repo.py:64-70](file://app/storage/document_repo.py#L64-L70)
- [app/storage/category_repo.py:48-61](file://app/storage/category_repo.py#L48-L61)
- [app/resources.py:208-252](file://app/resources.py#L208-L252)

**Section sources**
- [app/storage/database.py:1-58](file://app/storage/database.py#L1-L58)
- [app/storage/document_repo.py:64-70](file://app/storage/document_repo.py#L64-L70)
- [app/storage/category_repo.py:48-61](file://app/storage/category_repo.py#L48-L61)
- [app/resources.py:208-252](file://app/resources.py#L208-L252)

### Enhanced PostgreSQL Health Checking in Orchestrator
The centralized orchestrator now includes comprehensive PostgreSQL health checking with retry mechanisms and detailed error reporting.

**Updated**: The orchestrator includes a dedicated wait_for_postgres function with configurable retries and intervals, detailed error messages with fix suggestions, and integration with the Docker Compose PostgreSQL service for reliable database startup verification.

```mermaid
flowchart TD
Start(["wait_for_postgres"]) --> RetryLoop["Retry Loop<br/>Configurable retries & intervals"]
RetryLoop --> CheckDB["docker compose exec -T postgres<br/>pg_isready -U cafetera"]
CheckDB --> Success{"Database Ready?"}
Success --> |Yes| LogReady["Log: PostgreSQL is ready"]
Success --> |No| Continue{"More Retries?"}
Continue --> |Yes| Sleep["Sleep interval seconds"]
Sleep --> RetryLoop
Continue --> |No| LogError["Log: PostgreSQL did not become ready"]
LogError --> Return1["Return 1 (failure)"]
LogReady --> Return0["Return 0 (success)"]
```

**Diagram sources**
- [scripts/run_admin.sh:52-70](file://scripts/run_admin.sh#L52-L70)

**Section sources**
- [scripts/run_admin.sh:52-70](file://scripts/run_admin.sh#L52-L70)
- [scripts/run_admin.sh:275-281](file://scripts/run_admin.sh#L275-L281)

### Pre-downloaded FastEmbed Sparse Embeddings Cache
The Docker containerization now includes pre-downloading FastEmbed sparse embedding models during the build process to improve startup performance and reduce runtime dependencies.

**Updated**: Both Dockerfiles (admin and polling_vk) now include a pre-download step for the Qdrant/bm25 sparse embedding model during the builder stage. The cache is then copied to the runtime stage and made accessible to the appuser, eliminating the need for runtime model downloads and improving container startup times.

```mermaid
flowchart TD
BuilderStage["Builder Stage<br/>Dockerfile.admin/polling_vk"] --> PreDownload["Pre-download FastEmbed Model<br/>FastEmbedSparse(model_name='Qdrant/bm25')"]
PreDownload --> CachePath["Set FASTEMBED_CACHE_PATH<br/>/app/.cache/fastembed"]
CachePath --> CopyCache["Copy cache to runtime stage"]
CopyCache --> RuntimeStage["Runtime Stage"]
RuntimeStage --> FastEmbedCache["FastEmbed Cache<br/>Available at /app/.cache/fastembed"]
FastEmbedCache --> AppUser["Accessible by appuser"]
```

**Diagram sources**
- [Dockerfile.admin:26-36](file://Dockerfile.admin#L26-L36)
- [Dockerfile.admin:60-67](file://Dockerfile.admin#L60-L67)
- [Dockerfile.polling_vk:26-36](file://Dockerfile.polling_vk#L26-L36)
- [Dockerfile.polling_vk:57-64](file://Dockerfile.polling_vk#L57-L64)

**Section sources**
- [Dockerfile.admin:26-36](file://Dockerfile.admin#L26-L36)
- [Dockerfile.admin:60-67](file://Dockerfile.admin#L60-L67)
- [Dockerfile.polling_vk:26-36](file://Dockerfile.polling_vk#L26-L36)
- [Dockerfile.polling_vk:57-64](file://Dockerfile.polling_vk#L57-L64)

### Enhanced Cleanup Optimizations for Reduced Image Size
The Docker containerization includes comprehensive cleanup optimizations to reduce image size and improve security.

**Updated**: Both Dockerfiles now include extensive cleanup procedures that remove test files, caches, and temporary files to minimize the final image size. The cleanup targets include Python test directories, cache files, pip/uv caches, and other unnecessary artifacts.

```mermaid
flowchart TD
CleanupStep["Cleanup Step<br/>find /app/.venv/lib/python3.13/site-packages"] --> RemoveTests["Remove test directories<br/>tests, test*, *_tests, test_*.py"]
RemoveTests --> RemoveCaches["Remove cache directories<br/>pip, uv, tmp"]
RemoveCaches --> Finalize["Finalize cleanup<br/>true for error safety"]
Finalize --> SmallerImage["Smaller, More Secure Image"]
```

**Diagram sources**
- [Dockerfile.admin:30-36](file://Dockerfile.admin#L30-L36)
- [Dockerfile.polling_vk:30-36](file://Dockerfile.polling_vk#L30-L36)

**Section sources**
- [Dockerfile.admin:30-36](file://Dockerfile.admin#L30-L36)
- [Dockerfile.polling_vk:30-36](file://Dockerfile.polling_vk#L30-L36)

### Enhanced Docker Networking Documentation with Service Discovery Guidance
The documentation now includes comprehensive guidance for Docker service discovery and networking best practices.

**Updated**: The README includes detailed service discovery guidance showing how to use container names as hostnames when connecting from within Docker networks. The documentation covers the specific service names for Qdrant, MinIO, and PostgreSQL containers and provides examples of connecting using these service names instead of localhost.

```mermaid
flowchart TD
DockerNetwork["Docker Compose Network"] --> ServiceDiscovery["Service Discovery"]
ServiceDiscovery --> QdrantService["rag-bot-qdrant<br/>Host: rag-bot-qdrant"]
ServiceDiscovery --> MinioService["rag-bot-minio<br/>Host: rag-bot-minio"]
ServiceDiscovery --> PostgresService["rag-bot-postgres<br/>Host: rag-bot-postgres"]
QdrantService --> AppConnections["Application Connections"]
MinioService --> AppConnections
PostgresService --> AppConnections
```

**Diagram sources**
- [README.md:253-286](file://README.md#L253-L286)

**Section sources**
- [README.md:253-286](file://README.md#L253-L286)

## Dependency Analysis
External dependencies include FastAPI, Hypercorn, LangChain stack, Qdrant client, VK and Telegram adapters, PostgreSQL asyncpg driver, and testing tools. Optional extras enable Ollama or OpenAI-compatible LLMs. The system now supports llama.cpp with optimized embedding server flags and uses Hypercorn as the production ASGI server instead of Uvicorn. PostgreSQL integration adds asyncpg driver for database connectivity. **Updated**: Containerization dependencies include uv package manager for optimized dependency installation and multi-stage Docker builds. The hybrid search capability requires fastembed>=0.8.0 for sparse embeddings support. **Enhanced**: The VK bot now depends on vkbottle's loop_wrapper system for proper event loop integration and resource lifecycle management.

**Updated**: The centralized orchestrator manages dependency installation through uv sync with provider-specific extras, eliminates manual dependency management complexity, and includes comprehensive error handling for dependency resolution failures. The PostgreSQL integration adds asyncpg driver for production database connectivity. Containerization support uses uv for efficient dependency management in Docker images. The hybrid search feature requires the 'hybrid' extra for FastEmbed sparse embeddings. **Enhanced**: The VK bot integration with loop_wrapper ensures proper event loop binding for all resources, preventing resource binding issues and improving performance.

```mermaid
graph LR
App["cafetera_hr_bot"]
FastAPI["fastapi"]
Hypercorn["hypercorn>=0.18.0"]
LangChain["langchain"]
QdrantClient["qdrant-client"]
VK["vkbottle"]
Telegram["aiogram"]
Tests["pytest"]
LlamaCpp["llama.cpp"]
Ollama["ollama"]
Uv["uv (orchestration)"]
PostgreSQL["asyncpg (database)"]
Docker["docker (containerization)"]
FastEmbed["fastembed>=0.8.0 (hybrid)"]
LoopWrapper["loop_wrapper (event loop)"]
AppResources["AppResources (resource mgmt)"]
AdminDocker["Dockerfile.admin"]
VKDocker["Dockerfile.polling_vk"]
App --> FastAPI
App --> Hypercorn
App --> LangChain
App --> QdrantClient
App --> VK
App --> Telegram
App --> Tests
App --> LlamaCpp
App --> Ollama
App --> Uv
App --> PostgreSQL
App --> Docker
App --> FastEmbed
App --> LoopWrapper
App --> AppResources
AdminDocker --> Uv
VKDocker --> Uv
AdminDocker --> Docker
VKDocker --> Docker
AdminDocker --> FastEmbed
VKDocker --> FastEmbed
AdminDocker --> LoopWrapper
VKDocker --> AppResources
```

**Diagram sources**
- [pyproject.toml:7-29](file://pyproject.toml#L7-L29)

**Section sources**
- [pyproject.toml:1-62](file://pyproject.toml#L1-L62)

## Performance Considerations
- Use production-grade webhook transport instead of long polling to reduce resource overhead and latency.
- Tune Qdrant shard and index parameters for retrieval performance; monitor vector search latency.
- Use MinIO in-cluster for low-latency document ingestion and retrieval.
- Enable FastAPI lifespan initialization for shared resources to avoid cold-starts during requests.
- Apply async I/O patterns and keep handler logic lightweight to maximize throughput.
- **Updated**: Configure Hypercorn with HTTP/2 support and adjustable max concurrent streams (default: 100) for improved connection multiplexing and reduced latency.
- **Updated**: Use asyncio worker class for better performance with HTTP/2 multiplexing capabilities.
- **Updated**: Monitor HTTP/2 connection metrics including stream concurrency, connection reuse, and multiplexing efficiency.
- **Updated**: The modular llama.cpp deployment allows separate optimization of LLM inference and embedding servers for better resource utilization.
- **Updated**: Enhanced Docker Compose health checking ensures reliable infrastructure provisioning and faster failure detection.
- **Updated**: Centralized orchestrator provides optimized startup sequences, comprehensive dependency management, and robust error handling for improved deployment performance.
- **Updated**: Automated model downloading capabilities eliminate manual intervention and reduce deployment downtime.
- **Updated**: PostgreSQL database integration provides persistent storage for document metadata with proper indexing and connection pooling for improved performance.
- **Updated**: Database initialization with proper table creation and unique indexes ensures efficient metadata queries and prevents data integrity issues.
- **Updated**: Multi-stage Docker builds with uv package manager reduce image size and improve build performance.
- **Updated**: Non-root user execution in containers improves security posture and compliance requirements.
- **Updated**: Pre-downloaded FastEmbed sparse embeddings cache eliminates runtime model downloads and improves container startup times.
- **Updated**: Comprehensive cleanup optimizations reduce image size and improve security by removing unnecessary files and caches.
- **Enhanced**: Proper event loop integration ensures all resources bind to the same event loop that handlers will use, preventing resource binding issues and improving performance consistency.

## Monitoring and Logging
- Logging: Configure structured logging at INFO level for operational visibility. Use consistent log formatting and include correlation IDs where applicable.
- Health checks: Leverage Qdrant's health endpoint, MinIO console, and PostgreSQL pg_isready for availability monitoring.
- Metrics: Expose Prometheus metrics via FastAPI middleware and scrape with Prometheus.
- Alerting: Forward logs to centralized logging (e.g., ELK or Loki) and set alerts for error spikes and slow response times.
- Log rotation: Use OS-native log rotation (logrotate) or container logging drivers with size/time limits.
- **Updated**: Monitor Hypercorn HTTP/2 performance metrics including active connections, concurrent streams, and connection pooling efficiency.
- **Updated**: Track HTTP/2 stream statistics and connection reuse rates to optimize server configuration.
- **Updated**: Monitor llama.cpp embedding server performance including memory usage, GPU utilization, and embedding throughput for RAG operations.
- **Updated**: The centralized orchestrator provides comprehensive service status monitoring, automated cleanup on shutdown, and detailed error reporting with fix suggestions.
- **Updated**: Enhanced provider verification includes health checks, model validation, and smoke tests for improved observability.
- **Updated**: PostgreSQL database monitoring includes connection pool metrics, query performance, and table statistics for optimal database performance.
- **Updated**: Container health monitoring includes Docker Compose health checks and container resource utilization tracking.
- **Updated**: FastEmbed cache monitoring ensures proper model availability and cache hit rates for hybrid search operations.
- **Enhanced**: Monitor VK bot resource lifecycle including proper initialization and cleanup through loop_wrapper hooks for reliable resource management.

## Security Considerations
- Secrets management: Store all secrets in environment variables managed by pydantic-settings. Provide a template file with placeholders (.env.example) and never commit secrets.
- VK webhook security: Use secret and confirmation tokens; validate signatures and enforce HTTPS for webhook URLs.
- Network exposure: Restrict port exposure to internal networks; use reverse proxies with TLS termination.
- Least privilege: Run containers with non-root users and minimal capabilities; mount volumes with appropriate permissions.
- Backup and audit: Regularly snapshot Qdrant and MinIO; maintain audit trails for sensitive operations.
- **Updated**: Secure Hypercorn server with proper TLS configuration and HTTP/2 security headers for production deployments.
- **Updated**: Monitor HTTP/2 connections for security compliance and detect potential abuse patterns.
- **Updated**: Secure llama.cpp embedding server with proper network isolation and access controls for production deployments.
- **Updated**: The centralized orchestrator enforces ADMIN_API_KEY requirement, provides secure service coordination, and includes comprehensive error handling for security-related issues.
- **Updated**: Enhanced provider verification includes health checks and model validation to prevent deployment of compromised or incompatible models.
- **Updated**: PostgreSQL database security includes proper credential management, network isolation, and connection pooling with appropriate security settings.
- **Updated**: Container security includes non-root user execution, minimal base images, and proper volume permissions for production deployments.
- **Updated**: FastEmbed cache security ensures proper file permissions and access controls for cached model files.
- **Enhanced**: Event loop integration security ensures proper resource binding and prevents resource leakage or binding conflicts.

## Scaling Approaches
- Horizontal scaling: Run multiple replicas behind a load balancer; ensure stateless workers and shared storage/backends.
- Vertical scaling: Increase CPU/RAM for replicas and tune Qdrant shards and MinIO resources.
- Queueing: Offload heavy tasks (document ingestion) to background workers with retry policies.
- Caching: Cache frequently accessed KB articles and bot responses to reduce LLM calls.
- **Updated**: Scale Hypercorn instances horizontally for HTTP/2 multiplexing benefits; monitor stream concurrency across instances.
- **Updated**: Configure appropriate h2_max_concurrent_streams values based on workload characteristics and available resources.
- **Updated**: Scale llama.cpp embedding server horizontally if embedding workload exceeds single instance capacity; monitor embedding queue depth and processing latency.
- **Updated**: The modular deployment architecture enables independent scaling of LLM and embedding services based on workload characteristics.
- **Updated**: Enhanced error handling and verification capabilities enable more reliable scaling operations with automated failover and recovery.
- **Updated**: PostgreSQL database scaling includes connection pooling, read replicas, and proper indexing strategies for optimal performance under load.
- **Updated**: Container orchestration enables horizontal scaling of admin server and VK polling services with proper resource limits and health checks.
- **Updated**: FastEmbed cache scalability ensures efficient model serving across multiple container instances with shared cache management.
- **Enhanced**: Event loop integration enables proper resource sharing across scaled instances while maintaining resource lifecycle consistency.

## Production Deployment Playbooks

### Deploying VK Bot with Webhooks
- Prepare environment variables for VK webhook (tokens, confirmation, and webhook URL).
- Build and run the FastAPI service with Hypercorn in production mode.
- Configure reverse proxy (nginx/caddy) with TLS and rate limiting.
- Register VK webhook endpoint and confirm subscription.

**Section sources**
- [AGENTS.md:16-18](file://AGENTS.md#L16-L18)
- [PLAN.md:132-135](file://PLAN.md#L132-L135)

### Running Qdrant, MinIO, and PostgreSQL in Docker
- Use the provided compose file to start services with health checks and persistent volumes.
- Secure MinIO with strong credentials and restrict network access.
- Monitor Qdrant disk usage and configure backups.
- **Updated**: Configure PostgreSQL with proper credentials and volume mounting for persistent storage.
- **Updated**: Monitor PostgreSQL health using pg_isready and configure appropriate connection limits.
- **Updated**: The orchestrator includes comprehensive PostgreSQL health checking with retry mechanisms and detailed error reporting.
- **Updated**: Ensure FastEmbed cache is properly mounted and accessible for hybrid search operations.

**Section sources**
- [docker-compose.yml:1-53](file://docker-compose.yml#L1-L53)
- [scripts/run_admin.sh:52-70](file://scripts/run_admin.sh#L52-L70)

### Managing Secrets and Configuration
- Define canonical settings fields and load from .env using pydantic-settings.
- Provide .env.example with placeholders; never commit real secrets.
- Rotate secrets regularly and invalidate old keys after migration.
- **Updated**: Configure llamacpp provider settings including llm_provider='llamacpp', llm_base_url='http://localhost:8080', and embedding_model='qwen3-embedding'.
- **Updated**: Set up Hypercorn configuration with appropriate worker class and HTTP/2 settings for production deployment.
- **Updated**: Configure PostgreSQL database URL with asyncpg driver for production deployments.
- **Updated**: Configure hybrid search settings with retrieval_mode='hybrid' and sparse_embedding_model='Qdrant/bm25'.
- **Updated**: The centralized orchestrator manages provider-specific configurations, ensures proper model setup, and includes comprehensive error handling.
- **Updated**: Enhanced error handling includes detailed fix suggestions and automated recovery procedures for common configuration issues.

**Section sources**
- [app/config.py:15-62](file://app/config.py#L15-L62)
- [AGENTS.md:20-50](file://AGENTS.md#L20-L50)
- [scripts/admin_server.py:55-68](file://scripts/admin_server.py#L55-L68)
- [scripts/run_admin.sh:100-181](file://scripts/run_admin.sh#L100-L181)

### Handling Operational Tasks
- Log rotation: Configure logrotate or container logging driver with max-size and max-file.
- Backups: Snapshot Qdrant storage and MinIO buckets; automate and test restore procedures.
- Maintenance windows: Schedule updates during low-traffic periods; use blue/green deployments.
- **Updated**: Monitor and manage Hypercorn server lifecycle, including automatic restarts, HTTP/2 connection monitoring, and worker class optimization.
- **Updated**: Monitor and manage llama.cpp embedding server lifecycle, including automatic restarts, resource monitoring, and model verification.
- **Updated**: Monitor and manage PostgreSQL database lifecycle, including connection pool monitoring, backup procedures, and performance tuning.
- **Updated**: The centralized orchestrator provides automated cleanup, graceful shutdown procedures, and comprehensive error handling for operational tasks.
- **Updated**: Enhanced provider verification includes health checks, model validation, and automated recovery procedures for improved operational reliability.
- **Updated**: Monitor FastEmbed cache health and ensure proper cache synchronization across container instances.
- **Enhanced**: Monitor VK bot resource lifecycle through loop_wrapper hooks for proper initialization and cleanup across all deployment modes.

### Centralized Orchestrator Deployment
- Install prerequisites: Docker, uv, and Python 3.11+.
- Configure .env file with required settings including ADMIN_API_KEY.
- Run the centralized orchestrator: `./scripts/run_admin.sh`.
- The orchestrator will handle provider selection, dependency management, infrastructure provisioning, service coordination, PostgreSQL health checking, and comprehensive error handling.

**Updated**: The centralized orchestrator now includes enhanced error handling with detailed fix suggestions, comprehensive health checks including PostgreSQL readiness, automated model verification, and robust cleanup procedures for reliable production operations.

**Section sources**
- [scripts/run_admin.sh:69-98](file://scripts/run_admin.sh#L69-L98)
- [scripts/run_admin.sh:183-200](file://scripts/run_admin.sh#L183-L200)
- [scripts/run_admin.sh:202-221](file://scripts/run_admin.sh#L202-L221)
- [scripts/run_admin.sh:275-281](file://scripts/run_admin.sh#L275-L281)
- [scripts/run_admin.sh:365-385](file://scripts/run_admin.sh#L365-L385)

### Enhanced Error Handling and Verification Procedures
- Implement comprehensive error handling with detailed fix suggestions for common deployment issues.
- Configure health checks for all services with appropriate retry mechanisms and timeouts.
- Set up automated model verification for Ollama and llama.cpp providers.
- Establish monitoring and alerting for critical system components.
- **Updated**: The orchestrator now includes enhanced error handling with detailed fix suggestions, comprehensive health checks including PostgreSQL readiness, and automated recovery procedures.
- **Updated**: Provider verification includes health checks, model validation, and smoke tests for improved reliability.
- **Updated**: Automated model downloading capabilities eliminate manual intervention and reduce deployment downtime.
- **Updated**: PostgreSQL health checking includes detailed error reporting with fix suggestions and integration with Docker Compose services.
- **Updated**: FastEmbed cache verification ensures proper model availability and cache integrity.
- **Enhanced**: Event loop integration error handling ensures proper resource lifecycle management and prevents resource binding conflicts.

**Section sources**
- [scripts/run_admin.sh:243-321](file://scripts/run_admin.sh#L243-L321)
- [scripts/run_admin.sh:323-347](file://scripts/run_admin.sh#L323-L347)
- [scripts/run_ollama_embeddings.sh:26-73](file://scripts/run_ollama_embeddings.sh#L26-L73)
- [scripts/run_ollama_llm.sh:26-74](file://scripts/run_ollama_llm.sh#L26-L74)
- [scripts/run_llama_embeddings.sh:39-77](file://scripts/run_llama_embeddings.sh#L39-L77)
- [scripts/run_llama_llm.sh:39-75](file://scripts/run_llama_llm.sh#L39-L75)

### Hypercorn Server Configuration
- Install Hypercorn as the production ASGI server (version >= 0.18.0).
- Configure worker class as "asyncio" for optimal HTTP/2 performance.
- Set h2_max_concurrent_streams to control HTTP/2 stream concurrency (default: 100).
- Use asyncio event loop for better performance with HTTP/2 multiplexing.
- Monitor server performance and adjust configuration based on workload characteristics.

**Section sources**
- [pyproject.toml:9](file://pyproject.toml#L9)
- [scripts/admin_server.py:55-68](file://scripts/admin_server.py#L55-L68)

### Enhanced Modular Llama.cpp Deployment
- Install llama.cpp and ensure llama-server binary is available in PATH.
- Use specialized scripts for LLM and embedding servers:
  - LLM inference: `./scripts/run_llama_llm.sh`
  - Embedding: `./scripts/run_llama_embeddings.sh`
- Configure HOST, PORT, CTX_SIZE, N_GPU_LAYERS, and THREADS environment variables as needed.
- Start servers with optimized flags for their specific roles.
- **Updated**: The scripts now include automated model downloading with curl/wget fallback support, progress indicators, and comprehensive error handling.
- **Updated**: Enhanced verification includes model validation and smoke tests for improved reliability.

**Section sources**
- [scripts/run_llama_llm.sh:1-75](file://scripts/run_llama_llm.sh#L1-L75)
- [scripts/run_llama_embeddings.sh:1-77](file://scripts/run_llama_embeddings.sh#L1-L77)

### Enhanced Modular Ollama Deployment
- Install Ollama and ensure it's available in PATH.
- Use specialized scripts for LLM and embedding servers:
  - LLM inference: `./scripts/run_ollama_llm.sh`
  - Embedding: `./scripts/run_ollama_embeddings.sh`
- The scripts automatically handle model pulling, verification, and comprehensive error handling.
- Configure OLLAMA_HOST environment variable if using a different host/port.
- **Updated**: The scripts now include comprehensive health checks, model verification, and detailed error reporting with fix suggestions.
- **Updated**: Enhanced verification includes model validation and smoke tests for improved reliability.

**Section sources**
- [scripts/run_ollama_llm.sh:1-74](file://scripts/run_ollama_llm.sh#L1-L74)
- [scripts/run_ollama_embeddings.sh:1-73](file://scripts/run_ollama_embeddings.sh#L1-L73)

### PostgreSQL Database Deployment and Management
- Configure PostgreSQL service in Docker Compose with proper environment variables and volume mounting.
- Set up database credentials and ensure proper network isolation.
- Monitor PostgreSQL health using pg_isready and configure appropriate connection limits.
- **Updated**: The orchestrator includes comprehensive PostgreSQL health checking with retry mechanisms and detailed error reporting.
- **Updated**: Database initialization includes proper table creation for documents and category_files with unique indexing.
- **Updated**: Connection management uses asyncpg driver for production deployments with proper connection pooling.

**Section sources**
- [docker-compose.yml:30-47](file://docker-compose.yml#L30-L47)
- [app/storage/database.py:11-58](file://app/storage/database.py#L11-L58)
- [app/resources.py:208-252](file://app/resources.py#L208-L252)
- [scripts/run_admin.sh:52-70](file://scripts/run_admin.sh#L52-L70)

### Enhanced VK Bot Resource Management Deployment
- Ensure proper event loop integration through loop_wrapper.on_startup/on_shutdown hooks.
- Configure resource initialization with build_resources() for consistent resource lifecycle.
- Implement proper cleanup through close_resources() on shutdown.
- Monitor resource binding and lifecycle across all deployment modes.
- **Updated**: The VK bot now properly integrates with vkbottle's loop_wrapper system for event loop management.
- **Updated**: Resource initialization ensures all resources bind to the same event loop that handlers will use.
- **Updated**: Graceful shutdown through proper cleanup procedures prevents resource leaks.
- **Updated**: Enhanced monitoring of resource lifecycle through loop_wrapper hooks for reliable operations.

**Section sources**
- [scripts/polling_vk.py:23-73](file://scripts/polling_vk.py#L23-L73)
- [app/resources.py:130-316](file://app/resources.py#L130-L316)
- [app/resources.py:319-365](file://app/resources.py#L319-L365)

### Containerization and Docker Support

#### Multi-Stage Docker Builds with Pre-downloaded FastEmbed Cache
The project implements comprehensive containerization support through multi-stage Docker builds that optimize image size and security:

**Admin Server Container (Dockerfile.admin)**
- Builder stage: Uses uv package manager for efficient dependency installation
- Runtime stage: Minimal Python slim image with non-root user execution
- Optimized layers: Dependency caching, test file removal, and cache cleanup
- Environment configuration: Automatic BIND_HOST=0.0.0.0 for container networking
- **Updated**: Pre-downloaded FastEmbed sparse embeddings cache for hybrid search support

**VK Polling Container (Dockerfile.polling_vk)**
- Identical multi-stage build process optimized for development use
- Single CMD instruction for long-polling bot execution
- Non-root user execution for security compliance
- **Updated**: Pre-downloaded FastEmbed sparse embeddings cache for hybrid search support

```mermaid
flowchart TD
Builder["Builder Stage<br/>python:3.13-slim"] --> UVCopy["Copy uv binary<br/>/uv /uvx /bin/"]
UVCopy --> EnvVars["Set uv environment<br/>variables"]
EnvVars --> WorkDir["Set working directory<br/>/app"]
WorkDir --> DepFiles["Copy dependency files<br/>pyproject.toml uv.lock"]
DepFiles --> UvSync["uv sync --locked --no-dev<br/>Install production deps"]
UvSync --> AppCopy["Copy application code<br/>app/, scripts/, templates/"]
AppCopy --> PreDownload["Pre-download FastEmbed Model<br/>FastEmbedSparse(model_name='Qdrant/bm25')"]
PreDownload --> CachePath["Set FASTEMBED_CACHE_PATH<br/>/app/.cache/fastembed"]
CachePath --> Cleanup["Remove test files & caches<br/>Reduce image size"]
Cleanup --> Runtime["Runtime Stage<br/>python:3.13-slim"]
Runtime --> UserSetup["Create non-root user<br/>appuser"]
UserSetup --> CopyArtifacts["Copy virtual env & app<br/>from builder stage"]
CopyArtifacts --> CopyCache["Copy FastEmbed cache<br/>to runtime"]
CopyCache --> PathConfig["Set PATH to .venv/bin"]
PathConfig --> HostConfig["Set BIND_HOST=0.0.0.0<br/>for container networking"]
HostConfig --> UserExec["Switch to non-root user"]
UserExec --> PortExpose["Expose port 8000"]
PortExpose --> CmdExec["Execute CMD<br/>python scripts/admin_server.py"]
```

**Diagram sources**
- [Dockerfile.admin:1-77](file://Dockerfile.admin#L1-L77)

**Section sources**
- [Dockerfile.admin:1-77](file://Dockerfile.admin#L1-L77)
- [Dockerfile.polling_vk:1-71](file://Dockerfile.polling_vk#L1-L71)

#### Docker Compose Infrastructure
The docker-compose.yml defines three core services with comprehensive health checking and persistent storage:

**Qdrant Vector Database**
- Image: qdrant/qdrant:latest
- Ports: 6333 (API), 6334 (gRPC)
- Health check: HTTP GET to /healthz endpoint
- Persistent storage: qdrant_storage volume

**MinIO Object Storage**
- Image: minio/minio
- Command: server /data --console-address ":9001"
- Ports: 9000 (S3 API), 9001 (web console)
- Credentials: minioadmin/minioadmin
- Persistent storage: minio_data volume

**PostgreSQL Database**
- Image: postgres:16-alpine
- Ports: 5432
- Environment: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
- Health check: pg_isready command
- Persistent storage: pg_data volume

**Section sources**
- [docker-compose.yml:1-53](file://docker-compose.yml#L1-L53)

#### Environment Variable Configuration
Containerized deployments use environment variables loaded from .env files:

**Admin Server Environment Variables**
- ADMIN_API_KEY: Required for admin authentication
- DATABASE_URL: PostgreSQL connection string
- QDRANT_URL: Vector database endpoint
- S3_ENDPOINT_URL: Object storage endpoint
- LLM_PROVIDER/EMBEDDING_PROVIDER: Model provider selection
- BIND_HOST: Container bind address (automatically set to 0.0.0.0)
- **Updated**: FASTEMBED_CACHE_PATH: FastEmbed cache directory path

**Container Networking**
- Docker Compose creates a default network for service communication
- Services communicate using service names as hostnames
- Port mapping enables external access to admin server (8000:8000)
- **Updated**: Service discovery guidance for connecting to Qdrant, MinIO, and PostgreSQL using their container names

**Section sources**
- [app/config.py:37-46](file://app/config.py#L37-L46)
- [scripts/admin_server.py:6-20](file://scripts/admin_server.py#L6-L20)
- [README.md:241-252](file://README.md#L241-L252)

#### Docker Ignore Configuration
The .dockerignore file excludes unnecessary files and directories from container images:
- Python cache files (__pycache__, *.pyc)
- Git and IDE metadata
- Test files and models directory
- Documentation files
- Lock files backup

**Section sources**
- [.dockerignore:1-17](file://.dockerignore#L1-L17)

#### Production Deployment Examples
**Building Containers**
```bash
# Admin panel container
docker build -f Dockerfile.admin -t cafetera-admin .

# VK polling container  
docker build -f Dockerfile.polling_vk -t cafetera-polling-vk .
```

**Running Containers**
```bash
# Admin panel (accessible on localhost:8000)
docker run --rm --env-file .env -p 8000:8000 cafetera-admin

# VK polling bot
docker run --rm --env-file .env cafetera-polling-vk
```

**Connecting to External Services**
```bash
# Connect to services started by docker compose
docker run --rm --env-file .env --network cafetera_default -p 8000:8000 cafetera-admin
```

**Updated**: Service discovery examples showing how to connect to Qdrant, MinIO, and PostgreSQL using their container names instead of localhost.

**Section sources**
- [README.md:217-252](file://README.md#L217-L252)

## Troubleshooting Guide
- VK webhook not responding:
  - Verify secret and confirmation tokens match VK settings.
  - Confirm HTTPS endpoint is reachable and TLS certificate is valid.
  - Check FastAPI logs for incoming webhook events and error responses.
- Long polling fails locally:
  - Ensure VK access token is set in environment.
  - Confirm script runs from project root and imports are resolvable.
  - **Enhanced**: Verify loop_wrapper.on_startup/on_shutdown hooks are properly registered.
  - **Enhanced**: Check that resources are properly bound to the event loop.
- Qdrant or MinIO unhealthy:
  - Review health check endpoints and logs.
  - Check volume mounts and disk space.
  - Verify Docker Compose health checks are functioning properly.
- Slow responses:
  - Profile vector search and LLM calls; optimize prompts and chunk sizes.
- **Updated**: Hypercorn HTTP/2 connection issues:
  - Verify Hypercorn version >= 0.18.0 is installed.
  - Check worker class configuration (should be "asyncio").
  - Monitor h2_max_concurrent_streams setting for optimal performance.
  - Review HTTP/2 connection logs for protocol-level errors.
- **Updated**: Llama.cpp embedding server issues:
  - Verify llama-server binary is available in PATH.
  - Check model file exists at specified MODEL_PATH or default location.
  - Monitor server logs for embedding initialization errors.
  - Ensure sufficient memory allocation for embedding operations.
  - Verify --embedding and --pooling mean flags are properly configured.
  - Check automated model download logs for download failures.
- **Updated**: Centralized orchestrator issues:
  - Check prerequisite installation (docker, uv).
  - Verify .env file exists and contains required settings.
  - Review orchestrator logs for detailed error messages with fix suggestions.
  - Ensure proper provider selection and dependency installation.
  - Check automated cleanup procedures for proper shutdown.
  - **Updated**: Verify PostgreSQL health checking is functioning properly.
- **Updated**: Enhanced provider-specific deployment issues:
  - For Ollama: Verify server is running and models are properly pulled with verification.
  - For llama.cpp: Check model file downloads and server startup logs.
  - Ensure separate LLM and embedding servers are properly configured.
  - Verify automated model verification and health checks are functioning.
- **Updated**: Automated model downloading failures:
  - Check curl/wget availability for model downloads.
  - Verify network connectivity to model repositories.
  - Check disk space for model storage.
  - Review download logs for specific error messages.
- **Updated**: PostgreSQL database issues:
  - Verify PostgreSQL service is running and accessible.
  - Check database credentials and connection URL format.
  - Monitor PostgreSQL logs for initialization errors.
  - Verify table creation and indexing completed successfully.
  - Check connection pool configuration and limits.
  - Review database backup and recovery procedures.
- **Updated**: Containerization issues:
  - Verify Docker daemon is running and accessible.
  - Check Docker image build logs for dependency installation errors.
  - Ensure .env file is properly formatted and accessible to containers.
  - Verify network connectivity between containers and external services.
  - Check container resource limits and available system resources.
  - Review Docker Compose logs for service startup failures.
  - **Updated**: Verify FastEmbed cache is properly mounted and accessible.
  - **Updated**: Check that pre-downloaded FastEmbed models are available in the cache directory.
  - **Updated**: Ensure cleanup optimizations haven't removed necessary cache files.
- **Enhanced**: VK bot resource management issues:
  - Verify loop_wrapper.on_startup/on_shutdown hooks are properly registered.
  - Check that _setup() coroutine is properly awaited during initialization.
  - Verify that _cleanup() coroutine executes during shutdown.
  - Ensure resources are stored on bot._app_resources for proper cleanup access.
  - Monitor resource binding to event loop for proper lifecycle management.

**Section sources**
- [scripts/polling_vk.py:17-73](file://scripts/polling_vk.py#L17-L73)
- [docker-compose.yml:11-16](file://docker-compose.yml#L11-L16)
- [AGENTS.md:16-18](file://AGENTS.md#L16-L18)
- [scripts/run_llama_embeddings.sh:39-77](file://scripts/run_llama_embeddings.sh#L39-L77)
- [scripts/run_ollama_embeddings.sh:26-73](file://scripts/run_ollama_embeddings.sh#L26-L73)
- [scripts/admin_server.py:55-68](file://scripts/admin_server.py#L55-L68)
- [scripts/run_admin.sh:69-98](file://scripts/run_admin.sh#L69-L98)
- [scripts/run_admin.sh:52-70](file://scripts/run_admin.sh#L52-L70)
- [Dockerfile.admin:1-77](file://Dockerfile.admin#L1-L77)
- [Dockerfile.polling_vk:1-71](file://Dockerfile.polling_vk#L1-L71)
- [app/resources.py:130-316](file://app/resources.py#L130-L316)
- [app/resources.py:319-365](file://app/resources.py#L319-L365)

## Conclusion
cafetera_hr_bot is designed for production-grade operations with a clear separation between VK bot orchestration, RAG infrastructure, and storage. The system now features a centralized orchestration approach through run_admin.sh that manages provider selection, dependency installation, infrastructure provisioning, service coordination, PostgreSQL database initialization, and comprehensive error handling. The system supports multiple LLM providers including llama.cpp with optimized embedding capabilities for enhanced RAG functionality. The production server utilizes Hypercorn with HTTP/2 support, providing improved performance and modern protocol features compared to traditional ASGI servers. The modular deployment architecture enables flexible and maintainable configurations for different provider setups. The PostgreSQL database integration provides persistent storage for document metadata with proper table creation and indexing. **Updated**: Comprehensive Docker containerization support enables production-ready deployments with multi-stage builds, optimized runtime images, secure non-root execution, pre-downloaded FastEmbed sparse embeddings cache, and enhanced cleanup optimizations. The containerization layer includes uv package manager integration, environment variable management, Docker Compose orchestration, and comprehensive service discovery guidance. **Enhanced**: The VK bot startup process now features improved resource management with proper event loop integration using loop_wrapper.on_startup/on_shutdown hooks, ensuring all resources bind to the same event loop that handlers will use for optimal performance and resource lifecycle management. By adopting webhook-based transport, securing secrets, monitoring health, implementing robust scaling and backup strategies, properly managing the llama.cpp embedding server with automated model downloading, optimizing Hypercorn HTTP/2 configuration, implementing comprehensive PostgreSQL database management, leveraging containerized infrastructure with proper networking and security practices, utilizing pre-downloaded FastEmbed cache for improved performance, and implementing proper event loop integration for reliable resource management, teams can operate the bot reliably in production while preparing for future Telegram integration and advanced webhook deployments.