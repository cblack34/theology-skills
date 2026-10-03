#!/usr/bin/env python3
"""Create a cross-harness plugin with its first skill, or add a skill to an existing plugin."""

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PLUGINS_ROOT = ROOT / "plugins"
CLAUDE_MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
CODEX_MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"
MARKETPLACE_NAME = "theology-skills"
AUTHOR_NAME = "Clayton Black"
REPOSITORY_URL = "https://github.com/cblack34/theology-skills"
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create one skill as a Claude, Codex, and Grok-compatible plugin."
    )
    parser.add_argument("name", help="Skill name; normalized to lowercase kebab-case")
    parser.add_argument(
        "--description",
        required=True,
        help="Specific description of what the skill does and when to use it",
    )
    parser.add_argument(
        "--plugin",
        help="Add the skill to this existing plugin instead of creating a new plugin",
    )
    parser.add_argument("--category", default="Productivity")
    parser.add_argument("--version", default="0.1.0")
    return parser.parse_args()


def normalize_name(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    normalized = re.sub(r"-{2,}", "-", normalized)
    if not normalized:
        raise ValueError("name must contain at least one letter or digit")
    if len(normalized) > 64:
        raise ValueError("normalized name must be at most 64 characters")
    return normalized


def display_name(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split("-"))


def read_catalog(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"missing marketplace catalog: {path.relative_to(ROOT)}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON in {path.relative_to(ROOT)}: {error}") from error
    if not isinstance(payload, dict) or payload.get("name") != MARKETPLACE_NAME:
        raise ValueError(
            f"{path.relative_to(ROOT)} must be the {MARKETPLACE_NAME!r} marketplace"
        )
    if not isinstance(payload.get("plugins"), list):
        raise ValueError(f"{path.relative_to(ROOT)} field 'plugins' must be an array")
    return payload


def ensure_available(catalog: dict[str, Any], name: str, path: Path) -> None:
    for entry in catalog["plugins"]:
        if isinstance(entry, dict) and entry.get("name") == name:
            raise ValueError(f"plugin {name!r} is already listed in {path.relative_to(ROOT)}")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def skill_markdown(name: str, description: str) -> str:
    title = display_name(name)
    yaml_description = json.dumps(description, ensure_ascii=False)
    return f"""---
name: {name}
description: {yaml_description}
---

# {title}

Use this skill when the request matches this purpose: {description}

## Workflow

1. Identify the inputs and constraints that matter for the request.
2. Complete the requested work using the resources bundled with this skill.
3. Verify the result in proportion to its risk before responding.

## Output

Lead with the outcome and include only the evidence or follow-up steps the user needs.
"""


def plugin_readme(name: str, description: str) -> str:
    title = display_name(name)
    return f"""# {title}

{description}

The shared skill instructions are in `skills/{name}/SKILL.md`.

## Development

Run the marketplace validator from the repository root after changes:

```bash
uv run --locked scripts/validate.py
```
"""


def add_skill(plugin: str, name: str, description: str) -> Path:
    plugin_root = PLUGINS_ROOT / plugin
    has_claude_manifest = (plugin_root / ".claude-plugin" / "plugin.json").is_file()
    has_codex_manifest = (plugin_root / ".codex-plugin" / "plugin.json").is_file()
    if not (has_claude_manifest and has_codex_manifest):
        raise FileNotFoundError(f"plugin does not exist: {plugin_root.relative_to(PLUGINS_ROOT.parent)}")
    skill_root = plugin_root / "skills" / name
    if skill_root.exists():
        raise FileExistsError(f"skill directory already exists: {skill_root.relative_to(PLUGINS_ROOT.parent)}")
    skill_root.mkdir(parents=True)
    skill_path = skill_root / "SKILL.md"
    skill_path.write_text(skill_markdown(name, description), encoding="utf-8")
    return skill_path


def main() -> None:
    args = parse_args()
    name = normalize_name(args.name)
    description = args.description.strip()
    category = args.category.strip()
    if not description:
        raise ValueError("description must not be empty")
    if args.plugin:
        plugin_name = normalize_name(args.plugin)
        skill_path = add_skill(plugin_name, name, description)
        if name != args.name:
            print(f"Normalized skill name to {name!r}.")
        print(f"Edit: {skill_path.relative_to(ROOT)}")
        print("Do not bump the version: CI labels the PR release:minor and bumps on merge.")
        print("Validate: uv run --locked scripts/validate.py")
        return
    if not category:
        raise ValueError("category must not be empty")
    if SEMVER_RE.fullmatch(args.version) is None:
        raise ValueError("version must be valid semantic versioning, such as 0.1.0")

    plugin_root = PLUGINS_ROOT / name
    if plugin_root.exists():
        raise FileExistsError(f"plugin directory already exists: {plugin_root.relative_to(ROOT)}")

    claude_catalog = read_catalog(CLAUDE_MARKETPLACE)
    codex_catalog = read_catalog(CODEX_MARKETPLACE)
    ensure_available(claude_catalog, name, CLAUDE_MARKETPLACE)
    ensure_available(codex_catalog, name, CODEX_MARKETPLACE)

    title = display_name(name)
    claude_manifest = {
        "$schema": "https://json.schemastore.org/claude-code-plugin-manifest.json",
        "name": name,
        "displayName": title,
        "version": args.version,
        "description": description,
        "author": {"name": AUTHOR_NAME},
        "repository": REPOSITORY_URL,
        "skills": "./skills/",
    }
    codex_manifest = {
        "name": name,
        "version": args.version,
        "description": description,
        "author": {
            "name": AUTHOR_NAME,
            "url": "https://github.com/cblack34",
        },
        "repository": REPOSITORY_URL,
        "keywords": ["agent-skill"],
        "skills": "./skills/",
        "interface": {
            "displayName": title,
            "shortDescription": description,
            "longDescription": description,
            "developerName": AUTHOR_NAME,
            "category": category,
            "capabilities": [],
            "defaultPrompt": [f"Help me use {title}."],
        },
    }

    claude_catalog["plugins"].append(
        {
            "name": name,
            "source": f"./plugins/{name}",
            "description": description,
            "category": category,
            "tags": ["skill"],
        }
    )
    codex_catalog["plugins"].append(
        {
            "name": name,
            "source": {"source": "local", "path": f"./plugins/{name}"},
            "policy": {
                "installation": "AVAILABLE",
                "authentication": "ON_INSTALL",
            },
            "category": category,
        }
    )

    skill_root = plugin_root / "skills" / name
    skill_root.mkdir(parents=True)
    write_json(plugin_root / ".claude-plugin" / "plugin.json", claude_manifest)
    write_json(plugin_root / ".codex-plugin" / "plugin.json", codex_manifest)
    (skill_root / "SKILL.md").write_text(
        skill_markdown(name, description), encoding="utf-8"
    )
    (plugin_root / "README.md").write_text(
        plugin_readme(name, description), encoding="utf-8"
    )
    write_json(CLAUDE_MARKETPLACE, claude_catalog)
    write_json(CODEX_MARKETPLACE, codex_catalog)

    if name != args.name:
        print(f"Normalized skill name to {name!r}.")
    print(f"Created plugin: {plugin_root.relative_to(ROOT)}")
    print(f"Edit: {(skill_root / 'SKILL.md').relative_to(ROOT)}")
    print("Validate: uv run --locked scripts/validate.py")


if __name__ == "__main__":
    main()
