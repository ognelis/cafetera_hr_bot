# Configuration Management

<cite>
**Referenced Files in This Document**
- [packages/core/src/cafetera_core/config.py](file://packages/core/src/cafetera_core/config.py)
- [packages/admin/src/cafetera_admin/config.py](file://packages/admin/src/cafetera_admin/config.py)
- [packages/vk_bot/src/cafetera_vk_bot/config.py](file://packages/vk_bot/src/cafetera_vk_bot/config.py)
- [packages/rag_service/src/cafetera_rag_service/config.py](file://packages/rag_service/src/cafetera_rag_service/config.py)
- [packages/rag_service/src/cafetera_rag_service/rag/retriever.py](file://packages/rag_service/src/cafetera_rag_service/rag/retriever.py)
- [packages/rag_service/src/cafetera_rag_service/rag/text_processor.py](file://packages/rag_service/src/cafetera_rag_service/rag/text_processor.py)
- [packages/rag_service/src/cafetera_rag_service/rag/reranker.py](file://packages/rag_service/src/cafetera_rag_service/rag/reranker.py)
- [packages/rag_service/src/cafetera_rag_service/resources.py](file://packages/rag_service/src/cafetera_rag_service/resources.py)
- [packages/admin/pyproject.toml](file://packages/admin/pyproject.toml)
- [packages/vk_bot/pyproject.toml](file://packages/vk_bot/pyproject.toml)
- [packages/rag_service/pyproject.toml](file://packages/rag_service/pyproject.toml)
- [pyproject.toml](file://pyproject.toml)
- [scripts/run_all.sh](file://scripts/run_all.sh)
- [scripts/run_admin_docker.sh](file://scripts/run_admin_docker.sh)
- [tests/test_config.py](file://tests/test_config.py)
- [tests/test_rag_block6.py](file://tests/test_rag_block6.py)
- [tests/test_hybrid_rerank_retriever.py](file://tests/test_hybrid_rerank_retriever.py)
- [docker-compose.yml](file://docker-compose.yml)
- [README.md](file://README.md)
</cite>

## Update Summary
**Changes Made**
- Updated to document new configuration settings including llm_num_ctx for context window sizing, llm_disable_thinking for Qwen3/Qwen3.5 models, BM25 lemmatization controls, doc_query_k, global_max_k, and dense_score_threshold for fine-tuned retrieval control
- Enhanced RAG service configuration documentation with comprehensive LLM context window configuration and Russian lemmatization settings
- Added detailed coverage of retrieval parameter optimization with k-value configuration and scoring thresholds
- Updated HTTP-based reranking configuration with reranker_url, reranker_top_n, and reranker_prefetch_limit
- Expanded environment variable documentation with new parameter examples
- Added comprehensive testing coverage for new configuration parameters

## Table of Contents
1. [Introduction](#introduction)
2. [Package-Based Configuration Architecture](#package-based-configuration-architecture)
3. [Core Settings Foundation](#core-settings-foundation)
4. [RAG Service Configuration](#rag-service-configuration)
5. [Package-Specific Settings Classes](#package-specific-settings-classes)
6. [Configuration Inheritance Hierarchy](#configuration-inheritance-hierarchy)
7. [Enhanced Environment Variable Management](#enhanced-environment-variable-management)
8. [Package-Specific Configuration Examples](#package-specific-configuration-examples)
9. [Configuration Validation and Testing](#configuration-validation-and-testing)
10. [Migration from Legacy Configuration](#migration-from-legacy-configuration)
11. [Security Considerations](#security-considerations)
12. [Development and Deployment Patterns](#development-and-deployment-patterns)
13. [Troubleshooting Common Issues](#troubleshooting-common-issues)
14. [Best Practices](#best-practices)

## Introduction
This document explains the completely restructured configuration management system in cafetera_hr_bot, which has evolved from a monolithic Settings class to a sophisticated inheritance-based architecture. The new system centers around CoreSettings as the foundation for shared configuration, with AdminSettings, VKSettings, and RagServiceSettings extending CoreSettings for package-specific functionality. This architectural change provides better separation of concerns, package isolation, and maintainability while preserving backward compatibility.

The configuration system now follows a clear inheritance pattern where CoreSettings contains all shared RAG, storage, and basic configuration, while AdminSettings and VKSettings extend CoreSettings with their respective package-specific fields. RagServiceSettings operates as a standalone configuration class for the RAG microservice, providing comprehensive LLM, embedding, and retrieval configuration options. The "extra: ignore" model configuration ensures that environment variables intended for other packages are silently ignored, preventing cross-package interference.

**Section sources**
- [packages/core/src/cafetera_core/config.py:14-40](file://packages/core/src/cafetera_core/config.py#L14-L40)
- [packages/admin/src/cafetera_admin/config.py:6-20](file://packages/admin/src/cafetera_admin/config.py#L6-L20)
- [packages/vk_bot/src/cafetera_vk_bot/config.py:4-16](file://packages/vk_bot/src/cafetera_vk_bot/config.py#L4-L16)
- [packages/rag_service/src/cafetera_rag_service/config.py:8-84](file://packages/rag_service/src/cafetera_rag_service/config.py#L8-L84)

## Package-Based Configuration Architecture
The enhanced configuration system follows a modular package architecture with clear separation between shared and package-specific configurations:

- **Core Package**: Contains the CoreSettings class with shared storage and basic configuration
- **Admin Package**: Extends CoreSettings with admin-specific fields and maintains package isolation
- **VK Bot Package**: Extends CoreSettings with VK-specific fields and maintains package isolation
- **RAG Service Package**: Provides standalone RagServiceSettings with comprehensive LLM, embedding, and retrieval configuration
- **Inheritance Pattern**: CoreSettings serves as base for AdminSettings and VKSettings; RagServiceSettings is independent
- **Package Isolation**: Each package ignores environment variables not relevant to its configuration
- **Shared Dependencies**: All packages depend on the core package for shared functionality

```mermaid
graph TB
subgraph "Package-Based Configuration Architecture"
CoreSettings["CoreSettings<br/>(Shared Storage & Basic Config)"]
AdminSettings["AdminSettings<br/>(Extends CoreSettings)"]
VKSettings["VKSettings<br/>(Extends CoreSettings)"]
RagServiceSettings["RagServiceSettings<br/>(Standalone)"]
ExtraIgnore["model_config = {'extra': 'ignore'}"]
end
subgraph "Core Package"
CoreConfig["CoreSettings Definition"]
CoreFields["Database URL<br/>S3 Settings<br/>Indexing Concurrency"]
end
subgraph "Admin Package"
AdminConfig["AdminSettings Definition"]
AdminFields["Admin API Key"]
end
subgraph "VK Bot Package"
VKConfig["VKSettings Definition"]
VKFields["VK Access Token<br/>VK Group ID"]
end
subgraph "RAG Service Package"
RagConfig["RagServiceSettings Definition"]
RagFields["LLM Config<br/>Embedding Config<br/>Hybrid Search<br/>Retrieval K Values<br/>Scoring Thresholds<br/>HTTP Reranking"]
end
CoreSettings --> AdminSettings
CoreSettings --> VKSettings
CoreSettings --> CoreConfig
AdminSettings --> AdminConfig
VKSettings --> VKConfig
RagServiceSettings --> RagConfig
ExtraIgnore --> AdminSettings
ExtraIgnore --> VKSettings
CoreFields --> CoreConfig
AdminFields --> AdminConfig
VKFields --> VKConfig
RagFields --> RagConfig
```

**Diagram sources**
- [packages/core/src/cafetera_core/config.py:14-40](file://packages/core/src/cafetera_core/config.py#L14-L40)
- [packages/admin/src/cafetera_admin/config.py:6-20](file://packages/admin/src/cafetera_admin/config.py#L6-L20)
- [packages/vk_bot/src/cafetera_vk_bot/config.py:4-16](file://packages/vk_bot/src/cafetera_vk_bot/config.py#L4-L16)
- [packages/rag_service/src/cafetera_rag_service/config.py:8-84](file://packages/rag_service/src/cafetera_rag_service/config.py#L8-L84)

**Section sources**
- [packages/core/src/cafetera_core/config.py:14-40](file://packages/core/src/cafetera_core/config.py#L14-L40)
- [packages/admin/src/cafetera_admin/config.py:6-20](file://packages/admin/src/cafetera_admin/config.py#L6-L20)
- [packages/vk_bot/src/cafetera_vk_bot/config.py:4-16](file://packages/vk_bot/src/cafetera_vk_bot/config.py#L4-L16)
- [packages/rag_service/src/cafetera_rag_service/config.py:8-84](file://packages/rag_service/src/cafetera_rag_service/config.py#L8-L84)

## Core Settings Foundation
The CoreSettings class serves as the foundation for shared configuration across all packages, containing essential storage and basic configuration settings:

- **Storage Configuration**: Database connections, S3 storage settings, and bucket management
- **Indexing Configuration**: Concurrency limits for document processing operations
- **Environment File Integration**: UTF-8 encoded .env file loading with Pydantic BaseSettings
- **Package Isolation**: "extra: ignore" model configuration prevents cross-package interference
- **Backward Compatibility**: Legacy Settings alias maintains compatibility

Key implementation details:
- Inherits from Pydantic BaseSettings for type-safe configuration loading
- Uses UTF-8 encoding for .env file compatibility
- Includes essential configuration fields for database connectivity and storage
- Provides sensible defaults for development and production environments
- Supports environment variable precedence over defaults

**Section sources**
- [packages/core/src/cafetera_core/config.py:14-40](file://packages/core/src/cafetera_core/config.py#L14-L40)

## RAG Service Configuration
The RagServiceSettings class provides comprehensive configuration for the RAG microservice, operating independently from the core package:

- **RAG Service Configuration**: Service URL and API key for internal communication
- **Qdrant Configuration**: Vector database connection, API key, collection settings, and timeout parameters
- **LLM Provider Configuration**: Complete LLM configuration including provider selection, model names, base URLs, API keys, and sampling parameters
- **Embedding Provider Configuration**: Separate embedding provider settings with independent configuration
- **Hybrid Search Configuration**: Sparse embedding model settings for BM25-based lexical matching with Russian lemmatization support
- **Retrieval Parameter Configuration**: Comprehensive k-value optimization settings including doc_query_k, global_max_k, and dense_score_threshold
- **Reranking Configuration**: HTTP-based reranking with configurable URL, top-N results, and prefetch limits
- **Chunking Configuration**: Token-based and semantic chunking parameters with sensible defaults
- **S3 Storage Configuration**: MinIO-compatible storage settings for document management
- **API Authentication**: Service-level API key configuration

**Updated** Added comprehensive LLM context window configuration (llm_num_ctx: 8192), Russian lemmatization settings (bm25_lemmatize: True), retrieval parameter optimization (doc_query_k: 15, global_max_k: 10), dense scoring thresholds (dense_score_threshold: 0.5), and HTTP-based reranking configuration (reranking_enabled: False, reranker_url: http://localhost:8082, reranker_top_n: 5, reranker_prefetch_limit: 20)

Key implementation details:
- Standalone configuration class independent from CoreSettings
- Comprehensive LLM sampling parameters including temperature, top_p, top_k, and presence_penalty
- Advanced retrieval configuration with adaptive k-value calculation
- Russian lemmatization support for improved BM25 performance
- Dense score threshold filtering for confidence-based result filtering
- HTTP-based reranking with graceful fallback mechanisms
- Prefetch limit optimization for reranking performance

**Section sources**
- [packages/rag_service/src/cafetera_rag_service/config.py:8-84](file://packages/rag_service/src/cafetera_rag_service/config.py#L8-L84)

## Package-Specific Settings Classes
Each package implements its own settings class that extends CoreSettings, adding package-specific fields while maintaining configuration isolation:

### AdminSettings Class
The AdminSettings class extends CoreSettings with admin-specific configuration:

- **Admin API Key**: Secure authentication token for admin web interface
- **Package Isolation**: Inherits all CoreSettings fields while ignoring VK-specific variables
- **Configuration Validation**: Validates admin-specific settings independently
- **Environment Integration**: Loads admin settings from .env file with proper precedence

### VKSettings Class  
The VKSettings class extends CoreSettings with VK bot specific configuration:

- **VK Access Token**: Authentication token for VK community API access
- **VK Group ID**: Identifier for the target VK community/group
- **Package Isolation**: Inherits all CoreSettings fields while ignoring admin-specific variables
- **Configuration Validation**: Validates VK-specific settings independently
- **Environment Integration**: Loads VK settings from .env file with proper precedence

Both classes share the same inheritance pattern and configuration behavior, ensuring consistency across the package ecosystem.

**Section sources**
- [packages/admin/src/cafetera_admin/config.py:6-20](file://packages/admin/src/cafetera_admin/config.py#L6-L20)
- [packages/vk_bot/src/cafetera_vk_bot/config.py:4-16](file://packages/vk_bot/src/cafetera_vk_bot/config.py#L4-L16)

## Configuration Inheritance Hierarchy
The configuration system follows a clear inheritance hierarchy that promotes code reuse and maintains separation of concerns:

```mermaid
classDiagram
class BaseSettings {
<<Pydantic BaseSettings>>
+env_file : str
+env_file_encoding : str
+extra : str
}
class CoreSettings {
+database_url : str
+s3_endpoint_url : str
+s3_access_key : str
+s3_secret_key : str
+s3_bucket : str
+max_concurrent_indexing : int
}
class AdminSettings {
+admin_api_key : str
}
class VKSettings {
+vk_access_token : str
+vk_group_id : int
}
class RagServiceSettings {
+rag_service_url : str
+rag_service_api_key : str
+qdrant_url : str
+llm_provider : str
+embedding_provider : str
+llm_num_ctx : int
+bm25_lemmatize : bool
+doc_query_k : int
+global_max_k : int
+dense_score_threshold : float
+reranking_enabled : bool
+reranker_url : str
+reranker_top_n : int
+reranker_prefetch_limit : int
}
BaseSettings <|-- CoreSettings
CoreSettings <|-- AdminSettings
CoreSettings <|-- VKSettings
BaseSettings <|-- RagServiceSettings
```

**Diagram sources**
- [packages/core/src/cafetera_core/config.py:14-40](file://packages/core/src/cafetera_core/config.py#L14-L40)
- [packages/admin/src/cafetera_admin/config.py:6-20](file://packages/admin/src/cafetera_admin/config.py#L6-L20)
- [packages/vk_bot/src/cafetera_vk_bot/config.py:4-16](file://packages/vk_bot/src/cafetera_vk_bot/config.py#L4-L16)
- [packages/rag_service/src/cafetera_rag_service/config.py:8-84](file://packages/rag_service/src/cafetera_rag_service/config.py#L8-L84)

The inheritance hierarchy provides several benefits:
- **Code Reuse**: Shared storage configuration is defined once in CoreSettings
- **Type Safety**: All settings maintain proper type validation through Pydantic
- **Environment Integration**: Consistent .env file loading across all packages
- **Package Isolation**: "extra: ignore" prevents cross-package configuration interference
- **Flexibility**: RagServiceSettings operates independently for microservice deployment
- **Backward Compatibility**: Legacy Settings alias maintains compatibility

**Section sources**
- [packages/core/src/cafetera_core/config.py:14-40](file://packages/core/src/cafetera_core/config.py#L14-L40)
- [packages/admin/src/cafetera_admin/config.py:6-20](file://packages/admin/src/cafetera_admin/config.py#L6-L20)
- [packages/vk_bot/src/cafetera_vk_bot/config.py:4-16](file://packages/vk_bot/src/cafetera_vk_bot/config.py#L4-L16)
- [packages/rag_service/src/cafetera_rag_service/config.py:8-84](file://packages/rag_service/src/cafetera_rag_service/config.py#L8-L84)

## Enhanced Environment Variable Management
The package-based configuration system maintains comprehensive .env file integration with intelligent fallback behavior, package-specific isolation, and detailed configuration options:

### Environment Loading Mechanism
- **UTF-8 Encoding**: All .env files use UTF-8 encoding for international character support
- **Priority System**: Environment variables override .env file values
- **Package Isolation**: "extra: ignore" model configuration prevents cross-package interference
- **Field Binding**: Pydantic BaseSettings automatically binds environment variables to configuration fields
- **Template Support**: .env.example provides comprehensive configuration templates

### Supported Environment Variables
The system supports environment variables for all configuration categories:

**Core Settings Variables**:
- `DATABASE_URL`, `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`
- `MAX_CONCURRENT_INDEXING`

**Admin Settings Variables**:
- `ADMIN_API_KEY` (only recognized by AdminSettings)

**VK Settings Variables**:
- `VK_ACCESS_TOKEN`, `VK_GROUP_ID` (only recognized by VKSettings)

**RAG Service Variables**:
- `RAG_SERVICE_URL`, `RAG_SERVICE_API_KEY`
- `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_COLLECTION`, `QDRANT_TIMEOUT`
- `LLM_PROVIDER`, `LLM_MODEL`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_TEMPERATURE`, `LLM_NUM_CTX`, `LLM_DISABLE_THINKING`
- `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `EMBEDDING_BASE_URL`, `EMBEDDING_API_KEY`
- `SPARSE_EMBEDDING_MODEL`, `BM25_LEMMATIZE`
- `DOC_QUERY_K`, `GLOBAL_MAX_K`, `DENSE_SCORE_THRESHOLD`
- `RERANKING_ENABLED`, `RERANKER_URL`, `RERANKER_TOP_N`, `RERANKER_PREFETCH_LIMIT`
- `CHUNK_SIZE`, `CHUNKER_TOKENIZER_MODEL`
- `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`

### Environment Loading Process
```mermaid
flowchart TD
Start(["Environment Loading"]) --> CheckEnv["Check Environment Variables"]
CheckEnv --> CheckCore["Load Core Settings from .env"]
CheckEnv --> CheckAdmin["Load Admin Settings from .env"]
CheckEnv --> CheckVK["Load VK Settings from .env"]
CheckEnv --> CheckRAG["Load RagService Settings from .env"]
CheckCore --> CoreLoaded["CoreSettings Loaded"]
CheckAdmin --> AdminLoaded["AdminSettings Loaded"]
CheckVK --> VKLoaded["VKSettings Loaded"]
CheckRAG --> RAGLoaded["RagServiceSettings Loaded"]
CoreLoaded --> Merge["Merge with Environment Overrides"]
AdminLoaded --> Merge
VKLoaded --> Merge
RAGLoaded --> Merge
Merge --> Validate["Validate Configuration Types"]
Validate --> Done(["Configuration Ready"])
```

**Diagram sources**
- [packages/core/src/cafetera_core/config.py:21](file://packages/core/src/cafetera_core/config.py#L21)
- [packages/admin/src/cafetera_admin/config.py:17](file://packages/admin/src/cafetera_admin/config.py#L17)
- [packages/vk_bot/src/cafetera_vk_bot/config.py:12](file://packages/vk_bot/src/cafetera_vk_bot/config.py#L12)
- [packages/rag_service/src/cafetera_rag_service/config.py:16](file://packages/rag_service/src/cafetera_rag_service/config.py#L16)

**Section sources**
- [packages/core/src/cafetera_core/config.py:21](file://packages/core/src/cafetera_core/config.py#L21)
- [packages/admin/src/cafetera_admin/config.py:17](file://packages/admin/src/cafetera_admin/config.py#L17)
- [packages/vk_bot/src/cafetera_vk_bot/config.py:12](file://packages/vk_bot/src/cafetera_vk_bot/config.py#L12)
- [packages/rag_service/src/cafetera_rag_service/config.py:16](file://packages/rag_service/src/cafetera_rag_service/config.py#L16)
- [README.md:260-335](file://README.md#L260-L335)

## Package-Specific Configuration Examples
The package-based architecture allows for clean separation of configuration requirements across different components:

### Admin Package Configuration
The AdminSettings class provides configuration for the admin web interface:

**Environment Variables**:
```bash
# Admin configuration
ADMIN_API_KEY=your_secure_admin_api_key_here
```

**Usage Example**:
```python
from cafetera_admin.config import AdminSettings

# Load admin-specific configuration
admin_settings = AdminSettings()
print(f"Admin API Key: {admin_settings.admin_api_key}")
```

### VK Bot Package Configuration  
The VKSettings class provides configuration for VK community integration:

**Environment Variables**:
```bash
# VK bot configuration
VK_ACCESS_TOKEN=your_vk_community_token_here
VK_GROUP_ID=123456789
```

**Usage Example**:
```python
from cafetera_vk_bot.config import VKSettings

# Load VK-specific configuration
vk_settings = VKSettings()
print(f"VK Access Token: {vk_settings.vk_access_token}")
print(f"VK Group ID: {vk_settings.vk_group_id}")
```

### RAG Service Package Configuration
The RagServiceSettings class provides comprehensive configuration for the RAG microservice:

**Environment Variables**:
```bash
# RAG service configuration
RAG_SERVICE_URL=http://localhost:8001
RAG_SERVICE_API_KEY=your_service_api_key

# Qdrant configuration
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=hr_documents

# LLM configuration
LLM_PROVIDER=ollama
LLM_MODEL=qwen3.5:4b-q4_K_M
LLM_BASE_URL=http://localhost:11434
LLM_TEMPERATURE=0.3
LLM_NUM_CTX=8192
LLM_DISABLE_THINKING=true

# Embedding configuration
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=qwen3-embedding:4b-q4_K_M
EMBEDDING_BASE_URL=http://localhost:11434

# Hybrid search configuration
SPARSE_EMBEDDING_MODEL=Qdrant/bm25
BM25_LEMMATIZE=true

# Retrieval configuration
DOC_QUERY_K=15
GLOBAL_MAX_K=10
DENSE_SCORE_THRESHOLD=0.5

# HTTP-based reranking configuration
RERANKING_ENABLED=false
RERANKER_URL=http://localhost:8082
RERANKER_TOP_N=5
RERANKER_PREFETCH_LIMIT=20
```

**Usage Example**:
```python
from cafetera_rag_service.config import RagServiceSettings

# Load RAG service configuration
rag_settings = RagServiceSettings()
print(f"LLM Num Ctx: {rag_settings.llm_num_ctx}")
print(f"BM25 Lemmatize: {rag_settings.bm25_lemmatize}")
```

### Shared Core Configuration
Both packages inherit CoreSettings for shared functionality:

**Environment Variables**:
```bash
# Shared configuration (used by both packages)
DATABASE_URL=postgresql://cafetera:cafetera@localhost:5432/cafetera
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=rag-documents
MAX_CONCURRENT_INDEXING=2
```

**Usage Example**:
```python
from cafetera_core.config import CoreSettings

# Both packages inherit these settings
core_settings = CoreSettings()
print(f"Database URL: {core_settings.database_url}")
print(f"S3 Bucket: {core_settings.s3_bucket}")
```

**Section sources**
- [packages/admin/src/cafetera_admin/config.py:19](file://packages/admin/src/cafetera_admin/config.py#L19)
- [packages/vk_bot/src/cafetera_vk_bot/config.py:14-16](file://packages/vk_bot/src/cafetera_vk_bot/config.py#L14-L16)
- [packages/rag_service/src/cafetera_rag_service/config.py:8-84](file://packages/rag_service/src/cafetera_rag_service/config.py#L8-L84)
- [packages/core/src/cafetera_core/config.py:27-36](file://packages/core/src/cafetera_core/config.py#L27-L36)

## Configuration Validation and Testing
The package-based configuration system includes comprehensive validation and testing to ensure proper behavior:

### Test Structure
The test suite validates configuration behavior across all package-specific settings:

**Core Settings Tests**: Validate shared configuration defaults and environment precedence
**Admin Settings Tests**: Validate admin-specific configuration loading and isolation
**VK Settings Tests**: Validate VK-specific configuration loading and isolation
**RAG Service Settings Tests**: Validate comprehensive LLM, embedding, and retrieval configuration

### Configuration Validation Features
- **Type Safety**: Pydantic validation ensures correct data types for all configuration fields
- **Environment Precedence**: Environment variables override .env file values appropriately
- **Package Isolation**: Cross-package configuration interference is prevented
- **Default Values**: Sensible defaults are applied when environment variables are not set
- **Error Handling**: Invalid configuration values are caught during validation

### Test Examples
The test suite demonstrates proper configuration loading:

**Admin Settings Test**:
```python
def test_reads_token_from_env(self, monkeypatch):
    monkeypatch.setenv("VK_ACCESS_TOKEN", "env_test_token")
    settings = VKSettings()
    assert settings.vk_access_token == "env_test_token"
```

**Core Settings Test**:
```python
def test_default_token_is_empty(self):
    settings = VKSettings(vk_access_token="", _env_file=None)
    assert settings.vk_access_token == ""
```

**RAG Service Settings Test**:
```python
def test_defaults_for_llm(self):
    s = RagServiceSettings(_env_file=None)
    assert s.llm_num_ctx == 8192
    assert s.llm_disable_thinking is True
```

**New Configuration Tests**:
```python
def test_defaults_for_retrieval_k(self):
    s = RagServiceSettings(_env_file=None)
    assert s.doc_query_k == 15
    assert s.global_max_k == 10

def test_defaults_for_dense_score_threshold(self):
    s = RagServiceSettings(_env_file=None)
    assert s.dense_score_threshold == 0.5

def test_defaults_for_reranking(self):
    s = RagServiceSettings(_env_file=None)
    assert s.reranking_enabled is False
    assert s.reranker_url == "http://localhost:8082"
    assert s.reranker_top_n == 5
    assert s.reranker_prefetch_limit == 20
```

**Section sources**
- [tests/test_config.py:1-44](file://tests/test_config.py#L1-L44)
- [tests/test_rag_block6.py:19-38](file://tests/test_rag_block6.py#L19-L38)
- [tests/test_hybrid_rerank_retriever.py:135-180](file://tests/test_hybrid_rerank_retriever.py#L135-L180)

## Migration from Legacy Configuration
The package-based architecture maintains backward compatibility while providing enhanced functionality:

### Legacy Settings Alias
The system maintains a `Settings` alias that points to `CoreSettings` for backward compatibility:

```python
# Legacy import still works
from cafetera_core.config import Settings

# New preferred import
from cafetera_core.config import CoreSettings
```

### Migration Benefits
- **Gradual Migration**: Existing code can continue using Settings while new code uses CoreSettings
- **Improved Modularity**: Better separation of concerns across packages
- **Enhanced Isolation**: Cleaner package boundaries prevent configuration interference
- **Future-Proof**: Modern architecture supports future package additions
- **Microservice Support**: RagServiceSettings enables independent deployment

### Migration Steps
1. Update imports from `cafetera_core.config import Settings` to `cafetera_core.config import CoreSettings`
2. Continue using the same configuration patterns and environment variables
3. Leverage package-specific settings classes for new functionality
4. Consider using RagServiceSettings for microservice deployments
5. Maintain backward compatibility during transition period

**Section sources**
- [packages/core/src/cafetera_core/config.py:38-40](file://packages/core/src/cafetera_core/config.py#L38-L40)

## Security Considerations
The package-based configuration system incorporates several security best practices:

### Environment Variable Security
- **Secret Management**: All sensitive configuration (API keys, tokens) should be stored in environment variables
- **File Permissions**: .env files should have restricted permissions (600) to prevent unauthorized access
- **Version Control**: .env files should be excluded from version control systems
- **Template Files**: Provide .env.example templates with placeholder values instead of real secrets

### Package Isolation Security
- **Cross-Package Prevention**: "extra: ignore" model configuration prevents sensitive data leakage between packages
- **Minimal Exposure**: Each package only processes configuration relevant to its functionality
- **Validation**: All configuration values are validated through Pydantic for type safety

### Configuration Hardening
- **Default Values**: Use secure defaults for sensitive fields (empty strings for secrets)
- **Environment Precedence**: Ensure environment variables take precedence over .env file values
- **Error Handling**: Invalid configuration values trigger immediate validation errors

### AI Provider Security
- **API Key Management**: Store OpenAI API keys securely, never in version control
- **Model File Security**: Protect llama.cpp model files from unauthorized access
- **Local Service Security**: Restrict local Ollama service access to localhost only
- **HTTP Reranking Security**: Configure reranker URLs carefully and validate network access

**Section sources**
- [README.md:260-294](file://README.md#L260-L294)

## Development and Deployment Patterns
The package-based configuration system supports various development and deployment scenarios:

### Development Environment
- **Single .env File**: Use one .env file for all packages during development
- **Shared Configuration**: CoreSettings fields are shared across all packages
- **Package-Specific Variables**: Admin and VK settings are isolated to their respective packages
- **RAG Service Configuration**: Use RagServiceSettings for comprehensive LLM and retrieval testing
- **Local Services**: Use localhost URLs for development services
- **AI Provider Selection**: Choose Ollama for easy local development

**Development Configuration Example**:
```bash
# Development setup
ADMIN_API_KEY=my-development-key
VK_ACCESS_TOKEN=development-token
VK_GROUP_ID=123456789

# RAG service development
RAG_SERVICE_URL=http://localhost:8001
RAG_SERVICE_API_KEY=dev-key

# Ollama for local development
LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama
LLM_NUM_CTX=8192
BM25_LEMMATIZE=true
DOC_QUERY_K=15
GLOBAL_MAX_K=10
DENSE_SCORE_THRESHOLD=0.5
RERANKING_ENABLED=false
RERANKER_URL=http://localhost:8082
RERANKER_TOP_N=5
RERANKER_PREFETCH_LIMIT=20
```

### Production Environment
- **Environment Variables**: Use environment variables for production configuration
- **Secret Management**: Store sensitive values in secure secret management systems
- **Package Isolation**: Each package can be deployed independently
- **Configuration Validation**: Validate all configuration settings during startup
- **AI Provider Optimization**: Use OpenAI for production quality responses

**Production Configuration Example**:
```bash
# Production setup
ADMIN_API_KEY=${ADMIN_API_KEY}
VK_ACCESS_TOKEN=${VK_ACCESS_TOKEN}
VK_GROUP_ID=${VK_GROUP_ID}

# RAG service production
RAG_SERVICE_URL=${RAG_SERVICE_URL}
RAG_SERVICE_API_KEY=${RAG_SERVICE_API_KEY}

# OpenAI for production quality
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=openai
LLM_API_KEY=${OPENAI_API_KEY}
EMBEDDING_API_KEY=${OPENAI_API_KEY}
LLM_NUM_CTX=8192
BM25_LEMMATIZE=true
DOC_QUERY_K=15
GLOBAL_MAX_K=10
DENSE_SCORE_THRESHOLD=0.5
RERANKING_ENABLED=false
RERANKER_URL=${RERANKER_URL}
RERANKER_TOP_N=5
RERANKER_PREFETCH_LIMIT=20
```

### Microservice Deployment
- **Independent Packages**: Each package can be developed, tested, and deployed separately
- **RAG Service Independence**: RagServiceSettings enables standalone microservice deployment
- **Configuration Reuse**: CoreSettings provides consistent configuration across packages
- **Package-Specific Scaling**: Each package can scale independently based on its requirements

### Docker Deployment Scenarios
- **Compose Services**: Use docker-compose for orchestrated multi-service deployment
- **Service Isolation**: Each service runs in its own container with isolated configuration
- **Volume Management**: Persist configuration and data through named volumes
- **Network Security**: Use Docker networks for secure inter-service communication

**Section sources**
- [README.md:445-492](file://README.md#L445-L492)
- [scripts/run_all.sh:138-161](file://scripts/run_all.sh#L138-L161)
- [scripts/run_admin_docker.sh:134-146](file://scripts/run_admin_docker.sh#L134-L146)

## Troubleshooting Common Issues
Common configuration issues and their solutions:

### Configuration Not Loading
- **Verify .env File**: Ensure the .env file exists and is readable
- **Check Variable Names**: Confirm environment variable names match configuration field names
- **Validate Types**: Ensure environment values match expected data types
- **Check Package Isolation**: Verify that package-specific variables are not being ignored

### Cross-Package Interference
- **Check "extra: ignore"**: Ensure model configuration prevents cross-package variable processing
- **Verify Package Imports**: Confirm correct package-specific settings classes are being used
- **Test Isolation**: Validate that each package only processes relevant configuration variables

### Environment Variable Precedence
- **Order of Precedence**: Environment variables override .env file values
- **Debug Loading**: Print configuration values during startup to verify loading order
- **Validation**: Use Pydantic validation to catch type conversion errors

### Package-Specific Issues
- **Admin Settings**: Verify ADMIN_API_KEY is set for admin functionality
- **VK Settings**: Ensure VK_ACCESS_TOKEN and VK_GROUP_ID are configured for bot functionality
- **Core Settings**: Validate shared configuration fields for all packages
- **RAG Service Settings**: Ensure comprehensive LLM, embedding, and retrieval configuration is properly set

### New Parameter Issues
- **LLM Context Window**: Verify LLM_NUM_CTX is set appropriately for your model
- **Russian Lemmatization**: Ensure BM25_LEMMATIZE is set correctly for Russian corpora
- **Retrieval Parameters**: Validate DOC_QUERY_K and GLOBAL_MAX_K for optimal performance
- **Score Thresholds**: Adjust DENSE_SCORE_THRESHOLD based on your confidence requirements
- **HTTP Reranking**: Verify RERANKING_ENABLED, RERANKER_URL, RERANKER_TOP_N, and RERANKER_PREFETCH_LIMIT are configured correctly

### Environment Variable Loading Issues
- **Template Usage**: Use .env.example as template, copy to .env for customization
- **Variable Scope**: Ensure variables are exported before use in scripts
- **File Encoding**: Verify .env file uses UTF-8 encoding
- **Script Integration**: Check that shell scripts properly load .env variables

**Section sources**
- [scripts/run_all.sh:138-161](file://scripts/run_all.sh#L138-L161)
- [scripts/run_admin_docker.sh:134-146](file://scripts/run_admin_docker.sh#L134-L146)
- [README.md:523-578](file://README.md#L523-L578)

## Best Practices
Follow these best practices for effective configuration management:

### Configuration Organization
- **Use Package-Specific Classes**: Use AdminSettings for admin configuration, VKSettings for VK bot configuration, RagServiceSettings for RAG service configuration
- **Leverage CoreSettings**: Share common storage configuration through CoreSettings inheritance
- **Maintain Separation**: Keep package-specific configuration separate and isolated
- **Document Fields**: Provide clear documentation for all configuration fields

### Environment Management
- **Use .env Files**: Store development configuration in .env files
- **Use Environment Variables**: Store production configuration in environment variables
- **Secure Secrets**: Never commit sensitive configuration to version control
- **Validate Configuration**: Implement startup validation for critical configuration fields
- **Template Usage**: Always use .env.example as template for new installations

### Package Development
- **Extend CoreSettings**: AdminSettings and VKSettings should extend CoreSettings
- **Use "extra: ignore"**: Prevent cross-package configuration interference
- **Test Isolation**: Validate that each package processes only relevant configuration
- **Maintain Compatibility**: Preserve backward compatibility during configuration changes
- **Consider Microservices**: Use RagServiceSettings for independent microservice deployment

### Security Practices
- **Restrict File Permissions**: Set appropriate permissions on .env files (600)
- **Use Secure Defaults**: Initialize sensitive fields with empty values
- **Validate Input**: Use Pydantic validation for all configuration inputs
- **Monitor Access**: Implement logging for configuration loading and validation
- **Secret Rotation**: Regularly rotate API keys and tokens in production

### Deployment Best Practices
- **Environment Separation**: Use different .env files for development, staging, and production
- **Configuration Validation**: Validate all configuration settings during deployment
- **Service Health Checks**: Implement health checks for all configured services
- **Backup Strategy**: Backup configuration files and database regularly
- **Monitoring**: Monitor configuration-related errors and service health

**Section sources**
- [README.md:260-335](file://README.md#L260-L335)
- [packages/core/src/cafetera_core/config.py:21](file://packages/core/src/cafetera_core/config.py#L21)
- [packages/rag_service/src/cafetera_rag_service/config.py:16](file://packages/rag_service/src/cafetera_rag_service/config.py#L16)