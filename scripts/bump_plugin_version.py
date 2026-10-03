#!/usr/bin/env python3
"""Update the Claude and Codex manifest versions for one plugin."""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
PLUGINS_ROOT = ROOT / "plugins"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)
BUMP_KINDS = {"major", "minor", "patch"}


@dataclass(frozen=True)
class SemVer:
    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...] = ()
    build: tuple[str, ...] = ()

    @classmethod
    def parse(cls, value: str) -> SemVer:
        match = SEMVER_RE.fullmatch(value)
        if match is None:
            raise ValueError(f"invalid semantic version: {value!r}")
        prerelease = tuple(match.group(4).split(".")) if match.group(4) else ()
        build = tuple(match.group(5).split(".")) if match.group(5) else ()
        if any(
            identifier.isdigit() and len(identifier) > 1 and identifier.startswith("0")
            for identifier in prerelease
        ):
            raise ValueError(f"invalid semantic version: {value!r}")
        return cls(
            major=int(match.group(1)),
            minor=int(match.group(2)),
            patch=int(match.group(3)),
            prerelease=prerelease,
            build=build,
        )

    def __str__(self) -> str:
        value = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            value += f"-{'.'.join(self.prerelease)}"
        if self.build:
            value += f"+{'.'.join(self.build)}"
        return value

    def bump(self, kind: str) -> SemVer:
        if kind == "major":
            return SemVer(self.major + 1, 0, 0)
        if kind == "minor":
            return SemVer(self.major, self.minor + 1, 0)
        if kind == "patch":
            return SemVer(self.major, self.minor, self.patch + 1)
        raise ValueError(f"unsupported bump kind: {kind!r}")

    def compare_precedence(self, other: SemVer) -> int:
        left_core = (self.major, self.minor, self.patch)
        right_core = (other.major, other.minor, other.patch)
        if left_core != right_core:
            return 1 if left_core > right_core else -1
        if not self.prerelease and not other.prerelease:
            return 0
        if not self.prerelease:
            return 1
        if not other.prerelease:
            return -1
        for left, right in zip(self.prerelease, other.prerelease):
            if left == right:
                continue
            left_numeric = left.isdigit()
            right_numeric = right.isdigit()
            if left_numeric and right_numeric:
                return 1 if int(left) > int(right) else -1
            if left_numeric != right_numeric:
                return -1 if left_numeric else 1
            return 1 if left > right else -1
        if len(self.prerelease) == len(other.prerelease):
            return 0
        return 1 if len(self.prerelease) > len(other.prerelease) else -1


def is_valid_semver(value: str) -> bool:
    try:
        SemVer.parse(value)
    except ValueError:
        return False
    return True


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bump both harness manifest versions for one plugin."
    )
    parser.add_argument("plugin", help="Plugin directory name")
    parser.add_argument(
        "version",
        help="One of major, minor, patch, or an explicit semantic version",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the version change without writing either manifest",
    )
    return parser.parse_args(argv)


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"missing plugin manifest: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON in {path}: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"manifest root must be an object: {path}")
    return payload


def manifest_paths(plugin_root: Path) -> tuple[Path, Path]:
    return (
        plugin_root / ".claude-plugin" / "plugin.json",
        plugin_root / ".codex-plugin" / "plugin.json",
    )


def resolve_version(current: SemVer, requested: str) -> SemVer:
    if requested in BUMP_KINDS:
        return current.bump(requested)
    return SemVer.parse(requested)


def update_plugin_version(
    plugins_root: Path,
    plugin: str,
    requested: str,
    *,
    dry_run: bool = False,
) -> tuple[str, str, tuple[Path, Path]]:
    if NAME_RE.fullmatch(plugin) is None or len(plugin) > 64:
        raise ValueError(f"invalid plugin name: {plugin!r}")

    plugin_root = plugins_root / plugin
    if not plugin_root.is_dir():
        raise ValueError(f"plugin does not exist: {plugin}")

    paths = manifest_paths(plugin_root)
    manifests = [load_manifest(path) for path in paths]
    for path, manifest in zip(paths, manifests):
        if manifest.get("name") != plugin:
            raise ValueError(f"manifest name does not match {plugin!r}: {path}")
        if not isinstance(manifest.get("version"), str):
            raise ValueError(f"manifest version must be a string: {path}")

    versions = [manifest["version"] for manifest in manifests]
    if versions[0] != versions[1]:
        raise ValueError(
            "Claude and Codex manifest versions disagree: "
            f"{versions[0]!r} != {versions[1]!r}"
        )

    current = SemVer.parse(versions[0])
    target = resolve_version(current, requested)
    if str(target) == str(current):
        raise ValueError(f"plugin is already at version {target}")
    if target.compare_precedence(current) < 0:
        raise ValueError(f"refusing to downgrade {current} to {target}")

    if not dry_run:
        originals = [path.read_text(encoding="utf-8") for path in paths]
        try:
            for path, manifest in zip(paths, manifests):
                manifest["version"] = str(target)
                path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        except BaseException:
            for path, original in zip(paths, originals):
                path.write_text(original, encoding="utf-8")
            raise

    return str(current), str(target), paths


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        current, target, paths = update_plugin_version(
            PLUGINS_ROOT,
            args.plugin,
            args.version,
            dry_run=args.dry_run,
        )
    except (OSError, ValueError) as error:
        print(f"Version bump failed: {error}", file=sys.stderr)
        return 1

    prefix = "Would bump" if args.dry_run else "Bumped"
    print(f"{prefix} {args.plugin}: {current} -> {target}")
    for path in paths:
        print(f"- {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")
    if not args.dry_run:
        print("Validate: uv run --locked scripts/validate.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
