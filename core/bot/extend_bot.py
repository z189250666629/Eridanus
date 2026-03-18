# 实现黑白名单判断，后续 aiReplyCore 的阻断也将在这里实现
import asyncio
from typing import Union

from adapters.onebot.websocket_bot import WebSocketBot
from core.event.base import EventBase
from core.message.message_components import MessageComponent
from adapters.onebot import LagrangeApiClient, NapCatApiClient, normalize_outbound_components
from core.filter import BlacklistFilter, FilterChain


class ExtendBot(WebSocketBot):
    def __init__(self, uri: str, config, **kwargs):
        super().__init__(uri, **kwargs)
        self.config = config
        self.id = 1000000
        adapter_name = self.config.common_config.basic_config["adapter"]["name"]
        if adapter_name == "Lagrange":
            self._set_api_client(
                LagrangeApiClient(
                    self.session,
                    logger=self.logger,
                    readiness_checker=lambda: self.session.websocket is not None or self.receive_task is not None,
                )
            )
        else:
            self._set_api_client(
                NapCatApiClient(
                    self.session,
                    logger=self.logger,
                    readiness_checker=lambda: self.session.websocket is not None or self.receive_task is not None,
                ),
                extra_methods=["get_ai_characters", "get_ai_record"],
            )
            self.event_source.unmatched_event_message = "无法匹配事件类型，请向开发群913122269反馈。"
        self.filter_chain = FilterChain()
        self.filter_chain.add(BlacklistFilter(config))
    async def _handle_incoming_event(self, event_obj):
        decision = await self.filter_chain.check(event_obj)
        if decision.allowed:
            asyncio.create_task(self.event_bus.emit(event_obj))
        elif decision.reason:
            self.logger.info(decision.reason)

    async def send(self, event: EventBase, components: list[Union[MessageComponent, str]], Quote: bool = False):
        """
        构建并发送消息链。

        Args:
            components (list[Union[MessageComponent, str]]): 消息组件或字符串。
        """
        components, Quote = normalize_outbound_components(
            components,
            adapter_name=self.config.common_config.basic_config["adapter"]["name"],
            quote=Quote,
            message_id=getattr(event, "message_id", None),
            bot_id=self.id,
            bot_name=self.config.common_config.basic_config["bot"],
        )
        return await super().send(event, components, Quote)

    async def delay_recall(self,msg, interval=20):
        """
        延迟撤回消息的非阻塞封装函数，撤回机器人自身消息可以先msg = await bot.send(event, 'xxx')然后调用await delay_recall(bot, msg, 20)这样来不阻塞的撤回，默认20秒后撤回

        参数:
            bot
            msg: 消息
            interval: 延迟时间（秒）
        """

        async def recall_task():
            await asyncio.sleep(interval)
            await super().recall(msg['data']['message_id'])

        asyncio.create_task(recall_task())


__all__ = ["ExtendBot"]


