# Evidence ledger

Every consequential claim this knowledge set makes, with its source, evidence
class and next step. Unless a row says otherwise, all observations were made on
2026-09-15 against `8974a146fe9eb3ec69234a0169795b184cb0cb05` (`8974a14`) with
Herdr 0.8.2 and Python 3.12.3 locally.

Classes: **observed** (read or executed directly), **accepted** (asserted in the
repository and consistent with code, not executed here), **proposed** (not
implemented), **historical** (about a past measurement or capture), **unknown**.
Nothing in this document has been promoted to policy, and no contradiction listed
below has been fixed.

## Method and limits

Read-only throughout: file reads, `git log`/`show`/`status`, the unit suite, hash
comparison of committed fonts, and read-only inspection of the local
installation (config, backup record, plugin state directory, process list). No
`install`/`doctor`/`uninstall` was executed, not even `--dry-run`, because this
shell runs inside the user's live Herdr session; no Herdr server command was
issued; `HERDR_ENV` was never spoofed. Not covered: macOS rendering, Python 3.11
runtime behaviour, multi-agent performance, and anything that only a live
rendered sidebar can show.

## Ledger

| ID | Claim | Source | Class | Confidence | Next step |
| --- | --- | --- | --- | --- | --- |
| E1 | Only changed `hs_*` keys are published per pane and workspace; `hs_title` and other plugins' tokens are never written | `sidebar.py:246-268`, `tests/test_runtime.py:29-36` | observed | high | none |
| E2 | The shipped layout consumes every published token except `hs_logo_focus` and `hs_workspace_rank` | `sidebar-layout.toml`, `sidebar.py:152-239` | observed | high | confirm the rendered focused row in an isolated session |
| E3 | The focused-row token was never added to the layout; all three focus commits touched only `sidebar.py` | `git show --stat ab9b806 c7f5097 4352afa`; `git log -S hs_logo_focus -- sidebar-layout.toml` (empty) | observed | high | owner decision on C1 |
| E4 | Herdr 0.8.2 is installed and the manifest requires `0.8.2+` | `herdr --version`; `herdr-plugin.toml:4` | observed | high | none |
| E5 | Both committed fonts are byte-reproducible from tracked sources | `sha256sum dist/*.ttf` vs a rebuild in the pinned fontTools env; `tests/test_font.py:72-84`; CI `git diff --exit-code -- dist/` | observed | high | none |
| E6 | Animation runs at 8 fps, patches only `hs_working`/`hs_working_dim`, and costs one registry lookup plus one metadata call per cached pane per frame | `animation.py:5-42`, `deadline.py:53-70`, `tests/test_animation.py` | observed | high | re-measure cost at 8 fps (C11) |
| E7 | The installer backs up before writing and refuses to overwrite files edited since installation | `setup_sidebar.py:95-150`, `docs/setup.md#manual-removal` | observed | high | exercise install/doctor/uninstall in a scratch config root |
| E8 | The live install record's config hash differs from the current Herdr config, so install and uninstall would refuse today | `~/.config/herdr/herdr-sidebar-setup/install.json` vs `sha256` of `~/.config/herdr/config.toml` | observed | high | reconcile, then re-run install and doctor (C2) |
| E9 | `test_activity_titles` covers title precedence, but no test covers `refresh()`, `ipc.call`, `deadline.run`, the popup or focused rows | test inventory | observed | high | add a scratch harness stubbing `run_herdr`/`ipc.call` around `refresh()` |
| E10 | The README settings table omits `pane_names` and no user document names `inactive_after_seconds` | `README.md:70-77` vs `settings_ui.py:8-14`, `preferences.py:10-12`, `docs/setup.md:9-11` | observed | high | patch the table (C5) |
| E11 | `docs/architecture.md` documents the icon range as U+E1A0–U+E1A8 while ten marks ship through U+E1A9 | `docs/architecture.md:131` vs `runtime.py:13-15`, `font/codepoints.toml`, `docs/setup.md:97` | observed | high | one-line correction (C3) |
| E12 | Pi is a title source with no icon or text label, so Pi rows fall back to the generic mark | `activity_titles.py:167` vs `runtime.py:13-17` | observed | high | check the id Herdr reports for Pi, then add a mark or document the fallback |
| E13 | macOS live rendering has never been verified; CI runs unit tests only | `README.md:41-42`, `docs/architecture.md:161`, `.github/workflows/checks.yml` | historical | high | run install, doctor and a capture on macOS |
| E14 | The performance table is an explicitly historical 4 fps baseline, not a measurement of the current styles | `docs/architecture.md:107-123` with `animation.py:10` | historical | high | re-measure or date-qualify the table (C11) |
| E15 | Providers are matched by Herdr's agent id and the mapping to those canonical ids is asserted nowhere | `runtime.py:13-17`; installed binary mentions `opencode` and `open_code` | unknown | medium | dump `herdr api snapshot` for each provider in an isolated session |

