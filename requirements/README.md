## Eridanus Dependency Layout

本目录用于承接 `Eridanus/requirements.txt` 的单体依赖拆分。

### 当前规范

- `base.txt`
  - 仅放 `core/`、共享 `toolkit/`、共享数据库 / 配置 / 绘图能力所必需的依赖
  - 规则：如果依赖被多个插件复用，或者被 `Eridanus/main.py`、`core/*` 直接引用，优先归入这里

- `web.txt`
  - 仅放 `Eridanus/web/` 所需依赖
  - 规则：只有 WebUI 路径需要的包才能放这里，避免把插件依赖重新堆回 Web 层

- `adapter-onebot.txt`
  - 仅放 `adapters/onebot/` 相关传输层依赖
  - 规则：OneBot WebSocket / HTTP 传输层独占的包放这里，不并回 `base.txt`
  - 现状：由于 `Eridanus/main.py` 在导入期就会加载 OneBot adapter，当前“最小可运行集合”也需要包含这一组

- `all.txt`
  - 聚合入口
  - 当前聚合 `base/web/adapter` 三类公共依赖、`legacy-compat.txt`，以及已完成归档的插件级 `requirements.txt`
  - 规则：`python Eridanus/install.py --profile all` 应等价于旧单体依赖的完整安装入口

- `legacy-compat.txt`
  - 暂存“旧单体依赖里存在，但当前代码搜索暂未定位到稳定直接 import”的兼容保留项
  - 规则：这类依赖后续要么被确认迁入某个明确边界，要么在验证后删除，不能长期作为黑盒堆积

- `plugins/<plugin>/requirements.txt`
  - 插件自己的依赖入口
  - 规则：只放该插件独占或高耦合依赖；如果两个以上插件长期共享，再评估是否提升到 `base/` 或单独的共享组

### 归档边界

- `core`
  - `Eridanus/main.py`
  - `Eridanus/core/**`
  - `Eridanus/core/draw/**`

- `web`
  - `Eridanus/web/**`

- `adapter`
  - `Eridanus/adapters/onebot/**`

- `plugin`
  - `Eridanus/plugins/<plugin>/**`

### 迁移约束

- 不允许再把所有新依赖直接堆回单一 `requirements.txt`
- 新增依赖时，必须先判断归属边界，再落到对应文件
- `all.txt` 只负责聚合，不直接手写完整依赖列表
- `P6-2a` 只定义规范和骨架；实际包归档在 `P6-2b` 继续推进
