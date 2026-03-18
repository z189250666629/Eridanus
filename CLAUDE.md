# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Workspace Layout

- Active app root: `Eridanus/`
- Python entry point: `Eridanus/main.py`
- Frontend source is not stored here; `Eridanus/web/` contains the Python WebUI backend plus compiled static assets from a separate repo
- The workspace root (`new_Eridanus/`) contains `archive/` with historical docs and non-runtime artifacts — not part of the running app

## Project Overview

Eridanus is a multi-function QQ bot framework based on the OneBot v11 protocol. It connects via WebSocket and provides AI chat, image generation, media streaming, and other features through a plugin system.

- Language: Python 3.11+
- Runtime: primarily `asyncio`, with a threaded WebUI (Flask) and thread-pool plugin bootstrap
- License: CC BY-NC-SA 4.0 (non-commercial)
- Migration from legacy layout is complete — `Eridanus/` is the sole app root

## Running

```bash
python Eridanus/install.py --profile all
python Eridanus/main.py
```

Prerequisites:
- A OneBot v11 implementation must already be running and exposed over WebSocket
- Default WS address: `ws://127.0.0.1:3001` (configure in `Eridanus/config/basic_config.yaml` under `adapter.ws_client.ws_link`)
- WebUI: `http://localhost:5007`, credentials `eridanus / eridanus`

### Dependency Installation

```bash
# Full install
python Eridanus/install.py --profile all

# Minimum runnable set
python Eridanus/install.py --profile base --profile web --profile adapter-onebot --plugin basic_plugin

# Single plugin
python Eridanus/install.py --plugin ai_llm

# Windows wrapper
Eridanus/install.bat --profile all
```

Profiles map to `Eridanus/requirements/<profile>.txt` (`base`, `web`, `adapter-onebot`, `legacy-compat`, `all`). Plugins with their own deps have `Eridanus/plugins/<name>/requirements.txt`.

No `pyproject.toml` or `setup.py` exists — all dependency management goes through `install.py` + requirements files.

## Testing

No standard test suite. Only ad hoc `test.py` files exist in a few directories. There is no pytest config, no test runner, and no single canonical test command.

## Architecture

```text
Eridanus/main.py             # StandaloneRuntime: config → plugins → event loop
├── adapters/                 # OneBot protocol adapters and transport
│   └── onebot/               # Primary impl (websocket_bot, api_client, event_factory, etc.)
├── core/                     # Platform-agnostic core
│   ├── bot/                  # Bot, ExtendBot, EventBus, PluginManager, func_map
│   ├── config/               # YAMLManager (singleton, file-watching, hot-reload), constants
│   ├── event/                # Pydantic event models, EventFactory
│   ├── message/              # Message components (Text, Image, Node, At, etc.)
│   ├── filter/               # BlacklistFilter, FilterChain
│   ├── database/             # SQLite + Redis helpers
│   ├── services/             # ServiceRegistry singleton for cross-plugin service lookup
│   └── toolkit/              # Logger, installer, async HTTP, image utils, etc.
├── plugins/                  # ~22 runtime plugins
├── web/                      # Flask WebUI backend + compiled React frontend in dist/
└── requirements/             # Split dependency manifests
```

### Three Runtime Modes

`StandaloneRuntime` in `main.py` selects one of:

1. **Dual-bot** (`DualBotManager`) — when WebUI bot2 is active
2. **New core runtime** (`Bot` + `OneBotAdapter`) — when `adapter.use_new_core_bot: true` in config
3. **Legacy single-bot** (`ExtendBot._connect_and_run()`) — the default

### Bot Class Hierarchy

- `WebSocketBot` (`adapters/onebot/websocket_bot.py`) — owns EventBus, WebSocket session, ~40 OneBot API methods
- `ExtendBot` (`core/bot/extend_bot.py`) — subclasses WebSocketBot, adds blacklist/whitelist filtering via FilterChain, normalizes outbound messages per adapter type
- `Bot` (`core/bot/bot.py`) — thin composition of PlatformAdapter + FilterChain + EventBus (new architecture)

### Event Flow

1. WebSocket adapter receives raw OneBot JSON payloads
2. `EventFactory` (`core/event/factory.py`) creates typed Pydantic event objects
3. `ExtendBot` applies FilterChain and dispatches via `EventBus.emit()` (handlers run as `asyncio.create_task()` — non-blocking)
4. Handlers registered via `@bot.on(EventType)` run (with optional slow-handler monitoring)
5. Some plugins expose `call_*` functions through the LLM tool func-map path

### Configuration

`YAMLManager` (`core/config/manager.py`) is a singleton that:
- Loads all YAML from `config/` and `plugins/*/config.yaml` in parallel via ThreadPoolExecutor
- File-watches with debounced hot-reload via `watchdog`
- Config path resolution has a fallback chain defined in `core/config/constants.py`: app-local `Eridanus/config/` → repo-level `config/` → relative `config/`

