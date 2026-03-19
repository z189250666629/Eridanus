plugin_description = "AI LLM Plugin"

# 动态导入列表
dynamic_imports = {
    "plugins.ai_llm.official_search_tool": ["search_with_official_api"],
}

# 函数声明
function_declarations = [
    {
        "name": "search_with_official_api",
        "description": "使用官方API进行联网搜索或读取URL内容。当用户需要查询实时信息、新闻、天气、或需要访问特定网页内容时使用此功能。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询内容，或对URL内容提出的问题"
                },
                "urls": {
                    "type": "string",
                    "description": "可选，需要读取的URL地址。如果有多个URL，用逗号分隔"
                }
            },
            "required": ["query"]
        }
    }
]


def register_services(registry, provider: str = "ai_llm", **_kwargs):
    from plugins.ai_llm.clients.gemini_client import GeminiAPI
    from plugins.ai_llm.clients.openai_client import OpenAIAPI
    from plugins.ai_llm.aiReplyCore import aiReplyCore
    from plugins.ai_llm.aiReplyHandler.gemini import gemini_prompt_elements_construct
    from plugins.ai_llm.aiReplyHandler.openai import prompt_elements_construct
    from plugins.ai_llm.schemaReplyCore import schemaReplyCore

    service_map = {
        "aiReplyCore": aiReplyCore,
        "ai_llm.aiReplyCore": aiReplyCore,
        "schemaReplyCore": schemaReplyCore,
        "ai_llm.schemaReplyCore": schemaReplyCore,
        "GeminiAPI": GeminiAPI,
        "ai_llm.GeminiAPI": GeminiAPI,
        "OpenAIAPI": OpenAIAPI,
        "ai_llm.OpenAIAPI": OpenAIAPI,
        "gemini_prompt_elements_construct": gemini_prompt_elements_construct,
        "ai_llm.gemini_prompt_elements_construct": gemini_prompt_elements_construct,
        "prompt_elements_construct": prompt_elements_construct,
        "ai_llm.prompt_elements_construct": prompt_elements_construct,
    }

    for service_name, service in service_map.items():
        registry.register(
            service_name,
            service,
            provider=provider,
            metadata={"plugin": "ai_llm"},
        )

    return list(service_map.keys())


def unregister_services(registry, provider: str = "ai_llm", **_kwargs):
    registry.unregister_by_provider(provider)

