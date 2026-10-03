#!/usr/bin/env python3
"""Bump every plugin changed by a push to main; the level comes from the merged PR's release labels."""

import argparse
import subprocess
import sys
from collections.abc import Collection, Iterable
from pathlib import Path
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bump_plugin_version import PLUGINS_ROOT, update_plugin_version  # noqa: E402

LABEL_LEVELS = {"release:major": "major", "release:minor": "minor"}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def level_from_labels(labels: Iterable[str]) -> str:
    levels = {LABEL_LEVELS[label] for label in labels if label in LABEL_LEVELS}
    if "major" in levels:
        return "major"
    if "minor" in levels:
        return "minor"
    return "patch"


def resolve_base(before: str, after: str) -> str:
    return f"{after}~1" if set(before) <= {"0"} else before


def plugin_of(path: str) -> str | None:
    parts = Path(path).parts
    return parts[1] if len(parts) >= 3 and parts[0] == "plugins" else None


def select_plugins(paths: Iterable[str], new_plugins: Collection[str] = ()) -> list[str]:
    # A new plugin ships at its declared version; the workflow skips the bot's own bump commit by its message.
    changed = {plugin_of(path) for path in paths} - {None}
    return sorted(p for p in changed if p not in new_plugins)


def changed_plugins(before: str, after: str) -> list[str]:
    base = resolve_base(before, after)
    paths = git("diff", "--name-only", base, after).splitlines()
    touched = {plugin_of(p) for p in paths} - {None}
    new = {
        p for p in touched
        if subprocess.run(["git", "cat-file", "-e", f"{base}:plugins/{p}/.claude-plugin/plugin.json"],
                          capture_output=True).returncode != 0
    }
    return [p for p in select_plugins(paths, new) if (PLUGINS_ROOT / p).is_dir()]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", help="Commit before the push (all zeros for a new branch)")
    parser.add_argument("after", help="Head commit of the push")
    parser.add_argument("--labels", default="", help="Comma-separated labels of the merged PR")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    level = level_from_labels(label.strip() for label in args.labels.split(","))
    try:
        for plugin in changed_plugins(args.before, args.after):
            current, target, _ = update_plugin_version(PLUGINS_ROOT, plugin, level, dry_run=args.dry_run)
            print(f"{plugin}: {current} -> {target} ({level})")
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Version bump failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
