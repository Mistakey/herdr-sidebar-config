# Project knowledge: start here

This directory is the entry point for anyone (human or agent) who has to work on
this repository without re-deriving how it works. It states where truth lives,
what has been verified, what is still unknown, and how to re-check the parts
that drift.

Everything here describes the repository at
`8974a146fe9eb3ec69234a0169795b184cb0cb05` (short `8974a14`), inspected on
2026-09-15, plus read-only observations of the local Herdr installation on the
same day. Treat the code as current and these documents as a dated snapshot.

## Reading order

1. [AGENTS.md](../../AGENTS.md) — repository instructions and the contracts a
   change must preserve.
2. [system.md](system.md) — the dated current-system view: modules, data flow,
   token contract, preferences, providers, environment.
3. [runbooks.md](runbooks.md) — operations and the boundaries on what an agent
   may do without asking.
4. [evidence.md](evidence.md) — the evidence ledger, recorded contradictions,
   and the numbered unknowns with their next verification step. Read this before
   making a claim about behaviour that the tests do not cover.
5. [../architecture.md](../architecture.md) and [../setup.md](../setup.md) — the
   maintained developer and operator documents; [../demo.md](../demo.md) owns the
   provenance of the published captures.
6. [registry.json](registry.json) — the machine-readable form of the facts in
   `system.md`. Query it instead of re-deriving counts, defaults, codepoints or
   hashes; `tools/check_knowledge_docs.py` holds it against the code.

## Authority

When two sources disagree, resolve in this order rather than averaging them.

| Authority | Artifacts | Rule |
| --- | --- | --- |
| Live or generated truth | Herdr's own snapshot, the plugin state directory (`activity.json`, `view.json`, `deadline.lock`, `deadline.log`), the installed Herdr and Ghostty configs | Never hand-edit generated state; re-read it. Live state describes one machine, not the repository. |
| Accepted decisions | [AGENTS.md](../../AGENTS.md) contracts, the shipped `sidebar-layout.toml`, `herdr-plugin.toml` | Change only in a reviewed commit that keeps the contracts intact. |
| Canonical facts | The runtime modules, `preferences.DEFAULTS`, the token contract, the committed fonts, and [registry.json](registry.json) as their machine-readable mirror | Code wins over prose. A prose statement that the code contradicts is a defect in the prose. |
| Research evidence | [evidence.md](evidence.md) | Carries an evidence class; `proposed` items are not policy. |
| Historical | [../demo.md](../demo.md) capture provenance, the animation cost table in [../architecture.md](../architecture.md#animation-cost) | Dated observations. Never cite them as current behaviour. |
| Prototypes, archives | none in this repository | — |

## Drift-sensitive facts and how to re-check them

These are the facts most likely to be wrong later. Revalidate before relying on
them in a decision.

| Fact | Why it drifts | How to revalidate |
| --- | --- | --- |
| Installed layout equals the repository layout | The installer's change guard compares hashes, and users edit their own config | `python3 setup_sidebar.py doctor --json` inside the session, or compare the parsed `[ui.sidebar.agents]` table |
| Backup record versus the live config | Any edit after installation trips `edited_files` | compare `~/.config/herdr/herdr-sidebar-setup/install.json` hashes with the current files (see [evidence.md](evidence.md), contradiction C2) |
| Provider ids reported by Herdr | The icon map keys must equal Herdr's canonical agent ids | read `herdr api snapshot` in an isolated session, or the agent list of the installed Herdr version |
| Herdr minimum-version behaviour | `min_herdr_version` is asserted, not enforced by any test in this repository | link the plugin against an older Herdr binary in a sandbox |
| Anything about rendering: focused rows, token joining, dim realization, color contrast, braille cell width | These depend on Herdr and on the user's terminal, not on this repository | probe a live sidebar and read the bytes; see [evidence.md](evidence.md#unknowns) unknowns U3 to U6 |
| Python 3.11 compatibility | Local interpreters are 3.12.3; only CI runs 3.11 | run the suite under `uv run --python 3.11` or `docker run python:3.11-slim` |
| Published captures | They predate the last three UI commits | recapture from an isolated demo session and update [../demo.md](../demo.md) |
| Animation cost | The only table is an explicitly historical 4 fps baseline | re-measure with the method in [../architecture.md](../architecture.md#animation-cost) |

## How this set is verified

```sh
python3 tools/check_knowledge_docs.py        # links, anchors, placeholders, registry vs code
python3 -m unittest discover -s tests -v     # the repository suite, including the check above
```

`tools/check_knowledge_docs.py` re-derives the counts, defaults, codepoints,
environment variables, module inventory and font hashes from the code and fails
when [registry.json](registry.json) disagrees. It is wired into the suite as
`tests/test_knowledge_docs.py`, so CI fails on drift instead of on a reviewer's
memory.

## Glossary

| Term | Meaning here |
| --- | --- |
| Herdr | The terminal workspace manager for coding agents; it owns agent detection, lifecycle state and rendering |
| Workspace, tab, pane | Herdr's own nesting; this plugin only publishes display tokens for existing entities |
| Agent row | A sidebar row that belongs to a pane where Herdr detected an agent |
| Spaces / Agents | Herdr's two sidebar panels; this plugin labels the former and builds the tree in the latter |
| Token (`hs_*`) | A display string published per pane or workspace under `plugin:testy-cool.herdr-sidebar` |
| Layout fragment | `sidebar-layout.toml`, merged into the user's Herdr config by setup; it decides which tokens render and in what color |
| Group lock | `<state dir>/group-headers.lock`, the exclusive lock that serializes refreshes and animation frame writes |
| Deadline worker | The single `deadline.py` process that waits on a private Unix datagram socket for the next quiet-period or frame deadline |
| Quiet period | Time without any working agent in a workspace; at the delay (default 600 s) its tokens switch to their dim variants |
| Loader | The optional animated braille mark for working agents, off by default, 8 frames per second |
| PUA | Private use area codepoints U+E1A0–U+E1A9 in the bundled icon font |
