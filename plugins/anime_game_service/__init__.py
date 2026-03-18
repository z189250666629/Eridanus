plugin_description = "Anime Game Service"


def register_services(registry, provider: str = "anime_game_service", **_kwargs):
    from plugins.anime_game_service.service.epicfree import epic_free_game_get

    service_map = {
        "epic_free_game_get": epic_free_game_get,
        "anime_game_service.epic_free_game_get": epic_free_game_get,
    }

    for service_name, service in service_map.items():
        registry.register(
            service_name,
            service,
            provider=provider,
            metadata={"plugin": "anime_game_service"},
        )

    return list(service_map.keys())


def unregister_services(registry, provider: str = "anime_game_service", **_kwargs):
    registry.unregister_by_provider(provider)