## Contradictions

Recorded, not fixed. Each one names the evidence and the resolution I would
propose if asked.

**C1 — The focused-row token has no consumer.** `sidebar.py:152,186-189` gives a
focused pane `hs_logo_focus` and leaves `hs_logo` empty, but
`sidebar-layout.toml` references `$hs_logo` in all four row sets and never
`$hs_logo_focus`; `git log -S hs_logo_focus -- sidebar-layout.toml` is empty and
the three focus commits (`ab9b806`, `c7f5097`, `4352afa`) changed only
`sidebar.py`. Consequence, in the code's own terms: on a fresh install the
focused agent row loses its indentation, branch glyph and provider mark; the
effect on the rendered row is inferred, not observed. The local installation's
config declares `$hs_logo_focus` four times, so its layout differs from the
repository file by exactly that token — and `doctor`'s `layout_matches` compares
against the repository file. *Proposed:* add
`{ token = "$hs_logo_focus", fg = "<provider accent>", dim = false }` after each
`$hs_logo` entry in the four row sets (mirroring the local installation), decide
whether a dim twin is needed (see C4), add a test that focused rows keep a
prefix, and re-run doctor on a reconciled config. Owner decision.

**C2 — The change guard is currently tripped on this machine.** The recorded
`installed_sha256` for `~/.config/herdr/config.toml` does not match the file's
current hash, so `edited_files` (`setup_sidebar.py:147-150`) would make both
install and uninstall fail with "Files changed since setup" (exit 1). The
difference is consistent with the C1 edit being applied to the live config after
installation. `--dry-run` returns before the guard, so it reports success anyway.
*Proposed:* reconcile deliberately — keep the edit and use the manual steps, or
restore `before` from the backup record and re-run setup — then confirm with
`doctor`.

**C3 — Stale codepoint range in the architecture guide.**
`docs/architecture.md:131` says the bundled font covers U+E1A0–U+E1A8; the code,
`font/codepoints.toml`, the setup guide and the Ghostty migration all use ten
marks through U+E1A9. *Proposed:* correct the line and mention AGY.

**C4 — The focus token also escapes dimming and clearing.** The dim/clear loop
(`sidebar.py:199-203`) covers group, tab, logo and the five status tokens;
`hs_logo_focus` has no `_dim` twin and is never cleared, so a focused row inside
a quiet workspace keeps a bright prefix while its heading and status text dim.
Class: observed code, inferred effect; no test sets `focused`. *Proposed:* handle
it in the same change as C1.

**C5 — Preferences documentation gaps.** The README settings table omits
`pane_names` (exposed by the popup at `settings_ui.py:14` and documented only in
the setup guide), and no user-facing document names the
`inactive_after_seconds` key even though the popup writes it and shows minutes
while storing seconds. *Proposed:* add the `pane_names` row, and name the key
once in the setup guide.

**C6 — README wording on dimmed status colors.** README's AGY bullet reads
"Inactive rows still dim; blocked and done retain status colors"; in the dim
state the layout paints `hs_blocked_dim` and `hs_done_dim` neutral gray, so the
colors are retained only while the workspace is active. *Proposed:* scope the
sentence to active workspaces.

**C7 — Tracked but unreferenced capture.** `docs/sidebar.png` (572×308, added
2026-09-07) is linked from no document; the README uses the later
`sidebar-before.png` / `sidebar-after.png` pair. *Proposed:* reference it from
the demo provenance note or remove it.

**C8 — Version drift across artifacts.** The manifest says `0.3.0`, the font
sources say `1.2.0`, and the shipped font's name IDs say `1.0.0`; no document
explains the scheme. *Proposed:* document the three version axes, or align them.

