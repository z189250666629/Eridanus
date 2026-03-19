import asyncio
import datetime
import os
import random
import re
from core.toolkit.compat_utils import delay_recall
from core.event.events import GroupMessageEvent, LifecycleMetaEvent
from core.message.message_components import Node, Text, Image, At
from asyncio import sleep
from .api import check_lu, lock_lu, no_lu, rank_lu, supple_lu, today_lu
from core.draw import *

def main(bot, config):
    @bot.on(GroupMessageEvent)
    async def today_LU(event: GroupMessageEvent):
        context, userid=event.pure_text, str(event.sender.user_id)
        type_check = 'self'
        if event.message_chain.has(At) and event.message_chain.has(Text):
            userid, context = event.message_chain.get(At)[0].qq, event.message_chain.get(Text)[0].text
            type_check = 'help'
        if not context.startswith('🦌'):return
        times_add = 0
        for context_check in context:
            if context_check == '🦌':times_add += 1
        if context.replace('🦌','').replace(' ','') != '':return

        lu_recall = ['不！给！你！🦌！！！', '我靠你怎么这么坏！', '再🦌都🦌出火星子了！！', '让我来帮你吧~', '好恶心啊~~',
                     '有变态！！', '你这种人渣我才不会喜欢你呢！', '令人害怕的坏叔叔', '才不给你计数呢！（哼', '杂鱼杂鱼',
                     '杂鱼哥哥还是处男呢', '哥哥怎么还在这呀，好可怜']
        flag = random.randint(0, 100)
        if flag <= 8:
            await bot.send(event, lu_recall[random.randint(0, len(lu_recall) - 1)])
            return
        bot.logger.info("接收到开🦌请求")
        recall_id = await today_lu(userid,times_add,bot=bot,event=event,type_check=type_check)
        if config.group_fun.config["today_wife"]["签🦌撤回"] is True and recall_id is not None:
            await sleep(55)
            await bot.recall(recall_id['data']['message_id'])

    @bot.on(GroupMessageEvent)
    async def today_LU2(event: GroupMessageEvent):
        context, userid=event.pure_text, str(event.sender.user_id)
        if event.message_chain.has(At) and event.message_chain.has(Text):
            userid, context = event.message_chain.get(At)[0].qq, event.message_chain.get(Text)[0].text
        order_list = ['鹿','这倒提醒我了','🦌！','鹿！']
        if context in order_list:
            bot.logger.info("接收到🦌请求")
            recall_id = await today_lu(userid, 1, bot=bot, event=event)
            if config.group_fun.config["today_wife"]["签🦌撤回"] is True:
                await sleep(55)
                await bot.recall(recall_id['data']['message_id'])

    @bot.on(GroupMessageEvent)
    async def no_LU(event: GroupMessageEvent):
        context, userid=event.pure_text, str(event.sender.user_id)
        order_list = ['戒🦌']
        if context not in order_list: return
        bot.logger.info("接收到戒🦌请求")
        await no_lu(userid, bot=bot, event=event)

    @bot.on(GroupMessageEvent)
    async def lock_LU_self(event: GroupMessageEvent):
        context, userid=event.pure_text, str(event.sender.user_id)
        order_list = ['贞操锁']
        open_list, close_list = ['开启','打开','启用'], ['关闭','关掉','解开']
        total_list = open_list + close_list
        if not (any(word in context for word in order_list) and any(word in context for word in total_list)):return
        target = next((t for t in total_list if t in context), None)
        context = re.compile('|'.join(map(re.escape, order_list + total_list))).sub('', context).strip()
        status = 1 if target in open_list else 0 if target in close_list else None
        if status is None or context != '': return
        bot.logger.info("贞操锁请求设定中")
        await lock_lu(userid,status,bot=bot,event=event)

    @bot.on(GroupMessageEvent)
    async def check_LU(event: GroupMessageEvent):
        context, userid=event.pure_text, str(event.sender.user_id)
        if event.message_chain.has(At) and event.message_chain.has(Text):
            userid, context = event.message_chain.get(At)[0].qq, event.message_chain.get(Text)[0].text
        order_list = ['查🦌']
        if context in order_list:
            bot.logger.info("接收到查🦌请求")
            recall_id = await check_lu(userid,bot=bot,event=event)
            if config.group_fun.config["today_wife"]["签🦌撤回"] is True:
                await sleep(55)
                #await bot.recall(recall_id['data']['message_id'])

    @bot.on(GroupMessageEvent)
    async def supple_LU(event: GroupMessageEvent):
        context, userid=event.pure_text, str(event.sender.user_id)
        #if event.message_chain.has(At):userid, context = event.message_chain.get(At)[0].qq, event.message_chain.get(Text)[0].text
        order_list = ['补🦌']
        if context in order_list:
            bot.logger.info("接收到补🦌请求")
            recall_id = await supple_lu(userid,bot=bot,event=event)
            if config.group_fun.config["today_wife"]["签🦌撤回"] is True:
                await sleep(55)
                await bot.recall(recall_id['data']['message_id'])

    @bot.on(GroupMessageEvent)
    async def rank_LU(event: GroupMessageEvent):
        context, userid, type_check=event.pure_text, str(event.sender.user_id), 'month'
        #if event.message_chain.has(At):userid, context = event.message_chain.get(At)[0].qq, event.message_chain.get(Text)[0].text
        order_list = ['🦌排行','🦌排名']
        if not any(word in context for word in order_list):return
        bot.logger.info("接收到🦌排行请求")
        if any(word in context for word in ['每月','本月','当月']): type_check = 'month'
        elif any(word in context for word in ['年度', '今年']): type_check = 'year'
        elif any(word in context for word in ['所有', '总共', '全部']): type_check = 'total'
        recall_id = await bot.send(event, [f"开始查询中，请稍等喵～"])
        friendlist_get = await bot.get_group_member_list(event.group_id)
        userid_list = [friend['user_id'] for friend in friendlist_get["data"]]
        await rank_lu(userid_list,type_check,bot=bot,event=event)
        await bot.recall(recall_id['data']['message_id'])

    #菜单
    @bot.on(GroupMessageEvent)
    async def menu_lu(event: GroupMessageEvent):
        if event.pure_text.lower() in ['lu菜单','lu帮助','🦌菜单','🦌帮助',] :
            bot.logger.info("🦌菜单制作ing")
            draw_json=[
            {'type': 'basic_set','img_name_save': 'lu_menu.png'},
            {'type': 'avatar', 'subtype': 'common', 'img': [f"https://q1.qlogo.cn/g?b=qq&nk={event.self_id}&s=640"],'upshift_extra':15,
            'content': [f"[name]🦌 菜单喵[/name]\n[time]我要来视奸你们了喵[/time]"]},
            '\n- 🦌：一种生活方式'
            '\n- 多🦌！：🦌*n  eg：🦌🦌🦌🦌🦌🦌'
            '\n- 补🦌：帮你补上一天的🦌！'
            '\n- 戒🦌：清空你今天的🦌数据'
            '\n- 别名🦌： 鹿，这倒提醒我了，🦌！，鹿！'
            '\n- 🦌排行： 本月/年度/总共 🦌排行'
            '\n- 查🦌： 看看您最近🦌的状况'
            '\n- 贞操锁： 开启/关闭 贞操锁（开启后别人都无法帮你🦌，只能自己🦌了喵'
            '\n[des]                                             Function By 漫朔[/des]'
                       ]
            await bot.send(event, Image(file=(await manshuo_draw(draw_json))))

