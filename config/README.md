# config

当前配置已正式并入 `Eridanus/config/`。

这里承接原先位于仓库根 `config/` 下的核心配置文件：

- `basic_config.yaml`
- `menu.yaml`
- `censor_group.yaml`
- `censor_user.yaml`

`YAMLManager` 当前会优先读取本目录，并暂时保留仓库根 `config/` 作为过渡期回退路径。
