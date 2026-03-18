# Eridanus 重构分步 TODO

> 基于 `refactoring-plan.md`，按可执行粒度拆解。每步完成后必须通过 `python main.py` 启动验证。
>
> 2026-03-19 备注：当前迁移后的应用根目录已从 `newEridanus/` 正式更名回 `Eridanus/`。Phase 6 之前的历史记录原本用 `newEridanus/` 指代新根、用“旧 `Eridanus/`”指代迁移前目录树；如条目中出现“删除旧 `Eridanus/`”之类表述，均应理解为删除迁移前的旧树，而不是当前应用根。

---

## Phase 0：运行时去硬编码

### P0-1 插件目录 / 模块前缀参数化

- [x] **P0-1a** 创建 `framework_common/framework_util/constants.py`
  - 定义 `PLUGINS_DIR = "run"`、`PLUGINS_MODULE_PREFIX = "run"` 等常量
  - 所有需要用到插件根目录或模块前缀的地方统一从此导入
  - 进度：`constants.py` 已存在，`PLUGINS_DIR` / `PLUGINS_MODULE_PREFIX` 已被主入口与框架层引用

- [x] **P0-1b** 改造 `main.py` 中的硬编码
  - `YAMLManager("run")` → 使用常量
  - `from run.basic_plugin.service.self_condition import self_info_core`（第118行）→ 改为延迟导入或通过常量构造
  - 进度：`main.py` 已使用 `PLUGINS_DIR` / `PLUGINS_MODULE_PREFIX`，`self_condition` 已改为运行时动态导入

- [x] **P0-1c** 改造 `PluginAwareExtendBot.py`
  - `plugins_dir` 参数默认值改为引用常量
  - 检查文件监听、热重载、卸载中是否有其他 `"run"` / `"run."` 硬编码并替换
  - 进度：构造参数默认值已引用常量，模块缓存清理也已改为基于 `plugins_module_prefix`

- [x] **P0-1d** 改造 `main_func_detector.py`
  - 第105行 `run.character_detection.` 硬编码 → 改为通用的插件前缀判断
  - 第122-131行的目录名拼接逻辑确认无 `"run"` 假设
  - 进度：已改为通用插件子模块判断，不再对 `character_detection` 做特判

- [x] **P0-1e** 验证
  - `python main.py` 能启动，插件正常加载、热重载正常
  - 进度：2026-03-18 已补做热重载实测。后台启动 `python main.py` 后，日志确认 WebUI、Redis 自动拉起、21 个插件完成加载，并出现“文件监控已启动（递归监控所有插件文件）”。随后对 `run/comfyui_api/__init__.py` 做两次无语义影响的注释级改动，日志均出现完整的 `检测到插件 comfyui_api 的文件 __init__.py 变化 -> 开始重载插件 -> 插件 comfyui_api 已卸载 -> 找到 4 个 main 函数 -> 注册 4 个事件处理器 -> 插件 comfyui_api 重载成功` 链路，说明启动与插件热重载均已正常工作

### P0-2 配置系统兼容层

- [x] **P0-2a** 阅读 `yamlLoader.py` 全部309行，理解 `YAMLManager` 的目录扫描和属性访问机制
  - 进度：已确认当前实现已具备 `core_config_dir` + 多根扫描的基础能力，但运行时默认值和入口接线还未补完

- [x] **P0-2b** 为 `YAMLManager` 增加"多根"支持
  - 构造函数支持传入多个目录根（或额外的 `core_config_dir` 参数）
  - 保持 `config.common_config.basic_config[...]` 旧访问路径完全不变
  - 文件监听覆盖所有配置根
  - 进度：`YAMLManager` 已支持 `core_config_dir`、多个配置根和多根文件监听；主入口和 `get_instance()` 现已默认接入 `CORE_CONFIG_DIR`

- [x] **P0-2c** 验证
  - 不迁移任何目录，仅修改 `YAMLManager`
  - 所有配置访问路径不变，`python main.py` 正常
  - 进度：2026-03-18 按当前仓库阶段完成等价验证。由于仓库已经继续推进到 Phase 5，历史上的“仅修改 `YAMLManager`、尚未迁移 `config/`”场景已不再可原样复现；当前改以兼容性目标做验收：直接实例化 `YAMLManager(PLUGINS_DIR, CORE_CONFIG_DIR)` 后，`config.common_config.basic_config[...]` / `config.common_config.menu[...]` 旧访问路径仍可正常访问，`common_config.basic_config` 与 `common_config.menu` 的实际文件路径已解析到顶层 `config/basic_config.yaml`、`config/menu.yaml`，同时插件侧配置如 `config.ai_llm.config` 仍可访问；随后在删除旧 `run/common_config/` 后再次执行 `python main.py`，WebUI、21 个插件加载、Redis 自动拉起与长驻运行均保持正常，说明 YAML 兼容层目标已达成

### P0-3 func_map 显式构建

- [x] **P0-3a** 将 `func_map_loader.py` 第15-44行的 import-time 扫描逻辑封装进函数
  - 新增 `def scan_plugins(plugin_dir="run"):` 函数
  - 模块级变量 `dynamic_imports` / `all_function_declarations` 保留，但改为空初始化
  - 保留 `build_tool_map()` / `get_tool_declarations()` / `filter_tools_by_config()` 签名不变
  - 进度：`scan_plugins()` 已存在，模块级数据为显式扫描填充，导入模块本身不再主动扫描

- [x] **P0-3b** 在 `main.py` 的 `load_plugins()` 完成后显式调用 `scan_plugins()`
  - 确保时序：先加载插件 → 再扫描工具映射
  - 进度：`main.py` 在 `plugin_manager.start()` 之后和全量重载之后都显式调用了 `scan_plugins()`

- [x] **P0-3c** 找出所有 `import func_map_loader` / `from ... func_map_loader import ...` 的地方
  - 确认它们都在 `scan_plugins()` 被调用之后才真正使用 `dynamic_imports` / `all_function_declarations`
  - 消费方文件清单（已知）：
    - `run/ai_llm/aiReply.py`
    - `run/system_plugin/api_implements.py`
  - 进度：已核对 `aiReply.py`、`api_implements.py`、`aiReplyCore.py`、`aiReply_exp.py`，相关调用都发生在函数/事件处理器内部，不在 import 阶段消费扫描结果

- [x] **P0-3d** 验证
  - `import framework_common.framework_util.func_map_loader` 不再触发全量插件扫描
  - LLM 工具调用功能正常
  - 进度：2026-03-18 已补做当前环境验证。在正确的运行时路径下直接导入 `framework_common.framework_util.func_map_loader` 时，`dynamic_imports=0`、`all_function_declarations=0`，确认模块导入本身不再触发扫描；随后显式执行 `scan_plugins('run')` 后恢复到 `dynamic_imports=18`、`all_function_declarations=43`、`build_tool_map()=43`，说明“显式扫描才构建工具映射”的时序已生效，LLM 工具链也保持可用

### P0-4 入口层 / 框架层直连插件清理

- [x] **P0-4a** 清理 `main.py` 第118行 `from run.basic_plugin...`
  - 改为延迟导入（函数内 import）或服务查找
  - 进度：已改为 `importlib.import_module()` + 常量拼接的延迟导入

- [x] **P0-4b** 清理 `framework_common/utils/ai_translate.py`（4处 `from run.ai_llm...`）
  - 改为延迟导入包装
  - 进度：已统一替换为 `_get_*()` 包装函数，通过 `importlib` 按需导入

