# REDCap Medication Custom Labelling

Offline tools and reference labels for maintaining **seven repeating medication instruments** in the REDCap PANS2023 project, **Patient Baseline** event (\`patient_baseline_arm_1\`).

> **Privacy:** This repository may be public. Never commit a complete production data dictionary, actual REDCap data exports, record identifiers, API tokens, or identifiable patient information. Supply dictionaries privately to the program on your own computer or in a secured Codex workspace. The \`inputs/\` and \`outputs/\` folders are ignored by Git.

## Scope

| REDCap repeating instrument | Main field |
|---|---|
| \`meds_abs\` | \`med_abs_name\` |
| \`meds_nsaids\` | \`med_nsaids_name\` |
| \`meds_steroids\` | \`med_steroids_name\` |
| \`meds_dmards\` | \`med_dmards_name\` |
| \`meds_psych\` | \`med_psych_name\` |
| \`meds_misc\` | \`med_misc_name\` |
| \`meds_other\` | \`med_other_name\` |

\`meds_medication_history\` is **archived, excluded, and should not be tested or maintained** by this project. Do not confuse it with the seven active instruments. All seven repeat within \`patient_baseline_arm_1\`.

## Quick start

Python **3.10+**, standard library only.

\`\`\`bash
python3 -m unittest discover -s tests -v
python3 med_label_check.py check "inputs/PANS2023_DataDictionary_latest.csv" --out outputs/current-audit
python3 med_label_check.py generate "inputs/PANS2023_DataDictionary_latest.csv" --record-id 2 --out outputs/patient-2-tests
\`\`\`

The first command runs automated tests. The second checks the uploaded dictionary against the *actual seven custom-label source files*, validates field names/types, nested parent codes, and branching logic, and writes \`report.md\`, \`report.json\`, and any fully generated replacement label files. The third produces synthetic, coded REDCap import CSVs and expected-sort checklists for all seven categories. **It does not import anything into REDCap.**

Install a change only after reviewing the complete generated label, testing it in a REDCap test project, and obtaining user approval. Date sorting depends on the *Label* column being sorted ascending; HTML cannot force or persist REDCap's UI sort preference.

For an existing installation, optionally compare label text that was copied from REDCap:

\`\`\`bash
python3 med_label_check.py check inputs/new_dictionary.csv --installed-labels inputs/installed-labels --out outputs/audit
\`\`\`

Place one \`meds_*.html\` file per instrument in \`inputs/installed-labels/\`. The comparison detects drift; it does not update REDCap.

## Documentation

- [AGENTS.md](AGENTS.md): operational contract for Codex agents, including what to request from the user.
- [docs/OPERATIONS.md](docs/OPERATIONS.md): import safety, test workflow, checks, review decisions.
- [docs/FORMATTING.md](docs/FORMATTING.md): date and drug-label logic, color rules, known limitations.
- [docs/VALIDATION.md](docs/VALIDATION.md): how to verify changes manually in REDCap.
- [reference/labels](reference/labels): complete, paste-ready working custom labels.
- [config/instruments.json](config/instruments.json): the seven monitored form mappings and nested-drug selectors.

## Safety and limitations

- No REDCap connection, credentials, API calls, or changes to real records.
- Never automatically deploy HTML or change a study dictionary.
- The dictionary **does not contain the Custom Label for Repeating Instruments setting**; the installed HTML must be obtained separately to prove parity.
- The checker can safely synthesize candidate labels for unambiguous *parent choice-code* changes. New subfields, missing fields, ambiguous branching, or unexpected field types require human review.
- An added choice in an existing drug subfield usually **does not** require a label edit: the label pipes the choice text dynamically. It still requires a test import for that choice.
- The date prefix is \`YYYY-MM-DD\` (green start, red stop); empty dates render \`(Blank)\` (black). A missing start date cannot be sorted chronologically. The UI sorts each instrument **separately**.
- The generated synthetic CSVs use explicitly numbered instances. These may overwrite test data: back up and review the comparison table, and set **Overwrite data with blank values: Yes** if clearing existing values is intended.

## Typical maintenance task

1. Download a current *Data Dictionary* CSV from the intended REDCap project (not a patient export).
2. Copy it to \`inputs/\` without committing it.
3. Run \`check\`. Read the full report, not only the summary status.
4. Inspect any new parent-choice or subtype mapping; review complete generated candidate HTML.
5. Run \`generate\` against a test record, import **in a test project only**, and verify chronological label sorting, blank fields, drug names, and discontinued status.
6. After signoff, paste the approved full label into **Project Setup → Repeating Instruments and Events → Modify → Custom Label**, then save and retest.
7. Update the source labels and mapping in a code-reviewed commit; retain a local backup of the prior setting.

**Maintainers:** Keep checks and generated reports local to prevent accidental disclosure of research/patient data.
