# Domain Content Management

<cite>
**Referenced Files in This Document**
- [content.py](file://app/domain/content.py)
- [entities.py](file://app/domain/entities.py)
- [topic_hints.py](file://app/domain/topic_hints.py)
- [bot.py](file://app/integrations/vk/bot.py)
- [config.py](file://app/config.py)
- [keyboards.py](file://app/integrations/vk/keyboards.py)
- [states.py](file://app/integrations/vk/states.py)
- [rules.py](file://app/integrations/vk/rules.py)
- [start.py](file://app/integrations/vk/handlers/start.py)
- [ask.py](file://app/integrations/vk/handlers/ask.py)
- [hire.py](file://app/integrations/vk/handlers/hire.py)
- [fire.py](file://app/integrations/vk/handlers/fire.py)
- [vacation.py](file://app/integrations/vk/handlers/vacation.py)
- [pay.py](file://app/integrations/vk/handlers/pay.py)
- [sections.py](file://app/integrations/vk/handlers/sections.py)
- [fallback.py](file://app/integrations/vk/handlers/fallback.py)
- [attachments.py](file://app/integrations/vk/attachments.py)
- [polling_vk.py](file://scripts/polling_vk.py)
- [pyproject.toml](file://pyproject.toml)
- [test_content.py](file://tests/test_content.py)
- [test_keyboards_block2.py](file://tests/test_keyboards_block2.py)
- [test_rag_stub_block3.py](file://tests/test_rag_stub_block3.py)
</cite>

## Update Summary
**Changes Made**
- Removed TEMPLATE_DISCLAIMER constant and associated universal disclaimer from document templates
- Streamlined content module to use TEMPLATE_FILE_STUB for fallback document templates
- Simplified fire flow to maintain only essential HR templates and information
- Enhanced vacation template functionality to support paid and unpaid vacation types with clear Russian labeling
- Updated fire handler to use category document system instead of hardcoded content constants
- Improved content management system architecture for better maintainability
- Integrated category document system for robust document delivery with automatic fallback

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
This document describes the Domain Content Management system that powers the Cafetera HR Bot. The system centralizes static content, document templates, checklists, and structured formatters used across HR-related flows in the VKontakte chatbot. It ensures consistency, maintainability, and separation of concerns by keeping content definitions separate from handler logic, enabling thin handlers and reusable content modules.

**Updated** The system now focuses exclusively on content management rather than multi-step HR request processing, with free-text question handling via RAG integration. The content management system has been cleaned up to remove redundant universal disclaimer and associated disclaimer text, streamlining document templates to use TEMPLATE_FILE_STUB for fallback content. The fire flow has been streamlined to maintain only essential HR templates and information, removing redundant constants and simplifying the user interface. The vacation template functionality has been enhanced to support both paid and unpaid vacation types with clear Russian labeling. The category document system provides centralized document management with automatic fallback to static content, ensuring consistent user experience across different deployment configurations.

## Project Structure
The Domain Content Management spans three primary areas:
- Domain layer: Static content definitions, entity definitions, and topic hint detection
- Integration layer: VK bot wiring, handlers, keyboards, and state management
- RAG integration: Question processing and scenario detection

```mermaid
graph TB
subgraph "Domain Layer"
CNT["app/domain/content.py"]
ENT["app/domain/entities.py"]
TH["app/domain/topic_hints.py"]
end
subgraph "Integration Layer"
BOT["app/integrations/vk/bot.py"]
HKY["app/integrations/vk/keyboards.py"]
STT["app/integrations/vk/states.py"]
RUL["app/integrations/vk/rules.py"]
ATT["app/integrations/vk/attachments.py"]
HND["Handlers"]
end
subgraph "Handlers"
HSTART["start.py"]
HASK["ask.py"]
HHIRE["hire.py"]
HFIRE["fire.py"]
HVACA["vacation.py"]
HPAY["pay.py"]
HSECT["sections.py"]
HFALL["fallback.py"]
end
subgraph "Scripts"
POLL["scripts/polling_vk.py"]
end
CNT --> HND
ENT --> HND
TH --> HASK
BOT --> HND
HKY --> HND
STT --> HASK
RUL --> HND
ATT --> HND
HND --> HSTART
HND --> HASK
HND --> HHIRE
HND --> HFIRE
HND --> HVACA
HND --> HPAY
HND --> HSECT
HND --> HFALL
BOT --> POLL
```

**Diagram sources**
- [content.py:1-121](file://app/domain/content.py#L1-L121)
- [entities.py:1-24](file://app/domain/entities.py#L1-L24)
- [topic_hints.py:1-109](file://app/domain/topic_hints.py#L1-L109)
- [bot.py:1-56](file://app/integrations/vk/bot.py#L1-L56)
- [keyboards.py:1-263](file://app/integrations/vk/keyboards.py#L1-L263)
- [states.py:1-9](file://app/integrations/vk/states.py#L1-L9)
- [rules.py:1-31](file://app/integrations/vk/rules.py#L1-L31)
- [attachments.py:1-121](file://app/integrations/vk/attachments.py#L1-L121)
- [start.py:1-42](file://app/integrations/vk/handlers/start.py#L1-L42)
- [ask.py:1-90](file://app/integrations/vk/handlers/ask.py#L1-L90)
- [hire.py:1-118](file://app/integrations/vk/handlers/hire.py#L1-L118)
- [fire.py:1-75](file://app/integrations/vk/handlers/fire.py#L1-L75)
- [vacation.py:1-133](file://app/integrations/vk/handlers/vacation.py#L1-L133)
- [pay.py:1-53](file://app/integrations/vk/handlers/pay.py#L1-L53)
- [sections.py:1-42](file://app/integrations/vk/handlers/sections.py#L1-L42)
- [fallback.py:1-18](file://app/integrations/vk/handlers/fallback.py#L1-L18)
- [polling_vk.py:1-32](file://scripts/polling_vk.py#L1-L32)

**Section sources**
- [content.py:1-121](file://app/domain/content.py#L1-L121)
- [entities.py:1-24](file://app/domain/entities.py#L1-L24)
- [topic_hints.py:1-109](file://app/domain/topic_hints.py#L1-L109)
- [bot.py:1-56](file://app/integrations/vk/bot.py#L1-L56)
- [keyboards.py:1-263](file://app/integrations/vk/keyboards.py#L1-L263)
- [states.py:1-9](file://app/integrations/vk/states.py#L1-L9)
- [rules.py:1-31](file://app/integrations/vk/rules.py#L1-L31)
- [attachments.py:1-121](file://app/integrations/vk/attachments.py#L1-L121)
- [polling_vk.py:1-32](file://scripts/polling_vk.py#L1-L32)

## Core Components
- Domain content module: Centralizes static content, document templates, checklists, and formatters for HR-related content.
- Entities module: Defines legal entity data structures and lookup maps used across flows.
- Topic hints module: Detects clickable scenarios and background-topic disclaimers from free-text questions.
- VK bot factory: Creates and wires the VK bot with all handlers and shared state.
- Keyboard builders: Generate consistent UI layouts and payload commands for navigation and actions.
- Single-state question handler: Processes free-text questions via RAG integration with intelligent scenario detection.
- Handler modules: Thin handlers that orchestrate user interactions and delegate content rendering to domain modules.
- Category document system: Manages document attachments and fallback mechanisms for template delivery.

Key responsibilities:
- Content stability: All long-form content lives in the domain module to keep handlers concise.
- Entity consistency: Legal entities are defined centrally and referenced by ID across flows.
- Scenario detection: Topic hints intelligently route users to appropriate HR sections from free-text questions.
- Reusability: Formatters and templates are pure functions that accept entity context.
- Extensibility: New content can be added to the domain module without changing handler logic.
- **Updated** Streamlined content management: Removed redundant universal disclaimer and simplified template structure using TEMPLATE_FILE_STUB for fallback content.
- **Updated** Robust document delivery: Category document system provides centralized document management with automatic fallback to static content.
- **Updated** Enhanced vacation functionality: Supports both paid and unpaid vacation types with clear Russian labeling.

**Section sources**
- [content.py:1-121](file://app/domain/content.py#L1-L121)
- [entities.py:1-24](file://app/domain/entities.py#L1-L24)
- [topic_hints.py:1-109](file://app/domain/topic_hints.py#L1-L109)
- [bot.py:1-56](file://app/integrations/vk/bot.py#L1-L56)
- [keyboards.py:1-263](file://app/integrations/vk/keyboards.py#L1-L263)
- [states.py:1-9](file://app/integrations/vk/states.py#L1-L9)
- [attachments.py:1-121](file://app/integrations/vk/attachments.py#L1-L121)

## Architecture Overview
The system follows a layered architecture:
- Presentation layer: VK bot and handlers
- Domain layer: Content, entity, and topic hint definitions
- Infrastructure layer: VK integration, keyboards, state management, and routing rules
- Document delivery layer: Category file service and attachment management

```mermaid
graph TB
subgraph "Presentation Layer"
BOT["VK Bot"]
LBLS["Handler Labelers"]
end
subgraph "Domain Layer"
DCNT["Domain Content"]
DENT["Entities"]
DTH["Topic Hints"]
end
subgraph "Infrastructure Layer"
KBD["Keyboards"]
STS["Single State Handler"]
RUL["Payload Rules"]
ATT["Attachment Manager"]
end
subgraph "Document Delivery"
CAT["Category File Service"]
S3["S3 Storage"]
END["Template Fallback"]
end
BOT --> LBLS
LBLS --> DCNT
LBLS --> DENT
LBLS --> DTH
LBLS --> KBD
LBLS --> STS
LBLS --> RUL
LBLS --> ATT
ATT --> CAT
CAT --> S3
CAT --> END
```

**Diagram sources**
- [bot.py:44-56](file://app/integrations/vk/bot.py#L44-L56)
- [content.py:12-17](file://app/domain/content.py#L12-L17)
- [content.py:1-121](file://app/domain/content.py#L1-L121)
- [entities.py:1-24](file://app/domain/entities.py#L1-L24)
- [topic_hints.py:1-109](file://app/domain/topic_hints.py#L1-L109)
- [keyboards.py:1-263](file://app/integrations/vk/keyboards.py#L1-L263)
- [states.py:1-9](file://app/integrations/vk/states.py#L1-L9)
- [rules.py:1-31](file://app/integrations/vk/rules.py#L1-L31)
- [attachments.py:19-121](file://app/integrations/vk/attachments.py#L19-L121)

## Detailed Component Analysis

### Domain Content Module
The domain content module defines:
- Document template stubs for fallback content delivery using TEMPLATE_FILE_STUB
- Hire-related checklists and onboarding lists
- Enhanced vacation template text with optional vacation type parameter
- RAG stub placeholders for future knowledge base integration
- Error messages for unavailable documents and missing answers

Implementation highlights:
- Pure functions that accept a LegalEntity context to render localized content
- Centralized fallback text using TEMPLATE_FILE_STUB for consistency
- Standardized formatting for HR-related content with structured headers and fields
- **Updated** Removed universal TEMPLATE_DISCLAIMER constant and associated disclaimer text
- **Updated** Simplified template structure using TEMPLATE_FILE_STUB for fallback content
- **Updated** Enhanced vacation_template_text() function accepts optional vtype parameter with Russian labels mapping (paid/unpaid)

```mermaid
classDiagram
class DomainContent {
+TEMPLATE_FILE_STUB : string
+ERR_DOCUMENT_UNAVAILABLE : string
+ERR_NO_ANSWER : string
+ERR_INTEGRATION_REQUIRED : string
+hire_checklist(entity) string
+onboarding_checklist(entity) string
+hire_contract_text(entity) string
+vacation_template_text(entity, vtype="paid") string
+rag_stub(topic) string
}
```

**Diagram sources**
- [content.py:12-121](file://app/domain/content.py#L12-L121)

**Section sources**
- [content.py:1-121](file://app/domain/content.py#L1-L121)

### Entities Module
Defines LegalEntity dataclass and a fixed set of legal entities used across flows. Provides:
- Full and short names for display and selection
- Lookup dictionary by ID for fast resolution

```mermaid
classDiagram
class LegalEntity {
+int id
+string short_name
+string full_name
}
class Entities {
+tuple~LegalEntity~ ENTITIES
+dict~int, LegalEntity~ ENTITY_BY_ID
}
Entities --> LegalEntity : "contains"
```

**Diagram sources**
- [entities.py:8-24](file://app/domain/entities.py#L8-L24)

**Section sources**
- [entities.py:1-24](file://app/domain/entities.py#L1-L24)

### Topic Hints Module
The topic hints module provides intelligent scenario detection from free-text questions:
- Clickable scenario keywords for hire, fire, vacation, pay, sick, and probation
- Background-topic keywords with contextual disclaimers
- Deterministic keyword-based detection for fast and reliable routing

```mermaid
classDiagram
class TopicHint {
+scenario_id : str | None
+disclaimer : str | None
}
class TopicHints {
+_SCENARIO_KEYWORDS : dict
+_BACKGROUND_TOPICS : list
+detect_topic_hint(question) TopicHint
}
TopicHints --> TopicHint : "returns"
```

**Diagram sources**
- [topic_hints.py:14-109](file://app/domain/topic_hints.py#L14-L109)

**Section sources**
- [topic_hints.py:1-109](file://app/domain/topic_hints.py#L1-L109)

### VK Bot Factory and Handler Wiring
The bot factory:
- Creates a VK bot instance with a shared state dispenser
- Registers handler labelers in a specific order to ensure proper routing
- Logs successful initialization

```mermaid
sequenceDiagram
participant Script as "polling_vk.py"
participant Config as "Settings"
participant Factory as "create_bot()"
participant VKBot as "VK Bot"
participant Labelers as "Handler Labelers"
Script->>Config : Load environment
Script->>Factory : create_bot(Settings)
Factory->>VKBot : Initialize with token
Factory->>VKBot : Assign shared state dispenser
Factory->>Labelers : Register in order
Labelers-->>VKBot : Handlers loaded
Factory-->>Script : Bot instance
```

**Diagram sources**
- [polling_vk.py:23-27](file://scripts/polling_vk.py#L23-L27)
- [bot.py:44-56](file://app/integrations/vk/bot.py#L44-L56)
- [config.py:4-9](file://app/config.py#L4-L9)

**Section sources**
- [bot.py:1-56](file://app/integrations/vk/bot.py#L1-L56)
- [polling_vk.py:1-32](file://scripts/polling_vk.py#L1-L32)
- [config.py:1-9](file://app/config.py#L1-L9)

### Keyboard Builders and Navigation
Keyboards provide consistent navigation and action buttons:
- Main menu keyboard with seven sections
- Entity selection keyboards for hire and vacation flows
- Action menus for hire (checklist, contract, onboarding)
- Menus for fire (voluntary resignation, dismissal grounds)
- Pay menu (overtime, bonuses)
- Ask question input and result keyboards with scenario suggestions
- Service row with Back/Home/Contact HR buttons
- **Updated** Simplified fire menu with only two essential actions
- **Updated** Vacation type selection keyboard with paid/unpaid options

```mermaid
flowchart TD
Start(["Keyboard Request"]) --> Type{"Type?"}
Type --> |Main Menu| BuildMain["Build main_menu_kb()"]
Type --> |Entity Select| BuildEntity["Build entity_select_kb(cmd)"]
Type --> |Hire Actions| BuildHire["Build hire_actions_kb(entity_id)"]
Type --> |Fire Menu| BuildFire["Build fire_menu_kb()"]
Type --> |Vacation Menu| BuildVaca["Build vacation_menu_kb()"]
Type --> |Vacation Type| BuildVacaType["Build vacation_type_kb()"]
Type --> |Pay Menu| BuildPay["Build pay_menu_kb()"]
Type --> |Ask Input| BuildAskInput["Build ask_input_kb()"]
Type --> |Ask Result| BuildAskResult["Build ask_result_kb(scenario_id)"]
BuildMain --> AddService["Add service row"]
BuildEntity --> AddService
BuildHire --> AddService
BuildFire --> AddService
BuildVaca --> AddService
BuildVacaType --> AddService
BuildPay --> AddService
BuildAskInput --> AddService
BuildAskResult --> AddService
AddService --> End(["Keyboard JSON"])
```

**Diagram sources**
- [keyboards.py:75-263](file://app/integrations/vk/keyboards.py#L75-L263)

**Section sources**
- [keyboards.py:1-263](file://app/integrations/vk/keyboards.py#L1-L263)

### Free-Text Question Handler
The ask handler processes free-text questions through a streamlined flow:
1. Entry point: CMD_ASK payload triggers question input
2. State management: Sets ASK_QUESTION state to capture free text
3. Question processing: Validates input and clears state
4. RAG integration: Queries knowledge base with typing indicator
5. Scenario detection: Uses topic hints to detect clickable scenarios
6. Response formatting: Appends disclaimers and scenario suggestions

```mermaid
stateDiagram-v2
[*] --> AskEntry
AskEntry --> QuestionInput : "CMD_ASK payload"
QuestionInput --> Processing : "free text received"
Processing --> RAGQuery : "validate question"
RAGQuery --> TopicDetection : "RAG answer ready"
TopicDetection --> ResponseFormat : "detect scenario"
ResponseFormat --> [*] : "send formatted answer"
```

**Diagram sources**
- [states.py:4-9](file://app/integrations/vk/states.py#L4-L9)
- [ask.py:38-90](file://app/integrations/vk/handlers/ask.py#L38-L90)

**Section sources**
- [states.py:1-9](file://app/integrations/vk/states.py#L1-L9)
- [ask.py:1-90](file://app/integrations/vk/handlers/ask.py#L1-L90)

### Hire Flow
The hire flow guides users through entity selection and action choices:
- Entity selection with full legal entity names
- Action menu for checklist, contract template, and onboarding checklist
- Content retrieval delegated to domain content functions

```mermaid
sequenceDiagram
participant User as "User"
participant Hire as "hire.py"
participant Entities as "entities.py"
participant Content as "content.py"
User->>Hire : Select "Hire"
Hire->>User : Show entity_select_kb()
User->>Hire : Choose entity
Hire->>Entities : Resolve entity by ID
Entities-->>Hire : LegalEntity
Hire->>User : Show hire_actions_kb(entity_id)
User->>Hire : Choose action
Hire->>Content : hire_checklist/onboarding_checklist/hire_contract_text
Content-->>Hire : Formatted text
Hire-->>User : Send content
```

**Diagram sources**
- [hire.py:32-118](file://app/integrations/vk/handlers/hire.py#L32-L118)
- [entities.py:16-24](file://app/domain/entities.py#L16-L24)
- [content.py:36-68](file://app/domain/content.py#L36-L68)

**Section sources**
- [hire.py:1-118](file://app/integrations/vk/handlers/hire.py#L1-L118)
- [content.py:20-68](file://app/domain/content.py#L20-L68)

### Streamlined Fire Flow
The fire flow has been simplified to maintain only essential HR templates and information:
- Voluntary resignation template via category document system
- Dismissal grounds routed to RAG integration
- **Updated** Removed redundant FIRE_LAST_DAY_CHECKLIST and FIRE_BYPASS_SHEET_TEXT constants
- **Updated** Simplified fire menu to include only two essential actions
- **Updated** Enhanced document delivery using category file service with fallback to static content

```mermaid
flowchart TD
FireEntry["User selects Fire"] --> FireMenu["Show simplified fire_menu_kb()"]
FireMenu --> Resignation["Send category document: fire_resignation"]
Resignation --> AttachmentCheck{"Attachment available?"}
AttachmentCheck --> |Yes| SendDoc["Send document attachment"]
AttachmentCheck --> |No| SendFallback["Send fallback content"]
FireMenu --> Grounds["Send RAG answer: dismissal grounds"]
```

**Diagram sources**
- [fire.py:33-75](file://app/integrations/vk/handlers/fire.py#L33-L75)
- [keyboards.py:179-185](file://app/integrations/vk/keyboards.py#L179-L185)
- [attachments.py:19-121](file://app/integrations/vk/attachments.py#L19-L121)

**Section sources**
- [fire.py:1-75](file://app/integrations/vk/handlers/fire.py#L1-L75)
- [keyboards.py:179-185](file://app/integrations/vk/keyboards.py#L179-L185)
- [attachments.py:19-121](file://app/integrations/vk/attachments.py#L19-L121)

### Enhanced Vacation Flow
The vacation flow now supports both paid and unpaid vacation types with clear Russian labeling:
- Initial vacation menu selection
- Vacation type selection with paid/unpaid options
- Entity selection with vacation type context
- Template generation with explicit vacation type indication
- Disclaimer and file stub for leave application

```mermaid
sequenceDiagram
participant User as "User"
participant Vac as "vacation.py"
participant Entities as "entities.py"
participant Content as "content.py"
participant Attach as "attachments.py"
User->>Vac : Select "Vacation"
Vac->>User : Show vacation_menu_kb()
User->>Vac : Select "Leave Application Template"
Vac->>User : Show vacation_type_kb()
User->>Vac : Choose vacation type (paid/unpaid)
Vac->>User : Show entity_select_kb(CMD_VACATION_TEMPLATE, extra_payload={vtype})
User->>Vac : Choose entity
Vac->>Entities : Resolve entity by ID
Entities-->>Vac : LegalEntity
Vac->>Attach : send_category_document(category="vacation", subcategory=vacation_type)
Attach-->>Vac : Attachment success/failure
Vac->>Content : vacation_template_text(entity, vtype) [fallback]
Content-->>Vac : Formatted text with vacation type label
Vac-->>User : Send content
```

**Diagram sources**
- [vacation.py:47-133](file://app/integrations/vk/handlers/vacation.py#L47-L133)
- [entities.py:16-24](file://app/domain/entities.py#L16-L24)
- [content.py:74-85](file://app/domain/content.py#L74-L85)
- [keyboards.py:202-218](file://app/integrations/vk/keyboards.py#L202-L218)
- [attachments.py:19-121](file://app/integrations/vk/attachments.py#L19-L121)

**Section sources**
- [vacation.py:1-133](file://app/integrations/vk/handlers/vacation.py#L1-L133)
- [content.py:74-85](file://app/domain/content.py#L74-L85)
- [keyboards.py:202-218](file://app/integrations/vk/keyboards.py#L202-L218)
- [attachments.py:19-121](file://app/integrations/vk/attachments.py#L19-L121)

### Pay and Sections Flows
- Pay flow: Overtime and bonus conditions routed to RAG stubs
- Sections flow: Sick leave and probation routes to RAG stubs

These flows demonstrate consistent patterns of delegating content to domain modules and using stubs for future enhancements.

**Section sources**
- [pay.py:1-53](file://app/integrations/vk/handlers/pay.py#L1-L53)
- [sections.py:1-42](file://app/integrations/vk/handlers/sections.py#L1-L42)

### Fallback Handler
The fallback handler ensures users stay on track by responding to arbitrary text with a reminder to use menu buttons and returning to the main menu.

**Section sources**
- [fallback.py:1-18](file://app/integrations/vk/handlers/fallback.py#L1-L18)

### Category Document System
The category document system manages document attachments and fallback mechanisms:
- Queries CategoryFileService for files in given categories and subcategories
- Downloads files from S3 storage and uploads to VK documents API
- Provides fallback to static content when documents are unavailable
- Handles error cases gracefully with logging and user feedback

**Section sources**
- [attachments.py:1-121](file://app/integrations/vk/attachments.py#L1-L121)

## Dependency Analysis
The system exhibits low coupling and high cohesion:
- Handlers depend on domain content, entities, and topic hints but not on each other
- Keyboard builders encapsulate UI logic
- Single-state question handler processes free-text input efficiently
- Payload rules enable flexible routing based on JSON payloads
- **Updated** Simplified fire flow depends only on keyboard builders and category document system
- **Updated** Enhanced vacation flow depends on both content module and keyboard builders for type selection
- **Updated** Category document system provides centralized document delivery with fallback mechanisms
- **Updated** Robust error handling ensures graceful degradation when services are unavailable

```mermaid
graph TB
HSTART["start.py"] --> HKY["keyboards.py"]
HASK["ask.py"] --> HKY
HASK --> TH["topic_hints.py"]
HASK --> STT["states.py"]
HHIRE["hire.py"] --> HKY
HHIRE --> ENT["entities.py"]
HHIRE --> CNT["content.py"]
HFIRE["fire.py"] --> HKY
HFIRE --> ATT["attachments.py"]
HFIRE --> CNT
HVACA["vacation.py"] --> HKY
HVACA --> ENT
HVACA --> CNT
HVACA --> ATT
HPAY["pay.py"] --> HKY
HPAY --> CNT
HSECT["sections.py"] --> HKY
HSECT --> CNT
HFALL["fallback.py"] --> HKY
BOT["bot.py"] --> HSTART
BOT --> HASK
BOT --> HHIRE
BOT --> HFIRE
BOT --> HVACA
BOT --> HPAY
BOT --> HSECT
BOT --> HFALL
ATT --> CAT["CategoryFileService"]
CAT --> S3["S3 Storage"]
CAT --> FALLBACK["TEMPLATE_FILE_STUB"]
```

**Diagram sources**
- [bot.py:10-56](file://app/integrations/vk/bot.py#L10-L56)
- [start.py:1-42](file://app/integrations/vk/handlers/start.py#L1-L42)
- [ask.py:1-30](file://app/integrations/vk/handlers/ask.py#L1-L30)
- [hire.py:1-23](file://app/integrations/vk/handlers/hire.py#L1-L23)
- [fire.py:1-25](file://app/integrations/vk/handlers/fire.py#L1-L25)
- [vacation.py:1-22](file://app/integrations/vk/handlers/vacation.py#L1-L22)
- [pay.py:1-18](file://app/integrations/vk/handlers/pay.py#L1-L18)
- [sections.py:1-18](file://app/integrations/vk/handlers/sections.py#L1-L18)
- [fallback.py:1-18](file://app/integrations/vk/handlers/fallback.py#L1-L18)
- [keyboards.py:1-263](file://app/integrations/vk/keyboards.py#L1-L263)
- [states.py:1-9](file://app/integrations/vk/states.py#L1-L9)
- [content.py:12-17](file://app/domain/content.py#L12-L17)
- [content.py:1-121](file://app/domain/content.py#L1-L121)
- [entities.py:1-24](file://app/domain/entities.py#L1-L24)
- [topic_hints.py:1-109](file://app/domain/topic_hints.py#L1-L109)
- [attachments.py:1-121](file://app/integrations/vk/attachments.py#L1-L121)

**Section sources**
- [bot.py:1-56](file://app/integrations/vk/bot.py#L1-L56)
- [keyboards.py:1-263](file://app/integrations/vk/keyboards.py#L1-L263)
- [states.py:1-9](file://app/integrations/vk/states.py#L1-L9)
- [content.py:1-121](file://app/domain/content.py#L1-L121)
- [entities.py:1-24](file://app/domain/entities.py#L1-L24)
- [topic_hints.py:1-109](file://app/domain/topic_hints.py#L1-L109)
- [attachments.py:1-121](file://app/integrations/vk/attachments.py#L1-L121)

## Performance Considerations
- Content retrieval is constant-time string concatenations and lookups
- Keyboard generation is lightweight and cached as JSON
- Single-state handler eliminates complex state management overhead
- Topic hint detection uses efficient keyword matching for fast response times
- Handler logic remains thin, minimizing CPU overhead and improving responsiveness
- RAG integration handles heavy computation asynchronously
- **Updated** Simplified fire flow reduces unnecessary content lookups and improves response times
- **Updated** Vacation type selection adds minimal overhead with simple payload parsing and Russian label mapping
- **Updated** Category document system provides efficient document delivery with fallback mechanisms
- **Updated** Streamlined content management reduces memory footprint by removing redundant constants
- **Updated** Robust error handling ensures graceful degradation when services are unavailable

## Troubleshooting Guide
Common issues and resolutions:
- Missing or invalid entity ID: Handlers validate entity presence and return user-friendly messages with navigation back to previous steps
- Empty question input: Ask handler validates free text and prompts users to re-enter questions
- RAG processing delays: Typing indicators provide feedback during asynchronous processing
- Session expiration: State clearing prevents stale contexts; handlers guide users to restart flows
- Unmatched text input: Fallback handler redirects users to the main menu with clear guidance
- **Updated** Simplified fire flow eliminates issues with redundant constants and streamlines error handling
- **Updated** Vacation type parameter validation: Handlers validate vtype payload and default to "paid" if missing or invalid
- **Updated** Category document system failures: Automatic fallback to static content using TEMPLATE_FILE_STUB
- **Updated** Content management cleanup: Removed universal disclaimer constant resolves configuration issues
- **Updated** Document delivery failures: Graceful fallback to TEMPLATE_FILE_STUB ensures users always receive some content

Operational tips:
- Verify VK access token and group ID in environment settings
- Ensure handler registration order is preserved to avoid unintended routing
- Monitor logs for state management errors during question processing
- Test topic hint detection with various question formulations
- **Updated** Test simplified fire flow with category document system
- **Updated** Test vacation template generation with both paid and unpaid vacation types
- **Updated** Verify category file service configuration for document delivery
- **Updated** Monitor content management system for streamlined template functionality
- **Updated** Test fallback mechanisms when S3 storage is unavailable

**Section sources**
- [ask.py:51-90](file://app/integrations/vk/handlers/ask.py#L51-L90)
- [hire.py:44-52](file://app/integrations/vk/handlers/hire.py#L44-L52)
- [vacation.py:51-60](file://app/integrations/vk/handlers/vacation.py#L51-L60)
- [vacation.py:74-86](file://app/integrations/vk/handlers/vacation.py#L74-L86)
- [fire.py:33-75](file://app/integrations/vk/handlers/fire.py#L33-L75)
- [fallback.py:9-12](file://app/integrations/vk/handlers/fallback.py#L9-L12)
- [config.py:4-9](file://app/config.py#L4-L9)
- [attachments.py:45-63](file://app/integrations/vk/attachments.py#L45-L63)

## Conclusion
The Domain Content Management system successfully separates content from presentation, ensuring maintainable and scalable HR bot functionality. By centralizing content definitions, enforcing consistent entity handling, and using thin handlers with intelligent scenario detection, the system provides a solid foundation for future enhancements, including integration with a knowledge base and expanded HR workflows.

**Updated** The removal of universal TEMPLATE_DISCLAIMER constant and associated disclaimer text demonstrates the system's commitment to maintaining only essential HR templates and information. The streamlined content management system improves maintainability by reducing redundancy and simplifying the template structure. The enhanced document delivery system with category file service integration provides robust fallback mechanisms for improved user experience. The simplified fire flow improves user experience by focusing on the most commonly used HR templates while preserving the ability to route complex requests to RAG integration. The enhancement to the vacation template functionality demonstrates the system's extensibility and attention to localization requirements. The addition of optional vacation type parameter with Russian labels mapping (paid/unpaid) improves clarity and usability for Russian-speaking users while maintaining backward compatibility through default parameter values. The transition from multi-step HR request processing to free-text question handling via RAG integration maintains system reliability while improving user experience and reducing complexity. The category document system provides centralized document management with automatic fallback to static content, ensuring consistent user experience across different deployment configurations. The robust error handling and graceful degradation mechanisms ensure system reliability even when external services are unavailable.