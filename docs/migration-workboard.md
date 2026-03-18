# Eridanus 迁移工作台

本文件基于 `docs/refactoring-todo.md` 的目标，按实际执行顺序重组，目的是把“重构计划”变成“可连续交付的任务流”。

> 2026-03-19 备注：迁移后的应用根目录已从 `newEridanus/` 更名回 `Eridanus/`。工作台中涉及“旧 `Eridanus/`”的历史记录，指的是迁移前目录树；当前 `Eridanus/` 指的是已经完成重构承载的现行应用根。

## 当前判断

结合仓库现状，以下事项已经部分落地：

- `Eridanus/framework_common/framework_util/constants.py` 已存在，并定义了 `PLUGINS_DIR` 与 `PLUGINS_MODULE_PREFIX`
- `Eridanus/main.py` 已改为从常量读取插件目录，并在插件加载后显式调用 `scan_plugins()`
- `Eridanus/framework_common/utils/ai_translate.py` 与 `Eridanus/framework_common/database_util/Group.py` 已将部分 `from run...` 改为延迟导入

因此真正的首批工作不是“重复修改已完成项”，而是把剩余缺口整理成明确批次。

## 执行顺序

### Batch A: 运行时解耦收尾

目标：让旧工程不依赖写死的 `run` 目录语义，并压缩 import-time 副作用。

任务：

- A1. 复核 `PluginAwareExtendBot.py` 中所有插件目录扫描、模块缓存清理、热重载路径判断，确保只依赖 `plugins_dir` 与 `plugins_module_prefix`
- A2. 复核 `main_func_detector.py`，把 `character_detection` 这类特殊前缀判断改为基于通用常量
- A3. 阅读并改造 `yamlLoader.py`，支持核心配置与插件配置的多根加载，但保留旧访问路径
- A4. 全局扫描 `Eridanus/framework_common/`，继续清理剩余 `from run.` 顶层导入
- A5. 每完成一项，执行 `python main.py`

完成标志：

- 不迁移目录时，旧工程仍能启动
- 框架层不因单个插件缺失而在 import 阶段崩溃

### Batch B: 在 Eridanus 建立承载骨架

目标：建立新架构的稳定落点，避免后续迁移继续堆回旧目录。

任务：

- B1. 创建 `core/` 目录骨架
- B2. 创建 `adapters/onebot/` 协议骨架
- B3. 预留 `plugins/` 与 `config/` 目录
- B4. 在 `docs/` 维护迁移工作台

完成标志：

- 新目录结构清晰可导入
- OneBot 协议只有一个主承载层，避免 NapCat / Lagrange 双份分叉
- 后续迁移的每个模块都有明确目标路径

### Batch C: 建立 core 外观层

目标：先做低风险 re-export / facade，而不是直接搬大文件。

任务：

- C1. `core/event/` 暴露旧事件模型
- C2. `core/message/` 暴露旧消息模型
- C3. `core/config/` 暴露配置管理入口
- C4. `core/database/` / `core/toolkit/` / `core/draw/` 建立导出面

完成标志：

- 新入口代码可以逐步改成 `from core...`
- 旧路径暂时继续可用

### Batch D: Bot 与 adapter 拆解

目标：把 `WebSocketBot`、`ExtendBot`、`PluginManager` 这条主链从继承堆叠改成组合结构。

任务：

- D1. 提取 `EventBus`
- D2. 定义 `PlatformAdapter` / `Session` / `EventSource` / `ApiClient`
- D3. 实现 `adapters/onebot/` 首版骨架，并把 NapCat / Lagrange 作为实现差异并入该层
- D4. 从 `ExtendBot` 中拆出过滤链
- D5. 让新 `Bot` 类接管主编排

完成标志：

- 新 Bot 可完成收消息、发消息、插件加载

### Batch E: 插件系统与工具系统重构

目标：移除 monkey-patch 与全局副作用。

任务：

- E1. 新 `PluginManager`
- E2. 新 `FuncMap`
- E3. 插件元信息与生命周期接口
- E4. 热重载迁移

完成标志：

- 插件和 LLM 工具映射都通过显式生命周期注册

### Batch F: 跨插件依赖治理

目标：为最终物理迁移扫清边界问题。

任务：

- F1. 建立 `ServiceRegistry`
- F2. 优先抽出 `ai_llm` 高频服务
- F3. 逐批替换 `from run.X import Y`

完成标志：

- 框架层与高频插件不再硬连具体插件模块

### Batch G: 物理迁移

目标：把旧目录内容真正迁入 `Eridanus/` 下的新结构。

任务：

- G1. `common_config` -> `config/`
- G2. `run/<plugin>` -> `plugins/<plugin>`
- G3. 旧路径兼容层
- G4. 清理下线计划

完成标志：

- 项目只依赖 `core/`、`adapters/`、`plugins/`、`config/`

### Batch H: 单根交付与依赖拆分

目标：让仓库最终只剩 `Eridanus/` 也能运行，并把依赖清单拆到功能边界上。

任务：

- H1. 将启动入口、WebUI、部署脚本、工具脚本迁入 `Eridanus/`
- H2. 移除 `core._legacy` 与其他对 `Eridanus/` 目录级资源的硬依赖
- H3. 将单体依赖清单拆为 `base/web/adapter/plugin` 多份清单
- H4. 保留一个聚合安装入口，支持全量安装
- H5. 验证删除 `Eridanus/` 后仍可启动

完成标志：

- 仓库仅保留 `Eridanus/` 也可正常安装、启动与加载插件
- 依赖清单不再集中在单一 `requirements.txt`，而是跟随功能边界分布

## 本轮已完成

