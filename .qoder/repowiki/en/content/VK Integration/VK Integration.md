# VK Integration

<cite>
**Referenced Files in This Document**
- [bot.py](file://app/integrations/vk/bot.py)
- [start.py](file://app/integrations/vk/handlers/start.py)
- [sections.py](file://app/integrations/vk/handlers/sections.py)
- [ask.py](file://app/integrations/vk/handlers/ask.py)
- [fire.py](file://app/integrations/vk/handlers/fire.py)
- [pay.py](file://app/integrations/vk/handlers/pay.py)
- [vacation.py](file://app/integrations/vk/handlers/vacation.py)
- [fallback.py](file://app/integrations/vk/handlers/fallback.py)
- [hire.py](file://app/integrations/vk/handlers/hire.py)
- [keyboards.py](file://app/integrations/vk/keyboards.py)
- [states.py](file://app/integrations/vk/states.py)
- [handlers/__init__.py](file://app/integrations/vk/handlers/__init__.py)
- [rules.py](file://app/integrations/vk/rules.py)
- [entities.py](file://app/domain/entities.py)
- [qa_service.py](file://app/domain/qa_service.py)
- [chain.py](file://app/rag/chain.py)
- [polling_vk.py](file://scripts/polling_vk.py)
- [resources.py](file://app/resources.py)
- [config.py](file://app/config.py)
- [test_bot_factory.py](file://tests/test_bot_factory.py)
- [test_qa_service.py](file://tests/test_qa_service.py)
- [test_keyboards.py](file://tests/test_keyboards.py)
- [test_states.py](file://tests/test_states.py)
- [test_ask_block9.py](file://tests/test_ask_block9.py)
- [category_file_service.py](file://app/domain/category_file_service.py)
- [category_files.py](file://app/api/category_files.py)
- [s3.py](file://app/storage/s3.py)
- [category_models.py](file://app/storage/category_models.py)
- [category_repo.py](file://app/storage/category_repo.py)
- [deps.py](file://app/api/deps.py)
- [category_files.html](file://templates/category_files.html)
- [category_slot.html](file://templates/partials/category_slot.html)
- [attachments.py](file://app/integrations/vk/attachments.py)
- [pyproject.toml](file://pyproject.toml)
</cite>

## Update Summary
**Changes Made**
- Enhanced error handling consistency with new require_entity decorators and @catch_entity_error decorators
- Replaced get_entity_or_error pattern with require_entity functions and @catch_entity_error decorators for improved error handling across fire.py and handlers/__init__.y modules
- Added EntityNotFoundError class for consistent entity validation error handling
- Updated handler registration and ordering with improved error handling patterns
- Enhanced fire handler with require_entity decorator integration
- Improved error handling patterns in hire handler with @catch_entity_error decorators
- Updated vacation handler to maintain backward compatibility with get_entity_or_error pattern
- Enhanced test infrastructure with updated error handling expectations

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Centralized State Management](#centralized-state-management)
6. [Centralized QA Service Access Layer](#centralized-qa-service-access-layer)
7. [Enhanced RAG Response Handling](#enhanced-rag-response-handling)
8. [Document Template Management System](#document-template-management-system)
9. [QA Service and RAG Integration](#qa-service-and-rag-integration)
10. [Enhanced Fire Handler with Entity-Based Resignation Flow](#enhanced-fire-handler-with-entity-based-resignation-flow)
11. [Enhanced Error Handling with Decorators](#enhanced-error-handling-with-decorators)
12. [Detailed Component Analysis](#detailed-component-analysis)
13. [Dependency Analysis](#dependency-analysis)
14. [Performance Considerations](#performance-considerations)
15. [Troubleshooting Guide](#troubleshooting-guide)
16. [Conclusion](#conclusion)
17. [Appendices](#appendices)

## Introduction
This document explains the VKontakte integration system built with the vkbottle framework, featuring a comprehensive QA service integration for Retrieval-Augmented Generation (RAG) processing across all HR-related handlers. The system implements a bot factory pattern with centralized state dispenser sharing, advanced handler registration and ordering, payload-based navigation, and sophisticated VK API integration patterns. It covers bot initialization, message routing, RAG-powered content delivery, and practical guidance for extending the bot with new handlers, customizing behavior, and integrating with VK's webhook system. Common integration challenges, robust error handling, and best practices for VK bot development are addressed.

**Updated** The system now features enhanced error handling consistency with new require_entity decorators and @catch_entity_error decorators, providing improved reliability and user experience across all HR-related handlers. The new error handling patterns replace the previous get_entity_or_error pattern with more consistent and maintainable approaches.

## Project Structure
The VK integration resides under app/integrations/vk and includes:
- A bot factory that wires a vkbottle Bot with labeled handlers, shared state management, and centralized QA service access
- Handler modules for start/main menu, section entry points, dedicated ask-a-question functionality, and HR request workflows
- Keyboard builders for consistent UI and payload-driven navigation
- State definitions for multi-step dialogs using centralized state dispenser
- A domain-level QA service that provides RAG processing capabilities
- Enhanced fire handler with entity-based resignation flow and improved error handling
- A new document attachment system for delivering company-specific templates
- Tests validating factory wiring, keyboard layouts, state definitions, QA service integration, and enhanced handler functionality

```mermaid
graph TB
subgraph "VK Integration"
BOT["bot.py<br/>Bot factory with centralized state sharing"]
START["handlers/start.py<br/>Start & main menu"]
SECTIONS["handlers/sections.py<br/>Section entry points (RAG)"]
ASK["handlers/ask.py<br/>Ask-a-question (RAG)"]
HIRE["handlers/hire.py<br/>Hiring flows (multi-step)"]
FIRE["handlers/fire.py<br/>Enhanced dismissal flows (entity-based)"]
PAY["handlers/pay.py<br/>Pay & bonus flows (RAG)"]
VACATION["handlers/vacation.py<br/>Enhanced vacation flows (templates)"]
FALLBACK["handlers/fallback.py<br/>Unmatched messages"]
KEYBOARDS["keyboards.py<br/>Enhanced keyboard builders & payloads"]
ATTACHMENTS["attachments.py<br/>Document attachment helper"]
STATES["states.py<br/>Dialog states"]
UTILS["handlers/__init__.py<br/>Centralized state & QA access"]
RULES["rules.py<br/>Custom payload rules"]
ENTITIES["entities.py<br/>Updated legal entities"]
end
subgraph "Enhanced Error Handling"
REQUIRE_ENTITY["require_entity<br/>Entity validation function"]
CATCH_ERROR["@catch_entity_error<br/>Error handling decorator"]
ENTITY_NOT_FOUND["EntityNotFoundError<br/>Exception class"]
end
subgraph "Enhanced Fire Flow"
FIRE_MENU["Fire menu keyboard<br/>Resignation & grounds"]
ENTITY_SELECT["Entity selection keyboard<br/>Company-specific templates"]
DOC_ATTACHMENT["Document attachment<br/>Template delivery"]
end
RESOURCES["resources.py<br/>Resource management"]
QA_SERVICE["domain/qa_service.py<br/>RAG chain wrapper"]
CHAIN["rag/chain.py<br/>RAG implementation"]
SCRIPT["scripts/polling_vk.py<br/>Long Poll runner"]
CONFIG["app/config.py<br/>Settings"]
TESTS["tests/<br/>Enhanced integration tests"]
BOT --> START
BOT --> SECTIONS
BOT --> ASK
BOT --> HIRE
BOT --> FIRE
BOT --> PAY
BOT --> VACATION
BOT --> FALLBACK
START --> KEYBOARDS
SECTIONS --> KEYBOARDS
ASK --> KEYBOARDS
HIRE --> KEYBOARDS
FIRE --> KEYBOARDS
PAY --> KEYBOARDS
VACATION --> KEYBOARDS
FIRE --> ATTACHMENTS
ATTACHMENTS --> ENTITIES
ASK --> UTILS
FIRE --> UTILS
PAY --> UTILS
VACATION --> UTILS
SECTIONS --> UTILS
HIRE --> UTILS
UTILS --> QA_SERVICE
UTILS --> STATES
UTILS --> ENTITIES
UTILS --> REQUIRE_ENTITY
UTILS --> CATCH_ERROR
UTILS --> ENTITY_NOT_FOUND
KEYBOARDS --> FIRE_MENU
KEYBOARDS --> ENTITY_SELECT
FIRE_MENU --> DOC_ATTACHMENT
ENTITY_SELECT --> DOC_ATTACHMENT
RESOURCES --> SCRIPT
RESOURCES --> QA_SERVICE
QA_SERVICE --> CHAIN
BOT --> CONFIG
TESTS --> BOT
TESTS --> QA_SERVICE
TESTS --> UTILS
TESTS --> ENTITIES
TESTS --> FIRE
TESTS --> ATTACHMENTS
```

**Diagram sources**
- [bot.py:45-58](file://app/integrations/vk/bot.py#L45-L58)
- [ask.py:22-28](file://app/integrations/vk/handlers/ask.py#L22-L28)
- [hire.py:19-34](file://app/integrations/vk/handlers/hire.py#L19-L34)
- [fire.py:11](file://app/integrations/vk/handlers/fire.py#L11)
- [pay.py:1-46](file://app/integrations/vk/handlers/pay.py#L1-L46)
- [vacation.py:1-105](file://app/integrations/vk/handlers/vacation.py#L1-L105)
- [sections.py:1-35](file://app/integrations/vk/handlers/sections.py#L1-L35)
- [handlers/__init__.py:13-39](file://app/integrations/vk/handlers/__init__.py#L13-L39)
- [entities.py:16-21](file://app/domain/entities.py#L16-L21)
- [resources.py:32-49](file://app/resources.py#L32-L49)
- [qa_service.py:1-120](file://app/domain/qa_service.py#L1-L120)
- [chain.py:1-80](file://app/rag/chain.py#L1-L80)
- [polling_vk.py:17-31](file://scripts/polling_vk.py#L17-L31)
- [config.py:1-9](file://app/config.py#L1-L9)
- [attachments.py:19-121](file://app/integrations/vk/attachments.py#L19-L121)
- [test_bot_factory.py:54-67](file://tests/test_bot_factory.py#L54-L67)

**Section sources**
- [bot.py:1-59](file://app/integrations/vk/bot.py#L1-L59)
- [polling_vk.py:1-36](file://scripts/polling_vk.py#L1-L36)
- [config.py:1-9](file://app/config.py#L1-L9)

## Core Components
- Bot factory: Creates a vkbottle Bot with shared state dispenser, loads handler labelers in strict order, and integrates the QA service for RAG processing
- Centralized state management: Uses BuiltinStateDispenser singleton pattern shared between bot and handlers for consistent state persistence
- Handlers: Define message routes for start, main menu navigation, section entry points, dedicated ask-a-question functionality, and multi-step HR request workflows
- Centralized QA utilities: Provide unified access patterns for QA service initialization, retrieval, and error handling across all handlers
- QA Service: Provides centralized RAG processing with proper resource management, error handling, and VK message length truncation
- Enhanced fire handler: Implements entity-based resignation flow with document template attachment and improved error handling using decorators
- Document attachment system: Provides helper functions for sending S3-stored documents as VK message attachments
- Keyboard builders: Provide consistent UI and payload constants for navigation, including new entity selection flows
- States: Define multi-step dialog states for complex HR workflows using centralized state dispenser
- Legal entities: Manage company information with updated names and centralized entity lookup
- Local runner: Initializes Settings and starts the bot in Long Poll mode with proper resource management
- Resource management: Handles graceful initialization and cleanup of RAG resources and enhanced service components
- **New** Enhanced error handling system: Provides consistent entity validation and error handling across all handlers using require_entity functions and @catch_entity_error decorators

Key implementation references:
- Factory and handler loading order with centralized state sharing: [bot.py:49-52](file://app/integrations/vk/bot.py#L49-L52)
- Centralized state dispenser sharing pattern: [bot.py:50-52](file://app/integrations/vk/bot.py#L50-L52), [handlers/__init__.py:32-39](file://app/integrations/vk/handlers/__init__.py#L32-L39)
- Centralized QA service access patterns: [handlers/__init__.py:22-29](file://app/integrations/vk/handlers/__init__.py#L22-L29)
- Enhanced fire handler with entity-based flow: [fire.py:40-67](file://app/integrations/vk/handlers/fire.py#L40-L67)
- Document attachment helper: [attachments.py:19-121](file://app/integrations/vk/attachments.py#L19-L121)
- Enhanced keyboard system with entity selection: [keyboards.py:42-44](file://app/integrations/vk/keyboards.py#L42-L44)
- QA service initialization and RAG processing: [qa_service.py:51-105](file://app/domain/qa_service.py#L51-L105)
- Ask-a-question handler with RAG integration: [ask.py:40-45](file://app/integrations/vk/handlers/ask.py#L40-L45)
- HR request multi-step dialog with centralized state: [hire.py:69-74](file://app/integrations/vk/handlers/hire.py#L69-L74)
- Enhanced RAG-enabled HR handlers with centralized access: [fire.py:63-65](file://app/integrations/vk/handlers/fire.py#L63-L65), [pay.py:36-46](file://app/integrations/vk/handlers/pay.py#L36-L46), [vacation.py:67-80](file://app/integrations/vk/handlers/vacation.py#L67-L80)
- Keyboard builders and payloads: [keyboards.py:13-108](file://app/integrations/vk/keyboards.py#L13-L108)
- Dialog states: [states.py:4-17](file://app/integrations/vk/states.py#L4-L17)
- Updated legal entities with new company names: [entities.py:16-21](file://app/domain/entities.py#L16-L21)
- Local runner with resource management: [polling_vk.py:17-31](file://scripts/polling_vk.py#L17-L31)
- Settings: [config.py:4-9](file://app/config.py#L4-L9)
- Resource management: [resources.py:51-165](file://app/resources.py#L51-L165)
- **New** Enhanced error handling system: [handlers/__init__.py:98-141](file://app/integrations/vk/handlers/__init__.py#L98-L141)

**Section sources**
- [bot.py:24-59](file://app/integrations/vk/bot.py#L24-L59)
- [handlers/__init__.py:13-171](file://app/integrations/vk/handlers/__init__.py#L13-L171)
- [qa_service.py:1-120](file://app/domain/qa_service.py#L1-L120)
- [ask.py:1-90](file://app/integrations/vk/handlers/ask.py#L1-L90)
- [hire.py:1-119](file://app/integrations/vk/handlers/hire.py#L1-L119)
- [fire.py:1-76](file://app/integrations/vk/handlers/fire.py#L1-L76)
- [pay.py:1-46](file://app/integrations/vk/handlers/pay.py#L1-L46)
- [vacation.py:1-134](file://app/integrations/vk/handlers/vacation.py#L1-L134)
- [sections.py:1-35](file://app/integrations/vk/handlers/sections.py#L1-L35)
- [keyboards.py:13-108](file://app/integrations/vk/keyboards.py#L13-L108)
- [states.py:4-17](file://app/integrations/vk/states.py#L4-L17)
- [entities.py:1-24](file://app/domain/entities.py#L1-L24)
- [polling_vk.py:17-31](file://scripts/polling_vk.py#L17-L31)
- [config.py:4-9](file://app/config.py#L4-L9)
- [resources.py:51-165](file://app/resources.py#L51-L165)
- [attachments.py:1-121](file://app/integrations/vk/attachments.py#L1-121)

## Architecture Overview
The VK bot follows a modular architecture with integrated RAG capabilities and centralized service management:
- The factory constructs a Bot with shared state dispenser and registers labelers in a fixed order to ensure deterministic routing
- Handlers react to text commands and payload events, leveraging centralized state dispenser for persistent user context and centralized QA service access patterns for intelligent content generation
- The centralized utilities module provides consistent error handling and resource management across all handlers
- Payload constants drive navigation across screens, ensuring consistent UX
- Optional state groups enable multi-step dialogs with sophisticated HR workflows
- Enhanced fire handler implements entity-based resignation flow with document template attachment and improved error handling
- Resource management handles graceful initialization and cleanup of RAG components and enhanced service components
- **New** Enhanced error handling system provides consistent entity validation and error handling across all handlers using require_entity functions and @catch_entity_error decorators

```mermaid
sequenceDiagram
participant Dev as "Developer"
participant Script as "polling_vk.py"
participant Resources as "resources.build_resources()"
participant Factory as "bot.create_bot()"
participant Bot as "vkbottle.Bot"
participant SD as "BuiltinStateDispenser"
participant Labelers as "Handler Labelers"
participant Utils as "handlers/__init__.py"
participant QA as "QA Service"
participant Attachments as "attachments.send_category_document()"
participant Entities as "Legal Entities"
participant VK as "VK API"
Dev->>Script : Run long poll
Script->>Resources : build_resources(Settings)
Resources-->>Script : AppResources
Script->>Factory : create_bot(resources.settings)
Factory->>Bot : Initialize with token
Factory->>SD : Create BuiltinStateDispenser
Factory->>Bot : Set bot.state_dispenser = SD
Factory->>Utils : set_state_dispenser(SD)
Factory->>Utils : set_qa_service(resources.qa_service)
Factory->>Labelers : Load handlers (start, hire, fire, vacation, pay, sections, ask, fallback)
Script->>Utils : set_qa_service(resources.qa_service)
Utils->>QA : Initialize RAG chain
Utils->>Entities : Load legal entities
Labelers->>Utils : get_state_dispenser()
Utils-->>Labelers : Shared BuiltinStateDispenser
Labelers->>Utils : get_qa_service().ask()
Utils->>QA : Query RAG for HR-related questions
Labelers->>Attachments : send_category_document()
Attachments->>Entities : Get entity by ID
Entities-->>Attachments : Legal entity info
Attachments-->>Labelers : Document attachment or fallback
Script->>Bot : run_forever()
Bot->>VK : Poll for updates
VK-->>Bot : Incoming message
Bot->>Labelers : Match handler (top to bottom)
Labelers-->>Bot : Respond with text and keyboard
Bot-->>VK : Send response
```

**Diagram sources**
- [polling_vk.py:17-31](file://scripts/polling_vk.py#L17-L31)
- [resources.py:51-165](file://app/resources.py#L51-L165)
- [bot.py:49-52](file://app/integrations/vk/bot.py#L49-L52)
- [handlers/__init__.py:32-39](file://app/integrations/vk/handlers/__init__.py#L32-L39)
- [handlers/__init__.py:22-29](file://app/integrations/vk/handlers/__init__.py#L22-L29)
- [qa_service.py:51-105](file://app/domain/qa_service.py#L51-L105)
- [attachments.py:19-121](file://app/integrations/vk/attachments.py#L19-L121)
- [entities.py:16-21](file://app/domain/entities.py#L16-L21)

## Centralized State Management

### Centralized State Dispenser Sharing
The new centralized state management system ensures consistent state persistence across all handlers through a shared BuiltinStateDispenser instance:

```mermaid
classDiagram
class BuiltinStateDispenser {
+set(peer_id, state, **payload) None
+get(peer_id) StateContext | None
+delete(peer_id) None
}
class VKHandlersUtils {
- holder : Holder
+ set_state_dispenser(sd) None
+ get_state_dispenser() BuiltinStateDispenser
+ set_qa_service(service) None
+ get_qa_service() QAService
}
class Holder {
+ qa : QAService | None
+ state_dispenser : BuiltinStateDispenser | None
}
class BotFactory {
+ create_bot(settings) Bot
}
class HireHandlers {
+ on_hire(message) None
+ on_hire_entity(message) None
+ on_hire_checklist(message) None
+ on_hire_contract(message) None
+ on_hire_onboarding(message) None
}
class FireHandlers {
+ on_fire(message) None
+ on_fire_resignation(message) None
+ on_fire_resignation_entity(message) None
+ on_fire_grounds(message) None
}
class VacationHandlers {
+ on_vacation(message) None
+ on_vacation_select(message) None
+ on_vacation_type(message) None
}
class AskHandlers {
+ on_ask(message) None
+ on_ask_text(message) None
}
BotFactory --> BuiltinStateDispenser : creates and shares
BotFactory --> VKHandlersUtils : set_state_dispenser()
VKHandlersUtils --> Holder : manages
Holder --> BuiltinStateDispenser : stores
HireHandlers --> VKHandlersUtils : get_state_dispenser()
FireHandlers --> VKHandlersUtils : get_state_dispenser()
VacationHandlers --> VKHandlersUtils : get_state_dispenser()
AskHandlers --> VKHandlersUtils : get_state_dispenser()
```

**Diagram sources**
- [bot.py:50-52](file://app/integrations/vk/bot.py#L50-L52)
- [handlers/__init__.py:13-63](file://app/integrations/vk/handlers/__init__.py#L13-L63)
- [hire.py:56-60](file://app/integrations/vk/handlers/hire.py#L56-L60)
- [fire.py:40-67](file://app/integrations/vk/handlers/fire.py#L40-L67)
- [vacation.py:50-86](file://app/integrations/vk/handlers/vacation.py#L50-L86)
- [ask.py:40](file://app/integrations/vk/handlers/ask.py#L40)

### Centralized State Access Patterns
All handlers now use centralized state dispenser access patterns for consistent state management:

**Updated** All handlers (hire, fire, vacation, ask, sections) now use the centralized state dispenser through get_state_dispenser() calls, replacing direct imports with consistent shared state access patterns. The enhanced fire workflow utilizes state management for the two-step resignation process and entity selection flow.

**Section sources**
- [bot.py:49-52](file://app/integrations/vk/bot.py#L49-L52)
- [handlers/__init__.py:32-39](file://app/integrations/vk/handlers/__init__.py#L32-L39)
- [hire.py:56-60](file://app/integrations/vk/handlers/hire.py#L56-L60)
- [fire.py:40-67](file://app/integrations/vk/handlers/fire.py#L40-L67)
- [vacation.py:50-86](file://app/integrations/vk/handlers/vacation.py#L50-L86)
- [ask.py:40](file://app/integrations/vk/handlers/ask.py#L40)

## Centralized QA Service Access Layer

### Centralized Utilities Module
The new centralized utilities module provides a consistent interface for QA service access, state dispenser management, and enhanced service integration across all VK handlers:

```mermaid
classDiagram
class VKHandlersUtils {
- holder : Holder
+ set_qa_service(service) None
+ get_qa_service() QAService
+ set_state_dispenser(sd) None
+ get_state_dispenser() BuiltinStateDispenser
+ send_rag_answer(message, question, back_payload) None
+ get_entity_or_error(message, entity_id, back_payload) Entity | None
+ require_entity(message, entity_id, back_payload) Entity
+ catch_entity_error(handler) decorator
+ EntityNotFoundError exception
}
class Holder {
+ qa : QAService | None
+ state_dispenser : BuiltinStateDispenser | None
}
class QAService {
+ask(question) str
+close_qa() None
+_truncate(text) str
}
class ErrorHandler {
+ERR_NO_ANSWER : str
+ERR_DOCUMENT_UNAVAILABLE : str
+VK_MSG_LIMIT : int
}
class LegalEntities {
+ENTITIES : tuple[LegalEntity, ...]
+ENTITY_BY_ID : dict[int, LegalEntity]
}
VKHandlersUtils --> Holder : manages
VKHandlersUtils --> QAService : uses
VKHandlersUtils --> BuiltinStateDispenser : uses
VKHandlersUtils --> LegalEntities : uses
```

**Diagram sources**
- [handlers/__init__.py:13-63](file://app/integrations/vk/handlers/__init__.py#L13-L63)
- [qa_service.py:23-105](file://app/domain/qa_service.py#L23-L105)
- [entities.py:16-24](file://app/domain/entities.py#L16-L24)

### Centralized Access Patterns
All HR-related handlers now use centralized service access patterns for consistent error handling and resource management:

**Updated** All HR-related handlers (hire, fire, pay, vacation, sections) now use the centralized utilities module for QA service access and state dispenser management, replacing direct imports with consistent get_*_service() calls and improved error handling patterns. The enhanced fire handler integrates with the centralized utilities for entity validation and document template delivery.

**Section sources**
- [handlers/__init__.py:22-29](file://app/integrations/vk/handlers/__init__.py#L22-L29)
- [handlers/__init__.py:32-39](file://app/integrations/vk/handlers/__init__.py#L32-L39)
- [hire.py:63-65](file://app/integrations/vk/handlers/hire.py#L63-L65)
- [fire.py:63-65](file://app/integrations/vk/handlers/fire.py#L63-L65)
- [pay.py:36-46](file://app/integrations/vk/handlers/pay.py#L36-L46)
- [vacation.py:67-80](file://app/integrations/vk/handlers/vacation.py#L67-L80)
- [sections.py:25-45](file://app/integrations/vk/handlers/sections.py#L25-L45)
- [entities.py:16-24](file://app/domain/entities.py#L16-L24)

## Enhanced RAG Response Handling

### Intelligent Timeout Handling
The new `query_rag_with_wait()` function implements sophisticated timeout handling to improve user experience during slow RAG responses:

```mermaid
sequenceDiagram
participant User as "User"
participant Handler as "Handler"
participant Utils as "query_rag_with_wait()"
participant QA as "QA Service"
participant Task as "Async Task"
User->>Handler : Ask question
Handler->>Utils : query_rag_with_wait(message, question, timeout=3.0)
Utils->>Task : Create async task for QA.ask()
Utils->>Task : Create delay task (3 seconds)
Utils->>Task : Wait for first completion
alt RAG completes within 3 seconds
Task-->>Utils : RAG result
Utils-->>Handler : Return answer immediately
Handler-->>User : Display answer
else RAG takes longer than 3 seconds
Task-->>Utils : Delay task completes first
Utils->>User : Send "please wait" message
Utils->>Task : Wait for RAG completion
Task-->>Utils : RAG result
Utils-->>Handler : Return answer
Handler-->>User : Display answer
end
```

**Diagram sources**
- [handlers/__init__.py:46-68](file://app/integrations/vk/handlers/__init__.py#L46-L68)

### Automatic Question Context Prepending
The enhanced `send_rag_answer()` function automatically prepends user question context to all answers for better clarity and traceability:

```mermaid
flowchart TD
Start(["send_rag_answer(message, question, back_payload)"]) --> Typing["Set typing indicator"]
Typing --> Wait["Call query_rag_with_wait()"]
Wait --> CheckTimeout{"RAG completed within 3s?"}
CheckTimeout --> |Yes| Answer["Get answer from RAG"]
CheckTimeout --> |No| WaitMsg["Send 'please wait' message"]
WaitMsg --> Answer
Answer --> Prepend["Prepend question context"]
Prepend --> Truncate["Truncate to VK limits"]
Truncate --> Keyboard["Add back keyboard"]
Keyboard --> Send["Send final answer"]
Send --> End(["Complete"])
```

**Diagram sources**
- [handlers/__init__.py:70-86](file://app/integrations/vk/handlers/__init__.py#L70-L86)

### Key Features of Enhanced RAG Handling
- **Intelligent Timeout Detection**: Automatically detects slow RAG responses and sends "please wait" notifications
- **User Experience Enhancement**: Prevents user frustration with unresponsive bots during slow RAG processing
- **Automatic Context Preservation**: Ensures user questions remain visible in the conversation history
- **Consistent Formatting**: Maintains standardized answer presentation across all handlers
- **Graceful Degradation**: Continues processing even when RAG responses are delayed

**Updated** The new timeout handling system provides a seamless user experience by automatically managing slow RAG responses, while the automatic question context prepending ensures users always have clear reference to their original questions. All RAG-enabled handlers now use the enhanced `send_rag_answer()` function for consistent user experience.

**Section sources**
- [handlers/__init__.py:46-86](file://app/integrations/vk/handlers/__init__.py#L46-L86)
- [ask.py:75-90](file://app/integrations/vk/handlers/ask.py#L75-L90)
- [test_ask_block9.py:94-112](file://tests/test_ask_block9.py#L94-L112)

## Document Template Management System

### Enhanced Fire Handler with Document Attachment
The fire handler now integrates with the document attachment system to provide company-specific resignation templates:

```mermaid
classDiagram
class FireHandler {
+on_fire(message) None
+on_fire_resignation(message) None
+on_fire_resignation_entity(message) None
+on_fire_grounds(message) None
}
class DocumentAttachmentHelper {
+send_category_document(message, service, category, subcategory, entity_id, caption) bool
}
class CategoryFileService {
+get_file(category, subcategory, entity_id) CategoryFileRecord | None
+download_file(file_id) tuple[bytes, str]
}
class VKDocumentAPI {
+get_messages_upload_server(peer_id, type) dict
+save(file, title) dict
}
class LegalEntities {
+ENTITY_BY_ID : dict[int, LegalEntity]
}
FireHandler --> DocumentAttachmentHelper : uses
DocumentAttachmentHelper --> CategoryFileService : queries
DocumentAttachmentHelper --> VKDocumentAPI : uploads
DocumentAttachmentHelper --> LegalEntities : validates
```

**Diagram sources**
- [fire.py:40-67](file://app/integrations/vk/handlers/fire.py#L40-L67)
- [attachments.py:19-121](file://app/integrations/vk/attachments.py#L19-L121)
- [entities.py:16-24](file://app/domain/entities.py#L16-L24)

### Document Attachment Process
The document attachment system provides seamless template delivery with fallback capabilities:

```mermaid
flowchart TD
Start(["on_fire_resignation_entity(message)"]) --> Validate["Validate entity selection"]
Validate --> EntityOK{"Entity valid?"}
EntityOK --> |No| Error["Send error message"]
EntityOK --> |Yes| Caption["Build template caption"]
Caption --> SendDoc["send_category_document()"]
SendDoc --> Found{"Template found?"}
Found --> |Yes| Upload["Upload to VK docs"]
Upload --> Success["Send document attachment"]
Found --> |No| Fallback["send_rag_answer() fallback"]
Success --> End(["Complete"])
Error --> End
Fallback --> End
```

**Diagram sources**
- [fire.py:48-67](file://app/integrations/vk/handlers/fire.py#L48-L67)
- [attachments.py:19-121](file://app/integrations/vk/attachments.py#L19-L121)

### Key Features of Enhanced Document Management
- **Entity-Specific Templates**: Company-specific resignation templates delivered based on legal entity selection
- **Document Attachment Delivery**: Direct document attachment to VK messages with proper MIME type handling
- **Fallback Mechanism**: Automatic fallback to RAG-generated content when templates are unavailable
- **Error Handling**: Comprehensive error handling for S3 connectivity, VK API failures, and template validation
- **Template Validation**: Ensures templates exist before attempting delivery
- **Upload Server Integration**: Proper VK API integration for document upload and saving

**Updated** The enhanced fire handler now provides company-specific resignation templates through the document attachment system, with automatic fallback to RAG responses when templates are unavailable. This demonstrates the system's commitment to providing accurate, company-specific HR documentation.

**Section sources**
- [fire.py:1-76](file://app/integrations/vk/handlers/fire.py#L1-L76)
- [attachments.py:1-121](file://app/integrations/vk/attachments.py#L1-L121)
- [entities.py:1-24](file://app/domain/entities.py#L1-L24)

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
Detect --> Utils["Centralized QA Access"]
Utils --> QAService["QA Service.ask()"]
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
All HR-related handlers now leverage the centralized QA service for intelligent content delivery:

**Updated** All HR-related handlers (hire, fire, pay, vacation, sections) now use the centralized utilities module for consistent QA service access and state dispenser management, providing improved error handling and resource management across all handlers. The enhanced fire handler integrates with both QA service and document attachment systems for comprehensive HR support.

**Section sources**
- [handlers/__init__.py:22-29](file://app/integrations/vk/handlers/__init__.py#L22-L29)
- [qa_service.py:1-120](file://app/domain/qa_service.py#L1-L120)
- [chain.py:1-80](file://app/rag/chain.py#L1-L80)
- [hire.py:63-65](file://app/integrations/vk/handlers/hire.py#L63-L65)
- [fire.py:63-65](file://app/integrations/vk/handlers/fire.py#L63-L65)
- [pay.py:36-46](file://app/integrations/vk/handlers/pay.py#L36-L46)
- [vacation.py:67-80](file://app/integrations/vk/handlers/vacation.py#L67-L80)
- [sections.py:25-45](file://app/integrations/vk/handlers/sections.py#L25-L45)

## Enhanced Fire Handler with Entity-Based Resignation Flow

### New Entity-Based Resignation Workflow
The fire handler has been significantly enhanced with a two-step entity-based resignation flow:

```mermaid
flowchart TD
Start(["CMD_FIRE"]) --> FireMenu["Display fire menu"]
FireMenu --> Resignation["User selects resignation"]
Resignation --> EntitySelect["Display entity selection keyboard"]
EntitySelect --> EntityChoice["User selects legal entity"]
EntityChoice --> Validate["Validate entity selection"]
Validate --> Valid{"Entity valid?"}
Valid --> |No| Error["Send error message"]
Valid --> |Yes| Caption["Build resignation caption"]
Caption --> Template["Attempt document template delivery"]
Template --> Found{"Template found?"}
Found --> |Yes| Upload["Upload to VK docs"]
Upload --> Success["Send document attachment"]
Found --> |No| Fallback["Fallback to RAG answer"]
Success --> End(["Complete"])
Error --> End
Fallback --> End
```

**Diagram sources**
- [fire.py:29-67](file://app/integrations/vk/handlers/fire.py#L29-L67)
- [keyboards.py:179-185](file://app/integrations/vk/keyboards.py#L179-L185)
- [keyboards.py:129-152](file://app/integrations/vk/keyboards.py#L129-L152)

### Enhanced Keyboard System for Fire Flow
The keyboard system now includes specialized keyboards for the fire resignation flow:

```mermaid
classDiagram
class FireMenuKeyboard {
+fire_menu_kb() Keyboard
+builds : "🚪 Увольнение по собственному" + "📖 Основания увольнения"
}
class EntitySelectionKeyboard {
+entity_select_kb(cmd, back_payload, extra_payload) Keyboard
+builds : 4 legal entity buttons + service row
}
class PayloadConstants {
+CMD_FIRE_RESIGNATION : dict
+CMD_FIRE_GROUNDS : dict
+FIRE_RESIGNATION_ENTITY_CMD : str
}
FireMenuKeyboard --> PayloadConstants : uses
EntitySelectionKeyboard --> PayloadConstants : uses
```

**Diagram sources**
- [keyboards.py:179-185](file://app/integrations/vk/keyboards.py#L179-L185)
- [keyboards.py:129-152](file://app/integrations/vk/keyboards.py#L129-L152)
- [keyboards.py:42-44](file://app/integrations/vk/keyboards.py#L42-L44)

### Key Features of Enhanced Fire Handler
- **Entity-Based Resignation**: Users can select their legal entity for company-specific resignation templates
- **Two-Step Flow**: Clear separation between fire menu selection and entity selection
- **Document Template Integration**: Direct template delivery through document attachment system
- **Fallback Mechanisms**: Automatic fallback to RAG responses when templates are unavailable
- **Entity Validation**: Proper validation of entity selection with error handling
- **Company-Specific Content**: Templates tailored to individual legal entities

**Updated** The fire handler now provides a comprehensive entity-based resignation flow with document template delivery, representing a significant enhancement to the HR workflow capabilities. The system maintains backward compatibility while adding sophisticated company-specific template support.

**Section sources**
- [fire.py:1-76](file://app/integrations/vk/handlers/fire.py#L1-L76)
- [keyboards.py:179-185](file://app/integrations/vk/keyboards.py#L179-L185)
- [keyboards.py:129-152](file://app/integrations/vk/keyboards.py#L129-L152)
- [keyboards.py:42-44](file://app/integrations/vk/keyboards.py#L42-L44)

## Enhanced Error Handling with Decorators

### New Error Handling System
The system now features enhanced error handling consistency using require_entity functions and @catch_entity_error decorators:

```mermaid
classDiagram
class EntityNotFoundError {
+message : str
+raised by require_entity when entity lookup fails
+sends error message to user before raising
}
class CatchEntityErrorDecorator {
+catch_entity_error(handler) decorator
+silently returns if handler raises EntityNotFoundError
+prevents error propagation to user
}
class RequireEntityFunction {
+require_entity(message, entity_id, back_payload) Entity
+look up entity by ID
+raise EntityNotFoundError if not found
+send error message to user before raising
}
class GetEntityOrErrorFunction {
+get_entity_or_error(message, entity_id, back_payload) Entity | None
+look up entity by ID
+return None if not found
+send error message to user and return None
}
class ErrorHandlerPattern {
+Old Pattern : get_entity_or_error + manual None checks
+New Pattern : require_entity + @catch_entity_error decorator
+Consistent error handling across all handlers
}
EntityNotFoundError <|-- ErrorHandlerPattern
CatchEntityErrorDecorator --> ErrorHandlerPattern : implements
RequireEntityFunction --> ErrorHandlerPattern : implements
GetEntityOrErrorFunction --> ErrorHandlerPattern : legacy pattern
```

**Diagram sources**
- [handlers/__init__.py:98-141](file://app/integrations/vk/handlers/__init__.py#L98-L141)
- [fire.py:53-57](file://app/integrations/vk/handlers/fire.py#L53-L57)
- [hire.py:51-59](file://app/integrations/vk/handlers/hire.py#L51-L59)

### Error Handling Patterns in Handlers
The new error handling system provides consistent patterns across all HR-related handlers:

**Updated** The fire handler now uses `@catch_entity_error` decorator combined with `require_entity` function for improved error handling. The hire handler also uses the same pattern for entity validation. The vacation handler maintains backward compatibility with the `get_entity_or_error` pattern for continued support.

**Section sources**
- [handlers/__init__.py:98-141](file://app/integrations/vk/handlers/__init__.py#L98-L141)
- [fire.py:53-57](file://app/integrations/vk/handlers/fire.py#L53-L57)
- [hire.py:51-59](file://app/integrations/vk/handlers/hire.py#L51-L59)
- [vacation.py:79-86](file://app/integrations/vk/handlers/vacation.py#L79-L86)

## Detailed Component Analysis

### Bot Factory Pattern and Handler Registration
- The factory initializes a Bot with the VK access token from Settings and establishes shared state management through BuiltinStateDispenser
- It creates a BuiltinStateDispenser instance and assigns it to both the bot and the centralized utilities module
- It loads 27 labelers in a specific order: start, ask, hire, fire, vacation, pay, sections, fallback
- The order is crucial because vkbottle evaluates handlers top-to-bottom; fallback must be last to avoid intercepting intended matches
- The QA service is initialized during bot creation and registered with the centralized utilities module for consistent access patterns
- Enhanced fire handler is now included in the handler registration process with improved error handling patterns

**Updated** The factory now registers 27 total handlers across all VK integration modules, with the enhanced fire handler providing comprehensive entity-based resignation flow and improved error handling using decorators. The handler registration order ensures proper routing precedence with fallback as the last handler.

```mermaid
flowchart TD
Start(["create_bot(settings)"]) --> Init["Initialize Bot with token"]
Init --> ShareState["Create BuiltinStateDispenser"]
ShareState --> AssignSD["Assign to bot.state_dispenser"]
AssignSD --> RegisterSD["Register with centralized utils"]
RegisterSD --> LoadHandlers["Load 27 labelers in order"]
LoadHandlers --> RegisterServices["Register QA service"]
RegisterServices --> Log["Log handler count"]
Log --> ReturnBot(["Return Bot"])
```

**Diagram sources**
- [bot.py:45-58](file://app/integrations/vk/bot.py#L45-L58)

**Section sources**
- [bot.py:24-59](file://app/integrations/vk/bot.py#L24-L59)
- [test_bot_factory.py:54-67](file://tests/test_bot_factory.py#L54-L67)

### Message Routing and Navigation with Payloads
- Start handler responds to initial commands and sends the main menu with service buttons
- Payload constants define navigation actions (Home, Back, Contact HR, Section commands)
- Section handlers reply with RAG-generated content and a service row keyboard
- Ask handler provides dedicated question-answering with state management using centralized state dispenser
- Fallback handler ensures users stay within the menu-driven interface
- HR request handlers manage complex multi-step workflows with state persistence through centralized state dispenser
- Enhanced fire workflow provides two-step entity selection process for resignation flow
- Document attachment system delivers company-specific templates based on entity selection
- QA service integration provides fallback content when templates are unavailable
- **New** Enhanced error handling system provides consistent entity validation across all handlers using require_entity functions and @catch_entity_error decorators

```mermaid
sequenceDiagram
participant User as "User"
participant Bot as "vkbottle.Bot"
participant Start as "start.on_start/on_home"
participant Ask as "ask.on_ask/on_ask_text"
participant Hire as "hire.on_hire/on_hire_entity"
participant Fire as "fire.on_fire/on_fire_resignation_entity"
participant Vacation as "vacation.on_vacation/on_vacation_type"
participant Pay as "pay.on_pay/on_pay_overtime"
participant Sections as "sections.on_sick/on_probation"
participant Utils as "handlers/__init__.py"
participant SD as "BuiltinStateDispenser"
participant Attachments as "attachments.send_category_document()"
participant Fallback as "fallback.on_fallback"
User->>Bot : "/start" or "Start" or "Начать"
Bot->>Start : Match text route
Start->>SD : _clear_state(peer_id)
SD-->>Start : State cleared
Start-->>User : Greeting + main menu keyboard
User->>Bot : Payload "cmd_fire"
Bot->>Fire : Match payload route
Fire->>SD : get_state_dispenser().set()
SD-->>Fire : State set
Fire->>Utils : require_entity()
Utils-->>Fire : Entity validation
Fire->>Attachments : send_category_document()
Attachments-->>Fire : Template delivery or fallback
Fire-->>User : Resignation template or RAG answer
User->>Bot : Arbitrary text
Bot->>Fallback : Match default handler
Fallback-->>User : Prompt to use menu
```

**Diagram sources**
- [start.py:34-49](file://app/integrations/vk/handlers/start.py#L34-L49)
- [ask.py:40](file://app/integrations/vk/handlers/ask.py#L40)
- [hire.py:69](file://app/integrations/vk/handlers/hire.py#L69)
- [fire.py:40-67](file://app/integrations/vk/handlers/fire.py#L40-L67)
- [vacation.py:50-116](file://app/integrations/vk/handlers/vacation.py#L50-L116)
- [pay.py:36-46](file://app/integrations/vk/handlers/pay.py#L36-L46)
- [sections.py:25-45](file://app/integrations/vk/handlers/sections.py#L25-L45)
- [handlers/__init__.py:32-39](file://app/integrations/vk/handlers/__init__.py#L32-L39)
- [attachments.py:19-121](file://app/integrations/vk/attachments.py#L19-L121)
- [fallback.py:15-17](file://app/integrations/vk/handlers/fallback.py#L15-L17)

**Section sources**
- [start.py:14-50](file://app/integrations/vk/handlers/start.py#L14-L50)
- [ask.py:1-90](file://app/integrations/vk/handlers/ask.py#L1-L90)
- [hire.py:1-119](file://app/integrations/vk/handlers/hire.py#L1-L119)
- [fire.py:1-76](file://app/integrations/vk/handlers/fire.py#L1-L76)
- [vacation.py:1-134](file://app/integrations/vk/handlers/vacation.py#L1-L134)
- [pay.py:1-46](file://app/integrations/vk/handlers/pay.py#L1-L46)
- [sections.py:1-35](file://app/integrations/vk/handlers/sections.py#L1-L35)
- [handlers/__init__.py:13-171](file://app/integrations/vk/handlers/__init__.py#L13-L171)
- [fallback.py:9-18](file://app/integrations/vk/handlers/fallback.py#L9-L18)
- [keyboards.py:13-108](file://app/integrations/vk/keyboards.py#L13-L108)

### Keyboard Builders and Payload Constants
- Payload constants define navigation semantics (home, back, contact HR, section commands)
- Keyboard builders assemble rows and append a standard service row with Back/Home/Contact HR
- The main menu keyboard organizes seven sections plus a dedicated "Contact HR" button
- Specialized keyboards support multi-step dialog flows and RAG-powered content presentation
- Enhanced fire workflow keyboards support two-step entity selection process
- Document attachment system enables dynamic template loading based on entity selection
- Entity selection keyboards provide company-specific template delivery

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
+CMD_FIRE_RESIGNATION
+CMD_FIRE_GROUNDS
+CMD_HR_* (multi-step states)
+CMD_VACATION_* (enhanced workflow)
+CMD_HIRE_* (multi-step states)
+FIRE_RESIGNATION_ENTITY_CMD
}
class KeyboardBuilders {
+with_service_row(kb, back_payload, show_home, show_hr) Keyboard
+main_menu_kb() Keyboard
+ask_input_kb() Keyboard
+ask_result_kb(scenario_id) Keyboard
+hiring_*_kb() Hiring keyboards
+fire_menu_kb() Enhanced fire menu
+entity_select_kb(cmd, back_payload, extra_payload) Entity selection
+vacation_*_kb() Various vacation keyboards
+hr_*_kb() Various HR keyboards
+stub_kb(back_payload) Keyboard
}
Payloads <.. KeyboardBuilders : "used by"
```

**Diagram sources**
- [keyboards.py:13-108](file://app/integrations/vk/keyboards.py#L13-L108)
- [keyboards.py:42-44](file://app/integrations/vk/keyboards.py#L42-L44)

**Section sources**
- [keyboards.py:13-108](file://app/integrations/vk/keyboards.py#L13-L108)
- [test_keyboards.py:49-92](file://tests/test_keyboards.py#L49-L92)
- [test_keyboards.py:97-150](file://tests/test_keyboards.py#L97-L150)
- [test_keyboards.py:155-171](file://tests/test_keyboards.py#L155-L171)
- [test_keyboards.py:176-192](file://tests/test_keyboards.py#L176-L192)

### Dialog States for Multi-Step Flows
- States are defined as a typed group to support multi-step dialogs (e.g., HR request wizard)
- The ask-a-question flow uses dedicated state management to handle free-text input
- The enhanced fire workflow uses state management for the two-step resignation process and entity selection
- Tests confirm the state group inherits from the base type and contains expected state names/values
- All state operations now use the centralized BuiltinStateDispenser for consistency

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
+VACATION_TYPE_SELECTION
+VACATION_ENTITY_SELECTION
+VACATION_TEMPLATE_GENERATION
+HIRE_ENTITY_SELECTION
+HIRE_ACTION_SELECTION
+FIRE_RESIGNATION_ENTITY_SELECTION
}
class BuiltinStateDispenser {
+set(peer_id, state, **payload) None
+get(peer_id) StateContext | None
+delete(peer_id) None
}
BotStates --> BuiltinStateDispenser : uses
```

**Diagram sources**
- [states.py:4-17](file://app/integrations/vk/states.py#L4-L17)

**Section sources**
- [states.py:4-17](file://app/integrations/vk/states.py#L4-L17)
- [test_states.py:8-31](file://tests/test_states.py#L8-L31)

### Bot Initialization and Long Poll Runner
- The local runner loads Settings, creates the Bot via the factory, and starts Long Polling
- The factory initializes the QA service during bot creation and registers it with centralized utilities for immediate RAG capabilities
- Resource management handles graceful initialization and cleanup of RAG components
- Logging is configured for development visibility with RAG processing metrics

```mermaid
sequenceDiagram
participant CLI as "CLI"
participant Runner as "polling_vk.main()"
participant Resources as "resources.build_resources()"
participant Factory as "bot.create_bot()"
participant Bot as "vkbottle.Bot"
participant Utils as "handlers/__init__.py"
participant QA as "QA Service"
participant Entities as "Legal Entities"
participant Attachments as "attachments Module"
CLI->>Runner : Execute script
Runner->>Resources : build_resources(Settings)
Resources-->>Runner : AppResources
Runner->>Factory : create_bot(resources.settings)
Factory-->>Runner : Bot instance
Factory->>Utils : set_state_dispenser(bot.state_dispenser)
Factory->>Utils : set_qa_service(resources.qa_service)
Utils->>QA : Initialize RAG chain
Utils->>Entities : Load legal entities
Utils->>Attachments : Load module
Runner->>Bot : run_forever()
Bot-->>Runner : Running
```

**Diagram sources**
- [polling_vk.py:17-31](file://scripts/polling_vk.py#L17-L31)
- [resources.py:51-165](file://app/resources.py#L51-L165)
- [bot.py:49-52](file://app/integrations/vk/bot.py#L49-L52)
- [handlers/__init__.py:32-39](file://app/integrations/vk/handlers/__init__.py#L32-L39)
- [qa_service.py:51-81](file://app/domain/qa_service.py#L51-L81)
- [entities.py:16-21](file://app/domain/entities.py#L16-L21)

**Section sources**
- [polling_vk.py:17-31](file://scripts/polling_vk.py#L17-L31)
- [resources.py:51-165](file://app/resources.py#L51-L165)
- [config.py:4-9](file://app/config.py#L4-L9)

### Enhanced Ask Handler with Better UX
The ask handler has been significantly improved with better user experience:

```mermaid
flowchart TD
Start(["on_ask_text(message)"]) --> Validate["Validate question text"]
Validate --> Valid{"Question empty?"}
Valid --> |Yes| Retry["Prompt for question again"]
Valid --> |No| ClearState["Clear state"]
ClearState --> Typing["Show typing indicator"]
Typing --> Detect["Detect topic hints"]
Detect --> Query["Query RAG with wait"]
Query --> Hint{"Has disclaimer?"}
Hint --> |Yes| AddDisclaimer["Add background topic disclaimer"]
Hint --> |No| Prepend["Prepend question context"]
AddDisclaimer --> Prepend
Prepend --> Truncate["Truncate if too long"]
Truncate --> Answer["Send answer with scenario keyboard"]
Retry --> End(["End"])
Answer --> End
```

**Diagram sources**
- [ask.py:51-89](file://app/integrations/vk/handlers/ask.py#L51-L89)

**Section sources**
- [ask.py:1-90](file://app/integrations/vk/handlers/ask.py#L1-L90)

### Enhanced Vacation Workflow with Two-Step Selection and Template Attachment
The vacation workflow has been significantly enhanced with a two-step selection process and document template attachment:

```mermaid
flowchart TD
Start(["CMD_VACATION"]) --> Menu["Display vacation menu"]
Menu --> SelectType["User selects vacation type"]
SelectType --> TypeKB["Display vacation type keyboard"]
TypeKB --> EntitySelect["User selects legal entity"]
EntitySelect --> EntityKB["Display entity selection keyboard"]
EntityKB --> Template["Generate vacation template"]
Template --> CFService["CategoryFileService.get_file()"]
CFService --> S3Download["Download template from S3"]
S3Download --> SendAttachment["Send document attachment"]
SendAttachment --> End(["Complete"])
Template --> SendText["Fallback to text template"]
SendText --> End
```

**Diagram sources**
- [vacation.py:50-116](file://app/integrations/vk/handlers/vacation.py#L50-L116)

**Updated** The vacation workflow now features a two-step selection process: first selecting the vacation type (paid/unpaid), then selecting the legal entity for template generation. The system attempts to send document attachments first, falling back to text templates if no template is available. This provides better user experience and ensures accurate template generation based on company-specific policies.

**Section sources**
- [vacation.py:1-134](file://app/integrations/vk/handlers/vacation.py#L1-L134)

### Enhanced Legal Entity Definitions
The legal entity definitions have been updated with new company names:

**Updated** The legal entities now include four companies with their full legal names:
- "Кафетера" (Ooo "Кафетера Групп Рус")
- "Вкусно" (Ooo "Вкусно") 
- "Аврора" (Ooo "Аврора РусКо")
- "СМАРТ" (Ooo "СМАРТ ПИТАНИЕ")

These entities are used across hiring, vacation, and HR request workflows for accurate policy generation.

**Section sources**
- [entities.py:1-24](file://app/domain/entities.py#L1-L24)

### Sections Handler Using New Helper Function
The sections handler now uses the new `send_rag_answer()` helper function for consistent RAG response handling:

**Updated** The sections handler has been simplified to use the centralized `send_rag_answer()` function, which automatically handles typing indicators, timeout detection, question context prepending, and keyboard generation. This ensures consistent user experience across all RAG-enabled handlers.

**Section sources**
- [sections.py:1-35](file://app/integrations/vk/handlers/sections.py#L1-L35)

### Enhanced Error Handling Implementation
The new error handling system provides consistent patterns across all handlers:

**Updated** The enhanced error handling system replaces the previous get_entity_or_error pattern with require_entity functions and @catch_entity_error decorators. The fire handler now uses `@catch_entity_error` decorator combined with `require_entity` function for improved error handling. The hire handler also uses the same pattern. The vacation handler maintains backward compatibility with the `get_entity_or_error` pattern for continued support.

**Section sources**
- [handlers/__init__.py:98-141](file://app/integrations/vk/handlers/__init__.py#L98-L141)
- [fire.py:53-57](file://app/integrations/vk/handlers/fire.py#L53-L57)
- [hire.py:51-59](file://app/integrations/vk/handlers/hire.py#L51-L59)
- [vacation.py:79-86](file://app/integrations/vk/handlers/vacation.py#L79-L86)

## Dependency Analysis
External dependencies relevant to VK integration:
- vkbottle is the primary framework for VK bot development
- pydantic-settings provides typed configuration from environment variables
- pytest is used for unit tests covering factory wiring, keyboards, states, QA service integration, and enhanced handler functionality
- LangChain provides the RAG framework with configurable LLM providers
- Qdrant client provides vector database capabilities for document retrieval
- aiobotocore provides async S3/MinIO client for cloud storage
- aiosqlite provides async SQLite access for metadata storage

```mermaid
graph LR
VKBot["VK Bot (bot.py)"] --> VKFw["vkbottle"]
VKBot --> Cfg["Settings (config.py)"]
VKBot --> Utils["Centralized Utils (handlers/__init__.py)"]
Utils --> SD["BuiltinStateDispenser"]
Utils --> QA["QA Service (qa_service.py)"]
Utils --> Entities["Legal Entities (entities.py)"]
Utils --> Attachments["Document Attachments (attachments.py)"]
Attachments --> CFService["CategoryFileService"]
CFService --> CFRepo["CategoryFileRepository"]
CFService --> S3["S3Storage"]
QA --> LangChain["LangChain"]
QA --> Qdrant["Qdrant Client"]
Resources["Resources (resources.py)"] --> VKBot
Resources --> QA
Resources --> Attachments
Tests["Tests"] --> VKBot
Tests --> Utils
Tests --> QA
Tests --> Entities
Tests --> Attachments
Tests --> VKFw
Tests --> Cfg
```

**Diagram sources**
- [bot.py:7-10](file://app/integrations/vk/bot.py#L7-L10)
- [config.py:4-9](file://app/config.py#L4-L9)
- [handlers/__init__.py:32-39](file://app/integrations/vk/handlers/__init__.py#L32-L39)
- [qa_service.py:60-81](file://app/domain/qa_service.py#L60-L81)
- [entities.py:16-24](file://app/domain/entities.py#L16-L24)
- [attachments.py:19-121](file://app/integrations/vk/attachments.py#L19-L121)
- [category_repo.py:47-52](file://app/storage/category_repo.py#L47-L52)
- [s3.py:14-37](file://app/storage/s3.py#L14-L37)
- [resources.py:51-165](file://app/resources.py#L51-L165)
- [pyproject.toml:17-21](file://pyproject.toml#L17-L21)

**Section sources**
- [pyproject.toml:17-21](file://pyproject.toml#L17-L21)
- [bot.py:7-10](file://app/integrations/vk/bot.py#L7-L10)
- [config.py:4-9](file://app/config.py#L4-L9)
- [handlers/__init__.py:32-39](file://app/integrations/vk/handlers/__init__.py#L32-L39)
- [qa_service.py:60-81](file://app/domain/qa_service.py#L60-L81)
- [entities.py:16-24](file://app/domain/entities.py#L16-L24)
- [attachments.py:19-121](file://app/integrations/vk/attachments.py#L19-L121)
- [category_repo.py:47-52](file://app/storage/category_repo.py#L47-L52)
- [s3.py:14-37](file://app/storage/s3.py#L14-L37)
- [resources.py:51-165](file://app/resources.py#L51-L165)

## Performance Considerations
- Handler order minimizes unnecessary evaluations; keep fallback last
- Centralized state dispenser sharing provides consistent resource management with connection pooling and graceful degradation
- Centralized QA service access provides consistent resource management with connection pooling and graceful degradation
- Enhanced document attachment system provides efficient template delivery with proper error handling and fallback mechanisms
- RAG responses are truncated to VK message limits to prevent API errors
- Keyboard construction is lightweight; reuse shared keyboards and payloads to reduce overhead
- Long Poll mode is suitable for small to medium workloads; consider webhooks for higher throughput
- Avoid heavy synchronous operations inside handlers; delegate to async tasks when needed
- Centralized utilities provide consistent error handling and fallback responses for QA service failures
- Shared state dispenser reduces memory overhead across handlers
- Resource management handles graceful initialization and cleanup of RAG components
- **New** Intelligent timeout handling prevents blocking operations and improves perceived performance
- **New** Automatic question context prepending reduces user confusion and improves conversation clarity
- **New** The `send_rag_answer()` helper function standardizes RAG response handling across all handlers, reducing code duplication and improving consistency
- **New** Enhanced fire workflow with entity-based resignation flow improves user experience and reduces errors
- **New** Updated legal entity definitions with full company names improve accuracy and professionalism
- **New** Document attachment system provides scalable template delivery with lazy initialization and proper error handling
- **New** Enhanced keyboard system with entity selection provides better user experience for multi-step workflows
- **New** Improved test infrastructure validates enhanced handler functionality and handler count expectations
- **New** Enhanced error handling system provides consistent patterns across all handlers using require_entity functions and @catch_entity_error decorators
- **New** EntityNotFoundError class provides clear error semantics for entity validation failures

## Troubleshooting Guide
Common issues and resolutions:
- Handler not triggered:
  - Verify handler order and that fallback is last
  - Confirm payload keys match exactly (case-sensitive)
  - Check for proper handler registration in factory
- Incorrect keyboard layout:
  - Validate main menu composition and service row inclusion
  - Ensure payloads are present and unique
  - Verify entity selection keyboards are properly constructed
- Token errors:
  - Confirm VK access token is set in environment and forwarded to the Bot
- QA service failures:
  - Check Qdrant connectivity and LLM provider availability
  - Verify settings for qdrant_url, qdrant_api_key, qdrant_collection
  - Monitor for RAG chain initialization warnings
  - Ensure centralized QA service is properly initialized before handlers are loaded
- Document attachment failures:
  - Check S3 connectivity and bucket permissions
  - Verify settings for s3_endpoint_url, s3_access_key, s3_secret_key, s3_bucket
  - Ensure CategoryFileService is properly initialized before handlers are loaded
  - Monitor for S3 client initialization warnings
  - Verify document upload server integration with VK API
- Multi-step dialogs:
  - Use state groups to track user progress and avoid ambiguous replies
  - Verify state dispenser is properly shared between bot and handlers
  - Check entity validation logic for proper error handling
- RAG response issues:
  - Check for VK message length truncation
  - Verify topic detection and scenario linking
- Centralized access errors:
  - Ensure set_qa_service() and set_state_dispenser() are called before handler registration
  - Verify get_qa_service() and get_state_dispenser() are imported correctly in handler modules
- State management issues:
  - Verify BuiltinStateDispenser is properly shared between bot and handlers
  - Check that set_state_dispenser() is called during bot creation
  - Ensure get_state_dispenser() is used consistently across all handlers
- **New** Timeout handling issues:
  - Verify query_rag_with_wait() is properly imported in handlers
  - Check that timeout values are appropriate for your RAG service performance
  - Ensure "please wait" messages are being sent correctly
- **New** Question context issues:
  - Verify send_rag_answer() is being used instead of direct QA service calls
  - Check that question truncation logic is working correctly
  - Ensure back_payload parameters are properly passed to maintain navigation
- **New** Helper function integration issues:
  - Verify send_rag_answer() is imported from the centralized utilities module
  - Check that all handlers using the helper function are properly updated
  - Ensure the helper function is available in the handlers/__init__.py module
- **New** Fire handler issues:
  - Verify entity-based resignation flow is working correctly
  - Check that entity selection keyboard is properly generated
  - Ensure template generation uses correct entity information
  - Verify CategoryFileService is properly initialized for template attachment
  - Check document attachment system for proper template delivery
- **New** Legal entity issues:
  - Verify entity IDs match between keyboards and entity lookup
  - Check that full company names are displayed correctly
  - Ensure entity validation returns proper error messages
- **New** Handler count validation issues:
  - Verify factory registers all 27 handlers correctly
  - Check test expectations for updated handler counts
  - Ensure proper handler ordering with fallback as last
- **New** Error handling issues:
  - Verify @catch_entity_error decorator is properly imported and applied
  - Check that require_entity function is used instead of get_entity_or_error
  - Ensure EntityNotFoundError is properly handled by decorators
  - Verify error handling consistency across all handlers
- **New** Entity validation issues:
  - Check that entity IDs are properly extracted from payload data
  - Verify ENTITY_BY_ID dictionary contains all required entities
  - Ensure error messages are sent to users before raising exceptions

Validation references:
- Handler order and counts: [test_bot_factory.py:18-86](file://tests/test_bot_factory.py#L18-L86)
- QA service integration: [test_qa_service.py:176-198](file://tests/test_qa_service.py#L176-L198)
- Keyboard composition and payloads: [test_keyboards.py:49-92](file://tests/test_keyboards.py#L49-L92), [test_keyboards.py:176-192](file://tests/test_keyboards.py#L176-L192)
- State definitions: [test_states.py:8-31](file://tests/test_states.py#L8-L31)
- Centralized access patterns: [handlers/__init__.py:22-39](file://app/integrations/vk/handlers/__init__.py#L22-L39)
- Enhanced fire handler functionality: [fire.py:40-67](file://app/integrations/vk/handlers/fire.py#L40-L67)
- Document attachment system: [attachments.py:19-121](file://app/integrations/vk/attachments.py#L19-L121)
- State dispenser sharing: [test_bot_factory.py:82-86](file://tests/test_bot_factory.py#L82-L86)
- **New** Enhanced error handling patterns: [handlers/__init__.py:98-141](file://app/integrations/vk/handlers/__init__.py#L98-L141)
- **New** Fire handler with decorators: [fire.py:53-57](file://app/integrations/vk/handlers/fire.py#L53-L57)
- **New** Hire handler with decorators: [hire.py:51-59](file://app/integrations/vk/handlers/hire.py#L51-L59)
- **New** Vacation handler with backward compatibility: [vacation.py:79-86](file://app/integrations/vk/handlers/vacation.py#L79-L86)

**Section sources**
- [test_bot_factory.py:18-86](file://tests/test_bot_factory.py#L18-L86)
- [test_qa_service.py:176-198](file://tests/test_qa_service.py#L176-L198)
- [test_keyboards.py:49-92](file://tests/test_keyboards.py#L49-L92)
- [test_keyboards.py:176-192](file://tests/test_keyboards.py#L176-L192)
- [test_states.py:8-31](file://tests/test_states.py#L8-L31)
- [handlers/__init__.py:22-39](file://app/integrations/vk/handlers/__init__.py#L22-L39)
- [fire.py:40-67](file://app/integrations/vk/handlers/fire.py#L40-L67)
- [attachments.py:19-121](file://app/integrations/vk/attachments.py#L19-L121)
- [handlers/__init__.py:98-141](file://app/integrations/vk/handlers/__init__.py#L98-L141)
- [fire.py:53-57](file://app/integrations/vk/handlers/fire.py#L53-L57)
- [hire.py:51-59](file://app/integrations/vk/handlers/hire.py#L51-L59)
- [vacation.py:79-86](file://app/integrations/vk/handlers/vacation.py#L79-L86)

## Conclusion
The VK integration leverages a clean factory pattern with centralized state dispenser sharing, deterministic handler ordering, payload-driven navigation, and comprehensive RAG integration with centralized service management to deliver a sophisticated, extensible bot. The system now includes significant user experience improvements through intelligent timeout handling for RAG responses, automatic question context prepending, enhanced fire workflow with entity-based resignation flow, document template attachment capabilities, and updated legal entity definitions with new company names.

**Updated** The system now features enhanced error handling consistency with new require_entity decorators and @catch_entity_error decorators, providing improved reliability and user experience across all HR-related handlers. The new error handling patterns replace the previous get_entity_or_error pattern with more consistent and maintainable approaches. The system now includes 27 total handlers across all VK integration modules, providing comprehensive HR coverage with enhanced user experience.

The new `query_rag_with_wait()` function provides intelligent timeout detection that automatically sends "please wait" notifications when RAG responses take longer than 3 seconds, while the `send_rag_answer()` helper function standardizes RAG response handling across all handlers by automatically setting typing indicators, querying RAG with timeout handling, prepending question context, truncating responses to VK limits, and adding appropriate navigation keyboards.

The enhanced fire handler with entity-based resignation flow represents a significant advancement in HR workflow automation, providing company-specific templates and seamless document delivery. The document attachment system ensures accurate, company-specific HR documentation while maintaining backward compatibility with RAG-based fallback responses.

The new enhanced error handling system provides consistent patterns across all handlers using require_entity functions and @catch_entity_error decorators, with EntityNotFoundError class providing clear error semantics for entity validation failures. The system maintains backward compatibility with the vacation handler's use of get_entity_or_error pattern while adopting the new patterns in fire and hire handlers.

By following the established patterns—registering labelers in order, using shared keyboard builders, implementing centralized state management, integrating the centralized QA service access layer, following the centralized initialization process, and implementing consistent error handling patterns—the system supports easy extension and maintenance. For production, consider migrating to VK webhooks, adding structured error handling and logging, and implementing proper QA service lifecycle management.

## Appendices

### Extending the Bot with New Handlers
Steps to add a new section:
- Define a payload constant for the new command
- Add a handler in a new or existing module annotated with the payload
- Import and use the centralized state dispenser, QA service access patterns:
  - Use `from app.integrations.vk.handlers import get_state_dispenser` for state management
  - Use `from app.integrations.vk.handlers import get_qa_service` for direct access
  - Use `from app.integrations.vk.handlers import send_rag_answer` for standardized RAG responses
  - Use `from app.integrations.vk.handlers import require_entity` for entity validation
  - Use `from app.integrations.vk.handlers import catch_entity_error` for error handling
- Build a keyboard with the service row to ensure Back/Home/Contact HR are always available
- Register the new labeler in the factory's loader list and ensure it precedes fallback
- Update handler count expectations in tests
- **New** Implement proper error handling using require_entity and @catch_entity_error patterns

**Updated** When adding new handlers, integrate with the centralized state dispenser and QA service by importing from `app.integrations.vk.handlers` and using the provided utility functions for consistent error handling and resource management. Consider using `query_rag_with_wait()` for any handler that processes user questions to provide better user experience during slow RAG responses, and use `send_rag_answer()` for standardized RAG response handling across all handlers. For multi-step workflows with template attachment, consider implementing document attachment system integration using the provided helper functions. Implement proper error handling using require_entity and @catch_entity_error patterns for consistent error handling across all handlers.

References:
- Payload constants: [keyboards.py:13-24](file://app/integrations/vk/keyboards.py#L13-L24)
- Handler registration order: [bot.py:31-41](file://app/integrations/vk/bot.py#L31-L41)
- Centralized state dispenser access: [handlers/__init__.py:32-39](file://app/integrations/vk/handlers/__init__.py#L32-L39)
- Centralized QA access patterns: [handlers/__init__.py:22-29](file://app/integrations/vk/handlers/__init__.py#L22-L29)
- Keyboard service row: [keyboards.py:29-50](file://app/integrations/vk/keyboards.py#L29-L50)
- Enhanced fire handler integration: [fire.py:40-67](file://app/integrations/vk/handlers/fire.py#L40-L67)
- Document attachment system: [attachments.py:19-121](file://app/integrations/vk/attachments.py#L19-L121)
- **New** Timeout handling: [handlers/__init__.py:46-86](file://app/integrations/vk/handlers/__init__.py#L46-L86)
- **New** State management patterns: [states.py:4-17](file://app/integrations/vk/states.py#L4-L17)
- **New** Enhanced error handling patterns: [handlers/__init__.py:98-141](file://app/integrations/vk/handlers/__init__.py#L98-L141)
- **New** Fire handler with decorators: [fire.py:53-57](file://app/integrations/vk/handlers/fire.py#L53-L57)
- **New** Hire handler with decorators: [hire.py:51-59](file://app/integrations/vk/handlers/hire.py#L51-L59)
- **New** Vacation handler with backward compatibility: [vacation.py:79-86](file://app/integrations/vk/handlers/vacation.py#L79-L86)

**Section sources**
- [keyboards.py:13-50](file://app/integrations/vk/keyboards.py#L13-L50)
- [bot.py:31-41](file://app/integrations/vk/bot.py#L31-L41)
- [handlers/__init__.py:22-39](file://app/integrations/vk/handlers/__init__.py#L22-L39)
- [fire.py:40-67](file://app/integrations/vk/handlers/fire.py#L40-L67)
- [attachments.py:19-121](file://app/integrations/vk/attachments.py#L19-L121)
- [handlers/__init__.py:98-141](file://app/integrations/vk/handlers/__init__.py#L98-L141)
- [fire.py:53-57](file://app/integrations/vk/handlers/fire.py#L53-L57)
- [hire.py:51-59](file://app/integrations/vk/handlers/hire.py#L51-L59)
- [vacation.py:79-86](file://app/integrations/vk/handlers/vacation.py#L79-L86)

### Integrating with VK Webhook System
Guidance:
- Configure a VK community webhook endpoint pointing to your server
- Replace Long Poll runner with a FastAPI route that accepts VK POST callbacks
- Parse incoming update objects and dispatch to the same handler labelers
- Ensure the Bot is initialized with the same token, labelers, and centralized state dispenser access as in Long Poll mode
- Implement proper error handling for webhook processing failures
- Maintain the centralized QA service initialization patterns for consistent access across all handlers
- Ensure state dispenser is properly shared between bot and handlers in webhook mode
- **New** Implement consistent error handling patterns using require_entity and @catch_entity_error decorators in webhook mode

References:
- Bot initialization and token forwarding: [bot.py:45-58](file://app/integrations/vk/bot.py#L45-L58), [test_bot_factory.py:75-81](file://tests/test_bot_factory.py#L75-L81)
- Handler registration: [bot.py:54-55](file://app/integrations/vk/bot.py#L54-L55)
- Centralized state dispenser sharing: [bot.py:49-52](file://app/integrations/vk/bot.py#L49-L52)
- Centralized QA service initialization: [handlers/__init__.py:22-29](file://app/integrations/vk/handlers/__init__.py#L22-L29)
- **New** Enhanced error handling patterns: [handlers/__init__.py:98-141](file://app/integrations/vk/handlers/__init__.py#L98-L141)

**Section sources**
- [bot.py:45-58](file://app/integrations/vk/bot.py#L45-L58)
- [test_bot_factory.py:75-81](file://tests/test_bot_factory.py#L75-L81)
- [handlers/__init__.py:22-29](file://app/integrations/vk/handlers/__init__.py#L22-L29)
- [handlers/__init__.py:98-141](file://app/integrations/vk/handlers/__init__.py#L98-L141)

### Best Practices for VK Bot Development
- Keep handler order explicit and documented
- Use payload constants to prevent typos and ensure consistency
- Prefer keyboard-driven navigation to reduce ambiguity
- Centralize keyboard building logic to enforce UX standards
- Integrate the centralized state dispenser for dynamic content generation across HR-related flows
- Integrate the centralized QA service access layer for dynamic content generation across HR-related flows
- Implement proper error handling and fallback responses for QA service failures using centralized patterns
- Add logging around handler execution and RAG processing for observability
- Validate configuration at startup and fail fast on missing tokens or service initialization failures
- Manage service lifecycles with proper resource cleanup during shutdown
- Use centralized utilities for consistent state management, error handling, and service access patterns
- Ensure state dispenser is properly shared between bot and handlers for consistent state persistence
- Implement proper resource management for graceful initialization and cleanup of RAG components
- **New** Use intelligent timeout handling for any handler that processes user questions to improve user experience
- **New** Always use automatic question context prepending to maintain conversation clarity and traceability
- **New** Standardize RAG response handling across all handlers using the `send_rag_answer()` helper function
- **New** Use `query_rag_with_wait()` for any handler that processes user questions to provide intelligent timeout handling
- **New** Implement state management for multi-step workflows using the centralized BuiltinStateDispenser
- **New** Leverage the enhanced fire workflow patterns for improved user experience with entity-based resignation
- **New** Access updated legal entity definitions through the centralized utilities module for accurate content generation
- **New** Use document attachment system for all template-related operations with proper validation and error handling
- **New** Implement comprehensive error handling for document upload failures and template availability
- **New** Provide administrative UI for template management with proper validation and security measures
- **New** Use require_entity functions and @catch_entity_error decorators for consistent error handling across all handlers
- **New** Implement EntityNotFoundError class for clear error semantics in entity validation failures
- **New** Maintain backward compatibility with existing handlers while adopting new error handling patterns

### Centralized State and Service Integration Patterns
- Initialize state dispenser during bot creation and register with centralized utilities for immediate state management capabilities
- Initialize QA service during bot creation and register with centralized utilities for immediate RAG capabilities
- Use `from app.integrations.vk.handlers import get_state_dispenser` for all state management operations
- Use `from app.integrations.vk.handlers import get_qa_service` for all HR-related content generation
- Use `from app.integrations.vk.handlers import send_rag_answer` for standardized RAG response handling
- Use `from app.integrations.vk.handlers import get_entity_or_error` for entity validation (legacy pattern)
- Use `from app.integrations.vk.handlers import require_entity` for entity validation (new pattern)
- Use `from app.integrations.vk.handlers import catch_entity_error` for error handling (new pattern)
- Implement proper error handling with fallback responses using centralized patterns
- Truncate long responses to VK message limits automatically through centralized access
- Close QA service during application shutdown using centralized management
- Monitor service health and implement graceful degradation strategies through centralized access layer
- Ensure centralized state dispenser is initialized before handler registration to prevent runtime errors
- Ensure centralized QA service is initialized before handler registration to prevent runtime errors
- **New** Use `query_rag_with_wait()` for any handler that processes user questions to provide intelligent timeout handling
- **New** Always use `send_rag_answer()` instead of direct QA service calls to ensure consistent user experience and question context preservation
- **New** Leverage the centralized utilities module for consistent error handling and resource management patterns across all handlers
- **New** Implement state management patterns for multi-step workflows using the centralized BuiltinStateDispenser
- **New** Utilize the enhanced fire workflow patterns for improved user experience with entity-based resignation
- **New** Access legal entity definitions through the centralized utilities module for accurate content generation
- **New** Use document attachment system for all template operations with proper validation and error handling
- **New** Implement comprehensive error handling for document upload failures and template availability
- **New** Provide administrative UI for template management with proper validation and security measures
- **New** Use require_entity functions and @catch_entity_error decorators for consistent error handling across all handlers
- **New** Implement EntityNotFoundError class for clear error semantics in entity validation failures
- **New** Maintain backward compatibility with existing handlers while adopting new error handling patterns

**Section sources**
- [handlers/__init__.py:22-39](file://app/integrations/vk/handlers/__init__.py#L22-L39)
- [bot.py:49-52](file://app/integrations/vk/bot.py#L49-L52)
- [qa_service.py:51-120](file://app/domain/qa_service.py#L51-L120)
- [test_qa_service.py:1-198](file://tests/test_qa_service.py#L1-L198)
- [test_bot_factory.py:82-86](file://tests/test_bot_factory.py#L82-L86)
- [test_ask_block9.py:94-112](file://tests/test_ask_block9.py#L94-L112)
- [states.py:4-17](file://app/integrations/vk/states.py#L4-L17)
- [fire.py:40-67](file://app/integrations/vk/handlers/fire.py#L40-L67)
- [entities.py:16-24](file://app/domain/entities.py#L16-L24)
- [attachments.py:19-121](file://app/integrations/vk/attachments.py#L19-L121)
- [handlers/__init__.py:98-141](file://app/integrations/vk/handlers/__init__.py#L98-L141)
- [fire.py:53-57](file://app/integrations/vk/handlers/fire.py#L53-L57)
- [hire.py:51-59](file://app/integrations/vk/handlers/hire.py#L51-L59)
- [vacation.py:79-86](file://app/integrations/vk/handlers/vacation.py#L79-L86)