plugin_description="群聊娱乐功能"


dynamic_imports ={
    "plugins.group_fun.func_collection": ["random_ninjutsu","query_ninjutsu"],
}
function_declarations=[
    {
        "name": "query_ninjutsu",
        "description": "查询忍术",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "忍术名称"
                },
            },
            "required": [
                "name"
            ]
        }
    },
    {
        "name": "random_ninjutsu",
        "description": "随机获取忍术",
    }
]


def register_services(registry, provider: str = "group_fun", **_kwargs):
    from plugins.group_fun.lex_burner_Ninja import Lexburner_Ninja
    from plugins.group_fun.wife_you_want import manage_group_status, today_check_api

    service_map = {
        "manage_group_status": manage_group_status,
        "group_fun.manage_group_status": manage_group_status,
        "today_check_api": today_check_api,
        "group_fun.today_check_api": today_check_api,
        "Lexburner_Ninja": Lexburner_Ninja,
        "group_fun.Lexburner_Ninja": Lexburner_Ninja,
    }

    for service_name, service in service_map.items():
        registry.register(
            service_name,
            service,
            provider=provider,
            metadata={"plugin": "group_fun"},
        )

    return list(service_map.keys())


def unregister_services(registry, provider: str = "group_fun", **_kwargs):
    registry.unregister_by_provider(provider)

