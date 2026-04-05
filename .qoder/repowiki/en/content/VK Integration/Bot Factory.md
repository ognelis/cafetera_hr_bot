# Bot Factory

<cite>
**Referenced Files in This Document**
- [bot.py](file://app/integrations/vk/bot.py)
- [config.py](file://app/config.py)
- [start.py](file://app/integrations/vk/handlers/start.py)
- [sections.py](file://app/integrations/vk/handlers/sections.py)
- [fallback.py](file://app/integrations/vk/handlers/fallback.py)
- [keyboards.py](file://app/integrations/vk/keyboards.py)
- [states.py](file://app/integrations/vk/states.py)
- [polling_vk.py](file://scripts/polling_vk.py)
- [test_bot_factory.py](file://tests/test_bot_factory.py)
- [pyproject.toml](file://pyproject.toml)
</cite>

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
10. [Appendices](#appendices)

## Introduction
This document explains the VK bot factory implementation that creates a fully wired vkbottle Bot instance with all handlers registered. It covers the factory pattern, handler registration mechanism, the critical importance of handler ordering, the create_bot function’s parameters and return value, and practical guidance for extending the bot with new handlers, customizing behavior, centralized configuration via Settings, logging integration, error handling patterns, and testing strategies.

## Project Structure
The VK integration is organized around a factory that wires a Bot instance with a set of labeled handlers. Handlers are grouped by feature and exposed as BotLabeler instances. The factory centralizes configuration and handler loading.

```mermaid
graph TB
subgraph "VK Integration"
BOT["bot.py<br/>create_bot(settings)"]
HANDLERS["Handlers<br/>start.py, sections.py, fallback.py"]
KEYBOARDS["keyboards.py<br/>keyboard builders"]
STATES["states.py<br/>BotStates"]
end
CONFIG["config.py<br/>Settings"]
BOT --> HANDLERS
BOT --> KEYBOARDS
BOT --> STATES
BOT --> CONFIG
```

**Diagram sources**
- [bot.py:1-32](file://app/integrations/vk/bot.py#L1-L32)
- [config.py:1-9](file://app/config.py#L1-L9)
- [start.py:1-55](file://app/integrations/vk/handlers/start.py#L1-L55)
- [sections.py:1-82](file://app/integrations/vk/handlers/sections.py#L1-L82)
- [fallback.py:1-18](file://app/integrations/vk/handlers/fallback.py#L1-L18)
- [keyboards.py:1-108](file://app/integrations/vk/keyboards.py#L1-L108)
- [states.py:1-14](file://app/integrations/vk/states.py#L1-L14)

**Section sources**
- [bot.py:1-32](file://app/integrations/vk/bot.py#L1-L32)
- [config.py:1-9](file://app/config.py#L1-L9)

## Core Components
- Bot factory: create_bot(settings) constructs a Bot and registers handlers in a fixed order.
- Handler labelers: Each handler module exports a BotLabeler instance (bl) with decorated message handlers.
- Centralized configuration: Settings holds VK credentials and group ID.
- Keyboard builders: Shared keyboard construction utilities used by handlers.
- States: A state group for multi-step dialogs.

Key responsibilities:
- create_bot(settings): Creates a Bot, loads labelers, logs creation, and returns the instance.
- Settings: Provides VK access token and group ID from environment.
- Handlers: Define message routes and responses using BotLabeler decorators.
- Keyboards: Provide reusable keyboard layouts and service rows.
- States: Define state names for multi-step flows.

**Section sources**
- [bot.py:23-31](file://app/integrations/vk/bot.py#L23-L31)
- [config.py:4-9](file://app/config.py#L4-L9)
- [start.py:12](file://app/integrations/vk/handlers/start.py#L12)
- [sections.py:17](file://app/integrations/vk/handlers/sections.py#L17)
- [fallback.py:7](file://app/integrations/vk/handlers/fallback.py#L7)
- [keyboards.py:11-108](file://app/integrations/vk/keyboards.py#L11-L108)
- [states.py:4-14](file://app/integrations/vk/states.py#L4-L14)

## Architecture Overview
The factory pattern encapsulates Bot creation and wiring. The create_bot function:
- Initializes a Bot with the VK access token from Settings.
- Iterates through a predefined list of BotLabeler instances and loads them into the bot’s labeler.
- Logs successful creation and returns the configured Bot.

```mermaid
sequenceDiagram
participant Script as "polling_vk.py"
participant Factory as "bot.create_bot"
participant Config as "Settings"
participant Bot as "vkbottle.Bot"
participant Labeler as "BotLabeler"
Script->>Config : Load settings
Script->>Factory : create_bot(settings)
Factory->>Bot : Construct with token
loop Load handlers
Factory->>Labeler : Iterate _HANDLER_LABELERS
Factory->>Bot : labeler.load(labeler)
end
Factory-->>Script : Return Bot
Script->>Bot : run_polling()
```

**Diagram sources**
- [polling_vk.py:24-28](file://scripts/polling_vk.py#L24-L28)
- [bot.py:23-31](file://app/integrations/vk/bot.py#L23-L31)
- [config.py:4-9](file://app/config.py#L4-L9)

**Section sources**
- [bot.py:14-31](file://app/integrations/vk/bot.py#L14-L31)
- [polling_vk.py:24-28](file://scripts/polling_vk.py#L24-L28)

## Detailed Component Analysis

### Bot Factory: create_bot
Purpose:
- Build a fully configured vkbottle Bot instance.
- Centralize token provisioning and handler registration.

Parameters:
- settings: app.config.Settings containing vk_access_token and vk_group_id.

Processing logic:
- Construct Bot with token from settings.
- Iterate over _HANDLER_LABELERS and load each labeler into bot.labeler.
- Log the number of loaded labelers.
- Return the configured Bot.

Return value:
- vkbottle.Bot instance ready for polling or callbacks.

Important note:
- The order of _HANDLER_LABELERS is critical because vkbottle evaluates handlers top-to-bottom. The fallback labeler must be last to avoid intercepting messages intended for earlier handlers.

```mermaid
flowchart TD
Start(["create_bot(settings)"]) --> Init["Initialize Bot with token"]
Init --> Loop["Iterate _HANDLER_LABELERS"]
Loop --> Load["bot.labeler.load(labeler)"]
Load --> Next{"More labelers?"}
Next --> |Yes| Loop
Next --> |No| Log["Log number of loaded labelers"]
Log --> Return["Return Bot"]
```

**Diagram sources**
- [bot.py:23-31](file://app/integrations/vk/bot.py#L23-L31)

**Section sources**
- [bot.py:23-31](file://app/integrations/vk/bot.py#L23-L31)

### Handler Registration Mechanism
Each handler module defines a BotLabeler instance (bl) and registers message handlers using decorators. The factory loads these labelers in a fixed order.

- start.py: Registers greeting, home navigation, and contact HR handlers.
- sections.py: Registers section entry-point handlers (placeholders).
- fallback.py: Registers a catch-all handler for unmatched messages.

```mermaid
classDiagram
class BotLabeler {
+message(...)
+message(...)
+message(...)
}
class StartHandlers {
+on_start(message)
+on_home(message)
+on_contact_hr(message)
}
class SectionsHandlers {
+on_hire(message)
+on_fire(message)
+on_vacation(message)
+on_pay(message)
+on_sick(message)
+on_probation(message)
+on_ask(message)
}
class FallbackHandlers {
+on_fallback(message)
}
BotLabeler <|-- StartHandlers
BotLabeler <|-- SectionsHandlers
BotLabeler <|-- FallbackHandlers
```

**Diagram sources**
- [start.py:12](file://app/integrations/vk/handlers/start.py#L12)
- [sections.py:17](file://app/integrations/vk/handlers/sections.py#L17)
- [fallback.py:7](file://app/integrations/vk/handlers/fallback.py#L7)

**Section sources**
- [start.py:12](file://app/integrations/vk/handlers/start.py#L12)
- [sections.py:17](file://app/integrations/vk/handlers/sections.py#L17)
- [fallback.py:7](file://app/integrations/vk/handlers/fallback.py#L7)

### Handler Ordering and Its Importance
The factory maintains a strict order for handler labelers:
- start.bl (first)
- sections.bl (middle)
- fallback.bl (last)

Why this matters:
- vkbottle checks handlers top-to-bottom.
- If fallback were loaded earlier, it would match all messages and prevent more specific handlers from firing.

Validation in tests ensures:
- Fallback is last.
- Start is first.
- Sections appear before fallback.

**Section sources**
- [bot.py:14-20](file://app/integrations/vk/bot.py#L14-L20)
- [test_bot_factory.py:8-21](file://tests/test_bot_factory.py#L8-L21)

### Centralized Configuration with Settings
Settings provides:
- vk_access_token: Used by create_bot to initialize the Bot.
- vk_group_id: Available for future use (e.g., group-specific logic).

Environment binding:
- Settings reads from .env via pydantic-settings.

**Section sources**
- [config.py:4-9](file://app/config.py#L4-L9)
- [bot.py:25](file://app/integrations/vk/bot.py#L25)

### Logging Integration
Logging behavior:
- The factory logs a message upon successful creation and number of loaded labelers.
- Development entry-point sets up basic logging configuration.

**Section sources**
- [bot.py:12](file://app/integrations/vk/bot.py#L12)
- [bot.py:30](file://app/integrations/vk/bot.py#L30)
- [polling_vk.py:17-21](file://scripts/polling_vk.py#L17-L21)

### Error Handling Patterns
Current implementation:
- No explicit try/catch blocks in the factory.
- Tests validate token forwarding and handler counts, indirectly asserting robustness.

Recommended patterns (conceptual):
- Wrap bot initialization and labeler loading in try/except.
- Log initialization failures and re-raise or return None with structured error info.
- Validate settings presence before creating the Bot.

[No sources needed since this section provides general guidance]

### Practical Examples

#### Extending the bot with a new handler
Steps:
1. Create a new handler module under app/integrations/vk/handlers/ with a BotLabeler instance and decorated handlers.
2. Export bl from the module.
3. Add the new bl to _HANDLER_LABELERS in the correct position (before fallback).
4. Run tests to confirm ordering and handler count.

Example references:
- New handler module: [new_handler.py](file://app/integrations/vk/handlers/new_handler.py)
- Updated labelers list: [bot.py:16-20](file://app/integrations/vk/bot.py#L16-L20)

#### Modifying the handler loading sequence
- Adjust the order in _HANDLER_LABELERS to change precedence.
- Ensure fallback remains last.
- Verify tests pass to maintain correctness.

Example references:
- Labelers list: [bot.py:16-20](file://app/integrations/vk/bot.py#L16-L20)
- Tests enforcing order: [test_bot_factory.py:8-21](file://tests/test_bot_factory.py#L8-L21)

#### Customizing bot behavior
- Add or modify keyboard builders in keyboards.py to change UI behavior.
- Introduce new states in states.py for multi-step flows.
- Update Settings to support new configuration keys.

Example references:
- Keyboard builders: [keyboards.py:29-108](file://app/integrations/vk/keyboards.py#L29-L108)
- States: [states.py:4-14](file://app/integrations/vk/states.py#L4-L14)
- Settings: [config.py:4-9](file://app/config.py#L4-L9)

### Testing the Bot Factory and Validating Handler Registration
Test coverage includes:
- Handler labeler order enforcement.
- Bot instance creation and token forwarding.
- Total handler count verification.

```mermaid
sequenceDiagram
participant Test as "test_bot_factory.py"
participant Factory as "create_bot"
participant Bot as "vkbottle.Bot"
Test->>Factory : create_bot(Settings)
Factory-->>Test : Bot instance
Test->>Bot : Inspect labeler.message_view.handlers
Test-->>Test : Assert handler count equals 11
Test-->>Test : Assert token forwarded
```

**Diagram sources**
- [test_bot_factory.py:23-44](file://tests/test_bot_factory.py#L23-L44)
- [bot.py:23-31](file://app/integrations/vk/bot.py#L23-L31)

**Section sources**
- [test_bot_factory.py:8-44](file://tests/test_bot_factory.py#L8-L44)

## Dependency Analysis
External dependencies:
- vkbottle: Provides Bot and BotLabeler.
- pydantic-settings: Provides Settings with env_file binding.

Internal dependencies:
- bot.py depends on Settings and handler labelers.
- Handlers depend on keyboards and BotLabeler.
- polling script depends on bot factory and Settings.

```mermaid
graph LR
PY["pyproject.toml<br/>dependencies"] --> VK["vkbottle"]
PY --> PS["pydantic-settings"]
BOT["bot.py"] --> VK
BOT --> CFG["config.py"]
BOT --> START["start.py"]
BOT --> SECT["sections.py"]
BOT --> FALL["fallback.py"]
START --> KBD["keyboards.py"]
SECT --> KBD
FALL --> KBD
POLL["polling_vk.py"] --> BOT
POLL --> CFG
```

**Diagram sources**
- [pyproject.toml:7-21](file://pyproject.toml#L7-L21)
- [bot.py:7-10](file://app/integrations/vk/bot.py#L7-L10)
- [config.py:1](file://app/config.py#L1)
- [start.py:3](file://app/integrations/vk/handlers/start.py#L3)
- [sections.py:3](file://app/integrations/vk/handlers/sections.py#L3)
- [fallback.py:3](file://app/integrations/vk/handlers/fallback.py#L3)
- [keyboards.py:9](file://app/integrations/vk/keyboards.py#L9)
- [polling_vk.py:14-15](file://scripts/polling_vk.py#L14-L15)

**Section sources**
- [pyproject.toml:7-21](file://pyproject.toml#L7-L21)
- [bot.py:7-10](file://app/integrations/vk/bot.py#L7-L10)

## Performance Considerations
- Handler registration cost: Minimal overhead; executed once during bot creation.
- Token provisioning: One-time operation; ensure settings are cached if reused frequently.
- Logging: Low overhead; consider async logging for high-throughput scenarios.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and resolutions:
- Incorrect handler order: Ensure fallback is last; verify tests enforce ordering.
- Missing handlers: Confirm all bl instances are included in _HANDLER_LABELERS.
- Token errors: Validate vk_access_token in Settings; tests assert token forwarding.
- Keyboard inconsistencies: Review keyboards.py builders and payload constants.

Validation steps:
- Run tests to confirm handler count and ordering.
- Manually test long-poll mode via polling script.

**Section sources**
- [test_bot_factory.py:8-44](file://tests/test_bot_factory.py#L8-L44)
- [polling_vk.py:24-28](file://scripts/polling_vk.py#L24-L28)

## Conclusion
The VK bot factory cleanly applies the factory pattern to construct a configured Bot with a deterministic handler loading sequence. Centralized configuration via Settings and shared keyboard utilities promote maintainability. Strict handler ordering ensures predictable routing, validated by tests. The design supports easy extension with new handlers and customization while preserving reliability and testability.

## Appendices

### API Summary
- create_bot(settings: Settings) -> Bot
  - Constructs a Bot with token from settings.
  - Loads labelers in a fixed order.
  - Returns the configured Bot.

**Section sources**
- [bot.py:23-31](file://app/integrations/vk/bot.py#L23-L31)

### Example References
- Factory usage in development: [polling_vk.py:24-28](file://scripts/polling_vk.py#L24-L28)
- Handler modules: [start.py:1-55](file://app/integrations/vk/handlers/start.py#L1-L55), [sections.py:1-82](file://app/integrations/vk/handlers/sections.py#L1-L82), [fallback.py:1-18](file://app/integrations/vk/handlers/fallback.py#L1-L18)
- Keyboard builders: [keyboards.py:1-108](file://app/integrations/vk/keyboards.py#L1-L108)
- States: [states.py:1-14](file://app/integrations/vk/states.py#L1-L14)
- Configuration: [config.py:1-9](file://app/config.py#L1-L9)