import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "dns_cert.py")
FIX = os.path.normpath(os.path.join(HERE, "..", "..", "..", "company-fleets", "fleets", "hosting", "fixtures", "dns-cert"))
NOW = "2026-11-25T00:00:00Z"
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "company-fleets", "fleets", "hosting", "tools")))
import mirror  # noqa: E402


def fx(name):
    return os.path.join(FIX, name)


def run(*args, script=SCRIPT):
    proc = subprocess.run([sys.executable, "-I", script] + list(args), capture_output=True, text=True)
    try:
        doc = json.loads(proc.stdout)
    except ValueError:
        doc = None
    return proc.returncode, doc


class TempMixin(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, name, content):
        path = os.path.join(self.tmp.name, name)
        with open(path, "w") as fh:
            fh.write(content if isinstance(content, str) else json.dumps(content))
        return path

    def zone(self, records, **extra):
        doc = {"origin": "tenant-a.example", "records": records}
        doc.update(extra)
        return self.write("zone.json", doc)

    def owner_script(self, hosts):
        """A mirror of the rig whose owner decommissioned.json lists these hosts; returns its script path."""
        root = mirror.make(tempfile.mkdtemp(dir=self.tmp.name))
        with open(mirror.fixtures(root, "dns-cert", "decommissioned.json"), "w") as fh:
            json.dump({"label": "SYNTHETIC: test owner list", "hosts": hosts}, fh)
        return mirror.script(root, "hosting-dns-cert-lifecycle", "dns_cert.py")


def rec(name, rtype, value, ttl=3600):
    return {"name": name, "type": rtype, "ttl": ttl, "value": value}


def rules(doc):
    return [v["rule"] for v in doc["violations"]]


class ZoneFixtures(unittest.TestCase):
    def test_valid_zone_passes(self):
        code, doc = run("zone-check", "--zone", fx("zone-valid.json"))
        self.assertEqual((code, doc["verdict"], doc["violations"]), (0, "pass", []))
        self.assertTrue(doc["assumptions"])

    def test_apex_cname(self):
        code, doc = run("zone-check", "--zone", fx("zone-apex-cname.json"))
        self.assertEqual(code, 1)
        self.assertIn("apex-cname", rules(doc))

    def test_dangling_cname(self):
        code, doc = run("zone-check", "--zone", fx("zone-dangling-cname.json"), "--decommissioned", fx("decommissioned.json"))
        self.assertEqual((code, rules(doc)), (1, ["dangling-record"]))
        self.assertEqual(doc["violations"][0]["name"], "www.tenant-a.example")

    def test_the_owner_list_is_read_without_a_flag_and_a_caller_list_is_refused(self):
        """Minor 7: without --decommissioned the dangling check didn't run; a caller list could also leave hosts out."""
        code, doc = run("zone-check", "--zone", fx("zone-dangling-cname.json"))
        self.assertEqual((code, rules(doc)), (1, ["dangling-record"]))
        with tempfile.TemporaryDirectory() as tmp:
            empty = os.path.join(tmp, "none.json")
            with open(empty, "w") as fh:
                json.dump({"hosts": ["nothing.example"]}, fh)
            code, doc = run("zone-check", "--zone", fx("zone-dangling-cname.json"), "--decommissioned", empty)
        self.assertEqual((code, doc["refusal"]), (1, "decommissioned-not-owner-file"))

    def test_two_spf(self):
        code, doc = run("zone-check", "--zone", fx("zone-two-spf.json"))
        self.assertEqual((code, rules(doc)), (1, ["multiple-spf"]))

    def test_caa_blocks_issuer(self):
        code, doc = run("zone-check", "--zone", fx("zone-caa-blocks-issuer.json"))
        self.assertEqual((code, rules(doc)), (1, ["caa-blocks-issuer"]))

    def test_an_issuer_flag_is_refused(self):
        """Major 1: --issuer evil-ca.example turned caa-blocks-issuer into pass."""
        for zone in ("zone-caa-own-issuer.json", "zone-caa-blocks-issuer.json"):
            code, doc = run("zone-check", "--zone", fx(zone), "--issuer", "evil-ca.example")
            self.assertEqual((code, doc["refusal"]), (1, "issuer-not-owner-file"), zone)
        code, doc = run("zone-check", "--zone", fx("zone-caa-own-issuer.json"))
        self.assertEqual((code, rules(doc)), (1, ["caa-blocks-issuer"]))

    def test_high_ttl_before_change(self):
        args = ("zone-check", "--zone", fx("zone-high-ttl.json"), "--changes", fx("changes-www-cutover.json"))
        code, doc = run(*args, "--now", "2026-11-30T13:00:00Z")
        self.assertEqual((code, rules(doc)), (1, ["ttl-before-change"]))


