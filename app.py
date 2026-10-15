"""Streamlit UI for inspecting Open Targets evidence (no model fitting)."""
from pathlib import Path
import pandas as pd
import streamlit as st
from biotarget.core import (OpenTargetsError, fetch_associations, load_demo,
                            search_diseases, summarize_rows)

st.set_page_config(page_title="BioTarget Explorer", page_icon="🧬", layout="wide")
st.title("🧬 BioTarget Explorer")
st.caption("Research prototype · $0 software/data · Open Targets evidence, not medical advice")
st.warning("This is a research workflow, not a validated drug-discovery or clinical prediction model.")

mode = st.radio("Data", ["Live Open Targets API", "Offline synthetic demonstration"], horizontal=True)
if mode.startswith("Offline"):
    st.error("SYNTHETIC DEMO — gene names and scores are invented for testing; do not cite as findings.")
    name, disease_id, raw = load_demo()
    st.session_state["result"] = (name, disease_id, summarize_rows(raw), "demo")
else:
    disease_query = st.text_input("Disease name", value="pancreatic ductal adenocarcinoma")
    if st.button("Find matching ontology terms"):
        try:
            st.session_state["matches"] = search_diseases(disease_query)
        except (OpenTargetsError, ValueError) as exc:
            st.error(str(exc))
    matches = st.session_state.get("matches", [])
    if matches:
        lookup = {f"{m['name']} [{m['id']}]": m for m in matches}
        chosen = lookup[st.selectbox("Choose the exact disease", list(lookup))]
        limit = st.slider("Number of targets", min_value=10, max_value=200, value=50, step=10)
        if st.button("Load disease-target evidence", type="primary"):
            try:
                name, raw = fetch_associations(chosen["id"], limit=limit)
                st.session_state["result"] = (name, chosen["id"], summarize_rows(raw), "live")
            except (OpenTargetsError, ValueError) as exc:
                st.error(str(exc))

result = st.session_state.get("result")
if result:
    name, disease_id, rows, source = result
    st.subheader(f"{name} — {len(rows)} target associations")
    st.caption(f"Disease: https://platform.opentargets.org/disease/{disease_id}")
    df = pd.DataFrame(rows)
    if df.empty:
        st.info("No results returned.")
    else:
        st.dataframe(df[["gene", "association_score", "genetic_evidence", "somatic_evidence",
                         "known_drug_evidence", "evidence_categories", "target_url"]],
                     use_container_width=True, hide_index=True)
        st.bar_chart(df.head(20).set_index("gene")["association_score"])
        st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"),
                           file_name="target_evidence.csv", mime="text/csv")
        st.info("Higher association scores mean more support in Open Targets' evidence model, "
                "not proven druggability or clinical effectiveness. Evidence categories may be missing. "
                "A drug-evidence score does not mean a target is approved for this disease.")
