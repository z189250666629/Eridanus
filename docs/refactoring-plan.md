# Eridanus 重构文档

## 1. 重构目标

将 Eridanus 从当前的三层耦合架构（developTools / framework_common / run）逐步重构为 **core + adapter + plugin** 的清晰分层架构，同时保证迁移过程中项目始终可启动、可加载插件、可响应消息。

- **`core/`** — bot 本体：抽象接口、事件系统、消息模型、插件加载、配置管理、数据库、工具集
- **`adapters/`** — 平台 / 协议实现：当前以 NapCat / OneBot v11 为主线，并预留 Lagrange 独立 adapter
- **`plugins/`** — 所有增量功能：AI 对话、绘图、媒体、群管、游戏查询等
- **`web/`** — 继续独立维护

本方案强调两个原则：

1. **先解耦，再搬目录**：先把硬编码路径、模块前缀和运行时副作用收敛掉，再做物理迁移。
2. **兼容层先行**：在旧路径仍被大量引用时，不做“纯移动 + 全局替换”式改造。
3. **平台实现外置**：`core` 不直接绑定 NapCat / OneBot 的具体实现，平台相关代码放入独立 `adapters/`。

当前文档中 `adapter` 的讨论以 **NapCat / OneBot v11** 为主线，同时保留 **Lagrange** 作为独立 adapter 的兼容预留；不在本轮方案中展开 Telegram、Discord 等其他平台的实现细节。

---

## 2. 现状分析

### 2.1 当前目录结构

```
Eridanus/
├── main.py
├── developTools/          # OneBot SDK 层
│   ├── adapters/          #   WebSocketBot, EventBus, 全部 OneBot API 封装
│   ├── event/             #   EventFactory, EventBase, 所有事件模型
│   ├── message/           #   MessageChain, MessageComponent (Text, Image, Node...)
│   └── utils/             #   logger, CQ code 解析
├── framework_common/      # 框架层
│   ├── framework_util/    #   ExtendBot, PluginManager, YAMLManager, func_map
│   ├── database_util/     #   User, Group, llmDB, Redis, GroupSummary
│   ├── manshuo_draw/      #   自研绘图框架
│   ├── ToolKits/          #   BaseTool 工具基类 (file, image, network, system, text)
│   └── utils/             #   system_logger, install_and_import, memory monitor 等
├── run/                   # 插件目录（每个子目录是一个插件）
│   ├── common_config/     #   全局 YAML 配置
│   └── <plugin>/          #   插件代码 + 本地配置
└── web/                   # Flask WebUI
```

### 2.2 当前存在的问题

**1. 继承链过深且职责不清**

```
WebSocketBot (developTools/adapters)
  └─ ExtendBot (framework_common/framework_util/websocket_fix.py)
       └─ PluginAwareExtendBot (framework_common/framework_util/PluginAwareExtendBot.py)
```

- `WebSocketBot` 同时包含：连接管理、事件分发（EventBus）、消息发送（send/send_group_msg/...）、OneBot API 调用（mute/kick/recall/...） — 这是一个 ~900 行的上帝类
- `ExtendBot` 在 `_process_messages` 中硬编码了黑白名单过滤逻辑（~80 行嵌套 if-else），并且为 Lagrange 适配器做了特殊 send 处理
- `PluginManager` 通过 monkey-patch（`_enhance_bot_instance`）给 ExtendBot 动态注入插件管理能力

**2. func_map 是模块级副作用代码**

`framework_common/framework_util/func_map.py` 在 import 时就遍历 `run/` 目录并执行所有插件的 `__init__.py`。这导致：
- 无法控制加载时机
- 加载失败会影响整个 import 链
- 与 PluginManager 的加载逻辑重复

**3. 插件间存在硬耦合**

通过 `from run.xxx.service.yyy import zzz` 直接跨插件 import，例如：
- `ai_code_generator` → `ai_llm` (依赖 schemaReplyCore, GeminiAPI)
- `acg_infromation` → `group_fun` (依赖 manage_group_status)
- `group_msg_analyze` → `ai_llm` (依赖 gemini_prompt_elements_construct)
- `system_plugin` → `basic_plugin` (依赖 life_service)

这些跨插件依赖使得无法独立加载/卸载单个插件。

**4. 配置散落**

`common_config/` 既在 `run/` 下（被 YAMLManager 管理），又在逻辑上服务于 core 层（ws 地址、黑白名单、主人 ID 等）。插件配置和核心配置混在同一个目录体系中。

**5. 平台实现与核心边界不清**

当前 `developTools` 既承担了事件 / 消息模型，也承担了 OneBot WebSocket 连接、OneBot API 调用和 NapCat 运行方式耦合。这导致：

- `core` 很难脱离 OneBot / NapCat 独立存在
- 即使当前只做 NapCat，也容易把协议差异、部署方式、资源处理规则继续堆进 Bot 主体
- 未来若接入其他平台，会退化成在主类里不断加 `if platform == ...`