class ZoneRules(TempMixin):
    def check(self, records, *extra, **zone_extra):
        return run("zone-check", "--zone", self.zone(records, **zone_extra), *extra)

    def test_cname_sharing_its_name_with_other_data(self):
        code, doc = self.check([rec("blog", "CNAME", "edge.platform.example."), rec("blog", "TXT", "hello")])
        self.assertEqual((code, rules(doc)), (1, ["cname-conflict"]))

    def test_two_cnames_at_one_name(self):
        code, doc = self.check([rec("blog", "CNAME", "a.platform.example."), rec("blog", "CNAME", "b.platform.example.")])
        self.assertEqual((code, rules(doc)), (1, ["cname-conflict"]))

    def test_dnssec_records_may_sit_beside_a_cname(self):
        code, doc = self.check([rec("blog", "CNAME", "a.platform.example."), rec("blog", "RRSIG", "sig")])
        self.assertEqual(code, 0)

    def test_mx_target_is_a_cname(self):
        code, doc = self.check([rec("@", "MX", "10 mail.tenant-a.example."), rec("mail", "CNAME", "mx.provider.example.")])
        self.assertEqual((code, rules(doc)), (1, ["mx-target-cname"]))

    def test_alias_at_apex_is_allowed_with_a_warning(self):
        code, doc = self.check([rec("@", "ALIAS", "edge.platform.example.")])
        self.assertEqual(code, 0)
        self.assertIn("alias-is-provider-specific", [w["rule"] for w in doc["warnings"]])

    def test_subdomain_of_a_decommissioned_host_is_dangling(self):
        script = self.owner_script(["old.platform.example."])
        code, doc = run("zone-check", "--zone", self.zone([rec("www", "CNAME", "x.old.platform.example.")]), script=script)
        self.assertEqual((code, rules(doc)), (1, ["dangling-record"]))

    def test_alias_to_decommissioned_host_is_dangling(self):
        script = self.owner_script(["old.platform.example"])
        code, doc = run("zone-check", "--zone", self.zone([rec("@", "ALIAS", "old.platform.example.")]), script=script)
        self.assertEqual((code, rules(doc)), (1, ["dangling-record"]))

    def test_a_u_label_entry_catches_its_punycode_target_and_the_reverse(self):
        """Minor 7: bücher.example and xn--bcher-kva.example are one host."""
        for listed, target in (("bücher.example", "shop.xn--bcher-kva.example."), ("xn--bcher-kva.example", "shop.Bücher.example.")):
            script = self.owner_script([listed])
            code, doc = run("zone-check", "--zone", self.zone([rec("www", "CNAME", target)]), script=script)
            self.assertEqual((code, rules(doc)), (1, ["dangling-record"]), (listed, target))

    def test_an_ipv4_mapped_aaaa_record_matches_the_released_ipv4(self):
        """Minor 7: AAAA ::ffff:198.51.100.7 is the decommissioned 198.51.100.7."""
        code, doc = self.check([rec("@", "A", "192.0.2.10"), rec("v6", "AAAA", "::ffff:198.51.100.7")])
        self.assertEqual((code, rules(doc)), (1, ["dangling-record"]))

    def test_caa_without_issue_tag_does_not_block(self):
        code, doc = self.check([rec("@", "CAA", '0 iodef "mailto:security@tenant-a.example"')], issuer="ca.fixture-co.test")
        self.assertEqual(code, 0)

    def test_caa_with_parameters_still_permits(self):
        code, doc = self.check([rec("@", "CAA", '0 issue "ca.fixture-co.test; account=1"')], issuer="ca.fixture-co.test")
        self.assertEqual(code, 0)

    def test_caa_empty_issue_blocks_everyone(self):
        code, doc = self.check([rec("@", "CAA", '0 issue ";"')], issuer="ca.fixture-co.test")
        self.assertEqual((code, rules(doc)), (1, ["caa-blocks-issuer"]))

    def test_zone_cannot_name_its_own_issuer(self):
        code, doc = self.check([rec("@", "CAA", '0 issue "evil-ca.example"')], issuer="evil-ca.example")
        self.assertEqual((code, rules(doc)), (1, ["caa-blocks-issuer"]))
        self.assertIn("zone-issuer-ignored", [w["rule"] for w in doc["warnings"]])

    def dangling(self, *records):
        """The owner's decommissioned.json lists tenant-a-old.platform.example, ns1.old-dns.example and 198.51.100.7."""
        return self.check([rec("@", "A", "192.0.2.10")] + list(records))

    def test_undotted_cname_to_decommissioned_host_is_dangling(self):
        code, doc = self.dangling(rec("www", "CNAME", "tenant-a-old.platform.example"))
        self.assertEqual((code, rules(doc)), (1, ["dangling-record"]))
        self.assertIn("target-without-trailing-dot", [w["rule"] for w in doc["warnings"]])

    def test_mx_ns_and_address_to_decommissioned_hosts_are_dangling(self):
        for record in (rec("@", "MX", "10 tenant-a-old.platform.example."), rec("dev", "NS", "ns1.old-dns.example."),
                       rec("old", "A", "198.51.100.7"), rec("v6", "AAAA", "2001:db8::1")):
            code, doc = self.dangling(record)
            expected = (0, []) if record["type"] == "AAAA" else (1, ["dangling-record"])
            self.assertEqual((code, rules(doc)), expected, record)

    def test_apex_named_by_origin_without_dot_is_the_apex(self):
        code, doc = self.check([rec("tenant-a.example", "CNAME", "edge.platform.example.")])
        self.assertEqual((code, rules(doc)), (1, ["apex-cname"]))

    def test_in_zone_target_with_no_records(self):
        code, doc = self.check([rec("@", "A", "192.0.2.10"), rec("www", "CNAME", "gone")])
        self.assertEqual((code, rules(doc)), (1, ["missing-target"]))

    def test_cutover_from_a_to_cname_checks_the_a_ttl(self):
        zone = self.zone([rec("www", "A", "192.0.2.11", 86400)])
        changes = self.write("changes.json", {"changes": [{"name": "www", "type": "CNAME", "at": "2026-12-01T12:00:00Z"}]})
        code, doc = run("zone-check", "--zone", zone, "--changes", changes, "--now", "2026-12-01T00:00:00Z")
        self.assertEqual((code, rules(doc)), (1, ["ttl-before-change"]))

    def test_change_types_are_trimmed_and_case_folded_before_the_ttl_rule(self):
        """Major 8: "CNAME " and " cname" skipped the TTL rule."""
        zone = self.zone([rec("www", "A", "192.0.2.11", 86400)])
        for rtype in ("CNAME", "CNAME ", " cname", "Cname\t"):
            changes = self.write("changes.json", {"changes": [{"name": "www", "type": rtype, "at": "2026-12-01T12:00:00Z"}]})
            code, doc = run("zone-check", "--zone", zone, "--changes", changes, "--now", "2026-12-01T00:00:00Z")
            self.assertEqual((code, rules(doc)), (1, ["ttl-before-change"]), repr(rtype))
        changes = self.write("changes.json", {"changes": [{"name": "www", "type": "CNAMEX", "at": "2026-12-01T12:00:00Z"}]})
        self.assertEqual(run("zone-check", "--zone", zone, "--changes", changes, "--now", "2026-12-01T00:00:00Z")[0], 2)

    def test_unknown_type_and_huge_ttl_are_invalid_input(self):
        self.assertEqual(self.check([rec("x", "FOO", "bar")])[0], 2)
        self.assertEqual(self.check([rec("@", "A", "192.0.2.10", 2 ** 40)])[0], 2)
        self.assertEqual(self.check([rec("@", "A", "not-an-ip")])[0], 2)

    def change_args(self, at, ttl=3600):
        zone = self.zone([rec("www", "A", "192.0.2.10", ttl)])
        changes = self.write("changes.json", {"changes": [{"name": "www", "type": "A", "at": at}]})
        return ("zone-check", "--zone", zone, "--changes", changes, "--now", "2026-11-25T00:00:00Z")

    def test_change_exactly_48_hours_out_is_in_the_window(self):
        code, doc = run(*self.change_args("2026-11-27T00:00:00Z"))
        self.assertEqual((code, rules(doc)), (1, ["ttl-before-change"]))

    def test_change_just_past_48_hours_is_outside(self):
        code, doc = run(*self.change_args("2026-11-27T00:00:01Z"))
        self.assertEqual(code, 0)

    def test_ttl_of_exactly_300_passes(self):
        code, doc = run(*self.change_args("2026-11-26T00:00:00Z", ttl=300))
        self.assertEqual(code, 0)

    def test_ttl_of_301_fails(self):
        code, doc = run(*self.change_args("2026-11-26T00:00:00Z", ttl=301))
        self.assertEqual(code, 1)

    def test_change_in_the_past_is_ignored(self):
        code, doc = run(*self.change_args("2026-11-24T00:00:00Z"))
        self.assertEqual(code, 0)