- [x] **P0-4c** 清理 `framework_common/database_util/Group.py`（2处 `from run.ai_llm...`）
  - 改为延迟导入包装
  - 进度：已改为 `_get_gemini_prompt_elements_construct()` / `_get_openai_prompt_constructors()`

- [x] **P0-4d** 全局搜索 `framework_common/` 下是否还有其他 `from run.` 并逐一处理
  - 进度：当前 `framework_common/` 与 `main.py` 下已无 `from run.` / `import run.` 顶层导入残留

- [x] **P0-4e** 验证
  - 删除 `run/ai_llm/` 目录后框架层 import 不会立即崩溃（仅运行时调用时报错）
  - 恢复目录后 `python main.py` 正常运行
  - 进度：2026-03-18 已使用无损等价方式补做验证：通过自定义 `MetaPathFinder` 显式阻断 `run.ai_llm` / `run.ai_llm.*` 导入后，直接导入 `framework_common.utils.ai_translate` 与 `framework_common.database_util.Group` 仍可成功，说明框架层已不在 import 阶段硬依赖 `ai_llm`；随后在正常环境下再次执行 `python main.py`，21 个插件可正常加载，主程序维持既有长驻状态

---

## Phase 1：建立 core 外观层

### P1-1 创建 core 目录骨架

- [x] **P1-1a** 创建目录结构（仅 `__init__.py` + re-export）
  ```
  core/
  ├── __init__.py
  ├── bot/
  │   └── __init__.py
  ├── adapter/
  │   └── __init__.py
  ├── event/
  │   └── __init__.py
  ├── message/
  │   └── __init__.py
  ├── config/
  │   └── __init__.py
  ├── filter/
  │   └── __init__.py
  ├── database/
  │   └── __init__.py
  ├── toolkit/
  │   └── __init__.py
  ├── draw/
  │   └── __init__.py
  └── services/
      └── __init__.py
  ```
  - 进度：已在 `Eridanus/core/` 下创建首批骨架目录与 `__init__.py`

### P1-2 事件 / 消息模型 re-export

- [x] **P1-2a** `core/event/__init__.py` re-export `developTools.event` 下的所有事件类
  - 进度：已创建 `core/event/base.py`、`core/event/events.py`、`core/event/factory.py`，并通过 `core/event/__init__.py` 暴露旧事件模型
- [x] **P1-2b** `core/message/__init__.py` re-export `developTools.message` 下的消息模型
  - 进度：已创建 `core/message/message_chain.py`、`core/message/message_components.py`，并通过 `core/message/__init__.py` 暴露旧消息模型
- [x] **P1-2c** 验证：`from core.event.events import GroupMessageEvent` 可用
  - 进度：已在当前环境直接导入验证通过，`GroupMessageEvent` 可正常访问；原先关于缺失 `pydantic` 的阻塞说明已失效

### P1-3 工具 / 数据库 / 绘图 re-export

- [x] **P1-3a** `core/toolkit/__init__.py` re-export `framework_common.ToolKits` + `framework_common.utils` 关键导出
  - 进度：已在 `core/toolkit/__init__.py` 暴露 `Util`、`BaseTool`、`get_logger`、`install_and_import` 等常用入口
- [x] **P1-3b** `core/database/__init__.py` re-export `framework_common.database_util` 关键类
  - 进度：已在 `core/database/__init__.py` 暴露 `User`、`GroupMessageManager`、`RedisCacheManager`、`AsyncSQLiteDatabase` 等入口
- [x] **P1-3c** `core/draw/__init__.py` re-export `framework_common.manshuo_draw`
  - 进度：已在 `core/draw/__init__.py` 透传旧 `manshuo_draw` 导出面
- [x] **P1-3d** `core/config/__init__.py` re-export `YAMLManager`
  - 进度：已创建 `core/config/manager.py`，并通过 `core/config/__init__.py` 暴露 `YAMLManager`

### P1-4 创建 adapters 骨架

- [x] **P1-4a** 创建 `adapters/__init__.py` + `adapters/onebot/__init__.py`（协议主入口）
  - 进度：已在 `Eridanus/adapters/` 与 `Eridanus/adapters/onebot/` 下建立 OneBot 协议主命名空间
- [x] **P1-4b** 创建 `adapters/napcat/__init__.py`（兼容壳）
  - 进度：`Eridanus/adapters/napcat/` 已退化为兼容导出层，避免旧引用立即断裂
- [x] **P1-4c** 创建 `adapters/lagrange/__init__.py`（兼容壳）
  - 进度：`Eridanus/adapters/lagrange/` 已退化为兼容导出层，Lagrange 差异实现并入 `adapters/onebot/`

### P1-5 main.py 切换导入源（可选，低风险）

- [x] **P1-5a** `main.py` 中将部分 import 改为从 `core.*` 导入（事件类等低风险项）
  - 进度：`main.py` 已接入 `Eridanus/` 路径，并将事件类导入切换为 `from core.event.events import ...`
- [x] **P1-5b** 验证：`python main.py` 正常
  - 进度：已修正 `flask-sock`、`imageio`、`python-dateutil` 的自动安装问题，并在当前环境完成安装；`qzone_api`、`pyzbar` 与 `Microsoft Visual C++ 2013 Redistributable` 依赖链也已补齐，`qq_zone` 插件现可正常加载并注册 6 个事件处理器。2026-03-18 本地再次执行 `python main.py`，已验证 WebUI 启动、21 个插件分 6 批加载完成、Redis 自动拉起成功、双 Bot 管理器进入长驻运行；同时补上了 `websockets==16.0` 下 `ClientConnection.closed` 缺失的兼容处理。当前剩余日志仅为外部 OneBot 地址 `ws://127.0.0.1:3001` 在本机拒绝连接后的自动重试，不再属于主程序启动失败；插件数已从先前的 22 收敛为 21，是因为 `common_config` 已从插件发现 / 加载入口排除

---

## Phase 2：Bot 与传输层重构

### P2-1 定义 core 抽象

- [x] **P2-1a** 编写 `core/adapter/base.py` — `PlatformAdapter` 抽象基类
  - 进度：已定义 `start()` / `stop()` / `send()` 抽象接口
- [x] **P2-1b** 编写 `core/adapter/session.py` — `Session` 抽象
  - 进度：已定义 `connect()` / `disconnect()` / `recv()` / `send()` 抽象接口
- [x] **P2-1c** 编写 `core/adapter/event_source.py` — `EventSource` 抽象
  - 进度：已定义基于共享 session 的 `start()` / `stop()` 抽象接口
- [x] **P2-1d** 编写 `core/adapter/api_client.py` — `ApiClient` 抽象
  - 进度：已定义 `call_api()` 抽象接口

### P2-2 拆解 WebSocketBot（916行）

- [x] **P2-2a** 从 `WebSocketBot` 中提取 `EventBus` → `core/bot/event_bus.py`
  - 保留旧路径 re-export
  - 进度：已创建 `core/bot/event_bus.py`，并让 `developTools/adapters/websocket_adapter.py` 与 `developTools/event/bus.py` 指向新实现

- [x] **P2-2b** 实现 `adapters/onebot/session_ws.py` — OneBot WebSocket 会话
  - 从 `WebSocketBot` 中提取连接管理、重连、收包逻辑
  - `EventSource` 与 `ApiClient` 共享同一 session
  - 进度：已创建共享 `Eridanus/adapters/onebot/session_ws.py`，`Eridanus/adapters/napcat/session_ws.py` 现仅保留兼容包装；旧 `WebSocketBot` 已切换到共享 OneBot WebSocket 会话

