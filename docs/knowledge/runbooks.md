# Runbooks and authority boundaries

Operational procedures for this repository, plus the limits on what may be done
without asking a human. Facts referenced here live in [system.md](system.md);
open questions live in [evidence.md](evidence.md).

## Authority boundaries

**An agent may do without asking**

- Read anything in the checkout, run `git log`/`show`/`status`, and read the
  installed Herdr and Ghostty configs read-only.
- Run the test suite and `python3 tools/check_knowledge_docs.py`.
- Run `python3 setup_sidebar.py --help`, and `--dry-run` variants **only** from a
  scratch checkout against a scratch config root (a dry run still requires a live
  Herdr session and contact with its API).
- Rebuild fonts into a temporary directory for inspection.

**Ask a human first**

- Running `install`, `uninstall` or `doctor` against a real user's config. These
  write files, link or disable a plugin, reload the server config and invoke a
  refresh.
- Any change to the shipped layout's tokens or colors, since it changes what
  every user sees.
- Restarting Ghostty or anything that would end a Herdr session.
- Publishing or updating captures in [../demo.md](../demo.md).

**Never**

- Operate a user's working agent panes, or send prompts, keystrokes or stop
  commands to agents. The plugin reads native facts only; the tooling must too.
- Kill a live Herdr server, or spoof `HERDR_ENV=1` to target a session you were
  not invited into.
- Commit local configs, backups, session captures, credentials or personal paths.
- Publish a capture made from a real working session; use demo data and label it.

## Install or update

Run from this checkout, inside the intended Herdr session (`HERDR_ENV=1`):

```sh
python3 setup_sidebar.py install --dry-run --json
python3 setup_sidebar.py install --json
python3 setup_sidebar.py doctor --json
```

`--dry-run` reports planned paths and writes nothing. Setup backs up every file
it changes before writing, preserves unrelated settings, and refuses to run when
the plugin is registered from a different checkout. Updates are the same
procedure: `git pull --ff-only`, then install, then doctor. After writing a font,
a fresh Ghostty process is required before the marks can render — do not kill
Ghostty or restart a live Herdr server on the user's behalf.

Exit codes: 0 success, 1 setup error or a doctor check needing attention, 2
invalid arguments. JSON output carries a `status` field. For another terminal, or
when no font change is wanted, add `--text` to both install commands; custom
paths are `--config`, `--ghostty-config`, `--font-dir`, `--state-dir`, and they
must be repeated for doctor and uninstall.

## Verify a change

```sh
python3 -m unittest discover -s tests -v
python3 tools/check_knowledge_docs.py
python3 -m venv .venv-font && .venv-font/bin/pip install -r requirements-font.txt
.venv-font/bin/python -m unittest discover -s tests -v
```

The first command is the documented, dependency-free check; without fontTools
three font tests skip, so run the venv variant before claiming font work is
verified. Change the knowledge set or the facts it records, then the checker must
pass — it is also `tests/test_knowledge_docs.py`, so CI enforces it. For
runtime, layout or setup changes, continue with a live check.

## Live verification

Use a **separate Herdr session and a separate config root**. A named session alone
still shares the user's configuration. Exercise, in order:

1. `install --dry-run --json` (planned file list, no writes).
2. `install --json`, then `doctor --json` (exit 0, every check OK).
3. A second tab in the demo workspace, to force the multi-tab tree, and one
   workspace with no agents.
4. Focus transitions and, if animation is part of the change, one full frame
   cycle with the loader on and off.
5. `uninstall --dry-run --json`, then `uninstall --json`, then confirm the
   restored files and that the checkout is still linked but disabled.

Record the exit codes and the doctor `checks` object verbatim in the change
report. Doctor cannot see which fonts a terminal process actually loaded, so
font rendering still needs a human look.

## Doctor and troubleshooting

Doctor verifies plugin registration, layout equality, workspace sorting, the
latest hook result and the preferences file; in font mode it also checks the
installed font bytes and the Ghostty mapping line. When a check fails, the
symptom table in [../setup.md](../setup.md#troubleshooting) maps the common cases
(empty squares, blank rows, stale labels, flat tabs, failed hooks) to the right
next read, and `herdr plugin log list --plugin testy-cool.herdr-sidebar --limit 5`
shows the hook's stderr.

## Removal

```sh
python3 setup_sidebar.py uninstall --dry-run --json
python3 setup_sidebar.py uninstall --json
```

Automatic removal restores each backed-up file (deleting files setup created),
clears this plugin's tokens, disables the registration, reloads the config and
retains both the checkout and the preferences. If a managed file changed after
installation, setup refuses and the manual steps in
[../setup.md](../setup.md#manual-removal) apply; the original bytes are in the
backup record.

## Recovering from an interrupted or refused setup

The record at `~/.config/herdr/herdr-sidebar-setup/install.json` maps each
managed path to its original bytes (`before`, base64 or null) and the hash of
what setup wrote (`installed_sha256`). An interrupted setup leaves that record in
place so the files can be restored by hand.

When install or uninstall refuses with "Files changed since setup", the guard
found bytes that no longer match the record — typically a user's own edit to the
Herdr config. Resolve it deliberately: keep the edit and follow the manual steps,
or restore the file from `before` and re-run setup. Note that `--dry-run` returns
before the guard, so it will not reveal this state; only a real run or a hash
comparison does. This is exactly the state of the local installation as observed
on 2026-09-15 — see contradiction C2 in [evidence.md](evidence.md#contradictions)
for the evidence and the proposed reconciliation.

## Unresolved operational ownership

- Release and publishing ownership is unrecorded: no changelog, tag or release
  procedure exists in the repository, and the plugin manifest version is not
  mentioned by any document.
- macOS live verification has no owner or schedule; the repository only states
  that it has not been done ([evidence.md](evidence.md#unknowns) U7).
- Performance numbers for the current 8 fps loaders have no owner
  ([evidence.md](evidence.md#unknowns) U6).
