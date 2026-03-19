plugin_description="媒体服务"

dynamic_imports ={
    "plugins.streaming_media.youtube": ["download_video"],
    "plugins.streaming_media.cloud_music_parsing": ["parse_cloud_music"]
}
function_declarations=[
    {
        "name": "download_video",
        "description": "下载youtube/bilibili的视频或音频。",
        "parameters": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string", "enum": ["video", "audio"], "description": "下载类型。asmr100平台只能下载audio"
                },
                "url": {
                    "type": "string",
                    "description": "视频/音频的链接地址"
                },
                "platform": {
                    "type": "string", "enum": ["youtube", "bilibili", "asmr100"],
                    "description": "视频的来源平台。域名为b23.tv的为bilibili"
                }
            },
            "required": [
                "url",
                "platform"
            ]
        }
    },
    {
        "name": "parse_cloud_music",
        "description": "解析并下载网易云音乐单曲",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "音频的链接地址"
                },
            },
            "required": [
                "url"
            ]
        }
    },
]


def register_services(registry, provider: str = "streaming_media", **_kwargs):
    from plugins.streaming_media.Link_parsing import bangumi_PILimg
    from plugins.streaming_media.Link_parsing import majsoul_PILimg
    from plugins.streaming_media.bilibili.bili import (
        fetch_latest_dynamic,
        fetch_latest_dynamic_id,
    )
    from plugins.streaming_media.youtube import download_video

    service_map = {
        "bangumi_PILimg": bangumi_PILimg,
        "streaming_media.bangumi_PILimg": bangumi_PILimg,
        "majsoul_PILimg": majsoul_PILimg,
        "streaming_media.majsoul_PILimg": majsoul_PILimg,
        "fetch_latest_dynamic": fetch_latest_dynamic,
        "streaming_media.fetch_latest_dynamic": fetch_latest_dynamic,
        "fetch_latest_dynamic_id": fetch_latest_dynamic_id,
        "streaming_media.fetch_latest_dynamic_id": fetch_latest_dynamic_id,
        "download_video": download_video,
        "streaming_media.download_video": download_video,
    }

    for service_name, service in service_map.items():
        registry.register(
            service_name,
            service,
            provider=provider,
            metadata={"plugin": "streaming_media"},
        )

    return list(service_map.keys())


def unregister_services(registry, provider: str = "streaming_media", **_kwargs):
    registry.unregister_by_provider(provider)