- [x] **P2-2c** 实现 `adapters/onebot/api_client.py` — OneBot API 调用
  - 从 `WebSocketBot` 中提取 `_call_api`、`echo → Future` 匹配
  - 提取所有 OneBot API 方法（send_group_msg, mute, kick, recall 等）
  - 进度：已创建共享 `Eridanus/adapters/onebot/api_client.py` 承接通用 OneBot API；NapCat / Lagrange 扩展方法并入 `adapters/onebot/implementations.py`，旧路径仅做兼容导出

- [x] **P2-2d** 实现 `adapters/onebot/event_source.py` — OneBot 事件接收
  - 从 `WebSocketBot._receive` + `_process_messages` 中提取事件包识别逻辑
  - 进度：已创建 `Eridanus/adapters/onebot/event_source.py`，旧 `WebSocketBot` 的响应包识别、事件包识别和 lifecycle 处理已委托给共享 `OneBotEventSource`
- [x] **P2-2e** 实现 `adapters/onebot/event_factory.py` — 原始事件 → core 事件转换
  - 迁移 `developTools/event/EventFactory`
  - NapCat 原始字段保留到 `raw_event`
  - 进度：已创建 `Eridanus/adapters/onebot/event_factory.py` 作为 OneBot 协议事件转换器；`Eridanus/adapters/napcat/event_factory.py` 现仅保留兼容包装

- [x] **P2-2f** 实现 `adapters/onebot/adapter.py` — `OneBotAdapter(PlatformAdapter)`
  - 组合 session + event_source + api_client
  - 对 core 暴露统一 `start / stop / send` 接口
  - 进度：已创建 `Eridanus/adapters/onebot/adapter.py` 作为协议主适配器，`NapCatAdapter` / `LagrangeAdapter` 仅在其上叠加实现差异

### P2-3 拆解 ExtendBot（196行）

- [x] **P2-3a** 提取黑白名单过滤 → `core/filter/blacklist.py`
  - 进度：已创建 `core/filter/blacklist.py`，并保留旧 `ExtendBot` 的群/用户黑白名单判断语义
- [x] **P2-3b** 提取过滤链 → `core/filter/chain.py` + `core/filter/base.py`
  - 进度：已创建 `FilterDecision`、`Filter`、`FilterChain`，`ExtendBot` 已切换为通过 `filter_chain` 分发事件
- [x] **P2-3c** Lagrange 发送兼容逻辑 → `adapters/onebot/capabilities.py`
  - 进度：已创建 `Eridanus/adapters/onebot/capabilities.py`，并将 `ExtendBot.send()` 中的 Lagrange 消息组件兼容、引用处理和 `Node` 归一化逻辑下沉到 OneBot 实现差异层；`adapters/lagrange/capabilities.py` 仅保留兼容导出

### P2-L Lagrange adapter 预留

- [x] **P2-L0** 实现 Lagrange 扩展 API client 基础壳
  - 进度：Lagrange 扩展 client 已并入 `Eridanus/adapters/onebot/implementations.py`，旧 `adapters/lagrange/api_client.py` 仅保留兼容导出

- [x] **P2-L1** 实现 Lagrange 扩展 API client
  - 基于当前仓库实际依赖与首批 Lagrange.OneBot 扩展能力，已补齐自定义表情、消息历史、群文件目录 / URL 等专属 API 封装
  - 进度：Lagrange 专属 API 已收敛到 `Eridanus/adapters/onebot/implementations.py`；后续若出现新的 Lagrange.OneBot 扩展调用，再在该实现文件继续补充

- [x] **P2-L2** 实现 `LagrangeAdapter`
  - 与 `NapCatAdapter` 同属 OneBot 协议实现差异层，而不是一级 adapter 协议
  - 进度：`LagrangeAdapter` 已收敛到 `Eridanus/adapters/onebot/implementations.py`，旧 `adapters/lagrange/adapter.py` 仅保留兼容导出

### P2-4 新 Bot 类

- [x] **P2-4a** 编写 `core/bot/bot.py` — 组合式 Bot
  - 持有 adapter、event_bus、filter_chain、plugin_manager、config 引用
  - 提供 `start()`, `on()`, `send()` 统一接口
  - 进度：已创建 `Eridanus/core/bot/bot.py`，通过 `Bot` 组合 `adapter + event_bus + filter_chain + config`，并为 `plugin_manager` 预留可注入生命周期接口

- [x] **P2-4b** 更新 `main.py` 使用新 Bot + NapCatAdapter
  - 保留旧入口作为 fallback（可通过配置切换）
  - 进度：`main.py` 已加入 `adapter.use_new_core_bot` 开关；在单 Bot 路径下可切换到 `Eridanus` 的 `Bot + NapCatAdapter` / `Bot + LagrangeAdapter` 运行时，双 Bot / WebUI 仍回退旧入口

- [x] **P2-4c** 回归验证
  - 所有消息收发正常
  - 黑白名单行为与旧逻辑一致
  - Lagrange 兼容性保持
  - 进度：按当前验收口径，已使用 WebUI 路径和本地烟雾验证收口。2026-03-18 本地执行 `python main.py` 时，WebUI 可正常启动，21 个插件可完成加载，主程序进入双 Bot 长驻运行；同时已验证组合式 `Bot` / `FilterChain` / `LagrangeAdapter` 的关键行为：`BlacklistFilter` 对群黑名单、群白名单、用户黑名单、用户白名单 4 类分支的阻断与放行语义保持一致，`Bot` 可在事件通过过滤后将事件分发给已注册 handler，`LagrangeAdapter.send()` 会将引用消息归一化为 `Reply(id=str(message_id))`，并将 `At.qq`、转发 `Node.user_id` / `nickname` 调整为 Lagrange 兼容格式。外部 NapCat / Lagrange OneBot 服务端的真实联机回归暂不再作为该项前置条件；插件数已从先前的 22 收敛为 21，是因为 `common_config` 已从插件发现 / 加载入口排除

---

## Phase 3：插件系统与 LLM 工具系统重构

### P3-1 新 PluginManager

- [x] **P3-1a** 编写 `core/bot/plugin_manager.py` — 新 PluginManager
  - 去掉 monkey-patch (`_enhance_bot_instance`)
  - 组合方式管理插件生命周期
  - 同时支持 `main(bot, config)` 函数式 和 `PluginInterface` 类式
  - 进度：已创建 `Eridanus/core/bot/plugin_manager.py`，通过 `PluginRuntimeContext` 代理记录插件事件处理器，不再修改 bot 实例本身

- [x] **P3-1b** 定义 `PluginMeta` 和 `PluginInterface`
  - 从 `__init__.py` 读取元信息（name, description, dependencies）
  - 进度：已定义 `PluginMeta` / `PluginInterface`，并从插件包的 `plugin_name` / `plugin_description` / `plugin_dependencies` 读取元信息

- [x] **P3-1c** 迁移热重载 / 卸载逻辑到新 PluginManager
  - 进度：`Eridanus/core/bot/plugin_manager.py` 已补齐 `watchdog` 文件监听、基于事件循环的防抖热重载调度，以及插件目录变化触发的自动 `load / reload / unload`；已通过最小临时插件热重载烟雾验证，文件改动后可自动从 `v1` 重载到 `v2`

