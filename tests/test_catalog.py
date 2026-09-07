import json
import tempfile
import unittest
from brew2port.catalog import definitions_for, load_catalog

class TestCatalog(unittest.TestCase):
    def test_loads_confident_and_near_hit_relationships(self):
        data={"relations":[
            {"source":{"manager":"homebrew","package_type":"formula","native_name":"node"},"target":{"manager":"macports","package_type":"port","native_name":"nodejs26"},"confidence":1.0,"matching_method":"curated","review_status":"automatic"},
            {"source":{"manager":"homebrew","package_type":"formula","native_name":"ansible@12"},"target":{"manager":"macports","package_type":"port","native_name":"py313-ansible"},"confidence":0.78,"matching_method":"version-family","review_status":"needs-review"},
        ]}
        with tempfile.NamedTemporaryFile(mode="w") as handle:
            json.dump(data,handle); handle.flush(); table=load_catalog(handle.name)
        self.assertEqual(table[("formula","node")]["candidates"][0]["port"],"nodejs26")
        self.assertEqual(table[("formula","ansible@12")]["candidates"][0]["catalog_status"],"needs-review")

    def test_shared_core_contract_is_preserved(self):
        relation = {
            "source": {"manager": "homebrew", "package_type": "formula", "native_name": "ansible@12"},
            "target": {"manager": "macports", "package_type": "port", "native_name": "py313-ansible"},
            "type": "equivalent", "confidence": 0.78,
            "matching_method": "version-family", "review_status": "needs-review",
            "evidence": [{"kind": "version-family", "value": "ansible"}],
            "source_catalog_versions": {"homebrew": "homebrew-api", "macports": "macports-portindex"},
        }
        class Result:
            returncode = 0
            stderr = ""
            stdout = json.dumps({"catalog_version": "catalog-test", "results": [relation]})
        table = definitions_for([{"kind": "formula", "name": "ansible@12"}], run=lambda *a, **k: Result())
        record = table[("formula", "ansible@12")]["shared_record"]
        candidate = record["candidates"][0]
        self.assertEqual(record["catalog_version"], "catalog-test")
        self.assertEqual(candidate["relation_type"], "equivalent")
        self.assertEqual(candidate["review_status"], "needs-review")
        self.assertEqual(candidate["evidence"][0]["value"], "ansible")
        self.assertEqual(candidate["source_catalog_versions"]["macports"], "macports-portindex")

    def test_negative_relations_are_not_candidates(self):
        relation = {
            "source": {"manager": "homebrew", "package_type": "cask", "native_name": "macs-fan-control"},
            "target": {"manager": "macports", "package_type": "port", "native_name": "qmail-spamcontrol"},
            "type": "no-equivalent", "confidence": 1.0,
            "matching_method": "curated", "review_status": "automatic",
            "evidence": [{"kind": "curated-negative"}],
        }
        class Result:
            returncode = 0
            stderr = ""
            stdout = json.dumps({"catalog_version": "catalog-test", "results": [relation]})
        table = definitions_for([{"kind": "cask", "name": "macs-fan-control"}], run=lambda *a, **k: Result())
        self.assertEqual(table[("cask", "macs-fan-control")]["candidates"], [])
        self.assertIsNone(table[("cask", "macs-fan-control")]["shared_record"]["recommendation"])
