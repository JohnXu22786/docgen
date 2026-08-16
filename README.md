[简体中文](README.zh.md)

# docgen — Document Workshop skill pack

A set of document-generation skills in pure prompt (Agent Skills) form, providing four capabilities for plugin-based agent harnesses such as dsh: **README generation, PR description generation, changelog generation, and code review**. All skills follow the [Agent Skills open standard](https://agentskills.io/specification) (`SKILL.md` + YAML frontmatter), are self-contained, have no third-party dependencies, and work offline.

## Included skills

| Skill | What it does | When to use |
|---|---|---|
| [`readme-forge`](skills/readme-forge/SKILL.md) | Generate/rewrite README.md from a codebase, writing only content backed by evidence | "Write a README for this project" |
| [`pr-dossier`](skills/pr-dossier/SKILL.md) | Generate a complete PR description (change dossier) from a diff and commit history | "Write a PR description for this change" |
| [`changelog-curator`](skills/changelog-curator/SKILL.md) | Categorize, merge, and rewrite git history into a CHANGELOG | "Update the changelog and get ready for release" |
| [`diff-verdict`](skills/diff-verdict/SKILL.md) | Output structured review opinions: verdict + graded issue list + highlights | "Review this PR" |

Each skill is a **self-contained single `SKILL.md`**: the body contains input-collection guidance, a workflow, output templates with a template-variable table, language-style options, an output-quality checklist, a "don't" list, and edge-case handling.

## Directory structure

```
docgen/
├── README.md                     # this document: installation, usage, interface
├── package.json                  # npm manifest: name (dsh-docgen) + dsh.bundle
├── cordis.patch.yml              # bundle patch consumed by `dsh plugin` installs
├── index.js                      # skill-mount adapter (registers skills/ onto ctx.skills)
├── manifest.json                 # plugin manifest (self-describing metadata)
├── SKILLS.md                     # entry index file
├── LICENSE                       # MIT license
├── skills/                       # skills root (point here or copy entries when integrating)
│   ├── readme-forge/SKILL.md
│   ├── pr-dossier/SKILL.md
│   ├── changelog-curator/SKILL.md
│   └── diff-verdict/SKILL.md
├── examples/
│   ├── prompts.md                # example invocation prompts for each skill
│   └── dsh-patch-enable-skills.yml  # example dsh integration patch (enables skills in web profile + registers directory)
├── scripts/
│   └── validate_skills.py        # skill-pack validation script (Python standard library, no dependencies)
└── tests/
    ├── test_validate_skills.py   # regression tests for the validation script
    └── index.test.mjs            # node smoke tests for the skill-mount adapter
```

## Installing in DSH

docgen ships a `dsh.bundle` manifest, so it installs and activates with the plugin
loader:

```bash
dsh plugin --profile demo add github:JohnXu22786/docgen
```

The bundle inserts a plugin row (`id: docgen`, `name: dsh-docgen`) that resolves this
package's entry (`index.js`); its `apply(ctx)` scans the bundled `skills/` directory and
registers every `SKILL.md` onto `ctx.skills` at runtime — no copying, no extra config.
The file-based integration paths below remain available for harnesses or profiles where
the `skills` service or skill components are not loaded.

## Installation and dsh integration

dsh discovers skills through the `skill-filesystem` provider by **skills root directory** (one level deep: directory bundles `<root>/<name>/SKILL.md` or flat files `<root>/<name>.md`). Pick any one of the following ways to integrate this pack:

### Way zero: plugin loader (dsh.bundle, recommended)

```bash
dsh plugin --profile demo add github:JohnXu22786/docgen
```

The bundle's entry (`index.js`) registers the four `skills/` entries onto `ctx.skills`
at load time. This is the one-step path; the ways below are for manual or file-based
integration.

### Way one: project-level (zero config, no plugin loader)

Put the four skill directories under `skills/` (or the whole `skills/`) into the project's skills root:

```bash
# Any of these in the project root (the nearest ancestor containing .git):
#   <project>/.dsh/skills/    or   <project>/.agents/skills/
cp -r skills/* <project>/.dsh/skills/
```

### Way two: user-level (available in all projects)

```bash
# $DSH_HOME defaults to ~/.dsh; $DSH_AGENTS_HOME defaults to ~/.agents
cp -r skills/* ~/.dsh/skills/
```

### Way three: custom directory (in-place integration of the plugin, no copying)

Register `customSkillDirs` for the `skill-filesystem` provider via configuration, e.g. with a patch file (see `examples/dsh-patch-enable-skills.yml`):

```bash
npx @deepseek-ai/dsh web --patch ./examples/dsh-patch-enable-skills.yml
```

> Note: dsh's `web` profile disables skill-related components by default (`skill-filesystem` / `tool-skill`); enable them with a patch or preset. The `headless` profile has them enabled by default. The exact config key paths depend on your installed version — check `dsh --dump-config` and the official docs.

### Verifying the installation

```bash
python scripts/validate_skills.py            # validates this pack's skill format (exit code 0 when all pass)
python scripts/validate_skills.py --strict   # additionally checks the body line-count cap
python -m unittest discover -s tests -t .    # runs the validation script's own regression tests
npm test                                     # runs the skill-mount adapter's node smoke tests
```

After integration, just make natural-language requests in a session and the model loads the matching skill via the `skill` tool:

```
Write a README for this project
Generate a PR description for the change I just made
Update the changelog from git history and prepare 1.2.0
Help me review this PR
```

## Usage

- **Triggering**: describe the need naturally in your prompt (see the "When to use" column of the skill table); you don't need to remember skill names. The harness routes automatically based on `description` / `whenToUse`.
- **Style options**: each skill supports three overridable dimensions — language (defaults to the language of the prompt), length (concise/standard/detailed or full), and tone/depth. Just append them in natural language: `length=concise`, `focus=security`, `language=en`.
- **Output shape**: skills produce markdown text directly; README/changelog-type skills give complete content you can save to a file as-is, while PR/review-type skills give structured descriptions or opinion lists.
- **Example prompts**: see [examples/prompts.md](examples/prompts.md).

## Interface

### Skill interface (dsh native contract)

Each skill is a directory bundle whose `SKILL.md` frontmatter is the only contract the harness reads:

| Field | Required | Constraints | Usage in this pack |
|---|---|---|---|
| `name` | yes | kebab-case (lowercase letters/digits/hyphens), ≤ 64 chars, identical to the containing directory name | see each skill |
| `description` | yes | non-empty, ≤ 1024 chars, states what it does + when to use + trigger keywords | Chinese description + English keywords |
| `whenToUse` | no | string, extra routing hint (community-established camelCase extension field) | provided by every skill |
| `metadata` | no | string key-value map | author / version / family |
| `license` | no | string | MIT |
| `compatibility` | no | string, environment requirements | pure prompts, no network needed |
| `allowed-tools` | no | string, pre-approved tool list (experimental) | unused |

dsh additionally recognizes (not written in this pack, defaults apply): `disable-model-invocation` and `user-invocable` (both open by default). **Note**: field names must be spelled exactly as in the table — `allowed-tools` contains a hyphen, and `whenToUse` is the established camelCase spelling; inconsistent spellings (e.g. writing `allowed_tools` or `when-to-use`) cause the field to be unrecognized; if an invocation-policy field is misspelled or mis-typed, dsh drops the entire skill (fail-closed).

### Plugin manifest and entry

- `package.json` + `cordis.patch.yml`: the `dsh.bundle` manifest consumed by [`dsh plugin add`](https://github.com/deepseek-ai/deepseek-harness). During install, dsh reads `cordis.patch.yml`, inserts the `docgen` plugin row, and loads `index.js` — whose `apply(ctx)` registers the bundled skills onto `ctx.skills` (`name` / `description` / `whenToUse` / `content` / `metadata` / `source: bundled`) and returns a disposer that unregisters them on unload.
- `manifest.json`: the plugin's self-describing metadata (id / version / kind / entry / interface / skills / scripts). dsh's skill discovery does not read it; it serves human reference, publishing flows, and harnesses that support "entry file" style loaders; the `interface` field declares the skill-discovery contract.
- `SKILLS.md`: entry index listing the loading-contract summary and the skill list.

### How dsh loads skills (summary)

dsh's skill capabilities are provided by three plugins working together — `skill` (registry), `skill-filesystem` (local discovery), and `tool-skill` (model catalog and `skill` tool): at startup it scans the root directories' frontmatter to build a catalog (the model only sees `name` + `description`); when the model decides to call a skill it reads the latest body by name; relative references in the body resolve against the skill directory. All four skills in this pack are single-file self-contained and do not depend on relative resources.

## Development and extension

- **Adding a skill**: create a new directory + `SKILL.md` under `skills/` (frontmatter per the table above), run `python scripts/validate_skills.py` until it passes, and update `manifest.json` and `SKILLS.md` accordingly.
- **Modifying a skill**: only edit the corresponding `SKILL.md`; the harness reads the new content on the next load (body changes need no catalog-cache restart).
- **Validation script**: `scripts/validate_skills.py` uses only the Python standard library and can be used standalone on any skill pack; it accepts arbitrary directories/files. Its parsing scope is a flat YAML subset (top-level key-values + `metadata` indented maps + quoted/list literals), without anchors, comments, or other full-YAML features.

## Dependencies and privacy

- Zero third-party dependencies: pure prompts + a Python standard-library script;
- No network requests, no data collection; the only capabilities required are reading codebase files and git history (provided by the harness);
- License: MIT, see [LICENSE](LICENSE).

## FAQ

- **Skills not visible in the web UI?** The dsh web profile disables skill components by default; enable them with the Way-three patch (or use the CLI/headless profile).
- **Changed SKILL.md but no effect?** Skill bodies are read per invocation — just send a new request; if you changed the frontmatter `name`/`description`, the catalog refreshes via filesystem watching.
- **Name collision with an existing skill?** dsh resolves same-name skills by root-directory priority and layer proximity; all skill names in this pack are original — if there is a conflict, first check whether a same-name skill is already installed.

---

## License

MIT — see [LICENSE](LICENSE).