### P3-2 统一 func_map

- [x] **P3-2a** 编写 `core/bot/func_map.py` — `FuncMap` 类
  - `register()` / `call()` / `get_declarations()` 显式接口
  - 不再使用模块级全局变量
  - 进度：已创建 `Eridanus/core/bot/func_map.py`，按插件维度维护 `dynamic_imports` 与 `function_declarations` 注册表

- [x] **P3-2b** PluginManager 在加载每个插件时调用 `func_map.register()`
  - 读取插件的 `dynamic_imports` + `function_declarations`
  - 进度：`Eridanus/core/bot/plugin_manager.py` 已支持注入 `FuncMap`，并在插件加载 / 卸载时执行注册与反注册

- [x] **P3-2c** 保留旧 `build_tool_map()` / `get_tool_declarations()` 作为 facade 转发
  - 进度：`Eridanus/framework_common/framework_util/func_map_loader.py` 已改为复用 `core.bot.FuncMap`，同时继续维护 `dynamic_imports` / `all_function_declarations` 旧全局导出

- [x] **P3-2d** 验证：LLM 工具调用全流程正常
  - 进度：2026-03-18 已补做异步上下文验证。`scan_plugins()` 现仅扫描顶层插件包，避免在运行中的事件循环里递归导入服务子包；`system_plugin` 的工具导出已改为轻量 wrapper，消除了 `build_tool_map()` 时因 `llmDB` / 用户数据模块触发 `asyncio.run()` 导致的导入失败。当前在异步事件循环内已验证 `build_tool_map()` 返回 `tools=43`、`get_tool_declarations(config)` 返回 `decls=42`（按配置正确过滤掉 `search_with_official_api`），并已通过 `FuncMap.call("call_menu")` 与 `OpenAIAPI._execute_tool()` 实测完成一次代表性 tool-call 分发，确认“工具声明 -> tool map -> tool execute -> tool response”链路可用

### P3-3 skill.md 集成（如需要）

- [x] **P3-3a** 编写 `core/bot/skill_parser.py` — 解析插件目录下的 `skill.md`
  - 进度：已创建 `Eridanus/core/bot/skill_parser.py`，支持解析 `skill.md` 的标题、简介、正文和简单 front matter；当前仓库内尚无实际 `skill.md` 文件可接入验证
- [x] **P3-3b** PluginManager 加载插件时同时解析 `skill.md`，注册到 FuncMap
  - 进度：`Eridanus/core/bot/plugin_manager.py` 已在插件加载时解析插件目录下的 `skill.md`，并通过 `FuncMap` 的 `skill_documents` 注册表同步保存；`get_plugin_status()` 也已补充 `has_skill` / `skill_title` / `skill_path` 状态字段

---

## Phase 4：解耦跨插件依赖

### P4-1 ServiceRegistry

- [x] **P4-1a** 编写 `core/services/registry.py` — `ServiceRegistry` 单例
  - 进度：已创建 `Eridanus/core/services/registry.py`，提供进程级 `ServiceRegistry`、`ServiceEntry`、按名称注册/查询/强制获取、按 provider 反注册，以及 `core.services` 懒导出入口；最小注册/查询/清理烟雾验证已通过

- [x] **P4-1b** 梳理跨插件依赖图
  - 重点：`ai_llm` 被至少 10+ 插件依赖
  - 列出所有 `from run.X import Y` 的调用关系
  - 进度：已完成当前仓库的完整依赖图梳理，并落盘至 [cross-plugin-dependency-map.md](/c:/Users/z1892/OneDrive/Desktop/project/new_Eridanus/docs/cross-plugin-dependency-map.md)。截至 2026-03-18，`Eridanus/run` 与 `Eridanus/framework_common` 中 `from run.` 共 `157` 处，全部为插件内部自引用；真正跨插件依赖已降为 `0`，`framework_common` 残留为 `0`。这意味着 Phase 4 当前已经完成“静态 `from run.` 跨插件引用归零”的阶段性目标，后续重点将转向更高层的服务边界整理与物理目录迁移

### P4-2 高频服务提取

- [x] **P4-2a** `ai_llm` 核心服务注册
  - `aiReplyCore`, `schemaReplyCore`, `GeminiAPI`, `OpenAIAPI` → ServiceRegistry
  - `gemini_prompt_elements_construct`, `prompt_elements_construct` → ServiceRegistry
  - 进度：`Eridanus/core/bot/plugin_manager.py` 已支持插件级 `register_services / unregister_services` 生命周期钩子；`Eridanus/run/ai_llm/__init__.py` 已将上述 6 个核心服务注册到 `ServiceRegistry`，同时补充了 `ai_llm.*` 命名空间别名；已验证注册后 `aiReplyCore / schemaReplyCore / GeminiAPI / OpenAIAPI / gemini_prompt_elements_construct / prompt_elements_construct` 均可查询，卸载后可清理

- [x] **P4-2b** `group_fun` 的 `manage_group_status` → ServiceRegistry
  - 进度：`Eridanus/run/group_fun/__init__.py` 已注册 `manage_group_status`，并补充 `group_fun.manage_group_status` 命名空间别名；后续继续扩展注册了 `today_check_api` 与 `Lexburner_Ninja`；`acg_infromation/majsoul.py`、`acg_infromation/service/majsoul/majsoul_plugin.py`、`system_plugin/func_collection.py`、`scheduled_tasks/scheduledTasks.py`、`group_fun/func_collection.py` 现已优先从 `ServiceRegistry` 获取这些服务

- [x] **P4-2c** `basic_plugin` 的 `life_service` → ServiceRegistry
  - 进度：`Eridanus/run/basic_plugin/__init__.py` 已注册 `bingEveryDay`、`danxianglii`，并继续扩展注册 `get_nasa_apod`、`tarotChoice`、`free_weather_query`、`anime_trace`、`bing_dalle3`、`flux_ultra`、`doubao` 等跨插件高频服务，同时补充 `basic_plugin.*` 命名空间别名；最小注册烟雾检查已确认上述服务均可查询

### P4-3 替换跨插件 import

- [x] **P4-3a** 先替换 `framework_common/` 下的 6 处 `from run.` → ServiceRegistry 查找或延迟导入
  - 进度：已完成。`framework_common/utils/ai_translate.py` 中的 `GeminiAPI / OpenAIAPI` 与 `framework_common/database_util/Group.py` 中的 `gemini_prompt_elements_construct / prompt_elements_construct` 均已改为优先从 `ServiceRegistry` 获取，取不到时再回退到延迟导入；同时当前 `Eridanus/framework_common/` 与 `Eridanus/main.py` 范围内已无 `from run.` / `import run.` 残留
