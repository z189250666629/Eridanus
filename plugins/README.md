# plugins

当前运行时插件目录位于这里。

当前阶段：

- 插件实体目录已迁移到这里。
- `PLUGINS_MODULE_PREFIX` 已切换到 `plugins`，当前运行时主链已以 `plugins.*` 为准。
- 仍保留少量 `run.* -> plugins.*` 兼容命名空间，只用于历史导入兼容，不再作为新代码落点。
