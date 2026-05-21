"""
InterLock AI — Streamlit Review Console
4-page app: Upload | Extracted Claims | Discrepancy Review | Audit Report
"""

import os
import json
import requests
import streamlit as st

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "../sample_pdfs")

st.set_page_config(page_title="InterLock AI", layout="wide")

# --- Session state init ---
if "uploaded_docs" not in st.session_state:
    st.session_state.uploaded_docs = []  # list of {id, filename, doc_type, page_count}

# --- Sidebar nav ---
page = st.sidebar.radio(
    "Navigation",
    ["Upload", "Extracted Claims", "Discrepancy Review", "Audit Report"],
)
st.sidebar.markdown("---")
st.sidebar.caption(f"Backend: {API_BASE}")


def severity_badge(sev: str) -> str:
    colors = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
    return f"{colors.get(sev, '⚪')} {sev}"


def method_badge(method: str) -> str:
    badges = {
        "text": "🟢 text",
        "table": "🔵 table",
        "text+table": "🔵 text+table",
        "ocr": "🟠 ocr",
    }
    return badges.get(method, method)


def confidence_color(conf: float) -> str:
    if conf > 0.85:
        return "green"
    elif conf >= 0.65:
        return "orange"
    return "red"


# ==============================================================================
# PAGE 1 — Upload
# ==============================================================================
if page == "Upload":
    st.title("InterLock AI — Review Console")
    st.subheader("Upload Engineering Documents")

    col1, col2 = st.columns([3, 1])
    with col1:
        uploaded_files = st.file_uploader(
            "Upload PDF documents", type=["pdf"], accept_multiple_files=True
        )
    with col2:
        st.markdown("####")
        use_samples = st.button("Use Sample PDFs")

    # Doc type selectors per file
    file_configs = []
    if uploaded_files:
        st.markdown("**Set document type for each file:**")
        for uf in uploaded_files:
            c1, c2 = st.columns([2, 1])
            with c1:
                st.text(uf.name)
            with c2:
                dtype = st.selectbox(
                    "Type",
                    ["owner_spec", "control_spec", "vendor_submittal", "unknown"],
                    key=f"dtype_{uf.name}",
                )
            file_configs.append((uf, dtype))

    # Sample PDF loading
    if use_samples:
        sample_files = [f for f in os.listdir(SAMPLE_DIR) if f.endswith(".pdf")]
        if not sample_files:
            st.warning("No sample PDFs found. Run: python sample_pdfs/download_samples.py")
        else:
            st.info(f"Found {len(sample_files)} sample PDFs: {', '.join(sample_files)}")
            sample_configs = []
            for fname in sample_files:
                guess = "vendor_submittal" if "caterpillar" in fname.lower() else "owner_spec"
                sample_configs.append((fname, guess))

            if st.button("Upload Sample PDFs"):
                rows = []
                for fname, dtype in sample_configs:
                    fpath = os.path.join(SAMPLE_DIR, fname)
                    with open(fpath, "rb") as f:
                        resp = requests.post(
                            f"{API_BASE}/documents/upload",
                            files={"file": (fname, f, "application/pdf")},
                            params={"doc_type": dtype},
                        )
                    if resp.ok:
                        doc = resp.json()
                        st.session_state.uploaded_docs.append(doc)
                        rows.append({"filename": doc["filename"], "doc_type": dtype,
                                     "pages": doc.get("page_count", "?"), "status": "✓ Uploaded"})
                    else:
                        rows.append({"filename": fname, "doc_type": dtype,
                                     "pages": "?", "status": f"✗ {resp.status_code}"})
                st.dataframe(rows, use_container_width=True)

    # Upload button for user-selected files
    if file_configs:
        if st.button("Upload Documents", type="primary"):
            rows = []
            for uf, dtype in file_configs:
                resp = requests.post(
                    f"{API_BASE}/documents/upload",
                    files={"file": (uf.name, uf.getvalue(), "application/pdf")},
                    params={"doc_type": dtype},
                )
                if resp.ok:
                    doc = resp.json()
                    st.session_state.uploaded_docs.append(doc)
                    rows.append({
                        "filename": doc["filename"],
                        "doc_type": dtype,
                        "pages": doc.get("page_count", "?"),
                        "status": "✓ Uploaded",
                    })
                else:
                    rows.append({
                        "filename": uf.name,
                        "doc_type": dtype,
                        "pages": "?",
                        "status": f"✗ Error {resp.status_code}",
                    })
            st.dataframe(rows, use_container_width=True)

    # Current documents table
    if st.session_state.uploaded_docs:
        st.markdown("---")
        st.markdown("**Documents in session:**")
        st.dataframe(
            [{"id": d["id"], "filename": d["filename"], "doc_type": d["doc_type"],
              "pages": d.get("page_count", "?")} for d in st.session_state.uploaded_docs],
            use_container_width=True,
        )