### 2.3 实施约束

下面这些约束决定了本次重构不能按“先搬目录，再修引用”的方式执行：

- `main.py` 当前直接依赖 `YAMLManager("run")`、`PluginManager(..., plugins_dir="run")`，并且入口逻辑中仍有 `from run.xxx ...` 的直接导入
- `YAMLManager` 目前把传入目录视为唯一配置根，并将第一层子目录直接映射为 `config.common_config`、`config.ai_llm` 这类访问接口
- `PluginManager`、热重载逻辑、`main_func_detector` 当前都将插件模块前缀硬编码为 `run.<plugin>`
- LLM 工具系统的实际运行入口主要依赖 `func_map_loader.py`，而不是文档中原先提到的 `func_map.py`
- 框架层、入口层和插件层都存在大量 `run.*` 直接导入；这说明“插件独立装卸”必须建立在边界梳理之后，而不是目录改名之后

因此，后文所有阶段都以“运行时兼容优先”为前提。

---

## 3. 重构后目标结构

```
Eridanus/
├── main.py                     # 入口：初始化 core，启动事件循环
├── core/                       # Bot 本体（平台无关）
│   ├── __init__.py
│   ├── bot/                    # Bot 实例与生命周期
│   │   ├── bot.py              #   Bot 类（连接、重连、关闭）
│   │   ├── event_bus.py        #   EventBus（订阅、分发、监控）
│   │   ├── api.py              #   平台无关的 Bot 能力接口
│   │   ├── plugin_manager.py   #   插件加载、卸载、热重载
│   │   └── func_map.py         #   LLM 工具映射收集（懒加载，非 import 副作用）
│   ├── adapter/                #   适配器抽象
│   │   ├── base.py             #   PlatformAdapter 抽象
│   │   ├── session.py          #   传输会话抽象
│   │   ├── event_source.py     #   事件来源抽象
│   │   └── api_client.py       #   API 调用抽象
│   ├── event/                  # 事件模型
│   │   ├── base.py             #   EventBase
│   │   ├── factory.py          #   EventFactory
│   │   └── models.py           #   所有事件类型 (GroupMessageEvent, ...)
│   ├── message/                # 消息模型
│   │   ├── chain.py            #   MessageChain
│   │   └── components.py       #   Text, Image, At, Node, Reply, ...
│   ├── config/                 # 配置管理
│   │   ├── manager.py          #   YAMLManager（热重载）
│   │   └── schema.py           #   核心配置的 Schema 定义
│   ├── filter/                 # 消息过滤（从 ExtendBot 中拆出）
│   │   ├── base.py             #   Filter 基类
│   │   ├── blacklist.py        #   黑白名单过滤器
│   │   └── chain.py            #   FilterChain 组合过滤
│   ├── database/               # 数据持久化
│   │   ├── sqlite.py           #   aiosqlite 封装
│   │   ├── redis.py            #   Redis 缓存管理
│   │   └── models/             #   User, Group 等数据模型
│   ├── toolkit/                # 通用工具集（从 ToolKits + utils 合并）
│   │   ├── logger.py           #   统一日志
│   │   ├── installer.py        #   install_and_import
│   │   ├── memory.py           #   内存监控
│   │   ├── network.py          #   HTTP 下载等网络工具
│   │   ├── image.py            #   图片处理工具
│   │   └── file.py             #   文件操作工具
│   └── draw/                   # 绘图框架（manshuo_draw）
│       └── ...
├── adapters/                   # 平台实现（当前以 NapCat 为主，预留 Lagrange）
│   ├── __init__.py
│   ├── onebot/
│   │   ├── session_ws.py       #   共享 OneBot WebSocketSession
│   │   └── api_client.py       #   共享 OneBot API 调用
│   ├── napcat/
│   │   ├── adapter.py          #   NapCatAdapter
│   │   ├── session_ws.py       #   NapCat WebSocketSession
│   │   ├── event_source.py     #   NapCat 事件接入
│   │   ├── api_client.py       #   NapCat API 调用
│   │   ├── event_factory.py    #   NapCat 原始事件 -> core event
│   │   └── capabilities.py     #   NapCat 能力声明与差异实现
│   └── lagrange/
│       ├── adapter.py          #   LagrangeAdapter
│       ├── api_client.py       #   Lagrange API 调用
│       └── capabilities.py     #   Lagrange 发送兼容与差异实现
├── plugins/                    # 增量功能（原 run/ 中除 common_config 外的所有插件）
│   ├── ai_llm/
│   ├── ai_generated_art/
│   ├── ai_voice/
│   ├── basic_plugin/
│   ├── streaming_media/
│   ├── resource_collector/
│   ├── groupManager/
│   ├── group_fun/
│   ├── acg_infromation/
│   ├── system_plugin/
│   ├── scheduled_tasks/
│   ├── character_detection/
│   ├── meme_generate/
│   ├── auto_reply/
│   └── ...
├── config/                     # 运行时配置（原 run/common_config/）
│   ├── basic_config.yaml
│   ├── menu.yaml
│   ├── censor_group.yaml
│   └── censor_user.yaml
├── data/                       # 数据目录（不变）
└── web/                        # WebUI（独立维护，不变）
```

