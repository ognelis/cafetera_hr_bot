# LLM Providers Configuration

<cite>
**Referenced Files in This Document**
- [providers.md](file://docs/providers.md)
- [llamacpp.md](file://docs/llamacpp.md)
- [config.py](file://packages/rag_service/src/cafetera_rag_service/config.py)
- [chain.py](file://packages/rag_service/src/cafetera_rag_service/rag/chain.py)
- [run_all.sh](file://scripts/run_all.sh)
- [run_admin.sh](file://scripts/run_admin.sh)
- [run_llama_llm.sh](file://scripts/run_llama_llm.sh)
- [run_llama_embeddings.sh](file://scripts/run_llama_embeddings.sh)
- [test_rag_block6.py](file://tests/test_rag_block6.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Provider Types and Selection](#provider-types-and-selection)
3. [Configuration Architecture](#configuration-architecture)
4. [Environment Variables Reference](#environment-variables-reference)
5. [Provider-Specific Configuration](#provider-specific-configuration)
6. [Deployment Scripts Integration](#deployment-scripts-integration)
7. [Testing and Validation](#testing-and-validation)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Best Practices](#best-practices)
10. [Conclusion](#conclusion)

## Introduction

The LLM Providers Configuration system in this project enables flexible deployment of AI models through three distinct providers: Ollama, OpenAI, and llama.cpp. This configuration framework supports both local development and production deployments, allowing teams to choose the most appropriate AI infrastructure based on their requirements for cost, performance, and control.

The system is designed to be modular and extensible, supporting mixed-provider configurations where LLM and embedding models can be served by different providers simultaneously. This flexibility enables organizations to optimize for specific use cases, such as using high-quality cloud models for LLM inference while maintaining cost-effective local embeddings.

## Provider Types and Selection

The project supports three primary AI providers, each with distinct characteristics and use cases:

### Ollama Provider
- **Local Deployment**: Runs entirely on local hardware
- **Cost**: Free and open-source
- **Data Privacy**: No external data transmission
- **Default Choice**: Recommended for initial setup and development
- **Model Management**: Automatic model downloading and management

### OpenAI Provider
- **Cloud-Based**: Hosted on OpenAI's infrastructure
- **Cost**: Pay-per-token pricing
- **Performance**: High-quality models with extensive capabilities
- **API Integration**: Direct integration with OpenAI's API ecosystem
- **Key Management**: Requires API key configuration

### llama.cpp Provider
- **Local Deployment**: Maximum control over model execution
- **Cost**: Free with hardware requirements
- **Customization**: Fine-grained control over memory usage and performance
- **GPU Acceleration**: Automatic detection and utilization of hardware acceleration
- **Model Formats**: Uses GGUF format for optimized local inference

```mermaid
flowchart TD
A["Provider Selection"] --> B{"Choose Provider"}
B --> C["Ollama<br/>Local, Free, Default"]
B --> D["OpenAI<br/>Cloud, Paid, High Quality"]
B --> E["llama.cpp<br/>Local, Customizable, GPU Support"]
C --> F["Automatic Model Management"]
D --> G["API Key Required"]
E --> H["Hardware Acceleration"]
F --> I["Development Ready"]
G --> J["Production Scale"]
H --> K["Maximum Control"]
```

**Diagram sources**
- [providers.md:14](file://docs/providers.md#L14-L18)
- [providers.md:28](file://docs/providers.md#L28-L63)

**Section sources**
- [providers.md:12](file://docs/providers.md#L12-L21)
- [providers.md:28](file://docs/providers.md#L28-L63)

## Configuration Architecture

The configuration system follows a layered approach with environment variables driving provider selection and model parameters. The architecture ensures flexibility while maintaining consistency across different deployment scenarios.

### Core Configuration Structure

The system uses Pydantic BaseSettings for type-safe configuration management, supporting both environment variables and .env file loading. The configuration is divided into logical sections for different system components.

```mermaid
classDiagram
class RagServiceSettings {
+string llm_provider
+string llm_model
+string llm_base_url
+string llm_api_key
+float llm_temperature
+int llm_num_ctx
+string embedding_provider
+string embedding_model
+string embedding_base_url
+string embedding_api_key
+bool reranking_enabled
+string reranker_url
}
class CoreSettings {
+string rag_service_url
+string rag_service_api_key
+string database_url
+string s3_endpoint_url
}
class ProviderSelection {
+select_llm_provider()
+select_embedding_provider()
+validate_configuration()
}
RagServiceSettings --> ProviderSelection : "uses"
CoreSettings --> RagServiceSettings : "extends"
```

**Diagram sources**
- [config.py:8](file://packages/rag_service/src/cafetera_rag_service/config.py#L8-L84)
- [run_all.sh:218](file://scripts/run_all.sh#L218-L300)

### Environment Variable Priority

The configuration system implements a hierarchical approach to environment variable resolution:

1. **Command Line Arguments**: Highest priority for runtime overrides
2. **Environment Variables**: System-level configuration
3. .env File: Project-level defaults with lower priority
4. **Application Defaults**: Built-in fallback values

**Section sources**
- [config.py:16](file://packages/rag_service/src/cafetera_rag_service/config.py#L16-L20)
- [run_all.sh:171](file://scripts/run_all.sh#L171-L201)

## Environment Variables Reference

The LLM providers configuration relies on a comprehensive set of environment variables that control provider selection, model parameters, and service connectivity.

### Core Provider Variables

| Variable | Purpose | Default Value | Provider Compatibility |
|----------|---------|---------------|----------------------|
| `LLM_PROVIDER` | Select LLM provider | `ollama` | All providers |
| `LLM_MODEL` | LLM model identifier | `qwen3.5:4b-q4_K_M` | All providers |
| `LLM_BASE_URL` | LLM service endpoint | `http://localhost:11434` | All providers |
| `LLM_API_KEY` | LLM authentication key | Empty | OpenAI only |
| `EMBEDDING_PROVIDER` | Select embedding provider | `ollama` | All providers |
| `EMBEDDING_MODEL` | Embedding model identifier | `qwen3-embedding:4b-q4_K_M` | All providers |
| `EMBEDDING_BASE_URL` | Embedding service endpoint | `http://localhost:11434` | All providers |
| `EMBEDDING_API_KEY` | Embedding authentication key | Empty | OpenAI only |

### Advanced Configuration Variables

| Variable | Purpose | Default Value | Provider Specific |
|----------|---------|---------------|-------------------|
| `LLM_TEMPERATURE` | Generation randomness | `0.3` | All providers |
| `LLM_NUM_CTX` | Context window size | `8192` | Ollama/llama.cpp |
| `LLM_TOP_P` | Nucleus sampling threshold | Not set | OpenAI-compatible |
| `LLM_TOP_K` | Top-k sampling parameter | Not set | OpenAI-compatible |
| `LLM_PRESENCE_PENALTY` | Token presence penalty | Not set | OpenAI-compatible |
| `LLM_DISABLE_THINKING` | Disable reasoning mode | `True` | Ollama/llama.cpp |
| `OLLAMA_URL` | Ollama service address | `http://localhost:11434` | Ollama only |
| `LLM_N_GPU_LAYERS` | GPU acceleration layers | Auto-detected | llama.cpp only |
| `EMBED_N_GPU_LAYERS` | Embedding GPU layers | Auto-detected | llama.cpp only |

### Service Integration Variables

| Variable | Purpose | Default Value | Service |
|----------|---------|---------------|---------|
| `QDRANT_URL` | Vector database endpoint | `http://localhost:6333` | Qdrant |
| `DATABASE_URL` | PostgreSQL connection | `postgresql://cafetera:cafetera@localhost:5432/cafetera` | Database |
| `S3_ENDPOINT_URL` | Object storage endpoint | `http://localhost:9000` | MinIO |
| `RAG_SERVICE_URL` | Internal service address | `http://localhost:8001` | RAG Service |
| `RAG_SERVICE_API_KEY` | Service authentication | Empty | RAG Service |

**Section sources**
- [config.py:29](file://packages/rag_service/src/cafetera_rag_service/config.py#L29-L84)
- [run_all.sh:171](file://scripts/run_all.sh#L171-L201)

## Provider-Specific Configuration

Each provider requires specific configuration parameters and initialization procedures. The system handles provider-specific setup automatically based on environment variables.

### Ollama Configuration

Ollama provides the simplest setup with automatic model management and local execution:

```mermaid
sequenceDiagram
participant User as User
participant Script as run_all.sh
participant Ollama as Ollama Server
participant Models as Model Registry
User->>Script : Select Ollama provider
Script->>Ollama : Check service availability
Ollama-->>Script : Service ready
Script->>Models : Verify model existence
Models-->>Script : Model available
Script->>Ollama : Initialize service
Ollama-->>Script : Ready for inference
```

**Diagram sources**
- [run_all.sh:407](file://scripts/run_all.sh#L407-L409)
- [run_all.sh:361](file://scripts/run_all.sh#L361-L403)

### OpenAI Configuration

OpenAI requires API key configuration and operates as a remote service:

```mermaid
flowchart TD
A["OpenAI Setup"] --> B["API Key Configuration"]
B --> C["Endpoint Validation"]
C --> D["Rate Limit Checking"]
D --> E["Service Initialization"]
F["Model Configuration"] --> G["GPT-4o-mini"]
G --> H["Token Budget Management"]
E --> I["Ready for Production"]
H --> I
```

**Diagram sources**
- [run_all.sh:411](file://scripts/run_all.sh#L411-L416)
- [config.py:30](file://packages/rag_service/src/cafetera_rag_service/config.py#L30-L34)

### llama.cpp Configuration

llama.cpp offers maximum customization with manual model management and GPU acceleration:

```mermaid
flowchart TD
A["llama.cpp Setup"] --> B["GPU Detection"]
B --> C{"GPU Type?"}
C --> |Apple Silicon| D["Metal Acceleration"]
C --> |NVIDIA| E["CUDA Acceleration"]
C --> |Other| F["CPU Only"]
D --> G["Model Loading"]
E --> G
F --> G
G --> H["Server Initialization"]
H --> I["Port Configuration"]
I --> J["Service Ready"]
```

**Diagram sources**
- [run_llama_llm.sh:23](file://scripts/run_llama_llm.sh#L23-L43)
- [run_llama_embeddings.sh:23](file://scripts/run_llama_embeddings.sh#L23-L43)

**Section sources**
- [run_all.sh:218](file://scripts/run_all.sh#L218-L300)
- [run_llama_llm.sh:1](file://scripts/run_llama_llm.sh#L1-L125)
- [run_llama_embeddings.sh:1](file://scripts/run_llama_embeddings.sh#L1-L121)

## Deployment Scripts Integration

The deployment scripts provide automated configuration and service management across different providers and environments.

### Interactive Provider Selection

The system offers interactive selection through shell scripts with predefined options:

```mermaid
flowchart TD
A["Script Execution"] --> B["Display Provider Options"]
B --> C{"User Selection"}
C --> |1| D["Ollama Selected"]
C --> |2| E["OpenAI Selected"]
C --> |3| F["llama.cpp Selected"]
D --> G["Set Ollama Defaults"]
E --> H["Prompt for API Key"]
F --> I["Configure Local Servers"]
G --> J["Start Services"]
H --> J
I --> J
```

**Diagram sources**
- [run_all.sh:218](file://scripts/run_all.sh#L218-L258)
- [run_admin.sh:164](file://scripts/run_admin.sh#L164-L203)

### Automated Service Management

The scripts handle service lifecycle management including startup, health checking, and cleanup:

| Service | Port | Purpose | Startup Method |
|---------|------|---------|----------------|
| Ollama | 11434 | Local model serving | Automatic |
| LLM Server | 8080 | Language model inference | Manual |
| Embedding Server | 8090 | Document vector generation | Manual |
| Reranker Server | 8082 | Result ranking | Optional |
| Qdrant | 6333 | Vector database | Docker Compose |
| MinIO | 9000 | Object storage | Docker Compose |
| PostgreSQL | 5432 | Metadata storage | Docker Compose |

**Section sources**
- [run_all.sh:407](file://scripts/run_all.sh#L407-L439)
- [run_admin.sh:426](file://scripts/run_admin.sh#L426-L445)

## Testing and Validation

The configuration system includes comprehensive testing to validate provider selection and environment variable handling.

### Configuration Validation Tests

The test suite validates environment variable loading and provider-specific configurations:

```mermaid
sequenceDiagram
participant Test as Test Suite
participant Config as Configuration Loader
participant Provider as Provider Factory
participant Service as Service Instance
Test->>Config : Load environment variables
Config->>Config : Validate required fields
Config->>Provider : Create provider instance
Provider->>Service : Initialize service
Service-->>Provider : Service ready
Provider-->>Config : Provider configured
Config-->>Test : Configuration validated
```

**Diagram sources**
- [test_rag_block6.py:53](file://tests/test_rag_block6.py#L53-L62)
- [test_rag_block6.py:261](file://tests/test_rag_block6.py#L261-L277)

### Provider-Specific Testing

The testing framework includes provider-specific validation for different configuration scenarios:

| Test Category | Provider Focus | Validation Scope |
|---------------|----------------|------------------|
| Basic Configuration | All providers | Environment variable loading |
| Provider Dispatch | All providers | Correct provider instantiation |
| Llama.cpp Specific | llama.cpp | OpenAI-compatible interface |
| OpenAI Integration | OpenAI | API key validation and service health |
| Mixed Provider Setup | Both | Separate provider configurations |

**Section sources**
- [test_rag_block6.py:40](file://tests/test_rag_block6.py#L40-L62)
- [test_rag_block6.py:242](file://tests/test_rag_block6.py#L242-L280)

## Troubleshooting Guide

Common issues and solutions for LLM providers configuration:

### Provider Selection Issues

**Problem**: Provider not responding or unavailable
- **Solution**: Verify service endpoints and network connectivity
- **Check**: Use curl commands to test service health
- **Debug**: Review service logs for startup errors

**Problem**: Model not found or loading failures
- **Solution**: Ensure model files exist in correct location
- **Check**: Verify model names match configuration
- **Debug**: Review model download logs

### Configuration Issues

**Problem**: Environment variables not taking effect
- **Solution**: Check variable naming and case sensitivity
- **Check**: Verify .env file syntax and encoding
- **Debug**: Use print statements to trace variable loading

**Problem**: Mixed provider configuration conflicts
- **Solution**: Ensure separate endpoints for each provider
- **Check**: Verify port assignments don't overlap
- **Debug**: Test each provider independently first

### Performance Issues

**Problem**: Slow inference or memory usage
- **Solution**: Adjust context window sizes and GPU layer settings
- **Check**: Monitor system resource usage during inference
- **Debug**: Profile individual components separately

**Section sources**
- [run_all.sh:311](file://scripts/run_all.sh#L311-L338)
- [run_llama_llm.sh:74](file://scripts/run_llama_llm.sh#L74-L78)

## Best Practices

### Provider Selection Guidelines

1. **Development Environment**: Use Ollama for fastest setup and iteration
2. **Production Deployment**: Consider OpenAI for highest quality with proper SLA
3. **Resource-Constrained**: Use llama.cpp with appropriate GPU acceleration
4. **Mixed Strategy**: Use different providers for LLM and embeddings based on requirements

### Configuration Management

1. **Environment Separation**: Use separate .env files for different environments
2. **Variable Documentation**: Maintain inline documentation for all configuration variables
3. **Validation**: Implement configuration validation in CI/CD pipeline
4. **Security**: Store API keys in secure vaults, not in version control

### Performance Optimization

1. **GPU Utilization**: Enable GPU acceleration when available
2. **Context Window**: Adjust context sizes based on model capabilities
3. **Batch Processing**: Optimize batch sizes for embedding generation
4. **Caching**: Implement result caching for repeated queries

### Monitoring and Maintenance

1. **Health Checks**: Implement regular service health monitoring
2. **Logging**: Configure comprehensive logging for debugging
3. **Updates**: Regularly update models and dependencies
4. **Backup**: Implement backup strategies for trained models

## Conclusion

The LLM Providers Configuration system provides a robust, flexible framework for deploying AI models across different providers and environments. The system's modular design allows teams to optimize for their specific requirements while maintaining consistency and reliability.

Key strengths of the configuration system include:

- **Multi-provider Support**: Seamless switching between Ollama, OpenAI, and llama.cpp
- **Flexible Deployment**: Support for local development and production environments
- **Comprehensive Testing**: Thorough validation of configuration scenarios
- **Automated Management**: Scripts handle service lifecycle and dependency management
- **Extensible Architecture**: Foundation for adding new providers and configurations

The system's design enables organizations to start with the simplest configuration (Ollama) and scale to production-grade deployments with OpenAI or custom llama.cpp setups as requirements evolve.