# ==============================================================================
# PAGE 2 — Extracted Claims
# ==============================================================================
elif page == "Extracted Claims":
    st.title("Extracted Claims")

    if not st.session_state.uploaded_docs:
        st.info("Upload documents first.")
        st.stop()

    doc_options = {f"{d['filename']} ({d['id']})": d["id"] for d in st.session_state.uploaded_docs}
    selected_label = st.selectbox("Select document", list(doc_options.keys()))
    doc_id = doc_options[selected_label]

    claim_type_filter = st.selectbox(
        "Filter by claim type", ["All", "parameter", "assumption", "reference", "checklist"]
    )

    resp = requests.get(f"{API_BASE}/documents/{doc_id}/claims")
    if not resp.ok:
        st.error(f"Failed to fetch claims: {resp.status_code}")
        st.stop()

    claims = resp.json()
    if claim_type_filter != "All":
        claims = [c for c in claims if c["claim_type"] == claim_type_filter]

    if not claims:
        st.warning(
            "No claims found. "
            "Claims are populated when you run analysis — go to **Discrepancy Review** and click **Run Analysis** first, then return here."
        )
        st.stop()

    st.markdown(f"**{len(claims)} claims**")

    for c in claims:
        conf = c["confidence"]
        color = confidence_color(conf)
        with st.expander(
            f"{method_badge(c['extraction_method'])}  |  **{c['parameter_name']}**  =  "
            f"`{c['value_normalized'] or c['value_raw']}` {c.get('unit') or ''}  "
            f"  page {c['page_number']}  conf: :{color}[{conf:.0%}]"
        ):
            st.markdown(f"**entity:** `{c['entity']}`")
            st.markdown(f"**claim_type:** `{c['claim_type']}`")
            st.markdown(f"**value_raw:** `{c['value_raw']}`")
            if c.get("condition"):
                st.markdown(f"**condition:** {c['condition']}")
            st.markdown("**source text:**")
            st.code(c["source_text"], language=None)