Access patterns:
```python
config.common_config.basic_config["adapter"]["ws_client"]["ws_link"]
config.basic_plugin.config["key"]
```

Key config files:
- `Eridanus/config/basic_config.yaml` — primary runtime config (adapter, WebUI, plugin loading strategy, handler monitoring, Redis, master ID)
- `Eridanus/config/menu.yaml` — help menu content
- `Eridanus/config/censor_group.yaml` / `censor_user.yaml` — blacklist/whitelist

### Plugin System

Each plugin lives in `Eridanus/plugins/<plugin_name>/` with an `__init__.py`. Two registration patterns exist:

**Pattern 1: Event-driven** — `main(bot, config)` in any `.py` file (not `__init__.py`) registers handlers via `@bot.on(EventType)`. The plugin loader calls `main(bot, config)`, not `main(bot, event, config)`.

**Pattern 2: Service registry** — `register_services(registry, provider, **kwargs)` and `unregister_services(...)` in `__init__.py` register callables into a `ServiceRegistry`. Used by plugins like `ai_llm` and `basic_plugin`.

Optional `__init__.py` metadata fields:
- `plugin_description` — display name; also used as WebUI config key prefix and `ServiceRegistry` provider name
- `dynamic_imports` — `dict[str, list[str]]` mapping `"module.path": ["func_name"]` for LLM tool map
- `function_declarations` — OpenAI-style JSON function schemas for LLM tool exposure
- `plugin_dependencies` / `dependencies` — list of dependency plugin names
- `plugin_name` — override the directory name

Plugin loading is managed by `PluginManager` (`core/bot/legacy_plugin_manager.py`) with three strategies: `BATCH_LOADING`, `ALL_AT_ONCE`, `MEMORY_AWARE`. Configured in `basic_config.yaml` under `PluginLoadConfig`.

A new-arch `PluginManager` (`core/bot/plugin_manager.py`) also exists — supports class-style plugins via `PluginInterface` with `setup(bot, config, context)` / `teardown()`, clean handler ownership tracking, and file-watcher hot-reload. Not yet wired as the default in `StandaloneRuntime`.

### Adapter Layout

All real adapter code lives in `adapters/onebot/`. The `adapters/napcat/` and `adapters/lagrange/` directories are thin compatibility re-export shells — do not add new code there.

- `NapCatApiClient` extends `OneBotApiClient` with AI voice methods
- `LagrangeApiClient` extends with file/history methods
- `LagrangeAdapter.send()` calls `normalize_outbound_components()` for Lagrange-specific outbound compatibility

### Message Sending

```python
from core.message.message_components import Text, Image, Node, At

await bot.send(event, "plain text")
await bot.send(event, [Image(file="path.png"), Text("caption")])
await bot.send(event, [Node(content=[Text("forwarded")])])
await bot.send(event, components, Quote=True)  # with reply quote
```

### WebUI

- Flask backend (`web/server_new.py`) on port 5007, runs in a daemon thread
- Token-based auth (Fernet, 200-hour sessions), optional IP whitelist
- WebSocket bridge at `/api/ws` (flask-sock) connects WebUI chat to the bot's event stream
- REST endpoints for config YAML load/save, user management, chat history, log viewer, file upload
- 404 fallback serves `web/dist/index.html` (React SPA)
- YAML file discovery in the config editor uses `plugin_description` from each plugin's `__init__.py`

## Key Conventions

### Import Paths

Always import from the canonical module paths:
```python
from core.bot.event_bus import EventBus
from core.event.events import GroupMessageEvent
from adapters.onebot import OneBotAdapter, WebSocketBot
```

Never use deprecated namespace aliases (`run.*`, `developTools.*`, `framework_common.*`) in new code.

### Logging

```python
from core.toolkit.logger import get_logger
logger = get_logger("MyModule")

logger.info("...")          # cyan [bot] — default
logger.info_msg("...")      # green [MSG] — may be suppressed by _blocked_loggers
logger.info_func("...")     # blue [FUNC]
logger.server("...")        # purple [SERVER]
logger.warning("...")
logger.error("...")
```

Log files rotate daily under `Eridanus/log/YYYY-MM-DD.log`.

### Service Registry (cross-plugin access)

```python
from core.services.registry import ServiceRegistry
registry = ServiceRegistry.get_instance()
service = registry.get("service_name")        # returns None if not found
service = registry.require("service_name")    # raises KeyError if not found
```

### Other Conventions

- `call_*` prefix for async functions exposed to the LLM tool map
- `core.toolkit.installer.install_and_import("pkg")` for optional runtime dependencies
- Data assets and caches go under the workspace-level `data/` directory (gitignored)
- Built-in bot commands: `/reload all`, `/status`, `/info`, `/test`
- `APP_ROOT` and `PLUGINS_DIR` are defined in `core/config/constants.py`
- `PLUGIN_DIR_EXCLUDES = {"__pycache__", "common_config"}` — directories skipped during plugin scan
