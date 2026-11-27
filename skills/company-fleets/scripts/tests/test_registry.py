"""Milestone 1: registry validation, selective resolution, coverage and role scaffolding."""
import json
import os
import subprocess
import tempfile
import unittest

from support import SKILL, edit, make_root, messages, read

from fleetlib.checks import coverage, validate
from fleetlib.registry import Registry
from fleetlib.resolve import ResolveError, resolve
from fleetlib.scaffold import ScaffoldError, new_role
from fleetlib.schema import SchemaError, Schemas

ROLES = "fleets/agency/roles.json"
EVALS = "fleets/agency/evals.json"
SPECIALIST = 1  # index of agency.accessibility-specialist in the sample roles


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.reg = make_root(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def assertRejects(self, reg, fragment, fleet=None):
        result = validate(reg, fleet)
        self.assertFalse(result["ok"], "expected a rejection containing %r" % fragment)
        self.assertTrue(any(fragment in m for m in messages(result)), messages(result))


class ShippedRegistry(unittest.TestCase):
    def test_empty_fleets_validate(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = validate(make_root(tmp, sample=False))
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["counts"]["fleets"], 9)
        self.assertEqual(result["counts"]["profiles"], 11)

    def test_profiles_cover_the_hosting_ladder_and_business_profiles(self):
        ids = {p["id"] for p in json.load(open(os.path.join(SKILL, "registry", "profiles.json")))["profiles"]}
        self.assertTrue({"affiliate", "reseller", "shared", "managed", "platform", "enterprise",
                         "agency", "product", "devrel", "community", "school"} <= ids)

    def test_company_is_a_labeled_fixture(self):
        company = json.load(open(os.path.join(SKILL, "registry", "company.json")))
        self.assertIs(company["fixture"], True)
        self.assertIn("FIXTURE", company["label"])
        self.assertEqual(company["name"], "Fixture Co")


class Validation(Base):
    def test_sample_registry_is_valid_without_warnings(self):
        result = validate(self.reg)
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["warnings"], [])
        self.assertEqual(result["counts"]["roles"], 6)

    def test_schema_rejects_missing_field_unknown_field_and_bad_namespace(self):
        def mutate(doc):
            del doc["roles"][SPECIALIST]["voice"]
            doc["roles"][SPECIALIST]["persona_bio"] = "twenty years at a famous firm"
            doc["roles"][0]["id"] = "hosting.engagement-coordinator"
        reg = edit(self.reg, ROLES, mutate)
        msgs = messages(validate(reg))
        self.assertTrue(any("missing required field 'voice'" in m for m in msgs), msgs)
        self.assertTrue(any("unknown field 'persona_bio'" in m for m in msgs), msgs)
        self.assertTrue(any("must start with 'agency.'" in m for m in msgs), msgs)

    def test_no_role_may_dispatch(self):
        reg = edit(self.reg, ROLES, lambda d: d["roles"][0].update(dispatch=True))
        self.assertRejects(reg, "/roles/0/dispatch: must be false")

    def test_second_coordinator_in_a_fleet_is_refused(self):
        reg = edit(self.reg, ROLES, lambda d: d["roles"][SPECIALIST].update(kind="coordinator"))
        self.assertRejects(reg, "competing coordinators")

    def test_attached_skill_must_exist_or_be_blocked_with_a_reason(self):
        def mutate(doc):
            doc["roles"][SPECIALIST]["skills"].append({"id": "no-such-skill", "provenance": "local"})
        self.assertRejects(edit(self.reg, ROLES, mutate), "attaches skill no-such-skill")

        def blocked(doc):
            doc["roles"][SPECIALIST]["skills"][-1]["blocked_reason"] = "Upstream source not pinned yet"
        self.assertTrue(validate(edit(self.reg, ROLES, blocked))["ok"])

    def test_producer_cannot_accept_or_review_its_own_output(self):
        def mutate(doc):
            rel = doc["roles"][SPECIALIST]["relations"]
            rel["acceptor"] = "agency.accessibility-specialist"
            rel["reviewers"] = ["agency.accessibility-specialist"]
        result = validate(edit(self.reg, ROLES, mutate))
        msgs = messages(result)
        self.assertTrue(any("accepts its own output" in m for m in msgs), msgs)
        self.assertTrue(any("reviews its own output" in m for m in msgs), msgs)

    def test_every_role_needs_a_defined_evaluation_case(self):
        self.assertRejects(edit(self.reg, ROLES, lambda d: d["roles"][0].update(evals=[])), "needs at least 1 item")
        reg = edit(self.reg, ROLES, lambda d: d["roles"][0].update(evals=["agency.eval.does-not-exist"]))
        self.assertRejects(reg, "agency.eval.does-not-exist")
        reg = edit(self.reg, ROLES, lambda d: d["roles"][0].update(evals=["hosting.eval.handoff-needs-restore-point"]))
        self.assertRejects(reg, "none of agency.engagement-coordinator's evaluation cases targets it")

    def test_status_claims_need_evidence_that_exists(self):
        def claim(state):
            def mutate(doc):
                doc["roles"][SPECIALIST]["verification"]["installed"] = state
            return edit(self.reg, ROLES, mutate)
        self.assertRejects(claim({"state": "installed"}), "without an evidence path")
        self.assertRejects(claim({"state": "installed", "evidence": "fleets/agency/evidence/none.txt"}), "does not exist")
        self.assertTrue(validate(claim({"state": "installed", "evidence": "fleets/agency/evidence/resolve-sample.txt"}))["ok"])

        def behavioral(doc):
            doc["roles"][SPECIALIST]["verification"]["behavioral"] = {"state": "verified"}
        self.assertRejects(edit(self.reg, ROLES, behavioral), "behavioral=verified without an evidence path")

        def any_file(doc):
            doc["roles"][SPECIALIST]["verification"]["behavioral"] = {"state": "verified", "evidence": "registry/fleets.json"}
        self.assertRejects(edit(self.reg, ROLES, any_file), "must sit under fleets/agency/evidence/")

        def no_passing_case(doc):
            doc["roles"][SPECIALIST]["verification"]["behavioral"] = {
                "state": "verified", "evidence": "fleets/agency/evidence/resolve-sample.txt"}
        self.assertRejects(edit(self.reg, ROLES, no_passing_case), "none of its eval cases has outcome pass")

        def activated(doc):
            v = doc["roles"][SPECIALIST]["verification"]
            v["installed"] = {"state": "reference-only"}
            v["behavioral"] = {"state": "unverified"}
            v["activated"] = {"state": "activated", "evidence": "fleets/agency/evidence/resolve-sample.txt"}
        self.assertRejects(edit(self.reg, ROLES, activated), "claims activated while installed is reference-only")

    def test_verified_behavior_needs_an_independent_grader_under_strict(self):
        def claim(**extra):
            def mutate(doc):
                doc["roles"][0]["verification"]["behavioral"] = dict(
                    {"state": "verified", "evidence": "fleets/agency/evidence/resolve-sample.txt"}, **extra)
            return edit(self.reg, ROLES, mutate)
        reg = claim()
        self.assertTrue(validate(reg)["ok"])
        self.assertTrue(any("without a grader" in m for m in messages(validate(reg, strict=True))))
        for builder, grader in (("Agency Workstream Agent", "human:independent-reviewer"),):
            self.assertTrue(validate(claim(grader=grader, builder=builder), strict=True)["ok"])
        same = claim(grader="human:fleet-builder", builder=" Human:Fleet-Builder ")
        self.assertTrue(any("grader is the builder" in m for m in messages(validate(same, strict=True))))
        itself = claim(grader="agency.engagement-coordinator", builder="human:fleet-builder")
        self.assertTrue(any("graded itself" in m for m in messages(validate(itself, strict=True))))
        self.assertRejects(claim(grader=" human:padded"), "does not match")

    def test_eval_pass_needs_evidence_and_skill_buckets_must_match(self):
        reg = edit(self.reg, EVALS, lambda d: d["evals"][1]["outcome"].update(status="pass"))
        self.assertRejects(reg, "reports pass without an evidence path")
        reg = edit(self.reg, EVALS, lambda d: d["evals"][2].update(kind="positive"))
        self.assertRejects(reg, "lists agency.eval.no-conformance-claim as negative but the case is positive")

    def test_workload_rules(self):
        def two_coordinators(doc):
            doc["roles"][SPECIALIST]["kind"] = "coordinator"
        self.assertRejects(edit(self.reg, ROLES, two_coordinators), "one coordinator per workload")
        self.assertRejects(edit(self.reg, ROLES, lambda d: d["workloads"][0].update(profiles=["school"])),
                           "does not activate fleet agency")
        self.assertRejects(edit(self.reg, ROLES, lambda d: d["workloads"][0]["roles"].append("agency.ghost")),
                           "unknown role agency.ghost")

    def test_every_workload_has_one_home_fleet_coordinator(self):
        def drop(doc):
            doc["workloads"][0]["roles"].remove("agency.engagement-coordinator")
        self.assertRejects(edit(self.reg, ROLES, drop), "has no coordinator")

        def foreign(doc):
            doc["workloads"][0]["roles"].append("hosting.operations-coordinator")
        self.assertRejects(edit(self.reg, ROLES, foreign), "a workload's coordinator comes from its own fleet")

    def test_unregistered_fleet_directory_and_misfiled_record(self):
        os.makedirs(self.reg.path("fleets/rogue"))
        self.assertRejects(Registry(self.reg.root, self.reg.skills_root), "fleets/rogue is not registered")
        os.rmdir(self.reg.path("fleets/rogue"))
        self.assertRejects(edit(self.reg, EVALS, lambda d: d.update(fleet="hosting")), "sits in fleets/agency")

    def test_fleet_scope_includes_breakage_this_fleet_causes_elsewhere(self):
        reg = edit(self.reg, "fleets/hosting/roles.json", lambda d: d["roles"][1].update(id="hosting.renamed-owner"))
        hosting = validate(reg, "hosting")
        self.assertFalse(hosting["ok"])
        self.assertTrue(any(e["file"] == ROLES and "hosting.support-handoff-owner" in e["message"] for e in hosting["errors"]))

    def test_fleet_scope_reports_only_that_fleets_errors(self):
        reg = edit(self.reg, "fleets/hosting/roles.json", lambda d: d["roles"][0].update(dispatch=True))
        self.assertTrue(validate(reg, "agency")["ok"])
        self.assertFalse(validate(reg, "hosting")["ok"])
        self.assertFalse(validate(reg, "nope")["ok"])

    def test_schema_loader_refuses_keywords_it_does_not_enforce(self):
        sdir = os.path.join(self.tmp.name, "schemas")
        os.makedirs(sdir)
        json.dump({"type": "array", "maxItems": 2}, open(os.path.join(sdir, "x.json"), "w"))
        with self.assertRaises(SchemaError):
            Schemas(sdir).validate([], "x.json")


