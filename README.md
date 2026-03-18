# Eridanus

`Eridanus/` 是 Eridanus 的重构承载目录。

当前阶段的主目标已经从“只建骨架”推进到了“让 `Eridanus/` 成为可独立运行的应用根，并逐步收口依赖与兼容层”。

迁移原则：

- 先解耦，后搬迁。
- 先建立 `core/` 与 `adapters/` 的外观层，再逐步承接旧实现。
- 每完成一个子任务，都需要回到旧工程入口做运行验证。

当前目录说明：

- `core/`: 新架构下的平台无关核心层。
- `adapters/`: 平台适配层，当前以 `onebot/` 作为统一协议实现层；`napcat/` 与 `lagrange/` 仅保留兼容导出入口。
- `plugins/`: 当前运行时插件目录。
- `config/`: 当前应用根内核心配置目录。
- `docs/`: 迁移工作台与阶段说明。

当前状态：

- `python Eridanus/main.py` 已可作为独立入口启动。
- WebUI、插件加载与配置扫描主链已迁入 `Eridanus/`。
- 依赖清单已开始从单体 `requirements.txt` 拆分为 `requirements/base.txt`、`requirements/web.txt`、`requirements/adapter-onebot.txt` 与插件级 `requirements.txt`。

依赖安装：

- 全量安装：`python Eridanus/install.py --profile all`
- 仅安装核心：`python Eridanus/install.py --profile base`
- 核心 + WebUI：`python Eridanus/install.py --profile base --profile web`
- 当前最小可运行集合：`python Eridanus/install.py --profile base --profile web --profile adapter-onebot --plugin basic_plugin`
- 补装单个插件：`python Eridanus/install.py --plugin ai_llm`
- Windows 包装脚本：`Eridanus/install.bat --profile all`

自动补依赖：

- `core.toolkit.installer.install_and_import()` 现在会优先根据新的依赖布局定位对应 `requirements.txt`
- 当某个包只属于一个 profile / plugin 时，会直接安装对应的依赖文件
- 当某个包被多个插件共享时，才回退为直接安装该 pip 包
- `Eridanus/web/utils.py` 与 `core.toolkit.system.SystemProcessor` 也已统一走这套逻辑
