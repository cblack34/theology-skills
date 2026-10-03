import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ci_bump_versions import level_from_labels, resolve_base, select_plugins  # noqa: E402


class LevelFromLabelsTests(unittest.TestCase):
    def test_no_release_label_is_patch(self) -> None:
        self.assertEqual(level_from_labels([]), "patch")
        self.assertEqual(level_from_labels(["bug", "documentation"]), "patch")

    def test_minor_and_major(self) -> None:
        self.assertEqual(level_from_labels(["release:minor"]), "minor")
        self.assertEqual(level_from_labels(["release:major"]), "major")

    def test_highest_label_wins(self) -> None:
        self.assertEqual(level_from_labels(["release:minor", "release:major"]), "major")


class ResolveBaseTests(unittest.TestCase):
    def test_all_zero_before_falls_back_to_parent(self) -> None:
        self.assertEqual(resolve_base("0" * 40, "abc123"), "abc123~1")

    def test_real_before_is_kept(self) -> None:
        self.assertEqual(resolve_base("def456", "abc123"), "def456")


class SelectPluginsTests(unittest.TestCase):
    def test_multiple_plugins_sorted(self) -> None:
        paths = ["plugins/pr-review/skills/x/SKILL.md", "plugins/build-pack/README.md", "AGENTS.md"]
        self.assertEqual(select_plugins(paths), ["build-pack", "pr-review"])

    def test_manifest_only_change_is_bumped(self) -> None:
        paths = ["plugins/build-pack/.claude-plugin/plugin.json", "plugins/build-pack/.codex-plugin/plugin.json"]
        self.assertEqual(select_plugins(paths), ["build-pack"])

    def test_new_plugin_is_skipped(self) -> None:
        paths = ["plugins/fresh/skills/a/SKILL.md", "plugins/build-pack/README.md"]
        self.assertEqual(select_plugins(paths, new_plugins={"fresh"}), ["build-pack"])

    def test_non_plugin_paths_are_ignored(self) -> None:
        self.assertEqual(select_plugins(["plugins/.gitkeep", "scripts/validate.py"]), [])


if __name__ == "__main__":
    unittest.main()
