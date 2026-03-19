from core.event.events import GroupMessageEvent, LifecycleMetaEvent
from core.message.message_components import Text, Image, At
from core.draw import *
from plugins.anime_game_service.ZZZ import *


def main(bot, config):


    #绑定ZZZ
    @bot.on(GroupMessageEvent)
    async def bind_sklandid(event: GroupMessageEvent):
        context, userid=event.pure_text.lower(), str(event.sender.user_id)
        order_list = ['zzzbind', 'zzz绑定']
        if event.message_chain.has(At) and event.message_chain.has(Text):
            userid, context = event.message_chain.get(At)[0].qq, event.message_chain.get(Text)[0].text
        if context in order_list:
            await qrcode_get(userid, bot, event)