class Resolution(Base):
    def test_agency_workload_reads_no_hosting_or_education_file(self):
        out = resolve(self.reg, "agency", "agency.workload.accessibility-audit")
        self.assertEqual([r["id"] for r in out["roles"]], ["agency.engagement-coordinator", "agency.accessibility-specialist"])
        self.assertEqual(out["coordinator"], "agency.engagement-coordinator")
        self.assertEqual(out["files_read"], ["registry/profiles.json", "fleets/agency/roles.json"])

    def test_no_file_is_opened_behind_the_read_log(self):
        """Patch open() itself, so a direct read that bypasses Registry.load would show up."""
        import builtins
        opened, real_open = [], builtins.open

        def spy(path, *a, **kw):
            opened.append(os.path.realpath(str(path)))
            return real_open(path, *a, **kw)
        builtins.open = spy
        try:
            out = resolve(self.reg, "agency", "agency.workload.accessibility-audit")
        finally:
            builtins.open = real_open
        logged = [os.path.realpath(self.reg.path(f)) for f in out["files_read"]]
        self.assertEqual(opened, logged)
        self.assertFalse(any(os.sep + d + os.sep in p for p in opened
                             for d in ("hosting", "bcit-education", "instructional-design", "corporate", "consultancies")))

    def test_profile_decides_whether_a_cross_fleet_role_loads(self):
        out = resolve(self.reg, "agency", "agency.workload.launch-with-hosting")
        self.assertEqual(out["excluded"], [{"id": "hosting.support-handoff-owner",
                                            "reason": "profile agency does not activate fleet hosting"}])
        self.assertNotIn("fleets/hosting/roles.json", out["files_read"])
        reg = Registry(self.reg.root, self.reg.skills_root)
        out = resolve(reg, "managed", "agency.workload.launch-with-hosting")
        self.assertIn("hosting.support-handoff-owner", [r["id"] for r in out["roles"]])
        self.assertEqual(out["files_read"], ["registry/profiles.json", "fleets/agency/roles.json", "fleets/hosting/roles.json"])

    def test_skills_are_listed_for_loading_not_read(self):
        out = resolve(self.reg, "agency", "agency.workload.accessibility-audit")
        skills = {s["id"]: s for s in out["roles"][1]["skills"]}
        self.assertTrue(skills["verification-methodology"]["installed"])
        self.assertIn("blocked_reason", skills["agency-keyboard-audit"])
        self.assertFalse(any(f.endswith("SKILL.md") for f in out["files_read"]))

    def test_resolve_refuses_unknown_or_inapplicable_requests(self):
        for profile, workload, fragment in (("nope", "agency.workload.accessibility-audit", "unknown profile"),
                                            ("school", "agency.workload.accessibility-audit", "does not activate fleet agency"),
                                            ("managed", "agency.workload.accessibility-audit", "does not apply to profile managed"),
                                            ("agency", "agency.workload.nope", "has no workload")):
            with self.assertRaises(ResolveError) as ctx:
                resolve(Registry(self.reg.root, self.reg.skills_root), profile, workload)
            self.assertIn(fragment, str(ctx.exception))


