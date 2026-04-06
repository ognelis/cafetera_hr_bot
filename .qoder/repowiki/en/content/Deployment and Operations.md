# Deployment and Operations

<cite>
**Referenced Files in This Document**
- [docker-compose.yml](file://docker-compose.yml)
- [pyproject.toml](file://pyproject.toml)
- [app/config.py](file://app/config.py)
- [app/main.py](file://app/main.py)
- [scripts/admin_server.py](file://scripts/admin_server.py)
- [scripts/polling_vk.py](file://scripts/polling_vk.py)
- [scripts/run_llama_qwen.sh](file://scripts/run_llama_qwen.sh)
- [scripts/run_ollama_qwen.sh](file://scripts/run_ollama_qwen.sh)
- [app/integrations/vk/bot.py](file://app/integrations/vk/bot.py)
- [app/integrations/vk/handlers/start.py](file://app/integrations/vk/handlers/start.py)
- [app/integrations/vk/states.py](file://app/integrations/vk/states.py)
- [app/rag/retriever.py](file://app/rag/retriever.py)
- [app/rag/chain.py](file://app/rag/chain.py)
- [app/rag/indexer.py](file://app/rag/indexer.py)
- [app/rag/parser.py](file://app/rag/parser.py)
- [AGENTS.md](file://AGENTS.md)
- [PLAN.md](file://PLAN.md)
</cite>

## Update Summary
**Changes Made**
- Updated HTTP/2 support implementation documentation with Hypercorn replacement of Uvicorn
- Added Hypercorn server configuration details including worker classes and HTTP/2 max concurrent streams
- Updated production deployment considerations to reflect HTTP/2 enabled server configuration
- Enhanced monitoring and logging strategies for HTTP/2 performance metrics
- Updated dependency analysis to reflect Hypercorn as the production ASGI server

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
12. [Troubleshooting Guide](#troubleshooting-guide)
13. [Conclusion](#conclusion)

## Introduction
This document provides comprehensive guidance for deploying and operating cafetera_hr_bot in production. It covers containerized infrastructure using Docker Compose, operational controls for VK bot long-polling versus webhook-based production operation, planned Telegram integration, and future webhook deployment. The system now supports multiple LLM providers including llama.cpp with optimized embedding capabilities crucial for Retrieval-Augmented Generation (RAG) functionality. The production server now utilizes Hypercorn with HTTP/2 support, replacing Uvicorn for improved performance and modern protocol support. It also documents monitoring and logging strategies, secrets management, scaling approaches, performance optimization, disaster recovery planning, and practical deployment playbooks.

## Project Structure
The repository organizes runtime concerns into layered modules:
- Integrations: VK bot adapter and handlers
- Domain: States and navigation helpers
- Config: Pydantic-based settings loader with multiple LLM provider support
- Scripts: Local development entry-points including llama.cpp and Ollama deployment scripts
- Infrastructure: Docker Compose services for Qdrant and MinIO

```mermaid
graph TB
subgraph "Runtime"
VKBot["VK Bot Adapter<br/>app/integrations/vk/bot.py"]
Handlers["Handlers<br/>app/integrations/vk/handlers/*"]
States["States<br/>app/integrations/vk/states.py"]
Config["Settings Loader<br/>app/config.py"]
Embeddings["Embedding Models<br/>app/rag/retriever.py"]
Hypercorn["Hypercorn Server<br/>scripts/admin_server.py"]
end
subgraph "Infrastructure"
Qdrant["Qdrant Vector DB<br/>docker-compose.yml"]
MinIO["MinIO Object Storage<br/>docker-compose.yml"]
LlamaServer["llama.cpp Server<br/>scripts/run_llama_qwen.sh"]
OllamaServer["Ollama Server<br/>scripts/run_ollama_qwen.sh"]
end
subgraph "Operations"
DevPoll["Dev Long Poll Script<br/>scripts/polling_vk.py"]
Compose["Docker Compose<br/>docker-compose.yml"]
Env["Environment Variables<br/>.env"]
end
VKBot --> Handlers
VKBot --> States
VKBot --> Config
Handlers --> States
Embeddings --> Qdrant
Config --> Env
LlamaServer --> Embeddings
OllamaServer --> Embeddings
Compose --> Qdrant
Compose --> MinIO
Hypercorn --> VKBot
```

**Diagram sources**
- [app/integrations/vk/bot.py:1-56](file://app/integrations/vk/bot.py#L1-L56)
- [app/integrations/vk/handlers/start.py:1-55](file://app/integrations/vk/handlers/start.py#L1-L55)
- [app/integrations/vk/states.py:1-14](file://app/integrations/vk/states.py#L1-L14)
- [app/config.py:1-33](file://app/config.py#L1-L33)
- [app/rag/retriever.py:1-103](file://app/rag/retriever.py#L1-L103)
- [scripts/polling_vk.py:1-38](file://scripts/polling_vk.py#L1-L38)
- [scripts/run_llama_qwen.sh:1-61](file://scripts/run_llama_qwen.sh#L1-L61)
- [scripts/run_ollama_qwen.sh:1-74](file://scripts/run_ollama_qwen.sh#L1-L74)
- [docker-compose.yml:1-34](file://docker-compose.yml#L1-L34)
- [scripts/admin_server.py:1-74](file://scripts/admin_server.py#L1-L74)

**Section sources**
- [docker-compose.yml:1-34](file://docker-compose.yml#L1-L34)
- [pyproject.toml:1-62](file://pyproject.toml#L1-L62)
- [app/config.py:1-33](file://app/config.py#L1-L33)
- [scripts/polling_vk.py:1-38](file://scripts/polling_vk.py#L1-L38)
- [scripts/run_llama_qwen.sh:1-61](file://scripts/run_llama_qwen.sh#L1-L61)
- [scripts/run_ollama_qwen.sh:1-74](file://scripts/run_ollama_qwen.sh#L1-L74)
- [app/integrations/vk/bot.py:1-56](file://app/integrations/vk/bot.py#L1-L56)
- [app/integrations/vk/handlers/start.py:1-55](file://app/integrations/vk/handlers/start.py#L1-L55)
- [app/integrations/vk/states.py:1-14](file://app/integrations/vk/states.py#L1-L14)
- [app/rag/retriever.py:1-103](file://app/rag/retriever.py#L1-L103)
- [scripts/admin_server.py:1-74](file://scripts/admin_server.py#L1-L74)
- [AGENTS.md:1-88](file://AGENTS.md#L1-L88)
- [PLAN.md:1-207](file://PLAN.md#L1-L207)

## Core Components
- VK Bot Adapter: Creates a fully wired vkbottle Bot with registered labelers and logging.
- Handlers: Start/main menu/navigation and fallback handlers.
- States: Multi-step dialog states for HR request scenario.
- Config: Pydantic Settings with environment file support and multiple LLM provider configuration.
- Dev Long Poll Script: Local development entry-point for VK bot using long polling.
- Hypercorn Server: Production-grade ASGI server with HTTP/2 support and configurable worker classes.
- Llama.cpp Deployment Script: Optimized llama-server deployment with embedding capabilities for RAG systems.
- Ollama Deployment Script: Automated Ollama server management and model provisioning.

Operational highlights:
- Production mode requires webhook transport via FastAPI lifespan (not long polling).
- VK webhook requires secret and confirmation tokens plus a webhook URL.
- Telegram integration is post-MVP and will use aiogram with webhook.
- Multiple LLM providers supported: Ollama, OpenAI-compatible, and llama.cpp with optimized embedding flags.
- **Updated**: Production server uses Hypercorn with HTTP/2 support and configurable max concurrent streams for improved performance.

**Section sources**
- [app/integrations/vk/bot.py:24-56](file://app/integrations/vk/bot.py#L24-L56)
- [app/integrations/vk/handlers/start.py:23-55](file://app/integrations/vk/handlers/start.py#L23-L55)
- [app/integrations/vk/states.py:4-14](file://app/integrations/vk/states.py#L4-L14)
- [app/config.py:15-33](file://app/config.py#L15-L33)
- [scripts/polling_vk.py:25-38](file://scripts/polling_vk.py#L25-L38)
- [scripts/admin_server.py:55-68](file://scripts/admin_server.py#L55-L68)
- [scripts/run_llama_qwen.sh:52-60](file://scripts/run_llama_qwen.sh#L52-L60)
- [scripts/run_ollama_qwen.sh:12-24](file://scripts/run_ollama_qwen.sh#L12-L24)
- [AGENTS.md:16-18](file://AGENTS.md#L16-L18)
- [PLAN.md:132-135](file://PLAN.md#L132-L135)

## Architecture Overview
The system runs a VK bot with optional RAG capabilities backed by Qdrant and MinIO. The RAG system supports multiple embedding providers including llama.cpp with optimized server flags for document embedding tasks. In production, the VK bot operates via FastAPI webhook transport with Hypercorn server supporting HTTP/2; long polling is for local development only.

```mermaid
graph TB
Client["VK Client"]
Webhook["FastAPI Webhook Endpoint<br/>Production Transport"]
Bot["VK Bot<br/>app/integrations/vk/bot.py"]
Handlers["Handlers<br/>start/sections/fallback"]
States["States<br/>HR request dialogs"]
Config["Settings<br/>app/config.py"]
Qdrant["Qdrant Vector DB"]
MinIO["MinIO Object Storage"]
Embeddings["Embedding Models<br/>llama.cpp/Ollama"]
LlamaServer["llama.cpp Server<br/>--embedding --pooling mean"]
OllamaServer["Ollama Server"]
Hypercorn["Hypercorn Server<br/>HTTP/2 Enabled"]
Client --> Webhook
Webhook --> Bot
Bot --> Handlers
Bot --> States
Bot --> Config
Handlers --> States
Config --> Qdrant
Config --> MinIO
Embeddings --> Qdrant
LlamaServer --> Embeddings
OllamaServer --> Embeddings
Hypercorn --> Webhook
```

**Diagram sources**
- [app/integrations/vk/bot.py:24-56](file://app/integrations/vk/bot.py#L24-L56)
- [app/integrations/vk/handlers/start.py:23-55](file://app/integrations/vk/handlers/start.py#L23-L55)
- [app/integrations/vk/states.py:4-14](file://app/integrations/vk/states.py#L4-L14)
- [app/config.py:15-33](file://app/config.py#L15-L33)
- [docker-compose.yml:2-34](file://docker-compose.yml#L2-L34)
- [scripts/run_llama_qwen.sh:52-60](file://scripts/run_llama_qwen.sh#L52-L60)
- [app/rag/retriever.py:22-62](file://app/rag/retriever.py#L22-L62)
- [scripts/admin_server.py:55-68](file://scripts/admin_server.py#L55-L68)

**Section sources**
- [AGENTS.md:16-18](file://AGENTS.md#L16-L18)
- [PLAN.md:132-135](file://PLAN.md#L132-L135)
- [docker-compose.yml:2-34](file://docker-compose.yml#L2-L34)
- [scripts/run_llama_qwen.sh:52-60](file://scripts/run_llama_qwen.sh#L52-L60)
- [app/rag/retriever.py:22-62](file://app/rag/retriever.py#L22-L62)
- [scripts/admin_server.py:55-68](file://scripts/admin_server.py#L55-L68)

## Detailed Component Analysis

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
}
BotFactory --> VKBot : "creates"
VKBot --> Handlers : "loads labelers"
VKBot --> States : "uses"
BotFactory --> Settings : "reads"
```

**Diagram sources**
- [app/integrations/vk/bot.py:24-56](file://app/integrations/vk/bot.py#L24-L56)
- [app/integrations/vk/handlers/start.py:12-55](file://app/integrations/vk/handlers/start.py#L12-L55)
- [app/integrations/vk/states.py:4-14](file://app/integrations/vk/states.py#L4-L14)
- [app/config.py:15-33](file://app/config.py#L15-L33)

**Section sources**
- [app/integrations/vk/bot.py:14-56](file://app/integrations/vk/bot.py#L14-L56)
- [app/integrations/vk/handlers/start.py:12-55](file://app/integrations/vk/handlers/start.py#L12-L55)
- [app/integrations/vk/states.py:4-14](file://app/integrations/vk/states.py#L4-L14)
- [app/config.py:15-33](file://app/config.py#L15-L33)

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

### Llama.cpp Embedding Server Deployment
The llama.cpp deployment script provides optimized server configuration for RAG systems with specialized embedding capabilities.

```mermaid
flowchart TD
Start(["run_llama_qwen.sh"]) --> CheckServer["Check llama-server availability"]
CheckServer --> CheckModel["Verify model file exists"]
CheckModel --> DetectCPU["Detect CPU count automatically"]
DetectCPU --> StartServer["Start llama-server with optimized flags"]
StartServer --> EmbeddingFlag["--embedding flag enabled"]
StartServer --> PoolingMean["--pooling mean for document embeddings"]
StartServer --> OptimizeParams["Optimized ctx-size, threads, gpu layers"]
OptimizeParams --> Ready(["Ready for RAG operations"])
EmbeddingFlag --> Ready
PoolingMean --> Ready
```

**Diagram sources**
- [scripts/run_llama_qwen.sh:32-60](file://scripts/run_llama_qwen.sh#L32-L60)

**Section sources**
- [scripts/run_llama_qwen.sh:1-61](file://scripts/run_llama_qwen.sh#L1-L61)

### LLM Provider Configuration and Embedding Selection
The system supports multiple LLM providers with automatic embedding model selection based on configuration.

```mermaid
classDiagram
class Settings {
+llm_provider : string
+embedding_model : string
+llm_base_url : string
+llm_api_key : string
}
class EmbeddingFactory {
+build_embeddings(settings) Embeddings
}
class LlamaCppProvider {
+OpenAIEmbeddings with llama.cpp
+Custom base_url http : //localhost : 8080/v1
}
class OllamaProvider {
+OllamaEmbeddings with custom base_url
}
class OpenAIProvider {
+OpenAIEmbeddings with API key
}
Settings --> EmbeddingFactory : "provides config"
EmbeddingFactory --> LlamaCppProvider : "when llm_provider='llamacpp'"
EmbeddingFactory --> OllamaProvider : "when llm_provider='ollama'"
EmbeddingFactory --> OpenAIProvider : "when llm_provider='openai'"
```

**Diagram sources**
- [app/config.py:15-33](file://app/config.py#L15-L33)
- [app/rag/retriever.py:22-62](file://app/rag/retriever.py#L22-L62)

**Section sources**
- [app/config.py:15-33](file://app/config.py#L15-L33)
- [app/rag/retriever.py:22-62](file://app/rag/retriever.py#L22-L62)

### VK Long Polling Development Flow
Local development uses a script that loads settings and starts the VK bot in long-polling mode.

```mermaid
sequenceDiagram
participant Dev as "Developer"
participant Script as "scripts/polling_vk.py"
participant Config as "app/config.py"
participant Bot as "app/integrations/vk/bot.py"
Dev->>Script : "Run long poll"
Script->>Config : "Load settings"
Script->>Bot : "create_bot(settings)"
Bot-->>Script : "Bot instance"
Script->>Bot : "run_forever()"
Note over Script,Bot : "Long polling loop for VK updates"
```

**Diagram sources**
- [scripts/polling_vk.py:25-38](file://scripts/polling_vk.py#L25-L38)
- [app/config.py:15-33](file://app/config.py#L15-L33)
- [app/integrations/vk/bot.py:24-56](file://app/integrations/vk/bot.py#L24-L56)

**Section sources**
- [scripts/polling_vk.py:1-38](file://scripts/polling_vk.py#L1-L38)
- [app/config.py:15-33](file://app/config.py#L15-L33)
- [app/integrations/vk/bot.py:24-56](file://app/integrations/vk/bot.py#L24-L56)

### Containerized Infrastructure Setup
Docker Compose provisions Qdrant and MinIO with health checks and persistent volumes.

```mermaid
flowchart TD
Start(["Compose Up"]) --> Services["Start qdrant and minio"]
Services --> Health["Health checks enabled"]
Health --> Ports["Expose ports:<br/>Qdrant 6333,6334<br/>MinIO 9000,9001"]
Ports --> Volumes["Bind volumes:<br/>qdrant_storage<br/>minio_data"]
Volumes --> Ready(["Infra Ready"])
```

**Diagram sources**
- [docker-compose.yml:2-34](file://docker-compose.yml#L2-L34)

**Section sources**
- [docker-compose.yml:1-34](file://docker-compose.yml#L1-L34)

## Dependency Analysis
External dependencies include FastAPI, Hypercorn, LangChain stack, Qdrant client, VK and Telegram adapters, and testing tools. Optional extras enable Ollama or OpenAI-compatible LLMs. The system now supports llama.cpp with optimized embedding server flags and uses Hypercorn as the production ASGI server instead of Uvicorn.

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
App --> FastAPI
App --> Hypercorn
App --> LangChain
App --> QdrantClient
App --> VK
App --> Telegram
App --> Tests
App --> LlamaCpp
App --> Ollama
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
- **Updated**: Configure llama.cpp embedding server with optimized flags (--embedding and --pooling mean) for efficient document embedding tasks in RAG systems.
- **Updated**: Monitor llama.cpp server resource utilization and embedding performance metrics for optimal RAG system operation.

## Monitoring and Logging
- Logging: Configure structured logging at INFO level for operational visibility. Use consistent log formatting and include correlation IDs where applicable.
- Health checks: Leverage Qdrant's health endpoint and MinIO console for availability monitoring.
- Metrics: Expose Prometheus metrics via FastAPI middleware and scrape with Prometheus.
- Alerting: Forward logs to centralized logging (e.g., ELK or Loki) and set alerts for error spikes and slow response times.
- Log rotation: Use OS-native log rotation (logrotate) or container logging drivers with size/time limits.
- **Updated**: Monitor Hypercorn HTTP/2 performance metrics including active connections, concurrent streams, and connection pooling efficiency.
- **Updated**: Track HTTP/2 stream statistics and connection reuse rates to optimize server configuration.
- **Updated**: Monitor llama.cpp embedding server performance including memory usage, GPU utilization, and embedding throughput for RAG operations.

## Security Considerations
- Secrets management: Store all secrets in environment variables managed by pydantic-settings. Provide a template file with placeholders (.env.example) and never commit secrets.
- VK webhook security: Use secret and confirmation tokens; validate signatures and enforce HTTPS for webhook URLs.
- Network exposure: Restrict port exposure to internal networks; use reverse proxies with TLS termination.
- Least privilege: Run containers with non-root users and minimal capabilities; mount volumes with appropriate permissions.
- Backup and audit: Regularly snapshot Qdrant and MinIO; maintain audit trails for sensitive operations.
- **Updated**: Secure Hypercorn server with proper TLS configuration and HTTP/2 security headers for production deployments.
- **Updated**: Monitor HTTP/2 connections for security compliance and detect potential abuse patterns.
- **Updated**: Secure llama.cpp embedding server with proper network isolation and access controls for production deployments.

## Scaling Approaches
- Horizontal scaling: Run multiple replicas behind a load balancer; ensure stateless workers and shared storage/backends.
- Vertical scaling: Increase CPU/RAM for replicas and tune Qdrant shards and MinIO resources.
- Queueing: Offload heavy tasks (document ingestion) to background workers with retry policies.
- Caching: Cache frequently accessed KB articles and bot responses to reduce LLM calls.
- **Updated**: Scale Hypercorn instances horizontally for HTTP/2 multiplexing benefits; monitor stream concurrency across instances.
- **Updated**: Configure appropriate h2_max_concurrent_streams values based on workload characteristics and available resources.
- **Updated**: Scale llama.cpp embedding server horizontally if embedding workload exceeds single instance capacity; monitor embedding queue depth and processing latency.

## Production Deployment Playbooks

### Deploying VK Bot with Webhooks
- Prepare environment variables for VK webhook (tokens, confirmation, and webhook URL).
- Build and run the FastAPI service with Hypercorn in production mode.
- Configure reverse proxy (nginx/caddy) with TLS and rate limiting.
- Register VK webhook endpoint and confirm subscription.

**Section sources**
- [AGENTS.md:16-18](file://AGENTS.md#L16-L18)
- [PLAN.md:132-135](file://PLAN.md#L132-L135)

### Running Qdrant and MinIO in Docker
- Use the provided compose file to start services with health checks and persistent volumes.
- Secure MinIO with strong credentials and restrict network access.
- Monitor Qdrant disk usage and configure backups.

**Section sources**
- [docker-compose.yml:1-34](file://docker-compose.yml#L1-L34)

### Managing Secrets and Configuration
- Define canonical settings fields and load from .env using pydantic-settings.
- Provide .env.example with placeholders; never commit real secrets.
- Rotate secrets regularly and invalidate old keys after migration.
- **Updated**: Configure llamacpp provider settings including llm_provider='llamacpp', llm_base_url='http://localhost:8080/v1', and embedding_model='nomic-embed-text'.
- **Updated**: Set up Hypercorn configuration with appropriate worker class and HTTP/2 settings for production deployment.

**Section sources**
- [app/config.py:15-33](file://app/config.py#L15-L33)
- [AGENTS.md:20-50](file://AGENTS.md#L20-L50)
- [scripts/admin_server.py:55-68](file://scripts/admin_server.py#L55-L68)

### Handling Operational Tasks
- Log rotation: Configure logrotate or container logging driver with max-size and max-file.
- Backups: Snapshot Qdrant storage and MinIO buckets; automate and test restore procedures.
- Maintenance windows: Schedule updates during low-traffic periods; use blue/green deployments.
- **Updated**: Monitor and manage Hypercorn server lifecycle, including automatic restarts, HTTP/2 connection monitoring, and worker class optimization.
- **Updated**: Monitor and manage llama.cpp embedding server lifecycle, including automatic restarts and resource monitoring.

### Hypercorn Server Configuration
- Install Hypercorn as the production ASGI server (version >= 0.18.0).
- Configure worker class as "asyncio" for optimal HTTP/2 performance.
- Set h2_max_concurrent_streams to control HTTP/2 stream concurrency (default: 100).
- Use asyncio event loop for better performance with HTTP/2 multiplexing.
- Monitor server performance and adjust configuration based on workload characteristics.

**Section sources**
- [pyproject.toml:9](file://pyproject.toml#L9)
- [scripts/admin_server.py:55-68](file://scripts/admin_server.py#L55-L68)

### Llama.cpp Embedding Server Deployment
- Install llama.cpp and ensure llama-server binary is available in PATH.
- Prepare GGUF model file in ./models/ directory or set MODEL_PATH environment variable.
- Configure HOST, PORT, CTX_SIZE, N_GPU_LAYERS, and THREADS environment variables as needed.
- Start the server with optimized flags for RAG operations: --embedding and --pooling mean.
- Verify embedding server is accessible at http://localhost:8080/v1 with proper embedding capabilities.

**Section sources**
- [scripts/run_llama_qwen.sh:1-61](file://scripts/run_llama_qwen.sh#L1-L61)

## Troubleshooting Guide
- VK webhook not responding:
  - Verify secret and confirmation tokens match VK settings.
  - Confirm HTTPS endpoint is reachable and TLS certificate is valid.
  - Check FastAPI logs for incoming webhook events and error responses.
- Long polling fails locally:
  - Ensure VK access token is set in environment.
  - Confirm script runs from project root and imports are resolvable.
- Qdrant or MinIO unhealthy:
  - Review health check endpoints and logs.
  - Check volume mounts and disk space.
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

**Section sources**
- [scripts/polling_vk.py:17-38](file://scripts/polling_vk.py#L17-L38)
- [docker-compose.yml:11-16](file://docker-compose.yml#L11-L16)
- [AGENTS.md:16-18](file://AGENTS.md#L16-L18)
- [scripts/run_llama_qwen.sh:32-41](file://scripts/run_llama_qwen.sh#L32-L41)
- [scripts/admin_server.py:55-68](file://scripts/admin_server.py#L55-L68)

## Conclusion
cafetera_hr_bot is designed for production-grade operations with a clear separation between VK bot orchestration, RAG infrastructure, and storage. The system now supports multiple LLM providers including llama.cpp with optimized embedding capabilities for enhanced RAG functionality. The production server utilizes Hypercorn with HTTP/2 support, providing improved performance and modern protocol features compared to traditional ASGI servers. By adopting webhook-based transport, securing secrets, monitoring health, implementing robust scaling and backup strategies, properly managing the llama.cpp embedding server, and optimizing Hypercorn HTTP/2 configuration, teams can operate the bot reliably in production while preparing for future Telegram integration and advanced webhook deployments.