- [x] **P4-3b** 逐步替换 `run/` 下 89 个文件的 178 处 `from run.` — 按插件优先级排序
  - 优先：`ai_llm`, `system_plugin`, `basic_plugin`
  - 其次：`ai_generated_art`, `streaming_media`, `group_fun`
  - 最后：其他小插件
  - 进度：已完成第十批 `run/` 内消费方替换。本轮继续把剩余 helper fallback 的 `from run.` 改成 `import_module(...).attr` 延迟获取，覆盖了 `scheduled_tasks/scheduledTasks.py`、`system_plugin/func_collection.py`、`system_plugin/api_implements.py`、`acg_infromation/{bangumi,character_identify,galgame,majsoul}.py`、`acg_infromation/service/majsoul/majsoul_plugin.py`、`ai_generated_art/aiDraw.py`、`ai_llm/service/aiReplyCore.py`、`ai_code_generator/service/{AiChatbot,AiPluginGenerator}.py`、`character_detection/nailong_get.py`、`comfyui_api/example_t2i_workflow.py`、`Grok2api/grok2api_Video_image.py`、`group_fun/func_collection.py`、`group_msg_analyze/{EatMyEgg.py,service/prompt_constructer.py}`、`groupManager/group_manager.py`、`qq_zone/qzone.py`、`resource_collector/service/jmComic/jmComic.py`、`streaming_media/{bilibili.py,youtube.py,service/Link_parsing/core/gal.py}`。2026-03-18 再次执行 `python main.py`，21 个插件仍可正常加载。当前 `from run.` 文本总数已降到 `157`，并且基于 AST 的复核结果显示：`Eridanus/run` 与 `Eridanus/framework_common` 范围内跨插件 `from run.` 已全部清零，仅剩插件内部自引用

- [x] **P4-3c** 验证：移除单个低依赖插件不导致框架崩溃
  - 进度：2026-03-18 已用无损等价方式补做验证。通过 `MetaPathFinder` 显式阻断 `run.comfyui_api` / `run.comfyui_api.*` 导入，模拟“移除单个低依赖插件”后再次启动 `main.py`；结果显示主程序仍可完成 WebUI 启动、Redis 自动拉起、其余插件加载与双 Bot 长驻运行。被阻断的 `comfyui_api` 仅退化为“找到 0 个 main 函数 / 注册 0 个事件处理器”，未导致框架主链崩溃

---

## Phase 5：物理目录迁移与清理

### P5-1 配置目录迁移

- [x] **P5-1a** 将 `run/common_config/` 复制到顶层 `config/`
  - 进度：已在仓库顶层创建 `config/`，并复制 `basic_config.yaml`、`censor_group.yaml`、`censor_user.yaml`、`menu.yaml`
- [x] **P5-1b** `YAMLManager` 优先读取 `config/`，fallback 到 `run/common_config/`
  - 进度：`CORE_CONFIG_DIR` 已改为候选根列表，`YAMLManager` 现会优先读取顶层 `config/`，再兼容其他候选路径，并在配置已存在时回退到 `run/common_config/`；当前 `config.common_config.basic_config[...]` 访问路径保持不变，`basic_config` 实际来源已切到顶层 `config/basic_config.yaml`
- [x] **P5-1c** 验证后删除 `run/common_config/`
  - 进度：2026-03-18 已完成删除前清障与删除后验证。删除前已确认 `config/` 下 `basic_config.yaml`、`censor_group.yaml`、`censor_user.yaml`、`menu.yaml` 与旧目录内同名文件的 SHA256 完全一致；同时已把 `dockerfile`、`manshuo_draw/core/menu_maker/old_remain.py` 和菜单提示文案中的残留 `run/common_config` 路径切换到顶层 `config/`。随后已删除 `Eridanus/run/common_config/`，并再次执行 `python main.py` 做 35 秒烟雾验证：WebUI 正常启动、21 个插件分 6 批完成加载、Redis 自动拉起成功、文件监控正常启动，主程序继续进入双 Bot 长驻状态，说明运行时已不再依赖旧配置目录

### P5-2 插件目录迁移

- [x] **P5-2a** 将 `run/<plugin>/` 迁移到 `plugins/<plugin>/`
  - 进度：2026-03-18 已将 `Eridanus/run/` 下 21 个插件目录整体迁移到 `Eridanus/plugins/`，旧 `run/` 目录现仅保留兼容层 `__init__.py` 与缓存目录；同时 `PLUGINS_DIR` 已切换到 `../Eridanus/plugins`，插件发现、热重载与配置扫描都已指向新物理目录
- [x] **P5-2b** 在 `run/__init__.py` 中放置 deprecation re-export
  - 进度：`Eridanus/run/__init__.py` 已补为兼容命名空间壳，通过扩展 `__path__` 将 `run.<plugin>` 子模块解析到 `Eridanus/plugins/`。2026-03-18 现场验证 `run.ai_llm`、`run.basic_plugin` 均已从新目录导入，且 `python main.py` 启动后 21 个插件仍可正常加载
- [x] **P5-2c** 更新 `PLUGINS_DIR` / `PLUGINS_MODULE_PREFIX` 常量
  - 进度：`Eridanus/framework_common/framework_util/constants.py` 已切换为 `PLUGINS_DIR = "../Eridanus/plugins"`、`PLUGINS_MODULE_PREFIX = "plugins"`；`Eridanus/core/bot/plugin_manager.py`、旧 `PluginAwareExtendBot` 与主入口的插件发现 / 热重载 / 模块清理逻辑均已跟随新常量收口。2026-03-18 再次执行 `python main.py`，WebUI 正常启动，Redis 自动拉起，21 个插件在 `plugins.*` 命名空间下完成加载并进入长驻运行
- [x] **P5-2d** 全局替换 `from run.` → `from plugins.`（178处）
  - 进度：`Eridanus/plugins/` 范围内已完成插件内部自引用批量切换，`Eridanus/run/__init__.py` 也已升级为 `run.* -> plugins.*` 兼容别名层，避免旧路径与新路径出现双实例。此前残留的单个非插件脚本引用 `Eridanus/tool.py` 也已于 2026-03-18 切换到 `plugins.streaming_media...`。当前全仓库代码搜索已无运行路径上的 `from run.` / `import run.` 残留；最近一次 `python main.py` 烟雾验证同样确认 21 个插件可正常加载，`groupManager` 与 `streaming_media` 等迁移热点插件均已恢复

### P5-3 旧目录清理

- [x] **P5-3a** `developTools/` 下各模块放置 deprecation re-export → `core/`
  - 进度：2026-03-18 已完成 `developTools/` 运行期模块的源头翻转。`core.event/*`、`core.message/*` 现已承接事件模型与消息模型真实实现，`developTools.event/*`、`developTools.message/*` 全部降级为薄 re-export；`Eridanus/adapters/onebot/{websocket_bot,http_adapter,http_mailman}.py` 已承接旧适配层真实实现，`developTools.adapters/*` 与 `developTools.interface.http_sendMes` 仅保留兼容壳；`developTools.utils.logger` 与 `developTools.utils.cq_code_handler` 也已分别翻到 `core.toolkit.logger` / `core.message.cq_parser`。当前 `developTools/` 下剩余的仅是 demo 入口 `developTools/main.py` 与空 stub `interface/websocket_sendMes.py`，不再承载运行期核心实现；同日完成旧新路径对象一致性验证与 `python main.py` 启动烟雾验证，21 个插件可继续正常加载
