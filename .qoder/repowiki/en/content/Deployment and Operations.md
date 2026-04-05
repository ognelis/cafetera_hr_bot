# Deployment and Operations

<cite>
**Referenced Files in This Document**
- [docker-compose.yml](file://docker-compose.yml)
- [pyproject.toml](file://pyproject.toml)
- [app/config.py](file://app/config.py)
- [scripts/polling_vk.py](file://scripts/polling_vk.py)
- [app/integrations/vk/bot.py](file://app/integrations/vk/bot.py)
- [app/integrations/vk/handlers/start.py](file://app/integrations/vk/handlers/start.py)
- [app/integrations/vk/states.py](file://app/integrations/vk/states.py)
- [AGENTS.md](file://AGENTS.md)
- [PLAN.md](file://PLAN.md)
</cite>

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
This document provides comprehensive guidance for deploying and operating cafetera_hr_bot in production. It covers containerized infrastructure using Docker Compose, operational controls for VK bot long-polling versus webhook-based production operation, planned Telegram integration, and future webhook deployment. It also documents monitoring and logging strategies, secrets management, scaling approaches, performance optimization, disaster recovery planning, and practical deployment playbooks.

## Project Structure
The repository organizes runtime concerns into layered modules:
- Integrations: VK bot adapter and handlers
- Domain: States and navigation helpers
- Config: Pydantic-based settings loader
- Scripts: Local development entry-points
- Infrastructure: Docker Compose services for Qdrant and MinIO

```mermaid
graph TB
subgraph "Runtime"
VKBot["VK Bot Adapter<br/>app/integrations/vk/bot.py"]
Handlers["Handlers<br/>app/integrations/vk/handlers/*"]
States["States<br/>app/integrations/vk/states.py"]
Config["Settings Loader<br/>app/config.py"]
end
subgraph "Infrastructure"
Qdrant["Qdrant Vector DB<br/>docker-compose.yml"]
MinIO["MinIO Object Storage<br/>docker-compose.yml"]
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
DevPoll --> VKBot
Compose --> Qdrant
Compose --> MinIO
Config --> Env
```

**Diagram sources**
- [app/integrations/vk/bot.py:1-32](file://app/integrations/vk/bot.py#L1-L32)
- [app/integrations/vk/handlers/start.py:1-55](file://app/integrations/vk/handlers/start.py#L1-L55)
- [app/integrations/vk/states.py:1-14](file://app/integrations/vk/states.py#L1-L14)
- [app/config.py:1-9](file://app/config.py#L1-L9)
- [scripts/polling_vk.py:1-33](file://scripts/polling_vk.py#L1-L33)
- [docker-compose.yml:1-34](file://docker-compose.yml#L1-L34)

**Section sources**
- [docker-compose.yml:1-34](file://docker-compose.yml#L1-L34)
- [pyproject.toml:1-56](file://pyproject.toml#L1-L56)
- [app/config.py:1-9](file://app/config.py#L1-L9)
- [scripts/polling_vk.py:1-33](file://scripts/polling_vk.py#L1-L33)
- [app/integrations/vk/bot.py:1-32](file://app/integrations/vk/bot.py#L1-L32)
- [app/integrations/vk/handlers/start.py:1-55](file://app/integrations/vk/handlers/start.py#L1-L55)
- [app/integrations/vk/states.py:1-14](file://app/integrations/vk/states.py#L1-L14)
- [AGENTS.md:1-88](file://AGENTS.md#L1-L88)
- [PLAN.md:1-207](file://PLAN.md#L1-L207)

## Core Components
- VK Bot Adapter: Creates a fully wired vkbottle Bot with registered labelers and logging.
- Handlers: Start/main menu/navigation and fallback handlers.
- States: Multi-step dialog states for HR request scenario.
- Config: Pydantic Settings with environment file support.
- Dev Long Poll Script: Local development entry-point for VK bot using long polling.

Operational highlights:
- Production mode requires webhook transport via FastAPI lifespan (not long polling).
- VK webhook requires secret and confirmation tokens plus a webhook URL.
- Telegram integration is post-MVP and will use aiogram with webhook.

**Section sources**
- [app/integrations/vk/bot.py:23-32](file://app/integrations/vk/bot.py#L23-L32)
- [app/integrations/vk/handlers/start.py:23-55](file://app/integrations/vk/handlers/start.py#L23-L55)
- [app/integrations/vk/states.py:4-14](file://app/integrations/vk/states.py#L4-L14)
- [app/config.py:4-9](file://app/config.py#L4-L9)
- [scripts/polling_vk.py:24-32](file://scripts/polling_vk.py#L24-L32)
- [AGENTS.md:16-18](file://AGENTS.md#L16-L18)
- [PLAN.md:132-135](file://PLAN.md#L132-L135)

## Architecture Overview
The system runs a VK bot with optional RAG capabilities backed by Qdrant and MinIO. In production, the VK bot operates via FastAPI webhook transport; long polling is for local development only.

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
Client --> Webhook
Webhook --> Bot
Bot --> Handlers
Bot --> States
Bot --> Config
Handlers --> States
Config --> Qdrant
Config --> MinIO
```

**Diagram sources**
- [app/integrations/vk/bot.py:23-32](file://app/integrations/vk/bot.py#L23-L32)
- [app/integrations/vk/handlers/start.py:23-55](file://app/integrations/vk/handlers/start.py#L23-L55)
- [app/integrations/vk/states.py:4-14](file://app/integrations/vk/states.py#L4-L14)
- [app/config.py:4-9](file://app/config.py#L4-L9)
- [docker-compose.yml:2-28](file://docker-compose.yml#L2-L28)

**Section sources**
- [AGENTS.md:16-18](file://AGENTS.md#L16-L18)
- [PLAN.md:132-135](file://PLAN.md#L132-L135)
- [docker-compose.yml:2-28](file://docker-compose.yml#L2-L28)

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
}
BotFactory --> VKBot : "creates"
VKBot --> Handlers : "loads labelers"
VKBot --> States : "uses"
BotFactory --> Settings : "reads"
```

**Diagram sources**
- [app/integrations/vk/bot.py:23-32](file://app/integrations/vk/bot.py#L23-L32)
- [app/integrations/vk/handlers/start.py:12-55](file://app/integrations/vk/handlers/start.py#L12-L55)
- [app/integrations/vk/states.py:4-14](file://app/integrations/vk/states.py#L4-L14)
- [app/config.py:4-9](file://app/config.py#L4-L9)

**Section sources**
- [app/integrations/vk/bot.py:14-32](file://app/integrations/vk/bot.py#L14-L32)
- [app/integrations/vk/handlers/start.py:12-55](file://app/integrations/vk/handlers/start.py#L12-L55)
- [app/integrations/vk/states.py:4-14](file://app/integrations/vk/states.py#L4-L14)
- [app/config.py:4-9](file://app/config.py#L4-L9)

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
Script->>Bot : "run_polling()"
Note over Script,Bot : "Long polling loop for VK updates"
```

**Diagram sources**
- [scripts/polling_vk.py:24-32](file://scripts/polling_vk.py#L24-L32)
- [app/config.py:4-9](file://app/config.py#L4-L9)
- [app/integrations/vk/bot.py:23-32](file://app/integrations/vk/bot.py#L23-L32)

**Section sources**
- [scripts/polling_vk.py:1-33](file://scripts/polling_vk.py#L1-L33)
- [app/config.py:4-9](file://app/config.py#L4-L9)
- [app/integrations/vk/bot.py:23-32](file://app/integrations/vk/bot.py#L23-L32)

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
- [docker-compose.yml:2-28](file://docker-compose.yml#L2-L28)

**Section sources**
- [docker-compose.yml:1-34](file://docker-compose.yml#L1-L34)

## Dependency Analysis
External dependencies include FastAPI, Uvicorn, LangChain stack, Qdrant client, VK and Telegram adapters, and testing tools. Optional extras enable Ollama or OpenAI-compatible LLMs.

```mermaid
graph LR
App["cafetera_hr_bot"]
FastAPI["fastapi"]
Uvicorn["uvicorn[standard]"]
LangChain["langchain"]
QdrantClient["qdrant-client"]
VK["vkbottle"]
Telegram["aiogram"]
Tests["pytest"]
App --> FastAPI
App --> Uvicorn
App --> LangChain
App --> QdrantClient
App --> VK
App --> Telegram
App --> Tests
```

**Diagram sources**
- [pyproject.toml:7-22](file://pyproject.toml#L7-L22)

**Section sources**
- [pyproject.toml:1-56](file://pyproject.toml#L1-L56)

## Performance Considerations
- Use production-grade webhook transport instead of long polling to reduce resource overhead and latency.
- Tune Qdrant shard and index parameters for retrieval performance; monitor vector search latency.
- Use MinIO in-cluster for low-latency document ingestion and retrieval.
- Enable FastAPI lifespan initialization for shared resources to avoid cold-starts during requests.
- Apply async I/O patterns and keep handler logic lightweight to maximize throughput.

[No sources needed since this section provides general guidance]

## Monitoring and Logging
- Logging: Configure structured logging at INFO level for operational visibility. Use consistent log formatting and include correlation IDs where applicable.
- Health checks: Leverage Qdrant’s health endpoint and MinIO console for availability monitoring.
- Metrics: Expose Prometheus metrics via FastAPI middleware and scrape with Prometheus.
- Alerting: Forward logs to centralized logging (e.g., ELK or Loki) and set alerts for error spikes and slow response times.
- Log rotation: Use OS-native log rotation (e.g., logrotate) or container logging drivers with size/time limits.

[No sources needed since this section provides general guidance]

## Security Considerations
- Secrets management: Store all secrets in environment variables managed by pydantic-settings. Provide a template file with placeholders (.env.example) and never commit secrets.
- VK webhook security: Use secret and confirmation tokens; validate signatures and enforce HTTPS for webhook URLs.
- Network exposure: Restrict port exposure to internal networks; use reverse proxies with TLS termination.
- Least privilege: Run containers with non-root users and minimal capabilities; mount volumes with appropriate permissions.
- Backup and audit: Regularly snapshot Qdrant and MinIO; maintain audit trails for sensitive operations.

[No sources needed since this section provides general guidance]

## Scaling Approaches
- Horizontal scaling: Run multiple replicas behind a load balancer; ensure stateless workers and shared storage/backends.
- Vertical scaling: Increase CPU/RAM for replicas and tune Qdrant shards and MinIO resources.
- Queueing: Offload heavy tasks (document ingestion) to background workers with retry policies.
- Caching: Cache frequently accessed KB articles and bot responses to reduce LLM calls.

[No sources needed since this section provides general guidance]

## Production Deployment Playbooks

### Deploying VK Bot with Webhooks
- Prepare environment variables for VK webhook (tokens, confirmation, and webhook URL).
- Build and run the FastAPI service with Uvicorn in production mode.
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

**Section sources**
- [app/config.py:4-9](file://app/config.py#L4-L9)
- [AGENTS.md:20-50](file://AGENTS.md#L20-L50)

### Handling Operational Tasks
- Log rotation: Configure logrotate or container logging driver with max-size and max-file.
- Backups: Snapshot Qdrant storage and MinIO buckets; automate and test restore procedures.
- Maintenance windows: Schedule updates during low-traffic periods; use blue/green deployments.

[No sources needed since this section provides general guidance]

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

**Section sources**
- [scripts/polling_vk.py:17-32](file://scripts/polling_vk.py#L17-L32)
- [docker-compose.yml:11-16](file://docker-compose.yml#L11-L16)
- [AGENTS.md:16-18](file://AGENTS.md#L16-L18)

## Conclusion
cafetera_hr_bot is designed for production-grade operations with a clear separation between VK bot orchestration, RAG infrastructure, and storage. By adopting webhook-based transport, securing secrets, monitoring health, and implementing robust scaling and backup strategies, teams can operate the bot reliably in production while preparing for future Telegram integration and advanced webhook deployments.