class Scaffold(Base):
    def test_new_role_writes_a_valid_skeleton_once(self):
        out = new_role(self.reg, "agency", "content-strategist")
        self.assertEqual(out["role"], "agency.content-strategist")
        reg = Registry(self.reg.root, self.reg.skills_root)
        result = validate(reg)
        self.assertTrue(result["ok"], result["errors"])
        self.assertTrue(any("TODO" in w["message"] for w in result["warnings"]))
        strict = validate(reg, "agency", strict=True)
        self.assertFalse(strict["ok"])
        self.assertTrue(any("TODO" in m for m in messages(strict)))
        before = read(reg, ROLES)
        with self.assertRaises(ScaffoldError):
            new_role(reg, "agency", "content-strategist")
        self.assertEqual(read(reg, ROLES), before)

    def test_new_coordinator_is_refused_when_the_fleet_has_one(self):
        with self.assertRaises(ScaffoldError):
            new_role(self.reg, "agency", "second-coordinator", kind="coordinator")
        new_role(self.reg, "community", "community-coordinator", kind="coordinator")
        self.assertTrue(validate(Registry(self.reg.root, self.reg.skills_root))["ok"])

    def test_rerun_after_a_crash_between_writes_reuses_the_eval(self):
        def orphan(doc):
            doc["evals"].append({"id": "agency.eval.editor-smoke", "kind": "positive", "target": "agency.engagement-coordinator",
                                 "input": "x" * 5, "expected": "y" * 5, "check": {"method": "human"}, "outcome": {"status": "not-run"}})
        reg = edit(self.reg, EVALS, orphan)
        new_role(reg, "agency", "editor")
        ids = [e["id"] for e in read(reg, EVALS)["evals"]]
        self.assertEqual(ids.count("agency.eval.editor-smoke"), 1)


