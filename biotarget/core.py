"""Open Targets API client and transparent evidence summarization.

This is a research prototype, NOT a validated drug-discovery or medical tool.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

API_URL = "https://api.platform.opentargets.org/api/v4/graphql"

SEARCH_QUERY = """
query SearchDiseases($term: String!) {
  search(queryString: $term, entityNames: ["disease"]) {
    hits { id name }
  }
}
"""

TARGETS_QUERY = """
query AssociatedTargets($efoId: String!, $index: Int!, $size: Int!) {
  disease(efoId: $efoId) {
    id
    name
    associatedTargets(page: {index: $index, size: $size}) {
      count
      rows {
        score
        target { id approvedSymbol approvedName }
        datatypeScores { id score }
      }
    }
  }
}
"""


class OpenTargetsError(RuntimeError):
    """Network, API or data-validation issue."""


def graphql(query: str, variables: dict[str, Any], *, post=None) -> dict[str, Any]:
    """POST a single GraphQL request; network errors become actionable exceptions."""
    send = post if post is not None else requests.post
    try:
        response = send(API_URL, json={"query": query, "variables": variables}, timeout=30)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise OpenTargetsError(f"Open Targets API request failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise OpenTargetsError("Open Targets returned an unexpected payload.")
    if payload.get("errors"):
        raise OpenTargetsError(f"Open Targets GraphQL errors: {payload['errors']}")
    if not isinstance(payload.get("data"), dict):
        raise OpenTargetsError("Open Targets did not return a data object.")
    return payload["data"]


def search_diseases(term: str, *, post=None) -> list[dict[str, str]]:
    if not term.strip():
        raise ValueError("Provide a non-empty disease search term.")
    data = graphql(SEARCH_QUERY, {"term": term.strip()}, post=post)
    return [
        {"id": str(hit["id"]), "name": str(hit["name"])}
        for hit in (data.get("search") or {}).get("hits", [])
        if isinstance(hit, dict) and hit.get("id") and hit.get("name")
    ]


def choose_exact_disease(term: str, hits: list[dict[str, str]]) -> dict[str, str]:
    """Never silently select a potentially wrong disease from fuzzy results."""
    exact = [hit for hit in hits if hit["name"].casefold().strip() == term.casefold().strip()]
    if len(exact) == 1:
        return exact[0]
    labels = ", ".join(f"{h['name']} ({h['id']})" for h in hits[:8])
    raise OpenTargetsError(
        f"No unique exact disease match for '{term}'. Candidates: {labels or 'none'}. "
        "Use --disease-id after checking the correct ontology term in Open Targets."
    )


def fetch_associations(disease_id: str, *, limit: int = 50, post=None) -> tuple[str, list[dict[str, Any]]]:
    """Return Open Targets' existing ranked disease-target association rows."""
    if not disease_id.strip():
        raise ValueError("Missing disease ontology ID.")
    if not 1 <= limit <= 500:
        raise ValueError("limit must be 1 to 500 to prevent accidental bulk API use.")
    rows: list[dict[str, Any]] = []
    disease_name = ""
    page = 0
    while len(rows) < limit:
        size = min(100, limit - len(rows))
        data = graphql(TARGETS_QUERY, {"efoId": disease_id, "index": page, "size": size}, post=post)
        disease = data.get("disease")
        if not disease:
            raise OpenTargetsError(f"Disease ID '{disease_id}' was not found by Open Targets.")
        disease_name = str(disease.get("name") or disease_id)
        association = disease.get("associatedTargets") or {}
        batch = association.get("rows") or []
        if not isinstance(batch, list):
            raise OpenTargetsError("Unexpected rows shape from API.")
        rows.extend(batch)
        if not batch or len(rows) >= int(association.get("count") or 0):
            break
        page += 1
    return disease_name, rows[:limit]


def summarize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Explainable evidence table: no independent discovery score is invented."""
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        target = row.get("target") or {}
        if not target.get("id") or not target.get("approvedSymbol"):
            continue
        evidence = {
            str(item["id"]): float(item["score"])
            for item in (row.get("datatypeScores") or [])
            if isinstance(item, dict) and item.get("id")
            and isinstance(item.get("score"), (int, float))
        }
        score = row.get("score")
        if not isinstance(score, (int, float)):
            continue
        normalized.append({
            "gene": target["approvedSymbol"],
            "ensembl_id": target["id"],
            "description": target.get("approvedName") or "",
            "association_score": round(float(score), 5),
            "genetic_evidence": round(evidence.get("genetic_association", 0.0), 5),
            "somatic_evidence": round(evidence.get("somatic_mutation", 0.0), 5),
            "known_drug_evidence": round(evidence.get("known_drug", 0.0), 5),
            "evidence_categories": sum(x > 0 for x in evidence.values()),
            "all_datatype_scores": json.dumps(evidence, sort_keys=True),
            "target_url": f"https://platform.opentargets.org/target/{target['id']}",
        })
    return sorted(normalized, key=lambda r: (-r["association_score"], r["gene"]))


def save_results(folder: str | Path, *, name: str, disease_id: str, rows: list[dict[str, Any]],
                 source: str = "live") -> tuple[Path, Path]:
    path = Path(folder)
    path.mkdir(parents=True, exist_ok=True)
    csv_path, manifest_path = path / "targets.csv", path / "manifest.json"
    columns = ["gene", "ensembl_id", "description", "association_score", "genetic_evidence",
               "somatic_evidence", "known_drug_evidence", "evidence_categories",
               "all_datatype_scores", "target_url"]
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    manifest_path.write_text(json.dumps({
        "disease_name": name,
        "disease_id": disease_id,
        "records": len(rows),
        "source": source,
        "source_api": API_URL if source == "live" else "synthetic demonstration fixture",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "ranking": "Existing Open Targets disease-target association score (not a new AI model)",
        "limitations": "Exploratory only; not clinically validated; missing categories are not proof of no evidence.",
    }, indent=2) + "\n", encoding="utf-8")
    return csv_path, manifest_path


def load_demo(path: str | Path | None = None) -> tuple[str, str, list[dict[str, Any]]]:
    if path is None:
        path = Path(__file__).resolve().parent.parent / "sample_data" / "demo_api_response.json"
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    disease = data["data"]["disease"]
    return disease["name"], disease["id"], disease["associatedTargets"]["rows"]