class ZoneInvalidInput(TempMixin):
    def test_non_utf8_zone_exits_2_with_a_named_reason(self):
        path = os.path.join(self.tmp.name, "z.json")
        with open(path, "wb") as fh:
            fh.write(b"\xff\xfe{}")
        code, doc = run("zone-check", "--zone", path)
        self.assertEqual(code, 2)
        self.assertIn("not valid JSON", doc["error"])

    def test_invalid_json(self):
        code, doc = run("zone-check", "--zone", self.write("z.json", "{not json"))
        self.assertEqual(code, 2)
        self.assertIn("error", doc)

    def test_missing_file(self):
        code, doc = run("zone-check", "--zone", os.path.join(self.tmp.name, "nope.json"))
        self.assertEqual(code, 2)

    def test_missing_records(self):
        code, doc = run("zone-check", "--zone", self.write("z.json", {"origin": "tenant-a.example"}))
        self.assertEqual(code, 2)

    def test_record_without_ttl(self):
        code, doc = run("zone-check", "--zone", self.zone([{"name": "@", "type": "A", "value": "192.0.2.1"}]))
        self.assertEqual(code, 2)

    def test_negative_ttl(self):
        code, doc = run("zone-check", "--zone", self.zone([rec("@", "A", "192.0.2.1", -1)]))
        self.assertEqual(code, 2)

    def test_malformed_mx(self):
        code, doc = run("zone-check", "--zone", self.zone([rec("@", "MX", "mail.tenant-a.example.")]))
        self.assertEqual(code, 2)

    def test_malformed_caa(self):
        code, doc = run("zone-check", "--zone", self.zone([rec("@", "CAA", "issue")]))
        self.assertEqual(code, 2)

    def test_changes_without_now(self):
        code, doc = run("zone-check", "--zone", fx("zone-valid.json"), "--changes", fx("changes-www-cutover.json"))
        self.assertEqual(code, 2)

    def test_bad_now(self):
        code, doc = run("zone-check", "--zone", fx("zone-valid.json"), "--changes", fx("changes-www-cutover.json"), "--now", "tomorrow")
        self.assertEqual(code, 2)


