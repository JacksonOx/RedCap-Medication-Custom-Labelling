# Human acceptance checklist

- [ ] Seven repeating instruments present under Patient Baseline, `patient_baseline_arm_1`.
- [ ] Archived `meds_medication_history` ignored.
- [ ] Known dates YYYY-MM-DD; start green and stop red.
- [ ] Missing dates display `(Blank)`, no unwanted fixed-width spacing.
- [ ] Drug label blue and correct specific subtype for every selected parent+child pair.
- [ ] Stale child data does not appear for unrelated parents.
- [ ] Missing child falls back to parent label.
- [ ] Parent or child Other: free-text name when provided; otherwise a sensible fallback.
- [ ] Disc? Yes black, No orange, blank empty.
- [ ] Sorting ascending behaves correctly across year boundaries and leap day.
- [ ] Repeating instance numbers remain unchanged by sorting.
- [ ] Check a **second record** to assess sorting preference persistence; note whether any sort arrow was clicked.
- [ ] Import file contains raw choice codes, not visible labels, and correct record ID/event/instrument.
- [ ] Saved existing data backup and reviewed import comparison table.
- [ ] REDCap import was committed, not merely previewed.
- [ ] Proposed label reviewed, full copy-paste supplied, test signed off.
