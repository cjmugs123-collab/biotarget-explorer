import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
import requests
from biotarget.core import (OpenTargetsError, choose_exact_disease, fetch_associations,
                            graphql, load_demo, save_results, search_diseases, summarize_rows)


def fake_post(data):
    resp = Mock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"data": data}
    return Mock(return_value=resp)


class TestExplorer(unittest.TestCase):
    def test_search(self):
        post = fake_post({"search": {"hits": [{"id": "EFO_X", "name": "Cancer"}]}})
        self.assertEqual(search_diseases("Cancer", post=post)[0]["id"], "EFO_X")
        self.assertEqual(post.call_args.kwargs["timeout"], 30)

    def test_exact_selection_prevents_fuzzy_misclassification(self):
        self.assertEqual(choose_exact_disease("cancer", [{"id": "1", "name": "Cancer"}])["id"], "1")
        with self.assertRaises(OpenTargetsError):
            choose_exact_disease("cancer", [{"id": "1", "name": "Lung cancer"}])

    def test_api_error(self):
        resp = Mock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"errors": [{"message": "bad field"}]}
        with self.assertRaises(OpenTargetsError):
            graphql("query", {}, post=Mock(return_value=resp))

    def test_http_error(self):
        resp = Mock()
        resp.raise_for_status.side_effect = requests.HTTPError("503")
        with self.assertRaises(OpenTargetsError):
            graphql("query", {}, post=Mock(return_value=resp))

    def test_fetch_pagination(self):
        calls = []
        def post(url, json, timeout):
            calls.append(json["variables"])
            page = json["variables"]["index"]
            batch = [{"target":{"id":f"g{page}","approvedSymbol":f"G{page}"},"score":0.4}]
            return fake_post({"disease":{"name":"Cancer","associatedTargets":{"count":2,"rows":batch}}})()
        name, rows = fetch_associations("EFO_X", limit=2, post=post)
        self.assertEqual(name, "Cancer")
        self.assertEqual(len(rows), 2)
        self.assertEqual([c["index"] for c in calls], [0, 1])

    def test_demo_evidence_and_order(self):
        name, disease_id, raw = load_demo()
        self.assertTrue(name.startswith("SYNTHETIC"))
        rows = summarize_rows(raw)
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["gene"], "DEMO_A")
        self.assertEqual(rows[0]["evidence_categories"], 2)
        self.assertEqual(rows[3]["known_drug_evidence"], 0)

    def test_csv_and_provenance(self):
        name, disease_id, raw = load_demo()
        with tempfile.TemporaryDirectory() as d:
            csvfile, manifest = save_results(d, name=name, disease_id=disease_id,
                rows=summarize_rows(raw), source="synthetic-demo")
            self.assertTrue(csvfile.exists())
            record = json.loads(manifest.read_text())
            self.assertEqual(record["records"], 4)
            self.assertEqual(record["source"], "synthetic-demo")
            self.assertEqual(len(csvfile.read_text().splitlines()), 5)

    def test_limit_guard(self):
        with self.assertRaises(ValueError):
            fetch_associations("ID", limit=501)


if __name__ == "__main__":
    unittest.main()
