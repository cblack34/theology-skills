# Marketplace maintenance

These instructions apply to the entire repository.

## Source of truth

- Keep reusable instructions in `plugins/<plugin>/skills/<skill>/SKILL.md`.
- Keep shared workflow instructions in `SKILL.md`. Keep plugin-level harness metadata in `.claude-plugin/` and `.codex-plugin/`; use skill-local `agents/openai.yaml` only for Codex UI or invocation policy that has no portable equivalent.
- Group only closely related skills in the same plugin. Use separate plugins when skills should be installed or versioned independently.
- Keep every runtime dependency inside its plugin directory. Installed plugins cannot safely reference sibling directories.

## Adding a skill

- Run `uv run --locked scripts/new_skill.py <name> --description <description>` from the repository root to create a new plugin with its first skill.
- Add `--plugin <existing-plugin>` to add a skill to an existing plugin instead; this writes only the skill's `SKILL.md`, so update the plugin README yourself.
- Use lowercase kebab-case names no longer than 64 characters.
- Before creating a skill inside an existing plugin, confirm that placement with the user.
- Keep the plugin folder name and both plugin manifest names identical. Keep each skill folder name identical to its `SKILL.md` frontmatter name. Skill names need not match the plugin name; renaming a plugin forces users to reinstall it, so name plugins for their whole purpose and rename skills freely.
- Do not hand-edit only one marketplace catalog. The Claude and Codex catalogs must contain the same plugin names in the same order.
- Do not leave placeholder instructions in a published skill.

## Changing a skill

- Preserve cross-harness behavior in the shared `SKILL.md`; isolate unavoidable harness differences in clearly labeled sections.
- Do not bump plugin versions in a PR. CI bumps both manifests of every changed plugin when the PR squash-merges to `main`. The level comes from the PR's labels: `release:major`, `release:minor`, or patch when neither is present. CI adds `release:minor` when a PR adds a skill to an existing plugin and `release:major` when it removes or renames a skill; it never removes a label. A new or renamed plugin ships at the version its manifest declares. `scripts/bump_plugin_version.py` remains for local dry runs.
- Change one plugin per PR. Release labels apply to the whole PR, so a PR touching two plugins bumps both to the same level.
- Do not add secrets, credentials, machine-specific absolute paths, or private source material.
- Prefer deterministic helper scripts for mechanical work and keep them inside the owning skill.

## Verification

- Manage Python and Python dependencies with `uv`; do not introduce `pip`, Poetry, or ad hoc virtual-environment instructions.
- Run `uv lock --check`, `uv run --locked scripts/validate.py`, and `uv run --locked python -m unittest discover -s tests` after every marketplace, plugin, or script change.
- If Claude Code is installed, also run `claude plugin validate .`.
- If Grok is installed, run `grok plugin validate plugins/<plugin>` for each changed plugin.
- Review `git diff --check` before committing.
