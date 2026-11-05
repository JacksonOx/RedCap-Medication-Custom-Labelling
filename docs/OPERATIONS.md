# Runbook: checking and changing medication custom labels

## Before starting
Confirm instrument scope (seven active repeating instruments), Patient Baseline \`patient_baseline_arm_1\`, test vs production environment, and user's authority to modify instrument configuration. Keep the CSV private in \`inputs/\`.

## Audit
\`\`\`bash
python3 med_label_check.py check inputs/current.csv --out outputs/latest
\`\`\`
Read \`outputs/latest/report.md\` and \`report.json\`. A field can have changed choice labels without requiring new HTML because REDCap piping dynamically looks up the selected choice. If a *parent choice code* changes, the CSS condition may need changing. Missing referenced fields, new child fields or complex branching require review. The data dictionary alone does not reveal installed custom labels.

For an installed-label comparison, paste the actual current HTML into files named \`inputs/installed-labels/meds_abs.html\` etc. Run the same check with \`--installed-labels inputs/installed-labels\`.

## Change proposal
For every affected instrument show its status, changed code/field, a complete paste label from \`outputs/latest/labels/\` where available, a rationale, and rollback instructions. Do not apply directly to production without approval. Update the approved reference labels in source control after successful testing.

## Synthetic import
\`\`\`bash
python3 med_label_check.py generate inputs/current.csv --record-id 2 --out outputs/test-2
\`\`\`
This writes instrument-separated coded CSVs and expected-sort checklists. Use a **test REDCap project**. Confirm the unique event name and instrument names; use rows CSV; no automatic record renumbering; show comparison table; use explicitly numbered repeating instances. If changing/clearing existing test instances, choose **Overwrite blank values: Yes** and press *Import Data* after validation.

## Validation
Check each class/subtype and Other, missing start/stop dates, Disc? Yes/No/unanswered, duplicates, leap days and year-boundaries, and sorted order despite scrambled instance numbers. After switching patient 1 → patient 2, check whether *initial* sort direction persists without clicking header. A PDF/screenshot of the final sorted order proves the result but not how the UI reached it.

Report only the counts and cases actually verified. Distinguish REDCap UI checks from offline unit tests.
