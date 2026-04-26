# Configuration Management

<cite>
**Referenced Files in This Document**
- [packages/core/src/cafetera_core/config.py](file://packages/core/src/cafetera_core/config.py)
- [packages/admin/src/cafetera_admin/config.py](file://packages/admin/src/cafetera_admin/config.py)
- [packages/vk_bot/src/cafetera_vk_bot/config.py](file://packages/vk_bot/src/cafetera_vk_bot/config.py)
- [packages/core/pyproject.toml](file://packages/core/pyproject.toml)
- [packages/admin/pyproject.toml](file://packages/admin/pyproject.toml)
- [packages/vk_bot/pyproject.toml](file://packages/vk_bot/pyproject.toml)
- [pyproject.toml](file://pyproject.toml)
- [scripts/run_all.sh](file://scripts/run_all.sh)
- [scripts/run_admin_docker.sh](file://scripts/run_admin_docker.sh)
- [tests/test_config.py](file://tests/test_config.py)
- [docker-compose.yml](file://docker-compose.yml)
- [README.md](file://README.md)
</cite>

## Update Summary
**Changes Made**
- Updated to reflect complete restructuring of configuration system from monolithic Settings class to inheritance-based CoreSettings → AdminSettings/VKSettings architecture
- Documented package isolation mechanism using "extra: ignore" model configuration
- Added comprehensive coverage of shared configuration inheritance pattern
- Updated all configuration examples to reflect new package-based architecture
- Enhanced security considerations for package isolation
- Added detailed migration guidance from legacy Settings class

## Table of Contents
1. [Introduction](#introduction)
2. [Package-Based Configuration Architecture](#package-based-configuration-architecture)
3. [Core Settings Foundation](#core-settings-foundation)
4. [Package-Specific Settings Classes](#package-specific-settings-classes)
5. [Configuration Inheritance Hierarchy](#configuration-inheritance-hierarchy)
6. [Enhanced Environment Variable Management](#enhanced-environment-variable-management)
7. [Package-Specific Configuration Examples](#package-specific-configuration-examples)
8. [Configuration Validation and Testing](#configuration-validation-and-testing)
9. [Migration from Legacy Configuration](#migration-from-legacy-configuration)
10. [Security Considerations](#security-considerations)
11. [Development and Deployment Patterns](#development-and-deployment-patterns)
12. [Troubleshooting Common Issues](#troubleshooting-common-issues)
13. [Best Practices](#best-practices)

## Introduction
This document explains the completely restructured configuration management system in cafetera_hr_bot, which has evolved from a monolithic Settings class to a sophisticated inheritance-based architecture. The new system centers around CoreSettings as the foundation for shared configuration, with AdminSettings and VKSettings extending CoreSettings for package-specific functionality. This architectural change provides better separation of concerns, package isolation, and maintainability while preserving backward compatibility.

The configuration system now follows a clear inheritance pattern where CoreSettings contains all shared RAG, storage, LLM, and embedding configurations, while AdminSettings and VKSettings extend CoreSettings with their respective package-specific fields. The "extra: ignore" model configuration ensures that environment variables intended for other packages are silently ignored, preventing cross-package interference.

**Section sources**
- [packages/core/src/cafetera_core/config.py:14-67](file://packages/core/src/cafetera_core/config.py#L14-L67)
- [packages/admin/src/cafetera_admin/config.py:6-19](file://packages/admin/src/cafetera_admin/config.py#L6-L19)
- [packages/vk_bot/src/cafetera_vk_bot/config.py:4-15](file://packages/vk_bot/src/cafetera_vk_bot/config.py#L4-L15)

## Package-Based Configuration Architecture
The enhanced configuration system follows a modular package architecture with clear separation between shared and package-specific configurations:

- **Core Package**: Contains the CoreSettings class with shared RAG, storage, LLM, and embedding configurations
- **Admin Package**: Extends CoreSettings with admin-specific fields and maintains package isolation
- **VK Bot Package**: Extends CoreSettings with VK-specific fields and maintains package isolation
- **Inheritance Pattern**: All package-specific settings classes inherit from CoreSettings
- **Package Isolation**: Each package ignores environment variables not relevant to its configuration
- **Shared Dependencies**: All packages depend on the core package for shared functionality

```mermaid
graph TB
subgraph "Package-Based Configuration Architecture"
CoreSettings["CoreSettings<br/>(Shared Configuration)"]
AdminSettings["AdminSettings<br/>(Extends CoreSettings)"]
VKSettings["VKSettings<br/>(Extends CoreSettings)"]
ExtraIgnore["model_config = {'extra': 'ignore'}"]
end
subgraph "Core Package"
CoreConfig["CoreSettings Definition"]
CoreFields["RAG Settings<br/>LLM Settings<br/>Embedding Settings<br/>Storage Settings<br/>Chunking Settings<br/>Hybrid Search Settings<br/>Reranking Settings"]
end
subgraph "Admin Package"
AdminConfig["AdminSettings Definition"]
AdminFields["Admin API Key"]
end
subgraph "VK Bot Package"
VKConfig["VKSettings Definition"]
VKFields["VK Access Token<br/>VK Group ID"]
end
CoreSettings --> AdminSettings
CoreSettings --> VKSettings
CoreSettings --> CoreConfig
AdminSettings --> AdminConfig
VKSettings --> VKConfig
ExtraIgnore --> AdminSettings
ExtraIgnore --> VKSettings
CoreFields --> CoreConfig
AdminFields --> AdminConfig
VKFields --> VKConfig
```

**Diagram sources**
- [packages/core/src/cafetera_core/config.py:14-67](file://packages/core/src/cafetera_core/config.py#L14-L67)
- [packages/admin/src/cafetera_admin/config.py:6-19](file://packages/admin/src/cafetera_admin/config.py#L6-L19)
- [packages/vk_bot/src/cafetera_vk_bot/config.py:4-15](file://packages/vk_bot/src/cafetera_vk_bot/config.py#L4-L15)

**Section sources**
- [packages/core/src/cafetera_core/config.py:14-67](file://packages/core/src/cafetera_core/config.py#L14-L67)
- [packages/admin/src/cafetera_admin/config.py:6-19](file://packages/admin/src/cafetera_admin/config.py#L6-L19)
- [packages/vk_bot/src/cafetera_vk_bot/config.py:4-15](file://packages/vk_bot/src/cafetera_vk_bot/config.py#L4-L15)

## Core Settings Foundation
The CoreSettings class serves as the foundation for all package-specific configurations, containing shared settings that are inherited by AdminSettings and VKSettings:

- **Shared RAG Configuration**: Qdrant URL, API key, and collection settings for vector storage
- **LLM Provider Configuration**: Provider selection, model names, base URLs, and API keys
- **Embedding Provider Configuration**: Separate embedding provider settings with independent configuration
- **Storage Configuration**: Database connections, S3 storage settings, and bucket management
- **Indexing Configuration**: Concurrency limits for document processing operations
- **Chunking Configuration**: Token-based and semantic chunking parameters with sensible defaults
- **Hybrid Search Configuration**: Sparse embedding model settings for BM25-based lexical matching
- **Reranking Configuration**: ColBERT-based reranking with conditional activation and performance tuning
- **Environment File Integration**: UTF-8 encoded .env file loading with Pydantic BaseSettings
- **Package Isolation**: "extra: ignore" model configuration prevents cross-package interference

Key implementation details:
- Inherits from Pydantic BaseSettings for type-safe configuration loading
- Uses UTF-8 encoding for .env file compatibility
- Includes comprehensive configuration fields for all shared components
- Provides sensible defaults for development and production environments
- Supports environment variable precedence over defaults
- Maintains backward compatibility with legacy Settings alias

**Section sources**
- [packages/core/src/cafetera_core/config.py:14-67](file://packages/core/src/cafetera_core/config.py#L14-L67)

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
- [packages/admin/src/cafetera_admin/config.py:6-19](file://packages/admin/src/cafetera_admin/config.py#L6-L19)
- [packages/vk_bot/src/cafetera_vk_bot/config.py:4-15](file://packages/vk_bot/src/cafetera_vk_bot/config.py#L4-L15)

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
+qdrant_url : str
+llm_provider : str
+embedding_provider : str
+database_url : str
+chunk_size : int
+sparse_embedding_model : str
+reranking_enabled : bool
}
class AdminSettings {
+admin_api_key : str
}
class VKSettings {
+vk_access_token : str
+vk_group_id : int
}
BaseSettings <|-- CoreSettings
CoreSettings <|-- AdminSettings
CoreSettings <|-- VKSettings
```

**Diagram sources**
- [packages/core/src/cafetera_core/config.py:14-67](file://packages/core/src/cafetera_core/config.py#L14-L67)
- [packages/admin/src/cafetera_admin/config.py:6-19](file://packages/admin/src/cafetera_admin/config.py#L6-L19)
- [packages/vk_bot/src/cafetera_vk_bot/config.py:4-15](file://packages/vk_bot/src/cafetera_vk_bot/config.py#L4-L15)

The inheritance hierarchy provides several benefits:
- **Code Reuse**: Shared configuration fields are defined once in CoreSettings
- **Type Safety**: All settings maintain proper type validation through Pydantic
- **Environment Integration**: Consistent .env file loading across all packages
- **Package Isolation**: "extra: ignore" prevents cross-package configuration interference
- **Backward Compatibility**: Legacy Settings alias maintains compatibility

**Section sources**
- [packages/core/src/cafetera_core/config.py:14-67](file://packages/core/src/cafetera_core/config.py#L14-L67)
- [packages/admin/src/cafetera_admin/config.py:6-19](file://packages/admin/src/cafetera_admin/config.py#L6-L19)
- [packages/vk_bot/src/cafetera_vk_bot/config.py:4-15](file://packages/vk_bot/src/cafetera_vk_bot/config.py#L4-L15)

## Enhanced Environment Variable Management
The package-based configuration system maintains comprehensive .env file integration with intelligent fallback behavior, package-specific isolation, and detailed AI provider configuration options:

### Environment Loading Mechanism
- **UTF-8 Encoding**: All .env files use UTF-8 encoding for international character support
- **Priority System**: Environment variables override .env file values
- **Package Isolation**: "extra: ignore" model configuration prevents cross-package interference
- **Field Binding**: Pydantic BaseSettings automatically binds environment variables to configuration fields
- **Template Support**: .env.example provides comprehensive configuration templates

### Supported Environment Variables
The system supports environment variables for all configuration categories:

**Core Settings Variables**:
- `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_COLLECTION`
- `LLM_PROVIDER`, `LLM_MODEL`, `LLM_BASE_URL`, `LLM_API_KEY`
- `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `EMBEDDING_BASE_URL`, `EMBEDDING_API_KEY`
- `DATABASE_URL`, `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`
- `MAX_CONCURRENT_INDEXING`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `CHUNK_STRATEGY`
- `SPARSE_EMBEDDING_MODEL`, `RERANKING_ENABLED`, `COLBERT_RERANK_MODEL`

**Admin Settings Variables**:
- `ADMIN_API_KEY` (only recognized by AdminSettings)

**VK Settings Variables**:
- `VK_ACCESS_TOKEN`, `VK_GROUP_ID` (only recognized by VKSettings)

### Environment Loading Process
```mermaid
flowchart TD
Start(["Environment Loading"]) --> CheckEnv["Check Environment Variables"]
CheckEnv --> CheckCore["Load Core Settings from .env"]
CheckEnv --> CheckAdmin["Load Admin Settings from .env"]
CheckEnv --> CheckVK["Load VK Settings from .env"]
CheckCore --> CoreLoaded["CoreSettings Loaded"]
CheckAdmin --> AdminLoaded["AdminSettings Loaded"]
CheckVK --> VKLoaded["VKSettings Loaded"]
CoreLoaded --> Merge["Merge with Environment Overrides"]
AdminLoaded --> Merge
VKLoaded --> Merge
Merge --> Validate["Validate Configuration Types"]
Validate --> Done(["Configuration Ready"])
```

**Diagram sources**
- [packages/core/src/cafetera_core/config.py:21](file://packages/core/src/cafetera_core/config.py#L21)
- [packages/admin/src/cafetera_admin/config.py:17](file://packages/admin/src/cafetera_admin/config.py#L17)
- [packages/vk_bot/src/cafetera_vk_bot/config.py:12](file://packages/vk_bot/src/cafetera_vk_bot/config.py#L12)

**Section sources**
- [packages/core/src/cafetera_core/config.py:21](file://packages/core/src/cafetera_core/config.py#L21)
- [packages/admin/src/cafetera_admin/config.py:17](file://packages/admin/src/cafetera_admin/config.py#L17)
- [packages/vk_bot/src/cafetera_vk_bot/config.py:12](file://packages/vk_bot/src/cafetera_vk_bot/config.py#L12)
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

### Shared Core Configuration
Both packages inherit CoreSettings for shared functionality:

**Environment Variables**:
```bash
# Shared configuration (used by both packages)
QDRANT_URL=http://localhost:6333
LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama
DATABASE_URL=postgresql://cafetera:cafetera@localhost:5432/cafetera
```

**Usage Example**:
```python
from cafetera_core.config import CoreSettings

# Both packages inherit these settings
core_settings = CoreSettings()
print(f"Qdrant URL: {core_settings.qdrant_url}")
print(f"LLM Provider: {core_settings.llm_provider}")
```

**Section sources**
- [packages/admin/src/cafetera_admin/config.py:19](file://packages/admin/src/cafetera_admin/config.py#L19)
- [packages/vk_bot/src/cafetera_vk_bot/config.py:14-15](file://packages/vk_bot/src/cafetera_vk_bot/config.py#L14-L15)
- [packages/core/src/cafetera_core/config.py:23-48](file://packages/core/src/cafetera_core/config.py#L23-L48)

## Configuration Validation and Testing
The package-based configuration system includes comprehensive validation and testing to ensure proper behavior:

### Test Structure
The test suite validates configuration behavior across all package-specific settings:

**Core Settings Tests**: Validate shared configuration defaults and environment precedence
**Admin Settings Tests**: Validate admin-specific configuration loading and isolation
**VK Settings Tests**: Validate VK-specific configuration loading and isolation

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

**Section sources**
- [tests/test_config.py:1-28](file://tests/test_config.py#L1-L28)

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

### Migration Steps
1. Update imports from `cafetera_core.config import Settings` to `cafetera_core.config import CoreSettings`
2. Continue using the same configuration patterns and environment variables
3. Leverage package-specific settings classes for new functionality
4. Maintain backward compatibility during transition period

**Section sources**
- [packages/core/src/cafetera_core/config.py:69-71](file://packages/core/src/cafetera_core/config.py#L69-L71)

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

**Section sources**
- [README.md:260-294](file://README.md#L260-L294)

## Development and Deployment Patterns
The package-based configuration system supports various development and deployment scenarios:

### Development Environment
- **Single .env File**: Use one .env file for all packages during development
- **Shared Configuration**: CoreSettings fields are shared across all packages
- **Package-Specific Variables**: Admin and VK settings are isolated to their respective packages
- **Local Services**: Use localhost URLs for development services
- **AI Provider Selection**: Choose Ollama for easy local development

**Development Configuration Example**:
```bash
# Development setup
ADMIN_API_KEY=my-development-key
VK_ACCESS_TOKEN=development-token
VK_GROUP_ID=123456789

# Ollama for local development
LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama
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

# OpenAI for production quality
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=openai
LLM_API_KEY=${OPENAI_API_KEY}
EMBEDDING_API_KEY=${OPENAI_API_KEY}
```

### Multi-Package Deployment
- **Independent Packages**: Each package can be developed, tested, and deployed separately
- **Shared Dependencies**: All packages depend on the core package for shared functionality
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
- **Use Package-Specific Classes**: Use AdminSettings for admin configuration, VKSettings for VK bot configuration
- **Leverage CoreSettings**: Share common configuration through CoreSettings inheritance
- **Maintain Separation**: Keep package-specific configuration separate and isolated
- **Document Fields**: Provide clear documentation for all configuration fields

### Environment Management
- **Use .env Files**: Store development configuration in .env files
- **Use Environment Variables**: Store production configuration in environment variables
- **Secure Secrets**: Never commit sensitive configuration to version control
- **Validate Configuration**: Implement startup validation for critical configuration fields
- **Template Usage**: Always use .env.example as template for new installations

### Package Development
- **Extend CoreSettings**: All package-specific settings should extend CoreSettings
- **Use "extra: ignore"**: Prevent cross-package configuration interference
- **Test Isolation**: Validate that each package processes only relevant configuration
- **Maintain Compatibility**: Preserve backward compatibility during configuration changes

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