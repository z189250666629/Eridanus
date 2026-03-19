
from core.event.events import GroupMessageEvent
from core.bot.extend_bot import ExtendBot
from core.config.manager import YAMLManager
from plugins.group_fun.func_collection import random_ninjutsu, query_ninjutsu
from plugins.group_fun.lex_burner_Ninja import Lexburner_Ninja


def main(bot: ExtendBot,config: YAMLManager):
    @bot.on(GroupMessageEvent)
    async def handle_group_message(event: GroupMessageEvent):
        if event.pure_text=="随机忍术":
            await random_ninjutsu(bot,event,config)
        if event.pure_text.startswith("查询忍术"):
            name=event.pure_text.replace("查询忍术","")
            await query_ninjutsu(bot,event,config,name)


