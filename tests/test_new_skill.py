import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import new_skill  # noqa: E402


class AddSkillTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.plugins_root = Path(self.temporary_directory.name) / "plugins"
        claude_manifest = self.plugins_root / "existing" / ".claude-plugin" / "plugin.json"
        codex_manifest = self.plugins_root / "existing" / ".codex-plugin" / "plugin.json"
        claude_manifest.parent.mkdir(parents=True)
        codex_manifest.parent.mkdir(parents=True)
        claude_manifest.write_text("{}", encoding="utf-8")
        codex_manifest.write_text("{}", encoding="utf-8")

    def test_adds_skill_to_existing_plugin(self) -> None:
        with patch.object(new_skill, "PLUGINS_ROOT", self.plugins_root):
            path = new_skill.add_skill("existing", "second-skill", "Does a second thing.")
        self.assertEqual(path, self.plugins_root / "existing" / "skills" / "second-skill" / "SKILL.md")
        self.assertIn("name: second-skill\n", path.read_text(encoding="utf-8"))

    def test_rejects_missing_plugin_and_duplicate_skill(self) -> None:
        with patch.object(new_skill, "PLUGINS_ROOT", self.plugins_root):
            with self.assertRaises(FileNotFoundError):
                new_skill.add_skill("missing", "skill", "x")
            new_skill.add_skill("existing", "dup", "x")
            with self.assertRaises(FileExistsError):
                new_skill.add_skill("existing", "dup", "x")

    def test_rejects_plugin_missing_codex_manifest(self) -> None:
        incomplete_manifest = self.plugins_root / "incomplete" / ".claude-plugin" / "plugin.json"
        incomplete_manifest.parent.mkdir(parents=True)
        incomplete_manifest.write_text("{}", encoding="utf-8")
        with patch.object(new_skill, "PLUGINS_ROOT", self.plugins_root):
            with self.assertRaises(FileNotFoundError):
                new_skill.add_skill("incomplete", "skill", "x")


class MainVersionTests(unittest.TestCase):
    def test_rejects_invalid_version_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plugins_root = root / "plugins"
            catalog = root / "marketplace.json"
            catalog.write_text("{}", encoding="utf-8")
            argv = ["new_skill.py", "demo", "--description", "x", "--version", "1.0.0-01"]
            with (
                patch.object(sys, "argv", argv),
                patch.object(new_skill, "PLUGINS_ROOT", plugins_root),
                patch.object(new_skill, "CLAUDE_MARKETPLACE", catalog),
                patch.object(new_skill, "CODEX_MARKETPLACE", catalog),
            ):
                with self.assertRaisesRegex(ValueError, "semantic versioning"):
                    new_skill.main()
            self.assertFalse(plugins_root.exists())
            self.assertEqual(catalog.read_text(encoding="utf-8"), "{}")


if __name__ == "__main__":
    unittest.main()
