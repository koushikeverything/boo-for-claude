"""Phase 2: capability catalog + role matrix integrity, role-profile schema, and gating logic."""
import copy
import os
import sys
import unittest

from _util import REPO, load_json
import validate_brief

sys.path.insert(0, os.path.join(REPO, "lib"))
import gating  # noqa: E402


class TestCatalogIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_json("config", "capability-catalog.json")
        cls.matrix = load_json("config", "role-matrix.json")
        cls.brief_sources = set(load_json("schemas", "brief.schema.json")["$defs"]["source_type"]["enum"])

    def test_every_capability_provider_is_defined(self):
        for cap, spec in self.catalog["capabilities"].items():
            for prov in spec["providers"]:
                self.assertIn(prov, self.catalog["providers"], f"{cap} references undefined provider {prov}")

    def test_provider_sources_are_in_brief_schema(self):
        for prov, spec in self.catalog["providers"].items():
            for src in spec.get("sources", []):
                self.assertIn(src, self.brief_sources, f"provider {prov} source {src!r} not in brief schema enum")

    def test_min_max_sane(self):
        for cap, spec in self.catalog["capabilities"].items():
            self.assertLessEqual(spec["min"], spec["max"])
            self.assertLessEqual(spec["max"], len(spec["providers"]) if spec["min"] > 0 else 99)


class TestMatrixIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_json("config", "capability-catalog.json")
        cls.matrix = load_json("config", "role-matrix.json")

    def test_all_roles_offer_defined_capabilities_with_valid_levels(self):
        levels = set(self.matrix["requirement_levels"])
        for role, spec in self.matrix["roles"].items():
            for slot, lvl in spec["slots"].items():
                self.assertIn(slot, self.catalog["capabilities"], f"{role} offers unknown slot {slot}")
                self.assertIn(lvl, levels, f"{role}.{slot} has invalid level {lvl}")

    def test_productivity_is_mandatory_for_every_role(self):
        # the brief's spine (calendar/email) — every role needs it
        for role, spec in self.matrix["roles"].items():
            self.assertEqual(spec["slots"].get("productivity"), "mandatory", f"{role} missing mandatory productivity")

    def test_every_mandatory_slot_has_a_native_provider_option(self):
        for role, spec in self.matrix["roles"].items():
            for slot, lvl in spec["slots"].items():
                if lvl == "mandatory":
                    provs = self.catalog["capabilities"][slot]["providers"]
                    self.assertTrue(any(self.catalog["providers"][p]["native_connector"] for p in provs),
                                    f"{role}.{slot} mandatory but no native provider")


class TestRoleProfileSchema(unittest.TestCase):
    def test_sample_profile_validates(self):
        schema = load_json("schemas", "role-profile.schema.json")
        profile = load_json("schemas", "sample-role-profile.json")
        # schema-only validation (the brief's semantic rules don't apply to a profile)
        self.assertEqual(validate_brief.schema_validate(schema, profile), [])


class TestGating(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = gating.load_matrix()
        cls.catalog = gating.load_catalog()
        cls.profile = load_json("schemas", "sample-role-profile.json")

    def test_full_engineer_profile_is_satisfied(self):
        rep = gating.evaluate("software_engineer", self.profile, self.matrix, self.catalog)
        self.assertTrue(rep["satisfied"])
        self.assertEqual(rep["missing_mandatory"], [])
        # pagerduty is reconnect_needed → appears in degraded, not connected
        self.assertIn("incidents", rep["degraded"])

    def test_missing_mandatory_code_blocks_completeness(self):
        p = copy.deepcopy(self.profile)
        p["connections"] = [c for c in p["connections"] if c["capability"] != "code"]
        rep = gating.evaluate("software_engineer", p, self.matrix, self.catalog)
        self.assertFalse(rep["satisfied"])
        self.assertIn("code", rep["missing_mandatory"])

    def test_recommended_missing_is_reported_not_blocking(self):
        p = copy.deepcopy(self.profile)
        p["connections"] = [c for c in p["connections"] if c["capability"] not in ("observability",)]
        rep = gating.evaluate("software_engineer", p, self.matrix, self.catalog)
        self.assertTrue(rep["satisfied"])  # observability is recommended, not mandatory
        self.assertIn("observability", rep["missing_recommended"])

    def test_invalid_provider_for_capability_flagged(self):
        p = copy.deepcopy(self.profile)
        p["connections"].append({"capability": "code", "provider": "figma", "status": "active"})
        rep = gating.evaluate("software_engineer", p, self.matrix, self.catalog)
        self.assertTrue(any("not valid for capability 'code'" in x for x in rep["problems"]), rep["problems"])

    def test_capability_not_offered_to_role_flagged(self):
        # analytics is not offered to software_engineer
        p = copy.deepcopy(self.profile)
        p["connections"].append({"capability": "analytics", "provider": "amplitude", "status": "active"})
        rep = gating.evaluate("software_engineer", p, self.matrix, self.catalog)
        self.assertTrue(any("not offered to role" in x for x in rep["problems"]), rep["problems"])

    def test_coverage_note_renders(self):
        rep = gating.evaluate("software_engineer", self.profile, self.matrix, self.catalog)
        note = gating.coverage_note(rep, self.matrix)
        self.assertIn("Software Engineer", note)

    # --- availability gate (option A) ---

    def test_analytics_has_no_connectable_provider(self):
        self.assertEqual(gating.connectable_providers("analytics", self.catalog), [])

    def test_code_connectable_excludes_non_native_bitbucket(self):
        provs = gating.connectable_providers("code", self.catalog)
        self.assertIn("github", provs)
        self.assertIn("gitlab", provs)
        self.assertNotIn("bitbucket", provs)  # native_connector: false → hidden

    def test_unconnectable_slot_is_hidden_not_missing(self):
        # analytics is 'recommended' for data_analyst but has no connector → hidden, not a gap
        empty_profile = {"role": "data_analyst", "connections": [
            {"capability": "productivity", "provider": "google_workspace", "status": "active"}
        ]}
        rep = gating.evaluate("data_analyst", empty_profile, self.matrix, self.catalog)
        self.assertIn("analytics", rep["hidden_slots"])
        self.assertNotIn("analytics", rep["missing_recommended"])
        self.assertTrue(rep["satisfied"])  # only productivity is mandatory + it's connected

    def test_engineer_has_no_hidden_slots(self):
        rep = gating.evaluate("software_engineer", self.profile, self.matrix, self.catalog)
        self.assertEqual(rep["hidden_slots"], [])  # every engineer slot has a native provider

    def test_role_slot_menu_lists_only_connectable_providers(self):
        menu = gating.role_slot_menu("data_analyst", self.matrix, self.catalog)
        self.assertIn("analytics", menu["hidden"])
        # productivity offered with both connectable providers
        prod = [m for m in menu["mandatory"] if m["capability"] == "productivity"][0]
        self.assertEqual(set(prod["providers"]), {"google_workspace", "microsoft_365"})
        # no menu entry ever contains a non-connectable provider
        for level in ("mandatory", "recommended", "optional"):
            for entry in menu[level]:
                for p in entry["providers"]:
                    self.assertTrue(gating.is_connectable(p, self.catalog))


if __name__ == "__main__":
    unittest.main()
