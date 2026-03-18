"""Runtime dependency installer hosted under core.toolkit."""

from __future__ import annotations

import importlib
import importlib.util
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

from .logger import get_logger

logger = get_logger()

APP_ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS_ROOT = APP_ROOT / "requirements"
PLUGINS_ROOT = APP_ROOT / "plugins"

PACKAGE_NAME_ALIASES = {
    "flask_sock": "flask-sock",
    "flask-sock": "flask-sock",
    "qzone-api": "qzone_api",
    "qzone_api": "qzone_api",
    "python-dateutil": "python-dateutil",
    "dateutil": "python-dateutil",
    "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn",
}

PROFILE_REQUIREMENT_FILES = {
    "base": REQUIREMENTS_ROOT / "base.txt",
    "web": REQUIREMENTS_ROOT / "web.txt",
    "adapter-onebot": REQUIREMENTS_ROOT / "adapter-onebot.txt",
    "legacy-compat": REQUIREMENTS_ROOT / "legacy-compat.txt",
    "all": REQUIREMENTS_ROOT / "all.txt",
}

_FAILED_INSTALLS: set[str] = set()
_REQUIREMENT_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+")


def _resolve_package_name(package_name: str) -> str:
    return PACKAGE_NAME_ALIASES.get(package_name, package_name)


def _normalize_package_name(package_name: str) -> str:
    return _resolve_package_name(package_name).strip().lower().replace("_", "-")


def _extract_requirement_name(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or stripped.startswith("-r "):
        return None
    match = _REQUIREMENT_NAME_RE.match(stripped)
    if match is None:
        return None
    return _normalize_package_name(match.group(0))


def _iter_plugin_requirement_files():
    if not PLUGINS_ROOT.exists():
        return
    for requirement_file in PLUGINS_ROOT.glob("*/requirements.txt"):
        yield requirement_file


@lru_cache(maxsize=1)
def build_requirement_index() -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = {}
    requirement_files = list(PROFILE_REQUIREMENT_FILES.values()) + list(_iter_plugin_requirement_files())
    for requirement_file in requirement_files:
        if not requirement_file.exists():
            continue
        for line in requirement_file.read_text(encoding="utf-8").splitlines():
            package_name = _extract_requirement_name(line)
            if package_name is None:
                continue
            index.setdefault(package_name, []).append(requirement_file)
    return index


def _install_command_for_target(target: Path | str) -> list[str]:
    if isinstance(target, Path):
        return [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "-r",
            str(target),
        ]
    return [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        target,
    ]


def install_target(target: Path | str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        _install_command_for_target(target),
        capture_output=True,
        text=True,
        check=False,
    )


def install_profile(profile_name: str) -> bool:
    requirement_file = PROFILE_REQUIREMENT_FILES.get(profile_name)
    if requirement_file is None:
        raise ValueError(f"未知依赖分组: {profile_name}")
    if not requirement_file.exists():
        raise FileNotFoundError(f"依赖文件不存在: {requirement_file}")

    logger.info(f"安装依赖分组: {profile_name} -> {requirement_file}")
    result = install_target(requirement_file)
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "无额外输出").strip()
        logger.error(f"依赖分组安装失败: {profile_name}，详情：{stderr[-400:]}")
        return False
    return True


def install_plugin_requirements(plugin_name: str) -> bool:
    requirement_file = PLUGINS_ROOT / plugin_name / "requirements.txt"
    if not requirement_file.exists():
        raise FileNotFoundError(f"插件依赖文件不存在: {requirement_file}")

    logger.info(f"安装插件依赖: {plugin_name} -> {requirement_file}")
    result = install_target(requirement_file)
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "无额外输出").strip()
        logger.error(f"插件依赖安装失败: {plugin_name}，详情：{stderr[-400:]}")
        return False
    return True


def list_available_profiles() -> list[str]:
    return list(PROFILE_REQUIREMENT_FILES.keys())


def list_available_plugins() -> list[str]:
    return sorted(path.parent.name for path in _iter_plugin_requirement_files())


def resolve_install_target(package_name: str) -> Path | str:
    normalized_name = _normalize_package_name(package_name)
    owners = build_requirement_index().get(normalized_name, [])
    if len(owners) == 1:
        return owners[0]
    return _resolve_package_name(package_name)


def install_and_import(package_name, import_name=None):
    """检测模块是否已安装，若未安装则按新的依赖布局安装。"""

    if import_name is None:
        import_name = package_name

    spec = importlib.util.find_spec(import_name)
    if spec is None:
        target = resolve_install_target(package_name)
        failure_key = str(target)
        if failure_key in _FAILED_INSTALLS:
            logger.warning(f"{failure_key} 先前已安装失败，本次跳过重复安装尝试。")
            return None

        if isinstance(target, Path):
            logger.warning(f"{import_name} 未安装，正在按依赖文件安装: {target}")
        else:
            logger.warning(f"{import_name} 未安装，正在直接安装 pip 包: {target}")

        result = install_target(target)
        spec = importlib.util.find_spec(import_name)
        if spec is None:
            _FAILED_INSTALLS.add(failure_key)
            stderr = (result.stderr or "").strip()
            stdout = (result.stdout or "").strip()
            tail = stderr or stdout or "无额外输出"
            logger.error(
                f"安装失败：无法找到 {import_name} 模块。"
                f" 安装目标={failure_key}，退出码={result.returncode}，详情：{tail[-400:]}"
            )
            return None

    return importlib.import_module(import_name)


__all__ = [
    "APP_ROOT",
    "PACKAGE_NAME_ALIASES",
    "PLUGINS_ROOT",
    "PROFILE_REQUIREMENT_FILES",
    "REQUIREMENTS_ROOT",
    "build_requirement_index",
    "install_and_import",
    "install_plugin_requirements",
    "install_profile",
    "install_target",
    "list_available_plugins",
    "list_available_profiles",
    "resolve_install_target",
]
