# RAG Parser Enhancement

<cite>
**Referenced Files in This Document**
- [parser.py](file://app/rag/parser.py)
- [indexer.py](file://app/rag/indexer.py)
- [retriever.py](file://app/rag/retriever.py)
- [chain.py](file://app/rag/chain.py)
- [prompts.py](file://app/rag/prompts.py)
- [ingest.py](file://scripts/ingest.py)
- [document_service.py](file://app/domain/document_service.py)
- [document_repo.py](file://app/storage/document_repo.py)
- [config.py](file://app/config.py)
- [documents.py](file://app/api/documents.py)
- [qa_service.py](file://app/domain/qa_service.py)
- [main.py](file://app/main.py)
- [resources.py](file://app/resources.py)
- [test_parser.py](file://tests/test_parser.py)
- [test_semantic_chunker.py](file://tests/test_semantic_chunker.py)
- [test_hybrid_search.py](file://tests/test_hybrid_search.py)
- [test_rag_block6.py](file://tests/test_rag_block6.py)
- [test_indexer.py](file://tests/test_indexer.py)
- [pyproject.toml](file://pyproject.toml)
</cite>

## Update Summary
**Changes Made**
- Added semantic chunking functionality with new chunking strategies ('recursive' and 'semantic')
- Enhanced configuration options for breakpoint thresholds with four threshold types
- Integrated LangChain's SemanticChunker for embedding-based semantic chunking
- Added hybrid search capabilities with sparse embeddings support for BM25 keyword matching
- Extended parser functions to support semantic chunking with configurable breakpoint thresholds
- Updated retriever to support hybrid dense-sparse retrieval modes
- Enhanced indexer to support sparse embeddings during vector indexing
- Added comprehensive test coverage for semantic chunking and hybrid search functionality
- Updated configuration system to support semantic chunking parameters and hybrid retrieval modes

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)

## Introduction
This document describes the RAG (Retrieval-Augmented Generation) Parser Enhancement for the Cafetera HR Bot. The enhancement significantly expands document processing capabilities by implementing advanced chunking strategies including semantic chunking with LangChain's SemanticChunker, enhanced configuration options for breakpoint thresholds, and hybrid search functionality with sparse embeddings support for BM25 keyword matching. The system now features dual chunking strategies ('recursive' and 'semantic'), comprehensive test coverage for new functionality, and robust integration with Qdrant vector storage supporting both dense and sparse embeddings. The enhancement maintains backward compatibility while providing superior text segmentation accuracy, improved retrieval performance through semantic understanding, and enhanced search capabilities through hybrid dense-sparse retrieval modes.

## Project Structure
The RAG system is organized into cohesive modules with enhanced semantic chunking capabilities, hybrid search support, and comprehensive testing infrastructure:
- app/rag: Core RAG components with semantic chunking and hybrid search (parser, indexer, retriever, chain, prompts)
- scripts: Batch ingestion utilities with semantic chunking and configurable parameters
- app/domain: Business services orchestrating document lifecycle with enhanced chunking strategies
- app/storage: Metadata persistence and S3 integration
- app/api: Admin endpoints for document management with semantic-aware processing
- app/config: Environment-driven configuration with semantic chunking and hybrid retrieval parameters
- app/resources: Resource management with hybrid search capability initialization
- tests: Comprehensive unit and integration tests for semantic chunking and hybrid search functionality

```mermaid
graph TB
subgraph "Enhanced Semantic Chunking RAG Core"
P["parser.py<br/>Semantic chunking & dual strategies<br/>LangChain SemanticChunker<br/>4 breakpoint threshold types"]
I["indexer.py<br/>Chunk prep & Qdrant ops<br/>Sparse embeddings support"]
R["retriever.py<br/>Dense & hybrid retriever<br/>BM25 sparse embeddings"]
C["chain.py<br/>RAG chain builder"]
PR["prompts.py<br/>System prompts"]
RES["resources.py<br/>Hybrid search resource init<br/>FastEmbedSparse"]
end
subgraph "Application Layer"
DS["document_service.py<br/>Document lifecycle<br/>Semantic chunking support"]
DR["document_repo.py<br/>SQLite metadata"]
API["documents.py<br/>Admin API<br/>Semantic-aware chunking"]
QA["qa_service.py<br/>QA handler<br/>Hybrid retrieval support"]
CFG["config.py<br/>Settings<br/>semantic chunking & hybrid"]
MAIN["main.py<br/>App lifecycle"]
end
subgraph "External Systems"
QD["Qdrant"]
S3["S3 Storage"]
LLM["LLM Provider"]
SEM["SemanticChunker"]
FE["FastEmbedSparse"]
end
P --> I
I --> QD
R --> QD
R --> FE
C --> LLM
API --> DS
DS --> DR
DS --> QD
DS --> S3
QA --> R
QA --> C
RES --> FE
RES --> SEM
MAIN --> DS
MAIN --> QA
CFG --> R
CFG --> C
```

**Diagram sources**
- [parser.py:16-174](file://app/rag/parser.py#L16-L174)
- [indexer.py:49-71](file://app/rag/indexer.py#L49-L71)
- [retriever.py:88-160](file://app/rag/retriever.py#L88-L160)
- [chain.py:98-122](file://app/rag/chain.py#L98-L122)
- [prompts.py:1-19](file://app/rag/prompts.py#L1-L19)
- [resources.py:120-132](file://app/resources.py#L120-L132)
- [document_service.py:106-120](file://app/domain/document_service.py#L106-L120)
- [documents.py:154-163](file://app/api/documents.py#L154-L163)
- [qa_service.py:102-148](file://app/domain/qa_service.py#L102-L148)
- [config.py:54-62](file://app/config.py#L54-L62)
- [main.py:29-38](file://app/main.py#L29-L38)

**Section sources**
- [parser.py:16-174](file://app/rag/parser.py#L16-L174)
- [indexer.py:49-71](file://app/rag/indexer.py#L49-L71)
- [retriever.py:88-160](file://app/rag/retriever.py#L88-L160)
- [chain.py:98-122](file://app/rag/chain.py#L98-L122)
- [prompts.py:1-19](file://app/rag/prompts.py#L1-L19)
- [resources.py:120-132](file://app/resources.py#L120-L132)
- [document_service.py:106-120](file://app/domain/document_service.py#L106-L120)
- [documents.py:154-163](file://app/api/documents.py#L154-L163)
- [qa_service.py:102-148](file://app/domain/qa_service.py#L102-L148)
- [config.py:54-62](file://app/config.py#L54-L62)
- [main.py:29-38](file://app/main.py#L29-L38)

## Core Components
This section outlines the primary components of the RAG Parser Enhancement with semantic chunking capabilities, hybrid search support, and comprehensive testing infrastructure.

- **Semantic Chunking Parser and Dual Strategy Engine**
  - Implements dual chunking strategies: 'recursive' (token-based) and 'semantic' (embedding-based)
  - Integrates LangChain's SemanticChunker for intelligent semantic boundary detection
  - Supports four breakpoint threshold types: 'percentile', 'standard_deviation', 'interquartile', 'gradient'
  - Configurable breakpoint threshold amounts with default 95th percentile setting
  - Extracts text from both .docx and .doc files with semantic-aware processing
  - .docx files: Structured section extraction with semantic chunking preserving heading relationships
  - .doc files: Legacy format processing with semantic chunking treating entire text as single section
  - **Enhanced**: Semantic chunking with configurable breakpoint thresholds for optimal chunk boundaries
  - Returns LangChain Document objects with semantic-aware metadata and chunk positioning

- **Hybrid Search Retriever with Sparse Embeddings**
  - Supports both dense vector retrieval and hybrid dense-sparse retrieval modes
  - Integrates FastEmbedSparse for BM25 keyword matching alongside dense vector embeddings
  - Configurable retrieval modes: 'dense' (vector-only) and 'hybrid' (dense + sparse)
  - Automatic sparse embedding initialization when hybrid mode is enabled
  - Graceful fallback to dense-only retrieval when sparse embeddings are unavailable
  - Maintains backward compatibility with existing dense retrieval workflows

- **Enhanced Indexer with Sparse Embedding Support**
  - Extends chunk preparation to support sparse embeddings alongside dense vectors
  - Passes sparse_embedding parameter through to QdrantVectorStore constructor
  - Maintains consistency between dense and sparse embedding indexing operations
  - Supports hybrid indexing workflows with both embedding types

- **Resource Management with Hybrid Search Integration**
  - Initializes sparse embeddings automatically when hybrid search mode is enabled
  - Graceful degradation when sparse embedding dependencies are unavailable
  - Integrates FastEmbedSparse model initialization with configurable model names
  - Supports both automatic and manual sparse embedding configuration

- **Configuration System with Semantic and Hybrid Capabilities**
  - Centralized Settings class with semantic chunking parameters
  - Default chunk_strategy set to 'recursive' for backward compatibility
  - Semantic breakpoint threshold configuration with four supported types
  - Hybrid retrieval mode configuration with sparse embedding model specification
  - Retrieval mode selection between 'dense' and 'hybrid' operations

**Section sources**
- [parser.py:58-174](file://app/rag/parser.py#L58-L174)
- [parser.py:177-266](file://app/rag/parser.py#L177-L266)
- [retriever.py:88-160](file://app/rag/retriever.py#L88-L160)
- [indexer.py:49-71](file://app/rag/indexer.py#L49-L71)
- [resources.py:120-132](file://app/resources.py#L120-L132)
- [config.py:54-62](file://app/config.py#L54-L62)

## Architecture Overview
The RAG Parser Enhancement integrates semantic chunking, hybrid search capabilities, and dual retrieval strategies into a comprehensive pipeline with enhanced chunking accuracy and flexible retrieval modes. The system now supports both traditional token-based chunking and intelligent semantic chunking, with optional hybrid search combining dense vector similarity with sparse BM25 keyword matching for superior retrieval performance.

```mermaid
sequenceDiagram
participant Admin as "Admin UI/API"
participant API as "Documents API"
participant Service as "DocumentService"
participant S3 as "S3 Storage"
participant Parser as "Semantic Parser<br/>Dual strategies<br/>4 breakpoint types"
participant Indexer as "Indexer<br/>Sparse embedding support"
participant Qdrant as "Qdrant<br/>Dense + Sparse"
Admin->>API : Upload .docx or .doc<br/>with semantic chunking
API->>S3 : Store file
API->>Service : Create metadata record
API->>Service : Schedule background indexing<br/>with semantic-aware chunking
Service->>S3 : Download file
Service->>Parser : load_document(path)<br/>semantic or recursive strategy
Parser->>Parser : SemanticChunker or Recursive splitter<br/>breakpoint thresholds
Parser-->>Service : List of Documents<br/>semantic chunks
Service->>Indexer : Enrich metadata + prepare chunks
Indexer->>Qdrant : Add vectors + sparse embeddings
Service-->>API : Update status to completed
API-->>Admin : Show indexed document
```

**Diagram sources**
- [documents.py:154-163](file://app/api/documents.py#L154-L163)
- [document_service.py:106-120](file://app/domain/document_service.py#L106-L120)
- [parser.py:134-140](file://app/rag/parser.py#L134-L140)
- [indexer.py:65-71](file://app/rag/indexer.py#L65-L71)

**Section sources**
- [documents.py:154-163](file://app/api/documents.py#L154-L163)
- [document_service.py:106-120](file://app/domain/document_service.py#L106-L120)
- [ingest.py:49-155](file://scripts/ingest.py#L49-L155)

## Detailed Component Analysis

### Semantic Chunking System with Multiple Strategies
The parser now features a sophisticated dual-strategy chunking system supporting both traditional token-based chunking and intelligent semantic chunking. The semantic chunking leverages LangChain's SemanticChunker with configurable breakpoint thresholds for optimal chunk boundaries based on semantic similarity.

```mermaid
flowchart TD
Start(["load_document(path)"]) --> CheckExt{"Check file extension"}
CheckExt --> |".docx"| LoadDocx["load_docx(path)<br/>Dual strategies<br/>SemanticChunker"]
CheckExt --> |".doc"| LoadDoc["load_doc(path)<br/>Dual strategies<br/>SemanticChunker"]
LoadDocx --> Extract["_extract_sections(path)"]
LoadDoc --> ProcessLegacy["docx2txt.process(path)"]
Extract --> Strategy{"Strategy: recursive or semantic"}
ProcessLegacy --> Strategy
Strategy --> |"recursive"| RecursiveSplit["RecursiveCharacterTextSplitter<br/>tiktoken encoding<br/>500-token chunks"]
Strategy --> |"semantic"| SemanticSplit["SemanticChunker<br/>4 breakpoint types<br/>Breakpoint thresholds"]
RecursiveSplit --> CreateDocs["Create LCDocument with metadata"]
SemanticSplit --> PositionMapping["Position mapping & section assignment"]
PositionMapping --> CreateDocs
CreateDocs --> Return["Return list of Documents"]
subgraph "Semantic Configuration"
Config["chunk_strategy: 'recursive' or 'semantic'<br/>breakpoint_threshold_type:<br/>percentile | std | iq | gradient<br/>breakpoint_threshold_amount: 95"]
end
Config --> Strategy
```

**Diagram sources**
- [parser.py:270-323](file://app/rag/parser.py#L270-L323)
- [parser.py:58-174](file://app/rag/parser.py#L58-L174)
- [parser.py:177-266](file://app/rag/parser.py#L177-L266)
- [config.py:54-57](file://app/config.py#L54-L57)

**Section sources**
- [parser.py:270-323](file://app/rag/parser.py#L270-L323)
- [parser.py:58-174](file://app/rag/parser.py#L58-L174)
- [parser.py:177-266](file://app/rag/parser.py#L177-L266)
- [config.py:54-57](file://app/config.py#L54-L57)

### Semantic Chunking with LangChain SemanticChunker
The semantic chunking functionality integrates LangChain's SemanticChunker for intelligent boundary detection based on embedding similarity. This approach identifies natural semantic boundaries rather than relying solely on structural markers or fixed token counts.

```mermaid
flowchart TD
StartSemantic["Semantic Chunking Process"] --> BuildText["Build full text with section offsets<br/>Track positions for mapping"]
BuildText --> CreateChunker["Create SemanticChunker<br/>with embeddings model"]
CreateChunker --> GenerateChunks["Generate semantic chunks<br/>4 breakpoint threshold types"]
GenerateChunks --> MapPositions["Map chunk positions<br/>to original text offsets"]
MapPositions --> FindSection["Find best matching section<br/>by overlap calculation"]
FindSection --> CreateDocs["Create LCDocument<br/>with semantic metadata"]
CreateDocs --> ReturnDocs["Return semantic chunks"]
subgraph "Breakpoint Threshold Types"
Types["percentile: 95th percentile<br/>standard_deviation: std dev threshold<br/>interquartile: IQR method<br/>gradient: gradient-based detection"]
end
Types --> CreateChunker
```

**Diagram sources**
- [parser.py:115-172](file://app/rag/parser.py#L115-L172)
- [parser.py:240-264](file://app/rag/parser.py#L240-L264)

**Section sources**
- [parser.py:115-172](file://app/rag/parser.py#L115-L172)
- [parser.py:240-264](file://app/rag/parser.py#L240-L264)

### Hybrid Search Architecture with Sparse Embeddings
The retriever system now supports hybrid dense-sparse retrieval combining vector similarity with BM25 keyword matching. This dual approach leverages both semantic understanding and lexical matching for superior search results.

```mermaid
sequenceDiagram
participant Settings as "Settings"
participant Resources as "build_resources"
participant Retriever as "build_sparse_embeddings"
participant Sparse as "FastEmbedSparse"
Settings->>Resources : retrieval_mode="hybrid"
Resources->>Retriever : Call with settings
Retriever->>Retriever : Check retrieval_mode
Retriever->>Sparse : Initialize FastEmbedSparse
Sparse-->>Retriever : Sparse embeddings instance
Retriever-->>Resources : Return sparse embeddings
Resources-->>Settings : Store in app.state
```

**Diagram sources**
- [retriever.py:88-103](file://app/rag/retriever.py#L88-L103)
- [resources.py:120-132](file://app/resources.py#L120-L132)
- [config.py:59-62](file://app/config.py#L59-L62)

**Section sources**
- [retriever.py:88-103](file://app/rag/retriever.py#L88-L103)
- [resources.py:120-132](file://app/resources.py#L120-L132)
- [config.py:59-62](file://app/config.py#L59-L62)

### Sparse Embeddings Integration for BM25 Keyword Matching
The system integrates FastEmbedSparse for efficient BM25 keyword matching alongside dense vector embeddings. This enables keyword-based relevance scoring in addition to semantic similarity.

```mermaid
classDiagram
class SparseEmbeddings {
+model_name : str = "Qdrant/bm25"
+initialize_fastembed_sparse()
+create_sparse_vectors(texts)
+passage_embed() method
+query_embed() method
}
class HybridRetriever {
+build_retriever_with_sparse()
+combine_dense_sparse_scores()
+normalize_hybrid_scores()
}
class QdrantVectorStore {
+add_documents_with_sparse()
+retrieve_with_sparse_filter()
}
SparseEmbeddings --> HybridRetriever : provides sparse vectors
HybridRetriever --> QdrantVectorStore : uses sparse embeddings
```

**Diagram sources**
- [retriever.py:88-121](file://app/rag/retriever.py#L88-L121)
- [indexer.py:65-71](file://app/rag/indexer.py#L65-L71)

**Section sources**
- [retriever.py:88-121](file://app/rag/retriever.py#L88-L121)
- [indexer.py:65-71](file://app/rag/indexer.py#L65-L71)

### Enhanced Configuration System for Semantic and Hybrid Features
The Settings class now includes comprehensive configuration for semantic chunking and hybrid retrieval modes, providing centralized control over all new functionality.

```mermaid
classDiagram
class Settings {
+chunk_strategy : str = "recursive"
+semantic_breakpoint_threshold_type : str = "percentile"
+semantic_breakpoint_threshold_amount : float = 95
+retrieval_mode : str = "dense"
+sparse_embedding_model : str = "Qdrant/bm25"
+chunk_size : int = 500
+chunk_overlap : int = 50
}
class SemanticChunkingConfig {
+strategy : "recursive" | "semantic"
+threshold_type : "percentile" | "std" | "iq" | "gradient"
+threshold_amount : number
}
class HybridSearchConfig {
+mode : "dense" | "hybrid"
+sparse_model : string
}
Settings --> SemanticChunkingConfig : provides semantic params
Settings --> HybridSearchConfig : provides hybrid params
```

**Diagram sources**
- [config.py:54-62](file://app/config.py#L54-L62)

**Section sources**
- [config.py:54-62](file://app/config.py#L54-L62)

### Semantic Chunking Test Coverage and Validation
The testing infrastructure includes comprehensive validation for semantic chunking functionality, ensuring reliable operation across different document types and chunking strategies.

```mermaid
flowchart TD
TestSuite["Semantic Chunking Tests"] --> RecursiveCompat["Recursive Strategy Backward Compatibility"]
TestSuite --> SemanticDocx["Semantic Chunking .docx Files"]
TestSuite --> SemanticDoc["Semantic Chunking .doc Files"]
TestSuite --> EmbeddingsValidation["Embeddings Parameter Validation"]
TestSuite --> ConfigDefaults["Configuration Defaults Testing"]
RecursiveCompat --> Test1["load_document(strategy='recursive')<br/>preserves metadata"]
SemanticDocx --> Test2["load_document(strategy='semantic', embeddings)<br/>creates semantic chunks"]
SemanticDoc --> Test3["load_doc(strategy='semantic', embeddings)<br/>empty section metadata"]
EmbeddingsValidation --> Test4["semantic strategy requires embeddings<br/>raises ValueError"]
ConfigDefaults --> Test5["Settings defaults<br/>chunk_strategy='recursive'<br/>semantic defaults configured"]
```

**Diagram sources**
- [test_semantic_chunker.py:94-237](file://tests/test_semantic_chunker.py#L94-L237)

**Section sources**
- [test_semantic_chunker.py:94-237](file://tests/test_semantic_chunker.py#L94-L237)

### Hybrid Search Testing and Validation
The hybrid search functionality includes comprehensive testing for sparse embeddings initialization, vector store integration, and retrieval mode switching.

```mermaid
flowchart TD
HybridTests["Hybrid Search Tests"] --> DenseMode["Dense Mode Testing"]
HybridTests --> HybridMode["Hybrid Mode Testing"]
HybridTests --> SparseInit["Sparse Embeddings Initialization"]
HybridTests --> VectorStore["Vector Store Integration"]
HybridTests --> QAIntegration["QA Service Integration"]
DenseMode --> Test1["retrieval_mode='dense'<br/>build_sparse_embeddings returns None"]
HybridMode --> Test2["retrieval_mode='hybrid'<br/>returns FastEmbedSparse instance"]
SparseInit --> Test3["FastEmbedSparse model initialization<br/>Qdrant/bm25 model name"]
VectorStore --> Test4["QdrantVectorStore accepts sparse_embedding<br/>parameter"]
QAIntegration --> Test5["QAService stores and uses sparse embeddings<br/>for hybrid retrieval"]
```

**Diagram sources**
- [test_hybrid_search.py:17-169](file://tests/test_hybrid_search.py#L17-L169)

**Section sources**
- [test_hybrid_search.py:17-169](file://tests/test_hybrid_search.py#L17-L169)

### Document Lifecycle Service with Semantic Chunking Support
The DocumentService now supports semantic chunking through enhanced indexing operations that handle both dense and sparse embedding indexing workflows.

```mermaid
flowchart TD
DocumentService["DocumentService"] --> IndexDocument["index_document(document_id, chunks)"]
IndexDocument --> PrepareChunks["prepare_chunks(enriched metadata)"]
PrepareChunks --> AsyncThread["asyncio.to_thread()"]
AsyncThread --> IndexChunks["index_chunks(client, embeddings, collection, chunks,<br/>sparse_embedding=self._sparse_embedding)"]
IndexChunks --> UpdateRepo["update repository status<br/>completed with chunk_count"]
UpdateRepo --> Complete["Document indexing complete"]
```

**Diagram sources**
- [document_service.py:106-120](file://app/domain/document_service.py#L106-L120)

**Section sources**
- [document_service.py:106-120](file://app/domain/document_service.py#L106-L120)

### Admin Upload Flow with Semantic Chunking Options
The admin upload flow now supports semantic chunking strategies with configurable breakpoint thresholds, providing users with flexible document processing options.

```mermaid
sequenceDiagram
participant Client as "Admin Client"
participant API as "documents.py"
participant S3 as "S3Storage"
participant Service as "DocumentService"
participant BG as "Background Task"
Client->>API : POST /api/documents/upload<br/>semantic chunking options
API->>API : Validate file type/size (.doc/.docx)
API->>S3 : Upload file
API->>Service : create_document(...)
API->>BG : Schedule _index_in_background<br/>with semantic-aware chunking
BG->>S3 : Download file
BG->>Service : index_document(document_id, chunks)<br/>semantic or recursive strategy
Service-->>BG : Status updated
BG-->>API : Background indexing complete
API-->>Client : JSON or HTMX response
```

**Diagram sources**
- [documents.py:154-163](file://app/api/documents.py#L154-L163)

**Section sources**
- [documents.py:154-163](file://app/api/documents.py#L154-L163)

## Dependency Analysis
The RAG Parser Enhancement exhibits enhanced dependency management with new semantic chunking and hybrid search capabilities while maintaining backward compatibility. The system now integrates LangChain Experimental for semantic chunking and FastEmbed for sparse embeddings, with graceful fallback mechanisms for optional dependencies.

```mermaid
graph TB
CFG["config.py<br/>Semantic & hybrid settings<br/>chunk_strategy, sparse model"] --> RES["resources.py<br/>Hybrid search init<br/>FastEmbedSparse"]
CFG --> RET["retriever.py<br/>Hybrid retriever<br/>sparse embeddings"]
CFG --> PARSE["parser.py<br/>Semantic chunking<br/>SemanticChunker"]
RES --> RET
RES --> QDRANT["Qdrant"]
PARSE --> LC["LangChain Experimental<br/>SemanticChunker"]
PARSE --> TIKTOKEN["tiktoken"]
RET --> FE["FastEmbedSparse"]
RET --> QDRANT
INDEXER["indexer.py<br/>Sparse embedding support"] --> QDRANT
SERVICE["document_service.py<br/>Semantic chunking support"] --> INDEXER
API["documents.py<br/>Semantic chunking API"] --> SERVICE
QA["qa_service.py<br/>Hybrid retrieval"] --> RET
MAIN["main.py<br/>Resource initialization"] --> RES
```

**Diagram sources**
- [config.py:54-62](file://app/config.py#L54-L62)
- [resources.py:120-132](file://app/resources.py#L120-L132)
- [retriever.py:88-160](file://app/rag/retriever.py#L88-L160)
- [parser.py:16-17](file://app/rag/parser.py#L16-L17)
- [indexer.py:65-71](file://app/rag/indexer.py#L65-L71)
- [document_service.py:106-120](file://app/domain/document_service.py#L106-L120)
- [documents.py:154-163](file://app/api/documents.py#L154-L163)
- [qa_service.py:102-148](file://app/domain/qa_service.py#L102-L148)
- [main.py:29-38](file://app/main.py#L29-L38)

**Section sources**
- [config.py:54-62](file://app/config.py#L54-L62)
- [resources.py:120-132](file://app/resources.py#L120-L132)
- [retriever.py:88-160](file://app/rag/retriever.py#L88-L160)
- [parser.py:16-17](file://app/rag/parser.py#L16-L17)
- [indexer.py:65-71](file://app/rag/indexer.py#L65-L71)
- [document_service.py:106-120](file://app/domain/document_service.py#L106-L120)
- [documents.py:154-163](file://app/api/documents.py#L154-L163)
- [qa_service.py:102-148](file://app/domain/qa_service.py#L102-L148)
- [main.py:29-38](file://app/main.py#L29-L38)

## Performance Considerations
- **Enhanced Semantic Chunking Strategy**
  - The parser now supports dual chunking strategies with intelligent semantic boundary detection using LangChain's SemanticChunker
  - Four breakpoint threshold types provide flexibility for different document characteristics: percentile (default 95%), standard deviation, interquartile, and gradient-based detection
  - Semantic chunking requires embedding model initialization, adding computational overhead but improving semantic coherence
  - Breakpoint threshold configuration allows tuning chunk granularity based on document complexity and retrieval requirements
  - Legacy .doc files benefit from semantic chunking despite lacking structured headings, with empty section metadata for uniform processing
- **Hybrid Search Performance Optimization**
  - Sparse embeddings add minimal overhead compared to dense embeddings while providing complementary keyword matching capabilities
  - FastEmbedSparse offers efficient BM25 implementation with configurable model selection
  - Hybrid retrieval combines dense and sparse scores with configurable weighting strategies
  - Automatic fallback to dense-only retrieval when sparse embeddings are unavailable prevents performance degradation
- **Provider Selection and Resource Management**
  - Embedding and LLM providers impact both semantic chunking performance and hybrid search capabilities
  - Choose providers aligned with deployment constraints and enable caching where supported for semantic chunking operations
  - Monitor resource usage during semantic chunking as it requires additional computational resources for embedding calculations
- **Batch Processing and Memory Management**
  - Batch ingestion (scripts/ingest.py) supports both semantic and recursive strategies with configurable parameters
  - Admin uploads leverage background tasks with semantic-aware chunking parameters and breakpoint thresholds
  - Memory considerations for semantic chunking include embedding model loading and breakpoint threshold calculations
  - Consider chunk size adjustments when using semantic chunking to balance semantic coherence with computational efficiency
- **Vector Store and Hybrid Indexing**
  - Qdrant filtering excludes non-searchable chunks efficiently in both dense and hybrid modes
  - Sparse embedding indexing requires additional storage space but enables keyword-based retrieval capabilities
  - Collection indices should account for both dense and sparse embedding dimensions in hybrid configurations
  - Monitor query performance differences between dense-only and hybrid retrieval modes for optimal configuration

## Troubleshooting Guide
Common issues and resolutions for the enhanced RAG system:

- **Missing Semantic Chunking Dependencies**
  - The system requires langchain-experimental for SemanticChunker functionality. Ensure `langchain-experimental>=0.3.0` is installed as part of project dependencies.
  - Semantic chunking raises ImportError if LangChain Experimental is not available during initialization.
- **Missing Hybrid Search Dependencies**
  - Hybrid search requires fastembed for sparse embeddings. Install the 'hybrid' extra: `uv sync --extra hybrid`
  - FastEmbedSparse import failures trigger ImportError with guidance for installing hybrid dependencies.
  - Sparse embeddings initialization gracefully falls back to dense-only retrieval when dependencies are unavailable.
- **Semantic Chunking Configuration Issues**
  - Invalid chunk_strategy values raise ValueError in parser functions. Use 'recursive' or 'semantic' only.
  - Missing embeddings parameter for semantic strategy raises ValueError with clear error message.
  - Breakpoint threshold type validation ensures only supported types are used: 'percentile', 'standard_deviation', 'interquartile', 'gradient'.
  - Breakpoint threshold amount validation prevents invalid numeric values outside expected ranges.
- **Hybrid Search Mode Configuration**
  - retrieval_mode must be 'dense' or 'hybrid'. Invalid values fall back to dense mode.
  - sparse_embedding_model configuration affects FastEmbedSparse initialization and model availability.
  - Sparse embedding initialization failures log warnings and disable hybrid mode gracefully.
- **Resource Initialization Failures**
  - Qdrant client initialization failures prevent semantic chunking and hybrid search functionality.
  - Embeddings model initialization errors affect both chunking strategies and retrieval operations.
  - Resource cleanup handles partial initialization failures without blocking application shutdown.
- **Performance and Memory Issues**
  - Semantic chunking requires additional memory for embedding model loading and breakpoint calculations.
  - Large documents with semantic chunking may require increased memory allocation for embedding computations.
  - Monitor chunk count growth when switching from recursive to semantic chunking as semantic boundaries may create more chunks.
- **Backward Compatibility**
  - Default chunk_strategy remains 'recursive' to maintain backward compatibility with existing deployments.
  - Legacy .doc files automatically use semantic chunking when strategy is 'semantic' with empty section metadata.
  - Existing API endpoints continue to work with semantic chunking parameters passed through configuration.

**Section sources**
- [retriever.py:88-103](file://app/rag/retriever.py#L88-L103)
- [parser.py:115-118](file://app/rag/parser.py#L115-L118)
- [parser.py:240-242](file://app/rag/parser.py#L240-L242)
- [config.py:54-62](file://app/config.py#L54-L62)
- [resources.py:120-132](file://app/resources.py#L120-L132)

## Conclusion
The RAG Parser Enhancement delivers a comprehensive, production-ready pipeline for processing HR documents with advanced semantic understanding and hybrid search capabilities. By implementing dual chunking strategies (recursive and semantic) with configurable breakpoint thresholds, integrating LangChain's SemanticChunker for intelligent boundary detection, supporting hybrid dense-sparse retrieval with BM25 keyword matching, and providing robust configuration management, the system significantly enhances document processing accuracy and retrieval performance. The modular architecture with graceful fallback mechanisms ensures backward compatibility while enabling cutting-edge retrieval capabilities. The enhanced testing infrastructure validates both semantic chunking functionality and hybrid search operations, while the centralized configuration system provides fine-grained control over chunking strategies and retrieval modes. The system's ability to automatically initialize sparse embeddings for hybrid search, combined with comprehensive error handling and resource management, makes it suitable for enterprise-scale document processing with superior semantic understanding and flexible retrieval options.