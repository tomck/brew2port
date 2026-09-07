"""Branch metamacpkg-db: catalog-backed matching (not on main)."""
import csv, tempfile, unittest
from pathlib import Path
from brew2port.core import candidates, make_plan
from brew2port.metamacpkg_db import load, lookup


def write_catalog(tmp):
    d = Path(tmp)
    with open(d / "brew-formula-to-macports.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source", "target", "confidence", "method",
                    "status", "evidence", "alternatives"])
        w.writerow(["gtk+3", "gtk3", "0.96", "normalized",
                    "confident", "fold", ""])
        w.writerow(["git-svn", "", "0.0", "none", "missing",
                    "no port", "gitsign"])
        w.writerow(["node", "", "0.0", "ambiguous", "needs-review",
                    "several", "ode"])
        w.writerow(["stale-tool", "gone-port", "1.0", "exact",
                    "confident", "old", ""])
        w.writerow(["ansible@12", "py313-ansible", "0.73", "near-hit",
                    "near-hit", "1 major newer", "py312-ansible"])
        w.writerow(["stale-near", "gone-port", "0.73", "near-hit",
                    "near-hit", "old", ""])
    (d / "brew-cask-to-macports.csv").write_text(
        "source,target,confidence,method,status,evidence,alternatives\n")
    return str(d)


class TestCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.cat = load(write_catalog(cls.tmp.name))
        cls.ports = [{"name": n} for n in
                     ("gtk3", "gitsign", "ode", "nodejs", "git")]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_confident_catalog_row_wins(self):
        cs = candidates({"name": "gtk+3", "kind": "formula"},
                        self.ports, catalog=self.cat)
        self.assertEqual([(c["port"], c["reason"]) for c in cs],
                         [("gtk3", "metamacpkg:normalized")])

    def test_missing_suppresses_fuzzy(self):
        # Without the catalog, git-svn fuzzy-matches gitsign; with the
        # catalog's missing verdict there must be no candidates at all.
        without = candidates({"name": "git-svn", "kind": "formula"},
                             self.ports)
        self.assertTrue(any(c["port"] == "gitsign" for c in without))
        self.assertEqual(candidates({"name": "git-svn", "kind": "formula"},
                                    self.ports, catalog=self.cat), [])

    def test_needs_review_falls_back_filtered(self):
        # Local matching still runs, but weak heuristics are suppressed:
        # ode (0.857) must not survive for node under catalog review.
        ports = self.ports + [{"name": "nodejs24"}]
        cs = candidates({"name": "node", "kind": "formula"},
                        ports, catalog=self.cat)
        self.assertFalse(any(c["port"] == "ode" for c in cs))
        self.assertFalse(any(c["reason"].startswith("metamacpkg")
                             for c in cs))

    def test_needs_review_keeps_strong_tiers(self):
        ports = self.ports + [{"name": "node"}]
        cs = candidates({"name": "node", "kind": "formula"},
                        ports, catalog=self.cat)
        self.assertEqual(cs[0]["port"], "node")  # exact still passes

    def test_stale_target_not_trusted(self):
        cs = candidates({"name": "stale-tool", "kind": "formula"},
                        self.ports, catalog=self.cat)
        self.assertFalse(any(c["port"] == "gone-port" for c in cs))

    def test_plan_uses_catalog(self):
        plan = make_plan([{"name": "gtk+3", "kind": "formula"},
                          {"name": "git-svn", "kind": "formula"}],
                         self.ports, catalog=self.cat)
        self.assertEqual(plan[0]["candidates"][0]["port"], "gtk3")
        self.assertEqual(plan[1]["candidates"], [])

    def test_no_catalog_unchanged(self):
        cs = candidates({"name": "gtk+3", "kind": "formula"}, self.ports)
        self.assertTrue(cs)

    def test_near_hit_offered_not_forced(self):
        ports = self.ports + [{"name": "py313-ansible"}]
        cs = candidates({"name": "ansible@12", "kind": "formula"},
                        ports, catalog=self.cat)
        self.assertEqual([(c["port"], c["reason"]) for c in cs],
                         [("py313-ansible", "metamacpkg:near-hit")])
        # Below the 0.8 auto-install line: offered for review, never
        # installed without a human decision.
        from brew2port.core import install
        plan = make_plan([{"name": "ansible@12", "kind": "formula"}],
                         ports, catalog=self.cat)
        self.assertEqual(install(plan)[0]["status"], "needs-review")

    def test_near_hit_preview_lists_port_for_review(self):
        from brew2port.core import write_preview_csv
        ports = self.ports + [{"name": "py313-ansible"}]
        plan = make_plan([{"name": "ansible@12", "kind": "formula"}],
                         ports, catalog=self.cat)
        with tempfile.NamedTemporaryFile("r+", suffix=".csv") as f:
            write_preview_csv(plan, f.name)
            with open(f.name, newline="") as rf:
                rows = list(csv.DictReader(rf))
        self.assertEqual(rows[0]["recommended_port"], "py313-ansible")
        self.assertEqual(rows[0]["review_status"], "needs-review")

    def test_stale_near_hit_falls_back(self):
        cs = candidates({"name": "stale-near", "kind": "formula"},
                        self.ports, catalog=self.cat)
        self.assertFalse(any(c["reason"].startswith("metamacpkg")
                             for c in cs))

    def test_url_source_and_version(self):
        import tempfile
        from pathlib import Path as P
        from brew2port import metamacpkg_db as mdb
        tmp = tempfile.TemporaryDirectory()
        (P(tmp.name) / "brew-formula-to-macports.csv").write_text(
            "source,target,confidence,method,status,evidence,alternatives,"
            "catalog_version\n"
            "gtk+3,gtk3,0.96,normalized,confident,fold,,v20260906+abc123\n")
        (P(tmp.name) / "brew-cask-to-macports.csv").write_text(
            "source,target,confidence,method,status,evidence,alternatives,"
            "catalog_version\n")
        cat = mdb.load("file://" + tmp.name)
        cs = candidates({"name": "gtk+3", "kind": "formula"},
                        [{"name": "gtk3"}], catalog=cat)
        self.assertEqual(cs[0]["port"], "gtk3")
        self.assertEqual(cs[0]["catalog_version"], "v20260906+abc123")
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
