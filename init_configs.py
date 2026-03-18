"""
Eridanus 配置文件初始化脚本
当配置文件被 .gitignore 忽略后，新部署时运行此脚本生成默认配置。
用法: python init_configs.py
"""
import os
import hashlib

CONFIGS = {
    "config/basic_config.yaml": """\
user_handle_logic: blacklist #模式。可填 blacklist, whitelist
user_handle_logic_operate_level: 1000
group_handle_logic: blacklist
group_handle_logic_operate_level: 1000
邀请bot加群所需权限: 0
申请bot好友所需权限: 0

webui:
  enable: true
record_mface: true
proxy:
  http_proxy: ""
  socks_proxy: ""
bot: "Eridanus"
master:
  name: "管理员"
  id: 0           # 填写管理员QQ号
group: 0           # 填写测试群号
adapter:
  name: "any"
  use_new_core_bot: false
  ws_client:
    ws_link: "ws://127.0.0.1:3001"

PluginLoadConfig:
  load_strategy: "batch_loading"
  batch_size: 4
  batch_delay: 2
  max_retries: 3
  retry_delay: 1
  memory_threshold_mb: 200
  enable_gc_between_batches: True
HandlerMonitor:
  enable: false
  handler_timeout_warning: 15
redis:
  redis_ip: default
  redis_port: default
  redis_db: default
""",

    "config/censor_user.yaml": """\
blacklist:
- 0
whitelist:
- 0
""",

    "config/censor_group.yaml": """\
blacklist:
- 0
whitelist:
- 0
""",

    "plugins/ai_llm/config.yaml": """\
llm:
  model: openai   #可选openai、gemini、default
  system: ""
  chara_file_name: 猫娘.txt
  自动清理无效apikey: false
  retries: 6
  stream: true
  openai:
    enable_official_sdk: true
    api_keys:
    - ""              # 填写你的API Key
    model: ""         # 填写模型名称
    quest_url: ""     # 填写API地址
    temperature: 1
    max_tokens: 2048
    CoT: true
    使用旧版prompt结构: false
  gemini:
    api_keys:
    - ""              # 填写Gemini API Key
    model: gemini-3-flash-preview
    base_url: https://generativelanguage.googleapis.com
    temperature: 0.7
    maxOutputTokens: 2048
    include_thoughts: true
    fallback_models:
    - gemini-3-flash-preview
    - gemini-2.5-flash
    - gemini-2.0-flash-lite
    - gemini-2.5-flash-lite
  default:
    model: gpt-4o-mini
  腾讯元器:
    智能体ID: ""
    token: ""
  func_calling: true
  表情包发送: true
  单次发送表情包数量: 1
  google_search: false
  url_context: false
  联网搜索显示原始数据: true
  search_client:
    api_key: ""
    base_url: "https://generativelanguage.googleapis.com"
    model: ""
  utility_client:
    type: "gemini"
    api_key: ""
    base_url: ""
    model: ""
  读取群聊上下文: true
  群消息保留数量: 30
  上下文带原文: true
  上下文带图片原文: false
  可获取的群聊上下文长度: 10
  用户画像: false
  用户画像更新间隔: 360
  群聊总结:
    enable: false
    总结间隔消息数: 10
    聊天带总结: true
    读取图片: false
    whitelist_enabled: true
    chat_whitelist: []
  prefix: []
  aiReplyCore: true
  enable_proxy: false
  max_history_length: 40
  仁济模式:
    随机回复概率: 0
    算法回复:
      enable: false
      相似度阈值: 30
      频率阈值: 15
      消息列表最小长度: 10
      信息熵阈值: 2
    延时相关性:
      enable: false
      置信度阈值: 0.9
      有效延时: 100
  Quote: false
  语音回复几率: 30
  语音回复附带文本: true
heartflow:
  enabled: false
  system: ""
  listen_image: false
  client:
    type: "gemini"
    api_key: ""
    base_url: "https://generativelanguage.googleapis.com"
    model: "gemma-3-27b-it"
    temperature: 0.7
    max_tokens: 2048
  reply_threshold: 0.6
  energy_decay_rate: 0.1
  energy_recovery_rate: 0.02
  context_messages_count: 10
  interaction_timeout: 300
  whitelist_enabled: true
  chat_whitelist: []
  weight_relevance: 0.25
  weight_willingness: 0.2
  weight_social: 0.2
  weight_timing: 0.15
  weight_continuity: 0.2
core:
  ai_reply_group: 0
  ai_reply_private: 0
  ai_change_character: 0
  ai_token_limt: 0
  ai_token_limt_token: 10000
""",

    "plugins/Grok2api/config.yaml": """\
TEMP_DIR_VIDEO: "data/video/cache"
TEMP_DIR_IMAGE: "data/pictures/cache"
QUOTA_FILE: "grok_video_quota.json"
BASE_URL: "http://127.0.0.1:8000"
API_KEY: ""               # 填写xAI API Key
MODEL_VIDEO: "grok-imagine-1.0-video"
MODEL_IMAGE: "grok-imagine-1.0"
PERMISSION_NEED: 2
DAILY_LIMIT: 20
CONCURRENT_LIMIT: 1
TIMEOUT: 300
""",

    "plugins/anime_game_service/config.yaml": """\
steamsnooping:
  is_snooping: False
  steam_api_key:
    - ""              # 填写Steam API Key
  game_white:
    - Wallpaper Engine
    - MyDockFinder
    - MyDockerFinder
    - DSX
    - Source SDK
""",

    "plugins/basic_plugin/config.yaml": """\
心知天气:
  api_key: ""
image_search:
  sauceno_api_key: ""
nasa_api:
  api_key: ""
setu:
  r18mode: true
  download: true
  gray_layer: true
  setu_operate_level: 0
  today_img_list:
    - '巨乳'
    - '贫乳'
    - '萝莉'
    - '黑丝'
    - '白丝'
tarot:
  lock: false
  mode: "blueArchive"
  彩蛋牌:
    enable: true
    probability: 5
    card_index:
      - data/pictures/tarot/hidden_tarot/dio.jpg: ""
      - data/pictures/tarot/hidden_tarot/GIOGIO.jpg: ""
      - data/pictures/tarot/hidden_tarot/gyro.jpg: ""
      - data/pictures/tarot/hidden_tarot/hp.jpg: ""
      - data/pictures/tarot/hidden_tarot/johnny.jpg: ""
      - data/pictures/tarot/hidden_tarot/joseph.jpg: ""
      - data/pictures/tarot/hidden_tarot/vlt.jpg: ""
搜图:
  search_image_resource_operate_level: 0
  聚合搜图: true
  soutu_bot: true
self_condition:
  enable: False
""",

    "plugins/groupManager/config.yaml": """\
启用ai入群欢迎: true
is_at: False
通用入群欢迎: '欢迎。'
固定入群欢迎: {}
退群通知: true
自动退群: false
自动退出少于此人数的群: 1
自动退出多于此人数的群: 10000
BullshitMsgBlocker:
  enable: false
  blockList: []
  消息缓存池大小: 5
  每人最大发言数量: 5
  禁言时长: 180
  嘲讽: "检测到群友自言自语，已禁言180秒。"
""",

    "plugins/streaming_media/bili_dynamic.yaml": """\
# B站动态推送配置
# 格式:
#   UID:
#     latest_dynamic_id: []
#     push_groups:
#       - 群号
""",

    "web/user_info.yaml": f"""\
account: eridanus
password: {hashlib.sha256(b"eridanus").hexdigest()}
friends: 0
groups: 0
""",
}