---

## 4. 核心设计原则

### 4.1 Bot 类拆分：组合代替继承

**现状**：`WebSocketBot → ExtendBot → PluginAwareExtendBot`，单个类承担过多职责。

**重构**：Bot 类通过组合持有各子系统引用，而非继承：

```python
# core/bot/bot.py
class Bot:
    def __init__(self, adapter: PlatformAdapter, config: ConfigManager):
        self.adapter = adapter
        self.config = config
        self.event_bus = EventBus()                         # 事件分发
        self.filter_chain = FilterChain()                   # 消息过滤
        self.plugin_manager = PluginManager(self)           # 插件管理
        self.func_map = FuncMap()                           # LLM 工具映射

    async def start(self):
        await self.plugin_manager.load_all()
        await self.adapter.start(self._handle_raw_event)
        # adapter 收到平台事件 → 转换为 core event → filter_chain → event_bus

    def on(self, event_type):
        """注册事件处理器的装饰器"""
        return self.event_bus.on(event_type)

    async def send(self, event, components, quote=False):
        """统一发送接口"""
        return await self.adapter.send(event, components, quote)
```

### 4.2 传输层抽象化

当前文档虽然将 `adapter` 独立出来，但本轮实际承载层应当是 **OneBot v11 adapter**。`core` 只保留抽象与平台无关能力，具体协议实现放在顶层 `adapters/onebot/`，NapCat / Lagrange 只作为该协议下的实现差异，而不是两套一级 adapter。

根据 NapCat 官方文档，NapCat / OneBot v11 同时支持 HTTP 与 WebSocket 两类通信，并且两类通信下都存在“客户端 / 服务端”两种角色。结合当前项目现状，本轮只覆盖 **Bot 作为 WebSocket 客户端主动连接 NapCat** 这一主路径，不展开 HTTP 接入与其他部署角色。

因此这里不应设计为“Adapter = 连接 + 收事件 + 调 API + 轮询”的单一抽象，而应拆成三个层次：

- **PlatformAdapter**：平台适配器，对 `core` 暴露统一能力
- **事件来源（EventSource）**：负责接收事件
- **API 客户端（ApiClient）**：负责调用 OneBot API

这样既符合当前 NapCat 的 WebSocket 推送模型，也能把协议细节收束在 adapter 内部。

```python
# core/adapter/base.py
class PlatformAdapter(ABC):
    @abstractmethod
    async def start(self, on_event): ...

    @abstractmethod
    async def stop(self): ...

    @abstractmethod
    async def send(self, event, components, quote=False): ...


# core/adapter/session.py
class WebSocketSession:
    async def connect(self): ...
    async def disconnect(self): ...
    async def recv(self): ...
    async def send(self, payload): ...


# core/adapter/event_source.py
class EventSource(ABC):
    @abstractmethod
    async def start(self, on_event): ...

    @abstractmethod
    async def stop(self): ...


# core/adapter/api_client.py
class ApiClient(ABC):
    @abstractmethod
    async def call_api(self, action: str, params: dict) -> dict: ...
```

推荐的组合方式：

- **当前唯一落地主路径**：`adapters/onebot/adapter.py` 组合 `WebSocketSession + EventSource + ApiClient`，再由 `NapCatAdapter` / `LagrangeAdapter` 叠加少量差异

明确说明：

- 本项目当前不规划实现“HTTP 轮询收事件”
- 即使 NapCat 文档同时描述了 HTTP 与 WebSocket 模式，本项目当前也只实现 WebSocket 客户端模式
- 对当前 WebSocket 方案，`EventSource` 与 `ApiClient` 不能各自维护独立连接，应共享同一个底层 Session；因为现有实现中事件包和 API 响应包共用同一条连接，且 `echo -> Future` 的响应匹配也依赖这条连接
- `Bot` 只依赖 `PlatformAdapter` 抽象，不依赖具体平台实现
- NapCat 事件进入 `core` 前，需要先把原始 OneBot 事件转换成 `core` 事件；平台原始 payload 只作为 `raw_event` 或 `platform_data` 保留
- NapCat / Lagrange 的实现差异，例如消息 ID 语义、文件资源路径、Lagrange 的组件归一化，都应封装在 `adapters/onebot/` 的实现差异层中，而不是泄漏到 `core`

### 4.3 NapCat Adapter 边界

本节只定义 **NapCat / OneBot v11** 的 adapter 边界，不讨论其他平台。

#### 4.3.1 core 的职责

`core` 只负责平台无关的运行时能力：

- 事件总线
- 插件管理
- 配置管理
- 通用消息模型
- 数据库、权限、工具系统
- Bot 生命周期编排

`core` 不直接处理这些 NapCat / OneBot 细节：

