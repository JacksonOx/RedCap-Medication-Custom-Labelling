# Custom label formatting and medication hierarchy

REDCap location: **Project Setup → Repeating Instruments and Events → Modify → Custom Label**. Piping and inline HTML/CSS was empirically tested in the seven Patient Baseline repeating instruments.

Examples of the required display:

```text
Date: 2024-03-19 - 2024-04-20 | Sertraline (ZOLOFT) | Disc? Yes
Date: 2025-06-01 - (Blank) | Oseltamivir (TAMIFLU) | Disc? No
Date: (Blank) - 2024-11-14 | Buspirone (BUSPAR) | Disc?
```

Start: `#00B050` (green); stop: `#FF0000` (red); drug: `#0070C0` (blue); Disc? No: `#FFB000` (orange); Disc? Yes: `#000000` (black). Empty date: plain black `(Blank)`.

Dates use REDCap piping `[field:year]-[field:month]-[field:day]`. That alone prints `--` when the date is blank, so conditional CSS on `data-start=""` and `data-stop=""` hides the date elements and displays `(Blank)`. No new fields/action tags. For subcategory selection, compare `[parent:value]` with the raw coded parent option, and use `[child]` for the human-readable label. Do *not* display unrelated stale children.

Known subtype groups:
- DMARDs: TNF inhibitors `506` → `med_dmards_tnftype`; JAK `514` → `med_dmards_jaktype`.
- Psych: methylphenidate `818` → `med_psych_methylphenidate`; amphetamine `819` → `med_psych_amphetamine`.
- Misc: contraceptive `909` nested into `med_misc_name_type_contra` → pill or long-acting; acne `910`; migraine `911`; antihistamine `912`; antifungal `913`; antiviral `914`; gastric `915`; thyroid `916`; controlled `917`; supplements `918`; metabolic `919`.
- Other medication (parent value `99`) typically uses the instrument's `*_other_name` free text; Misc also has child `99` Other paths.

**Date sorting:** The Label column is sorted as *text*, so YYYY-MM-DD is necessary to sort across years; MM-DD-YYYY does not. Chronological sorting does *not* change REDCap repeat-instance IDs. Start-date blanks cluster together. HTML **does not persist the UI's column sort direction** across different records; that must be tested separately.