# ==============================================================================
# PAGE 3 — Discrepancy Review
# ==============================================================================
elif page == "Discrepancy Review":
    st.title("Discrepancy Review")

    if len(st.session_state.uploaded_docs) < 2:
        st.info("Upload at least 2 documents to run analysis.")
        st.stop()

    doc_ids = [d["id"] for d in st.session_state.uploaded_docs]
    doc_name = {d["id"]: d["filename"] for d in st.session_state.uploaded_docs}

    if st.button("Run Analysis", type="primary"):
        with st.spinner("Extracting claims and comparing documents..."):
            resp = requests.post(f"{API_BASE}/analysis/run", json=doc_ids)
        if resp.ok:
            result = resp.json()
            st.success(
                f"Analysis complete — {result['claims_extracted']} claims extracted, "
                f"{result['discrepancies_found']} discrepancies found "
                f"({result['high_count']} HIGH, {result['medium_count']} MEDIUM, {result['low_count']} LOW)"
            )
        else:
            st.error(f"Analysis failed: {resp.text}")
            st.stop()

    # Fetch discrepancies
    resp = requests.get(f"{API_BASE}/discrepancies")
    if not resp.ok:
        st.error("Failed to fetch discrepancies.")
        st.stop()

    all_discs = resp.json()
    if not all_discs:
        st.info("No discrepancies found yet. Run analysis first.")
        st.stop()

    # Summary metrics
    high_n   = sum(1 for d in all_discs if d["severity"] == "HIGH")
    medium_n = sum(1 for d in all_discs if d["severity"] == "MEDIUM")
    low_n    = sum(1 for d in all_discs if d["severity"] == "LOW")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Flags", len(all_discs))
    m2.metric("HIGH", high_n)
    m3.metric("MEDIUM", medium_n)
    m4.metric("LOW", low_n)

    # Filter chips
    filter_type = st.radio(
        "Filter by type",
        ["All", "PARAMETER_MISMATCH", "ASSUMPTION_MISMATCH", "REFERENCE_GAP", "CHECKLIST_GAP"],
        horizontal=True,
    )

    discs = all_discs if filter_type == "All" else [d for d in all_discs if d["mismatch_type"] == filter_type]

    # Sort HIGH → MEDIUM → LOW
    sev_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    discs = sorted(discs, key=lambda d: sev_order.get(d["severity"], 3))

    st.markdown(f"**Showing {len(discs)} flags**")
    st.markdown("---")

    for disc in discs:
        sev = disc["severity"]
        mtype = disc["mismatch_type"]
        conf = disc["confidence"]

        border_color = {"HIGH": "#ff4444", "MEDIUM": "#ffaa00", "LOW": "#44aa44"}.get(sev, "#888")

        with st.container():
            st.markdown(
                f"<div style='border-left: 4px solid {border_color}; padding-left: 12px; margin-bottom: 8px;'>"
                f"<b>{severity_badge(sev)}</b> &nbsp; <code>{mtype}</code> &nbsp; confidence: {conf:.0%}"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.markdown(f"**{disc['summary']}**")

            ca = disc.get("claim_a")
            cb = disc.get("claim_b")

            if ca:
                ca_name = doc_name.get(ca.get("document_id", ""), ca.get("document_id", ""))
                st.markdown(
                    f"**Document A says:**  \n> \"{ca['source_text']}\"  \n"
                    f"*Source: {ca_name} · page {ca['page_number']} · "
                    f"extracted via {ca['extraction_method']}*"
                )
            if cb:
                cb_name = doc_name.get(cb.get("document_id", ""), cb.get("document_id", ""))
                st.markdown(
                    f"**Document B says:**  \n> \"{cb['source_text']}\"  \n"
                    f"*Source: {cb_name} · page {cb['page_number']} · "
                    f"extracted via {cb['extraction_method']}*"
                )
            else:
                st.markdown("**Document B:** *Absent from vendor submittal*")

            if disc.get("explanation"):
                st.info(f"**Review note:** {disc['explanation']}")

            st.markdown("---")


# ==============================================================================
# PAGE 4 — Audit Report
# ==============================================================================
elif page == "Audit Report":
    st.title("Audit Report")

    if not st.session_state.uploaded_docs:
        st.info("Upload and analyze documents first.")
        st.stop()

    doc_ids = [d["id"] for d in st.session_state.uploaded_docs]

    # Summary table
    resp = requests.get(f"{API_BASE}/discrepancies")
    if resp.ok:
        all_discs = resp.json()
        high_n   = sum(1 for d in all_discs if d["severity"] == "HIGH")
        medium_n = sum(1 for d in all_discs if d["severity"] == "MEDIUM")
        low_n    = sum(1 for d in all_discs if d["severity"] == "LOW")

        st.markdown("**Audit Summary**")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Flags", len(all_discs))
        c2.metric("HIGH", high_n)
        c3.metric("MEDIUM", medium_n)
        c4.metric("LOW", low_n)

        st.markdown("**Documents:**")
        st.dataframe(
            [{"id": d["id"], "filename": d["filename"], "type": d["doc_type"],
              "pages": d.get("page_count", "?")} for d in st.session_state.uploaded_docs],
            use_container_width=True,
        )

    # Download buttons
    col1, col2 = st.columns(2)
    with col1:
        params = "&".join(f"document_ids={did}" for did in doc_ids)
        json_resp = requests.get(f"{API_BASE}/audit/json?{params}")
        if json_resp.ok:
            st.download_button(
                "Download JSON Report",
                data=json_resp.content,
                file_name="audit_report.json",
                mime="application/json",
            )

    with col2:
        pdf_resp = requests.get(f"{API_BASE}/audit/pdf?{params}")
        if pdf_resp.ok:
            st.download_button(
                "Download PDF Report",
                data=pdf_resp.content,
                file_name="audit_report.pdf",
                mime="application/pdf",
            )

    # Raw JSON viewer
    if json_resp.ok:
        with st.expander("Raw JSON (collapsible)"):
            try:
                st.json(json_resp.json())
            except Exception:
                st.code(json_resp.text)
