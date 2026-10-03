#!/usr/bin/env python3
"""Validate cross-harness marketplace catalogs and their skill plugins."""

import json
import re
import sys
from pathlib import Path
from typing import Any


from bump_plugin_version import is_valid_semver

ROOT = Path(__file__).resolve().parents[1]
PLUGINS_ROOT = ROOT / "plugins"
CLAUDE_MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
CODEX_MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---(?:\n|\Z)", re.DOTALL)


class Validation:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def error(self, path: Path, message: str) -> None:
        try:
            label = path.relative_to(ROOT).as_posix()
        except ValueError:
            label = str(path)
        self.errors.append(f"{label}: {message}")


def load_object(path: Path, check: Validation) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        check.error(path, "file is missing")
        return None
    except json.JSONDecodeError as error:
        check.error(path, f"invalid JSON: {error}")
        return None
    if not isinstance(payload, dict):
        check.error(path, "root must be a JSON object")
        return None
    return payload


def catalog_entries(
    path: Path, payload: dict[str, Any] | None, check: Validation
) -> list[dict[str, Any]]:
    if payload is None:
        return []
    if payload.get("name") != "theology-skills":
        check.error(path, "name must be 'theology-skills'")
    entries = payload.get("plugins")
    if not isinstance(entries, list):
        check.error(path, "plugins must be an array")
        return []
    if not all(isinstance(entry, dict) for entry in entries):
        check.error(path, "every plugin entry must be an object")
        return []
    names = [entry.get("name") for entry in entries]
    string_names = [name for name in names if isinstance(name, str)]
    if len(string_names) != len(set(string_names)):
        check.error(path, "plugin names must be unique")
    return entries


def validate_catalog_entry(
    path: Path, entry: dict[str, Any], harness: str, check: Validation
) -> None:
    name = entry.get("name")
    if not isinstance(name, str) or NAME_RE.fullmatch(name) is None or len(name) > 64:
        check.error(path, f"invalid plugin name: {name!r}")
        return
    expected_path = f"./plugins/{name}"
    if harness == "claude":
        if entry.get("source") != expected_path:
            check.error(path, f"{name!r} source must be {expected_path!r}")
        if not isinstance(entry.get("description"), str) or not entry["description"].strip():
            check.error(path, f"{name!r} must include a description")
    else:
        expected_source = {"source": "local", "path": expected_path}
        if entry.get("source") != expected_source:
            check.error(path, f"{name!r} source must be {expected_source!r}")
        policy = entry.get("policy")
        if not isinstance(policy, dict):
            check.error(path, f"{name!r} must include a policy object")
        else:
            if policy.get("installation") not in {
                "NOT_AVAILABLE",
                "AVAILABLE",
                "INSTALLED_BY_DEFAULT",
            }:
                check.error(path, f"{name!r} has invalid policy.installation")
            if policy.get("authentication") not in {"ON_INSTALL", "ON_USE"}:
                check.error(path, f"{name!r} has invalid policy.authentication")
    if not isinstance(entry.get("category"), str) or not entry["category"].strip():
        check.error(path, f"{name!r} must include a category")


def frontmatter_value(frontmatter: str, key: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*(.+?)\s*$", frontmatter)
    if match is None:
        return None
    value = match.group(1)
    if value.startswith('"'):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, str) else None
    return value.strip("' ")


def validate_skill(path: Path, expected_name: str, check: Validation) -> None:
    try:
        contents = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        check.error(path, "SKILL.md is missing")
        return
    match = FRONTMATTER_RE.match(contents)
    if match is None:
        check.error(path, "must start with closed YAML frontmatter")
        return
    frontmatter = match.group("body")
    if frontmatter_value(frontmatter, "name") != expected_name:
        check.error(path, f"frontmatter name must be {expected_name!r}")
    description = frontmatter_value(frontmatter, "description")
    if not description:
        check.error(path, "frontmatter description must be non-empty")
    if "[TODO:" in contents:
        check.error(path, "contains an unfinished [TODO: ...] marker")