class Coverage(Base):
    def test_coverage_keeps_the_four_states_apart(self):
        out = coverage(self.reg)
        agency = next(f for f in out["fleets"] if f["fleet"] == "agency")
        self.assertEqual(agency["roles"], 2)
        self.assertEqual(agency["role_states"]["installed"], {"not-installed": 1, "reference-only": 1})
        self.assertEqual(agency["attached_skills"], {"available": 2, "blocked": 1})
        self.assertEqual(agency["evals"], {"positive": 2, "negative": 1, "boundary": 1})


class Cli(Base):
    def run_cli(self, *args):
        p = subprocess.run([os.path.join(SKILL, "bin", "fleet"), "--root", self.reg.root,
                            "--skills-root", self.reg.skills_root] + list(args), capture_output=True, text=True, timeout=60)
        return p.returncode, json.loads(p.stdout)

    def test_cli_exit_codes(self):
        self.assertEqual(self.run_cli("validate")[0], 0)
        code, out = self.run_cli("resolve", "--profile", "agency", "--workload", "agency.workload.accessibility-audit")
        self.assertEqual(code, 0)
        self.assertEqual(len(out["roles"]), 2)
        code, out = self.run_cli("resolve", "--profile", "school", "--workload", "agency.workload.accessibility-audit")
        self.assertEqual(code, 1)
        self.assertIn("error", out)
        edit(self.reg, ROLES, lambda d: d["roles"][0].update(dispatch=True))
        self.assertEqual(self.run_cli("validate", "--fleet", "agency")[0], 1)


if __name__ == "__main__":
    unittest.main()