- OneBot action 名称
- WebSocket 包结构
- `echo` 响应匹配
- NapCat 资源 URL 规则
- NapCat 特有的消息 ID / 文件 ID 时效性

#### 4.3.2 onebot adapter 的职责

`adapters/onebot/` 负责：

- 管理与 NapCat 的 WebSocket 连接
- 接收原始事件包和 API 响应包
- 通过 `echo` 机制匹配请求与响应
- 将原始事件转换为 `core` 可消费的事件对象
- 将 `core` 的发送请求翻译为 NapCat / OneBot v11 API 调用
- 封装 NapCat 的差异实现与资源规则

一句话原则：

**adapter 负责翻译 OneBot 协议与实现差异，core 负责编排运行时，plugin 负责业务。**

#### 4.3.3 NapCat 能力边界

本轮只抽象当前项目已经大量依赖、且在 NapCat / OneBot v11 中稳定存在的能力：

- 发送私聊 / 群消息
- 回复消息
- 撤回消息
- 获取群 / 好友 / 成员信息
- 群管理相关操作（禁言、踢人、设置群名片 / 头衔等）
- 转发消息
- 文件上传

这些能力仍然通过 `PlatformAdapter` 暴露给 `core`，但实现与参数翻译都留在 `adapters/onebot/`。

#### 4.3.4 NapCat 事件与消息映射

当前项目大量使用 OneBot 事件字段，例如：

- `post_type`
- `message_type`
- `group_id`
- `user_id`
- `message_id`
- `raw_message`

重构时不要求一次性删除这些字段，但要求分层：

- `adapters/onebot/event_factory.py` 负责从 OneBot 原始事件构建 `core` 事件
- `core` 事件保留当前业务所需的稳定字段
- NapCat 原始字段通过 `raw_event` / `platform_data` 保留，供极少数平台耦合逻辑使用

也就是说，本轮目标不是“立即做成真正多平台事件模型”，而是先把 NapCat 原始协议隔离到 adapter 层。

#### 4.3.5 NapCat 特有差异

根据 NapCat 文档，需要在 adapter 层明确处理这些差异：

- WebSocket 连接中事件与 API 响应共用同一通道
- 消息 ID 并非连续数字，且会随缓存淘汰失效
- 文件 / 图片资源支持本地路径、`file://`、`base64://`、`data:`、`http/https` 等多种输入形式

因此以下逻辑必须留在 `adapters/onebot/`：

- `echo -> Future` 响应匹配
- 消息发送参数组装
- 资源路径规范化
- 平台特定消息兼容修正（如 Lagrange 组件类型归一化）

### 4.4 Filter Chain：过滤逻辑可插拔

将 `websocket_fix.py` 中的群/用户黑白名单逻辑拆为可组合的过滤器链；但迁移时必须保留现有行为，包括：

- 群消息与私聊消息的分流
- 群/用户黑白名单组合判断
- 对无法识别事件的兜底日志

Lagrange 下的消息组件类型修正不属于 Filter 责任，应保留在发送层 / API 层。

```python
# core/filter/base.py
class Filter(ABC):
    @abstractmethod
    async def check(self, event: EventBase) -> bool:
        """返回 True 表示放行，False 表示拦截"""
        ...

# core/filter/blacklist.py
class GroupBlacklistFilter(Filter):
    async def check(self, event):
        if not hasattr(event, "group_id"):
            return True
        return event.group_id not in self.config.blacklist

# core/filter/chain.py
class FilterChain:
    def __init__(self):
        self.filters: list[Filter] = []

    def add(self, f: Filter):
        self.filters.append(f)

    async def check(self, event) -> bool:
        return all(await f.check(event) for f in self.filters)
```

### 4.5 插件接口标准化

**现状**：插件通过 `main(bot, config)` 注册事件 + `__init__.py` 中 `dynamic_imports` / `function_declarations` 声明 LLM 工具，两套机制独立运行。

**重构**：统一为 Plugin 基类 + 声明式元数据：

```python
# core/bot/plugin_manager.py

class PluginMeta:
    """插件元数据，从 __init__.py 或 plugin.yaml 中读取"""
    name: str
    description: str
    version: str = "0.0.1"
    dependencies: list[str] = []   # 依赖的其他插件名

class PluginInterface(ABC):
    """插件接口（可选实现，也可继续用 main() 函数式写法）"""

    @abstractmethod
    async def setup(self, bot: Bot, config: ConfigManager): ...

    async def teardown(self): ...
```

**兼容方案**：PluginManager 同时支持两种加载方式：
1. **函数式**（向后兼容）：检测 `main(bot, config)` 函数
2. **类式**（新推荐）：检测实现了 `PluginInterface` 的类

### 4.6 插件间通信：ServiceRegistry

解决跨插件 `from run.xxx import yyy` 的硬耦合问题。引入服务注册表，插件注册自己提供的服务，其他插件通过名称查找。

