# LLM Providers Configuration

<cite>
**Referenced Files in This Document**
- [providers.md](file://docs/providers.md)
- [llamacpp.md](file://docs/llamacpp.md)
- [config.py](file://packages/rag_service/src/cafetera_rag_service/config.py)
- [chain.py](file://packages/rag_service/src/cafetera_rag_service/rag/chain.py)
- [retriever.py](file://packages/rag_service/src/cafetera_rag_service/rag/retriever.py)
- [instructed_embeddings.py](file://packages/rag_service/src/cafetera_rag_service/rag/instructed_embeddings.py)
- [run_all.sh](file://scripts/run_all.sh)
- [run_admin.sh](file://scripts/run_admin.sh)
- [run_llama_llm.sh](file://scripts/run_llama_llm.sh)
- [run_llama_embeddings.sh](file://scripts/run_llama_embeddings.sh)
- [test_rag_block6.py](file://tests/test_rag_block6.py)
- [troubleshooting.md](file://docs/troubleshooting.md)
</cite>

## Update Summary
**Changes Made**
- Enhanced llama.cpp embedding configuration documentation with chunk size parameter passing
- Added documentation for check_embedding_ctx_length=False parameter for historical tokenization compatibility
- Updated troubleshooting guide with llama.cpp embedding server configuration details
- Expanded environment variables reference with EMBEDDING_CHUNK_SIZE parameter
- Added comprehensive llama.cpp embedding server configuration documentation

## Table of Contents
1. [Introduction](#introduction)
2. [Provider Types and Selection](#provider-types-and-selection)
3. [Configuration Architecture](#configuration-architecture)
4. [Environment Variables Reference](#environment-variables-reference)
5. [Provider-Specific Configuration](#provider-specific-configuration)
6. [Instructed Embeddings Configuration](#instructed-embeddings-configuration)
7. [llama.cpp Embedding Server Configuration](#llamacpp-embedding-server-configuration)
8. [Deployment Scripts Integration](#deployment-scripts-integration)
9. [Testing and Validation](#testing-and-validation)
10. [Troubleshooting Guide](#troubleshooting-guide)
11. [Best Practices](#best-practices)
12. [Conclusion](#conclusion)

## Introduction

The LLM Providers Configuration system in this project enables flexible deployment of AI models through three distinct providers: Ollama, OpenAI, and llama.cpp. This configuration framework supports both local development and production deployments, allowing teams to choose the most appropriate AI infrastructure based on their requirements for cost, performance, and control.

The system is designed to be modular and extensible, supporting mixed-provider configurations where LLM and embedding models can be served by different providers simultaneously. This flexibility enables organizations to optimize for specific use cases, such as using high-quality cloud models for LLM inference while maintaining cost-effective local embeddings.

**Updated** Enhanced with comprehensive llama.cpp embedding server configuration, including proper chunk size parameter passing and historical tokenization compatibility fixes for improved Qwen3-Embedding model performance.

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
- **Embedding Support**: Full embedding server capabilities with configurable chunk sizes

```mermaid
flowchart TD
A["Provider Selection"] --> B{"Choose Provider"}
B --> C["Ollama<br/>Local, Free, Default"]
B --> D["OpenAI<br/>Cloud, Paid, High Quality"]
B --> E["llama.cpp<br/>Local, Customizable, GPU Support, Embeddings"]
C --> F["Automatic Model Management"]
D --> G["API Key Required"]
E --> H["Hardware Acceleration"]
E --> I["Embedding Server Support"]
F --> J["Development Ready"]
G --> K["Production Scale"]
H --> L["Maximum Control"]
I --> M["Configurable Chunk Sizes"]
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
+int embedding_chunk_size
+bool embedding_use_query_instruction
+string embedding_query_instruction
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
- [config.py:8](file://packages/rag_service/src/cafetera_rag_service/config.py#L8-L95)
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

### Embedding Configuration Variables

**Updated** New section for embedding-specific configuration supporting llama.cpp embedding server optimization.

| Variable | Purpose | Default Value | Provider Specific |
|----------|---------|---------------|-------------------|
| `EMBEDDING_CHUNK_SIZE` | Batch size for embedding processing | `16` | llama.cpp only |
| `EMBED_POOLING` | Embedding pooling strategy | `last` | llama.cpp only |
| `EMBED_CTX_SIZE` | Embedding server context size | `8192` | llama.cpp only |
| `EMBED_UBATCH_SIZE` | Embedding micro-batch size | `2048` | llama.cpp only |

### Instructed Embeddings Configuration Variables

**Updated** New section for instructed embeddings configuration supporting asymmetric query-side instruction requirements.

| Variable | Purpose | Default Value | Provider Compatibility |
|----------|---------|---------------|----------------------|
| `EMBEDDING_USE_QUERY_INSTRUCTION` | Enable instructed embeddings | `True` | All providers |
| `EMBEDDING_QUERY_INSTRUCTION` | Instruction template for queries | "Given a web search query, retrieve relevant passages that answer the query" | All providers |

### Service Integration Variables

| Variable | Purpose | Default Value | Service |
|----------|---------|---------------|---------|
| `QDRANT_URL` | Vector database endpoint | `http://localhost:6333` | Qdrant |
| `DATABASE_URL` | PostgreSQL connection | `postgresql://cafetera:cafetera@localhost:5432/cafetera` | Database |
| `S3_ENDPOINT_URL` | Object storage endpoint | `http://localhost:9000` | MinIO |
| `RAG_SERVICE_URL` | Internal service address | `http://localhost:8001` | RAG Service |
| `RAG_SERVICE_API_KEY` | Service authentication | Empty | RAG Service |

**Section sources**
- [config.py:29](file://packages/rag_service/src/cafetera_rag_service/config.py#L29-L95)
- [config.py:56](file://packages/rag_service/src/cafetera_rag_service/config.py#L56-L62)
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
J --> K["Embedding Server Support"]
K --> L["Configurable Chunk Sizes"]
```

**Diagram sources**
- [run_llama_llm.sh:23](file://scripts/run_llama_llm.sh#L23-L43)
- [run_llama_embeddings.sh:23](file://scripts/run_llama_embeddings.sh#L23-L43)

**Section sources**
- [run_all.sh:218](file://scripts/run_all.sh#L218-L300)
- [run_llama_llm.sh:1](file://scripts/run_llama_llm.sh#L1-L125)
- [run_llama_embeddings.sh:1](file://scripts/run_llama_embeddings.sh#L1-L121)

## Instructed Embeddings Configuration

**New Section** The system now supports instructed embeddings for Qwen3/E5-instruct families, providing asymmetric query-side instruction requirements for improved retrieval performance.

### Asymmetric Query-Side Instructions

Instructed embeddings apply different formatting to queries versus documents:
- **Queries**: Formatted with instruction prefix "Instruct: {task}\nQuery: {text}"
- **Documents**: Embedded as-is without instruction prefix

This asymmetric approach is essential for models like Qwen3-Embedding and E5-instruct that require specific instruction formatting on the query side while preserving document content unchanged.

### Configuration Parameters

The instructed embeddings feature is controlled by two key parameters:

| Parameter | Description | Default Value | Usage |
|-----------|-------------|---------------|-------|
| `EMBEDDING_USE_QUERY_INSTRUCTION` | Enables/disables instructed embeddings | `True` | Toggle feature on/off |
| `EMBEDDING_QUERY_INSTRUCTION` | Instruction template for query formatting | "Given a web search query, retrieve relevant passages that answer the query" | Customize instruction task |

### Implementation Details

The `InstructedQueryEmbeddings` wrapper class provides transparent integration:

```mermaid
classDiagram
class InstructedQueryEmbeddings {
+Embeddings _inner
+string _instruction
+__init__(Embeddings, string)
+_format_query(string) string
+embed_documents(list) list
+aembed_documents(list) list
+embed_query(string) list
+aembed_query(string) list
}
class Embeddings {
<<interface>>
}
InstructedQueryEmbeddings ..|> Embeddings
```

**Diagram sources**
- [instructed_embeddings.py:13](file://packages/rag_service/src/cafetera_rag_service/rag/instructed_embeddings.py#L13-L37)

### Automatic Integration

The instructed embeddings are automatically applied when both conditions are met:
1. `EMBEDDING_USE_QUERY_INSTRUCTION` is `True`
2. `EMBEDDING_QUERY_INSTRUCTION` contains a non-empty instruction

The integration occurs in the `build_embeddings` function, which wraps the base embedding instance with `InstructedQueryEmbeddings` when instructed embeddings are enabled.

**Section sources**
- [config.py:56](file://packages/rag_service/src/cafetera_rag_service/config.py#L56-L62)
- [instructed_embeddings.py:1](file://packages/rag_service/src/cafetera_rag_service/rag/instructed_embeddings.py#L1-L37)
- [retriever.py:226](file://packages/rag_service/src/cafetera_rag_service/rag/retriever.py#L226-L236)

## llama.cpp Embedding Server Configuration

**New Section** Comprehensive documentation for llama.cpp embedding server configuration, including chunk size parameter passing and historical tokenization compatibility fixes.

### Embedding Server Architecture

The llama.cpp embedding server provides dedicated embedding generation capabilities with configurable performance parameters:

```mermaid
flowchart TD
A["Embedding Request"] --> B["Chunk Size Validation"]
B --> C{"Chunk Size <= Context Size?"}
C --> |Yes| D["Process Embedding Batch"]
C --> |No| E["Adjust Chunk Size"]
D --> F["Apply Pooling Strategy"]
F --> G["Return Embedding Vectors"]
E --> H["Retry with Reduced Batch"]
H --> D
```

**Diagram sources**
- [run_llama_embeddings.sh:114](file://scripts/run_llama_embeddings.sh#L114-L123)
- [llamacpp.md:122](file://docs/llamacpp.md#L122-L128)

### Key Configuration Parameters

The llama.cpp embedding server supports several critical configuration parameters:

| Parameter | Purpose | Default Value | Formula |
|-----------|---------|---------------|---------|
| `EMBEDDING_CHUNK_SIZE` | Number of texts processed in one batch | `16` | `EMBED_CTX_SIZE >= EMBEDDING_CHUNK_SIZE × max_tokens_per_chunk` |
| `EMBED_CTX_SIZE` | Server context size (KV cache) | `8192` | Must accommodate batch processing capacity |
| `EMBED_POOLING` | Embedding pooling strategy | `last` | `last` for Qwen3-Embedding, `mean` for nomic-embed-text, `cls` for BGE/E5 |
| `EMBED_UBATCH_SIZE` | Micro-batch size for processing | `2048` | Controls memory usage during batch processing |

### Historical Tokenization Compatibility

**Updated** The system now includes a critical compatibility fix for historical tokenization issues:

**Problem**: LangChain's `OpenAIEmbeddings` uses tiktoken tokenizer by default, sending token IDs instead of raw text to embedding servers. This causes compatibility issues with llama.cpp servers that expect raw text input.

**Solution**: The `check_embedding_ctx_length=False` parameter prevents token length validation, allowing raw text to be sent to llama.cpp servers regardless of tokenization differences.

**Implementation**: This parameter is automatically set when building OpenAI-compatible embeddings for llama.cpp providers.

### Pooling Strategies

Different embedding models require different pooling strategies:

| Model Family | Required Pooling | Purpose |
|--------------|------------------|---------|
| **Qwen3-Embedding** | `last` | Uses last token for final representation |
| nomic-embed-text | `mean` | Averages all tokens for representation |
| BGE / E5 | `cls` | Uses first special token (CLS) for representation |

### Memory Management

The embedding server implements sophisticated memory management for batch processing:

1. **Context Size Calculation**: `EMBED_CTX_SIZE >= EMBEDDING_CHUNK_SIZE × max_tokens_per_chunk`
2. **KV Cache Management**: Efficient memory allocation for batch processing
3. **Micro-batch Processing**: `EMBED_UBATCH_SIZE` controls intermediate processing steps
4. **GPU Acceleration**: Automatic detection and utilization of hardware acceleration

**Section sources**
- [config.py:56](file://packages/rag_service/src/cafetera_rag_service/config.py#L56-L57)
- [run_llama_embeddings.sh:114](file://scripts/run_llama_embeddings.sh#L114-L123)
- [llamacpp.md:110](file://docs/llamacpp.md#L110-L138)
- [troubleshooting.md:214](file://docs/troubleshooting.md#L214-L216)

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
| Instructed Embeddings | All providers | Query instruction formatting |
| Embedding Server | llama.cpp | Chunk size parameter passing |

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

### llama.cpp Embedding Server Issues

**Problem**: Embedding server crashes with SIGTRAP or "failed to find a memory slot"
- **Solution**: Increase EMBED_CTX_SIZE or decrease EMBEDDING_CHUNK_SIZE
- **Formula**: `EMBED_CTX_SIZE >= EMBEDDING_CHUNK_SIZE × max_tokens_per_chunk`
- **Check**: Monitor memory usage during batch processing
- **Debug**: Review embedding server logs for memory allocation errors

**Problem**: Embedding vectors differ between providers
- **Solution**: Verify EMBED_POOLING setting matches model requirements
- **Check**: Ensure check_embedding_ctx_length=False for llama.cpp compatibility
- **Debug**: Compare embedding outputs using diagnostic curl commands

**Problem**: Performance issues with llama.cpp embedding server
- **Solution**: Optimize chunk size and context size parameters
- **Check**: Monitor GPU utilization and memory usage
- **Debug**: Profile embedding performance with different batch sizes

### Instructed Embeddings Issues

**Problem**: Query instruction not applied correctly
- **Solution**: Verify `EMBEDDING_USE_QUERY_INSTRUCTION` is `True`
- **Check**: Ensure `EMBEDDING_QUERY_INSTRUCTION` contains a non-empty value
- **Debug**: Review instruction formatting in `InstructedQueryEmbeddings`

**Problem**: Retrieval quality degradation with instructed embeddings
- **Solution**: Adjust instruction template for specific use cases
- **Check**: Compare embedding vectors with and without instruction formatting
- **Debug**: Test with different instruction templates

**Problem**: Performance issues with instructed embeddings
- **Solution**: Monitor embedding latency and adjust batch processing
- **Check**: Verify instruction formatting doesn't add excessive overhead
- **Debug**: Profile embedding performance with and without instruction wrapper

### Historical Tokenization Compatibility Issues

**Problem**: Embedding server receives token IDs instead of text
- **Solution**: Ensure check_embedding_ctx_length=False is set for llama.cpp providers
- **Check**: Verify OpenAIEmbeddings initialization includes this parameter
- **Debug**: Compare raw text vs token ID inputs in embedding server logs

**Problem**: Embedding vectors inconsistent across different providers
- **Solution**: Use llama.cpp embedding server with proper pooling configuration
- **Check**: Verify EMBED_POOLING matches model requirements (last for Qwen3-Embedding)
- **Debug**: Test embedding server directly with curl commands

**Section sources**
- [run_all.sh:311](file://scripts/run_all.sh#L311-L338)
- [run_llama_llm.sh:74](file://scripts/run_llama_llm.sh#L74-L78)
- [instructed_embeddings.py:22](file://packages/rag_service/src/cafetera_rag_service/rag/instructed_embeddings.py#L22-L23)
- [troubleshooting.md:214](file://docs/troubleshooting.md#L214-L216)
- [troubleshooting.md:243](file://docs/troubleshooting.md#L243-L257)

## Best Practices

### Provider Selection Guidelines

1. **Development Environment**: Use Ollama for fastest setup and iteration
2. **Production Deployment**: Consider OpenAI for highest quality with proper SLA
3. **Resource-Constrained**: Use llama.cpp with appropriate GPU acceleration
4. **Mixed Strategy**: Use different providers for LLM and embeddings based on requirements

### llama.cpp Embedding Server Best Practices

**Updated** New best practices for llama.cpp embedding server configuration:

1. **Optimize Chunk Size**: Start with EMBEDDING_CHUNK_SIZE=16 and adjust based on memory constraints
2. **Monitor Context Size**: Ensure EMBED_CTX_SIZE >= EMBEDDING_CHUNK_SIZE × max_tokens_per_chunk
3. **Select Proper Pooling**: Use EMBED_POOLING=last for Qwen3-Embedding models
4. **Configure GPU Layers**: Set EMBED_N_GPU_LAYERS appropriately for your hardware
5. **Enable Historical Compatibility**: Ensure check_embedding_ctx_length=False for llama.cpp embedding servers

### Instructed Embeddings Best Practices

**Updated** New best practices for instructed embeddings configuration:

1. **Enable for Qwen3/E5-instruct Models**: Always enable instructed embeddings for Qwen3-Embedding and E5-instruct families
2. **Customize Instruction Templates**: Tailor instruction templates to specific use cases and domains
3. **Monitor Performance Impact**: Track embedding latency and vector quality when enabling instructed embeddings
4. **Test Different Instructions**: Experiment with various instruction templates to optimize retrieval quality

### Configuration Management

1. **Environment Separation**: Use separate .env files for different environments
2. **Variable Documentation**: Maintain inline documentation for all configuration variables
3. **Validation**: Implement configuration validation in CI/CD pipeline
4. **Security**: Store API keys in secure vaults, not in version control

### Performance Optimization

1. **GPU Utilization**: Enable GPU acceleration when available
2. **Context Window**: Adjust context sizes based on model capabilities
3. **Batch Processing**: Optimize batch sizes for embedding generation
4. **Memory Management**: Monitor and tune memory usage for embedding servers
5. **Caching**: Implement result caching for repeated queries

### Monitoring and Maintenance

1. **Health Checks**: Implement regular service health monitoring
2. **Logging**: Configure comprehensive logging for debugging
3. **Updates**: Regularly update models and dependencies
4. **Backup**: Implement backup strategies for trained models

## Conclusion

The LLM Providers Configuration system provides a robust, flexible framework for deploying AI models across different providers and environments. The system's modular design allows teams to optimize for their specific requirements while maintaining consistency and reliability.

**Updated** Recent enhancements include comprehensive llama.cpp embedding server configuration with proper chunk size parameter passing, historical tokenization compatibility fixes, and detailed troubleshooting guidance for embedding server optimization.

Key strengths of the configuration system include:

- **Multi-provider Support**: Seamless switching between Ollama, OpenAI, and llama.cpp
- **Flexible Deployment**: Support for local development and production environments
- **Advanced Embeddings**: Asymmetric query-side instruction support for modern models
- **llama.cpp Optimization**: Comprehensive embedding server configuration with chunk size management
- **Historical Compatibility**: Tokenization compatibility fixes for seamless integration
- **Comprehensive Testing**: Thorough validation of configuration scenarios
- **Automated Management**: Scripts handle service lifecycle and dependency management
- **Extensible Architecture**: Foundation for adding new providers and configurations

The system's design enables organizations to start with the simplest configuration (Ollama) and scale to production-grade deployments with OpenAI or custom llama.cpp setups as requirements evolve. The addition of instructed embeddings configuration and llama.cpp embedding server optimization ensures optimal performance for modern embedding models while maintaining backward compatibility with traditional embedding approaches.