"""Behavior tests for catalogue_check.py: verdicts, violations, exit codes and rendered output."""
import contextlib
import copy
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import catalogue_check as cc  # noqa: E402

FIXTURES = os.path.normpath(os.path.join(cc.SKILL_DIR, "..", "company-fleets", "fleets", "hosting", "fixtures", "service-catalogue"))


def load(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as fh:
        return json.load(fh)


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="catalogue-test-")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def write(self, doc, name="catalogue.json"):
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(doc if isinstance(doc, str) else json.dumps(doc))
        return path

    def check(self, doc, *extra):
        return cc.execute(["check", "--catalogue", self.write(doc), *extra])

    def rules(self, out):
        return [(v["rule"], v["service"], v["function"]) for v in out["violations"]]

    def entry(self, doc, service, function):
        svc = next(s for s in doc["services"] if s["id"] == service)
        return next(e for e in svc["functions"] if e["function"] == function)


class FixtureVerdicts(Base):
    def test_each_fixture_gets_its_expected_verdict(self):
        expected = {
            "affiliate-valid.json": (0, []),
            "reseller-valid.json": (0, []),
            "shared-valid-no-mail.json": (0, []),
            "platform-managed-cloud.json": (0, []),
            "affiliate-backups-accountable.json": (1, [(2, "provider-hosting", "backups")]),
            "shared-two-accountable.json": (1, [(1, None, "backups")]),
        }
        for name, (code, rules) in expected.items():
            got_code, out = cc.execute(["check", "--catalogue", os.path.join(FIXTURES, name)])
            self.assertEqual((got_code, self.rules(out)), (code, rules), name)
            self.assertEqual(out["verdict"], "pass" if code == 0 else "fail", name)

    def test_missing_escalation_fixture_fails_rule_3_for_each_upstream_function(self):
        code, out = cc.execute(["check", "--catalogue", os.path.join(FIXTURES, "reseller-missing-escalation.json")])
        self.assertEqual(code, 1)
        self.assertEqual({v["rule"] for v in out["violations"]}, {3})
        self.assertEqual(sorted(v["function"] for v in out["violations"]), ["data-center", "hardware", "network"])
        self.assertIn("escalation_path", out["violations"][0]["message"])

    def test_output_carries_registry_text_and_assumptions(self):
        _, out = cc.execute(["check", "--catalogue", os.path.join(FIXTURES, "affiliate-valid.json")])
        registry = json.load(open(cc.DEFAULT_PROFILES))["profiles"]
        affiliate = next(p for p in registry if p["id"] == "affiliate")
        self.assertEqual(out["profile"]["responsible_for"], affiliate["responsible_for"])
        self.assertEqual(out["profile"]["not_responsible_for"], affiliate["not_responsible_for"])
        self.assertTrue(out["assumptions"])

    def test_function_vocabulary_covers_exactly_the_hosting_profiles_in_the_registry(self):
        registry = json.load(open(cc.DEFAULT_PROFILES))["profiles"]
        hosting = sorted(p["id"] for p in registry if p["kind"] == "hosting")
        self.assertEqual(sorted(cc.load_vocabulary()["profiles"]), hosting)

    def test_main_prints_json_and_returns_the_exit_code(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = cc.main(["check", "--catalogue", os.path.join(FIXTURES, "affiliate-backups-accountable.json")])
        self.assertEqual((code, json.loads(buf.getvalue())["verdict"]), (1, "fail"))


class Rule1AccountableParty(Base):
    def test_missing_must_hold_function_is_a_violation(self):
        doc = load("shared-valid-no-mail.json")
        doc["services"][1]["functions"] = [e for e in doc["services"][1]["functions"] if e["function"] != "isolation"]
        code, out = self.check(doc)
        self.assertEqual((code, self.rules(out)), (1, [(1, None, "isolation")]))
        self.assertIn("nobody is accountable", out["violations"][0]["message"])

    def test_the_same_party_listed_in_two_services_is_still_one_party(self):
        doc = load("shared-valid-no-mail.json")
        doc["services"][0]["functions"].append(copy.deepcopy(self.entry(doc, "shared-protection", "backups")))
        self.assertEqual(self.check(doc)[0], 0)

    def test_two_parties_name_both_and_their_services(self):
        _, out = cc.execute(["check", "--catalogue", os.path.join(FIXTURES, "shared-two-accountable.json")])
        msg = out["violations"][0]["message"]
        for text in ("2 accountable parties", "customer (customer-site-backups)", "fixture-co (shared-protection)"):
            self.assertIn(text, msg)

    def test_declared_capability_set_adds_its_functions(self):
        doc = load("platform-managed-cloud.json")
        doc["services"][1]["functions"] = [e for e in doc["services"][1]["functions"] if e["function"] != "cost"]
        code, out = self.check(doc)
        self.assertEqual((code, self.rules(out)), (1, [(1, None, "cost")]))
        doc["capability_sets"] = []  # without the set, cost is not owed
        self.assertEqual(self.check(doc)[0], 0)

    def test_two_capability_sets_share_a_function_without_double_counting(self):
        doc = load("platform-managed-cloud.json")
        doc["capability_sets"] = ["managed-cloud", "vps-dedicated"]
        code, out = self.check(doc)
        self.assertEqual(code, 1)
        self.assertNotIn("capacity", [v["function"] for v in out["violations"]])  # capacity is in both sets and is listed
        self.assertIn("os-lifecycle", [v["function"] for v in out["violations"]])
        self.assertEqual(out["checked"]["must_hold"].count("capacity"), 1)


class OptionalFunctions(Base):
    def test_absent_optional_function_passes_and_is_reported(self):
        code, out = cc.execute(["check", "--catalogue", os.path.join(FIXTURES, "shared-valid-no-mail.json")])
        self.assertEqual((code, out["checked"]["optional_absent"], out["checked"]["optional_present"]), (0, ["mail"], []))

    def test_present_optional_function_needs_one_accountable_party(self):
        doc = load("shared-valid-no-mail.json")
        doc["services"][0]["functions"].append({"function": "mail", "accountable": "fixture-co", "responsible": ["fixture-co"]})
        code, out = self.check(doc)
        self.assertEqual((code, out["checked"]["optional_present"]), (0, ["mail"]))
        doc["services"][1]["functions"].append({"function": "mail", "accountable": "customer", "responsible": ["customer"]})
        code, out = self.check(doc)
        self.assertEqual((code, self.rules(out)), (1, [(1, None, "mail")]))


class Rule2MustNotHold(Base):
    def test_reseller_cannot_be_accountable_for_hardware(self):
        doc = load("reseller-valid.json")
        e = self.entry(doc, "upstream-capacity", "hardware")
        e["accountable"], e["responsible"] = "fixture-co", ["fixture-co"]
        code, out = self.check(doc)
        self.assertEqual((code, self.rules(out)), (1, [(2, "upstream-capacity", "hardware")]))

    def test_every_affiliate_must_not_hold_function_is_refused_for_the_company(self):
        for fn in ("infrastructure", "accounts", "backups", "restores", "incident-response"):
            doc = load("affiliate-valid.json")
            e = self.entry(doc, "provider-hosting", fn)
            e["accountable"] = "fixture-co"
            self.assertEqual(self.rules(self.check(doc)[1]), [(2, "provider-hosting", fn)], fn)

    def test_the_company_cannot_be_responsible_for_a_must_not_hold_function_either(self):
        doc = load("affiliate-valid.json")
        self.entry(doc, "provider-hosting", "backups")["responsible"] = ["fixture-co"]
        self.assertEqual(self.rules(self.check(doc)[1]), [(2, "provider-hosting", "backups")])

    def test_an_affiliate_holds_nothing_beyond_referral(self):
        for fn in ("disaster-recovery", "restoration", "databases", "network", "storage", "os-lifecycle", "redundancy"):
            doc = load("affiliate-valid.json")
            self.entry(doc, "provider-hosting", "backups")  # the service exists
            next(s for s in doc["services"] if s["id"] == "provider-hosting")["functions"].append(
                {"function": fn, "accountable": "fixture-co", "responsible": ["fixture-co"]})
            code, out = self.check(doc)
            self.assertEqual((code, [v["name"] for v in out["violations"]]), (1, ["beyond-referral"]), fn)

    def test_the_company_named_as_its_own_upstream_is_still_the_company(self):
        """Major 5: upstream:fixture-co accountable for affiliate infrastructure passed with 0 violations."""
        doc = load("affiliate-valid.json")
        functions = ("infrastructure", "accounts", "backups", "restores", "incident-response")
        doc["parties"].append("upstream:fixture-co")
        svc = doc["services"][0]
        svc["functions"] += [{"function": f, "accountable": "upstream:fixture-co"} for f in functions]
        svc.setdefault("upstream_dependencies", []).append({"provider": "fixture-co", "obligations": ["run it"], "escalation_path": ["ops"]})
        code, out = self.check(doc)
        self.assertEqual(code, 1)
        got = {(v["name"], v["function"]) for v in out["violations"] if v["rule"] == 2}
        for f in functions:
            self.assertTrue(got & {("beyond-referral", f), ("must-not-hold", f)}, f)
        doc = load("affiliate-valid.json")
        doc["parties"].append("upstream:fixture-co")
        doc["services"][0]["functions"].append({"function": "backups", "accountable": "customer", "responsible": ["upstream:fixture-co"]})
        code, out = self.check(doc)
        self.assertIn("backups", [v["function"] for v in out["violations"] if v["rule"] == 2])

    def test_an_affiliate_cannot_declare_a_capability_set(self):
        doc = load("affiliate-valid.json")
        doc["capability_sets"] = ["vps-dedicated"]
        self.assertIn("beyond-referral", [v["name"] for v in self.check(doc)[1]["violations"]])


class Rule3UpstreamDependency(Base):
    def test_missing_dependency_entry_is_a_violation(self):
        doc = load("reseller-valid.json")
        doc["services"][1]["upstream_dependencies"] = []
        code, out = self.check(doc)
        self.assertEqual(code, 1)
        self.assertEqual({v["rule"] for v in out["violations"]}, {3})
        self.assertIn("no upstream_dependencies entry", out["violations"][0]["message"])

    def test_dependency_in_another_service_does_not_count(self):
        doc = load("reseller-valid.json")
        doc["services"][0]["upstream_dependencies"] = doc["services"][1]["upstream_dependencies"]
        doc["services"][1]["upstream_dependencies"] = []
        self.assertEqual(self.check(doc)[0], 1)

    def test_empty_obligations_and_blank_escalation_are_violations(self):
        for key, value in (("obligations", []), ("escalation_path", [""]), ("escalation_path", ["  "])):
            doc = load("reseller-valid.json")
            doc["services"][1]["upstream_dependencies"][0][key] = value
            code, out = self.check(doc)
            self.assertEqual(code, 1, (key, value))
            self.assertIn(key, out["violations"][0]["message"])


class Rule3Placeholders(Base):
    def test_placeholder_escalation_and_obligations_are_empty(self):
        doc = load("affiliate-valid.json")
        dep = doc["services"][1]["upstream_dependencies"][0]
        dep["escalation_path"], dep["obligations"] = ["TBD"], ["none"]
        code, out = self.check(doc)
        self.assertEqual((code, {v["rule"] for v in out["violations"]}), (1, {3}))


class Rule4CustomerVisibleLimits(Base):
    def limit_violations(self, mutate):
        doc = load("shared-valid-no-mail.json")
        mutate(doc["services"][0]["customer_visible_limits"])
        code, out = self.check(doc)
        self.assertEqual(code, 1)
        self.assertEqual({v["rule"] for v in out["violations"]}, {4})
        return out["violations"]

    def test_non_numeric_value_is_a_violation(self):
        got = self.limit_violations(lambda lims: lims[0].update(value="unlimited"))
        self.assertIn('"unlimited"', got[0]["message"])

    def test_boolean_value_is_not_a_number(self):
        self.limit_violations(lambda lims: lims[0].update(value=True))

    def test_nan_and_negative_values_are_violations(self):
        self.limit_violations(lambda lims: lims[0].update(value=float("nan")))
        self.limit_violations(lambda lims: lims[0].update(value=-30))

    def test_missing_or_blank_unit_is_a_violation(self):
        self.limit_violations(lambda lims: lims[0].pop("unit"))
        self.limit_violations(lambda lims: lims[1].update(unit=" "))

    def test_quotas_holder_without_a_limit_is_a_violation(self):
        got = self.limit_violations(lambda lims: lims.clear())
        self.assertEqual((got[0]["service"], got[0]["function"]), ("shared-accounts", "quotas"))

    def test_a_service_without_quotas_may_list_no_limits(self):
        doc = load("shared-valid-no-mail.json")
        doc["services"][1]["customer_visible_limits"] = []
        self.assertEqual(self.check(doc)[0], 0)


class Rule5InvalidInput(Base):
    def assert_invalid(self, doc, text):
        code, out = self.check(doc)
        self.assertEqual(code, 2, out)
        self.assertIn(text, out["error"])

    def test_company_must_be_fixture_co(self):
        doc = load("affiliate-valid.json")
        doc["company"] = "some-other-co"
        self.assert_invalid(doc, "company must be fixture-co")

    def test_unknown_function_id(self):
        doc = load("shared-valid-no-mail.json")
        doc["services"][0]["functions"].append({"function": "telepathy", "accountable": "fixture-co", "responsible": []})
        self.assert_invalid(doc, "unknown function id 'telepathy'")

    def test_unknown_or_non_hosting_profile(self):
        for profile in ("vps", "agency"):
            doc = load("shared-valid-no-mail.json")
            doc["profile"] = profile
            self.assert_invalid(doc, "not a hosting profile")

    def test_unknown_capability_set(self):
        doc = load("platform-managed-cloud.json")
        doc["capability_sets"] = ["quantum"]
        self.assert_invalid(doc, "unknown capability set")

    def test_undeclared_or_malformed_party(self):
        doc = load("affiliate-valid.json")
        self.entry(doc, "referral-program", "eligibility")["responsible"] = ["upstream:other-host"]
        self.assert_invalid(doc, "not declared in parties")
        doc = load("affiliate-valid.json")
        doc["parties"].append("Some Person")
        self.assert_invalid(doc, "must be fixture-co, customer or upstream")

    def test_accountable_must_be_one_string_party(self):
        doc = load("shared-valid-no-mail.json")
        self.entry(doc, "shared-accounts", "dns")["accountable"] = ["fixture-co", "customer"]
        self.assert_invalid(doc, "is not declared in parties")

    def test_invalid_json_missing_file_and_missing_flag(self):
        self.assert_invalid("{broken", "not valid JSON")
        self.assertEqual(cc.execute(["check", "--catalogue", os.path.join(self.dir, "nope.json")])[0], 2)
        self.assertEqual(cc.execute(["check"])[0], 2)
        self.assertEqual(cc.execute(["matrix", "--catalogue", self.write(load("affiliate-valid.json")), "--format", "pdf"])[0], 2)

    def test_duplicate_service_id_and_non_list_services(self):
        doc = load("shared-valid-no-mail.json")
        doc["services"][1]["id"] = doc["services"][0]["id"]
        self.assert_invalid(doc, "unique kebab-case slug")
        doc = load("shared-valid-no-mail.json")
        doc["services"] = {"shared-accounts": {}}
        self.assert_invalid(doc, "'services' must be a non-empty list")

    def test_malformed_dependency(self):
        doc = load("reseller-valid.json")
        doc["services"][1]["upstream_dependencies"][0]["obligations"] = "run the servers"
        self.assert_invalid(doc, "must be a list")

    def registry_is(self, doc):
        """The rig registry changes: repoint the module's fixed path to an edited copy."""
        self.addCleanup(setattr, cc, "DEFAULT_PROFILES", cc.DEFAULT_PROFILES)
        cc.DEFAULT_PROFILES = self.write(doc, "profiles.json")

    def test_a_caller_profiles_file_is_refused(self):
        catalogue = self.write(load("affiliate-valid.json"))
        code, out = cc.execute(["check", "--catalogue", catalogue, "--profiles", os.path.join(self.dir, "none.json")])
        self.assertEqual((code, out["refusal"]), (1, "profiles-not-registry-file"))
        self.assertEqual(cc.execute(["check", "--catalogue", catalogue, "--profiles", cc.DEFAULT_PROFILES])[0], 0)

    def test_registry_problems_are_invalid_input(self):
        catalogue = self.write(load("affiliate-valid.json"))
        self.registry_is({"profiles": [{"id": "affiliate", "kind": "hosting", "name": "A", "responsible_for": [], "not_responsible_for": []}]})
        code, out = cc.execute(["check", "--catalogue", catalogue])
        self.assertEqual(code, 2)
        self.assertIn("lacks hosting profiles", out["error"])

    def test_a_profile_without_function_coverage_is_invalid_input_not_a_crash(self):
        """Minor 5: an extra hosting profile in the profiles file gave a KeyError traceback."""
        registry = json.load(open(cc.DEFAULT_PROFILES))
        registry["profiles"].append({"id": "colo", "kind": "hosting", "name": "Colocation", "responsible_for": [], "not_responsible_for": []})
        self.registry_is(registry)
        doc = load("reseller-valid.json")
        doc["profile"] = "colo"
        for cmd in ("check", "matrix"):
            code, out = cc.execute([cmd, "--catalogue", self.write(doc)])
            self.assertEqual(code, 2, cmd)
            self.assertIn("function coverage", out["error"])


class MatrixOutput(Base):
    def test_json_output_has_one_row_per_function_entry_and_a_markdown_table(self):
        code, out = cc.execute(["matrix", "--catalogue", os.path.join(FIXTURES, "reseller-valid.json")])
        self.assertEqual(code, 0)
        doc = load("reseller-valid.json")
        self.assertEqual(len(out["rows"]), sum(len(s["functions"]) for s in doc["services"]))
        self.assertIn("| Service | Function | Accountable | Responsible |", out["markdown"])
        self.assertIn("| upstream-capacity | hardware | upstream:example-upstream | upstream:example-upstream |", out["markdown"])
        self.assertIn("| reseller-packages | delegated-access | fixture-co | fixture-co, customer |", out["markdown"])

    def test_markdown_format_prints_raw_markdown_with_limits_and_dependencies(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = cc.main(["matrix", "--catalogue", os.path.join(FIXTURES, "reseller-valid.json"), "--format", "markdown"])
        text = buf.getvalue()
        self.assertEqual(code, 0)
        self.assertTrue(text.startswith("# Responsibility matrix: fixture-co, Hosting reseller or white-label (reseller)"))
        self.assertIn("## Customer-visible limits", text)
        self.assertIn("| reseller-packages | disk-per-account | 10 | GB |", text)
        self.assertIn("## Upstream dependencies", text)
        self.assertIn("Fixture Co reseller support tier 2 role > Upstream reseller desk", text)

    def test_matrix_describes_and_does_not_judge(self):
        code, out = cc.execute(["matrix", "--catalogue", os.path.join(FIXTURES, "affiliate-backups-accountable.json")])
        self.assertEqual(code, 0)
        self.assertNotIn("verdict", out)

    def test_matrix_rejects_invalid_input_and_escapes_pipes(self):
        self.assertEqual(cc.execute(["matrix", "--catalogue", self.write("{broken")])[0], 2)
        doc = load("affiliate-valid.json")
        doc["services"][0]["customer_visible_limits"][0]["name"] = "window|days"
        _, out = cc.execute(["matrix", "--catalogue", self.write(doc)])
        self.assertIn("window\\|days", out["markdown"])

    def test_capability_sets_are_listed(self):
        _, out = cc.execute(["matrix", "--catalogue", os.path.join(FIXTURES, "platform-managed-cloud.json")])
        self.assertIn("Capability sets: managed-cloud", out["markdown"])


if __name__ == "__main__":
    unittest.main()