注意：这一步不只是改插件内部互相引用。当前框架层和入口层也直接依赖部分插件实现，因此迁移时要优先抽出高复用服务，再逐步替换调用方。
还要特别注意：`ServiceRegistry` 只能替代“运行时查找服务”的场景，**不能自动消除模块顶层 import 的耦合**。如果某个模块在 import 阶段就执行了 `from run.xxx import yyy`，那它在导入时就已经绑定了目标插件，后续再改成注册表查找也无效。

因此实际迁移顺序必须是：

1. 先把顶层跨插件 import 改成延迟查找，或抽到 `core/services` / `core/interfaces` 这样的稳定边界
2. 再在运行时通过 `ServiceRegistry` 注册 / 获取实现
3. 最后再尝试实现真正的插件独立加载 / 卸载

```python
# core/services/registry.py
class ServiceRegistry:
    _instance = None
    _services: dict[str, Any] = {}

    @classmethod
    def register(cls, name: str, service: Any):
        cls._services[name] = service

    @classmethod
    def get(cls, name: str) -> Any:
        return cls._services.get(name)

# 插件 ai_llm 注册服务
ServiceRegistry.register("ai_reply_core", aiReplyCore)
ServiceRegistry.register("schema_reply_core", schemaReplyCore)

# 插件 ai_code_generator 消费服务
schema_reply = ServiceRegistry.get("schema_reply_core")
```

### 4.7 func_map 懒加载

当前运行时真正影响较大的是 `func_map_loader.py` 的 import 副作用扫描，而不是单独的 `func_map.py`。因此这里的目标应改为：

1. 将 `func_map_loader.py` 的目录扫描和模块导入从 import-time 副作用改为显式构建
2. 由 `PluginManager` 在插件元信息可用后统一注册 LLM 工具
3. `build_tool_map()` / `get_tool_declarations()` 改为基于已加载插件数据构建，而不是再次扫描目录

```python
# core/bot/func_map.py
class FuncMap:
    def __init__(self):
        self.functions: dict[str, Callable] = {}
        self.declarations: list[dict] = []

    def register(self, name: str, func: Callable, declaration: dict = None):
        self.functions[name] = func
        if declaration:
            self.declarations.append(declaration)

    async def call(self, bot, event, config, func_name: str, params: dict):
        func = self.functions.get(func_name)
        if func is None:
            raise ValueError(f"Function '{func_name}' not found")
        return await func(bot, event, config, **params)
```

PluginManager 在加载每个插件时，读取其 `dynamic_imports` 和 `function_declarations`，调用 `func_map.register()` 注册。

---

## 5. 迁移映射表

| 现有位置 | 重构后位置 | 备注 |
|---------|-----------|------|
| `developTools/adapters/websocket_adapter.py` (WebSocketBot) | `core/bot/bot.py` + `core/adapter/*.py` + `adapters/onebot/*.py` | `core` 放抽象，OneBot 协议实现移入 `adapters/onebot/` |
| `developTools/adapters/websocket_adapter.py` (EventBus) | `core/bot/event_bus.py` | 独立模块 |
| `developTools/event/` | `core/event/` | 直接迁移 |
| `developTools/message/` | `core/message/` | 直接迁移 |
| `developTools/utils/logger.py` | `core/toolkit/logger.py` | 合并为统一日志 |
| `developTools/utils/cq_code_handler.py` | `core/message/cq_parser.py` | 归入消息模块 |
| `framework_common/framework_util/websocket_fix.py` (ExtendBot) | 拆解 → `core/filter/`, `core/bot/api.py` | 黑白名单逻辑 → Filter，Lagrange 适配 → API 层 |
| `framework_common/framework_util/PluginAwareExtendBot.py` | `core/bot/plugin_manager.py` | PluginManager 重写 |
| `framework_common/framework_util/func_map.py` + `func_map_loader.py` | `core/bot/func_map.py` | 统一为显式注册 |
| `framework_common/framework_util/yamlLoader.py` | `core/config/manager.py` | 需先改为支持多配置根与兼容别名，再迁移 |
| `framework_common/framework_util/DualBotManager.py` | `core/bot/dual_manager.py` | 直接迁移 |
| `framework_common/framework_util/bot_info.py` | `core/bot/info.py` | 直接迁移 |
| `framework_common/database_util/` | `core/database/` | 直接迁移 |
| `framework_common/manshuo_draw/` | `core/draw/` | 直接迁移 |
| `framework_common/ToolKits/` | `core/toolkit/` | 合并到 toolkit |
| `framework_common/utils/` | `core/toolkit/` | 合并到 toolkit |
| `run/common_config/` | `config/` | 最后阶段物理迁移；前期先支持多配置根 |
| `run/<plugin>/` | `plugins/<plugin>/` | 最后阶段物理迁移；前期保持 `run` 逻辑命名空间 |

---

## 6. 核心类映射图

本节不是最终代码结构图，而是“当前主要类 / 模块在重构后的落点”说明，方便实施时逐个拆解。

### 6.1 Bot 主链路

