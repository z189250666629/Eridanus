from core.event.events import GroupMessageEvent
from core.message.message_components import Forward
from importlib import import_module
from core.services import get_service_registry
from core.bot.extend_bot import ExtendBot
from core.config.manager import YAMLManager
from core.toolkit.gemini_keys import GeminiKeyManager
from plugins.group_msg_analyze.service.prompt_constructer import gemini_prompt_construct_vGroup


def _get_gemini_api():
    registry = get_service_registry()
    service = registry.get("GeminiAPI") or registry.get("ai_llm.GeminiAPI")
    if service is not None:
        return service
    return import_module("plugins.ai_llm.clients.gemini_client").GeminiAPI


def main(bot: ExtendBot,config: YAMLManager):
    @bot.on(GroupMessageEvent)
    async def handle_group_message(event: GroupMessageEvent):
        return
        if event.user_id==1840094972:
            print("message from admin")
            print(event.message_chain)
            if event.message_chain.has(Forward):
                bot.logger.info("forward message received")
                forward_msg = event.message_chain.get(Forward)[0]
                msg_id=forward_msg.id
                i=0
                while i<3:
                    full_msg = await bot.get_forward_msg(msg_id)
                    if full_msg["status"]=="ok":
                        try:
                            role_set=config.group_msg_analyze.config["role_set"]

                            proxy = config.common_config.basic_config["proxy"]["http_proxy"] if config.ai_llm.config["llm"]["enable_proxy"] else None
                            proxies = {"http://": proxy, "https://": proxy} if proxy else None

                            GeminiAPI = _get_gemini_api()
                            api = GeminiAPI(
                                apikey=await GeminiKeyManager.get_gemini_apikey(),
                                baseurl=config.ai_llm.config["llm"]["gemini"]["base_url"],
                                model=config.ai_llm.config["llm"]["gemini"]["model"],
                                proxies=proxies
                            )

                            response_text = ""
                            async for part in api.chat(
                                await gemini_prompt_construct_vGroup(full_msg),
                                stream=False,
                                system_instruction=role_set,
                                temperature=config.ai_llm.config["llm"]["gemini"]["temperature"],
                                max_output_tokens=config.ai_llm.config["llm"]["gemini"]["maxOutputTokens"],
                            ):
                                if isinstance(part, str):
                                    response_text += part

                            bot.logger.info(response_text)
                            await bot.send(event, response_text.strip() if response_text else "")
                            break
                        except Exception as e:
                            bot.logger.error(e)
                            i+=1

            #await bot.send(event,"Hello World!")


