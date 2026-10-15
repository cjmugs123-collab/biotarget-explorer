# BioTarget Explorer — v0.1

**Mission:** Make target–disease evidence easier to inspect and reproduce, starting with **pancreatic ductal adenocarcinoma (PDAC)**.

**Research prototype — not a diagnostic, a drug-discovery validation, or medical advice.**

## Why this specific problem?

A researcher choosing genes for follow-up experiments must reconcile several kinds of evidence. In this first iteration, we simplify finding and exporting that evidence from [Open Targets](https://platform.opentargets.org/). Later, we can compare those associations with *independent* CRISPR dependency measurements from [DepMap](https://depmap.org/portal/data_page/) and evaluate whether a learned model adds predictive value. We have **not** trained an AI model or validated any novel target yet.

## What works now

- Search Open Targets' public API for disease ontology terms, avoiding fuzzy misidentification.
- Fetch the top 1–500 disease-target association rows, with pagination.
- Display gene identifiers and association/evidence-category scores.
- Export a reproducible CSV plus a JSON provenance record (source and retrieval time).
- Run an **offline synthetic demo** without a network connection or paid accounts.
- Launch a Streamlit research UI.
- Run local automated tests with fake HTTP responses.

## Setup ($0 extra)

Install Python 3.10+ and use your own computer or a free notebook environment.

```bash
python3 -m venv .venv
source .venv/bin/activate    # Windows: .venv\\Scripts\\activate
python -m pip install -r requirements.txt
```

### 1. Test offline (no API call)

```bash
python -m unittest discover -s tests -v
python -m biotarget.cli --demo --out results/demo
```

The demo is **fabricated test data**. Do not present its scores as biological findings.

### 2. Query real Open Targets data (internet needed)

```bash
python -m biotarget.cli --disease "pancreatic ductal adenocarcinoma" --top 50 --out results/pdac
```

If no single exact ontology-term match is returned, the CLI provides candidate disease IDs. Check the correct term at Open Targets and run:

```bash
python -m biotarget.cli --disease-id YOUR_VERIFIED_ONTOLOGY_ID --top 50 --out results/pdac
```

**Important:** We have not tested the live query in this environment because external network access was unavailable. The GraphQL query follows Open Targets' published schema; if the upstream schema changes, update the query. Live network may be rate-limited.

### 3. Use the visual app

```bash
streamlit run app.py
```

Select **Live Open Targets API**, search the disease name, choose an ontology term, and load results. Use the **Offline synthetic demonstration** option to explore without the internet.

## Output explained

- `association_score`: Open Targets' *existing* disease-target association score. It is **not** a probability that a drug will work.
- `genetic_evidence`, `somatic_evidence`, `known_drug_evidence`: score summaries associated with specific evidence categories, **not independent experimental confirmations**.
- `evidence_categories`: number of returned categories with scores above zero, not a count of experimental studies.
- `target_url`: link back to Open Targets.
- `manifest.json`: retrieval metadata and explicit limitations.

A missing score should be interpreted as unavailable/not represented in the response, **not** evidence of biological absence. Known drug evidence may be a sign of a well-characterized target, not target novelty. Scores can reflect correlated evidence and should not be treated as independent measurements.

## Roadmap

**Phase 1 (implemented)** — Transparent, reproducible Open Targets evidence explorer, offline fixture and tests.

**Phase 2 (not implemented)** — Bring in DepMap's latest public CRISPR dependency data; accurately map cell-line metadata to PDAC; test overlap of evidence versus cancer-cell-essentiality. Important: dependency in vitro does not establish tumor-specific selectivity or safe druggability.

**Phase 3 (not implemented)** — Separate known targets from candidate novel targets, quantify evidence gaps, design objective labels, and train a simple baseline ML model with held-out evaluation that avoids data leakage. Compare against Open Targets-only ranking.

**Phase 4 (not implemented)** — Interview computational cancer biologists and pharma target-validation researchers to identify a narrower, valuable workflow. Re-scope based on actual feedback.

## Validation checklist

- [x] Offline demo produces an export.
- [x] Automated tests cover search, paging, errors, provenance, and scoring.
- [ ] Real live API query confirmed in a networked environment.
- [ ] Two independent scientists find the output useful.
- [ ] DepMap cancer cell-line mapping verified.
- [ ] Any model evaluated against a non-leaking hold-out and strong baseline.

## Primary sources

- Open Targets GraphQL API: https://platform-docs.opentargets.org/data-access/graphql-api
- Open Targets platform and data: https://platform.opentargets.org/
- DepMap releases: https://depmap.org/portal/data_page/

## Contribution and reproducibility

This code is MIT licensed. It is intended for a dedicated repository (create one called `biotarget-explorer`, then upload this folder). Avoid placing it inside an unrelated existing repository. If you use public scientific data commercially, review the **data provider's** own license and attribution rules rather than assuming the code's MIT license covers external data.