def validate_plugin(name: str, check: Validation) -> None:
    plugin_root = PLUGINS_ROOT / name
    claude_path = plugin_root / ".claude-plugin" / "plugin.json"
    codex_path = plugin_root / ".codex-plugin" / "plugin.json"
    claude = load_object(claude_path, check)
    codex = load_object(codex_path, check)
    if claude is None or codex is None:
        return

    for path, manifest in ((claude_path, claude), (codex_path, codex)):
        if manifest.get("name") != name:
            check.error(path, f"name must match plugin directory {name!r}")
        version = manifest.get("version")
        if not isinstance(version, str) or not is_valid_semver(version):
            check.error(path, "version must use semantic versioning")
        if not isinstance(manifest.get("description"), str) or not manifest["description"].strip():
            check.error(path, "description must be non-empty")
        if manifest.get("skills") != "./skills/":
            check.error(path, "skills must be './skills/'")
    if claude.get("version") != codex.get("version"):
        check.error(plugin_root, "Claude and Codex manifest versions must match")

    interface = codex.get("interface")
    if not isinstance(interface, dict):
        check.error(codex_path, "interface must be an object")
    else:
        for field in (
            "displayName",
            "shortDescription",
            "longDescription",
            "developerName",
            "category",
        ):
            if not isinstance(interface.get(field), str) or not interface[field].strip():
                check.error(codex_path, f"interface.{field} must be non-empty")
        if not isinstance(interface.get("capabilities"), list):
            check.error(codex_path, "interface.capabilities must be an array")
        prompts = interface.get("defaultPrompt")
        if not isinstance(prompts, list) or not prompts or not all(
            isinstance(prompt, str) and prompt.strip() for prompt in prompts
        ):
            check.error(codex_path, "interface.defaultPrompt must be a non-empty string array")

    skills_root = plugin_root / "skills"
    if not skills_root.is_dir():
        check.error(skills_root, "skills directory is missing")
        return
    skill_dirs = sorted(
        path for path in skills_root.iterdir() if path.is_dir() and not path.name.startswith(".")
    )
    if not skill_dirs:
        check.error(skills_root, "plugin must contain at least one skill directory")
    for skill_root in skill_dirs:
        skill_name = skill_root.name
        if NAME_RE.fullmatch(skill_name) is None or len(skill_name) > 64:
            check.error(skill_root, f"invalid skill directory name: {skill_name!r}")
        validate_skill(skill_root / "SKILL.md", skill_name, check)


def main() -> int:
    check = Validation()
    claude_payload = load_object(CLAUDE_MARKETPLACE, check)
    codex_payload = load_object(CODEX_MARKETPLACE, check)
    claude_entries = catalog_entries(CLAUDE_MARKETPLACE, claude_payload, check)
    codex_entries = catalog_entries(CODEX_MARKETPLACE, codex_payload, check)

    for entry in claude_entries:
        validate_catalog_entry(CLAUDE_MARKETPLACE, entry, "claude", check)
    for entry in codex_entries:
        validate_catalog_entry(CODEX_MARKETPLACE, entry, "codex", check)

    claude_names = [entry.get("name") for entry in claude_entries]
    codex_names = [entry.get("name") for entry in codex_entries]
    if claude_names != codex_names:
        check.error(ROOT, "Claude and Codex catalogs must list the same plugins in the same order")

    plugin_dirs = sorted(
        path.name
        for path in PLUGINS_ROOT.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )
    listed_names = [name for name in claude_names if isinstance(name, str)]
    if plugin_dirs != sorted(listed_names):
        check.error(
            PLUGINS_ROOT,
            f"plugin directories {plugin_dirs!r} do not match catalog entries {sorted(listed_names)!r}",
        )
    for name in listed_names:
        validate_plugin(name, check)

    if check.errors:
        print("Marketplace validation failed:", file=sys.stderr)
        for error in check.errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Marketplace validation passed ({len(listed_names)} plugins).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