| 当前实现 | 当前职责 | 重构后落点 | 迁移策略 |
|---------|---------|-----------|---------|
| `developTools.adapters.websocket_adapter.EventBus` | 事件订阅、分发、超时监控 | `core.bot.event_bus.EventBus` | 基本可直接抽出 |
| `developTools.adapters.websocket_adapter.WebSocketBot` | WS 连接、收包、事件分发、API 调用、消息发送 | `adapters.onebot.session_ws.OneBotWebSocketSession` + `adapters.onebot.event_source.OneBotEventSource` + `adapters.onebot.api_client.OneBotApiClient` + `core.bot.bot.Bot` | 拆成“会话 / 事件 / API / Bot 编排”四部分 |
| `framework_common.framework_util.websocket_fix.ExtendBot` | 黑白名单过滤、Lagrange/NapCat 发送兼容 | `core.filter.*` + `adapters.onebot.NapCatAdapter` + `adapters.onebot.LagrangeAdapter` | 过滤逻辑进 `core.filter`，平台兼容逻辑留在 OneBot 实现差异层 |
| `framework_common.framework_util.PluginAwareExtendBot.PluginAwareExtendBot` | 插件感知事件注册 | `core.bot.plugin_manager.PluginRuntimeContext` 或 `core.bot.plugin_manager.PluginManager` 内部状态 | 不再通过 bot monkey-patch 暴露 |
| `framework_common.framework_util.PluginAwareExtendBot.PluginManager` | 插件发现、加载、卸载、热重载、文件监听 | `core.bot.plugin_manager.PluginManager` | 先参数化目录与模块前缀，再去掉 monkey-patch |
| `main.py` 中的启动编排 | 初始化配置、创建 bot、加载插件、启动 WebUI | `main.py` + `core.bot.bot.Bot` + `adapters.onebot.NapCatAdapter` | 保持入口不变，逐步切换依赖 |

### 6.2 配置与工具链

| 当前实现 | 当前职责 | 重构后落点 | 迁移策略 |
|---------|---------|-----------|---------|
| `framework_common.framework_util.yamlLoader.YAMLManager` | 运行时 YAML 加载、热重载、属性访问 | `core.config.manager.ConfigManager` | 先做兼容封装，再考虑类名迁移 |
| `framework_common.framework_util.func_map_loader` | 扫描插件 `dynamic_imports` / `function_declarations` | `core.bot.func_map.FuncMapRegistry` | 先改成显式构建，后并入 `PluginManager` 生命周期 |
| `framework_common.framework_util.func_map` | 历史函数调用映射 | `core.bot.func_map` | 合并到统一工具注册机制 |
| `framework_common.framework_util.main_func_detector` | 扫描插件目录中的 `main()` | `core.bot.plugin_discovery` | 保留发现能力，但去除 `run.<plugin>` 硬编码 |
| `framework_common.framework_util.DualBotManager` | 双 Bot 协调 | `core.bot.dual_manager` | 后移，等主 Bot 稳定后再迁 |

### 6.3 NapCat 专属落点

| 当前实现 | 问题 | 重构后落点 |
|---------|------|-----------|
| `WebSocketBot._receive()` + `_process_messages()` | 事件包与 API 响应包耦合在一个类里 | `adapters.onebot.session_ws.OneBotWebSocketSession` + `adapters.onebot.event_source.OneBotEventSource` |
| `WebSocketBot._call_api()` | API 调用与连接管理耦合 | `adapters.onebot.api_client.OneBotApiClient` |
| `ExtendBot.send()` 中的 Lagrange/NapCat 类型修正 | 平台兼容逻辑泄漏进 bot | `adapters.onebot.capabilities` + `adapters.onebot.LagrangeAdapter.send()` |
| `EventFactory.create_event()` 直接接 OneBot 原始 payload | 平台协议直接渗透到 core | `adapters.onebot.event_factory` 先做协议转换，再进入 `core.event` |

---

## 7. 分阶段执行计划

### Phase 0：运行时去硬编码

目标：先把所有“写死在 `run` / `developTools` / `framework_common` 名字里”的运行时假设抽出来，不搬目录。

1. 为插件目录、插件模块前缀、配置根目录建立统一常量或配置项
2. 改造 `YAMLManager`，支持“核心配置根 + 插件配置根”的双根模式，同时保留 `config.common_config.xxx` 旧访问方式
3. 改造 `PluginManager` / `main_func_detector`，去掉对 `run.<plugin>` 的硬编码，改为可配置模块前缀
4. 改造 `func_map_loader`，将扫描逻辑改为显式调用而非 import 副作用
5. 清理入口层和框架层对 `run.*` 的直接导入，先替换成统一 facade 或服务接口

**验证标准**：

- 在目录结构完全不变的前提下，`python main.py` 仍能启动
- 插件可发现、可加载、可热重载
- LLM 工具映射仍可构建

### Phase 0 首批文件清单

本节列出真正开工时建议优先改动的文件。原则是：先改“运行时入口与发现链路”，暂不改业务插件内容。

