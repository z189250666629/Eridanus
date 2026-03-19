plugin_description = "基础功能集合"


dynamic_imports = {
    "plugins.basic_plugin.basic_plugin": [
        "call_weather_query", "call_setu","call_tarot", "call_pick_music",
        "call_fortune", "call_quit_chat","call_menu"
    ],
    "plugins.basic_plugin.image_search":
        ["call_image_search"],
}
function_declarations=[
    {
        "name": "call_weather_query",
        "description": "Get the current weather in a given location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and state, e.g. 上海"
                }
            },
            "required": [
                "location"
            ]
        }
    },
    {
        "name": "call_setu",
        "description": "根据关键词搜索相关图片并返回图片。",
        "parameters": {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "description": "所要求的关键词。eg.白丝 萝莉",
                    "items": {
                        "type": "string"
                    }
                },
                "num": {
                    "type": "integer",
                    "description": "返回的图片数量。默认为1"
                }
            },
            "required": [
                "tags"
            ]
        }
    },
    {
        "name": "call_image_search",
        "description": "按照用户要求搜索给定图片的来源，当且仅当用户要求搜索时才可触发。",
        "parameters": {
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "图片的url"
                }
            },
            "required": [
                "image_url"
            ]
        }
    },
    {
        "name": "call_pick_music",
        "description": "触发音乐选取功能。根据歌曲名或歌手名搜索点歌。",
        "parameters": {
            "type": "object",
            "properties": {
                "aim": {
                    "type": "string",
                    "description": "歌曲名、歌手名或者二者混合。eg.周杰伦 eg.屋顶 eg.周杰伦 屋顶"
                }
            },
            "required": [
                "aim"
            ]
        }
    },
    {
        "name": "call_tarot",
        "description": "抽取一张塔罗牌。"
    },
    {
        "name": "call_fortune",
        "description": "运势占卜，返回图片。"
    },

    {
        "name": "call_quit_chat",
        "description": "停止对话，不再接收信息"
    },
    {
        "name": "call_menu",
        "description": "发送功能列表/菜单/帮助指令表"
    },

]


def register_services(registry, provider: str = "basic_plugin", **_kwargs):
    from plugins.basic_plugin.ai_text2img import bing_dalle3, doubao, flux_ultra
    from plugins.basic_plugin.divination import tarotChoice
    from plugins.basic_plugin.imgae_search.anime_trace import anime_trace
    from plugins.basic_plugin.life_service import bingEveryDay, danxianglii
    from plugins.basic_plugin.nasa_api import get_nasa_apod
    from plugins.basic_plugin.weather_query import free_weather_query

    service_map = {
        "bingEveryDay": bingEveryDay,
        "basic_plugin.bingEveryDay": bingEveryDay,
        "danxianglii": danxianglii,
        "basic_plugin.danxianglii": danxianglii,
        "get_nasa_apod": get_nasa_apod,
        "basic_plugin.get_nasa_apod": get_nasa_apod,
        "tarotChoice": tarotChoice,
        "basic_plugin.tarotChoice": tarotChoice,
        "free_weather_query": free_weather_query,
        "basic_plugin.free_weather_query": free_weather_query,
        "anime_trace": anime_trace,
        "basic_plugin.anime_trace": anime_trace,
        "bing_dalle3": bing_dalle3,
        "basic_plugin.bing_dalle3": bing_dalle3,
        "flux_ultra": flux_ultra,
        "basic_plugin.flux_ultra": flux_ultra,
        "doubao": doubao,
        "basic_plugin.doubao": doubao,
    }

    for service_name, service in service_map.items():
        registry.register(
            service_name,
            service,
            provider=provider,
            metadata={"plugin": "basic_plugin"},
        )

    return list(service_map.keys())


def unregister_services(registry, provider: str = "basic_plugin", **_kwargs):
    registry.unregister_by_provider(provider)

