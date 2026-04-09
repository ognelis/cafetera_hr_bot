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
- [app/config.py](file://app/config.py)
</cite>

## Update Summary
**Changes Made**
- Removed HR request workflow documentation completely
- Eliminated multi-step HR request dialog coverage
- Removed HR communication features and state management documentation
- Updated focus to core HR operations only (hiring, firing, vacation, payment, sick leave, probation)
- Removed HR request state management and keyboard builders
- Simplified handler registration order to exclude HR request handlers

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
end
subgraph "Integration Layer"
I1["bot.py<br/>Bot factory and handler registration"]
I2["keyboards.py<br/>Keyboard builders"]
I3["states.py<br/>FSM state definitions"]
I4["handlers/*<br/>Core HR operations flows"]
end
subgraph "Configuration"
C1["config.py<br/>Settings"]
end
D1 --> I4
D2 --> I4
I2 --> I4
I3 --> I4
I1 --> I4
C1 --> I1
```

**Diagram sources**
- [app/domain/entities.py:1-24](file://app/domain/entities.py#L1-L24)
- [app/domain/content.py:1-140](file://app/domain/content.py#L1-L140)
- [app/integrations/vk/bot.py:1-56](file://app/integrations/vk/bot.py#L1-L56)
- [app/integrations/vk/keyboards.py:1-234](file://app/integrations/vk/keyboards.py#L1-L234)
- [app/integrations/vk/states.py:1-9](file://app/integrations/vk/states.py#L1-L9)
- [app/config.py:1-9](file://app/config.py#L1-L9)

**Section sources**
- [app/domain/entities.py:1-24](file://app/domain/entities.py#L1-L24)
- [app/domain/content.py:1-140](file://app/domain/content.py#L1-L140)
- [app/integrations/vk/bot.py:1-56](file://app/integrations/vk/bot.py#L1-L56)
- [app/integrations/vk/keyboards.py:1-234](file://app/integrations/vk/keyboards.py#L1-L234)
- [app/integrations/vk/states.py:1-9](file://app/integrations/vk/states.py#L1-L9)
- [app/config.py:1-9](file://app/config.py#L1-L9)

## Core Components
- LegalEntity and entity registry: central identifiers for Russian legal entities used across hiring and vacation flows.
- Static content and templates: standardized messages, checklists, and placeholders for documents and RAG stubs.
- VK bot factory: wires handlers and state dispensation to a vkbottle Bot instance.
- Keyboard builders: reusable keyboards for main menu, entity selection, and multi-step dialogs.
- Handler modules: feature-specific flows for hire, fire, vacation, pay, sick leave, probation, ask-a-question, and fallback.

**Section sources**
- [app/domain/entities.py:8-24](file://app/domain/entities.py#L8-L24)
- [app/domain/content.py:10-140](file://app/domain/content.py#L10-L140)
- [app/integrations/vk/bot.py:42-56](file://app/integrations/vk/bot.py#L42-L56)
- [app/integrations/vk/keyboards.py:75-234](file://app/integrations/vk/keyboards.py#L75-L234)
- [app/integrations/vk/handlers/hire.py:32-98](file://app/integrations/vk/handlers/hire.py#L32-L98)
- [app/integrations/vk/handlers/fire.py:28-74](file://app/integrations/vk/handlers/fire.py#L28-L74)
- [app/integrations/vk/handlers/vacation.py:30-80](file://app/integrations/vk/handlers/vacation.py#L30-L80)
- [app/integrations/vk/handlers/pay.py:24-46](file://app/integrations/vk/handlers/pay.py#L24-L46)
- [app/integrations/vk/handlers/sections.py:24-35](file://app/integrations/vk/handlers/sections.py#L24-L35)
- [app/integrations/vk/handlers/ask.py:38-90](file://app/integrations/vk/handlers/ask.py#L38-L90)
- [app/integrations/vk/handlers/fallback.py:15-18](file://app/integrations/vk/handlers/fallback.py#L15-L18)

## Architecture Overview
The system uses a modular handler architecture with explicit ordering and state management:
- Handlers are registered in a specific order to ensure proper matching precedence.
- Multi-step dialogs use a shared state dispenser to persist user context.
- Content is centralized in domain modules to keep handlers thin and maintainable.
- Focus remains on core HR operations without external communication workflows.

```mermaid
graph TB
A["bot.py<br/>create_bot()"] --> B["handlers/*<br/>Core HR flows"]
B --> C["keyboards.py<br/>Keyboard builders"]
B --> D["domain/content.py<br/>Templates & errors"]
B --> E["domain/entities.py<br/>LegalEntity registry"]
B --> F["states.py<br/>FSM states"]
A --> G["config.py<br/>Settings"]
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
- [app/integrations/vk/handlers/fire.py:28-74](file://app/integrations/vk/handlers/fire.py#L28-L74)
- [app/integrations/vk/handlers/vacation.py:30-80](file://app/integrations/vk/handlers/vacation.py#L30-L80)
- [app/integrations/vk/handlers/pay.py:24-46](file://app/integrations/vk/handlers/pay.py#L24-L46)
- [app/integrations/vk/handlers/sections.py:24-35](file://app/integrations/vk/handlers/sections.py#L24-L35)
- [app/integrations/vk/handlers/fallback.py:15-18](file://app/integrations/vk/handlers/fallback.py#L15-L18)
- [app/integrations/vk/keyboards.py:75-234](file://app/integrations/vk/keyboards.py#L75-L234)
- [app/domain/content.py:10-140](file://app/domain/content.py#L10-L140)
- [app/domain/entities.py:8-24](file://app/domain/entities.py#L8-L24)
- [app/integrations/vk/states.py:4-9](file://app/integrations/vk/states.py#L4-L9)
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
- Fire: last-day checklist, bypass sheet text
- Vacation: leave application template
- RAG stub: placeholder responses during knowledge base integration
- Error states: document unavailable, no answer, integration required

```mermaid
flowchart TD
Start(["Content Request"]) --> Type{"Content Type?"}
Type --> |Hire Checklist| HC["hire_checklist(entity)"]
Type --> |Onboarding Checklist| OC["onboarding_checklist(entity)"]
Type --> |Contract Template| CT["hire_contract_text(entity)"]
Type --> |Fire Last Day| FL["FIRE_LAST_DAY_CHECKLIST"]
Type --> |Fire Bypass Sheet| FB["FIRE_BYPASS_SHEET_TEXT"]
Type --> |Vacation Template| VT["vacation_template_text(entity)"]
Type --> |RAG Stub| RS["rag_stub(topic)"]
Type --> |Errors| ER["ERR_* constants"]
HC --> End(["Response"])
OC --> End
CT --> End
FL --> End
FB --> End
VT --> End
RS --> End
ER --> End
```

**Diagram sources**
- [app/domain/content.py:24-140](file://app/domain/content.py#L24-L140)

**Section sources**
- [app/domain/content.py:10-140](file://app/domain/content.py#L10-L140)

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
- Entity selection for hire and vacation
- Action menus for hire, fire, vacation, pay
- Service row with Back/Home buttons

```mermaid
classDiagram
class KeyboardBuilders {
+main_menu_kb() Keyboard
+entity_select_kb(cmd, back_payload) Keyboard
+hire_actions_kb(entity_id) Keyboard
+fire_menu_kb() Keyboard
+vacation_menu_kb() Keyboard
+pay_menu_kb() Keyboard
+with_service_row(kb, back_payload, show_home) Keyboard
}
```

**Diagram sources**
- [app/integrations/vk/keyboards.py:75-234](file://app/integrations/vk/keyboards.py#L75-L234)

**Section sources**
- [app/integrations/vk/keyboards.py:13-234](file://app/integrations/vk/keyboards.py#L13-L234)

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
- [app/integrations/vk/keyboards.py:126-160](file://app/integrations/vk/keyboards.py#L126-L160)
- [app/domain/content.py:24-73](file://app/domain/content.py#L24-L73)

**Section sources**
- [app/integrations/vk/handlers/hire.py:26-98](file://app/integrations/vk/handlers/hire.py#L26-L98)
- [app/integrations/vk/keyboards.py:126-160](file://app/integrations/vk/keyboards.py#L126-L160)
- [app/domain/content.py:24-73](file://app/domain/content.py#L24-L73)

### Termination Flow (S-20, S-21b)
Flow for employment termination:
- Open fire menu
- Choose last-day checklist, bypass sheet, voluntary dismissal (RAG stub), or dismissal grounds

```mermaid
sequenceDiagram
participant User as "User"
participant Bot as "VK Bot"
participant Fire as "fire handlers"
participant KB as "keyboards"
participant Content as "domain.content"
User->>Bot : "Fire" button
Bot->>Fire : on_fire()
Fire->>KB : fire_menu_kb()
KB-->>User : Fire menu keyboard
User->>Fire : Select option
alt Checklist
Fire-->>User : FIRE_LAST_DAY_CHECKLIST
else Bypass sheet
Fire-->>User : FIRE_BYPASS_SHEET_TEXT
else Voluntary dismissal
Fire-->>User : rag_stub("Увольнение по собственному желанию")
end
```

**Diagram sources**
- [app/integrations/vk/handlers/fire.py:28-74](file://app/integrations/vk/handlers/fire.py#L28-L74)
- [app/integrations/vk/keyboards.py:165-176](file://app/integrations/vk/keyboards.py#L165-L176)
- [app/domain/content.py:75-95](file://app/domain/content.py#L75-L95)

**Section sources**
- [app/integrations/vk/handlers/fire.py:24-74](file://app/integrations/vk/handlers/fire.py#L24-L74)
- [app/integrations/vk/keyboards.py:165-176](file://app/integrations/vk/keyboards.py#L165-L176)
- [app/domain/content.py:75-95](file://app/domain/content.py#L75-L95)

### Vacation Flow (S-30)
Partial flow for vacation:
- Open vacation menu
- Select leave application template (requires entity selection)
- Receive disclaimer and template stub
- Other vacation-related RAG stubs (procedure, schedule) are placeholders

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
Vac->>KB : entity_select_kb(vacation_template, back_payload)
KB-->>User : Entity selection keyboard
User->>Vac : Select entity
Vac->>Content : vacation_template_text(entity)
Content-->>User : Template text with disclaimer
```

**Diagram sources**
- [app/integrations/vk/handlers/vacation.py:30-80](file://app/integrations/vk/handlers/vacation.py#L30-L80)
- [app/integrations/vk/keyboards.py:181-190](file://app/integrations/vk/keyboards.py#L181-L190)
- [app/domain/content.py:96-105](file://app/domain/content.py#L96-L105)

**Section sources**
- [app/integrations/vk/handlers/vacation.py:26-80](file://app/integrations/vk/handlers/vacation.py#L26-L80)
- [app/integrations/vk/keyboards.py:181-190](file://app/integrations/vk/keyboards.py#L181-L190)
- [app/domain/content.py:96-105](file://app/domain/content.py#L96-L105)

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
- [app/integrations/vk/keyboards.py:195-202](file://app/integrations/vk/keyboards.py#L195-L202)

**Section sources**
- [app/integrations/vk/handlers/pay.py:22-46](file://app/integrations/vk/handlers/pay.py#L22-L46)
- [app/integrations/vk/keyboards.py:195-202](file://app/integrations/vk/keyboards.py#L195-L202)

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

## Dependency Analysis
The system exhibits low coupling and high cohesion:
- Handlers depend on domain content and keyboards but remain thin.
- Shared state dispenser enables persistent multi-step dialogs.
- Strict handler registration order prevents unintended message routing.

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
B["bot.py"]
CFG["config.py"]
H1 --> K
H2 --> K
H2 --> S
H3 --> K
H3 --> E
H3 --> C
H4 --> K
H4 --> C
H5 --> K
H5 --> E
H5 --> C
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
B --> CFG
```

**Diagram sources**
- [app/integrations/vk/bot.py:42-56](file://app/integrations/vk/bot.py#L42-L56)
- [app/integrations/vk/handlers/start.py:31-42](file://app/integrations/vk/handlers/start.py#L31-L42)
- [app/integrations/vk/handlers/ask.py:38-90](file://app/integrations/vk/handlers/ask.py#L38-L90)
- [app/integrations/vk/handlers/hire.py:32-98](file://app/integrations/vk/handlers/hire.py#L32-L98)
- [app/integrations/vk/handlers/fire.py:28-74](file://app/integrations/vk/handlers/fire.py#L28-L74)
- [app/integrations/vk/handlers/vacation.py:30-80](file://app/integrations/vk/handlers/vacation.py#L30-L80)
- [app/integrations/vk/handlers/pay.py:24-46](file://app/integrations/vk/handlers/pay.py#L24-L46)
- [app/integrations/vk/handlers/sections.py:24-35](file://app/integrations/vk/handlers/sections.py#L24-L35)
- [app/integrations/vk/handlers/fallback.py:15-18](file://app/integrations/vk/handlers/fallback.py#L15-L18)
- [app/integrations/vk/keyboards.py:75-234](file://app/integrations/vk/keyboards.py#L75-L234)
- [app/domain/content.py:10-140](file://app/domain/content.py#L10-L140)
- [app/domain/entities.py:8-24](file://app/domain/entities.py#L8-L24)
- [app/integrations/vk/states.py:4-9](file://app/integrations/vk/states.py#L4-L9)
- [app/config.py:4-9](file://app/config.py#L4-L9)

**Section sources**
- [app/integrations/vk/bot.py:24-56](file://app/integrations/vk/bot.py#L24-L56)

## Performance Considerations
- Handler registration order ensures efficient routing and avoids unnecessary fallback matching.
- Keyboard building is lightweight and reused across flows to minimize overhead.
- State dispenser is used sparingly and cleared promptly to avoid memory bloat.
- Centralized content reduces duplication and improves cache locality for repeated messages.

## Troubleshooting Guide
Common issues and resolutions:
- Handler precedence: If a message is not recognized, verify the handler order in the bot factory and ensure fallback is last.
- State persistence: If multi-step dialogs fail, confirm the shared state dispenser is attached to the bot and state transitions occur in the correct order.
- Entity selection: If entity selection fails, verify the payload command and entity ID mapping.
- Content availability: For document templates, ensure the document storage integration is configured; in the meantime, the system returns a standardized placeholder message.
- Free-text input: For ask-a-question, ensure the state is set before accepting free text to prevent fallback consumption.

**Section sources**
- [app/integrations/vk/bot.py:24-56](file://app/integrations/vk/bot.py#L24-L56)
- [app/integrations/vk/handlers/ask.py:51-90](file://app/integrations/vk/handlers/ask.py#L51-L90)
- [app/domain/content.py:124-140](file://app/domain/content.py#L124-L140)

## Conclusion
The Employment Lifecycle Management system provides a robust, extensible foundation for automating core HR-related workflows in a VKontakte chatbot. Its modular design, centralized content, and state-managed dialogs enable clear user experiences while keeping business logic maintainable. The system focuses exclusively on essential HR operations (hiring, firing, vacation, payment, sick leave, probation) without external communication workflows, providing a streamlined and efficient solution for employee lifecycle management.