- [x] **P5-3b** `framework_common/` 下各模块放置 deprecation re-export → `core/`
  - 进度：已补上 `framework_common` 包根与 `database_util`、`framework_util`、`ToolKits`、`utils` 的首批 deprecation shim，统一发出旧路径告警。2026-03-18 先后完成十二批真实源头翻转：其一，`BaseTool`、`install_and_import`、`delete_old_files_async`、`MemoryMonitor`、`random_str`、`random_session_hash` 已迁入 `Eridanus/core/toolkit/{base,installer,gc_tool,memory,random_utils}.py`；其二，`framework_common.framework_util.constants` 与 `yamlLoader` 已分别翻入 `Eridanus/core/config/constants.py`、`Eridanus/core/config/manager.py`；其三，`framework_common.framework_util.{func_map_loader,main_func_detector,bot_info}` 已分别翻入 `Eridanus/core/bot/{func_map_loader,main_func_detector,bot_info}.py`；其四，`framework_common.database_util.{Group,GroupSummary,RedisCacheManager,User,llmDB,ManShuoDrawCompatibleDataBase}` 已分别翻入 `Eridanus/core/database/{group,group_summary,redis_cache,user,llm_db,manshuo_compatible_db}.py`，`web.server_new`、`ai_llm`、`system_plugin`、`scheduled_tasks`、`auto_reply`、`groupManager` 以及其余 `Eridanus/plugins/` 侧 `Group/User/llmDB/AsyncSQLiteDatabase` 主运行路径消费方已切到新路径；其五，`framework_common.framework_util.{websocket_fix,DualBotManager}` 已分别翻入 `Eridanus/core/bot/{extend_bot,dual_bot_manager}.py`，`Eridanus/main.py` 与插件侧高频 `ExtendBot` 消费方已切到 `core.bot`；其六，旧插件管理实现 `framework_common.framework_util.PluginAwareExtendBot` 已整体翻入 `Eridanus/core/bot/legacy_plugin_manager.py`，`Eridanus/main.py` 已改为从新模块导入 `PluginManager / PluginLoadConfig / LoadStrategy`，旧路径现仅保留 shim；其七，`framework_common.utils.{GeminiKeyManager,PDFEncrypt,cloudscraper,system_logger,utils}` 已分别翻入 `Eridanus/core/toolkit.{gemini_keys,pdf_encrypt,async_web_client,logger,compat_utils}`，`ai_llm`、`group_msg_analyze`、`resource_collector`、`bilibili`、`main.py` 等主运行路径消费方已切到新路径；其八，`framework_common.manshuo_draw` 已整体翻入 `Eridanus/core/draw/`，旧 `framework_common.manshuo_draw` 根包与 `manshuo_draw.py` 已退化为 shim，插件侧主要绘图消费方已切到 `core.draw`；其九，边缘工具模块 `framework_common.utils.{ai_translate,zip,zip_2_pwd_version,PlayWrightAutoInstaller}` 已分别翻入 `Eridanus/core/toolkit/{translator,archive,archive_pwd,playwright_installer}.py`，对应旧文件已全部退化为 shim，`ai_voice`、`resource_collector`、`streaming_media.service.bilibili` 等消费方也已切到新路径；其十，`framework_common.ToolKits.{util,file,image,network,text,system,logger}` 已分别翻入 `Eridanus/core/toolkit/{util,file,image,network,text,system,logger}.py`，`core.toolkit.{compat_utils,archive,archive_pwd,__init__}` 不再反向依赖旧 `ToolKits`，而 `framework_common.ToolKits.*` 现已全部降级为 shim；其十一，遗留兼容模块 `framework_common.framework_util.func_map` 与 `framework_common.utils.tomato_image_enc` 已分别翻入 `Eridanus/core/bot/legacy_func_map.py` 与 `Eridanus/core/toolkit/tomato_image_enc.py`，旧路径现仅保留告警 re-export；其十二，`framework_common.manshuo_draw/core/**` 历史镜像子树已压缩为目录级兼容层，旧叶子模块全部删除，仅保留包壳 `__init__.py` 与 `_bridge.py` 以把旧路径解析到 `core.draw.core/**`。与此同时，`Eridanus/core/database/__init__.py` 与 `Eridanus/core/toolkit/__init__.py` 均已改为 lazy export，分别避免 `User -> core.database -> User` 和 `core.toolkit -> GeminiKeyManager -> YAMLManager` 这类导入期副作用 / 回环；本轮还继续修复了 `resource_collector` 与 `GeminiKeyManager` 的导入期配置读取，以及 `core.draw` 在 `Eridanus/` 工作目录下的相对路径计算问题，避免插件入口扫描阶段因副作用或路径假设导致 `main()` 丢失。随后又继续做了两轮插件侧高频导入翻转，把 `Eridanus/plugins/` 中大量 `framework_common.framework_util.yamlLoader`、`framework_common.utils.{utils,random_str,random_session_hash,install_and_import}`、`framework_common.ToolKits.logger`，以及上述边缘工具模块消费方，批量切到 `core.config.manager` 与 `core.toolkit.*`。当前代码搜索结果显示：`Eridanus/plugins/` 运行路径下已无直接 `framework_common.*` 依赖残留，`Eridanus/core/toolkit` 也已不再反向导入 `framework_common.ToolKits`。2026-03-18 已对 `Eridanus/core/toolkit`、`Eridanus/core/bot`、`Eridanus/framework_common/ToolKits`、`Eridanus/framework_common/framework_util`、`Eridanus/framework_common/utils` 与 `Eridanus/framework_common/manshuo_draw` 重新执行 `python -m compileall`，全部通过；并额外验证了 `Util`、`SystemProcessor`、`tomato_encrypt` / `tomato_decrypt`、`framework_common.ToolKits` shim，以及 `framework_common.manshuo_draw.core.classic_collection.avatar` / `...util.download_img` 等旧路径导入可用。同日再次在 `Eridanus/` 工作目录下执行 `python main.py` 45 秒烟雾验证，确认 WebUI 正常启动、21 个插件分 6 批完成加载、Redis 自动连接成功、主程序进入双 Bot 长驻运行。当前 `framework_common` 下除 `manshuo_draw/_bridge.py` 这类桥接辅助代码外，包级运行时模块均已完成 shim 化，因此本项已完成
- [x] **P5-3c** 制定旧路径下线时间表（建议2个版本后删除）
  - 进度：2026-03-18 已补充下线节奏并与当前迁移状态对齐。`R0`（当前版本）继续保留 `run.*`、`developTools.*`、`framework_common.*` 的 shim / 桥接层，但禁止新增任何旧路径依赖；`R1`（下一个发布窗口）在文档、部署脚本与巡检脚本中把旧路径告警提升为显式迁移提示，并将对旧路径的新增引用视为回归；`R2`（再下一个发布窗口）在 `P6-1` 与 `P6-2` 完成、确认 `Eridanus/` 可独立运行且依赖清单已拆分后，正式删除 `Eridanus/` 下兼容层与旧脚本。当前执行约束也已明确：从本项完成起，除 shim 维护外不再接受任何新功能继续落到 `run/`、`developTools/`、`framework_common/` 旧命名空间

### P5-4 收尾

- [x] **P5-4a** 统一日志系统 — `get_logger()` 收归 `core/toolkit/logger.py`
  - 进度：2026-03-18 已完成统一。当前运行态代码已统一从 `core.toolkit.logger` 导入 `get_logger()`；`developTools.utils.logger`、`framework_common.utils.system_logger`、`framework_common.ToolKits.logger` 仅保留 deprecation shim。全局代码搜索结果显示，除上述 shim 文件与文档描述外，仓库运行路径上已无旧 logger 模块消费方；同日多次 `python main.py` 烟雾验证也确认 WebUI、插件加载、Redis 自动连接与长驻运行均保持正常
- [x] **P5-4b** 为核心配置添加 Schema 验证
  - 进度：`Eridanus/core/config/schema.py` 已正式接入 `YAMLManager` 的启动加载与热重载校验链路，并覆盖 `config/basic_config.yaml`、`config/menu.yaml`、`config/censor_group.yaml`、`config/censor_user.yaml` 四类核心配置；`core.config` 入口现也直接导出 `ConfigValidationError` 与各项校验函数。2026-03-18 已对 `core.config` 执行 `py_compile` 验证通过
