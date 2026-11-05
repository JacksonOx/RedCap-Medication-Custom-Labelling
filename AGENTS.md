# AGENTS.md — Codex operating contract

## Purpose and scope

Help the user maintain *Custom Labels for Repeating Instruments* for the seven active medication instruments in the PANS2023 REDCap project, **Patient Baseline** event \`patient_baseline_arm_1\`. The active forms are \`meds_abs\`, \`meds_nsaids\`, \`meds_steroids\`, \`meds_dmards\`, \`meds_psych\`, \`meds_misc\`, and \`meds_other\`.

**\`meds_medication_history\` is archived. Ignore it entirely**, even when it occurs in a newer dictionary.

The repo is a source of locally tested proposed HTML and scripts. It is not a REDCap integration, cannot infer the installed custom-label setting from a data dictionary, and must not silently deploy changes.

## Working with the user: ask only for needed inputs

1. For a routine audit, ask for the latest **REDCap Data Dictionary CSV export** from the relevant project (Project Setup → Data Dictionary). You can work with the seven repeating-instrument ZIP exports, but the full dictionary is preferred.
2. To check what is actually configured, separately ask for **the current custom-label HTML** copied from *Project Setup → Repeating Instruments and Events → Modify*. One text file per instrument in an ignored \`inputs/installed-labels/\` directory. Never claim a dictionary proves which label is currently installed.
3. For safe testing, ask for **a test project/record ID** and confirmation the intended repeating event is \`patient_baseline_arm_1\`. Use synthetic test records only; ask for the data import template if the actual project differs. Never presume a real record ID is safe to overwrite.
4. For a code rename, ask for an explicit old→new field mapping when ambiguous; never guess based on similar labels.
5. For confirming sort persistence, ask the user to switch records *without clicking sort first* and share a screenshot/PDF of the initial view. A static sorted screenshot alone cannot prove persistence.

Do not ask again for data already available in the conversation or workspace. Proceed with the reference dictionary and labels when sufficient.

## Mandatory workflow

1. Inspect \`README.md\`, \`config/instruments.json\`, \`reference/labels/\`, and relevant tests before editing.
2. Run \`python3 -m unittest discover -s tests -v\`.
3. Put user-supplied exports in \`inputs/\`, **which is Git-ignored**. Do not commit the actual full project dictionary, record-level data, screenshots with identifiers, access tokens, or passwords.
4. Run \`python3 med_label_check.py check inputs/NEW_DICTIONARY.csv --out outputs/AUDIT_DATE\`. For a comparison with installed labels, supply \`--installed-labels inputs/installed-labels\`.
5. Read per-form \`report.md\` and \`report.json\`; classify each instrument:
   - \`NO_LABEL_CHANGE\`: no relevant model change.
   - \`RETEST_NO_HTML_CHANGE\`: choice label/addition only, label piping is still dynamic; add synthetic test.
   - \`UPDATE_REQUIRED\`: safe and unambiguous generated complete label differs; propose full paste.
   - \`REVIEW_REQUIRED\`: incompatible type, absent field, new nested group, nontrivial branching or unclear parent code; explain, don't auto-install.
6. For changes, prepare a small diff summary, the **full complete copy-and-paste label**, and a validation plan. The user consistently needs the *entire label* after each change, not a snippet.
7. Run \`generate\` to produce *synthetic* coded CSV + expected values. Before a REDCap import, instruct user to back up any existing test records and review comparison table. If deliberately clearing fields, select "Overwrite data with blank values: Yes". Confirm the import second step (\`Import Data\`) was clicked.
8. Review a REDCap screenshot/PDF and compare expected examples, including every changed subtype and fallback. Never declare a 100% match if only sample entries were checked.
9. Require explicit user approval before modifying approved label files or updating the baseline. Prefer a PR, run CI, and record the rationale and tests in the PR.

## Label specification

- Display \`Date:\` followed by start and stop **YYYY-MM-DD**, green \`#00B050\` for known start, red \`#FF0000\` for known stop; missing dates show plain black \`(Blank)\` without fixed-width padding.
- Drug name appears blue \`#0070C0\`. For a known parent medication class, use the specific child field only if the parent code matches **and** the child has a value. Stale data from an unrelated subfield must not leak into the label.
- \`Disc?\` in bold; "No" orange \`#FFB000\`; "Yes" black; missing blank.
- Prefer CSS \`data-parent\`, \`data-specific\` selectors, proven working in this project; no helper fields or action tags.
- A missing start date groups in the sort with other blanks; label sorting is lexical and only works chronologically for known **YYYY-MM-DD** prefixes. Each instrument sorts separately; no HTML can enforce the browser's default column direction across records.
- If a new type of nested choice appears, map it deliberately and add tests. If an old label path is unmatched, fallback to the parent name rather than inventing a drug.
- Free-text Other paths are conditional on parent/subchoice; note existing unusual branching of \`med_misc_other_name\` but do not edit the dictionary without a separate decision.

## Safety and quality guardrails

- Never push raw patient records or full private project dictionary to GitHub, particularly if this repository is public. Use minimal *synthetic* fixtures in unit tests.
- Do not change instrument names, record identifiers, or instance numbers in a user's REDCap without explicit confirmation.
- Don't confuse sort appearance with actual instance reordering. The instance numbers are storage identity; the labels are a display mechanism.
- Treat suspected reversed start/stop dates as a *data quality* issue, not a custom-label issue. Never silently rewrite dates.
- Do not claim REDCap's actual environment was automatically tested; offline tests only confirm generated markup and CSV structure.
- If tests or import settings fail, show concrete failures and what is needed to diagnose them.
- Keep changes narrow, show diffs, and retain an approved known-good label for rollback.

## Commands

\`\`\`bash
python3 -m unittest discover -s tests -v
python3 med_label_check.py check inputs/DataDictionary.csv --out outputs/audit
python3 med_label_check.py generate inputs/DataDictionary.csv --record-id 2 --out outputs/synthetic
\`\`\`

For unusual field types or new hierarchies, **STOP at REVIEW_REQUIRED** and consult the user before updating mappings.