- 创建 `Eridanus/` 目录说明
- 创建 `Eridanus/core/` 骨架
- 创建 `Eridanus/adapters/onebot/` 协议骨架
- 创建 `Eridanus/adapters/onebot/` 共享骨架
- 创建迁移工作台
- 创建 `core/event` facade：`base.py`、`events.py`、`factory.py`
- 创建 `core/message` facade：`message_chain.py`、`message_components.py`
- 创建 `core/config/manager.py` 并暴露 `YAMLManager`
- 创建 `core/database`、`core/toolkit`、`core/draw` 的首批 re-export 入口
- `Eridanus/main.py` 已开始切换到 `core.event` facade
- `YAMLManager` 默认入口已接入 `CORE_CONFIG_DIR`
- 已核对 `func_map_loader` 主要消费方的调用时序，确认不在 import 阶段消费扫描结果
- 已创建 `core/adapter` 抽象：`PlatformAdapter`、`Session`、`EventSource`、`ApiClient`
- 已从旧 `WebSocketBot` 中抽取 `core/bot/event_bus.py`，旧路径已接入兼容 re-export
- 已创建 `core/filter`：`FilterDecision`、`Filter`、`FilterChain`、`BlacklistFilter`
- `ExtendBot` 的黑白名单判断已切换为通过 `core.filter` 执行
- 已将 Lagrange outbound normalization 并入 `adapters/onebot/`，`adapters/lagrange/` 现仅保留兼容导出入口
- 已创建 `adapters/onebot/session_ws.py`、`adapters/onebot/api_client.py`、`adapters/onebot/event_source.py`、`adapters/onebot/event_factory.py` 与 `adapters/onebot/adapter.py`，共享 OneBot 传输 / API / 事件 / adapter 基础层已从 NapCat 命名中拆出
- NapCat / Lagrange 的差异实现已并入 `adapters/onebot/implementations.py` 与 `adapters/onebot/capabilities.py`
- `adapters/napcat/` 与 `adapters/lagrange/` 目录当前仅作为兼容导出壳保留，避免旧引用立刻断裂
- 已将 `adapters/napcat/*.py` 与 `adapters/lagrange/*.py` 的重复实现收敛为薄兼容包装，避免 OneBot 协议层继续出现双份维护
- 已创建 `core/bot/bot.py`，组合式 `Bot` 已具备 `start / stop / on / send` 主接口，并预留 plugin manager 注入位
- `Eridanus/main.py` 已加入 `adapter.use_new_core_bot` 开关，可在单 Bot 路径下切换到 `Bot + NapCatAdapter` 或 `Bot + LagrangeAdapter` 运行时，同时保留双 Bot / WebUI 的旧入口 fallback
- Lagrange 的专属 API 与发送兼容逻辑已并入 `adapters/onebot/`，旧 `adapters/lagrange/` 文件只保留兼容导出
- 旧 `WebSocketBot` 已改为默认组合共享 OneBot session/client，避免在公共运行路径中误绑 NapCat 实现
- 已创建 `core/bot/plugin_manager.py` 的首版无 monkey-patch 插件管理器，支持插件元信息、函数式 `main(bot, config)` 入口、类式 `PluginInterface` 入口，以及基础的加载 / 卸载 / 重载
- `core/bot/plugin_manager.py` 已补齐 `watchdog` 文件监听、基于事件循环的防抖热重载调度，以及插件目录变化触发的自动 `load / reload / unload`
- 已创建 `core/bot/func_map.py`，并让新 `PluginManager` 可在插件加载 / 卸载时同步注册和反注册工具声明
- 已将旧 `framework_common/framework_util/func_map_loader.py` 接成 facade，当前 `build_tool_map()` / `get_tool_declarations()` / `filter_tools_by_config()` 已可转发到新的 `core/bot/func_map.py`
- 已创建 `core/bot/skill_parser.py`，为后续插件级 `skill.md` 接入预留统一解析入口
- `core/bot/plugin_manager.py` 已在插件加载时解析插件目录下的 `skill.md`，并将结构化结果注册到 `FuncMap.skill_documents`
- 已完成一轮 `func_map_loader` 烟雾检查，当前工具注册结果为 `tools=43`、`decls=43`，`FuncMap` 的技能文档注册 / 查询接口也已做最小校验
- 已完成一轮新 `PluginManager` 热重载烟雾验证：临时插件修改 `main.py` 后，可自动触发卸载和重新加载，执行结果从 `v1` 切换到 `v2`
- 已创建 `core/services/registry.py`，提供进程级 `ServiceRegistry` / `ServiceEntry`、按名称注册查询、按 provider 清理，以及 `core.services` 懒导出入口
- `core/bot/plugin_manager.py` 已支持插件级 `register_services / unregister_services` 生命周期钩子，可在插件加载 / 卸载时自动注册和清理跨插件服务
- `run/ai_llm/__init__.py` 已接入首批核心服务注册：`aiReplyCore`、`schemaReplyCore`、`GeminiAPI`、`OpenAIAPI`、`gemini_prompt_elements_construct`、`prompt_elements_construct`，并补充 `ai_llm.*` 命名空间别名
- `framework_common/utils/ai_translate.py` 与 `framework_common/database_util/Group.py` 已开始消费 `ServiceRegistry`，优先从注册中心获取 `GeminiAPI`、`OpenAIAPI`、`gemini_prompt_elements_construct`、`prompt_elements_construct`
- `run/group_fun/__init__.py` 已注册 `manage_group_status`，`run/basic_plugin/__init__.py` 已注册 `bingEveryDay / danxianglii`
- `system_plugin/func_collection.py`、`scheduled_tasks/scheduledTasks.py`、`acg_infromation/majsoul.py`、`acg_infromation/service/majsoul/majsoul_plugin.py` 已开始消费 `ServiceRegistry`
- `groupManager/group_manager.py`、`system_plugin/api_implements.py`、`qq_zone/qzone.py`、`character_detection/nailong_get.py`、`group_msg_analyze/EatMyEgg.py`、`group_msg_analyze/service/prompt_constructer.py`、`ai_code_generator/service/AiPluginGenerator.py`、`ai_code_generator/service/AiChatbot.py`、`Grok2api/grok2api_Video_image.py` 已完成第二批替换，改为优先通过 `ServiceRegistry` 获取 `aiReplyCore`、`schemaReplyCore`、`GeminiAPI`、`gemini_prompt_elements_construct`
- `run/basic_plugin/__init__.py` 已继续扩展注册 `get_nasa_apod`、`tarotChoice`、`free_weather_query`、`anime_trace`、`bing_dalle3`、`flux_ultra`、`doubao`；`run/group_fun/__init__.py` 已补充注册 `Lexburner_Ninja`
- `system_plugin/func_collection.py`、`scheduled_tasks/scheduledTasks.py`、`acg_infromation/character_identify.py`、`ai_generated_art/aiDraw.py` 已完成第三批替换，改为优先通过 `ServiceRegistry` 获取上述 `basic_plugin / group_fun` 高频服务
- `run/anime_game_service/__init__.py`、`run/resource_collector/__init__.py`、`run/streaming_media/__init__.py`、`run/ai_generated_art/__init__.py` 已继续补充注册 `epic_free_game_get`、`random_asmr_100`、`bangumi_PILimg`、`download_video`、`call_text2img1`、`simple_call_text2img1`
- `scheduled_tasks/scheduledTasks.py`、`acg_infromation/bangumi.py`、`qq_zone/qzone.py`、`group_fun/func_collection.py` 已完成第四批替换，改为优先通过 `ServiceRegistry` 获取上述服务
- `ai_generated_art/service/simple_text2img.py` 已移除 `loguru` 依赖，改回项目 `developTools.utils.logger.get_logger` 风格，避免新增运行时依赖偏差
- `run/system_plugin/__init__.py` 已补充注册 `trigger_tasks` 与 `operate_group_push_tasks`
- `scheduled_tasks/scheduledTasks.py`、`streaming_media/bilibili.py` 已完成第五批替换，改为优先通过 `ServiceRegistry` 获取 `system_plugin` 暴露的系统级服务
- `run/streaming_media/__init__.py` 已继续补充注册 `majsoul_PILimg`、`fetch_latest_dynamic`、`fetch_latest_dynamic_id`，`run/resource_collector/__init__.py` 已补充注册 `parse_from_asmr_id`
- `system_plugin/func_collection.py`、`streaming_media/youtube.py`、`acg_infromation/majsoul.py` 已完成第六批替换，改为优先通过 `ServiceRegistry` 获取上述 `streaming_media / resource_collector` 服务
- `core.event.events` 已在当前环境直接导入验证通过，`GroupMessageEvent` facade 可用；原先 `pydantic` 缺失阻塞已不成立
- `framework_common/utils/install_and_import.py` 已补强为更稳健的自动安装入口：支持 `flask_sock -> flask-sock` 包名映射、失败结果缓存，避免同一进程内重复触发失败安装
- `web/server_new.py` 已改为通过 `install_and_import("flask-sock", "flask_sock")` 加载 WebUI WebSocket 依赖，避免因 pip 包名与 import 名不一致而安装失败
- 当前环境已完成 `flask-sock`、`imageio`、`python-dateutil` 安装；`python main.py` 不再因这三项依赖反复安装失败而中断
- `qzone_api` 与 `pyzbar` 已接入运行环境，`framework_common/utils/install_and_import.py` 现也支持 `qzone-api -> qzone_api` 包名映射；`run/qq_zone/qzone.py` 已补齐“依赖未就绪时的安全降级”，避免插件初始化退化为 `NameError`
- 已确认 `pyzbar` 的 Windows 原生依赖需要 `Microsoft Visual C++ 2013 Redistributable`；当前机器已完成 x86/x64 运行库安装后，`from qzone_api.login import QzoneLogin` 已可直接导入，`qq_zone` 插件恢复正常加载
- `Eridanus/一键部署脚本(整合包用户不要点).bat` 已前置集成 VC++ 2013 x86/x64 官方安装器下载与静默安装，避免新环境部署后在 `qq_zone` 路径上再次踩到 DLL 缺失
- `func_map_loader.scan_plugins()` 已收敛为仅扫描顶层插件包，避免在运行中的事件循环里递归导入插件内部服务子包；`run/system_plugin/tool_exports.py` 已作为轻量 wrapper 接入，解决 `build_tool_map()` 在异步上下文里被 `llmDB` / 用户数据模块的 `asyncio.run()` 导入副作用打断的问题
- 已补做异步 LLM tool-call 验证：当前 `build_tool_map()` 在事件循环内恢复到 `tools=43`，`get_tool_declarations(config)` 为 `decls=42`（按配置过滤掉 `search_with_official_api`），并已通过 `FuncMap.call("call_menu")` 与 `OpenAIAPI._execute_tool()` 跑通一条代表性的工具执行链路
- 已补齐 `websockets==16.0` 下 `ClientConnection.closed` 缺失的兼容处理，`Eridanus/adapters/onebot/session_ws.py` 现在可同时识别旧版 `.closed` 与新版 `.state` / `.close_code`
- 当前 `python main.py` 的 40 秒窗口验证已可完成 WebUI 启动、21 个插件分 6 批加载、Redis 自动拉起，并进入双 Bot 长驻运行；当前剩余阻塞为外部 OneBot 地址 `ws://127.0.0.1:3001` 在本机拒绝连接后的自动重试，不再是主程序内部启动崩溃
- `P2-4c` 当前按 WebUI 路径验收：不再要求本机必须同时具备可连接的 NapCat / Lagrange OneBot 服务端。现阶段以 WebUI 启动成功、主程序进入长驻运行，以及组合式 `Bot` / `FilterChain` / `LagrangeAdapter` 的本地行为验证为准
- 已将旧 `run/common_config/` 收口到仓库顶层 `config/`。当前 `YAMLManager` 仍保留兼容性的多根解析能力，但运行期实际配置已完全由顶层 `config/` 提供；删除旧目录后再次执行 `python main.py`，启动期不再出现与旧配置目录相关的缺失或回退问题
- `common_config` 已从插件发现 / 加载 / 工具扫描入口排除，启动批次从 22 个插件收敛为 21 个；随着 `Eridanus/run/common_config/` 实际删除，`main_func_detector` 与运行时配置加载均不再接触该旧目录
- 已完成 `P4-1b` 的完整依赖图梳理，并输出到 `docs/cross-plugin-dependency-map.md`：当前 `from run.` 共 `157` 处，全部为插件内部自引用；真正跨插件依赖已归零，`framework_common` 侧残留为 `0`
- 已完成 `P4-3` 的第十批收口：剩余 helper fallback 中的 `from run.` 已大批改为 `import_module(...).attr` 延迟获取，覆盖 `scheduled_tasks`、`system_plugin`、`acg_infromation`、`ai_generated_art`、`ai_llm`、`ai_code_generator`、`character_detection`、`comfyui_api`、`Grok2api`、`group_fun`、`group_msg_analyze`、`groupManager`、`qq_zone`、`resource_collector`、`streaming_media` 等热点模块。当前 AST 复核结果已显示 `Eridanus/run` 与 `Eridanus/framework_common` 范围内跨插件 `from run.` 全部清零；2026-03-18 再次执行 `python main.py`，21 个插件仍可完成加载，说明这轮静态解耦未引入启动回归
- 已补做 `P0-1e` 热重载验证：后台启动 `python main.py` 后，日志确认“文件监控已启动（递归监控所有插件文件）”；随后对 `run/comfyui_api/__init__.py` 做两次注释级改动，均触发 `检测到插件 comfyui_api 的文件 __init__.py 变化 -> 开始重载插件 -> 卸载 4 个事件处理器 -> 重新找到 4 个 main 函数 -> 重新注册 4 个事件处理器 -> 插件 comfyui_api 重载成功`，说明旧运行时的插件热重载链路已可复现且稳定
- 已补做 `P0-2c` 的当前等价验证：直接实例化 `YAMLManager(PLUGINS_DIR, CORE_CONFIG_DIR)` 时，`config.common_config.basic_config` 与 `config.common_config.menu` 的底层文件路径均已解析到仓库顶层 `config/`，旧访问路径未变化，插件配置如 `config.ai_llm.config` 仍可访问；结合删除 `run/common_config/` 后的再次启动烟雾验证，可以确认 YAML 兼容层已完成当前阶段的目标
- `P5-2` 已整体收口：`Eridanus/run/` 下 21 个插件目录已迁移到 `Eridanus/plugins/`；`PLUGINS_DIR` 已切到 `../Eridanus/plugins`，`PLUGINS_MODULE_PREFIX` 已切到 `plugins`，插件内部自引用也已批量从 `run.*` 收口到 `plugins.*`
- `Eridanus/run/__init__.py` 已升级为真实兼容别名层，统一把 `run.<plugin>` 映射到 `plugins.<plugin>`，避免旧路径与新路径各自导入出双实例
- `Eridanus/tool.py` 中最后一个非插件脚本的 `run.streaming_media...` 残留已切到 `plugins.streaming_media...`，当前运行路径上不再依赖旧 `run.*` 导入
- 已开始推进 `P5-3`：补上 `developTools` / `framework_common` 包级 deprecation shim，统一发出 `DeprecationWarning`；其中 `framework_common` 侧目前先保持轻量告警层，避免在包初始化阶段直接反向 import `core.*` 引入循环依赖
- `P5-3a` 已进入第二阶段：`core.event` 与 `core.message` 现已承接真实实现，`developTools.event/*` 与 `developTools.message/*` 已降级为薄 re-export；这意味着事件模型与消息模型的“源头”已正式从旧目录翻到 `core/`
- 上述切换后，`Eridanus/plugins/`、`Eridanus/adapters/onebot/`、`Eridanus/framework_common/` 以及 `Eridanus/developTools/{main,adapters,interface}` 中原先依赖 `developTools.event/message` 的消费方导入也已改到 `core.event/message`；当前仓库内已无这几类旧事件/消息导入残留
- `P5-3a` 的旧适配层本体安置问题已收口：`developTools.adapters.websocket_adapter`、`developTools.adapters.http_adapter`、`developTools.interface.http_sendMes` 现已分别迁到 `Eridanus/adapters/onebot/{websocket_bot,http_adapter,http_mailman}.py`，旧路径只保留兼容壳
- `P5-3a` 已于 2026-03-18 收口：`developTools.utils.logger` 与 `developTools.utils.cq_code_handler` 已分别翻到 `core.toolkit.logger` / `core.message.cq_parser`，旧路径仅保留 deprecation shim；结合旧新路径对象一致性验证与同日 `python main.py` 启动烟雾结果，可以确认 `developTools/` 运行期模块已不再承载核心实现
- `P5-3b` 已进入第一批细粒度源头翻转：`core.toolkit` 现已正式承接 `BaseTool`、`install_and_import`、`delete_old_files_async`、`MemoryMonitor`、`random_str`、`random_session_hash` 的真实实现，对应 `framework_common` 旧路径已降级为兼容壳；这意味着 `framework_common` 已不再是 `toolkit` 这条链路上的唯一实现源
- `P5-3b` 已继续向 `framework_util` 的配置链路推进：`framework_common.framework_util.constants` 与 `yamlLoader` 现已分别翻到 `core.config.constants` / `core.config.manager`，旧路径仅保留 deprecation shim；`Eridanus/main.py` 与 `core.bot.plugin_manager` 已切到 `core.config`，且 2026-03-18 再次执行 `python main.py` 后 WebUI 与 21 个插件仍可正常进入长驻运行
- `P5-3b` 也已开始切走 `framework_util` 中仍由旧目录承载的 Bot 辅助能力：`func_map_loader`、`main_func_detector`、`bot_info` 已翻到 `core.bot`，旧路径仅保留兼容壳；`Eridanus/main.py`、`PluginAwareExtendBot`、`plugins/comfyui_api`、`plugins/ai_llm`、`plugins/system_plugin` 的关键消费方已切到新路径，并完成旧新路径对象一致性验证
- `P5-3b` 已继续进入数据库外壳收缩阶段：`framework_common.database_util.{Group,GroupSummary,RedisCacheManager,User,llmDB,ManShuoDrawCompatibleDataBase}` 已翻到 `core.database.{group,group_summary,redis_cache,user,llm_db,manshuo_compatible_db}`，旧路径仅保留 deprecation shim；`web.server_new`、`plugins.ai_llm`、`plugins.system_plugin`、`plugins.scheduled_tasks`、`plugins.auto_reply`、`plugins.groupManager` 以及 `group_fun`、`anime_game_service`、`basic_plugin` 等消费方都已切到 `core.database`
- 上述数据库迁移过程中顺手修复了 `core.database` 的包初始化设计问题：包入口现已改为 lazy export，不再在 import 阶段立即反向拉起 `framework_common.database_util.*`，从而避免 `User -> core.database -> User` 的循环导入；同时已补齐 `set_all_users_chara`、`merge_dicts`、`optimized_batch_update_speeches` 的 facade 导出，确保新旧导出面不再出现缺口
- 2026-03-18 再次执行 `python main.py` 后，WebUI、21 个插件加载、Redis 自动拉起与双 Bot 长驻运行均保持正常，说明 `Group/User/llmDB/AsyncSQLiteDatabase` 这批导入翻转未引入启动回归；当前 `framework_common.database_util` 已全部退化为 shim，不再承载真实实现
- `P5-3b` 也已开始收缩 `framework_util` 的 Bot 运行时外壳：`framework_common.framework_util.{websocket_fix,DualBotManager}` 已翻到 `core.bot.{extend_bot,dual_bot_manager}`，旧路径仅保留 deprecation shim；`Eridanus/main.py` 与插件侧高频 `ExtendBot` 消费方已切到新路径，目前该条链路上仅剩旧 `PluginAwareExtendBot.py` 自身仍通过 shim 兼容引用 `ExtendBot`
- 2026-03-18 再次执行 `python main.py` 后，WebUI、21 个插件加载、Redis 自动拉起与双 Bot 长驻运行均保持正常，说明 `ExtendBot/DualBotManager` 这批导入翻转也未引入启动回归
- `P5-3b` 现已继续收缩旧插件管理链路：`framework_common.framework_util.PluginAwareExtendBot` 的完整旧实现已翻到 `core.bot.legacy_plugin_manager`，主入口 `Eridanus/main.py` 已切到该新模块；旧 `PluginAwareExtendBot.py` 现仅保留 shim，以避免与现有新式 `core.bot.plugin_manager` 命名冲突
- 2026-03-18 再次执行 `python main.py` 后，WebUI、21 个插件加载、Redis 自动拉起与双 Bot 长驻运行均保持正常，说明旧插件管理实现的迁移也未引入启动回归
- `P5-3b` 也已开始收缩高频工具模块：`framework_common.utils.{GeminiKeyManager,PDFEncrypt,cloudscraper,system_logger,utils}` 已分别翻到 `core.toolkit.{gemini_keys,pdf_encrypt,async_web_client,logger,compat_utils}`；`main.py`、`ai_llm`、`group_msg_analyze`、`resource_collector`、`streaming_media.service.bilibili` 等主运行路径消费方已先切到新路径，旧文件均已退化为 shim
- 工具迁移过程中顺手修复了 `core.toolkit` 包入口的导入期副作用：由于 `GeminiKeyManager` 会在模块导入时访问 `YAMLManager`，`core.toolkit.__init__` 已从 eager import 改为 lazy export，避免在非完整运行时上下文中单纯 `import core.toolkit` 就触发配置缺失异常
- 2026-03-18 再次执行 `python main.py` 后，WebUI、21 个插件加载、Redis 自动拉起与双 Bot 长驻运行均保持正常，说明这批工具模块迁移未引入启动回归
- `P5-3b` 已继续收缩 `framework_common.manshuo_draw`：整套绘图运行时代码、核心资源与数据目录已复制承接到 `Eridanus/core/draw/`，旧 `framework_common.manshuo_draw` 仅保留 shim；插件侧 `ai_llm`、`scheduled_tasks`、`anime_game_service`、`streaming_media`、`group_fun`、`resource_collector` 等主要绘图消费方已切到 `core.draw`
- 这轮 `core.draw` 迁移顺手消掉了两类启动回归：一是 `resource_collector` 与 `GeminiKeyManager` 的导入期配置访问被改为惰性获取，避免插件入口扫描时因 `YAMLManager` 尚未就绪而直接 import 失败；二是 `core.draw.core.classic_collection.util.common` 里针对工作目录的路径假设已修正，不再要求 `Eridanus/core/draw` 必须位于当前工作目录子路径下
- 2026-03-18 在 `Eridanus/` 工作目录下重新完成定向入口扫描验证：`basic_plugin=4`、`anime_game_service=5`、`scheduled_tasks=1`、`streaming_media=4`、`resource_collector=4`、`ai_llm=2`、`group_fun=11`、`system_plugin=3`、`acg_infromation=6`
- 同日重新执行 `python main.py` 45 秒烟雾验证后，WebUI 正常启动、21 个插件分 6 批完成加载、Redis 成功连通并进入双 Bot 长驻运行；此前因为误把子包 `main()` 当插件入口而出现的 `main() takes 0 positional arguments but 2 were given` 日志已不再出现，当前剩余告警仍仅为外部 OneBot 地址 `ws://127.0.0.1:3001` 在本机拒绝连接后的自动重试
- `P5-3b` 又继续做了一轮插件侧高频导入翻转：`Eridanus/plugins/` 中大量 `framework_common.framework_util.yamlLoader`、`framework_common.utils.{utils,random_str,random_session_hash,install_and_import}` 与 `framework_common.ToolKits.logger` 已批量切到 `core.config.manager`、`core.toolkit.{compat_utils,random_utils,installer,logger}`，覆盖 `ai_generated_art`、`basic_plugin`、`streaming_media`、`resource_collector`、`system_plugin`、`qq_zone`、`group_fun`、`comfyui_api`、`auto_reply`、`ai_code_generator`、`ai_voice`、`anime_game_service`、`group_msg_analyze`、`Grok2api` 等主运行路径
- 同日对上述热点插件目录重新执行 `python -m compileall`，全部通过；随后再次在 `Eridanus/` 工作目录下执行定向入口扫描，结果仍为 `basic_plugin=4`、`anime_game_service=5`、`scheduled_tasks=1`、`streaming_media=4`、`resource_collector=4`、`ai_llm=2`、`group_fun=11`、`system_plugin=3`、`acg_infromation=6`
- 再次执行 `python main.py` 45 秒烟雾验证后，WebUI 仍正常启动、21 个插件分 6 批完成加载、Redis 自动连通成功、主程序进入双 Bot 长驻运行，说明这轮大批量 import 翻转未引入新的启动回归
- `P5-3b` 已继续收掉剩余边缘工具模块：`framework_common.utils.{ai_translate,zip,zip_2_pwd_version,PlayWrightAutoInstaller}` 已分别翻到 `core.toolkit.{translator,archive,archive_pwd,playwright_installer}`，对应旧文件均已退化为 shim；`ai_voice.service.tts`、`resource_collector.func_collection`、`streaming_media.service.bilibili.BiliCooikeManager` 已切到新路径，`resource_collector.hitomi` 中无用的 `framework_common.ToolKits.Util` 依赖也已移除
- 同日对 `core/toolkit`、`ai_voice`、`resource_collector`、`streaming_media` 与旧 `framework_common/utils` shim 重新执行 `python -m compileall`，全部通过；并额外验证了 `Translator`、`compress_files`、`compress_files_with_pwd`、`check_and_install_playwright` 的新路径导入可用
- 2026-03-18 再次执行 `python main.py` 45 秒烟雾验证后，WebUI 仍正常启动、21 个插件分 6 批完成加载、Redis 自动连通成功、主程序进入双 Bot 长驻运行；此时 `Eridanus/plugins/` 运行路径下已无直接 `framework_common.*` 依赖残留
- `P5-3b` 又继续收掉了 `ToolKits` 本体与两处边缘遗留：`framework_common.ToolKits.{util,file,image,network,text,system,logger}` 已分别翻到 `core.toolkit.{util,file,image,network,text,system,logger}`，`framework_common.framework_util.func_map` 与 `framework_common.utils.tomato_image_enc` 也已分别翻到 `core.bot.legacy_func_map` 与 `core.toolkit.tomato_image_enc`；对应旧文件现均为 deprecation shim，且 `core.toolkit.{compat_utils,archive,archive_pwd,__init__}` 已不再反向依赖旧 `ToolKits`
- 同日对 `Eridanus/core/toolkit`、`Eridanus/core/bot`、`Eridanus/framework_common/ToolKits`、`Eridanus/framework_common/framework_util`、`Eridanus/framework_common/utils` 再次执行 `python -m compileall`，全部通过；并额外验证了 `Util`、`SystemProcessor`、`tomato_encrypt` / `tomato_decrypt`、以及 `framework_common.ToolKits` shim 导入可用
- 2026-03-18 再次执行 `python main.py` 45 秒烟雾验证后，WebUI 仍正常启动、21 个插件分 6 批完成加载、Redis 自动连通成功、主程序进入双 Bot 长驻运行；截至当前，`framework_common` 包级模块层面的真实实现已基本清空，剩余旧代码主要收敛在 `framework_common/manshuo_draw/core/**` 的历史镜像子树
- `P5-3b` 最后又继续把 `framework_common/manshuo_draw/core/**` 历史镜像压成目录级兼容层：旧 `core`、`classic_collection`、`classic_collection.util`、`db_core`、`menu_maker` 现仅保留桥接型 `__init__.py` 与 `_bridge.py`，子树中的重复叶子模块已全部删除，旧路径会通过包 `__path__` 解析到 `core.draw.core/**`
- 同日对 `Eridanus/framework_common/manshuo_draw` 与 `Eridanus/core/draw` 重新执行 `python -m compileall`，并额外验证了 `framework_common.manshuo_draw.core`、`framework_common.manshuo_draw.core.classic_collection.avatar`、`framework_common.manshuo_draw.core.classic_collection.util.download_img` 等旧路径导入可用
- 2026-03-18 再次执行 `python main.py` 45 秒烟雾验证后，WebUI 仍正常启动、21 个插件分 6 批完成加载、Redis 自动连通成功、主程序进入双 Bot 长驻运行；截至当前，`framework_common` 下除 `manshuo_draw/_bridge.py` 这类桥接辅助代码外，包级运行时模块均已完成 shim 化，`P5-3b` 已可视为完成
- `P5-3c` 已落盘旧路径下线时间表：`R0` 保留兼容层但冻结旧命名空间新增引用，`R1` 把旧路径告警升级为显式迁移约束，`R2` 在 `P6-1/P6-2` 完成后删除 `Eridanus/` 兼容层与旧脚本；这意味着后续新工作将不再接受继续落到 `run.*`、`developTools.*`、`framework_common.*`
- `P5-4a` 也已复核完成：当前运行态代码的 `get_logger()` 已统一收归 `core.toolkit.logger`，仓库中剩余 `developTools.utils.logger`、`framework_common.utils.system_logger`、`framework_common.ToolKits.logger` 仅为 shim，不再承载真实实现
- `P5-4b` 已完成当前范围的核心配置 Schema 校验补齐：`core.config.schema` 除 `basic_config`、`menu` 外，已继续覆盖 `censor_group` / `censor_user` 两类黑白名单配置；`YAMLManager` 在初始加载与文件热重载时都会执行这些校验，`core.config` 入口也已直接导出 `ConfigValidationError` 与相关校验函数
- `P6-1a` 已完成首版独立入口落地：新增 `Eridanus/main.py` 与 `Eridanus/__main__.py`，把工作目录切换、配置初始化、插件加载、单 Bot / 双 Bot / 组合式 Bot 启动编排统一收进 `Eridanus/`；2026-03-18 直接执行 `python Eridanus/main.py` 的 20 秒烟雾窗口中，已完成初始化并装入前五批插件
- `P6-1b` 已完成第一轮主链去旧目录：`adapters/onebot/*`、`core/bot/{event_bus,plugin_manager,func_map}.py`、`core/{filter,database,toolkit,services}` 等运行态模块中的 `ensure_legacy_root()` 调用已全部移除；当前代码搜索结果显示，`Eridanus/` 运行态已不再主动把 `Eridanus/` 加入 `sys.path`
- 2026-03-18 随后再次执行 `python Eridanus/main.py` 的 12 秒烟雾验证，独立入口仍可完成初始化并装入前三批插件，说明这轮主链去旧目录未引入新的启动回归
- `P6-1b` 已继续进入第二轮：现有 `Eridanus/web/` 已整体迁入 `Eridanus/web/`，并把 `server_new.py` 的安装器入口切到 `core.toolkit.installer`，配置扫描主链切到 `Eridanus/plugins/ + Eridanus/config/`
- 2026-03-18 随后再次执行 `python Eridanus/main.py` 的 12 秒烟雾验证，`web.server_new` 已可在新入口中真正启动 Flask WebUI 线程，独立入口同时仍可完成初始化并装入前三批插件
- `P6-1b` 已继续进入第三轮：`Eridanus/web/server_new.py` 现已去掉固定 `Eridanus` 目录名和当前工作目录假设，克隆目标目录改为动态推导，配置导入导出统一改走 `config_backups/` 绝对路径；同时 `core.draw` 默认 `config_path` 与初始化逻辑已改为按 `core/draw` 根目录自解析，`group_fun/service/lu` 与 `streaming_media/service/Link_parsing` 的运行期字体 / 资源路径也已收口到 `Eridanus/core/draw` 与插件自身目录
- 2026-03-18 随后再次执行 `python Eridanus/main.py` 的 15 秒烟雾验证，WebUI 在线程中正常启动，独立入口已稳定完成前四批插件加载；同时针对 `Eridanus/web`、`Eridanus/core/draw`、`group_fun/service/lu` 与 `streaming_media/service/Link_parsing` 的旧路径扫描已清零
- `P6-1b` 已继续进入第四轮：`core.config.constants` 已改为按 `Eridanus` 应用根动态推导 `plugins/` 与 `config/`；`resource_collector/service/{jmComic,obsidianLink,zLibrary}` 已不再读写 `run/resource_collector/jmcomic.yml`，而是直接定位插件根下的 `jmcomic.yml`；`zLibrary/canvas.py`、`comfyui_api/example_neta_lumina_i2i.py`、`group_fun/func_collection.py` 与 `scheduled_tasks/scheduledTasks.py` 的运行期图片 / 占位路径也已收口；同时 `basic_plugin` 与 `ai_generated_art` 中的示例块旧绝对路径已清理
- 2026-03-18 随后再次执行 `python Eridanus/main.py` 的 12 秒烟雾验证，WebUI 在线程中正常启动，独立入口已稳定完成前三批插件加载；针对 `run/resource_collector/jmcomic.yml`、`run/group_fun/service/img.png`、`run/resource_collector/service/zLibrary/img.png`、`run/comfyui_api/example_src/upload_img.png` 与 `data/pictures/img.png` 的目标扫描已清零
- `P6-1c` 已完成：工作区内已创建仅包含 `Eridanus/` 与顶层 `config/` 的临时隔离副本，并在该隔离根目录下直接执行 `python Eridanus/main.py` 做 15 秒烟雾验证；结果显示 WebUI 可正常在线程中启动，独立入口可稳定完成前四批插件加载，说明当前启动主链已可在不依赖外层 `Eridanus/` 目录存在的前提下运行
- `P6-1b` 已做最终残留收口：原先仅剩的孤立兼容文件 `Eridanus/core/_legacy.py` 已在确认全仓库无代码引用后删除，并再次执行 `python Eridanus/main.py` 的 12 秒烟雾验证通过
- `P6-1b` 已继续清理 Phase 6 完成后残留的本地旧路径硬编码：`meme_generate`、`acg_infromation/service/bangumisearch.py`、`memes/service/aoyi.py`、`groupManager/self_Manager.py`、`streaming_media/service/Link_parsing/core/login_core.py`、`anime_game_service/service/{skland,mihuyo_club}`、`basic_plugin/service/{random_pic,scheduled_tasks}.py`、`comfyui_api/example_*` 与 `ai_code_generator/service/AiPluginGenerator.py` 已改为插件相对路径或 `Eridanus/core` 资源路径；同时 `Eridanus/README.md`、`Eridanus/plugins/README.md`、`CLAUDE.md` 已同步去掉旧目录说明。当前非文档代码中的 `run/` 命中已只剩第三方接口 URL（如 `.../gradio/run/predict`）与兼容命名空间说明；2026-03-19 再次执行 `python Eridanus/main.py` 的 15 秒烟雾验证时，WebUI 与前四批插件加载均保持正常
- `P6-2a` 已启动并完成骨架落地：新增 `Eridanus/requirements/{README,base,web,adapter-onebot,all}.txt`，同时为 `ai_llm`、`streaming_media`、`resource_collector`、`qq_zone`、`comfyui_api`、`ai_voice` 建立了插件级 `requirements.txt` 入口，占位后续逐项归档
- `P6-2b` 已完成归档收口：新增 `Eridanus/requirements/legacy-compat.txt`，并把 `ai_llm`、`streaming_media`、`resource_collector`、`qq_zone`、`comfyui_api`、`ai_voice`、`basic_plugin`、`anime_game_service`、`auto_reply`、`group_fun`、`acg_infromation`、`Grok2api`、`ai_generated_art` 的插件级 `requirements.txt` 从占位改为实际依赖列表；`base.txt` 也已补入 `numpy`
- 2026-03-18 已对旧 `Eridanus/requirements.txt` 与新拆分后的全部 `requirements*.txt` 做集合比对，结果 `MISSING` / `EXTRA` 均为空，说明旧单体依赖清单里的包已经全部归档到新结构中；`legacy-compat.txt` 现作为已定义边界的兼容保留层保留给后续验证收缩，不再阻塞 `P6-2b`
- `P6-2c` 已完成首版收口：`Eridanus/core/toolkit/installer.py` 已改为基于 `requirements/` 与插件级 `requirements.txt` 建立索引，`install_and_import()` 会优先按唯一归属的 profile / plugin 依赖文件安装，只有在多个插件共享同一包时才回退为直接 `pip install`
- 同日已新增 `Eridanus/install.py` 作为 CLI 安装入口，并补充 `Eridanus/install.bat` 作为 Windows 包装脚本；`Eridanus/requirements/all.txt` 现已聚合公共依赖与已归档插件依赖，`Eridanus/web/utils.py` 与 `core.toolkit.system.SystemProcessor` 也已统一复用共享安装器
- 2026-03-18 已完成 `python -m py_compile Eridanus/core/toolkit/installer.py`、`python -m py_compile Eridanus/install.py`、`python -m py_compile Eridanus/core/toolkit/system.py`、`python -m py_compile Eridanus/web/utils.py` 与 `python Eridanus/install.py --help` 验证通过；CLI 当前可正确列出 5 类 profile 与 13 个插件入口
- `P6-2d` 已拿到首批实证：`python Eridanus/install.py --profile all`、`python Eridanus/install.py --profile base --profile web` 与 `python Eridanus/install.py --plugin ai_llm` 已在当前环境实际执行成功，说明聚合安装、最小公共安装与单插件补装三条入口均可落地
- 同日再次执行 `python Eridanus/main.py` 的 20 秒烟雾验证后，WebUI 正常启动，21 个插件按 6 个批次完成加载，说明全量安装入口与当前主程序启动链路兼容
- 随后又完成了隔离最小依赖环境验证：在临时目录中仅保留 `Eridanus/ + config/ + basic_plugin`，并新建独立虚拟环境按 `base + web + basic_plugin` 安装时，首先暴露 `Eridanus/main.py` 在导入期硬依赖 `adapters/onebot`；补装 `adapter-onebot` 后再次启动，已确认 WebUI 正常启动、仅 `basic_plugin` 单插件成功加载并进入单批次运行
- 因此 `P6-2d` 已完成，当前代码基线下的“最小可运行集合”可明确记为 `base + web + adapter-onebot + basic_plugin`；如果后续希望把 `adapter-onebot` 从最小集合中剥离，需要再做入口层延迟导入收口
- `P6-3a` 已完成：删前校验已确认 `Eridanus/` 运行链路中已无 `ensure_legacy_root()` 调用残留、无运行期 `framework_common` / `developTools` 依赖残留；随后已实际删除仓库根 `Eridanus/` 旧目录，并立刻执行 `python Eridanus/main.py` 的 20 秒烟雾验证，确认 WebUI 正常启动、21 个插件继续按批次完成加载
- `P6-3b` 也已完成：4 个核心配置文件已物理并入 `Eridanus/config/`，`CORE_CONFIG_DIR` 已调整为优先读取应用根内配置；先在仅包含 `Eridanus/` 的临时副本中验证无需仓库根 `config/` 也可启动，再在真实工作区中删除仓库根 `config/` 后复验通过。当前仓库根已不再包含 `Eridanus/` 与旧 `config/`，运行所需的启动入口、WebUI、配置、插件与依赖清单均已收敛到 `Eridanus/`
- 2026-03-19 又补做了一轮交付形态整理：已新增 `archive/non_runtime_artifacts/` 作为统一归档根，将历史验证日志收口到 `archive/non_runtime_artifacts/validation_logs/`，将历史运行日志收口到 `archive/non_runtime_artifacts/runtime_logs/{workspace-log,app-log}/`，并清理了一轮全仓 `__pycache__`。随后再次执行 `python Eridanus/main.py` 的 15 秒烟雾验证，确认 WebUI 与前四批插件仍可正常启动；当前运行态若需要写日志，会自动重建 `Eridanus/log/`
- 同步地，`P5-4c` 的“仅依赖 core/plugins/config 可正常启动”也已自然收口：当前真实仓库形态与临时单根副本都已通过 20 秒启动烟雾验证
- `P6` 已纳入计划：最终交付不再以“仓库根下同时保留 `Eridanus/` 与 `Eridanus/`”为目标，而是要求 `Eridanus/` 成为唯一应用根，并将依赖清单按 `core/web/plugin` 边界拆分

## 下一轮建议

建议直接推进剩余未完成项：

1. 继续做 Phase 6 收尾清理，把仓库根文档、用户提示和辅助说明里残留的旧路径描述全部改到 `Eridanus/`
2. 视需要开始 Phase 7 之外的非功能性整理，例如进一步清理示例脚本中的历史 `run/...` 路径文本
