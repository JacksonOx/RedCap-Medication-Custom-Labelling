#!/usr/bin/env python3
"""Offline REDCap medication custom-label audit and synthetic test generator.

Python 3.10+; standard library only. Never connects to REDCap.
Only the seven active repeating medication instruments are in scope.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config" / "instruments.json"
LABELS = ROOT / "reference" / "labels"

NAME = "Variable / Field Name"
FORM = "Form Name"
TYPE = "Field Type"
CHOICES = "Choices, Calculations, OR Slider Labels"
BRANCH = "Branching Logic (Show field only if...)"


def settings():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def read_dictionary(path):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {NAME, FORM, TYPE, CHOICES, BRANCH}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("Not a REDCap Data Dictionary CSV: missing " +
                             ", ".join(sorted(required - set(reader.fieldnames or []))))
        return list(reader)


def indexed(rows, form):
    return {row[NAME]: row for row in rows if row[FORM] == form}


def choice_map(raw):
    """Return raw coded choice -> display label; do not substitute labels for codes."""
    result = {}
    for part in (raw or "").split("|"):
        if not part.strip():
            continue
        if "," not in part:
            continue
        key, label = part.split(",", 1)
        key = key.strip()
        if key:
            result[key] = label.strip()
    return result


def choice_hash(raw):
    return hashlib.sha256((raw or "").encode("utf-8")).hexdigest()[:16]


def branch_code(branch, ref_name):
    """Extract unambiguous simple [field] = 'code' predicate, if present."""
    regex = r"\[" + re.escape(ref_name) + r"\]\s*=\s*['\"]([^'\"]+)['\"]"
    matches = set(re.findall(regex, branch or ""))
    return next(iter(matches)) if len(matches) == 1 else None


def normalize_html(text):
    return re.sub(r"\s+", " ", text).strip()


def render_label(form, spec, code_overrides=None):
    """Render full source label with safely updated known parent-code selectors.

    New hierarchy/subfield types are not automatically generated. The user must
    explicitly review and update the reference label and configuration first.
    """
    template_path = LABELS / (form + ".html")
    html = template_path.read_text(encoding="utf-8")
    for old, new in (code_overrides or {}).items():
        if old != new:
            html = html.replace('data-parent="' + old + '"',
                                'data-parent="' + new + '"')
    return html


def check_dictionary(dictionary, output, installed_labels=None):
    rows = read_dictionary(dictionary)
    config = settings()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    candidate_dir = output / "labels"
    candidate_dir.mkdir(exist_ok=True)
    results = {}
    known_forms = config["forms"]
    for form, spec in known_forms.items():
        by_name = indexed(rows, form)
        findings = []
        code_overrides = {}
        hard_review = False
        retest = False
        update = False
        pfx = spec["prefix"]
        expected = {
            spec["parent"]: {"dropdown", "radio"},
            spec["other"]: {"text", "notes"},
            pfx + "_start": {"text"},
            pfx + "_stop": {"text"},
            pfx + "_disc": {"yesno"},
        }
        for child in spec["children"]:
            expected[child["field"]] = {"radio", "dropdown"}
        for name, acceptable_types in expected.items():
            row = by_name.get(name)
            if not row:
                hard_review = True
                findings.append(f"MISSING: required piping field {name}")
            elif row[TYPE] not in acceptable_types:
                hard_review = True
                findings.append(f"TYPE: {name} is {row[TYPE]!r}, expected one of {sorted(acceptable_types)}")
        parent = by_name.get(spec["parent"])
        current_parent_choices = choice_map(parent[CHOICES]) if parent else {}
        for field, baseline_hash in spec.get("baseline_choice_hashes", {}).items():
            if baseline_hash and field in by_name:
                if choice_hash(by_name[field][CHOICES]) != baseline_hash:
                    retest = True
                    findings.append(f"CHOICES: {field} options or labels changed; retest coded choices")
        for child in spec["children"]:
            row = by_name.get(child["field"])
            if not row:
                continue
            if choice_hash(row[CHOICES]) != child.get("baseline_hash"):
                retest = True
                findings.append(f"CHOICES: {child['field']} options or labels changed; retest choices")
            ref = child.get("branch_parent", spec["parent"])
            old_code = child.get("branch_code", child["parent_code"])
            new_code = branch_code(row[BRANCH], ref)
            if new_code is None:
                hard_review = True
                findings.append(f"BRANCH REVIEW: {child['field']} does not have a simple unambiguous [{ref}] = 'code'")
            elif new_code != old_code:
                if ref == spec["parent"]:
                    if old_code in current_parent_choices and new_code in current_parent_choices:
                        hard_review = True
                        findings.append(f"AMBIGUOUS: {child['field']} moved to {new_code} but old parent code {old_code} still exists")
                    elif new_code not in current_parent_choices:
                        hard_review = True
                        findings.append(f"INVALID: branching code {new_code} for {child['field']} not found in parent choices")
                    elif old_code in code_overrides and code_overrides[old_code] != new_code:
                        hard_review = True
                        findings.append(f"CONFLICT: multiple replacements for old parent code {old_code}")
                    else:
                        code_overrides[old_code] = new_code
                        update = True
                        findings.append(f"UPDATE: {child['field']} parent code {old_code} -> {new_code}")
                else:
                    hard_review = True
                    findings.append(f"NESTED BRANCH REVIEW: {child['field']} {ref} code {old_code} -> {new_code}")
            if ref == spec["parent"] and old_code not in current_parent_choices and new_code == old_code:
                hard_review = True
                findings.append(f"MISSING PARENT CODE: {child['field']} references absent choice {old_code}")
        # Newly added branching subfields could introduce a medication class and
        # require label structure changes. Do not guess their meaning.
        allowed = set(expected) | set(spec.get("contextual_fields", []))
        for name, row in by_name.items():
            if name in allowed:
                continue
            branching = row.get(BRANCH, "")
            if row[TYPE] in {"dropdown", "radio", "checkbox"} and (
                ("[" + spec["parent"] + "]") in branching or
                any(("[" + c["field"] + "]") in branching for c in spec["children"])
            ):
                hard_review = True
                findings.append(f"NEW CONDITIONAL CHOICE FIELD: {name}; manual mapping required")
        candidate = render_label(form, spec, code_overrides)
        if installed_labels:
            installed = Path(installed_labels) / (form + ".html")
            if installed.exists():
                if normalize_html(installed.read_text(encoding="utf-8")) != normalize_html(render_label(form, spec)):
                    findings.append("INSTALLED LABEL DRIFT: differs from saved approved reference")
                    hard_review = True
            else:
                findings.append(f"Installed label file not supplied for {form}; cannot verify installed HTML")
        if hard_review:
            status = "REVIEW_REQUIRED"
        elif update:
            status = "UPDATE_REQUIRED"
        elif retest:
            status = "RETEST_NO_HTML_CHANGE"
        else:
            status = "NO_LABEL_CHANGE"
        if update and not hard_review:
            (candidate_dir / (form + ".html")).write_text(candidate, encoding="utf-8")
        results[form] = {"status": status, "findings": findings,
                         "candidate_file": ("labels/" + form + ".html") if update and not hard_review else None}
    report = {"event": config["event"], "archived_ignored": config["archived"],
              "dictionary": Path(dictionary).name, "forms": results}
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = ["# REDCap medication label maintenance audit", "",
             f"Event: \`{config['event']}\`. Archived instruments excluded.",
             "", "| Instrument | Decision |", "|---|---|"]
    for form, item in results.items():
        lines.append(f"| \`{form}\` | **{item['status']}** |")
    for form, item in results.items():
        lines += ["", f"## {form}", ""]
        lines += ["- " + f for f in item["findings"]] if item["findings"] else ["- No label-relevant differences detected against stored schema checks."]
        if item["candidate_file"]:
            lines.append(f"- Candidate complete label: \`{item['candidate_file']}\` (test before deployment).")
    lines += ["", "## Limits", "",
              "- The REDCap data dictionary does not export installed repeating-instrument custom labels.",
              "- No automated changes or imports were made to REDCap.",
              "- Choice hashing reflects the recorded baseline for selected medication fields; unrelated dictionary edits are out of scope.",
              "- Review any new branching choices even if a candidate was generated.",
              ""]
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return report


def synthetic_rows(rows, form, spec, record_id, id_field, event):
    by_name = indexed(rows, form)
    parent_field = spec["parent"]
    choices = choice_map(by_name[parent_field][CHOICES])
    if not choices:
        raise ValueError("No coded choices for " + parent_field)
    cases = []
    child_groups = defaultdict(list)
    for child in spec["children"]:
        child_groups[child["parent_code"]].append(child)
    for code, label in choices.items():
        children = child_groups.get(code, [])
        cases.append((code, {}, label, "parent; subtype missing"))
        if code == "99":
            cases.append((code, {spec["other"]: "Synthetic other medication"}, "Synthetic other medication", "Other free-text"))
        for child in children:
            nested_cases = []
            for option, sublabel in choice_map(by_name[child["field"]][CHOICES]).items():
                fields = {child["field"]: option}
                if child.get("branch_parent"):
                    fields[child["branch_parent"]] = child["branch_code"]
                display = sublabel
                if option == "99":
                    fields[spec["other"]] = "Synthetic " + form + " other medication"
                    display = fields[spec["other"]]
                nested_cases.append((code, fields, display, child["field"]))
            cases.extend(nested_cases)
    # Add formatting permutations independent of parent choices.
    first_code, first_label = next(iter(choices.items()))
    for name in ("both_blank", "start_blank", "stop_blank", "disc_yes", "disc_no", "disc_blank"):
        cases.append((first_code, {}, first_label, name))
    # Scramble dates relative to repeat instance numbers on purpose.
    n = len(cases)
    all_fields = [parent_field, spec["other"], spec["prefix"] + "_start",
                  spec["prefix"] + "_stop", spec["prefix"] + "_disc"]
    all_fields += [child["field"] for child in spec["children"]]
    all_fields = list(dict.fromkeys(all_fields))
    output = []
    checklist = []
    for i, (code, fields, display, scenario) in enumerate(cases, 1):
        day_offset = (n - i) * 19
        start = date(2022, 1, 1) + timedelta(days=day_offset)
        stop = start + timedelta(days=30)
        # Existing odd-numbered instances do not correspond to ascending dates.
        row = {id_field: str(record_id), "redcap_event_name": event,
               "redcap_repeat_instrument": form, "redcap_repeat_instance": str(i)}
        row.update({k: "" for k in all_fields})
        row[parent_field] = code
        row.update(fields)
        row[spec["prefix"] + "_start"] = start.isoformat()
        row[spec["prefix"] + "_stop"] = stop.isoformat() if i % 3 == 0 else ""
        row[spec["prefix"] + "_disc"] = ["", "0", "1"][i % 3]
        if scenario in {"both_blank", "start_blank"}:
            row[spec["prefix"] + "_start"] = ""
        if scenario in {"both_blank", "stop_blank"}:
            row[spec["prefix"] + "_stop"] = ""
        if scenario == "disc_yes":
            row[spec["prefix"] + "_disc"] = "1"
        elif scenario == "disc_no":
            row[spec["prefix"] + "_disc"] = "0"
        elif scenario == "disc_blank":
            row[spec["prefix"] + "_disc"] = ""
        output.append(row)
        checklist.append({"instrument": form, "instance": i, "start": row[spec["prefix"] + "_start"],
                          "stop": row[spec["prefix"] + "_stop"], "expected_medication": display,
                          "scenario": scenario})
    return output, checklist


def generate(dictionary, output, record_id, id_field, event):
    rows = read_dictionary(dictionary)
    config = settings()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    all_checks = []
    counts = {}
    for form, spec in config["forms"].items():
        entries, checks = synthetic_rows(rows, form, spec, record_id, id_field, event)
        all_checks.extend(checks)
        cols = list(entries[0])
        with (output / (form + "_import.csv")).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=cols)
            writer.writeheader()
            writer.writerows(entries)
        counts[form] = len(entries)
    with (output / "expected_results.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(all_checks[0]))
        writer.writeheader()
        writer.writerows(all_checks)
    with (output / "expected_sort_order.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(all_checks[0]))
        writer.writeheader()
        for form in config["forms"]:
            part = [r for r in all_checks if r["instrument"] == form]
            # Lexical default sorted label: "(Blank)" before YYYY-MM-DD.
            writer.writerows(sorted(part, key=lambda r: (r["start"] != "", r["start"], str(r["expected_medication"]))))
    manifest = {"record_id": str(record_id), "event": event, "counts": counts,
                "total": sum(counts.values()), "note": "Synthetic test data; review before importing into a test project"}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    audit = subs.add_parser("check", help="Compare dictionary to seven reference labels and schema")
    audit.add_argument("dictionary", type=Path)
    audit.add_argument("--out", type=Path, default=Path("outputs/audit"))
    audit.add_argument("--installed-labels", type=Path)
    syn = subs.add_parser("generate", help="Create seven synthetic REDCap CSVs and expected checks")
    syn.add_argument("dictionary", type=Path)
    syn.add_argument("--record-id", default="2")
    syn.add_argument("--id-field", default="participant_id")
    syn.add_argument("--event", default="patient_baseline_arm_1")
    syn.add_argument("--out", type=Path, default=Path("outputs/synthetic"))
    args = parser.parse_args()
    if args.command == "check":
        summary = check_dictionary(args.dictionary, args.out, args.installed_labels)
        for form, item in summary["forms"].items():
            print(form + ": " + item["status"])
        print("Reports written to", args.out)
    else:
        summary = generate(args.dictionary, args.out, args.record_id, args.id_field, args.event)
        print("Created", summary["total"], "synthetic repeating instances; outputs in", args.out)


if __name__ == "__main__":
    main()
