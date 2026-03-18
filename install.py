"""CLI helper for installing Eridanus dependency profiles."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parent
app_root_str = str(APP_ROOT)
if app_root_str not in sys.path:
    sys.path.insert(0, app_root_str)

from core.toolkit.installer import (
    list_available_plugins,
    list_available_profiles,
    install_plugin_requirements,
    install_profile,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install dependency groups for Eridanus.")
    parser.add_argument(
        "--profile",
        action="append",
        choices=list_available_profiles(),
        help="Install a shared dependency profile such as base/web/adapter-onebot/all.",
    )
    parser.add_argument(
        "--plugin",
        action="append",
        choices=list_available_plugins(),
        help="Install requirements for a specific plugin.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.profile and not args.plugin:
        parser.print_help()
        return 1

    ok = True
    for profile_name in args.profile or []:
        ok = install_profile(profile_name) and ok
    for plugin_name in args.plugin or []:
        ok = install_plugin_requirements(plugin_name) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