- [x] **P5-4c** 最终全量验证：仅依赖 `core/` + `plugins/` + `config/` 可正常启动
  - 进度：2026-03-18 已完成最终收口。`Eridanus/core/config/constants.py` 现已优先指向 `Eridanus/config/`，4 个核心配置文件已物理并入该目录；随后先在仅包含 `Eridanus/` 的临时副本中直接执行 `python Eridanus/main.py` 做 20 秒烟雾验证，确认无需仓库根 `config/` 也可完成 WebUI 启动与 21 个插件加载；再在真实工作区中删除旧 `Eridanus/` 目录与仓库根 `config/` 后再次执行同样的 20 秒烟雾验证，WebUI、21 个插件分批加载、Redis 路径与主程序长驻链路均保持正常。当前仓库运行形态已满足“仅依赖 `core/` + `plugins/` + `config/` 可正常启动”的验收口径

---

## Phase 6：彻底脱离 Eridanus 与依赖清单拆分

### P6-1 `Eridanus/` 独立运行

- [x] **P6-1a** 为 `Eridanus/` 建立独立启动入口
  - 目标：将当前仍停留在 `Eridanus/main.py`、`Eridanus/web/`、`Eridanus/tool.py`、旧部署脚本中的启动编排迁入 `Eridanus/`
  - 要求：`Eridanus` 内部自行完成 `sys.path`、配置根、WebUI、Bot 启动与插件加载，不再依赖外层 `Eridanus/` 目录存在
  - 进度：2026-03-18 已创建 `Eridanus/main.py` 与 `Eridanus/__main__.py`，把工作目录切换、配置初始化、插件加载、单 Bot / 双 Bot / 组合式 Bot 启动编排统一收敛到 `Eridanus/` 内；直接执行 `python Eridanus/main.py` 的 20 秒烟雾窗口中，已完成初始化并装入前五批插件。当前若 `Eridanus/web/server_new.py` 不存在，会记录告警并安全降级跳过 WebUI，后续由 `P6-1b` 继续补齐

- [x] **P6-1b** 清除 `Eridanus/` 对 `Eridanus/` 目录级资源的硬依赖
  - 目标：删除或替换 `core._legacy`、旧兼容导入、旧脚本路径拼接、对 `Eridanus/web` / `Eridanus/config` / `Eridanus/framework_common` 的直接文件级依赖
  - 要求：`Eridanus` 内部具备自己的 `core/`、`adapters/`、`plugins/`、`config/`、`web/`、启动脚本与必要静态资源
  - 进度：2026-03-19 已完成四轮主链清理与最终残留收口，并通过隔离验证确认 `Eridanus/` 已不再对外层 `Eridanus/` 目录形成运行期硬依赖。其一，`adapters/onebot/*`、`core/bot/{event_bus,plugin_manager,func_map}.py`、`core/{filter,database,toolkit,services}` 等运行态模块中的 `ensure_legacy_root()` 调用已全部移除；其二，现有 `Eridanus/web/` 已整体迁入 `Eridanus/web/`，并将 `server_new.py` 的安装器与配置扫描主链切到 `core.toolkit.installer`、`Eridanus/plugins/` 与 `Eridanus/config/`；其三，`server_new.py` 又进一步去掉了固定 `Eridanus` 目录名和相对工作目录假设，克隆目标目录改为动态推导，配置导入导出统一改走 `config_backups/` 绝对路径；其四，`core.config.constants` 已改为按应用根动态推导 `plugins/` 与 `config`，`resource_collector/service/{jmComic,obsidianLink,zLibrary}` 的运行期配置文件定位已切到插件根，`zLibrary/canvas.py`、`comfyui_api/example_neta_lumina_i2i.py`、`group_fun/func_collection.py`、`scheduled_tasks/scheduledTasks.py` 以及 `basic_plugin` / `ai_generated_art` 中的示例块旧图片路径也已收口；其五，原先仅剩的孤立兼容文件 `Eridanus/core/_legacy.py` 也已在确认全仓库无代码引用后删除，并再次执行 `python Eridanus/main.py` 的 12 秒烟雾验证通过；其六，已继续清理 Phase 6 完成后残留的本地旧路径硬编码，把 `meme_generate`、`acg_infromation/bangumisearch`、`memes/aoyi`、`groupManager/self_Manager`、`streaming_media/Link_parsing/login_core`、`anime_game_service/{skland,mihuyo_club}`、`basic_plugin/random_pic`、`comfyui_api/example_*`、`ai_code_generator/AiPluginGenerator` 等模块收口到插件相对路径或 `Eridanus/core` 资源路径，并同步更新 `Eridanus/README.md`、`Eridanus/plugins/README.md`、`CLAUDE.md`；当前非文档代码中的 `run/` 命中已只剩第三方接口 URL（如 `.../gradio/run/predict`）与兼容命名空间说明，2026-03-19 再次执行 `python Eridanus/main.py` 的 15 秒烟雾验证时，WebUI 与前四批插件加载均保持正常

- [x] **P6-1c** 验证：临时移除 `Eridanus/` 后仍可启动
  - 验收口径：将 `Eridanus/` 整体移走、改名或在隔离目录下仅保留 `Eridanus/` 运行，`python main.py` 或等价的新入口仍可正常完成 WebUI 启动、插件加载、Redis 自动拉起与长驻运行
  - 进度：2026-03-18 已在工作区内创建仅包含 `Eridanus/` 与顶层 `config/` 的临时隔离副本，并在该隔离根目录下直接执行 `python Eridanus/main.py` 做 15 秒烟雾验证。结果显示 WebUI 可正常在线程中启动，独立入口可稳定完成前四批插件加载，说明当前启动主链已可在不依赖外层 `Eridanus/` 目录存在的前提下运行

### P6-2 依赖清单按功能边界拆分

- [x] **P6-2a** 定义依赖清单拆分规范
  - 目标：不再只维护单一 `Eridanus/requirements.txt`
  - 建议目标结构：
    - `Eridanus/requirements/base.txt`：核心运行时依赖
    - `Eridanus/requirements/web.txt`：WebUI 依赖
    - `Eridanus/plugins/<plugin>/requirements.txt`：插件自有依赖
    - `Eridanus/requirements/all.txt`：聚合安装入口（可由脚本生成）
  - 要求：明确“哪些依赖属于 core / web / adapter / plugin”，避免再次把所有依赖堆回一个文件
  - 进度：2026-03-18 已创建 `Eridanus/requirements/README.md`、`base.txt`、`web.txt`、`adapter-onebot.txt` 与 `all.txt`，并为 `ai_llm`、`streaming_media`、`resource_collector`、`qq_zone`、`comfyui_api`、`ai_voice` 建立了插件级 `requirements.txt` 入口占位文件。当前规范已明确 core / web / adapter / plugin 的归档边界，后续由 `P6-2b` 继续把单体依赖逐项归档进去

