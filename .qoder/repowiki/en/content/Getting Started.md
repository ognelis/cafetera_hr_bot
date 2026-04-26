# Getting Started

<cite>
**Referenced Files in This Document**
- [README.md](file://README.md)
- [docker-compose.yml](file://docker-compose.yml)
- [.env.example](file://.env.example)
- [pyproject.toml](file://pyproject.toml)
- [Dockerfile.admin](file://Dockerfile.admin)
- [Dockerfile.polling_vk](file://Dockerfile.polling_vk)
- [packages/admin/pyproject.toml](file://packages/admin/pyproject.toml)
- [packages/core/pyproject.toml](file://packages/core/pyproject.toml)
- [packages/vk_bot/pyproject.toml](file://packages/vk_bot/pyproject.toml)
- [scripts/run_admin.sh](file://scripts/run_admin.sh)
- [scripts/run_all.sh](file://scripts/run_all.sh)
- [scripts/run_admin_docker.sh](file://scripts/run_admin_docker.sh)
- [scripts/run_llama_embeddings.sh](file://scripts/run_llama_embeddings.sh)
- [scripts/run_llama_llm.sh](file://scripts/run_llama_llm.sh)
- [AGENTS.md](file://AGENTS.md)
</cite>

## Update Summary
**Changes Made**
- Completely rewritten to reflect the massive README.md overhaul transforming project from basic installation guide to comprehensive multilingual user manual
- Added detailed coverage of all four deployment scenarios (A through D) with practical step-by-step instructions
- Enhanced Docker installation and configuration documentation with platform-specific guidance
- Updated environment setup with comprehensive .env configuration options and AI provider examples
- Expanded troubleshooting section with specific error scenarios and solutions
- Added llama.cpp model management and GPU acceleration configuration
- Included practical examples for all deployment variants with verification steps

## Table of Contents
1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Environment Setup](#environment-setup)
5. [Deployment Scenarios](#deployment-scenarios)
6. [Running the Admin Panel](#running-the-admin-panel)
7. [Development Workflow](#development-workflow)
8. [Testing the Admin Panel](#testing-the-admin-panel)
9. [Verification Checklist](#verification-checklist)
10. [Troubleshooting Guide](#troubleshooting-guide)
11. [AI Provider Configuration](#ai-provider-configuration)
12. [Conclusion](#conclusion)

## Introduction
This guide helps you set up cafetera_hr_bot for local development with comprehensive deployment options. The project consists of two main components: an admin panel for document management and a VK messenger bot that answers employee questions using AI-powered RAG (Retrieval-Augmented Generation).

**System Components:**
- **Admin Panel** — Web interface for uploading and managing documents, accessible at `http://localhost:8000/documents`
- **VK Bot** — Messenger integration that responds to employee questions based on uploaded documents

**AI Providers Available:**
- **Ollama** — Free local AI models with automatic download (recommended for beginners)
- **OpenAI** — Cloud-based models via API keys (requires internet and payment)
- **llama.cpp** — Maximum control over local models with manual configuration

**Section sources**
- [README.md:30-53](file://README.md#L30-L53)
- [README.md:46-51](file://README.md#L46-L51)

## Prerequisites
Before starting, ensure you have the following installed:

### Essential Tools
- **Docker** — Container orchestration for infrastructure services
- **uv** — Modern Python package manager with workspace support
- **Git** — Version control for repository access

### Optional AI Tools
- **Ollama** — For local AI models (free, recommended)
- **llama.cpp** — For advanced local model control

### System Requirements
- **macOS**: Intel or Apple Silicon (M1/M2/M3/M4)
- **Linux**: Debian/Ubuntu with Docker support
- **Windows**: WSL2 with Docker Desktop

**Section sources**
- [README.md:56-136](file://README.md#L56-L136)
- [README.md:140-165](file://README.md#L140-L165)
- [README.md:168-240](file://README.md#L168-L240)

## Installation
Follow these steps to install and configure the project:

### Step 1: Install Docker
**macOS:**
1. Download Docker Desktop from docker.com
2. Install and launch Docker
3. Wait for the Docker icon to stop blinking

**Linux (Debian/Ubuntu):**
```bash
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER
```
**Important:** Log out and back in after adding to docker group

### Step 2: Install uv (Python Package Manager)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
**Important:** Close and reopen terminal after installation

### Step 3: Install Ollama (Optional)
**macOS:** Download from ollama.com/download
**Linux:** `curl -fsSL https://ollama.com/install.sh | sh`

### Step 4: Install llama.cpp (Optional)
**macOS (Homebrew):**
```bash
brew install llama.cpp
```

**Linux (Build from source):**
```bash
sudo apt-get install -y build-essential cmake
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
cmake -B build
cmake --build build --config Release -j$(nproc)
sudo cp build/bin/llama-server /usr/local/bin/
```

### Step 5: Clone the Repository
```bash
cd ~/Projects
git clone <repository-url> cafetera_hr_bot
cd cafetera_hr_bot
```

**Section sources**
- [README.md:56-136](file://README.md#L56-L136)
- [README.md:242-257](file://README.md#L242-L257)
- [README.md:168-240](file://README.md#L168-L240)

## Environment Setup
Configure your environment variables using the `.env` file:

### Create Environment File
```bash
cp .env.example .env
```

### Required Variables
| Variable | Description | Example Value |
|----------|-------------|---------------|
| `ADMIN_API_KEY` | Admin panel authentication key | `my-secret-key-2025` |
| `VK_ACCESS_TOKEN` | VK community access token | `vk1_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `VK_GROUP_ID` | VK community numeric ID | `123456789` |

### AI Provider Configuration
Choose one of the following AI providers:

**Ollama (Recommended):**
```
LLM_PROVIDER=ollama
LLM_MODEL=qwen3.5:4b-q4_K_M
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=qwen3-embedding:4b-q4_K_M
```

**OpenAI (Cloud-based):**
```
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-...your-key...
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_API_KEY=sk-...your-key...
```

**llama.cpp (Local models):**
```
LLM_PROVIDER=llamacpp
LLM_MODEL=local-model
EMBEDDING_PROVIDER=llamacpp
EMBEDDING_MODEL=qwen3-embedding
```

**Section sources**
- [README.md:260-335](file://README.md#L260-L335)
- [README.md:302-332](file://README.md#L302-L332)
- [.env.example:16-35](file://.env.example#L16-L35)

## Deployment Scenarios
The project supports four deployment scenarios, each suited for different use cases:

### Scenario A: Admin Panel Only (Bash Script)
**Best for:** First-time users and development
```bash
cd ~/Projects/cafetera_hr_bot
bash scripts/run_admin.sh
```

**What it does:**
1. Checks Docker and uv installation
2. Asks for AI provider selection
3. Starts PostgreSQL, Qdrant, and MinIO
4. Launches the admin panel on port 8000

### Scenario B: Admin Panel Only (Docker)
**Best for:** Pure Docker environment without uv
```bash
cd ~/Projects/cafetera_hr_bot
bash scripts/run_admin_docker.sh
```

### Scenario C: Admin Panel + VK Bot (Bash Script)
**Best for:** Full development with messaging integration
```bash
cd ~/Projects/cafetera_hr_bot
bash scripts/run_all.sh
```

**Requirements:** Fill VK_ACCESS_TOKEN and VK_GROUP_ID in .env

### Scenario D: Everything via Docker Compose
**Best for:** Production servers and clean deployments
```bash
cd ~/Projects/cafetera_hr_bot
docker compose up -d --build
```

**Services started:**
- PostgreSQL (database)
- Qdrant (vector database)
- MinIO (object storage)
- Admin Panel (port 8000)
- VK Bot (polling mode)

**Section sources**
- [README.md:338-493](file://README.md#L338-L493)
- [README.md:351-394](file://README.md#L351-L394)
- [README.md:397-416](file://README.md#L397-L416)
- [README.md:419-442](file://README.md#L419-L442)
- [README.md:445-492](file://README.md#L445-L492)

## Running the Admin Panel
After successful deployment, access the admin panel:

### Access the Interface
1. Open browser to `http://localhost:8000/documents`
2. Enter `ADMIN_API_KEY` from your `.env` file
3. Upload PDF/DOCX documents using drag-and-drop

### Admin Panel Features
- Document upload and management
- Search result toggling
- Vector embedding reindexing
- Bulk document operations

**Section sources**
- [README.md:495-512](file://README.md#L495-L512)

## Development Workflow
The project uses a modern monorepo architecture with uv workspace management:

### Workspace Commands
```bash
# Install all dependencies
uv sync

# Install development dependencies
uv sync --extra dev

# Run package-specific tests
uv run pytest packages/admin/tests/
uv run pytest packages/core/tests/
uv run pytest packages/vk_bot/tests/

# Run linting
uv run ruff check packages/core/src packages/admin/src packages/vk_bot/src

# Type checking
uv run mypy packages/core/src packages/admin/src packages/vk_bot/src
```

### Package Structure
- **packages/core/** — Shared RAG logic and infrastructure
- **packages/admin/** — FastAPI web interface
- **packages/vk_bot/** — VK messenger integration

**Section sources**
- [pyproject.toml:9-20](file://pyproject.toml#L9-L20)
- [pyproject.toml:22-28](file://pyproject.toml#L22-L28)

## Testing the Admin Panel
Execute comprehensive tests to validate your setup:

### Test Categories
```bash
# Document management tests
uv run pytest tests/test_api_documents.py
uv run pytest tests/test_api_documents_auth.py
uv run pytest tests/test_api_documents_bulk.py
uv run pytest tests/test_api_documents_upload.py

# QA and search functionality
uv run pytest tests/test_qa_service.py
uv run pytest tests/test_hybrid_search.py

# Core functionality tests
uv run pytest tests/test_config.py
uv run pytest tests/test_indexer.py
uv run pytest tests/test_document_service.py
```

**Section sources**
- [README.md:201-209](file://README.md#L201-L209)

## Verification Checklist
### Basic Setup Verification
- **Docker Health:** `docker compose ps` shows all services healthy
- **Admin Access:** Browser opens `http://localhost:8000/documents`
- **Authentication:** ADMIN_API_KEY validation successful
- **Database Connection:** PostgreSQL accessible at port 5432

### AI Provider Verification
- **Ollama Models:** `ollama list` shows downloaded models
- **OpenAI API:** API key validation successful
- **llama.cpp Servers:** Ports 8080 (LLM) and 8090 (Embeddings) responsive

### Document Processing
- **Upload Success:** PDF/DOCX files processed
- **Vector Indexing:** Documents indexed in Qdrant
- **Search Results:** RAG queries return relevant responses

**Section sources**
- [README.md:217-249](file://README.md#L217-L249)

## Troubleshooting Guide

### Common Installation Issues
**Docker Not Found:**
```bash
# Check Docker installation
docker --version
# Install Docker Desktop or Docker Engine
```

**uv Command Not Found:**
```bash
# Reinstall uv
curl -LsSf https://astral.sh/uv/install.sh | sh
# Restart terminal
```

**Port Conflicts:**
```bash
# Check what's using port 8000
lsof -i :8000
# Stop conflicting process or change port
ADMIN_PORT=8080 bash scripts/run_admin.sh
```

### Database and Service Issues
**Service Failures:**
```bash
# Check service health
docker compose ps
docker compose logs qdrant
docker compose logs postgres
docker compose logs minio

# Restart failed services
docker compose restart qdrant postgres minio
```

**Model Download Delays (Ollama):**
- Initial download size: ~4-6 GB
- Network-dependent, expect 10-60 minutes
- Subsequent runs use cached models

### VK Bot Issues
**Bot Not Responding:**
1. Verify VK_ACCESS_TOKEN and VK_GROUP_ID in .env
2. Check bot logs: `docker compose logs vk_bot`
3. Ensure VK community has "Messages" enabled

**Docker Host Resolution (Linux):**
```bash
# Check host.docker.internal resolution
docker compose exec admin ping host.docker.internal
# Update Docker version if needed
docker --version
```

**Section sources**
- [README.md:523-568](file://README.md#L523-L568)

## AI Provider Configuration

### Ollama Setup
**Automatic Model Management:**
- LLM model: `qwen3.5:4b-q4_K_M` (~2.5 GB)
- Embedding model: `qwen3-embedding:4b-q4_K_M` (~2.4 GB)
- Automatic download during first run

**GPU Acceleration:**
```bash
# Check available GPUs
ollama list
# Configure GPU layers in .env
LLM_N_GPU_LAYERS=99
EMBED_N_GPU_LAYERS=99
```

### OpenAI Configuration
**API Key Setup:**
```
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-...your-key...
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_API_KEY=sk-...your-key...
```

**Cost Considerations:**
- Pay-per-use pricing
- Requires active billing
- Monitor API usage regularly

### llama.cpp Configuration
**Model Files:**
Place GGUF format models in `models/` directory:
- `models/Qwen3.5-4B-Q4_K_M.gguf` (LLM)
- `models/Qwen3-Embedding-4B-Q4_K_M.gguf` (Embeddings)

**Manual Server Management:**
```bash
# Start LLM server
bash scripts/run_llama_llm.sh

# Start Embedding server
bash scripts/run_llama_embeddings.sh

# GPU acceleration configuration
export LLM_N_GPU_LAYERS=99
export EMBED_N_GPU_LAYERS=99
```

**GPU Support Matrix:**
- **Apple Silicon:** Metal acceleration (all layers)
- **NVIDIA:** CUDA acceleration (all layers)
- **Other:** CPU-only operation

**Section sources**
- [README.md:168-240](file://README.md#L168-L240)
- [README.md:302-332](file://README.md#L302-L332)
- [README.md:201-222](file://README.md#L201-L222)

## Conclusion
You now have comprehensive knowledge to deploy cafetera_hr_bot in various environments. Choose the scenario that best fits your needs:

### Deployment Strategy Recommendations
- **First-time Users:** Start with Scenario A (Admin Panel Only)
- **Development with Messaging:** Use Scenario C (Full Stack)
- **Production Deployments:** Implement Scenario D (Docker Compose)
- **Pure Docker Environments:** Use Scenario B

### Next Steps
1. **Test Document Upload:** Upload sample PDF/DOCX files
2. **Verify AI Integration:** Test question-answering functionality
3. **Configure VK Bot:** Set up messaging integration
4. **Monitor Performance:** Check logs and resource usage
5. **Scale Up:** Plan for production deployment

The flexible deployment options ensure you can start simple and scale complexity as your needs grow, while the unified configuration system maintains consistency across all environments.

**Section sources**
- [README.md:570-582](file://README.md#L570-L582)