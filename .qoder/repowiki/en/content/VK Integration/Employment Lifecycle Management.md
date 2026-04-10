# Employment Lifecycle Management

<cite>
**Referenced Files in This Document**
- [app/domain/entities.py](file://app/domain/entities.py)
- [app/domain/content.py](file://app/domain/content.py)
- [app/integrations/vk/bot.py](file://app/integrations/vk/bot.py)
- [app/integrations/vk/states.py](file://app/integrations/vk/states.py)
- [app/integrations/vk/keyboards.py](file://app/integrations/vk/keyboards.py)
- [app/integrations/vk/handlers/start.py](file://app/integrations/vk/handlers/start.py)
- [app/integrations/vk/handlers/hire.py](file://app/integrations/vk/handlers/hire.py)
- [app/integrations/vk/handlers/fire.py](file://app/integrations/vk/handlers/fire.py)
- [app/integrations/vk/handlers/vacation.py](file://app/integrations/vk/handlers/vacation.py)
- [app/integrations/vk/handlers/pay.py](file://app/integrations/vk/handlers/pay.py)
- [app/integrations/vk/handlers/sections.py](file://app/integrations/vk/handlers/sections.py)
- [app/integrations/vk/handlers/ask.py](file://app/integrations/vk/handlers/ask.py)
- [app/integrations/vk/handlers/fallback.py](file://app/integrations/vk/handlers/fallback.py)
- [app/integrations/vk/rules.py](file://app/integrations/vk/rules.py)
- [app/config.py](file://app/config.py)
- [app/storage/category_models.py](file://app/storage/category_models.py)
- [tests/test_bot_factory.py](file://tests/test_bot_factory.py)
</cite>

## Update Summary
**Changes Made**
- **Simplified Fire Workflow**: Removed FR-6 checklist and S-21b bypass sheet functionality from fire workflow handlers
- **Streamlined Employment Lifecycle**: Focus now exclusively on core resignation processes and dismissal grounds
- **Updated Handler Count**: Reduced from 27 to 25 handlers with simplified fire flow
- **Enhanced Keyboard System**: Maintained entity selection functionality for resignation templates
- **Removed Fire Resignation Category Slot**: Fire category now only supports fire_resignation subcategory

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
This document describes the Employment Lifecycle Management system implemented as a VKontakte chatbot. The system automates core HR tasks across the employee lifecycle: hiring, onboarding, employment termination, vacation requests, payroll questions, sick leave, and probation periods. It provides structured menus, multi-step dialogs, and standardized content templates while maintaining a clean separation between UI, business logic, and domain data. The system focuses exclusively on core HR operations without HR request integration or external communication workflows.

**Updated** The fire workflow has been simplified to focus on core resignation processes, removing FR-6 checklist and S-21b bypass sheet functionality to streamline employment lifecycle management.

## Project Structure
The project follows a layered architecture:
- Domain layer: reusable entities and static content
- Integration layer: VK bot wiring, keyboards, handlers, and state management
- Configuration: environment-driven settings

```mermaid
graph TB
subgraph "Domain Layer"
D1["entities.py<br/>LegalEntity definitions"]
D2["content.py<br/>Static content, templates, errors"]
D3["category_models.py<br/>Category file models"]
end
subgraph "Integration Layer"
I1["bot.py<br/>Bot factory and handler registration"]
I2["keyboards.py<br/>Keyboard builders"]
I3["states.py<br/>FSM state definitions"]
I4["handlers/*<br/>Core HR operations flows"]
I5["rules.py<br/>Custom payload matching rules"]
end
subgraph "Configuration"
C1["config.py<br/>Settings"]
end
D1 --> I4
D2 --> I4
D3 --> I4
I2 --> I4
I3 --> I4
I5 --> I4
I1 --> I4
C1 --> I1
```

**Diagram sources**
- [app/domain/entities.py:1-24](file://app/domain/entities.py#L1-L24)
- [app/domain/content.py:1-129](file://app/domain/content.py#L1-L129)
- [app/storage/category_models.py:1-64](file://app/storage/category_models.py#L1-L64)
- [app/integrations/vk/bot.py:1-56](file://app/integrations/vk/bot.py#L1-L56)
- [app/integrations/vk/keyboards.py:1-263](file://app/integrations/vk/keyboards.py#L1-L263)
- [app/integrations/vk/states.py:1-9](file://app/integrations/vk/states.py#L1-L9)
- [app/integrations/vk/rules.py:1-31](file://app/integrations/vk/rules.py#L1-L31)
- [app/config.py:1-9](file://app/config.py#L1-L9)

**Section sources**
- [app/domain/entities.py:1-24](file://app/domain/entities.py#L1-L24)
- [app/domain/content.py:1-129](file://app/domain/content.py#L1-L129)
- [app/storage/category_models.py:1-64](file://app/storage/category_models.py#L1-L64)
- [app/integrations/vk/bot.py:1-56](file://app/integrations/vk/bot.py#L1-L56)
- [app/integrations/vk/keyboards.py:1-263](file://app/integrations/vk/keyboards.py#L1-L263)
- [app/integrations/vk/states.py:1-9](file://app/integrations/vk/states.py#L1-L9)
- [app/integrations/vk/rules.py:1-31](file://app/integrations/vk/rules.py#L1-L31)
- [app/config.py:1-9](file://app/config.py#L1-L9)

## Core Components
- LegalEntity and entity registry: central identifiers for Russian legal entities used across hiring and vacation flows.
- Static content and templates: standardized messages, checklists, and placeholders for documents and RAG stubs.
- Category file models: structured category and subcategory definitions for document templates including simplified fire resignation support.
- VK bot factory: wires handlers and state dispensation to a vkbottle Bot instance.
- Keyboard builders: reusable keyboards for main menu, entity selection, vacation type selection, and multi-step dialogs.
- Handler modules: feature-specific flows for hire, fire, vacation, pay, sick leave, probation, ask-a-question, and fallback.
- Custom payload rules: specialized matching for complex payload structures.

**Section sources**
- [app/domain/entities.py:8-24](file://app/domain/entities.py#L8-L24)
- [app/domain/content.py:10-129](file://app/domain/content.py#L10-L129)
- [app/storage/category_models.py:32-55](file://app/storage/category_models.py#L32-L55)
- [app/integrations/vk/bot.py:42-56](file://app/integrations/vk/bot.py#L42-L56)
- [app/integrations/vk/keyboards.py:75-263](file://app/integrations/vk/keyboards.py#L75-L263)
- [app/integrations/vk/handlers/hire.py:32-98](file://app/integrations/vk/handlers/hire.py#L32-L98)
- [app/integrations/vk/handlers/fire.py:29-76](file://app/integrations/vk/handlers/fire.py#L29-L76)
- [app/integrations/vk/handlers/vacation.py:30-105](file://app/integrations/vk/handlers/vacation.py#L30-L105)
- [app/integrations/vk/handlers/pay.py:24-46](file://app/integrations/vk/handlers/pay.py#L24-L46)
- [app/integrations/vk/handlers/sections.py:24-35](file://app/integrations/vk/handlers/sections.py#L24-L35)
- [app/integrations/vk/handlers/ask.py:38-90](file://app/integrations/vk/handlers/ask.py#L38-L90)
- [app/integrations/vk/handlers/fallback.py:15-18](file://app/integrations/vk/handlers/fallback.py#L15-L18)
- [app/integrations/vk/rules.py:11-31](file://app/integrations/vk/rules.py#L11-L31)

## Architecture Overview
The system uses a modular handler architecture with explicit ordering and state management:
- Handlers are registered in a specific order to ensure proper matching precedence.
- Multi-step dialogs use a shared state dispenser to persist user context.
- Content is centralized in domain modules to keep handlers thin and maintainable.
- Focus remains on core HR operations without external communication workflows.
- Custom payload rules enable sophisticated matching for complex workflows.

```mermaid
graph TB
A["bot.py<br/>create_bot()"] --> B["handlers/*<br/>Core HR flows"]
B --> C["keyboards.py<br/>Keyboard builders"]
B --> D["domain/content.py<br/>Templates & errors"]
B --> E["domain/entities.py<br/>LegalEntity registry"]
B --> F["states.py<br/>FSM states"]
B --> G["rules.py<br/>Payload matching rules"]
A --> H["config.py<br/>Settings"]
subgraph "Handler Registration Order"
O1["start.py"]
O2["ask.py"]
O3["hire.py / fire.py / vacation.py / pay.py"]
O4["sections.py"]
O5["fallback.py"]
end
A --> O1
A --> O2
A --> O3
A --> O4
A --> O5
```

**Diagram sources**
- [app/integrations/vk/bot.py:42-56](file://app/integrations/vk/bot.py#L42-L56)
- [app/integrations/vk/handlers/start.py:31-42](file://app/integrations/vk/handlers/start.py#L31-L42)
- [app/integrations/vk/handlers/ask.py:38-90](file://app/integrations/vk/handlers/ask.py#L38-L90)
- [app/integrations/vk/handlers/hire.py:32-98](file://app/integrations/vk/handlers/hire.py#L32-L98)
- [app/integrations/vk/handlers/fire.py:29-76](file://app/integrations/vk/handlers/fire.py#L29-L76)
- [app/integrations/vk/handlers/vacation.py:30-105](file://app/integrations/vk/handlers/vacation.py#L30-L105)
- [app/integrations/vk/handlers/pay.py:24-46](file://app/integrations/vk/handlers/pay.py#L24-L46)
- [app/integrations/vk/handlers/sections.py:24-35](file://app/integrations/vk/handlers/sections.py#L24-L35)
- [app/integrations/vk/handlers/fallback.py:15-18](file://app/integrations/vk/handlers/fallback.py#L15-L18)
- [app/integrations/vk/keyboards.py:75-263](file://app/integrations/vk/keyboards.py#L75-L263)
- [app/domain/content.py:10-129](file://app/domain/content.py#L10-L129)
- [app/domain/entities.py:8-24](file://app/domain/entities.py#L8-L24)
- [app/integrations/vk/states.py:4-9](file://app/integrations/vk/states.py#L4-L9)
- [app/integrations/vk/rules.py:11-31](file://app/integrations/vk/rules.py#L11-L31)
- [app/config.py:4-9](file://app/config.py#L4-L9)

## Detailed Component Analysis

### Legal Entities Registry
Centralized definition of legal entities used across hire and vacation flows. Provides both lookup by ID and enumeration for selection UIs.

```mermaid
classDiagram
class LegalEntity {
+int id
+string short_name
+string full_name
}
class EntitiesModule {
+tuple~LegalEntity~ ENTITIES
+dict~int,LegalEntity~ ENTITY_BY_ID
}
EntitiesModule --> LegalEntity : "defines"
```

**Diagram sources**
- [app/domain/entities.py:8-24](file://app/domain/entities.py#L8-L24)

**Section sources**
- [app/domain/entities.py:8-24](file://app/domain/entities.py#L8-L24)

### Static Content and Templates
Centralized content for:
- Hire: document checklists, onboarding checklist, contract template
- Fire: voluntary dismissal template (replaces previous FR-6 checklist and S-21b bypass sheet)
- Vacation: leave application template with vacation type support
- RAG stub: placeholder responses during knowledge base integration
- Error states: document unavailable, no answer, integration required

**Updated** The fire workflow has been simplified to focus on voluntary dismissal templates, removing the previous FR-6 checklist and S-21b bypass sheet functionality.

```mermaid
flowchart TD
Start(["Content Request"]) --> Type{"Content Type?"}
Type --> |Hire Checklist| HC["hire_checklist(entity)"]
Type --> |Onboarding Checklist| OC["onboarding_checklist(entity)"]
Type --> |Contract Template| CT["hire_contract_text(entity)"]
Type --> |Fire Resignation Template| FRT["fire_resignation_template(entity)"]
Type --> |Vacation Template| VT["vacation_template_text(entity, vtype)"]
Type --> |RAG Stub| RS["rag_stub(topic)"]
Type --> |Errors| ER["ERR_* constants"]
HC --> End(["Response"])
OC --> End
CT --> End
FRT --> End
VT --> End
RS --> End
ER --> End
```

**Diagram sources**
- [app/domain/content.py:24-129](file://app/domain/content.py#L24-L129)

**Section sources**
- [app/domain/content.py:10-129](file://app/domain/content.py#L10-L129)

### Category File Models
Structured category and subcategory definitions for document templates including simplified fire resignation support. Defines valid combinations and provides validation functions.

**Updated** The fire category now only supports the fire_resignation subcategory, removing the previous FR-6 checklist and S-21b bypass sheet functionality.

```mermaid
classDiagram
class CategoryFileRecord {
+string file_id
+string category
+string subcategory
+int entity_id
+string filename
+string s3_key
+string mime_type
+int size_bytes
}
class CategorySlots {
+dict CATEGORY_SLOTS
+dict LEGAL_ENTITIES
+is_valid_slot(category, subcategory) bool
}
CategorySlots --> CategoryFileRecord : "validates"
```

**Diagram sources**
- [app/storage/category_models.py:9-64](file://app/storage/category_models.py#L9-L64)

**Section sources**
- [app/storage/category_models.py:32-55](file://app/storage/category_models.py#L32-L55)

### VK Bot Factory and Handler Registration
Creates a vkbottle Bot instance, shares state dispenser with ask handlers, and loads labelers in a strict order to ensure correct matching precedence.

```mermaid
sequenceDiagram
participant App as "Application"
participant BotFactory as "bot.create_bot()"
participant VKBot as "vkbottle.Bot"
participant SD as "state_dispenser"
participant Labelers as "Handlers"
App->>BotFactory : create_bot(Settings)
BotFactory->>VKBot : initialize with token
BotFactory->>SD : share state dispenser
loop Load handlers in order
BotFactory->>Labelers : bot.labeler.load(bl)
end
BotFactory-->>App : Bot instance
```

**Diagram sources**
- [app/integrations/vk/bot.py:42-56](file://app/integrations/vk/bot.py#L42-L56)

**Section sources**
- [app/integrations/vk/bot.py:24-56](file://app/integrations/vk/bot.py#L24-L56)

### Keyboard Builders
Provides reusable keyboards for:
- Main menu with seven sections
- Entity selection for hire, vacation, and fire resignation flows
- Action menus for hire, fire, vacation, pay
- Service row with Back/Home buttons

**Updated** The fire menu keyboard now only includes "Voluntary dismissal" and "Dismissal grounds" options, removing the previous checklist and bypass sheet selections.

```mermaid
classDiagram
class KeyboardBuilders {
+main_menu_kb() Keyboard
+entity_select_kb(cmd, back_payload, extra_payload) Keyboard
+hire_actions_kb(entity_id) Keyboard
+fire_menu_kb() Keyboard
+vacation_menu_kb() Keyboard
+vacation_type_kb() Keyboard
+pay_menu_kb() Keyboard
+with_service_row(kb, back_payload, show_home) Keyboard
}
```

**Diagram sources**
- [app/integrations/vk/keyboards.py:75-263](file://app/integrations/vk/keyboards.py#L75-L263)

**Section sources**
- [app/integrations/vk/keyboards.py:13-263](file://app/integrations/vk/keyboards.py#L13-L263)

### Hiring Flow (S-10, S-11)
End-to-end flow for new hires:
- Select legal entity
- Choose action: checklist, contract template, or onboarding checklist
- Receive templated content with service buttons

```mermaid
sequenceDiagram
participant User as "User"
participant Bot as "VK Bot"
participant Hire as "hire handlers"
participant KB as "keyboards"
participant Content as "domain.content"
User->>Bot : /start or "Hire" button
Bot->>Hire : on_hire()
Hire->>KB : entity_select_kb(hire_entity, back_payload)
KB-->>User : Entity selection keyboard
User->>Hire : Select entity
Hire->>KB : hire_actions_kb(entity_id)
KB-->>User : Action menu keyboard
User->>Hire : Select action
Hire->>Content : hire_checklist/onboarding_checklist/hire_contract_text
Content-->>Hire : Formatted text
Hire-->>User : Content + service buttons
```

**Diagram sources**
- [app/integrations/vk/handlers/hire.py:32-98](file://app/integrations/vk/handlers/hire.py#L32-L98)
- [app/integrations/vk/keyboards.py:126-171](file://app/integrations/vk/keyboards.py#L126-L171)
- [app/domain/content.py:24-73](file://app/domain/content.py#L24-L73)

**Section sources**
- [app/integrations/vk/handlers/hire.py:26-98](file://app/integrations/vk/handlers/hire.py#L26-L98)
- [app/integrations/vk/keyboards.py:126-171](file://app/integrations/vk/keyboards.py#L126-L171)
- [app/domain/content.py:24-73](file://app/domain/content.py#L24-L73)

### Simplified Termination Flow (S-20, S-21b)
Simplified flow for employment termination focusing on core resignation processes:
- Open fire menu with two options: voluntary dismissal and dismissal grounds
- Voluntary dismissal: entity selection → entity-specific template generation
- Dismissal grounds: RAG-powered response

**Updated** The fire workflow has been significantly simplified, removing FR-6 checklist and S-21b bypass sheet functionality to focus exclusively on core resignation processes.

```mermaid
sequenceDiagram
participant User as "User"
participant Bot as "VK Bot"
participant Fire as "fire handlers"
participant KB as "keyboards"
participant CF as "category_file_service"
User->>Bot : "Fire" button
Bot->>Fire : on_fire()
Fire->>KB : fire_menu_kb()
KB-->>User : Fire menu keyboard
User->>Fire : "Voluntary dismissal" option
Fire->>KB : entity_select_kb(fire_resignation_entity, back_payload)
KB-->>User : Entity selection keyboard
User->>Fire : Select entity
Fire->>CF : send_category_document("fire", "fire_resignation", entity_id)
CF-->>User : Entity-specific resignation template
```

**Diagram sources**
- [app/integrations/vk/handlers/fire.py:29-76](file://app/integrations/vk/handlers/fire.py#L29-L76)
- [app/integrations/vk/keyboards.py:179-185](file://app/integrations/vk/keyboards.py#L179-L185)
- [app/storage/category_models.py:42-47](file://app/storage/category_models.py#L42-L47)

**Section sources**
- [app/integrations/vk/handlers/fire.py:29-76](file://app/integrations/vk/handlers/fire.py#L29-L76)
- [app/integrations/vk/keyboards.py:179-185](file://app/integrations/vk/keyboards.py#L179-L185)
- [app/domain/content.py:75-95](file://app/domain/content.py#L75-L95)
- [app/storage/category_models.py:42-47](file://app/storage/category_models.py#L42-L47)

### Enhanced Vacation Flow (S-30)
Enhanced two-step flow for vacation requests:
- Open vacation menu
- Select vacation type (paid/unpaid)
- Select legal entity
- Receive template with type indicator and disclaimer

```mermaid
sequenceDiagram
participant User as "User"
participant Bot as "VK Bot"
participant Vac as "vacation handlers"
participant KB as "keyboards"
participant Content as "domain.content"
User->>Bot : "Vacation" button
Bot->>Vac : on_vacation()
Vac->>KB : vacation_menu_kb()
KB-->>User : Vacation menu keyboard
User->>Vac : "Leave application template"
Vac->>KB : vacation_type_kb()
KB-->>User : Vacation type selection keyboard
User->>Vac : Select vacation type
Vac->>KB : entity_select_kb(vacation_template, back_payload, extra_payload{"vtype" : vtype})
KB-->>User : Entity selection keyboard
User->>Vac : Select entity
Vac->>Content : vacation_template_text(entity, vtype)
Content-->>User : Template text with type indicator and disclaimer
```

**Diagram sources**
- [app/integrations/vk/handlers/vacation.py:30-105](file://app/integrations/vk/handlers/vacation.py#L30-L105)
- [app/integrations/vk/keyboards.py:193-221](file://app/integrations/vk/keyboards.py#L193-L221)
- [app/domain/content.py:96-110](file://app/domain/content.py#L96-L110)

**Section sources**
- [app/integrations/vk/handlers/vacation.py:26-105](file://app/integrations/vk/handlers/vacation.py#L26-L105)
- [app/integrations/vk/keyboards.py:193-221](file://app/integrations/vk/keyboards.py#L193-L221)
- [app/domain/content.py:96-110](file://app/domain/content.py#L96-L110)

### Pay & Bonus Flow (S-40)
Flow for payroll questions:
- Open pay menu
- Choose overtime/weekend pay or bonus conditions (both RAG stubs)

```mermaid
sequenceDiagram
participant User as "User"
participant Bot as "VK Bot"
participant Pay as "pay handlers"
participant Content as "domain.content"
User->>Bot : "Pay" button
Bot->>Pay : on_pay()
Pay-->>User : Pay menu keyboard
User->>Pay : Select topic
Pay-->>User : rag_stub(topic)
```

**Diagram sources**
- [app/integrations/vk/handlers/pay.py:24-46](file://app/integrations/vk/handlers/pay.py#L24-L46)
- [app/integrations/vk/keyboards.py:226-232](file://app/integrations/vk/keyboards.py#L226-L232)

**Section sources**
- [app/integrations/vk/handlers/pay.py:22-46](file://app/integrations/vk/handlers/pay.py#L22-L46)
- [app/integrations/vk/keyboards.py:226-232](file://app/integrations/vk/keyboards.py#L226-L232)

### Sick Leave and Probation Flows (S-50, S-60)
RAG-powered flows for:
- Sick leave/ELN procedures
- Probation period guidance

```mermaid
flowchart TD
S["Sections Entry"] --> SL["Sick/ELN RAG stub"]
S --> PR["Probation RAG stub"]
SL --> End(["Response"])
PR --> End
```

**Diagram sources**
- [app/integrations/vk/handlers/sections.py:24-35](file://app/integrations/vk/handlers/sections.py#L24-L35)

**Section sources**
- [app/integrations/vk/handlers/sections.py:22-35](file://app/integrations/vk/handlers/sections.py#L22-L35)

### Ask-A-Question Flow (Block 4, section 4.4)
- Sets a temporary state to prevent fallback from consuming free text
- Receives free text input and responds with a standardized RAG stub

```mermaid
sequenceDiagram
participant User as "User"
participant Bot as "VK Bot"
participant Ask as "ask handlers"
participant SD as "state_dispenser"
participant Content as "domain.content"
User->>Bot : "Ask" button
Bot->>Ask : on_ask()
Ask->>SD : set ASK_QUESTION
Ask-->>User : Prompt for question + input keyboard
User->>Ask : Free text
Ask->>SD : delete state
Ask-->>User : rag_stub(question)
```

**Diagram sources**
- [app/integrations/vk/handlers/ask.py:38-90](file://app/integrations/vk/handlers/ask.py#L38-L90)
- [app/integrations/vk/states.py:7-9](file://app/integrations/vk/states.py#L7-L9)

**Section sources**
- [app/integrations/vk/handlers/ask.py:23-90](file://app/integrations/vk/handlers/ask.py#L23-L90)
- [app/integrations/vk/states.py:7-9](file://app/integrations/vk/states.py#L7-L9)

### Fallback Handler
Catches any unmatched text input and prompts the user to use menu buttons.

```mermaid
sequenceDiagram
participant User as "User"
participant Bot as "VK Bot"
participant Fallback as "fallback handlers"
User->>Bot : Arbitrary text
Bot->>Fallback : on_fallback()
Fallback-->>User : Prompt + main menu keyboard
```

**Diagram sources**
- [app/integrations/vk/handlers/fallback.py:15-18](file://app/integrations/vk/handlers/fallback.py#L15-L18)
- [app/integrations/vk/keyboards.py:75-112](file://app/integrations/vk/keyboards.py#L75-L112)

**Section sources**
- [app/integrations/vk/handlers/fallback.py:15-18](file://app/integrations/vk/handlers/fallback.py#L15-L18)
- [app/integrations/vk/keyboards.py:75-112](file://app/integrations/vk/keyboards.py#L75-L112)

### Custom Payload Matching Rules
Enables sophisticated payload matching for complex workflows:
- PayloadCmdRule: matches messages with specific command payloads
- Supports extraction of additional payload data for handlers

```mermaid
classDiagram
class PayloadCmdRule {
+str cmd
+check(event) dict|bool
}
PayloadCmdRule --> Message : "matches"
```

**Diagram sources**
- [app/integrations/vk/rules.py:11-31](file://app/integrations/vk/rules.py#L11-L31)

**Section sources**
- [app/integrations/vk/rules.py:11-31](file://app/integrations/vk/rules.py#L11-L31)

## Dependency Analysis
The system exhibits low coupling and high cohesion:
- Handlers depend on domain content and keyboards but remain thin.
- Shared state dispenser enables persistent multi-step dialogs.
- Strict handler registration order prevents unintended message routing.
- Custom payload rules enable sophisticated matching without complex handler logic.

```mermaid
graph TB
H1["handlers/start.py"]
H2["handlers/ask.py"]
H3["handlers/hire.py"]
H4["handlers/fire.py"]
H5["handlers/vacation.py"]
H6["handlers/pay.py"]
H7["handlers/sections.py"]
H8["handlers/fallback.py"]
K["keyboards.py"]
E["entities.py"]
C["content.py"]
S["states.py"]
R["rules.py"]
B["bot.py"]
CFG["config.py"]
CF["category_models.py"]
H1 --> K
H2 --> K
H2 --> S
H3 --> K
H3 --> E
H3 --> C
H4 --> K
H4 --> C
H4 --> CF
H5 --> K
H5 --> E
H5 --> C
H5 --> R
H6 --> K
H6 --> C
H7 --> K
H7 --> C
H8 --> K
B --> H1
B --> H2
B --> H3
B --> H4
B --> H5
B --> H6
B --> H7
B --> H8
B --> S
B --> R
B --> CFG
```

**Diagram sources**
- [app/integrations/vk/bot.py:42-56](file://app/integrations/vk/bot.py#L42-L56)
- [app/integrations/vk/handlers/start.py:31-42](file://app/integrations/vk/handlers/start.py#L31-L42)
- [app/integrations/vk/handlers/ask.py:38-90](file://app/integrations/vk/handlers/ask.py#L38-L90)
- [app/integrations/vk/handlers/hire.py:32-98](file://app/integrations/vk/handlers/hire.py#L32-L98)
- [app/integrations/vk/handlers/fire.py:29-76](file://app/integrations/vk/handlers/fire.py#L29-L76)
- [app/integrations/vk/handlers/vacation.py:30-105](file://app/integrations/vk/handlers/vacation.py#L30-L105)
- [app/integrations/vk/handlers/pay.py:24-46](file://app/integrations/vk/handlers/pay.py#L24-L46)
- [app/integrations/vk/handlers/sections.py:24-35](file://app/integrations/vk/handlers/sections.py#L24-L35)
- [app/integrations/vk/handlers/fallback.py:15-18](file://app/integrations/vk/handlers/fallback.py#L15-L18)
- [app/integrations/vk/keyboards.py:75-263](file://app/integrations/vk/keyboards.py#L75-L263)
- [app/domain/content.py:10-129](file://app/domain/content.py#L10-L129)
- [app/domain/entities.py:8-24](file://app/domain/entities.py#L8-L24)
- [app/integrations/vk/states.py:4-9](file://app/integrations/vk/states.py#L4-L9)
- [app/integrations/vk/rules.py:11-31](file://app/integrations/vk/rules.py#L11-L31)
- [app/config.py:4-9](file://app/config.py#L4-L9)
- [app/storage/category_models.py:32-55](file://app/storage/category_models.py#L32-L55)

**Section sources**
- [app/integrations/vk/bot.py:24-56](file://app/integrations/vk/bot.py#L24-L56)

## Performance Considerations
- Handler registration order ensures efficient routing and avoids unnecessary fallback matching.
- Keyboard building is lightweight and reused across flows to minimize overhead.
- State dispenser is used sparingly and cleared promptly to avoid memory bloat.
- Centralized content reduces duplication and improves cache locality for repeated messages.
- Custom payload rules provide efficient matching without complex handler logic.
- Entity-based document generation eliminates RAG processing overhead for template requests.

**Updated** The simplified fire workflow improves performance by reducing the number of handlers from 27 to 25 and eliminating redundant checklist and bypass sheet processing.

## Troubleshooting Guide
Common issues and resolutions:
- Handler precedence: If a message is not recognized, verify the handler order in the bot factory and ensure fallback is last.
- State persistence: If multi-step dialogs fail, confirm the shared state dispenser is attached to the bot and state transitions occur in the correct order.
- Entity selection: If entity selection fails, verify the payload command and entity ID mapping.
- Vacation type handling: If vacation type selection fails, verify the vacation_type payload structure and extra_payload forwarding.
- Voluntary dismissal flow: If fire resignation template generation fails, verify the entity-specific template exists in category storage and the category_file_service is properly configured.
- Content availability: For document templates, ensure the document storage integration is configured; in the meantime, the system returns a standardized placeholder message.
- Free-text input: For ask-a-question, ensure the state is set before accepting free text to prevent fallback consumption.
- Payload matching: For custom payload rules, ensure the JSON payload structure matches the expected format.

**Updated** The troubleshooting guide now reflects the simplified fire workflow, focusing on voluntary dismissal template generation and dismissal grounds RAG responses.

**Section sources**
- [app/integrations/vk/bot.py:24-56](file://app/integrations/vk/bot.py#L24-L56)
- [app/integrations/vk/handlers/ask.py:51-90](file://app/integrations/vk/handlers/ask.py#L51-L90)
- [app/integrations/vk/handlers/vacation.py:53-68](file://app/integrations/vk/handlers/vacation.py#L53-L68)
- [app/integrations/vk/handlers/fire.py:48-67](file://app/integrations/vk/handlers/fire.py#L48-L67)
- [app/domain/content.py:124-129](file://app/domain/content.py#L124-L129)
- [app/integrations/vk/rules.py:21-31](file://app/integrations/vk/rules.py#L21-L31)

## Conclusion
The Employment Lifecycle Management system provides a robust, extensible foundation for automating core HR-related workflows in a VKontakte chatbot. Its modular design, centralized content, and state-managed dialogs enable clear user experiences while keeping business logic maintainable. The system focuses exclusively on essential HR operations (hiring, firing, vacation, payment, sick leave, probation) without external communication workflows, providing a streamlined and efficient solution for employee lifecycle management.

**Updated** The recent simplification of the fire workflow demonstrates the system's evolution toward greater efficiency and clarity. By removing FR-6 checklist and S-21b bypass sheet functionality, the system now focuses exclusively on core resignation processes, reducing complexity from 27 to 25 handlers while maintaining the technical excellence that characterizes the Employment Lifecycle Management system.

The simplified fire workflow maintains entity-based document generation for voluntary dismissals while preserving the RAG-powered dismissal grounds functionality. This streamlined approach provides users with direct access to essential resignation templates while keeping the system's architecture clean and maintainable. The enhanced keyboard system continues to support entity selection for resignation templates, ensuring users can quickly access the correct template for their specific legal entity.

The reduction in handler count from 27 to 25 represents a significant improvement in system maintainability without sacrificing functionality. The simplified architecture makes the system easier to understand, debug, and extend, while the focused feature set ensures that users receive exactly what they need for employment lifecycle management.