from core.event.events import GroupMessageEvent
from core.message.message_components import Text
from core.database.user import get_user
from core.bot.extend_bot import ExtendBot
from core.config.manager import YAMLManager
from plugins.ai_code_generator.service.AiPluginGenerator import code_generate


def main(bot: ExtendBot,config: YAMLManager):
    @bot.on(GroupMessageEvent)
    async def _(event: GroupMessageEvent):
        if event.pure_text.startswith(config.ai_code_generator.ai_coder["prefix"]):
            user_info = await get_user(event.user_id)
            if user_info.permission>config.ai_code_generator.ai_coder["code_generation_permission_need"]:
                prompt=event.pure_text.replace(config.ai_code_generator.ai_coder["prefix"],"").strip()
                bot.logger.info(f"AI插件生成器收到需求:{prompt}")
                if prompt=="":
                    await bot.send(event, "请输入需求")
                    return
                r=await code_generate(config,prompt,event.user_id)
                await bot.send(event, "请查看控制台输出以验证")
            else:
                await bot.send(event, "你没有权限生成插件")

