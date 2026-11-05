"""Regression tests using deliberately synthetic, minimal REDCap dictionary rows."""
import csv
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import med_label_check as med


HEADERS = [med.NAME, med.FORM, med.TYPE, med.CHOICES, med.BRANCH]


class MedicationLabelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = deepcopy(med.settings())
        self.rows = []
        for form, spec in self.config["forms"].items():
            pfx = spec["prefix"]
            parent_codes = ["99"] + [c["parent_code"] for c in spec["children"]]
            parent_codes = list(dict.fromkeys(parent_codes + ["1"]))
            parent_choices = " | ".join(f"{x}, Synthetic parent {x}" for x in parent_codes)
            self.add(form, spec["parent"], "dropdown", parent_choices)
            self.add(form, spec["other"], "text")
            self.add(form, pfx + "_start", "text")
            self.add(form, pfx + "_stop", "text")
            self.add(form, pfx + "_disc", "yesno")
            for child in spec["children"]:
                ref = child.get("branch_parent", spec["parent"])
                code = child.get("branch_code", child["parent_code"])
                self.add(form, child["field"], "radio", "1, Specific option 1 | 2, Specific option 2",
                         f"[{ref}] = '{code}'")
            # Simulate existing context fields but make sure they are exempted.
            for name in spec.get("contextual_fields", []):
                self.add(form, name, "radio", "1, Context choice", f"[{spec['parent']}] = '1'")
            spec["baseline_choice_hashes"] = {
                spec["parent"]: med.choice_hash(parent_choices)}
            for child in spec["children"]:
                child["baseline_hash"] = med.choice_hash(
                    "1, Specific option 1 | 2, Specific option 2")
        self.add("meds_medication_history", "med_history_reviewer", "dropdown", "1, Archived")
        self.write()

    def add(self, form, name, field_type, choices="", branch=""):
        self.rows.append({
            med.NAME: name, med.FORM: form, med.TYPE: field_type,
            med.CHOICES: choices, med.BRANCH: branch,
        })

    def write(self):
        self.dictionary = self.root / "dictionary.csv"
        with self.dictionary.open("w", newline="", encoding="utf-8") as handle:
            out = csv.DictWriter(handle, fieldnames=HEADERS)
            out.writeheader()
            out.writerows(self.rows)

    def audit(self):
        with patch.object(med, "settings", return_value=deepcopy(self.config)):
            return med.check_dictionary(self.dictionary, self.root / "audit")["forms"]

    def test_original_fixture_no_label_change_and_archived_ignored(self):
        results = self.audit()
        self.assertEqual(set(results), set(self.config["forms"]))
        self.assertTrue(all(x["status"] == "NO_LABEL_CHANGE" for x in results.values()))

    def test_new_choice_needs_retest_but_not_html_rewrite(self):
        row = next(x for x in self.rows if x[med.NAME] == "med_psych_amphetamine")
        row[med.CHOICES] += " | 3, New synthetic stimulant"
        self.write()
        results = self.audit()
        self.assertEqual(results["meds_psych"]["status"], "RETEST_NO_HTML_CHANGE")

    def test_changed_parent_code_generates_full_label(self):
        row = next(x for x in self.rows if x[med.NAME] == "med_dmards_name")
        row[med.CHOICES] = row[med.CHOICES].replace("506, Synthetic parent 506",
                                                     "555, Synthetic parent 555")
        subtype = next(x for x in self.rows if x[med.NAME] == "med_dmards_tnftype")
        subtype[med.BRANCH] = "[med_dmards_name] = '555'"
        self.write()
        results = self.audit()
        self.assertEqual(results["meds_dmards"]["status"], "UPDATE_REQUIRED")
        html = (self.root / "audit" / "labels" / "meds_dmards.html").read_text()
        self.assertIn('data-parent="555"', html)
        self.assertIn("[med_dmards_tnftype]", html)

    def test_ambiguous_parent_code_change_requires_manual_review(self):
        row = next(x for x in self.rows if x[med.NAME] == "med_dmards_name")
        row[med.CHOICES] += " | 555, Another class"
        subtype = next(x for x in self.rows if x[med.NAME] == "med_dmards_tnftype")
        subtype[med.BRANCH] = "[med_dmards_name] = '555'"
        self.write()
        self.assertEqual(self.audit()["meds_dmards"]["status"], "REVIEW_REQUIRED")

    def test_unknown_medication_child_requires_review(self):
        self.add("meds_psych", "med_psych_new_child", "radio", "1, New drug",
                 "[med_psych_name] = '819'")
        self.write()
        self.assertEqual(self.audit()["meds_psych"]["status"], "REVIEW_REQUIRED")

    def test_missing_required_field_requires_review(self):
        self.rows = [x for x in self.rows if x[med.NAME] != "med_abs_start"]
        self.write()
        self.assertEqual(self.audit()["meds_abs"]["status"], "REVIEW_REQUIRED")

    def test_synthetic_csv_codes_and_event(self):
        with patch.object(med, "settings", return_value=deepcopy(self.config)):
            result = med.generate(self.dictionary, self.root / "generated",
                                  record_id="2", id_field="participant_id",
                                  event="patient_baseline_arm_1")
        self.assertGreater(result["total"], 70)
        for form in self.config["forms"]:
            path = self.root / "generated" / (form + "_import.csv")
            self.assertTrue(path.exists())
            with path.open(newline="", encoding="utf-8") as handle:
                entries = list(csv.DictReader(handle))
            self.assertEqual(len(entries), result["counts"][form])
            self.assertEqual([int(x["redcap_repeat_instance"]) for x in entries],
                             list(range(1, len(entries) + 1)))
            for entry in entries:
                self.assertEqual(entry["participant_id"], "2")
                self.assertEqual(entry["redcap_event_name"], "patient_baseline_arm_1")
                self.assertEqual(entry["redcap_repeat_instrument"], form)
        self.assertFalse((self.root / "generated" / "meds_medication_history_import.csv").exists())

    def test_detects_installed_label_drift(self):
        folder = self.root / "installed"
        folder.mkdir()
        (folder / "meds_psych.html").write_text("wrong label", encoding="utf-8")
        with patch.object(med, "settings", return_value=deepcopy(self.config)):
            results = med.check_dictionary(self.dictionary, self.root / "drift",
                                           installed_labels=folder)["forms"]
        self.assertEqual(results["meds_psych"]["status"], "REVIEW_REQUIRED")

    def test_date_and_subtype_templates_exist(self):
        for form in self.config["forms"]:
            html = med.render_label(form, self.config["forms"][form])
            self.assertIn(":year]", html)
            self.assertIn(".start-blank", html)
            self.assertIn("#0070C0", html)
            self.assertIn("Disc?", html)


if __name__ == "__main__":
    unittest.main()