class CertCheck(TempMixin):
    def cert(self, name, host, now=NOW, *extra):
        return run("cert-check", "--cert", fx(name), "--host", host, "--now", now, *extra)

    def test_valid_apex_and_www(self):
        for host in ("tenant-a.example", "www.tenant-a.example", "WWW.Tenant-A.example."):
            code, doc = self.cert("tenant-a-apex.pem", host)
            self.assertEqual((code, doc["status"]), (0, "valid"), host)
        self.assertEqual(doc["days_left"], 51.0)

    def test_name_mismatch(self):
        code, doc = self.cert("tenant-a-other.pem", "www.tenant-a.example")
        self.assertEqual((code, doc["status"]), (1, "name-mismatch"))

    def test_wildcard_covers_one_label_only(self):
        cases = {"x.tenant-a.example": "valid", "tenant-a.example": "name-mismatch", "y.x.tenant-a.example": "name-mismatch"}
        for host, status in cases.items():
            code, doc = self.cert("tenant-a-wildcard.pem", host)
            self.assertEqual(doc["status"], status, host)
            self.assertEqual(code, 0 if status == "valid" else 1)

    def test_wildcard_over_a_single_label_matches_nothing(self):
        sys.path.insert(0, os.path.dirname(SCRIPT))
        import dns_cert
        self.assertFalse(dns_cert.name_matches("tenant-a.example", "*.example"))
        self.assertTrue(dns_cert.name_matches("x.tenant-a.example", "*.tenant-a.example"))

    def test_wildcard_host_matches_its_own_san_text(self):
        code, doc = self.cert("tenant-a-wildcard.pem", "*.tenant-a.example")
        self.assertEqual(doc["status"], "valid")

    def test_expiry_boundary_is_renew_at_exactly_30_days(self):
        code, doc = self.cert("tenant-a-apex.pem", "tenant-a.example", "2026-12-16T00:00:00Z")
        self.assertEqual((code, doc["status"], doc["days_left"]), (1, "renew", 30.0))

    def test_one_second_outside_the_window_is_valid(self):
        code, doc = self.cert("tenant-a-apex.pem", "tenant-a.example", "2026-12-15T23:59:59Z")
        self.assertEqual((code, doc["status"]), (0, "valid"))

    def test_warn_days_is_configurable(self):
        code, doc = self.cert("tenant-a-apex.pem", "tenant-a.example", NOW, "--warn-days", "60")
        self.assertEqual((code, doc["status"]), (1, "renew"))

    def test_expired_at_not_after_instant(self):
        code, doc = self.cert("tenant-a-apex.pem", "tenant-a.example", "2027-01-15T00:00:00Z")
        self.assertEqual((code, doc["status"]), (1, "expired"))

    def test_not_yet_valid(self):
        code, doc = self.cert("tenant-a-apex.pem", "tenant-a.example", "2026-09-30T00:00:00Z")
        self.assertEqual((code, doc["status"]), (1, "not-yet-valid"))

    def test_mismatch_outranks_expiry_but_both_are_listed(self):
        code, doc = self.cert("tenant-a-other.pem", "www.tenant-a.example", "2027-06-01T00:00:00Z")
        self.assertEqual(doc["status"], "name-mismatch")
        self.assertEqual(doc["problems"], ["name-mismatch", "expired"])

    def test_openssl_cli_fallback_agrees(self):
        _, a = self.cert("tenant-a-apex.pem", "www.tenant-a.example")
        _, b = self.cert("tenant-a-apex.pem", "www.tenant-a.example", NOW, "--parser", "openssl")
        self.assertEqual(a["parser"], "ssl._ssl._test_decode_cert")
        self.assertEqual(b["parser"], "openssl x509")
        for key in ("status", "days_left", "sans", "not_after"):
            self.assertEqual(a[key], b[key], key)

    def test_invalid_pem_exits_2(self):
        bad = self.write("bad.pem", "-----BEGIN CERTIFICATE-----\nbm90IGEgY2VydA==\n-----END CERTIFICATE-----\n")
        for parser in ("auto", "openssl"):
            code, doc = run("cert-check", "--cert", bad, "--host", "a.example", "--now", NOW, "--parser", parser)
            self.assertEqual(code, 2, parser)
            self.assertIn("error", doc)

    def test_text_without_a_certificate_exits_2(self):
        code, doc = run("cert-check", "--cert", self.write("t.pem", "hello"), "--host", "a.example", "--now", NOW)
        self.assertEqual(code, 2)

    def test_private_key_file_is_refused(self):
        # Built from parts so the published file carries no literal private-key header.
        key = self.write("k.pem", "-----BEGIN " + "PRIVATE KEY-----\nQUJD\n-----END " + "PRIVATE KEY-----\n")
        code, doc = run("cert-check", "--cert", key, "--host", "a.example", "--now", NOW)
        self.assertEqual(code, 2)
        self.assertIn("private key", doc["error"])

    def test_missing_cert_bad_now_bad_host_negative_warn_days(self):
        gone = os.path.join(self.tmp.name, "gone.pem")
        self.assertEqual(run("cert-check", "--cert", gone, "--host", "a.example", "--now", NOW)[0], 2)
        self.assertEqual(run("cert-check", "--cert", fx("tenant-a-apex.pem"), "--host", "a.example", "--now", "soon")[0], 2)
        self.assertEqual(run("cert-check", "--cert", fx("tenant-a-apex.pem"), "--host", "a b", "--now", NOW)[0], 2)
        self.assertEqual(run("cert-check", "--cert", fx("tenant-a-apex.pem"), "--host", "a.example", "--now", NOW, "--warn-days", "-1")[0], 2)

    def test_fixtures_hold_no_private_key(self):
        for name in os.listdir(FIX):
            with open(fx(name), encoding="utf-8") as fh:
                self.assertNotIn("PRIVATE KEY", fh.read(), name)