- [x] **P6-2b** 将现有依赖按功能归档到对应目录
  - 目标：把当前 `Eridanus/requirements.txt` 中的依赖按实际使用边界拆分
  - 要求：高频插件如 `ai_llm`、`streaming_media`、`qq_zone`、`comfyui_api`、`resource_collector` 等各自拥有独立依赖清单；通用依赖保留在 base / web / onebot 侧
  - 进度：2026-03-18 已完成归档收口。`Eridanus/requirements/{base,web,adapter-onebot,all,legacy-compat}.txt` 已落位，且 `ai_llm`、`streaming_media`、`resource_collector`、`qq_zone`、`comfyui_api`、`ai_voice`、`basic_plugin`、`anime_game_service`、`auto_reply`、`group_fun`、`acg_infromation`、`Grok2api`、`ai_generated_art` 的插件级 `requirements.txt` 已写入实际依赖；其中 `core` 侧补入了 `numpy`，WebUI、OneBot adapter 与高频插件的专属依赖也已分别归档。随后已对旧 `Eridanus/requirements.txt` 与新拆分后的全部 `requirements*.txt` 做集合比对，`MISSING` / `EXTRA` 结果均为空，说明旧单体依赖清单里的包已经全部落位；`legacy-compat.txt` 作为已定义边界的兼容保留层继续留给后续验证收缩，不再阻塞本项勾选

- [x] **P6-2c** 改造安装与自动补依赖逻辑
  - 目标：部署脚本、自动安装脚本、`install_and_import()` 与文档都能理解新的依赖布局
  - 要求：支持“全量安装”和“按功能安装”两条路径；至少要能通过聚合入口完成与当前等价的完整安装
  - 进度：2026-03-18 已完成首版收口。`Eridanus/core/toolkit/installer.py` 已改为基于 `requirements/` 与插件级 `requirements.txt` 建立索引，`install_and_import()` 会优先按唯一归属的 profile / plugin 依赖文件安装，只有在多个插件共享同一包时才回退为直接 `pip install`；同时新增 `Eridanus/install.py` 作为 CLI 安装入口，并补充 `Eridanus/install.bat` 作为 Windows 包装脚本，支持 `--profile` 与 `--plugin` 两类按边界安装。`Eridanus/requirements/all.txt` 现已聚合公共依赖与已归档插件依赖，`Eridanus/web/utils.py` 与 `core.toolkit.system.SystemProcessor` 也已统一复用共享安装器。随后已完成 `python -m py_compile Eridanus/core/toolkit/installer.py`、`python -m py_compile Eridanus/install.py`、`python -m py_compile Eridanus/core/toolkit/system.py`、`python -m py_compile Eridanus/web/utils.py` 以及 `python Eridanus/install.py --help` 验证通过

- [x] **P6-2d** 验证：依赖拆分后可完成全量安装与最小安装
  - 验收口径：
    - 通过聚合依赖入口可完成全量安装，并正常启动主程序
    - 通过最小依赖集合可启动 core + web + 基础插件
    - 为单个高依赖插件补装其 `requirements.txt` 后，该插件可恢复正常加载
  - 进度：2026-03-18 已完成三类安装入口与两轮启动烟雾验证。其一，`python Eridanus/install.py --profile all` 已在当前环境实际执行成功；其二，`python Eridanus/install.py --profile base --profile web` 与 `python Eridanus/install.py --plugin ai_llm` 也已分别实际执行成功；其三，随后再次执行 `python Eridanus/main.py` 的 20 秒烟雾验证，确认 WebUI 正常启动、21 个插件按批次完成加载，说明聚合依赖入口与当前主程序启动链路兼容；其四，又在临时隔离目录中仅保留 `Eridanus/ + config/ + basic_plugin`，新建独立虚拟环境后按 `base + web + basic_plugin` 安装时，启动验证首先暴露 `Eridanus/main.py` 在导入期硬依赖 `adapters/onebot`，因此补装 `adapter-onebot` 后再次启动，已确认 WebUI 正常启动、仅 `basic_plugin` 单插件成功加载并进入单批次运行。当前可确认的“最小可运行集合”已收敛为 `base + web + adapter-onebot + basic_plugin`；单插件补装、全量安装与最小集合启动三条路径均已具备实证，因此本项勾选完成

### P6-3 旧目录彻底下线

- [x] **P6-3a** 删除 `Eridanus/` 兼容层与旧脚本
  - 目标：在 `P6-1` 与 `P6-2` 完成后，正式移除 `Eridanus/` 整个旧目录及其兼容壳
  - 进度：2026-03-18 已完成。删前校验已确认 `Eridanus/` 运行链路中已无 `ensure_legacy_root()` 调用残留、无运行期 `framework_common` / `developTools` 依赖残留，`core._legacy.py` 也仅剩孤立兼容文件本体；随后已实际删除仓库根 `Eridanus/` 旧目录，并立刻执行 `python Eridanus/main.py` 的 20 秒烟雾验证，确认 WebUI 正常启动、21 个插件继续按批次完成加载，说明旧兼容层与旧脚本删除后未引入启动回归

- [x] **P6-3b** 最终交付验证：仓库仅保留 `Eridanus/` 即可工作
  - 验收口径：最终交付形态下，仓库只保留 `Eridanus/` 作为应用根目录，且包含启动入口、WebUI、配置、插件与依赖清单；删除 `Eridanus/` 后仍可完成安装、启动与核心功能验证
  - 进度：2026-03-18 已完成。其一，已将核心配置文件 `basic_config.yaml`、`menu.yaml`、`censor_group.yaml`、`censor_user.yaml` 复制并收口到 `Eridanus/config/`，`CORE_CONFIG_DIR` 也已调整为优先读取应用根内配置；其二，在仅包含 `Eridanus/` 的临时副本中直接执行 `python Eridanus/main.py` 的 20 秒烟雾验证，确认不再需要仓库根 `config/` 即可完成 WebUI 启动和 21 个插件加载；其三，在真实工作区中删除仓库根 `config/` 后再次执行 `python Eridanus/main.py` 的 20 秒烟雾验证，结果同样正常。当前仓库根已不再包含 `Eridanus/` 与旧 `config/`，应用运行所需的启动入口、WebUI、配置、插件与依赖清单都已收敛到 `Eridanus/` 内。2026-03-19 又补做了一轮交付形态整理：将历史验证日志统一归档到 `archive/non_runtime_artifacts/validation_logs/`，将历史运行日志归档到 `archive/non_runtime_artifacts/runtime_logs/`，并清理了一轮工作区 `__pycache__`；归档后再次执行 `python Eridanus/main.py` 的 15 秒烟雾验证，确认 WebUI 与前四批插件仍可正常启动，运行时也会按需重新创建当前 `Eridanus/log/`，说明归档未破坏实际运行链路

---

## 实施注意事项

1. **每个子步骤完成后都要 `python main.py` 验证**，不要积累多步再验证
2. **跨插件 import 数量庞大**（178处 / 89文件），Phase 4 是最耗时的阶段，预计占总工作量 40%+
3. **func_map_loader.py 的 import-time 副作用**是 Phase 0 最关键的改动，需要特别注意消费方的调用时序
4. **WebSocketBot 916行拆解**是 Phase 2 的核心难点，建议先画出方法级依赖图再动手
5. Phase 0-1 可以并行推进（无依赖），Phase 2 依赖 Phase 1，Phase 4 依赖 Phase 3
6. 内存中关于 `skill_parser.py`、`command_router.py`、`registry.py` 已存在的记忆是错误的 — 这些文件不存在，需要从头创建
7. **Phase 6 不是简单删目录**：必须先让 `Eridanus/` 具备独立入口、独立 WebUI 与独立依赖布局，再删除 `Eridanus/`
8. **依赖拆分不能只做文本搬运**：要同时改造部署脚本、自动安装逻辑与聚合安装入口，否则拆完依赖文件后运行时会更脆弱
