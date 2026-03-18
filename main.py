"""Standalone startup entrypoint hosted inside ``Eridanus/``."""

from __future__ import annotations

import asyncio
import importlib
import os
import sys
import threading
import traceback
from pathlib import Path
from typing import Any


APP_ROOT = Path(__file__).resolve().parent


def _configure_process_environment() -> None:
    os.chdir(APP_ROOT)
    app_root_str = str(APP_ROOT)
    if app_root_str not in sys.path:
        sys.path.insert(0, app_root_str)
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


_configure_process_environment()

from adapters.onebot import LagrangeAdapter, NapCatAdapter
from adapters.onebot.websocket_bot import WebSocketBot
from core.bot import Bot
from core.bot.bot_info import bot_info_collect
from core.bot.dual_bot_manager import DualBotManager
from core.bot.extend_bot import ExtendBot
from core.bot.func_map_loader import scan_plugins
from core.bot.legacy_plugin_manager import LoadStrategy, PluginLoadConfig, PluginManager
from core.config import CORE_CONFIG_DIR, PLUGINS_DIR, PLUGINS_MODULE_PREFIX, YAMLManager
from core.event.events import GroupMessageEvent, LifecycleMetaEvent, PrivateMessageEvent
from core.toolkit.logger import get_logger


class StandaloneRuntime:
    """Boot the migrated runtime from the ``Eridanus/`` root."""

    def __init__(self) -> None:
        self.plugin_manager: PluginManager | None = None
        self.bot2: WebSocketBot | None = None
        self.dual_manager: DualBotManager | None = None
        self.runtime_bot: Bot | None = None
        self.runtime_adapter: Any | None = None
        self.webui_thread: threading.Thread | None = None

        self.config = YAMLManager(PLUGINS_DIR, CORE_CONFIG_DIR)
        enable_monitoring = self.config.common_config.basic_config["HandlerMonitor"]["enable"]
        handler_timeout_warning = float(
            self.config.common_config.basic_config["HandlerMonitor"]["handler_timeout_warning"]
        )
        ws_link = self.config.common_config.basic_config["adapter"]["ws_client"]["ws_link"]
        self.bot1 = ExtendBot(
            ws_link,
            self.config,
            blocked_loggers=["DEBUG", "INFO_MSG"],
            handler_timeout_warning=handler_timeout_warning,
            enable_monitoring=enable_monitoring,
        )
        self.bot1.logger.info("正在初始化 Eridanus....")

        if self.config.common_config.basic_config["webui"]["enable"]:
            self._setup_webui()

    def _setup_webui(self) -> None:
        web_dir = APP_ROOT / "web"
        server_path = web_dir / "server_new.py"
        if not server_path.exists():
            self.bot1.logger.warning(
                f"Eridanus WebUI 尚未迁入，已跳过 WebUI 启动: {server_path}"
            )
            return

        web_dir_str = str(web_dir)
        if web_dir_str not in sys.path:
            sys.path.insert(0, web_dir_str)

        self.bot2 = WebSocketBot("ws://127.0.0.1:5007/api/ws")
        self.bot1.logger.server("🔧 WebUI 服务启动中，请在完全启动后，本机浏览器访问 http://localhost:5007")
        self.bot1.logger.server("🔧 若您部署的远程主机有公网ip或端口转发功能，请访问对应ip的5007端口，或设置的转发端口。")
        self.bot1.logger.server("🔧 WebUI 初始账号密码均为 eridanus")
        self.bot1.logger.server("🔧 WebUI 初始账号密码均为 eridanus")
        self.bot1.logger.server("🔧 WebUI 初始账号密码均为 eridanus")

        def run_webui() -> None:
            try:
                self.bot1.logger.info(f"WebUI 线程：启动 WebUI，模块路径 {web_dir}")
                from web.server_new import start_webui

                start_webui()
            except Exception as exc:
                self.bot1.logger.error(f"WebUI 线程：启动 WebUI 失败：{exc}")
                traceback.print_exc()

        self.webui_thread = threading.Thread(target=run_webui, daemon=True)
        self.webui_thread.start()
        self.bot1.logger.info("主线程：WebUI 已启动在子线程中")

    def _should_use_new_core_runtime(self) -> bool:
        adapter_config = self.config.common_config.basic_config.get("adapter", {})
        if not adapter_config.get("use_new_core_bot", False):
            return False
        if self.bot2 is not None:
            self.bot1.logger.warning("当前 `use_new_core_bot` 暂不覆盖双 Bot / WebUI 路径，已回退到旧运行时。")
            return False
        return True

    def _bridge_legacy_bot_to_runtime(self, legacy_bot: ExtendBot, core_runtime_bot: Bot, adapter: Any) -> None:
        legacy_bot._core_runtime_bot = core_runtime_bot
        legacy_bot.session = adapter.session
        legacy_bot.api_client = adapter.api_client
        legacy_bot.event_source = adapter.event_source
        legacy_bot.response_callbacks = adapter.api_client.response_callbacks
        legacy_bot.send = core_runtime_bot.send
        legacy_bot._call_api = adapter.api_client.call_api

        for method_name in WebSocketBot.API_CLIENT_METHODS:
            if hasattr(adapter, method_name):
                setattr(legacy_bot, method_name, getattr(adapter, method_name))

        for method_name in ("get_ai_characters", "get_ai_record"):
            if hasattr(adapter, method_name):
                setattr(legacy_bot, method_name, getattr(adapter, method_name))

        original_lifecycle = adapter.event_source.on_lifecycle

        async def bridged_lifecycle(event_obj: Any) -> None:
            if original_lifecycle is not None:
                await original_lifecycle(event_obj)
            legacy_bot.id = adapter.id

        adapter.event_source.on_lifecycle = bridged_lifecycle

    def _build_new_runtime(self) -> Bot:
        adapter_name = self.config.common_config.basic_config["adapter"].get("name")
        ws_link = self.config.common_config.basic_config["adapter"]["ws_client"]["ws_link"]
        if adapter_name == "Lagrange":
            self.runtime_adapter = LagrangeAdapter(
                ws_link,
                logger=self.bot1.logger,
                bot_name=self.config.common_config.basic_config["bot"],
            )
        else:
            self.runtime_adapter = NapCatAdapter(
                ws_link,
                logger=self.bot1.logger,
            )

        self.runtime_bot = Bot(
            self.runtime_adapter,
            self.config,
            event_bus=self.bot1.event_bus,
            filter_chain=self.bot1.filter_chain,
        )
        self._bridge_legacy_bot_to_runtime(self.bot1, self.runtime_bot, self.runtime_adapter)
        return self.runtime_bot

    async def _run_new_runtime(self) -> None:
        if self.runtime_bot is None:
            raise RuntimeError("runtime_bot 尚未初始化")

        await self.runtime_bot.start()
        event_task = getattr(self.runtime_bot.adapter, "_event_task", None)
        if event_task is not None:
            await event_task

    async def load_plugins(self) -> PluginManager | None:
        self.bot1.logger.info("🔧 正在使用插件管理器加载插件....")

        try:
            load_strategy_dict = {
                "batch_loading": LoadStrategy.BATCH_LOADING,
                "all_at_once": LoadStrategy.ALL_AT_ONCE,
                "memory_aware": LoadStrategy.MEMORY_AWARE,
            }

            plugin_load_settings = self.config.common_config.basic_config["PluginLoadConfig"]
            load_config = PluginLoadConfig(
                batch_size=plugin_load_settings["batch_size"],
                batch_delay=plugin_load_settings["batch_delay"],
                max_retries=plugin_load_settings["max_retries"],
                retry_delay=plugin_load_settings["retry_delay"],
                memory_threshold_mb=plugin_load_settings["memory_threshold_mb"],
                enable_gc_between_batches=plugin_load_settings["enable_gc_between_batches"] | True,
                load_strategy=load_strategy_dict.get(
                    plugin_load_settings["load_strategy"],
                    LoadStrategy.BATCH_LOADING,
                ),
            )
            self.plugin_manager = PluginManager(
                self.bot1,
                self.config,
                plugins_dir=PLUGINS_DIR,
                plugins_module_prefix=PLUGINS_MODULE_PREFIX,
                load_config=load_config,
            )

            await self.plugin_manager.retry_failed_plugins()
            await self.plugin_manager.start()
            scan_plugins(PLUGINS_DIR, PLUGINS_MODULE_PREFIX)

            loaded_plugins = self.plugin_manager.get_loaded_plugins()
            self.bot1.logger.info(
                f"🔧 插件加载完成，共加载 {len(loaded_plugins)} 个插件：{', '.join(loaded_plugins)}"
            )
            return self.plugin_manager
        except Exception as exc:
            self.bot1.logger.error(f"🔧 插件管理器启动失败：{exc}")
            traceback.print_exc()
            return None

    async def handler(self, bot: ExtendBot, event: GroupMessageEvent | PrivateMessageEvent) -> None:
        if event.pure_text == "/reload all":
            await self.reload_all_plugins()
            await bot.send(event, "插件重载完成")
        elif event.pure_text in ["/status", "/info"]:
            status = await self.get_plugin_status()
            module = importlib.import_module(f"{PLUGINS_MODULE_PREFIX}.basic_plugin.service.self_condition")
            await module.self_info_core(bot, event, status)
        elif event.pure_text == "/test" and self.plugin_manager is not None:
            report = self.plugin_manager.log_memory_report()
            await bot.send(event, report)

    async def reload_all_plugins(self) -> None:
        if self.plugin_manager is None:
            return
        self.bot1.logger.info("重载主Bot插件...")
        await self.plugin_manager.reload_all_plugins()
        scan_plugins(PLUGINS_DIR, PLUGINS_MODULE_PREFIX)

    async def get_plugin_status(self) -> dict[str, Any]:
        status: dict[str, Any] = {}
        if self.plugin_manager is not None:
            status["main_bot"] = await self.plugin_manager.get_plugin_status()
        return status

    def setup_event_handlers(self) -> None:
        @self.bot1.on(GroupMessageEvent)
        async def handle_group_message(event: GroupMessageEvent) -> None:
            await self.handler(self.bot1, event)

        @self.bot1.on(PrivateMessageEvent)
        async def handle_private_message(event: PrivateMessageEvent) -> None:
            await self.handler(self.bot1, event)

        @self.bot1.on(LifecycleMetaEvent)
        async def handle_lifecycle(event: LifecycleMetaEvent) -> None:
            await asyncio.sleep(2)
            await self.bot1.send_friend_message(
                self.config.common_config.basic_config["master"]["id"],
                "欢迎使用\n\n群内发送 帮助 可查看命令列表\n\n访问webui请在bot所在设备用浏览器访问\nhttp://localhost:5007",
            )

    async def async_main(self) -> None:
        try:
            await self.load_plugins()
            self.bot1.logger.info("🚀 主Bot插件管理器启动完成")

            self.setup_event_handlers()

            if self.bot2 is not None:
                self.bot2.fix_id = self.config.common_config.basic_config["master"]["id"]
                self.dual_manager = DualBotManager(self.bot1, self.bot2, target_group_id=879886836)
                self.bot1.logger.info("🔧 双Bot管理器已创建，开始启动双Bot系统...")
                await self.dual_manager.start_both_bots()
            elif self._should_use_new_core_runtime():
                self._build_new_runtime()
                self.bot1.logger.info("🚀 开始运行 Eridanus Bot + OneBotAdapter 模式...")
                await self._run_new_runtime()
            else:
                self.bot1.logger.info("🚀 开始运行单Bot模式...")
                await self.bot1._connect_and_run()
        except Exception as exc:
            self.bot1.logger.error(f"运行错误：{exc}")
            traceback.print_exc()

    async def cleanup(self) -> None:
        if self.plugin_manager is not None:
            try:
                await self.plugin_manager.stop()
                self.bot1.logger.info("主Bot插件管理器已停止")
            except Exception as exc:
                self.bot1.logger.error(f"停止主Bot插件管理器失败：{exc}")

        if self.runtime_bot is not None:
            try:
                await self.runtime_bot.stop()
                self.bot1.logger.info("Eridanus 运行时已停止")
            except Exception as exc:
                self.bot1.logger.error(f"停止 Eridanus 运行时失败：{exc}")

    def run(self) -> None:
        try:
            asyncio.run(bot_info_collect(self.config.common_config.basic_config["bot"]))
            asyncio.run(self.async_main())
        except KeyboardInterrupt:
            self.bot1.logger.info("收到停止信号，正在关闭...")
        except Exception as exc:
            self.bot1.logger.error(f"主程序运行错误：{exc}")
            traceback.print_exc()
        finally:
            try:
                asyncio.run(self.cleanup())
            except Exception as exc:
                self.bot1.logger.error(f"清理过程出错：{exc}")


def main() -> None:
    get_logger("Eridanus")
    StandaloneRuntime().run()


if __name__ == "__main__":
    main()
