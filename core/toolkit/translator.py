"""Translation helper hosted under core.toolkit."""

from __future__ import annotations

import importlib
import random
import traceback

from core.config.constants import PLUGINS_MODULE_PREFIX
from core.config.manager import YAMLManager
from core.services import get_service_registry
from core.toolkit.gemini_keys import GeminiKeyManager
from core.toolkit.logger import get_logger


def _get_default_model_request():
    module = importlib.import_module(
        f"{PLUGINS_MODULE_PREFIX}.ai_llm.aiReplyHandler.default"
    )
    return module.defaultModelRequest


def _get_yuan_qi_tencent():
    module = importlib.import_module(
        f"{PLUGINS_MODULE_PREFIX}.ai_llm.aiReplyHandler.tecentYuanQi"
    )
    return module.YuanQiTencent


def _get_gemini_api():
    registry = get_service_registry()
    service = registry.get("GeminiAPI") or registry.get("ai_llm.GeminiAPI")
    if service is not None:
        return service
    module = importlib.import_module(f"{PLUGINS_MODULE_PREFIX}.ai_llm.clients.gemini_client")
    return module.GeminiAPI


def _get_openai_api():
    registry = get_service_registry()
    service = registry.get("OpenAIAPI") or registry.get("ai_llm.OpenAIAPI")
    if service is not None:
        return service
    module = importlib.import_module(f"{PLUGINS_MODULE_PREFIX}.ai_llm.clients.openai_client")
    return module.OpenAIAPI


class Translator:
    def __init__(self):
        self.config = YAMLManager.get_instance()
        self.system_instruction = "请翻译以下内容为日文，直接给出结果，不要有回应之类的内容。需要翻译的文本为："
        self.logger = get_logger()

    async def translate(self, text):
        return await self.aiReplyCore(text, self.config, self.system_instruction)

    async def aiReplyCore(self, text, config, system_instruction=None, recursion_times=0):
        logger = self.logger
        logger.info(f"translator called with message: {text}")

        if recursion_times > config.ai_llm.config["llm"]["recursion_limit"]:
            logger.warning(f"roll back to original history, recursion times: {recursion_times}")
            return text

        try:
            if config.ai_llm.config["llm"]["model"] == "default":
                prompt = [{"role": "user", "content": system_instruction + text}]
                defaultModelRequest = _get_default_model_request()
                response_message = await defaultModelRequest(
                    prompt,
                    config.common_config.basic_config["proxy"]["http_proxy"]
                    if config.ai_llm.config["llm"]["enable_proxy"]
                    else None,
                )
                reply_message = response_message["content"]
            elif config.ai_llm.config["llm"]["model"] == "openai":
                prompt = [{"role": "user", "content": system_instruction + text}]
                proxy = (
                    config.common_config.basic_config["proxy"]["http_proxy"]
                    if config.ai_llm.config["llm"]["enable_proxy"]
                    else None
                )
                proxies = {"http://": proxy, "https://": proxy} if proxy else None

                OpenAIAPI = _get_openai_api()
                api = OpenAIAPI(
                    apikey=random.choice(config.ai_llm.config["llm"]["openai"]["api_keys"]),
                    baseurl=(
                        config.ai_llm.config["llm"]["openai"].get("quest_url")
                        or config.ai_llm.config["llm"]["openai"].get("base_url")
                    ),
                    model=config.ai_llm.config["llm"]["openai"]["model"],
                    proxies=proxies,
                )

                response_text = ""
                async for part in api.chat(
                    prompt,
                    stream=False,
                    max_output_tokens=config.ai_llm.config["llm"]["openai"]["max_tokens"],
                    temperature=config.ai_llm.config["llm"]["openai"]["temperature"],
                ):
                    if isinstance(part, str):
                        response_text += part
                reply_message = response_text.strip() if response_text else None
            elif config.ai_llm.config["llm"]["model"] == "gemini":
                prompt = [{"parts": [{"text": system_instruction + text}], "role": "user"}]
                proxy = (
                    config.common_config.basic_config["proxy"]["http_proxy"]
                    if config.ai_llm.config["llm"]["enable_proxy"]
                    else None
                )
                proxies = {"http://": proxy, "https://": proxy} if proxy else None

                GeminiAPI = _get_gemini_api()
                api = GeminiAPI(
                    apikey=await GeminiKeyManager.get_gemini_apikey(),
                    baseurl=config.ai_llm.config["llm"]["gemini"]["base_url"],
                    model=config.ai_llm.config["llm"]["gemini"]["model"],
                    proxies=proxies,
                )

                response_text = ""
                async for part in api.chat(
                    prompt,
                    stream=False,
                    system_instruction="请你扮演翻译官，我给你要翻译的文本，你直接给我结果，不需要回应。",
                    temperature=config.ai_llm.config["llm"]["gemini"]["temperature"],
                    max_output_tokens=config.ai_llm.config["llm"]["gemini"]["maxOutputTokens"],
                ):
                    if isinstance(part, str):
                        response_text += part
                reply_message = response_text.strip() if response_text else None
            elif config.ai_llm.config["llm"]["model"] == "腾讯元器":
                prompt = [{"role": "user", "content": [{"type": "text", "text": system_instruction + text}]}]
                YuanQiTencent = _get_yuan_qi_tencent()
                response_message = await YuanQiTencent(
                    prompt,
                    config.ai_llm.config["llm"]["腾讯元器"]["智能体ID"],
                    config.ai_llm.config["llm"]["腾讯元器"]["token"],
                    random.randint(1, 100),
                )
                reply_message = response_message["content"]
                response_message["content"] = [{"type": "text", "text": response_message["content"]}]
            else:
                reply_message = text

            logger.info(f"aiReplyCore returned: {reply_message}")
            return reply_message.strip() if reply_message is not None else reply_message
        except Exception as e:
            logger.error(f"Error occurred: {e}")
            traceback.print_exc()
            logger.warning(f"roll back to original history, recursion times: {recursion_times}")
            if recursion_times <= config.ai_llm.config["llm"]["recursion_limit"]:
                logger.warning(f"Recursion times: {recursion_times}")
                return await self.aiReplyCore(text, config, system_instruction, recursion_times + 1)
            return text


__all__ = ["Translator"]
