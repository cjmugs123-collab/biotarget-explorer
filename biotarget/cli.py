"""Command-line entry point, including a fully offline synthetic demo."""
import argparse
from .core import (OpenTargetsError, choose_exact_disease, fetch_associations,
                   load_demo, save_results, search_diseases, summarize_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Free cancer target-evidence explorer")
    parser.add_argument("--disease", default="pancreatic ductal adenocarcinoma",
                        help="Exact Open Targets disease name; use --disease-id if no exact match")
    parser.add_argument("--disease-id", help="Open Targets disease ontology ID (avoids search)")
    parser.add_argument("--top", type=int, default=50, help="Number of associations, max 500")
    parser.add_argument("--out", default="results", help="Directory for CSV and provenance JSON")
    parser.add_argument("--demo", action="store_true", help="Synthetic offline sample; NOT real findings")
    args = parser.parse_args()
    try:
        if args.demo:
            name, disease_id, raw = load_demo()
            source = "synthetic-demo"
            print("WARNING: SYNTHETIC EXAMPLE DATA. NOT BIOLOGICAL FINDINGS.")
        else:
            disease_id = args.disease_id
            if not disease_id:
                found = search_diseases(args.disease)
                matched = choose_exact_disease(args.disease, found)
                disease_id = matched["id"]
            name, raw = fetch_associations(disease_id, limit=args.top)
            source = "live"
        rows = summarize_rows(raw)
        csv_path, manifest_path = save_results(args.out, name=name, disease_id=disease_id,
                                                rows=rows, source=source)
        print(f"Disease: {name} [{disease_id}]")
        print(f"Saved {len(rows)} records: {csv_path}, {manifest_path}")
        for row in rows[:10]:
            print(f"{row['gene']:12s} score={row['association_score']:.3f} "
                  f"categories={row['evidence_categories']}")
    except (OpenTargetsError, ValueError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
