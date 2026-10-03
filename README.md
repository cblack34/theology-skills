# theology-skills

A domain marketplace for theology plugins. Not a coding toolkit, not a sermon generator, and not a substitute for the text.

Adding this marketplace installs nothing. Install a plugin by name after the catalog is registered.

```text
/plugin marketplace add cblack34/theology-skills
/plugin install scripture-exegesis@theology-skills
```

## Plugins

| Plugin | What it does |
|---|---|
| `scripture-exegesis` | Arbitrates a passage from the Greek or Hebrew text, in the argument of the book, and labels inference. |

The marketplace can grow. A new method ships as its own plugin, not as another skill stuffed into `scripture-exegesis`.

## What this is not

- Not a developer tool. Do not add it to a coding marketplace.
- Not a commentary dump. Working commentaries for a particular study stay in that study's notes.
- Not a claim that the agent is a substitute for the text or for peer-reviewed work on the original languages.

## Development

Python tooling is managed with [uv](https://docs.astral.sh/uv/getting-started/installation/). From the repository root:

```bash
uv lock --check
uv run --locked scripts/validate.py
uv run --locked python -m unittest discover -s tests
claude plugin validate .
```

Do not bump plugin versions in a pull request. CI bumps both manifests of every changed plugin when the PR merges to `main`: patch by default, `release:minor` or `release:major` by label. `AGENTS.md` has the full maintenance rules, including how to add a plugin with `scripts/new_skill.py`.
