import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import new_skill  # noqa: E402
import validate  # noqa: E402


def errors_for(frontmatter: str, expected_name: str | None = "demo") -> list[str]:
    check = validate.Validation()
    validate.validate_frontmatter(
        Path("SKILL.md"), f"---\n{frontmatter}\n---\n\nbody\n", expected_name, check
    )
    return check.errors


class RejectedFrontmatterTests(unittest.TestCase):
    def assert_rejected(self, frontmatter: str, fragment: str) -> None:
        errors = errors_for(frontmatter)
        self.assertTrue(any(fragment in error for error in errors), errors)

    def test_null_description(self) -> None:
        self.assert_rejected("name: demo\ndescription: null", "description must be")

    def test_boolean_description(self) -> None:
        self.assert_rejected("name: demo\ndescription: false", "description must be")

    def test_number_name(self) -> None:
        self.assert_rejected("name: 123\ndescription: ok", "name must be")

    def test_empty_block_scalar_description(self) -> None:
        self.assert_rejected("name: demo\ndescription: |\n", "description must be")

    def test_blank_description(self) -> None:
        self.assert_rejected('name: demo\ndescription: "   "', "description must be")

    def test_missing_description(self) -> None:
        self.assert_rejected("name: demo", "description must be")

    def test_missing_name(self) -> None:
        self.assert_rejected("description: ok", "name must be")

    def test_malformed_yaml_elsewhere(self) -> None:
        self.assert_rejected("name: demo\ndescription: ok\nextra: [", "not valid YAML")

    def test_plain_scalar_with_colon(self) -> None:
        self.assert_rejected("name: demo\ndescription: ok: nope", "not valid YAML")

    def test_duplicate_name(self) -> None:
        self.assert_rejected("name: demo\nname: demo\ndescription: ok", "duplicate key")

    def test_duplicate_description(self) -> None:
        self.assert_rejected("name: demo\ndescription: a\ndescription: b", "duplicate key")

    def test_unhashable_key(self) -> None:
        self.assert_rejected("? [a, b]\n: 1\nname: demo\ndescription: ok", "unhashable mapping key")

    def test_non_mapping(self) -> None:
        self.assert_rejected("- name\n- description", "must be a YAML mapping")

    def test_empty_frontmatter(self) -> None:
        self.assert_rejected("", "must be a YAML mapping")

    def test_name_directory_mismatch(self) -> None:
        self.assert_rejected("name: other\ndescription: ok", "name must be 'demo'")

    def test_unclosed_frontmatter(self) -> None:
        check = validate.Validation()
        validate.validate_frontmatter(Path("SKILL.md"), "---\nname: demo\n", "demo", check)
        self.assertEqual(len(check.errors), 1)
        self.assertIn("closed YAML frontmatter", check.errors[0])


class AcceptedFrontmatterTests(unittest.TestCase):
    def test_generator_output(self) -> None:
        descriptions = [
            "Does a thing.",
            'Quotes "inside", a colon: here, and a # hash.',
            "Unicode — café ✓ and 'single quotes'.",
            "Backslash \\ and a trailing space ",
        ]
        for description in descriptions:
            with self.subTest(description=description):
                check = validate.Validation()
                validate.validate_frontmatter(
                    Path("SKILL.md"), new_skill.skill_markdown("demo", description), "demo", check
                )
                self.assertEqual(check.errors, [])

    def test_block_scalar_description(self) -> None:
        self.assertEqual(errors_for("name: demo\ndescription: >\n  folded\n  text"), [])

    def test_extra_keys_and_lists(self) -> None:
        self.assertEqual(
            errors_for("name: demo\ndescription: ok\nmodel: sonnet\nmaxTurns: 12\nskills:\n  - a"),
            [],
        )

    def test_name_not_checked_without_expected_name(self) -> None:
        self.assertEqual(errors_for("name: anything\ndescription: ok", None), [])


class AgentFrontmatterTests(unittest.TestCase):
    def validate_with_agent(self, agent_text: str) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            plugins = Path(directory) / "plugins"
            plugin = plugins / "demo"
            skill = plugin / "skills" / "demo"
            (plugin / "agents").mkdir(parents=True)
            skill.mkdir(parents=True)
            (plugin / "agents" / "helper.md").write_text(agent_text, encoding="utf-8")
            skill.joinpath("SKILL.md").write_text(
                new_skill.skill_markdown("demo", "Does a thing."), encoding="utf-8"
            )
            manifest = {
                "name": "demo",
                "version": "1.0.0",
                "description": "d",
                "skills": "./skills/",
            }
            interface = {
                "displayName": "d",
                "shortDescription": "d",
                "longDescription": "d",
                "developerName": "d",
                "category": "d",
                "capabilities": [],
                "defaultPrompt": ["p"],
            }
            for folder, extra in ((".claude-plugin", {}), (".codex-plugin", {"interface": interface})):
                (plugin / folder).mkdir()
                (plugin / folder / "plugin.json").write_text(
                    json.dumps({**manifest, **extra}), encoding="utf-8"
                )
            check = validate.Validation()
            with patch.object(validate, "PLUGINS_ROOT", plugins):
                validate.validate_plugin("demo", check)
            return check.errors

    def test_valid_agent_passes(self) -> None:
        self.assertEqual(self.validate_with_agent("---\nname: helper\ndescription: ok\n---\n"), [])

    def test_broken_agent_is_rejected(self) -> None:
        errors = self.validate_with_agent("---\nname: helper\ndescription: null\n---\n")
        self.assertTrue(any("helper.md" in e and "description must be" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