# 需要创建的空目录
DIRS = [
    "data/pictures/tarot",
    "data/pictures/Amamiya",
    "data/pictures/doc",
    "data/pictures/blueArchive",
    "data/pictures/galgame",
    "data/pictures/benzi",
    "data/pictures/wife_you_want_img",
    "data/pictures/auto_reply",
    "data/pictures/cache",
    "data/pictures/Mface",
    "data/pictures/emojimix",
    "data/voice/cache",
    "data/video/cache",
    "data/cache",
    "data/dataBase",
    "data/system/chara",
]


def main():
    created = []
    skipped = []

    # 创建目录
    for d in DIRS:
        os.makedirs(d, exist_ok=True)
    print(f"[OK] 已确保 {len(DIRS)} 个数据目录存在")

    # 生成配置文件
    for path, content in CONFIGS.items():
        if os.path.exists(path):
            skipped.append(path)
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            created.append(path)

    if created:
        print(f"\n[已创建] 以下配置文件（请填写敏感字段）:")
        for p in created:
            print(f"  - {p}")

    if skipped:
        print(f"\n[已跳过] 以下配置文件已存在:")
        for p in skipped:
            print(f"  - {p}")

    print("\n完成！请编辑配置文件填写 API Key、QQ号等信息。")


if __name__ == "__main__":
    main()