#### P0-1 插件目录 / 模块前缀参数化

优先文件：

- `Eridanus/main.py`
- `Eridanus/framework_common/framework_util/PluginAwareExtendBot.py`
- `Eridanus/framework_common/framework_util/main_func_detector.py`

目标：

- 将 `plugins_dir="run"` 提取为统一配置
- 将 `run.<plugin>` 模块名前缀提取为统一配置
- 热重载、卸载、模块缓存清理都不再写死 `run.`

完成标准：

- 仅修改配置常量即可切换逻辑插件根与模块前缀

#### P0-2 配置系统兼容层

优先文件：

- `Eridanus/framework_common/framework_util/yamlLoader.py`
- `Eridanus/main.py`

目标：

- 支持“核心配置根”和“插件配置根”分离
- 保持现有 `config.common_config.xxx`、`config.ai_llm.config` 访问方式可用
- 文件监听仍然生效

完成标准：

- 不迁目录的前提下，配置根可以从单根演化为双根

#### P0-3 func_map 显式构建

优先文件：

- `Eridanus/framework_common/framework_util/func_map_loader.py`
- `Eridanus/framework_common/framework_util/func_map.py`
- `Eridanus/run/ai_llm/aiReply.py`
- `Eridanus/run/system_plugin/api_implements.py`

目标：

- 去掉 import-time 自动扫描
- 提供一个显式 `build_from_plugins(...)` 入口
- 保持 `build_tool_map()`、`get_tool_declarations()` 的旧调用方式暂时不变

完成标准：

- 导入 `func_map_loader` 本身不再触发全量插件扫描

#### P0-4 入口层直连插件清理

优先文件：

- `Eridanus/main.py`
- `Eridanus/framework_common/utils/ai_translate.py`
- 其他直接 `from run.xxx` 的 framework 层文件

目标：

- 入口层和框架层不再直接 import 某个插件实现
- 先替换成 facade、延迟导入或服务接口

完成标准：

- 框架层不因某个插件缺失而在 import 阶段直接失败

### Phase 1：建立 core 外观层

目标：先建立新命名空间和新模块边界，再决定是否搬物理文件。

1. 创建 `core/` 目录结构
2. 创建顶层 `adapters/` 目录，并在 `core/adapter/` 中定义抽象接口
3. 将 `EventBus`、事件模型、消息模型先以 re-export 或轻量包装方式暴露到 `core/`
4. 为数据库、draw、toolkit 建立 `core` 下的新导出入口
5. `main.py` 优先切换为从 `core.*` 和 `adapters.*` 导入，而不是直接依赖旧层路径
6. 保留旧路径重导出，避免一次性修改所有插件

**验证标准**：

- 主入口主要依赖 `core.*`
- OneBot 平台实现主要位于 `adapters.onebot.*`
- 老插件不改代码仍能运行

### Phase 2：Bot 与传输层重构

1. 从 `WebSocketBot` 中拆出 `EventBus` → `core/bot/event_bus.py`
2. 在 `core/adapter/` 中定义 `PlatformAdapter` / `EventSource` / `ApiClient` / `Session` 抽象
3. 在 `adapters/onebot/` 中实现基于 WebSocket 的适配器
4. 从 `WebSocketBot` 中拆出 OneBot API 方法 → `adapters/onebot/api_client.py`
5. 创建组合式 `Bot` 类 → `core/bot/bot.py`
6. 从 `ExtendBot._process_messages` 中拆出过滤逻辑 → `core/filter/`
7. 将 Lagrange 发送兼容逻辑下沉到平台适配器层，并保持其独立于 NapCat adapter
8. 更新 `main.py` 使用新 Bot 类 + `NapCatAdapter`（来自 `adapters/onebot/`）

**验证标准**：

- 所有消息收发正常
- 群/用户黑白名单结果与旧逻辑一致
- Lagrange 下的 Reply / At / Node / File 等消息兼容保持一致
- `Bot` 不直接依赖 NapCat / OneBot 具体实现类
- NapCat WebSocket 主路径在新架构下行为与当前一致

### Phase 3：插件系统与 LLM 工具系统重构

1. 重写 `PluginManager`，去掉 monkey-patch，改为组合方式
2. 将 `func_map_loader` 和 `func_map` 合并为统一的显式注册机制
3. 定义 `PluginMeta` 和 `PluginInterface`
4. 支持插件元信息从 `__init__.py` 读取，`plugin.yaml` 作为后续增强项而不是前置条件
5. 为插件加载、卸载、热重载建立统一生命周期接口

**验证标准**：

- 插件加载/卸载/热重载正常
- `build_tool_map()` 等价能力迁移完成
- `function_declarations` 可按已加载插件正确收集

### Phase 4：解耦跨插件依赖