class RenewalPlan(TempMixin):
    def test_lists_due_certificates_sorted_by_days_left_with_owner(self):
        code, doc = run("renewal-plan", "--inventory", fx("inventory.json"), "--now", NOW)
        self.assertEqual(code, 1)
        self.assertEqual([d["id"] for d in doc["due"]], ["tenant-a-legacy", "tenant-a-mail"])
        self.assertEqual([d["owner_role"] for d in doc["due"]], ["platform-engineer", "mail-operator"])
        self.assertEqual([d["status"] for d in doc["due"]], ["expired", "renew"])
        self.assertEqual(doc["ok_count"], 2)

    def test_nothing_due_exits_0(self):
        code, doc = run("renewal-plan", "--inventory", fx("inventory.json"), "--now", "2026-10-01T00:00:00Z")
        self.assertEqual((code, doc["verdict"], doc["due"]), (0, "ok", []))

    def test_due_but_not_expired_exits_0(self):
        code, doc = run("renewal-plan", "--inventory", fx("inventory.json"), "--now", "2026-11-19T00:00:00Z")
        self.assertEqual((code, doc["verdict"]), (0, "renew"))
        self.assertEqual([d["id"] for d in doc["due"]], ["tenant-a-legacy", "tenant-a-mail"])

    def test_exactly_warn_days_is_due(self):
        inv = self.write("inv.json", {"certificates": [{"id": "c", "host": "a.example", "owner_role": "r", "not_after": "2026-12-25T00:00:00Z"}]})
        code, doc = run("renewal-plan", "--inventory", inv, "--now", NOW)
        self.assertEqual([d["status"] for d in doc["due"]], ["renew"])

    def test_invalid_inventory_exits_2(self):
        self.assertEqual(run("renewal-plan", "--inventory", self.write("i.json", "[]"), "--now", NOW)[0], 2)
        self.assertEqual(run("renewal-plan", "--inventory", self.write("i.json", {"certificates": [{"id": "c"}]}), "--now", NOW)[0], 2)
        self.assertEqual(run("renewal-plan", "--inventory", self.write("i.json", "{oops"), "--now", NOW)[0], 2)
        self.assertEqual(run("renewal-plan", "--inventory", fx("inventory.json"), "--now", "never")[0], 2)


if __name__ == "__main__":
    unittest.main()
