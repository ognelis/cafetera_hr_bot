# VK Integration

<cite>
**Referenced Files in This Document**
- [bot.py](file://app/integrations/vk/bot.py)
- [start.py](file://app/integrations/vk/handlers/start.py)
- [sections.py](file://app/integrations/vk/handlers/sections.py)
- [ask.py](file://app/integrations/vk/handlers/ask.py)
- [hr_request.py](file://app/integrations/vk/handlers/hr_request.py)
- [fire.py](file://app/integrations/vk/handlers/fire.py)
- [pay.py](file://app/integrations/vk/handlers/pay.py)
- [vacation.py](file://app/integrations/vk/handlers/vacation.py)
- [fallback.py](file://app/integrations/vk/handlers/fallback.py)
- [keyboards.py](file://app/integrations/vk/keyboards.py)
- [states.py](file://app/integrations/vk/states.py)
- [qa_service.py](file://app/domain/qa_service.py)
- [chain.py](file://app/rag/chain.py)
- [polling_vk.py](file://scripts/polling_vk.py)
- [config.py](file://app/config.py)
- [test_bot_factory.py](file://tests/test_bot_factory.py)
- [test_qa_service.py](file://tests/test_qa_service.py)
- [test_keyboards.py](file://tests/test_keyboards.py)
- [test_states.py](file://tests/test_states.py)
- [pyproject.toml](file://pyproject.toml)
</cite>

## Update Summary
**Changes Made**
- Added comprehensive documentation for the QA service integration and RAG processing system
- Updated handler registration patterns to reflect the new QA service usage across HR-related handlers
- Enhanced integration patterns documentation with proper resource management and error handling
- Added detailed coverage of the new ask-a-question handler and its RAG capabilities
- Updated architecture diagrams to show the QA service integration layer

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [QA Service and RAG Integration](#qa-service-and-rag-integration)
6. [Detailed Component Analysis](#detailed-component-analysis)
7. [Dependency Analysis](#dependency-analysis)
8. [Performance Considerations](#performance-considerations)
9. [Troubleshooting Guide](#troubleshooting-guide)
10. [Conclusion](#conclusion)
11. [Appendices](#appendices)

## Introduction
This document explains the VKontakte integration system built with the vkbottle framework, featuring a comprehensive QA service integration for Retrieval-Augmented Generation (RAG) processing across all HR-related handlers. The system implements a bot factory pattern, advanced handler registration and ordering, payload-based navigation, and sophisticated VK API integration patterns. It covers bot initialization, message routing, RAG-powered content delivery, and practical guidance for extending the bot with new handlers, customizing behavior, and integrating with VK's webhook system. Common integration challenges, robust error handling, and best practices for VK bot development are addressed.

## Project Structure
The VK integration resides under app/integrations/vk and includes:
- A bot factory that wires a vkbottle Bot with labeled handlers and shared state management
- Handler modules for start/main menu, section entry points, dedicated ask-a-question functionality, and HR request workflows
- Keyboard builders for consistent UI and payload-driven navigation
- State definitions for multi-step dialogs
- A domain-level QA service that provides RAG processing capabilities
- A local development script to run the bot in Long Poll mode
- Tests validating factory wiring, keyboard layouts, state definitions, and QA service integration

```mermaid
graph TB
subgraph "VK Integration"
BOT["bot.py<br/>Bot factory"]
START["handlers/start.py<br/>Start & main menu"]
SECTIONS["handlers/sections.py<br/>Section entry points (RAG)"]
ASK["handlers/ask.py<br/>Ask-a-question (RAG)"]
HR_REQUEST["handlers/hr_request.py<br/>Multi-step HR requests"]
FIRE["handlers/fire.py<br/>Dismissal flows (RAG)"]
PAY["handlers/pay.py<br/>Pay & bonus flows (RAG)"]
VACATION["handlers/vacation.py<br/>Vacation flows (RAG)"]
FALLBACK["handlers/fallback.py<br/>Unmatched messages"]
KEYBOARDS["keyboards.py<br/>Keyboard builders & payloads"]
STATES["states.py<br/>Dialog states"]
end
QA_SERVICE["domain/qa_service.py<br/>RAG chain wrapper"]
CHAIN["rag/chain.py<br/>RAG implementation"]
SCRIPT["scripts/polling_vk.py<br/>Long Poll runner"]
CONFIG["app/config.py<br/>Settings"]
TESTS["tests/<br/>Integration tests"]
BOT --> START
BOT --> SECTIONS
BOT --> ASK
BOT --> HR_REQUEST
BOT --> FIRE
BOT --> PAY
BOT --> VACATION
BOT --> FALLBACK
START --> KEYBOARDS
SECTIONS --> KEYBOARDS
ASK --> KEYBOARDS
HR_REQUEST --> KEYBOARDS
FIRE --> KEYBOARDS
PAY --> KEYBOARDS
VACATION --> KEYBOARDS
ASK --> QA_SERVICE
FIRE --> QA_SERVICE
PAY --> QA_SERVICE
VACATION --> QA_SERVICE
SECTIONS --> QA_SERVICE
QA_SERVICE --> CHAIN
BOT --> CONFIG
TESTS --> BOT
TESTS --> QA_SERVICE
STATES -. optional .-> BOT
```

**Diagram sources**
- [bot.py:1-56](file://app/integrations/vk/bot.py#L1-L56)
- [ask.py:1-86](file://app/integrations/vk/handlers/ask.py#L1-L86)
- [hr_request.py:1-305](file://app/integrations/vk/handlers/hr_request.py#L1-L305)
- [fire.py:1-82](file://app/integrations/vk/handlers/fire.py#L1-L82)
- [pay.py:1-57](file://app/integrations/vk/handlers/pay.py#L1-L57)
- [vacation.py:1-93](file://app/integrations/vk/handlers/vacation.py#L1-L93)
- [sections.py:1-46](file://app/integrations/vk/handlers/sections.py#L1-L46)
- [qa_service.py:1-120](file://app/domain/qa_service.py#L1-L120)
- [chain.py:1-80](file://app/rag/chain.py#L1-L80)
- [polling_vk.py:1-33](file://scripts/polling_vk.py#L1-L33)
- [config.py:1-9](file://app/config.py#L1-L9)

**Section sources**
- [bot.py:1-56](file://app/integrations/vk/bot.py#L1-L56)
- [polling_vk.py:1-33](file://scripts/polling_vk.py#L1-L33)
- [config.py:1-9](file://app/config.py#L1-L9)

## Core Components
- Bot factory: Creates a vkbottle Bot with shared state dispenser, loads handler labelers in strict order, and integrates the QA service for RAG processing
- Handlers: Define message routes for start, main menu navigation, section entry points, dedicated ask-a-question functionality, and multi-step HR request workflows
- QA Service: Provides centralized RAG processing with proper resource management, error handling, and VK message length truncation
- Keyboard builders: Provide consistent UI and payload constants for navigation
- States: Define multi-step dialog states for complex HR workflows
- Local runner: Initializes Settings and starts the bot in Long Poll mode

Key implementation references:
- Factory and handler loading order with QA integration: [bot.py:44-55](file://app/integrations/vk/bot.py#L44-L55)
- QA service initialization and RAG processing: [qa_service.py:51-105](file://app/domain/qa_service.py#L51-L105)
- Ask-a-question handler with RAG integration: [ask.py:49-85](file://app/integrations/vk/handlers/ask.py#L49-L85)
- HR request multi-step dialog: [hr_request.py:69-305](file://app/integrations/vk/handlers/hr_request.py#L69-L305)
- RAG-enabled HR handlers: [fire.py:61-81](file://app/integrations/vk/handlers/fire.py#L61-L81), [pay.py:36-56](file://app/integrations/vk/handlers/pay.py#L36-L56), [vacation.py:72-92](file://app/integrations/vk/handlers/vacation.py#L72-L92)
- Keyboard builders and payloads: [keyboards.py:13-108](file://app/integrations/vk/keyboards.py#L13-L108)
- Dialog states: [states.py:4-14](file://app/integrations/vk/states.py#L4-L14)
- Local runner: [polling_vk.py:24-28](file://scripts/polling_vk.py#L24-L28)
- Settings: [config.py:4-9](file://app/config.py#L4-L9)

**Section sources**
- [bot.py:24-55](file://app/integrations/vk/bot.py#L24-L55)
- [qa_service.py:1-120](file://app/domain/qa_service.py#L1-L120)
- [ask.py:1-86](file://app/integrations/vk/handlers/ask.py#L1-L86)
- [hr_request.py:1-305](file://app/integrations/vk/handlers/hr_request.py#L1-L305)
- [fire.py:1-82](file://app/integrations/vk/handlers/fire.py#L1-L82)
- [pay.py:1-57](file://app/integrations/vk/handlers/pay.py#L1-L57)
- [vacation.py:1-93](file://app/integrations/vk/handlers/vacation.py#L1-L93)
- [sections.py:1-46](file://app/integrations/vk/handlers/sections.py#L1-L46)
- [keyboards.py:13-108](file://app/integrations/vk/keyboards.py#L13-L108)
- [states.py:4-14](file://app/integrations/vk/states.py#L4-L14)
- [polling_vk.py:24-28](file://scripts/polling_vk.py#L24-L28)
- [config.py:4-9](file://app/config.py#L4-L9)

## Architecture Overview
The VK bot follows a modular architecture with integrated RAG capabilities:
- The factory constructs a Bot with shared state dispenser and registers labelers in a fixed order to ensure deterministic routing
- Handlers react to text commands and payload events, leveraging the QA service for intelligent content generation
- The QA service provides centralized RAG processing with proper resource management and error handling
- Payload constants drive navigation across screens, ensuring consistent UX
- Optional state groups enable multi-step dialogs with sophisticated HR workflows

```mermaid
sequenceDiagram
participant Dev as "Developer"
participant Script as "polling_vk.py"
participant Factory as "bot.create_bot()"
participant Bot as "vkbottle.Bot"
participant Labelers as "Handler Labelers"
participant QA as "QA Service"
participant RAG as "RAG Chain"
participant VK as "VK API"
Dev->>Script : Run long poll
Script->>Factory : create_bot(Settings)
Factory->>Bot : Initialize with token
Factory->>Labelers : Load handlers (start, hr_request, ask, fire, pay, vacation, sections, fallback)
Factory->>QA : Initialize RAG chain (init_qa)
Labelers->>QA : Query RAG for HR-related questions
QA->>RAG : Process with retriever + LLM
RAG-->>QA : Generated answer
QA-->>Labelers : Formatted response
Script->>Bot : run_polling()
Bot->>VK : Poll for updates
VK-->>Bot : Incoming message
Bot->>Labelers : Match handler (top to bottom)
Labelers-->>Bot : Respond with text and keyboard
Bot-->>VK : Send response
```

**Diagram sources**
- [polling_vk.py:24-28](file://scripts/polling_vk.py#L24-L28)
- [bot.py:44-55](file://app/integrations/vk/bot.py#L44-L55)
- [qa_service.py:51-105](file://app/domain/qa_service.py#L51-L105)
- [chain.py:61-79](file://app/rag/chain.py#L61-L79)
- [ask.py:75-85](file://app/integrations/vk/handlers/ask.py#L75-L85)

## QA Service and RAG Integration

### QA Service Architecture
The QA service provides a centralized RAG processing layer with robust error handling and resource management:

```mermaid
classDiagram
class QAService {
-_chain : Runnable | None
-_qdrant_client : QdrantClient | None
+init_qa(settings) None
+ask(question) str
+close_qa() None
+_truncate(text) str
}
class RAGChain {
+build_llm(settings) BaseChatModel
+build_rag_chain(retriever, llm) Runnable
}
class ErrorHandler {
+ERR_NO_ANSWER : str
+ERR_DOCUMENT_UNAVAILABLE : str
+VK_MSG_LIMIT : int
}
QAService --> RAGChain : uses
QAService --> ErrorHandler : returns
```

**Diagram sources**
- [qa_service.py:23-105](file://app/domain/qa_service.py#L23-L105)
- [chain.py:30-79](file://app/rag/chain.py#L30-L79)

### RAG Processing Pipeline
The RAG system integrates Qdrant vector database with configurable LLM providers:

```mermaid
flowchart TD
Start(["User Question"]) --> Detect["Topic Detection"]
Detect --> QAService["QA Service.ask()"]
QAService --> CheckChain{"Chain Available?"}
CheckChain --> |No| NoAnswer["Return ERR_NO_ANSWER"]
CheckChain --> |Yes| Invoke["Invoke RAG Chain"]
Invoke --> HandleError{"Exception?"}
HandleError --> |Yes| DocUnavailable["Return ERR_DOCUMENT_UNAVAILABLE"]
HandleError --> |No| CheckAnswer{"Empty Answer?"}
CheckAnswer --> |Yes| NoAnswer
CheckAnswer --> |No| Truncate["Truncate to VK Limit"]
Truncate --> Response["Formatted Response"]
Response --> End(["Send to User"])
NoAnswer --> End
DocUnavailable --> End
```

**Diagram sources**
- [qa_service.py:86-105](file://app/domain/qa_service.py#L86-L105)
- [chain.py:61-79](file://app/rag/chain.py#L61-L79)

### Handler Integration Patterns
All HR-related handlers now leverage the QA service for intelligent content delivery:

**Updated** All HR-related handlers (fire, pay, vacation, sections) now use the QA service for RAG-powered responses, replacing static content with dynamic, contextually relevant information.

**Section sources**
- [qa_service.py:1-120](file://app/domain/qa_service.py#L1-L120)
- [chain.py:1-80](file://app/rag/chain.py#L1-L80)
- [fire.py:61-81](file://app/integrations/vk/handlers/fire.py#L61-L81)
- [pay.py:36-56](file://app/integrations/vk/handlers/pay.py#L36-L56)
- [vacation.py:72-92](file://app/integrations/vk/handlers/vacation.py#L72-L92)
- [sections.py:25-45](file://app/integrations/vk/handlers/sections.py#L25-L45)

## Detailed Component Analysis

### Bot Factory Pattern and Handler Registration
- The factory initializes a Bot with the VK access token from Settings and establishes shared state management
- It loads nine labelers in a specific order: start, hr_request, ask, hire, fire, vacation, pay, sections, fallback
- The order is crucial because vkbottle evaluates handlers top-to-bottom; fallback must be last to avoid intercepting intended matches
- The QA service is initialized during bot creation to provide RAG capabilities across all handlers

```mermaid
flowchart TD
Start(["create_bot(settings)"]) --> Init["Initialize Bot with token"]
Init --> ShareState["Share state dispenser"]
ShareState --> LoadHandlers["Load 9 labelers in order"]
LoadHandlers --> InitQA["Initialize QA service"]
InitQA --> Log["Log handler count"]
Log --> ReturnBot(["Return Bot"])
```

**Diagram sources**
- [bot.py:44-55](file://app/integrations/vk/bot.py#L44-L55)

**Section sources**
- [bot.py:24-55](file://app/integrations/vk/bot.py#L24-L55)
- [test_bot_factory.py:18-85](file://tests/test_bot_factory.py#L18-L85)

### Message Routing and Navigation with Payloads
- Start handler responds to initial commands and sends the main menu with service buttons
- Payload constants define navigation actions (Home, Back, Contact HR, Section commands)
- Section handlers reply with RAG-generated content and a service row keyboard
- Ask handler provides dedicated question-answering with state management
- Fallback handler ensures users stay within the menu-driven interface
- HR request handlers manage complex multi-step workflows with state persistence

```mermaid
sequenceDiagram
participant User as "User"
participant Bot as "vkbottle.Bot"
participant Start as "start.on_start/on_home"
participant Ask as "ask.on_ask/on_ask_text"
participant HR as "hr_request.*"
participant Sections as "sections.*"
participant Fallback as "fallback.on_fallback"
User->>Bot : "/start" or "Start" or "Начать"
Bot->>Start : Match text route
Start-->>User : Greeting + main menu keyboard
User->>Bot : Payload "cmd_ask"
Bot->>Ask : Match payload route
Ask-->>User : Set ASK_QUESTION state
User->>Bot : Free text question
Ask->>QA : Query RAG chain
QA-->>Ask : Generated answer
Ask-->>User : Answer + navigation options
User->>Bot : Payload "contact_hr"
Bot->>HR : Match payload route
HR-->>User : Multi-step HR request flow
User->>Bot : Arbitrary text
Bot->>Fallback : Match default handler
Fallback-->>User : Prompt to use menu
```

**Diagram sources**
- [start.py:31-54](file://app/integrations/vk/handlers/start.py#L31-L54)
- [ask.py:34-85](file://app/integrations/vk/handlers/ask.py#L34-L85)
- [hr_request.py:69-305](file://app/integrations/vk/handlers/hr_request.py#L69-L305)
- [sections.py:25-45](file://app/integrations/vk/handlers/sections.py#L25-L45)
- [fallback.py:15-17](file://app/integrations/vk/handlers/fallback.py#L15-L17)

**Section sources**
- [start.py:14-55](file://app/integrations/vk/handlers/start.py#L14-L55)
- [ask.py:1-86](file://app/integrations/vk/handlers/ask.py#L1-L86)
- [hr_request.py:1-305](file://app/integrations/vk/handlers/hr_request.py#L1-L305)
- [sections.py:1-46](file://app/integrations/vk/handlers/sections.py#L1-L46)
- [fallback.py:9-18](file://app/integrations/vk/handlers/fallback.py#L9-L18)
- [keyboards.py:13-108](file://app/integrations/vk/keyboards.py#L13-L108)

### Keyboard Builders and Payload Constants
- Payload constants define navigation semantics (home, back, contact HR, section commands)
- Keyboard builders assemble rows and append a standard service row with Back/Home/Contact HR
- The main menu keyboard organizes seven sections plus a dedicated "Contact HR" button
- Specialized keyboards support multi-step dialog flows and RAG-powered content presentation

```mermaid
classDiagram
class Payloads {
+CMD_HOME
+CMD_BACK
+CMD_CONTACT_HR
+CMD_HIRE
+CMD_FIRE
+CMD_VACATION
+CMD_PAY
+CMD_SICK
+CMD_PROBATION
+CMD_ASK
+CMD_HR_* (multi-step states)
}
class KeyboardBuilders {
+with_service_row(kb, back_payload, show_home, show_hr) Keyboard
+main_menu_kb() Keyboard
+ask_input_kb() Keyboard
+ask_result_kb(scenario_id) Keyboard
+hr_*_kb() Various HR keyboards
+stub_kb(back_payload) Keyboard
}
Payloads <.. KeyboardBuilders : "used by"
```

**Diagram sources**
- [keyboards.py:13-108](file://app/integrations/vk/keyboards.py#L13-L108)

**Section sources**
- [keyboards.py:13-108](file://app/integrations/vk/keyboards.py#L13-L108)
- [test_keyboards.py:49-92](file://tests/test_keyboards.py#L49-L92)
- [test_keyboards.py:97-150](file://tests/test_keyboards.py#L97-L150)
- [test_keyboards.py:155-171](file://tests/test_keyboards.py#L155-L171)
- [test_keyboards.py:176-192](file://tests/test_keyboards.py#L176-L192)

### Dialog States for Multi-Step Flows
- States are defined as a typed group to support multi-step dialogs (e.g., HR request wizard)
- The ask-a-question flow uses dedicated state management to handle free-text input
- Tests confirm the state group inherits from the base type and contains expected state names/values

```mermaid
classDiagram
class BotStates {
+HR_REQUEST_NAME
+HR_REQUEST_TOPIC
+HR_REQUEST_DETAILS
+HR_REQUEST_ENTITY
+HR_REQUEST_URGENCY
+HR_REQUEST_CONFIRM
+ASK_QUESTION
}
```

**Diagram sources**
- [states.py:4-14](file://app/integrations/vk/states.py#L4-L14)

**Section sources**
- [states.py:4-14](file://app/integrations/vk/states.py#L4-L14)
- [test_states.py:8-31](file://tests/test_states.py#L8-L31)

### Bot Initialization and Long Poll Runner
- The local runner loads Settings, creates the Bot via the factory, and starts Long Polling
- The factory initializes the QA service during bot creation for immediate RAG capabilities
- Logging is configured for development visibility with RAG processing metrics

```mermaid
sequenceDiagram
participant CLI as "CLI"
participant Runner as "polling_vk.main()"
participant Factory as "bot.create_bot()"
participant Bot as "vkbottle.Bot"
participant QA as "QA Service"
CLI->>Runner : Execute script
Runner->>Factory : create_bot(Settings)
Factory-->>Runner : Bot instance with QA
Factory->>QA : init_qa(settings)
QA-->>Factory : RAG chain ready
Runner->>Bot : run_polling()
Bot-->>Runner : Running
```

**Diagram sources**
- [polling_vk.py:24-28](file://scripts/polling_vk.py#L24-L28)
- [bot.py:44-55](file://app/integrations/vk/bot.py#L44-L55)
- [qa_service.py:51-81](file://app/domain/qa_service.py#L51-L81)

**Section sources**
- [polling_vk.py:17-33](file://scripts/polling_vk.py#L17-L33)
- [config.py:4-9](file://app/config.py#L4-L9)

## Dependency Analysis
External dependencies relevant to VK integration:
- vkbottle is the primary framework for VK bot development
- pydantic-settings provides typed configuration from environment variables
- pytest is used for unit tests covering factory wiring, keyboards, states, and QA service integration
- LangChain provides the RAG framework with configurable LLM providers
- Qdrant client provides vector database capabilities for document retrieval

```mermaid
graph LR
VKBot["VK Bot (bot.py)"] --> VKFw["vkbottle"]
VKBot --> Cfg["Settings (config.py)"]
VKBot --> QA["QA Service (qa_service.py)"]
QA --> LangChain["LangChain"]
QA --> Qdrant["Qdrant Client"]
Tests["Tests"] --> VKBot
Tests --> QA
Tests --> VKFw
Tests --> Cfg
```

**Diagram sources**
- [bot.py:7-10](file://app/integrations/vk/bot.py#L7-L10)
- [config.py:4-9](file://app/config.py#L4-L9)
- [qa_service.py:60-81](file://app/domain/qa_service.py#L60-L81)
- [pyproject.toml:17-21](file://pyproject.toml#L17-L21)

**Section sources**
- [pyproject.toml:17-21](file://pyproject.toml#L17-L21)
- [bot.py:7-10](file://app/integrations/vk/bot.py#L7-L10)
- [config.py:4-9](file://app/config.py#L4-L9)
- [qa_service.py:60-81](file://app/domain/qa_service.py#L60-L81)

## Performance Considerations
- Handler order minimizes unnecessary evaluations; keep fallback last
- QA service implements proper resource management with connection pooling and graceful degradation
- RAG responses are truncated to VK message limits to prevent API errors
- Keyboard construction is lightweight; reuse shared keyboards and payloads to reduce overhead
- Long Poll mode is suitable for small to medium workloads; consider webhooks for higher throughput
- Avoid heavy synchronous operations inside handlers; delegate to async tasks when needed
- QA service handles LLM provider failures gracefully with fallback responses

## Troubleshooting Guide
Common issues and resolutions:
- Handler not triggered:
  - Verify handler order and that fallback is last
  - Confirm payload keys match exactly (case-sensitive)
- Incorrect keyboard layout:
  - Validate main menu composition and service row inclusion
  - Ensure payloads are present and unique
- Token errors:
  - Confirm VK access token is set in environment and forwarded to the Bot
- QA service failures:
  - Check Qdrant connectivity and LLM provider availability
  - Verify settings for qdrant_url, qdrant_api_key, qdrant_collection
  - Monitor for RAG chain initialization warnings
- Multi-step dialogs:
  - Use state groups to track user progress and avoid ambiguous replies
- RAG response issues:
  - Check for VK message length truncation
  - Verify topic detection and scenario linking

Validation references:
- Handler order and counts: [test_bot_factory.py:18-85](file://tests/test_bot_factory.py#L18-L85)
- QA service integration: [test_qa_service.py:176-198](file://tests/test_qa_service.py#L176-L198)
- Keyboard composition and payloads: [test_keyboards.py:49-92](file://tests/test_keyboards.py#L49-L92), [test_keyboards.py:176-192](file://tests/test_keyboards.py#L176-L192)
- State definitions: [test_states.py:8-31](file://tests/test_states.py#L8-L31)

**Section sources**
- [test_bot_factory.py:18-85](file://tests/test_bot_factory.py#L18-L85)
- [test_qa_service.py:176-198](file://tests/test_qa_service.py#L176-L198)
- [test_keyboards.py:49-92](file://tests/test_keyboards.py#L49-L92)
- [test_keyboards.py:176-192](file://tests/test_keyboards.py#L176-L192)
- [test_states.py:8-31](file://tests/test_states.py#L8-L31)

## Conclusion
The VK integration leverages a clean factory pattern, deterministic handler ordering, payload-driven navigation, and comprehensive RAG integration to deliver a sophisticated, extensible bot. The QA service provides centralized intelligence processing with proper resource management and error handling, enabling dynamic content generation across all HR-related handlers. By following the established patterns—registering labelers in order, using shared keyboard builders, implementing state management, and integrating the QA service—the system supports easy extension and maintenance. For production, consider migrating to VK webhooks, adding structured error handling and logging, and implementing proper QA service lifecycle management.

## Appendices

### Extending the Bot with New Handlers
Steps to add a new section:
- Define a payload constant for the new command
- Add a handler in a new or existing module annotated with the payload
- Integrate with the QA service for RAG-powered content delivery
- Build a keyboard with the service row to ensure Back/Home/Contact HR are always available
- Register the new labeler in the factory's loader list and ensure it precedes fallback

**Updated** When adding new handlers, integrate with the QA service by importing `from app.domain import qa_service` and using `await qa_service.ask(question)` for dynamic content generation.

References:
- Payload constants: [keyboards.py:13-24](file://app/integrations/vk/keyboards.py#L13-L24)
- Handler registration order: [bot.py:31-41](file://app/integrations/vk/bot.py#L31-L41)
- QA service integration: [qa_service.py:86-105](file://app/domain/qa_service.py#L86-L105)
- Keyboard service row: [keyboards.py:29-50](file://app/integrations/vk/keyboards.py#L29-L50)

**Section sources**
- [keyboards.py:13-50](file://app/integrations/vk/keyboards.py#L13-L50)
- [bot.py:31-41](file://app/integrations/vk/bot.py#L31-L41)
- [qa_service.py:86-105](file://app/domain/qa_service.py#L86-L105)

### Integrating with VK Webhook System
Guidance:
- Configure a VK community webhook endpoint pointing to your server
- Replace Long Poll runner with a FastAPI route that accepts VK POST callbacks
- Parse incoming update objects and dispatch to the same handler labelers
- Ensure the Bot is initialized with the same token, labelers, and QA service as in Long Poll mode
- Implement proper error handling for webhook processing failures

References:
- Bot initialization and token forwarding: [bot.py:44-55](file://app/integrations/vk/bot.py#L44-L55), [test_bot_factory.py:74-85](file://tests/test_bot_factory.py#L74-L85)
- Handler registration: [bot.py:51-52](file://app/integrations/vk/bot.py#L51-L52)
- QA service initialization: [qa_service.py:51-81](file://app/domain/qa_service.py#L51-L81)

**Section sources**
- [bot.py:44-55](file://app/integrations/vk/bot.py#L44-L55)
- [test_bot_factory.py:74-85](file://tests/test_bot_factory.py#L74-L85)
- [qa_service.py:51-81](file://app/domain/qa_service.py#L51-L81)

### Best Practices for VK Bot Development
- Keep handler order explicit and documented
- Use payload constants to prevent typos and ensure consistency
- Prefer keyboard-driven navigation to reduce ambiguity
- Centralize keyboard building logic to enforce UX standards
- Integrate the QA service for dynamic content generation across HR-related flows
- Implement proper error handling and fallback responses for QA service failures
- Add logging around handler execution and RAG processing for observability
- Validate configuration at startup and fail fast on missing tokens or QA service initialization failures
- Manage QA service lifecycle with proper resource cleanup during shutdown

### QA Service Integration Patterns
- Initialize QA service during bot creation for immediate RAG capabilities
- Use `await qa_service.ask(question)` for all HR-related content generation
- Implement proper error handling with fallback responses
- Truncate long responses to VK message limits automatically
- Close QA service resources properly during application shutdown
- Monitor QA service health and implement graceful degradation strategies

**Section sources**
- [qa_service.py:51-120](file://app/domain/qa_service.py#L51-L120)
- [test_qa_service.py:1-198](file://tests/test_qa_service.py#L1-L198)