**C9 — Dead backup field.** `created_link` is written on first install
(`setup_sidebar.py:110`) and read nowhere. *Proposed:* remove it or use it during
removal to decide whether the registration should be dropped.

**C10 — Manual installation produces no workspace dimming.** The manual steps
tell users to merge `sidebar-layout.toml`, but the Spaces rows that carry
`$hs_space`/`$hs_space_dim` are generated in code and are not in that file, so a
manual installer silently loses the Spaces half of dimming. *Proposed:* add the
generated Spaces fragment to the manual steps.

**C11 — The only cost table describes the previous frame rate.**
`docs/architecture.md:107-123` labels itself a "historical four-fps animation
baseline" while the code runs at 8 fps. *Proposed:* re-measure with the same
method and publish the new numbers, or date-qualify the table in the README too.

**C12 — Text mode falls back to a symbol for unmapped agents.** README says
providers use short text labels; an agent outside the ten mapped ids renders `◇`
in both modes. *Proposed:* state the mapped set.

**C13 — Governance gaps in the artwork pipeline.** `assets/licenses/MIT.txt`
carries no copyright line for the four MIT marks it appears to cover;
`assets/svg/claude.svg` is pinned to a moving branch rather than a commit;
`assets/svg/agy.svg` has no inline provenance comment; and the installed TTF
ships without `THIRD_PARTY_NOTICES.md` or `assets/licenses/`, so the redistributed
binary's only attribution is a name-table pointer to files the user may not have.
*Proposed:* per-source license files, commit pins, and a notice copy step in
`plan()` with a doctor check.

**C14 — Python 3.11 is required but never executed locally.** The requirement is
declared by the README, AGENTS.md and the setup guide, and CI covers it, but both
local interpreters are 3.12.3. *Proposed:* run the suite once under a 3.11
interpreter and record the result.

## Unknowns

| ID | Unknown | Next verification step |
| --- | --- | --- |
| U1 | Does Herdr render a token whose name appears in no row? What does the focused row actually show? | In an isolated session with a separate config root, focus an agent pane and read the row; then compare with a layout amended per C1 |
| U2 | Do the ten map keys equal Herdr's canonical agent ids (notably `opencode` vs `open_code`)? | Dump `herdr api snapshot` for each provider type in an isolated session |
| U3 | How does Herdr join several populated tokens in one row, and do empty tokens emit separators? | Compare a rendered row with the tokens reported for it |
| U4 | Is `dim = true` realized as SGR faint or as a substituted color, and is it legible on dark themes? | Capture the bytes Herdr emits for a dim row |
| U5 | What is the contrast of each palette color against the user's theme? | Sample foreground/background pixels from a live capture and compute contrast per theme |
| U6 | Are braille cells (loaders, the U+2800 spacer) rendered one column wide in the user's font? | Measure the rendered advance of `⠏` and U+2800 in the terminal font |
| U7 | macOS live rendering and font loading | Run install, doctor and a capture on a Mac |
| U8 | Does `rows_by_agent` accept provider keys beyond the three shipped ones, and how are unknown keys treated? | Test one extra key such as `opencode` live |
| U9 | Does a `min_herdr_version` of 0.8.2 actually block older binaries? | Link the plugin against an older Herdr in a sandbox |
| U10 | Does the current 8 fps animation cost scale with working rows? | Re-measure with several working agents using the documented method |
| U11 | What produced the demo captures (harness, session log)? | Reproduce the demo session and compare, or record the harness |
| U12 | Do preferences really survive uninstall and reinstall? | Isolated install, edit preferences, uninstall, reinstall, diff |
| U13 | Is the checked-in `dist/HerdrHarnessLogos-Regular.ttf` still wanted, given it is only the sidebar font's build input? | Owner decision |
| U14 | Does the backup record's refusal path behave as documented on a real interrupted setup? | Interrupt a scratch install deliberately and follow the recovery steps |

## Adjacent inconsistencies recorded but not fixed

Beyond the contradictions above: the plugin is named "Herdr Sidebar Config" in
the manifest and "Herdr Agent Sidebar" in the README; `dist/` ships two fonts
where setup installs one; `font/codepoints.toml` still carries the older family
name because the shipped font is renamed at build time; the preference validation
message mixes units ("a positive number of minutes" for a key measured in
seconds); and the README's install size claim and hooks count are not stated
anywhere, so no numeric comparison is available. None of these were changed.
