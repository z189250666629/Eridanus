"""Config backup and restore helpers for the standalone WebUI."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from core.toolkit.logger import get_logger


logger = get_logger("web.config_tools")
yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)

APP_ROOT = Path(__file__).resolve().parent.parent
BACKUP_ROOT = APP_ROOT / "config_backups"
CONFIG_ROOT = APP_ROOT / "config"
PLUGINS_ROOT = APP_ROOT / "plugins"
MANAGED_ROOTS = (
    ("config", CONFIG_ROOT),
    ("plugins", PLUGINS_ROOT),
)


def _iter_yaml_files(base_dir: Path):
    for root, _, files in os.walk(base_dir):
        for file_name in files:
            if file_name.endswith(".yaml"):
                file_path = Path(root) / file_name
                yield file_path.relative_to(base_dir)


def merge_dicts(old: dict[str, Any], new: dict[str, Any]) -> None:
    for key, value in old.items():
        if isinstance(value, dict) and key in new and isinstance(new[key], dict):
            merge_dicts(value, new[key])
        elif isinstance(value, list) and key in new and isinstance(new[key], list):
            if key in {
                "api_keys",
                "sdUrl",
                "其他默认绘图参数",
                "card_index",
                "steam_api_key",
                "nano_banana_key",
                "固定入群欢迎",
            }:
                new[key] = value
            elif isinstance(key, str) and key.startswith("page"):
                continue
            else:
                try:
                    new[key] = list(dict.fromkeys(new[key] + value))
                except Exception:
                    logger.warning(f"列表合并失败，保留新值: {key}")
        elif key in new and type(value) != type(new[key]):
            continue
        elif key in new:
            new[key] = value
        elif isinstance(key, int):
            new[key] = value


def conflict_file_dealer(old_file: Path, new_file: Path) -> None:
    with old_file.open("r", encoding="utf-8") as file_obj:
        old_data = yaml.load(file_obj)
    with new_file.open("r", encoding="utf-8") as file_obj:
        new_data = yaml.load(file_obj)

    merge_dicts(old_data, new_data)

    with new_file.open("w", encoding="utf-8") as file_obj:
        yaml.dump(new_data, file_obj)


def export_yaml() -> list[str]:
    if BACKUP_ROOT.exists():
        shutil.rmtree(BACKUP_ROOT)
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)

    exported: list[str] = []
    for label, root_dir in MANAGED_ROOTS:
        if not root_dir.exists():
            continue
        for relative_path in _iter_yaml_files(root_dir):
            src_path = root_dir / relative_path
            dst_path = BACKUP_ROOT / label / relative_path
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst_path)
            exported.append(f"{label}/{relative_path.as_posix()}")

    logger.info(f"导出 yaml 文件完成: {BACKUP_ROOT}")
    return exported


def import_yaml() -> list[str]:
    if not BACKUP_ROOT.exists():
        raise FileNotFoundError(f"备份目录不存在: {BACKUP_ROOT}")

    restored: list[str] = []
    for label, root_dir in MANAGED_ROOTS:
        backup_dir = BACKUP_ROOT / label
        if not backup_dir.exists() or not root_dir.exists():
            continue

        for relative_path in _iter_yaml_files(root_dir):
            current_file = root_dir / relative_path
            backup_file = backup_dir / relative_path
            if not backup_file.exists():
                logger.warning(f"备份中缺少文件，跳过: {backup_file}")
                continue
            conflict_file_dealer(backup_file, current_file)
            restored.append(f"{label}/{relative_path.as_posix()}")

    return restored


__all__ = ["BACKUP_ROOT", "export_yaml", "import_yaml"]
