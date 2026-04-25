# Getting Started

<cite>
**Referenced Files in This Document**
- [README.md](file://README.md)
- [pyproject.toml](file://pyproject.toml)
- [docker-compose.yml](file://docker-compose.yml)
- [packages/admin/src/cafetera_admin/main.py](file://packages/admin/src/cafetera_admin/main.py)
- [packages/admin/src/cafetera_admin/config.py](file://packages/admin/src/cafetera_admin/config.py)
- [packages/core/src/cafetera_core/config.py](file://packages/core/src/cafetera_core/config.py)
- [packages/vk_bot/src/cafetera_vk_bot/bot.py](file://packages/vk_bot/src/cafetera_vk_bot/bot.py)
- [scripts/run_admin.sh](file://scripts/run_admin.sh)
- [scripts/admin_server.py](file://scripts/admin_server.py)
- [packages/admin/pyproject.toml](file://packages/admin/pyproject.toml)
- [packages/core/pyproject.toml](file://packages/core/pyproject.toml)
- [packages/vk_bot/pyproject.toml](file://packages/vk_bot/pyproject.toml)
- [tests/conftest.py](file://tests/conftest.py)
</cite>

## Update Summary
**Changes Made**
- Updated project structure to reflect new monorepo with uv workspace configuration
- Added comprehensive documentation for package-based installation using uv sync
- Updated directory structure documentation with packages/*/src/ organization
- Enhanced installation section with workspace configuration and package imports
- Added new section for workspace-based development workflow
- Updated environment setup to reflect shared configuration inheritance
- Revised troubleshooting section for workspace-related issues

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Prerequisites](#prerequisites)
4. [Workspace Setup](#workspace-setup)
5. [Installation](#installation)
6. [Environment Setup](#environment-setup)
7. [Running the Admin Panel](#running-the-admin-panel)
8. [Development Workflow](#development-workflow)
9. [Testing the Admin Panel](#testing-the-admin-panel)
10. [Verification Checklist](#verification-checklist)
11. [Troubleshooting Guide](#troubleshooting-guide)
12. [Conclusion](#conclusion)

## Introduction
This guide helps you set up cafetera_hr_bot for local development in a modern monorepo environment. The project uses a uv workspace architecture with three main packages: admin, core, and vk_bot. Each package has its own configuration and dependencies, managed through uv workspace. The admin package provides a comprehensive web interface for document management and RAG administration, while the core package contains shared domain logic and infrastructure.

**Updated** Added comprehensive coverage of the new monorepo structure with workspace configuration and package-based imports.

## Project Structure
The repository follows a modern monorepo architecture with uv workspace configuration:

```
cafetera_hr_bot/
├── packages/
│   ├── admin/           # FastAPI admin web interface
│   ├── core/            # Shared domain logic and infrastructure
│   └── vk_bot/          # VK messenger bot implementation
├── scripts/             # Development and deployment helpers
├── static/              # Static assets for admin interface
├── templates/           # Jinja2 templates for admin interface
├── tests/               # Shared test suite
├── docker-compose.yml   # Local infrastructure services
├── pyproject.toml       # Workspace configuration
└── README.md           # Setup documentation
```

```mermaid
graph TB
subgraph "Workspace Packages"
CORE["packages/core/"]
ADMIN["packages/admin/"]
VKBOT["packages/vk_bot/"]
end
subgraph "Workspace Configuration"
PYPROJECT["pyproject.toml<br/>[tool.uv.workspace]"]
SOURCES["[tool.uv.sources]<br/>cafetera-core/admin/vk-bot"]
end
subgraph "Shared Infrastructure"
DOCKER["docker-compose.yml"]
STATIC["static/ & templates/"]
end
PYPROJECT --> CORE
PYPROJECT --> ADMIN
PYPROJECT --> VKBOT
SOURCES --> CORE
SOURCES --> ADMIN
SOURCES --> VKBOT
ADMIN --> STATIC
CORE --> DOCKER
ADMIN --> DOCKER
VKBOT --> DOCKER
```

**Diagram sources**
- [pyproject.toml:22-28](file://pyproject.toml#L22-L28)
- [packages/admin/src/cafetera_admin/main.py:70-78](file://packages/admin/src/cafetera_admin/main.py#L70-L78)
- [docker-compose.yml:1-115](file://docker-compose.yml#L1-L115)

**Section sources**
- [pyproject.toml:1-49](file://pyproject.toml#L1-L49)
- [packages/admin/src/cafetera_admin/main.py:1-88](file://packages/admin/src/cafetera_admin/main.py#L1-L88)
- [docker-compose.yml:1-115](file://docker-compose.yml#L1-L115)

## Prerequisites
- **Python 3.13+** (required for all packages)
- **uv** (Python package manager with workspace support)
- **Docker** (for infrastructure services)
- **Ollama** (for local AI models, optional)
- **Git** (for cloning the repository)
- **Terminal access** (macOS Terminal or Linux shell)

**Updated** Enhanced prerequisites to include uv workspace requirements and modern Python packaging standards.

Key facts from the codebase:
- Python version requirement is 3.13+ across all packages
- uv workspace manages dependencies for all three packages
- Docker Compose orchestrates Qdrant, MinIO, and PostgreSQL
- Ollama provides local LLM and embedding models

**Section sources**
- [pyproject.toml:6](file://pyproject.toml#L6)
- [packages/core/pyproject.toml:5](file://packages/core/pyproject.toml#L5)
- [packages/admin/pyproject.toml:5](file://packages/admin/pyproject.toml#L5)
- [packages/vk_bot/pyproject.toml:5](file://packages/vk_bot/pyproject.toml#L5)

## Workspace Setup
The project uses uv workspace configuration to manage dependencies across multiple packages. The workspace definition in pyproject.toml specifies all member packages and their source locations.

### Workspace Configuration
The main workspace configuration includes:
- **Members**: `["packages/*"]` - all packages in the packages directory
- **Sources**: Individual package sources for proper import resolution
- **Dev Dependencies**: All packages included in the development group

### Package Structure
Each package follows the standard structure:
- `src/` - Source code with proper package naming
- `pyproject.toml` - Package-specific configuration and dependencies
- Proper import paths using `cafetera_package_name` naming convention

**Section sources**
- [pyproject.toml:22-28](file://pyproject.toml#L22-L28)
- [packages/admin/pyproject.toml:1-20](file://packages/admin/pyproject.toml#L1-L20)
- [packages/core/pyproject.toml:1-29](file://packages/core/pyproject.toml#L1-L29)
- [packages/vk_bot/pyproject.toml:1-17](file://packages/vk_bot/pyproject.toml#L1-L17)

## Installation
Follow these steps to install and prepare the workspace environment:

### Step 1: Install Prerequisites
1. **Install Docker** (macOS or Linux)
   - macOS: Download Docker Desktop from docker.com
   - Linux: Use the provided installation commands

2. **Install uv** (Python package manager)
   - Run: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Restart terminal after installation

3. **Install Ollama** (optional, for local AI models)
   - macOS: Download from ollama.com/download
   - Linux: `curl -fsSL https://ollama.com/install.sh | sh`

### Step 2: Clone and Configure Repository
```bash
cd ~/Projects
git clone <repository-url> cafetera_hr_bot
cd cafetera_hr_bot
```

### Step 3: Install Workspace Dependencies
```bash
# Install all workspace dependencies
uv sync

# Install with specific extras if needed
uv sync --extra dev
uv sync --extra ollama
uv sync --extra openai
```

### Step 4: Verify Installation
```bash
# Run tests to verify environment
uv run pytest

# Check package imports work correctly
uv run python -c "from cafetera_core import config; from cafetera_admin import main; from cafetera_vk_bot import bot"
```

**Updated** Added comprehensive workspace setup with uv sync commands and package import verification.

**Section sources**
- [README.md:7-83](file://README.md#L7-L83)
- [pyproject.toml:9-20](file://pyproject.toml#L9-L20)
- [scripts/run_admin.sh:242-250](file://scripts/run_admin.sh#L242-L250)

## Environment Setup
Configure environment variables using the shared settings system. The AdminSettings class extends CoreSettings, inheriting all shared configuration while adding admin-specific fields.

### Required Variables
- **ADMIN_API_KEY** (required for admin authentication)
- **VK_ACCESS_TOKEN** (optional, for VK bot functionality)

### Shared Infrastructure Variables
- **QDRANT_URL** (default: http://localhost:6333)
- **DATABASE_URL** (default: postgresql://cafetera:cafetera@localhost:5432/cafetera)
- **S3_ENDPOINT_URL** (default: http://localhost:9000)

### LLM Provider Configuration
- **LLM_PROVIDER** (default: ollama)
- **LLM_MODEL** (default: qwen3.5:4b-q4_K_M)
- **LLM_BASE_URL** (default: http://localhost:11434)

**Updated** Enhanced environment setup to reflect the shared configuration inheritance pattern.

**Section sources**
- [packages/admin/src/cafetera_admin/config.py:6-20](file://packages/admin/src/cafetera_admin/config.py#L6-L20)
- [packages/core/src/cafetera_core/config.py:14-71](file://packages/core/src/cafetera_core/config.py#L14-L71)
- [scripts/run_admin.sh:113-148](file://scripts/run_admin.sh#L113-L148)

## Running the Admin Panel
The admin panel provides a comprehensive web interface for document management and RAG administration. The run_admin.sh script automates the entire setup process.

### Automated Startup Process
1. **Prerequisite Check**: Verifies Docker, uv, and .env file
2. **Provider Selection**: Interactive choice between Ollama, OpenAI, or llama.cpp
3. **Dependency Sync**: Installs Python dependencies with appropriate extras
4. **Infrastructure Start**: Launches Qdrant, MinIO, and PostgreSQL via Docker Compose
5. **AI Model Setup**: Starts Ollama and downloads required models
6. **Server Launch**: Starts the admin panel on http://127.0.0.1:8000

### Usage Commands
```bash
# Basic startup
cd ~/Projects/cafetera_hr_bot
bash scripts/run_admin.sh

# Custom port
ADMIN_PORT=8080 bash scripts/run_admin.sh

# Custom host
ADMIN_HOST=0.0.0.0 bash scripts/run_admin.sh
```

### Access the Admin Interface
1. **Start the Admin Server**: `bash scripts/run_admin.sh`
2. **Open Browser**: Navigate to `http://127.0.0.1:8000/documents`
3. **Authentication**: Enter ADMIN_API_KEY from .env file

**Section sources**
- [scripts/run_admin.sh:1-445](file://scripts/run_admin.sh#L1-L445)
- [README.md:165-209](file://README.md#L165-L209)

## Development Workflow
The workspace-based architecture enables efficient development across multiple packages with proper dependency management and import resolution.

### Workspace Development Commands
```bash
# Install all dependencies
uv sync

# Install development dependencies
uv sync --extra dev

# Run individual package tests
uv run pytest packages/admin/tests/
uv run pytest packages/core/tests/
uv run pytest packages/vk_bot/tests/

# Run linting across all packages
uv run ruff check packages/core/src packages/admin/src packages/vk_bot/src

# Run type checking
uv run mypy packages/core/src packages/admin/src packages/vk_bot/src
```

### Package-Specific Development
- **Core Package**: Domain logic, RAG pipeline, and storage abstractions
- **Admin Package**: FastAPI web interface with document management
- **VK Bot Package**: Messenger integration with handler registration

### Import Resolution
The workspace configuration ensures proper import resolution:
```python
from cafetera_core.config import CoreSettings
from cafetera_admin.main import create_app
from cafetera_vk_bot.bot import create_bot
```

**Section sources**
- [pyproject.toml:34-49](file://pyproject.toml#L34-L49)
- [packages/admin/src/cafetera_admin/main.py:14-16](file://packages/admin/src/cafetera_admin/main.py#L14-L16)
- [packages/vk_bot/src/cafetera_vk_bot/bot.py:9-20](file://packages/vk_bot/src/cafetera_vk_bot/bot.py#L9-L20)

## Testing the Admin Panel
The admin panel provides comprehensive functionality for document management and RAG administration:

### Admin Interface Features
- **Document Upload**: Drag-and-drop or browse to upload Word documents
- **Document Management**: View, edit, and manage document metadata
- **Search Toggle**: Enable/disable documents from RAG search results
- **Reindex Documents**: Recreate vector embeddings for updated documents
- **Bulk Operations**: Manage multiple documents simultaneously

### Backend API Endpoints
- **GET /documents**: List all documents with pagination
- **POST /documents**: Upload new documents
- **GET /documents/{id}**: Get document details
- **PUT /documents/{id}**: Update document metadata
- **PATCH /documents/{id}/toggle-search**: Enable/disable search participation
- **POST /documents/{id}/reindex**: Rebuild vector embeddings
- **DELETE /documents/{id}**: Remove document and associated data

### Testing Commands
```bash
# Run admin-specific tests
uv run pytest tests/test_api_documents.py
uv run pytest tests/test_api_documents_auth.py
uv run pytest tests/test_api_documents_bulk.py
uv run pytest tests/test_api_documents_upload.py

# Test QA functionality
uv run pytest tests/test_qa_service.py
uv run pytest tests/test_hybrid_search.py
```

**Section sources**
- [scripts/admin_server.py:1-12](file://scripts/admin_server.py#L1-L12)
- [README.md:201-209](file://README.md#L201-L209)

## Verification Checklist
### Workspace Setup Verification
- **Workspace Detection**: `uv workspace show` confirms workspace members
- **Package Imports**: `uv run python -c "from cafetera_core import config"` succeeds
- **Dependency Resolution**: All packages install without conflicts
- **Import Paths**: Proper package naming resolves correctly

### Admin Panel Verification
- **Docker Services**: `docker compose ps` shows healthy Qdrant, MinIO, and PostgreSQL
- **Admin Interface**: Browser access to `http://127.0.0.1:8000/documents`
- **Authentication**: ADMIN_API_KEY successfully validates
- **AI Models**: Ollama models downloaded and ready
- **Static Assets**: CSS and JavaScript files load correctly

### Core Functionality Verification
- **Document Processing**: Upload test documents and verify indexing
- **RAG Query**: Test question-answering with uploaded documents
- **Database Connection**: Verify PostgreSQL connectivity
- **Storage Integration**: Confirm MinIO bucket access

**Section sources**
- [scripts/run_admin.sh:244-261](file://scripts/run_admin.sh#L244-L261)
- [README.md:217-249](file://README.md#L217-L249)
- [packages/admin/src/cafetera_admin/main.py:70-78](file://packages/admin/src/cafetera_admin/main.py#L70-L78)

## Troubleshooting Guide
### Workspace and Package Issues
- **Workspace Not Detected**: Run `uv workspace show` to verify workspace configuration
- **Package Import Errors**: Ensure proper package naming (`cafetera-package-name`)
- **Dependency Conflicts**: Use `uv pip tree` to diagnose dependency resolution issues
- **Source Resolution**: Verify package directories contain proper `src/` structure

### Docker and Infrastructure Issues
- **Docker Not Found**: Install Docker Desktop or Docker Engine
- **Service Health**: Check `docker compose logs qdrant` for initialization errors
- **Port Conflicts**: Use `lsof -i :PORT` to identify conflicting processes
- **Volume Permissions**: Ensure proper permissions for mounted volumes

### Environment and Configuration Issues
- **ADMIN_API_KEY Missing**: Add ADMIN_API_KEY to .env file
- **Import Path Errors**: Verify PYTHONPATH includes `packages/core/src`, `packages/admin/src`, `packages/vk_bot/src`
- **Settings Inheritance**: Check that AdminSettings properly extends CoreSettings
- **Static File Loading**: Verify repository root detection in main.py

### Development Workflow Issues
- **Test Discovery**: Ensure test files follow pytest naming conventions
- **Linting Errors**: Run `uv run ruff check` with proper source paths
- **Type Checking**: Verify mypy configuration includes all package sources
- **Package Isolation**: Use separate virtual environments for different package development

**Section sources**
- [README.md:290-322](file://README.md#L290-L322)
- [packages/admin/src/cafetera_admin/main.py:20-35](file://packages/admin/src/cafetera_admin/main.py#L20-L35)
- [pyproject.toml:34-49](file://pyproject.toml#L34-L49)

## Conclusion
You now have a comprehensive understanding of the cafetera_hr_bot monorepo setup and development workflow. The workspace-based architecture provides several advantages:

### Benefits of Workspace Architecture
- **Unified Dependency Management**: Single source of truth for all package dependencies
- **Consistent Development Environment**: Standardized tooling across all packages
- **Proper Import Resolution**: Clean package naming and import paths
- **Modular Code Organization**: Clear separation of concerns across packages

### Next Steps
1. **Explore Package Structure**: Examine the three main packages and their responsibilities
2. **Run Tests**: Execute the test suite to verify your setup
3. **Experiment with Admin Interface**: Upload documents and test RAG functionality
4. **Contribute Code**: Follow the established patterns for adding new features

The workspace configuration ensures that all development activities align with the project's architectural principles, making it easier to maintain code quality and developer productivity.