1. 建立 `ServiceRegistry` 或等价的服务接口层
2. 先梳理被依赖最多的公共能力，例如 `ai_llm`、群管状态、通用工具函数
3. 先清理模块顶层的跨插件 import，将其改为延迟绑定或稳定接口依赖
4. 优先替换入口层、框架层对插件实现的直接依赖
5. 再逐步替换插件间的 `from run.xxx import yyy`
6. 为依赖声明增加拓扑排序支持

**验证标准**：

- 关键高复用插件可独立加载
- 移除单个插件时不会因为框架层直连而崩溃

### Phase 5：物理目录迁移与清理

1. 将 `run/common_config/` 迁移到顶层 `config/`
2. 将 `run/<plugin>/` 迁移到 `plugins/<plugin>/`
3. 保留兼容包或 re-export，逐步下线 `run.*` 旧路径
4. 删除旧的 `developTools/`、`framework_common/`、`run/` 目录
5. 统一日志系统
6. 为核心配置添加 Schema 验证

**验证标准**：

- 仅依赖 `core/` + `plugins/` + `config/` 即可启动
- 旧路径只剩兼容层，且已有明确下线计划

### Phase 6：彻底脱离 `Eridanus/` 与依赖布局重组

1. 将当前仍位于 `Eridanus/` 的启动入口、WebUI、部署脚本与工具脚本迁入 `Eridanus/`
2. 移除 `core._legacy` 和所有“运行时仍需回到 `Eridanus/` 找资源”的路径假设
3. 让 `Eridanus/` 成为唯一应用根目录，可在没有 `Eridanus/` 目录的情况下独立启动
4. 将现有单体 `requirements.txt` 按功能边界拆分为：
   - core / adapter / web 基础依赖
   - 各插件独立依赖清单
   - 一个聚合安装入口
5. 更新部署脚本、自动安装逻辑与文档，支持全量安装与按功能安装
6. 最终删除 `Eridanus/` 旧目录

**验证标准**：

- 仓库在仅保留 `Eridanus/` 的形态下仍可完成安装与启动
- `Eridanus/` 内部自带启动入口、WebUI、配置与插件
- 依赖清单拆分后，既可通过聚合入口完成全量安装，也可按插件 / 功能按需安装

---

## 8. 迁移期间的兼容策略

在 Phase 1 完成后、Phase 5 之前，旧路径和新路径会共存。使用以下方式保持兼容：

```python
# 在旧目录的 __init__.py 中放置重导出
# developTools/__init__.py
import warnings
warnings.warn("developTools 已迁移至 core，请更新 import", DeprecationWarning)

# developTools/event/__init__.py
from core.event import *  # 重导出
```

除旧路径重导出外，还需要补齐以下兼容措施：

- `PluginManager` 支持旧插件根 `run` 与新插件根 `plugins` 并存
- 配置系统支持旧访问名 `common_config` 与新物理目录 `config/` 的兼容映射
- 旧的 `build_tool_map()` 等函数保留同名 facade，内部转发到新的 `FuncMap`

这样未迁移的插件代码不会立即 break，但会打印 deprecation 警告，便于逐步清理。

---

## 9. 关键风险与应对

| 风险 | 影响 | 应对 |
|-----|------|------|
| import 路径大量变更 | 所有文件都受影响 | 不在早期阶段做物理迁移；先引入 `core` facade 和旧路径 re-export |
| `run` 模块前缀硬编码 | 插件发现、热重载、卸载全部失效 | Phase 0 先参数化插件模块前缀，再谈目录改名 |
| 配置根目录变化 | 启动即失败，`config.common_config` 全部失效 | Phase 0 先改 `YAMLManager` 支持双根和兼容别名 |
| 跨插件依赖打破 | 部分插件功能异常 | Phase 4 先摸清依赖图，优先迁移被依赖最多的服务（如 `ai_llm`） |
| 顶层跨插件 import 仍然存在 | 即使引入 `ServiceRegistry` 也无法真正解耦 | 先改成延迟绑定或稳定接口，再切换到注册表查找 |
| 黑白名单过滤逻辑迁移 | 消息过滤失效 | Phase 2 对照测试：同一批消息，新旧过滤结果一致 |
| Lagrange 兼容逻辑迁移遗漏 | 发送消息行为异常 | Phase 2 对 `Reply` / `At` / `Node` / `File` 做回归验证 |
| 传输层拆分后使用多条 WS 连接 | 事件与 API 响应时序混乱，重连复杂度上升 | `EventSource` 与 `ApiClient` 共享底层 Session，不各自建连 |
| adapter 独立后仍泄漏实现特有字段到 core | 表面上分层，实际核心仍绑死 OneBot 某个实现 | 先将 NapCat / Lagrange 的原始字段与资源规则封装在 `adapters/onebot/` 的实现差异层，再逐步收敛 `core` 模型 |
| PluginManager monkey-patch 移除 | 插件加载/卸载异常 | Phase 3 先让新 PluginManager 通过所有已有插件的加载测试 |
| func_map 加载时机变更 | LLM 工具调用失败 | Phase 3 验证所有 `call_*` 函数可被正常调用，且 `function_declarations` 与旧实现对齐 |
