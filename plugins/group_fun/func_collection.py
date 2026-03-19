from core.message.message_components import Image, Text
from importlib import import_module
from core.services import get_service_registry
from core.bot.extend_bot import ExtendBot
from core.config.manager import YAMLManager


def _build_no_image_message(parse_message: str):
    return [Text("啊没图使\n"), Text(parse_message)]


def _get_lexburner_ninja():
    registry = get_service_registry()
    service = registry.get("Lexburner_Ninja") or registry.get("group_fun.Lexburner_Ninja")
    if service is not None:
        return service
    return import_module("plugins.group_fun.lex_burner_Ninja").Lexburner_Ninja


def _get_download_video():
    registry = get_service_registry()
    service = registry.get("download_video") or registry.get("streaming_media.download_video")
    if service is not None:
        return service
    return import_module("plugins.streaming_media.youtube").download_video


ninja = _get_lexburner_ninja()()



async def random_ninjutsu(bot: ExtendBot,event,config: YAMLManager):
    bot.logger.info("随机获取忍术")
    ninjutsu=await ninja.random_ninjutsu()
    tags=""
    for tag in ninjutsu['tags']:
        tags+=f"{tag['name']},"
    parse_message=f"忍术名称: {ninjutsu['name']}\n忍术介绍: {ninjutsu['description']}\n忍术标签: {tags}\n忍术教学: {ninjutsu['videoLink']}\n更多忍术请访问: https://wsfrs.com/"
    if not ninjutsu.get('imageUrl'):
        messages = _build_no_image_message(parse_message)
    else:
        messages=[Image(file=ninjutsu['imageUrl']),Text(parse_message)]
    try:
        await bot.send(event,messages)
    except Exception as e:
        await bot.send(event, _build_no_image_message(parse_message))
    if ninjutsu['videoLink']:
        download_video = _get_download_video()
        await download_video(bot,event,config,ninjutsu['videoLink'],platform="bilibili")
async def query_ninjutsu(bot: ExtendBot,event,config: YAMLManager,name):
    bot.logger.info(f"查询忍术: {name}")
    try:
        ninjutsu=await ninja.query_ninjutsu(name)
        parse_message=f"忍术名称: {ninjutsu['title']}\n忍术介绍: {ninjutsu['description']}\n忍术标签: {ninjutsu['tags']}\n忍术教学: {ninjutsu['videoLink']}"
        await bot.send(event, _build_no_image_message(parse_message))
        if ninjutsu['videoLink']:
            download_video = _get_download_video()
            await download_video(bot, event, config, ninjutsu['videoLink'], platform="bilibili")
    except Exception as e:
        bot.logger.error(f"忍术查询失败: {e}")
        await bot.send(event, _build_no_image_message("找不到这个忍术，请检查拼写或重新输入"))



