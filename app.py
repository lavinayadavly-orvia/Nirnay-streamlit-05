"""
app.py — Nirnay · CDSCO AI Hackathon 2026
------------------------------------------
Entry point. All 6 guideline-mandated features + full reviewer workflow.

HOW TO RUN:
    streamlit run app.py

FOR JUDGES:
    • The app opens on the Command Dashboard with a pre-loaded sample packet.
    • Use the LEFT SIDEBAR to switch between the two sample case packets
      or to walk through the CDSCO review workflow screens.
    • Use the TABS at the top of the main panel to access all 6 AI features.
    • Upload your own documents inside any feature tab — the AI engines
      process your real files immediately. Sample data is only a fallback.
    • All outputs (PDF, CSV, JSON, TXT) are downloadable from within each tab.

FEATURES (per CDSCO-IndiaAI Hackathon Guidelines, Section 3.I):
    01 Anonymisation     — PII/PHI detection, two-step DPDP Act 2023 process
    02 Summarisation     — SAE narration, SUGAM checklist, meeting transcripts
    03 Completeness      — Schedule Y / Form CT mandatory field assessment
    04 Classification    — SAE severity grading + duplicate detection
    05 Comparison        — Semantic document diff, substantive change flagging
    06 Inspection Report — CDSCO GCP site inspection report generator

ARCHITECTURE:
    app.py          — Main entry point (this file)
    components.py   — UI components, session state, audit trail, sidebar
    engine.py       — All processing engines (anonymisation, summarisation, etc.)
    demo_data.py    — Sample case packets (pre-loaded for evaluation)
    requirements.txt
"""

from __future__ import annotations

import datetime
import json as _json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as _cv1

from components import (
    APP_DISCLAIMER,
    CLAUDE_OK,
    SCREENS,
    add_audit_event,
    ai_recommendation_card,
    apply_redaction_filters,
    apply_styles,
    audit_dataframe,
    compliance_ribbon,
    confirm_reviewer_action,
    configure_page,
    create_compare_packet,
    create_sae_packet,
    generate_audit_packet,
    get_active_case,
    init_state,
    render_banner,
    render_case_header,
    render_metrics,
    render_sidebar,
    run_classification,
    save_active_case,
    set_screen,
    to_csv_bytes,
    to_json_bytes,
    validate_redaction,
)
from engine import (
    CHIP_MAP,
    assess_completeness,
    classify_sae,
    claude_summarise,
    compare_documents,
    detect_duplicates,
    extract_text,
    generate_inspection_report,
    run_anonymisation,
    summarise_checklist,
    summarise_meeting,
    summarise_sae,
)

# ── Bootstrap ─────────────────────────────────────────────────────────────────
configure_page()
init_state()
apply_styles()

# ── Login state ───────────────────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "_login_failed" not in st.session_state:
    st.session_state["_login_failed"] = False

VALID_USER = "admin"
VALID_PASS = "nirnay2026"

# ═══════════════════════════════════════════════════════════════════════════════
# LOGIN PAGE
# ═══════════════════════════════════════════════════════════════════════════════
if not st.session_state["logged_in"]:
    # Hide sidebar on login page
    st.markdown("""
<style>
section[data-testid="stSidebar"]{display:none;}
.stApp{background:#f0f3f8!important;}
</style>
""", unsafe_allow_html=True)

    _lcol, _rcol = st.columns([1.3, 1], gap="small")

    # ── LEFT — branding + feature cards ──────────────────────────────────────
    with _lcol:
        _cv1.html("""
<style>
body{margin:0;padding:0;font-family:'Inter',system-ui,sans-serif;}
.wrap{background:#0a2240;border-radius:16px 0 0 16px;padding:40px 36px;min-height:580px;display:flex;flex-direction:column;}
.brand{display:flex;align-items:center;gap:10px;margin-bottom:6px;}
.shield{width:30px;height:30px;border-radius:8px;background:#FF9933;display:flex;align-items:center;justify-content:center;}
.brand-name{font-size:20px;font-weight:800;color:white;letter-spacing:-0.5px;}
.brand-tag{font-size:9px;color:rgba(255,255,255,0.4);border:0.5px solid rgba(255,255,255,0.15);border-radius:20px;padding:2px 10px;}
.tagline{margin:16px 0 24px;}
.tagline h2{font-size:22px;font-weight:700;color:white;line-height:1.3;margin:0 0 6px;}
.tagline h2 span{color:#FF9933;}
.tagline p{font-size:11px;color:rgba(255,255,255,0.45);line-height:1.6;margin:0;}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-bottom:24px;}
.card{background:white;border-radius:10px;padding:13px 14px;}
.cat{font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;margin-bottom:4px;}
.title{font-size:13px;font-weight:600;color:#0a2240;margin-bottom:2px;}
.desc{font-size:10px;color:#64748b;line-height:1.4;}
.badges{display:flex;gap:7px;flex-wrap:wrap;margin-top:auto;padding-top:8px;}
.badge{font-size:9px;font-weight:600;color:#16a34a;background:#f0fdf4;border:0.5px solid #bbf7d0;border-radius:20px;padding:3px 9px;}
</style>
<div class="wrap">
  <div class="brand">
    <div class="shield">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" stroke="white" stroke-width="2.2" stroke-linejoin="round"/></svg>
    </div>
    <span class="brand-name">Nirnay</span>
    <span class="brand-tag">AI Review System</span>
  </div>
  <div class="tagline">
    <h2>Regulatory review,<br><span>reimagined for India.</span></h2>
    <p>All 6 CDSCO-mandated AI features. Upload real documents and get structured regulatory outputs in seconds.</p>
  </div>
  <div class="grid">
    <div class="card"><div class="cat" style="color:#0052cc;">01 · Privacy</div><div class="title">Anonymisation</div><div class="desc">DPDP Act 2023 compliant PII removal</div></div>
    <div class="card"><div class="cat" style="color:#0f766e;">02 · Intelligence</div><div class="title">Summarisation</div><div class="desc">SAE reports, checklists, meeting audio</div></div>
    <div class="card"><div class="cat" style="color:#6d28d9;">03 · Validation</div><div class="title">Completeness</div><div class="desc">Mandatory field verification, flagging</div></div>
    <div class="card"><div class="cat" style="color:#b45309;">04 · Triage</div><div class="title">Classification</div><div class="desc">SAE severity scoring + duplicate detection</div></div>
    <div class="card"><div class="cat" style="color:#0369a1;">05 · Diff Engine</div><div class="title">Comparison</div><div class="desc">Semantic + structural dossier diff</div></div>
    <div class="card"><div class="cat" style="color:#be185d;">06 · Generation</div><div class="title">Inspection Report</div><div class="desc">Typed / handwritten / audio → GCP report</div></div>
  </div>
  <div class="badges">
    <span class="badge">✓ DPDP Act 2023</span>
    <span class="badge">✓ NDCT Rules 2019</span>
    <span class="badge">✓ ICMR GCP</span>
    <span class="badge">✓ MeitY AI Ethics</span>
  </div>
</div>
""", height=600)

    # ── RIGHT — login form ────────────────────────────────────────────────────
    with _rcol:
        st.markdown("""
<div style="background:white;border-radius:0 16px 16px 0;padding:48px 36px 32px;min-height:580px;border:0.5px solid #e2e8f0;border-left:none;display:flex;flex-direction:column;justify-content:center;">
  <div style="font-size:10px;font-weight:700;color:#94a3b8;letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px;">Authorised access only</div>
  <div style="font-size:22px;font-weight:700;color:#0a2240;margin-bottom:28px;">Sign in</div>
</div>
""", unsafe_allow_html=True)

        _uname = st.text_input("Username", placeholder="Enter username", key="login_uname")
        _pwd   = st.text_input("Password", placeholder="Enter password", type="password", key="login_pwd")

        if st.session_state["_login_failed"]:
            st.markdown('<p style="color:#dc2626;font-size:12px;">⚠ Invalid credentials. Try again.</p>', unsafe_allow_html=True)

        _do_login = st.button("Sign in →", key="login_btn", use_container_width=True, type="primary")

        st.markdown("""
<div style="background:#f8fafc;border:0.5px solid #e2e8f0;border-radius:8px;padding:12px 14px;margin-top:14px;text-align:center;">
  <div style="font-size:10px;font-weight:700;color:#64748b;margin-bottom:4px;text-transform:uppercase;letter-spacing:.05em;">Demo credentials</div>
  <div style="font-size:13px;color:#0a2240;font-weight:500;">Username: <b>admin</b></div>
  <div style="font-size:13px;color:#0a2240;font-weight:500;">Password: <b>nirnay2026</b></div>
</div>
<div style="font-size:10px;color:#94a3b8;text-align:center;margin-top:14px;line-height:1.6;">
  Authorised CDSCO personnel only.<br>All sessions are logged for compliance.
</div>
""", unsafe_allow_html=True)

    if _do_login:
        if _uname.strip() == VALID_USER and _pwd == VALID_PASS:
            st.session_state["logged_in"]    = True
            st.session_state["_login_failed"] = False
            st.rerun()
        else:
            st.session_state["_login_failed"] = True
            st.rerun()

    st.stop()

# ── Past login gate ───────────────────────────────────────────────────────────
screen = render_sidebar()
case   = get_active_case()


def go_to(screen_name: str) -> None:
    set_screen(screen_name)
    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TOP BAR
# ═══════════════════════════════════════════════════════════════════════════════
tb1, tb2, tb3 = st.columns([3, 3, 1])
with tb1:
    st.markdown("""
<div style="display:flex;align-items:center;gap:12px;">
  <div style="font-size:22px;font-weight:900;color:#0a2240;letter-spacing:-0.8px;">Nirnay</div>
  <div style="font-size:12px;color:#475569;font-weight:500;">Regulatory review, <span style="color:#FF9933;">reimagined for India.</span></div>
</div>
""", unsafe_allow_html=True)
with tb2:
    st.markdown("""
<div style="display:flex;align-items:center;height:100%;">
  <div style="background:#fff3cd;border:0.5px solid #ffc107;border-radius:6px;padding:5px 12px;font-size:11px;color:#856404;font-weight:600;">
    ← Click the arrow on the left edge to expand the sidebar · case packets &amp; workflow
  </div>
</div>
""", unsafe_allow_html=True)
with tb3:
    col_ai, col_out = st.columns([2, 1])
    with col_ai:
        if CLAUDE_OK:
            st.markdown('<span style="font-size:10px;color:#16a34a;font-weight:600;">✓ Claude AI</span>', unsafe_allow_html=True)
    with col_out:
        if st.button("Sign out", key="signout"):
            st.session_state["logged_in"] = False
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN TABS — Features + Workflow
# ═══════════════════════════════════════════════════════════════════════════════
(t_home, t_anon, t_sum, t_comp, t_cls, t_cmp, t_insp,
 t_workflow) = st.tabs([
    "🏠 Home",
    "🔒 Anonymisation",
    "📄 Summarisation",
    "✅ Completeness",
    "🏷️ Classification",
    "🔍 Comparison",
    "📋 Inspection Report",
    "⚙️ Review Workflow",
])

# ── Tab-jump JS helper ────────────────────────────────────────────────────────
_active_tab_idx = st.session_state.get("active_tab", 0)
if _active_tab_idx > 0:
    st.session_state["active_tab"] = 0
    _cv1.html(f"""<script>
(function(){{
  var idx={_active_tab_idx};
  function clickTab(){{
    var tabs=window.parent.document.querySelectorAll('[data-baseweb="tab"]');
    if(tabs.length>idx)tabs[idx].click();
    else setTimeout(clickTab,100);
  }}
  setTimeout(clickTab,200);
}})();
</script>""", height=0)


# ═══════════════════════════════════════════════════════════════════════════════
# HOME TAB
# ═══════════════════════════════════════════════════════════════════════════════
with t_home:
    st.markdown("""
<div style="background:linear-gradient(135deg,#001f5b 0%,#003087 55%,#0052cc 100%);border-radius:16px;padding:28px 36px;margin-bottom:20px;box-shadow:0 4px 24px rgba(0,48,135,0.18);">
  <p style="font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:rgba(255,255,255,0.6);margin:0 0 6px;">CDSCO-IndiaAI Health Innovation Acceleration Hackathon · Stage 1</p>
  <h1 style="color:white;font-size:24px;font-weight:800;margin:0 0 8px;">Nirnay — AI-Driven Regulatory Workflow</h1>
  <p style="color:rgba(255,255,255,0.75);font-size:13px;max-width:700px;margin:0 0 16px;">
    All 6 mandated features from the CDSCO-IndiaAI guidelines implemented and operational.
    Upload real documents in any tab — sample packets are pre-loaded for quick evaluation.
  </p>
  <div style="display:flex;gap:8px;flex-wrap:wrap;">
    <span style="background:rgba(255,255,255,0.12);border:1px solid rgba(74,222,128,0.5);border-radius:20px;padding:4px 12px;font-size:11px;color:#4ade80;font-weight:500;">✓ DPDP Act 2023</span>
    <span style="background:rgba(255,255,255,0.12);border:1px solid rgba(74,222,128,0.5);border-radius:20px;padding:4px 12px;font-size:11px;color:#4ade80;font-weight:500;">✓ NDCT Rules 2019</span>
    <span style="background:rgba(255,255,255,0.12);border:1px solid rgba(74,222,128,0.5);border-radius:20px;padding:4px 12px;font-size:11px;color:#4ade80;font-weight:500;">✓ Schedule Y</span>
    <span style="background:rgba(255,255,255,0.12);border:1px solid rgba(74,222,128,0.5);border-radius:20px;padding:4px 12px;font-size:11px;color:#4ade80;font-weight:500;">✓ ICMR GCP Guidelines</span>
    <span style="background:rgba(255,255,255,0.12);border:1px solid rgba(74,222,128,0.5);border-radius:20px;padding:4px 12px;font-size:11px;color:#4ade80;font-weight:500;">✓ MeitY AI Ethics</span>
  </div>
</div>
""", unsafe_allow_html=True)

    # Judge evaluation guide
    st.markdown("""
<div style="background:#fffbeb;border:1px solid #fcd34d;border-radius:12px;padding:16px 20px;margin-bottom:20px;">
  <p style="font-size:12px;font-weight:700;color:#92400e;margin:0 0 8px;">📋 JUDGE EVALUATION GUIDE</p>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:12px;color:#78350f;">
    <div>• <b>Sample packets pre-loaded</b> — use sidebar to switch between them</div>
    <div>• <b>Upload real documents</b> in any tab to run live AI processing</div>
    <div>• <b>Review Workflow tab</b> — walk the full CDSCO reviewer pipeline</div>
    <div>• <b>All outputs downloadable</b> as PDF, CSV, JSON, or TXT</div>
    <div>• <b>Audit trail</b> — every AI action and reviewer decision is logged</div>
    <div>• <b>Claude AI summaries</b> available if API key is configured</div>
  </div>
</div>
""", unsafe_allow_html=True)

    _features = [
        ("01", "🔒", "Anonymisation",     "#003087",
         "PII/PHI detection and removal from regulatory documents",
         "Two-step DPDP Act 2023 process: pseudonymisation + irreversible generalisation. Detects patient names, IDs, dates, phone numbers, Aadhaar, hospital records. Full compliance audit log.", 1),
        ("02", "📄", "Summarisation",     "#0f766e",
         "Structured summaries for 3 document types",
         "SAE case narrations → priority/causality/outcome. SUGAM checklists → completeness score. Meeting transcripts → decisions, actions, next steps. Optional Claude AI enhancement.", 2),
        ("03", "✅", "Completeness",      "#6d28d9",
         "Schedule Y / Form CT mandatory field assessment",
         "Checks 20 mandatory fields against CDSCO Schedule Y requirements. RAG status per field. Approve / Return / Reject recommendation with critical gap flagging.", 3),
        ("04", "🏷️", "Classification",   "#b45309",
         "SAE severity grading + duplicate detection",
         "Classifies SAEs as DEATH / DISABILITY / HOSPITALISATION / OTHERS per Schedule Y. ICD-10 mapping, reporting timeline, priority queue. Session-based duplicate cross-detection.", 4),
        ("05", "🔍", "Comparison",        "#0369a1",
         "Semantic document diff with substantive change flagging",
         "Identifies added, removed, and changed content between two document versions. Classifies each change as substantive or administrative. Colour-coded table, downloadable PDF.", 5),
        ("06", "📋", "Inspection Report", "#be185d",
         "CDSCO GCP site inspection report generator",
         "Converts raw handwritten or typed site observations into formal CDSCO-format reports. Critical / Major / Minor grading per NDCT Rules 2019. CAPA timelines and regulatory references.", 6),
    ]

    col_a, col_b, col_c = st.columns(3, gap="medium")
    cols_cycle = [col_a, col_b, col_c]
    for i, (num, icon, name, colour, title, desc, tab_idx) in enumerate(_features):
        with cols_cycle[i % 3]:
            st.markdown(f"""
<div style="background:#0a2240;border-radius:12px;padding:22px 20px;min-height:240px;display:flex;flex-direction:column;justify-content:space-between;position:relative;overflow:hidden;">
  <div style="position:absolute;right:12px;bottom:-8px;font-size:68px;font-weight:900;color:rgba(255,255,255,0.03);pointer-events:none;">{num}</div>
  <div>
    <div style="font-size:24px;margin-bottom:8px;">{icon}</div>
    <div style="font-size:16px;font-weight:800;color:#FF9933;margin-bottom:4px;">{num} · {name}</div>
    <div style="font-size:13px;font-weight:600;color:rgba(255,255,255,0.85);margin-bottom:6px;">{title}</div>
    <div style="font-size:12px;color:rgba(255,255,255,0.6);line-height:1.5;">{desc}</div>
  </div>
</div>
""", unsafe_allow_html=True)
            if st.button(f"Open {name} →", key=f"home_{i}", use_container_width=True, type="primary"):
                st.session_state["active_tab"] = tab_idx
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — ANONYMISATION
# ═══════════════════════════════════════════════════════════════════════════════
with t_anon:
    st.markdown("""
<div class="sec-hd">
  <div class="sec-ic ic-blue" style="font-size:14px;font-weight:700;color:#1e40af;">01</div>
  <div><h2>Data Anonymisation — DPDP Act 2023</h2>
  <p>Two-step PII/PHI removal · Step 1: Reversible pseudonymisation · Step 2: Irreversible generalisation · Full audit log</p></div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<div class="upload-card"><h4>📁 Upload document</h4>', unsafe_allow_html=True)
    anon_file = st.file_uploader("Word (.docx) · PDF · Plain text (.txt)", type=["docx","pdf","txt"], key="anon_up")
    if anon_file:
        txt, err = extract_text(anon_file)
        if err:
            st.error(f"Extraction error: {err}")
        elif txt.strip():
            st.session_state["anon_text"]    = txt
            st.session_state["anon_textarea"] = txt
            st.success(f"✓ Extracted **{len(txt.split())} words** from {anon_file.name}")
    st.markdown('<div class="or-line">or paste text below</div>', unsafe_allow_html=True)
    st.text_area("Document content", height=200,
                 placeholder="Paste SAE report, clinical trial document, or any regulatory text with PII/PHI...",
                 key="anon_textarea")
    st.session_state["anon_text"] = st.session_state.get("anon_textarea","")
    st.markdown('</div>', unsafe_allow_html=True)

    c1, c2, _ = st.columns([1,1,3])
    with c1: run_anon = st.button("Analyse & protect document", type="primary", use_container_width=True)
    with c2:
        if st.button("🗑 Clear", use_container_width=True, key="anon_clear"):
            st.session_state["anon_text"] = st.session_state["anon_textarea"] = ""
            st.rerun()

    if run_anon:
        content = st.session_state["anon_text"].strip()
        if not content:
            st.markdown('<div class="rc warn">⚠️ Please upload a file or paste text first.</div>', unsafe_allow_html=True)
        else:
            with st.spinner("Detecting PII/PHI entities..."):
                result = run_anonymisation(content)
            n = result["count"]
            risk   = "High" if n >= 5 else "Medium" if n > 0 else "Low"
            action = (f"{n} sensitive items detected and anonymised. Download the anonymised version for external sharing. DPDP Act 2023 audit log generated."
                      if n > 0 else "No standard PII/PHI patterns found. Verify manually before external sharing.")
            ai_recommendation_card(
                f"{n} sensitive item(s) detected and anonymised" if n else "No sensitive information detected",
                risk, action, f"Entity types: {', '.join(result['types'])}" if result['types'] else "")

            if result["types"]:
                chips = '<div class="pii-chips">'
                for pt in result["types"]:
                    cls = CHIP_MAP.get(pt, "cg")
                    chips += f'<span class="chip {cls}">● {pt}</span>'
                chips += f'<span class="chip cg">Total: {n}</span></div>'
                st.markdown(chips, unsafe_allow_html=True)

            col_s1, col_s2 = st.columns(2, gap="large")
            fname = anon_file.name if anon_file else "document"
            base  = fname.rsplit(".",1)[0] if "." in fname else fname
            now   = datetime.datetime.now().isoformat()

            with col_s1:
                st.markdown('<span style="background:#003087;color:white;border-radius:20px;padding:3px 12px;font-size:11px;font-weight:600;">Step 1 — Reversible pseudonymisation</span>', unsafe_allow_html=True)
                st.text_area("", result["step1"], height=260, key="s1o", label_visibility="collapsed")
                tok_json = _json.dumps({
                    "document": fname, "generatedAt": now,
                    "note": "In production, encrypt this file with AES-256 at rest.",
                    "mappings": [{"token": r["Token"], "originalValue": r["Original Value"],
                                  "entityType": r["Entity Type"]} for r in result["tokens"]]
                }, indent=2)
                st.download_button("⬇ Token Registry (JSON)", tok_json,
                                   file_name=f"{base}_TokenRegistry.json", mime="application/json",
                                   use_container_width=True)

            with col_s2:
                st.markdown('<span style="background:#0f766e;color:white;border-radius:20px;padding:3px 12px;font-size:11px;font-weight:600;">Step 2 — Irreversible generalisation</span>', unsafe_allow_html=True)
                st.text_area("", result["step2"], height=260, key="s2o", label_visibility="collapsed")
                st.download_button("⬇ Anonymised Document (TXT)", result["step2"],
                                   file_name=f"{base}_Anonymised.txt", mime="text/plain",
                                   use_container_width=True)

            with st.expander("Compliance audit log (DPDP Act 2023)", expanded=False):
                st.markdown('<div class="tw">', unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(result["audit"]), use_container_width=True, hide_index=True)
                st.markdown('</div>', unsafe_allow_html=True)

            if result["tokens"]:
                with st.expander("Token mapping table (Step 1 registry)", expanded=False):
                    st.markdown('<div class="tw">', unsafe_allow_html=True)
                    st.dataframe(pd.DataFrame(result["tokens"]), use_container_width=True, hide_index=True)
                    st.markdown('</div>', unsafe_allow_html=True)

            add_audit_event("Anonymisation", f"Anonymised document — {n} PII/PHI entities",
                            0.93, "AI output generated", "Generated", fname,
                            f"Two-step DPDP Act 2023 anonymisation. Entities: {', '.join(result['types'])}")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — SUMMARISATION
# ═══════════════════════════════════════════════════════════════════════════════
with t_sum:
    st.markdown("""
<div class="sec-hd">
  <div class="sec-ic ic-teal">📄</div>
  <div><h2>Document Summarisation</h2>
  <p>Three source types: SAE Case Narration · Application Checklist (SUGAM) · Meeting Transcript/Audio</p></div>
</div>
""", unsafe_allow_html=True)

    if CLAUDE_OK:
        st.markdown('<div class="rc info">✓ Claude AI active — summaries will be AI-enhanced where available.</div>', unsafe_allow_html=True)

    doc_type = st.selectbox("Document type",
        ["SAE Case Narration", "Application Checklist (SUGAM)", "Meeting Transcript / Audio"])

    st.markdown('<div class="upload-card"><h4>📁 Upload document</h4>', unsafe_allow_html=True)
    if doc_type == "Meeting Transcript / Audio":
        st.markdown('<div class="audio-note">Audio accepted. Automatic transcription requires Stage 2 Whisper API integration. Paste transcript text below.</div>', unsafe_allow_html=True)
        sum_file = st.file_uploader("Word / PDF / TXT / Audio", type=["docx","pdf","txt","mp3","wav","m4a"], key="sum_up")
    else:
        sum_file = st.file_uploader("Word / PDF / TXT", type=["docx","pdf","txt"], key="sum_up2")

    if sum_file:
        name_l = sum_file.name.lower()
        if any(name_l.endswith(x) for x in [".mp3",".wav",".m4a"]):
            st.success(f"✓ Audio received: {sum_file.name} — paste transcript text below")
        else:
            txt, err = extract_text(sum_file)
            if err: st.error(err)
            elif txt.strip():
                st.session_state["sum_text"] = st.session_state["sum_ta"] = txt
                st.success(f"✓ Extracted {len(txt.split())} words from {sum_file.name}")

    st.markdown('<div class="or-line">or paste text manually</div>', unsafe_allow_html=True)
    st.text_area("Document content", height=200, placeholder="Paste content here...", key="sum_ta")
    st.session_state["sum_text"] = st.session_state.get("sum_ta","")
    st.markdown('</div>', unsafe_allow_html=True)

    c1, c2, _ = st.columns([1,1,3])
    with c1: run_sum = st.button("Summarise document", type="primary", use_container_width=True)
    with c2:
        if st.button("🗑 Clear ", use_container_width=True, key="sum_clear"):
            st.session_state["sum_text"] = st.session_state["sum_ta"] = ""
            st.rerun()

    if run_sum:
        content = st.session_state["sum_text"].strip()
        if not content:
            st.markdown('<div class="rc warn">Please upload or paste content first.</div>', unsafe_allow_html=True)
        else:
            # Try Claude AI first, fall back to rule-based
            ai_result = claude_summarise(content, doc_type) if CLAUDE_OK else None
            if ai_result:
                st.markdown('<div class="rc info">AI-enhanced summary (Claude Haiku)</div>', unsafe_allow_html=True)
                st.markdown(ai_result)
                st.markdown("---")
                st.caption("Rule-based structured analysis below:")

            if doc_type == "SAE Case Narration":
                r = summarise_sae(content)
                cc = "err" if r["priority"]=="URGENT" else "warn" if r["priority"]=="STANDARD" else "ok"
                risk_map = {"URGENT":"Critical","STANDARD":"Medium","LOW":"Low"}
                action_map = {
                    "URGENT": f"Immediate escalation to DCGI required. {r['timeline']} report applicable under Schedule Y.",
                    "STANDARD": "Route to standard SAE review queue. Expedited 15-day report required.",
                    "LOW": "Log as periodic SAE. Standard 90-day reporting timeline applies.",
                }
                ai_recommendation_card(
                    f"SAE classified as {r['priority']} · {r['causality']} · Outcome: {r['outcome']}",
                    risk_map[r["priority"]], action_map[r["priority"]], "CDSCO Form 12A")
                st.markdown(f'<div class="rc {cc}"><b>Priority: {r["priority"]}</b> · Causality: {r["causality"]} · Outcome: {r["outcome"]}</div>', unsafe_allow_html=True)
                c1,c2,c3 = st.columns(3)
                c1.metric("Priority", r["priority"]); c2.metric("Causality", r["causality"]); c3.metric("Outcome", r["outcome"])
                with st.expander("Full Structured SAE Summary", expanded=True):
                    st.markdown(f"| Field | Value |\n|---|---|\n| Priority | {r['priority']} |\n| Causality | {r['causality']} |\n| Outcome | {r['outcome']} |\n| Setting | {r['setting']} |\n| Reporting Timeline | {r['timeline']} |")
                st.download_button("⬇ SAE Summary (TXT)",
                    f"Priority:{r['priority']}\nCausality:{r['causality']}\nOutcome:{r['outcome']}\nTimeline:{r['timeline']}",
                    file_name="sae_summary.txt")

            elif doc_type == "Application Checklist (SUGAM)":
                r = summarise_checklist(content)
                cc = "ok" if r["score"] >= 80 else "warn" if r["score"] >= 50 else "err"
                risk_c = "Low" if r["score"] >= 80 else "Medium" if r["score"] >= 50 else "High"
                ai_recommendation_card(f"Checklist score: {r['score']}% · {r['recommendation']}",
                    risk_c, f"{r['missing']} fields missing, {r['incomplete']} incomplete.", "SUGAM portal")
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("Total",r["total"]); c2.metric("Complete",r["complete"])
                c3.metric("Incomplete",r["incomplete"]); c4.metric("Missing",r["missing"])
                st.progress(r["score"]/100, text=f"Score: {r['score']}%")
                st.markdown(f'<div class="rc {cc}"><b>Recommendation:</b> {r["recommendation"]}</div>', unsafe_allow_html=True)
                if r["actions"]:
                    with st.expander("Actionable Items", expanded=True):
                        for i,a in enumerate(r["actions"][:10],1): st.markdown(f"{i}. {a}")

            else:  # Meeting
                r = summarise_meeting(content)
                ai_recommendation_card("Meeting transcript summarised", "Low",
                    f"{len(r['decisions'])} decisions, {len(r['actions'])} action items, {len(r['next_steps'])} next steps extracted.", "Meeting summary")
                if r["decisions"]:
                    with st.expander("✅ Key Decisions", expanded=True):
                        for d in r["decisions"]: st.write(f"• {d}")
                if r["actions"]:
                    with st.expander("📌 Action Items", expanded=True):
                        for a in r["actions"]: st.write(f"• {a}")
                if r["next_steps"]:
                    with st.expander("📅 Next Steps", expanded=False):
                        for n in r["next_steps"]: st.write(f"• {n}")

            add_audit_event("Summarisation", f"Document summarised — {doc_type}", 0.90,
                            "AI output generated", "Generated", doc_type, "")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — COMPLETENESS
# ═══════════════════════════════════════════════════════════════════════════════
with t_comp:
    st.markdown("""
<div class="sec-hd">
  <div class="sec-ic ic-purple">✅</div>
  <div><h2>Completeness Assessment — Schedule Y / Form CT</h2>
  <p>Checks 20 mandatory fields · RAG status per field · Approve / Return / Reject recommendation · Critical gap flagging</p></div>
</div>
""", unsafe_allow_html=True)

    col_a, col_b = st.columns([3,1])
    with col_a:
        st.markdown('<div class="upload-card"><h4>📁 Upload application document</h4>', unsafe_allow_html=True)
        comp_file = st.file_uploader("Word / PDF / TXT", type=["docx","pdf","txt"], key="comp_up")
        if comp_file:
            txt, err = extract_text(comp_file)
            if err: st.error(err)
            elif txt.strip():
                st.session_state["comp_text"] = st.session_state["comp_ta"] = txt
                st.success(f"✓ Extracted {len(txt.split())} words from {comp_file.name}")
        st.markdown('<div class="or-line">or paste text manually</div>', unsafe_allow_html=True)
        st.text_area("Application content", height=180,
                     placeholder="Paste SUGAM application or checklist content...", key="comp_ta")
        st.session_state["comp_text"] = st.session_state.get("comp_ta","")
        st.markdown('</div>', unsafe_allow_html=True)
    with col_b:
        app_id = st.text_input("Application ID", placeholder="SUGAM-CT-2024-0892")
        st.markdown("<br>", unsafe_allow_html=True)
        run_comp = st.button("✅ Check Completeness", type="primary", use_container_width=True)

    if run_comp:
        content = st.session_state["comp_text"].strip()
        if not content:
            st.markdown('<div class="rc warn">Please upload or paste content first.</div>', unsafe_allow_html=True)
        else:
            r = assess_completeness(content)
            cc = "ok" if r["score"] >= 85 and not r["critical_missing"] else "warn" if r["score"] >= 60 else "err"
            risk_c = "Critical" if r["critical_missing"] else "High" if r["score"] < 60 else "Medium" if r["score"] < 85 else "Low"
            action = (f"Reject — {len(r['critical_missing'])} critical field(s) missing: {', '.join(r['critical_missing'][:3])}."
                      if r["critical_missing"] else
                      f"Return — {r['total'] - r['present']} field(s) need attention."
                      if r["score"] < 85 else "Approve for technical review — all critical fields present.")
            ai_recommendation_card(f"Application completeness: {r['score']}% · {r['recommendation']}",
                risk_c, action, f"Fields checked: {r['total']} · Present: {r['present']} · Missing: {r['total']-r['present']}")
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Total",r["total"]); c2.metric("Present",r["present"])
            c3.metric("Missing",r["total"]-r["present"])
            c4.metric("Score",f"{r['score']}%")
            st.progress(r["score"]/100, text=f"Application completeness: {r['score']}%")
            st.markdown(f'<div class="rc {cc}"><b>Recommendation:</b> {r["recommendation"]}</div>', unsafe_allow_html=True)
            if r["critical_missing"]: st.error(f"Critical missing: {', '.join(r['critical_missing'])}")
            if r["major_missing"]: st.warning(f"Major missing: {', '.join(r['major_missing'])}")
            with st.expander("Full Field Status (RAG)", expanded=True):
                def srag(v):
                    if "Green" in str(v): return "background-color:#dcfce7;color:#15803d;font-weight:600"
                    if "Amber" in str(v): return "background-color:#fef9c3;color:#a16207;font-weight:600"
                    if "Red"   in str(v): return "background-color:#fee2e2;color:#b91c1c;font-weight:600"
                    return ""
                df = pd.DataFrame(r["rows"])
                st.markdown('<div class="tw">', unsafe_allow_html=True)
                st.dataframe(df.style.map(srag, subset=["RAG"]), use_container_width=True, hide_index=True)
                st.markdown('</div>', unsafe_allow_html=True)
            st.download_button("⬇ Completeness Report (CSV)", df.to_csv(index=False),
                               file_name="completeness_report.csv", mime="text/csv")
            add_audit_event("Completeness", f"Assessment — score {r['score']}%", 0.91,
                            "AI output generated", "Generated",
                            app_id or "unknown", r["recommendation"])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════════
with t_cls:
    st.markdown("""
<div class="sec-hd">
  <div class="sec-ic ic-amber">🏷️</div>
  <div><h2>SAE Classification &amp; Duplicate Detection</h2>
  <p>DEATH · DISABILITY · HOSPITALISATION · OTHERS · ICD-10 mapping · Session-based duplicate detection</p></div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="dup-session"><b>Duplicate detection:</b> Upload multiple SAE reports below.
The system cross-checks Patient IDs and drug names across all session files to flag duplicates.
Files are cleared on browser refresh — DPDP compliant (no external storage).</div>
""", unsafe_allow_html=True)

    st.markdown('<div class="upload-card"><h4>📁 Primary SAE Report</h4>', unsafe_allow_html=True)
    cls_file = st.file_uploader("Word / PDF / TXT", type=["docx","pdf","txt"], key="class_up")
    if cls_file:
        txt, err = extract_text(cls_file)
        if err: st.error(err)
        elif txt.strip():
            st.session_state["class_text"] = st.session_state["class_ta"] = txt
            st.session_state["dup_files"]["SAE-1"] = {"name": cls_file.name, "text": txt}
            st.success(f"✓ Loaded: {cls_file.name}")
    st.markdown('<div class="or-line">or paste text</div>', unsafe_allow_html=True)
    st.text_area("SAE report content", height=160, key="class_ta")
    st.session_state["class_text"] = st.session_state.get("class_ta","")
    st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("+ Add more SAE reports for duplicate detection", expanded=False):
        dcols = st.columns(2)
        for idx, (slot, label) in enumerate([("SAE-2","SAE Report 2"),("SAE-3","SAE Report 3")]):
            with dcols[idx]:
                f2 = st.file_uploader(label, type=["docx","pdf","txt"], key=f"dup_{slot}")
                if f2:
                    t2, e2 = extract_text(f2)
                    if not e2 and t2.strip():
                        st.session_state["dup_files"][slot] = {"name": f2.name, "text": t2}
                        st.success(f"✓ {f2.name}")
        if st.session_state["dup_files"]:
            st.write(f"**Files in session:** {', '.join(v['name'] for v in st.session_state['dup_files'].values())}")
        if st.button("🗑 Clear session files"):
            st.session_state["dup_files"] = {}; st.rerun()

    c1, _, _ = st.columns([1,1,3])
    with c1: run_cls = st.button("🏷️ Classify & Check Duplicates", type="primary", use_container_width=True)

    if run_cls:
        content = st.session_state["class_text"].strip()
        if not content:
            st.markdown('<div class="rc warn">Please upload or paste an SAE report first.</div>', unsafe_allow_html=True)
        else:
            r = classify_sae(content)
            risk_map = {"DEATH":"Critical","DISABILITY":"High","HOSPITALISATION":"Medium","OTHERS":"Low"}
            action_map = {
                "DEATH":          "Expedited 7-day report mandatory. Immediate notification to DCGI and Ethics Committee required under Schedule Y.",
                "DISABILITY":     "Expedited 15-day report required. Notify sponsor and Ethics Committee. Assess causality.",
                "HOSPITALISATION":"Expedited 15-day report required. Monitor patient outcome and submit follow-up report.",
                "OTHERS":         "Periodic reporting within 90 days. Document in safety database.",
            }
            sev_colours = {"DEATH":"background:#fee2e2;color:#991b1b","DISABILITY":"background:#ffedd5;color:#9a3412",
                           "HOSPITALISATION":"background:#fef9c3;color:#92400e","OTHERS":"background:#dbeafe;color:#1e40af"}
            ai_recommendation_card(
                f"SAE classified as {r['severity']} · Confidence: {r['confidence']} · Priority queue: {r['priority']}/4",
                risk_map[r["severity"]], action_map[r["severity"]],
                f"ICD-10: {r['icd10']} · Reporting timeline: {r['timeline']}")
            st.markdown(f'<div style="{sev_colours[r["severity"]]};border-radius:10px;padding:10px 20px;font-size:18px;font-weight:700;display:inline-block;margin-bottom:12px;">⬤ {r["severity"]}</div>', unsafe_allow_html=True)
            c1,c2,c3 = st.columns(3)
            c1.metric("Severity",r["severity"]); c2.metric("Confidence",r["confidence"]); c3.metric("Priority Queue",f"{r['priority']} / 4")
            with st.expander("Classification Evidence", expanded=True):
                st.markdown(f'<div class="rc info"><b>Keywords detected:</b> {", ".join(r["keywords"])}<br><b>ICD-10:</b> {r["icd10"]} · <b>Reporting:</b> {r["timeline"]}</div>', unsafe_allow_html=True)

            st.markdown("**Duplicate detection across session files**")
            dups = detect_duplicates(content, st.session_state["dup_files"])
            if len(st.session_state["dup_files"]) > 1:
                if dups:
                    for d in dups:
                        st.markdown(f'<div class="rc err">⚠️ DUPLICATE DETECTED — matches <b>{d["file"]}</b> · Patient IDs: {d["shared_ids"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="rc ok">✓ No duplicates found across session files.</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="rc info">Upload additional SAE reports above to enable duplicate cross-checking.</div>', unsafe_allow_html=True)

            report_txt = f"Severity:{r['severity']}\nConfidence:{r['confidence']}\nKeywords:{', '.join(r['keywords'])}\nPriority:{r['priority']}/4\nICD-10:{r['icd10']}\nTimeline:{r['timeline']}"
            st.download_button("⬇ Classification Report (TXT)", report_txt, file_name="classification_report.txt")
            add_audit_event("Classification", f"SAE classified as {r['severity']}", 0.93,
                            "AI output generated", "Generated", "SAE upload", action_map[r["severity"]])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — COMPARISON
# ═══════════════════════════════════════════════════════════════════════════════
with t_cmp:
    st.markdown("""
<div class="sec-hd">
  <div class="sec-ic ic-sky">🔍</div>
  <div><h2>Document Comparison</h2>
  <p>Upload two filing versions · Substantive vs administrative diff · Colour-coded table · Downloadable PDF report</p></div>
</div>
""", unsafe_allow_html=True)

    cv1, cv2 = st.columns(2)
    with cv1:
        st.markdown("**Version 1 — Original**")
        v1f = st.file_uploader("Upload V1", type=["docx","pdf","txt"], key="v1f")
        if v1f:
            t, e = extract_text(v1f)
            if not e and t.strip():
                st.session_state["v1_text"] = st.session_state["v1ta"] = t
                st.success(f"✓ {v1f.name}")
        st.text_area("or paste V1", height=200, key="v1ta", placeholder="Original document...")
        st.session_state["v1_text"] = st.session_state.get("v1ta","")
    with cv2:
        st.markdown("**Version 2 — Updated**")
        v2f = st.file_uploader("Upload V2", type=["docx","pdf","txt"], key="v2f")
        if v2f:
            t, e = extract_text(v2f)
            if not e and t.strip():
                st.session_state["v2_text"] = st.session_state["v2ta"] = t
                st.success(f"✓ {v2f.name}")
        st.text_area("or paste V2", height=200, key="v2ta", placeholder="Updated document...")
        st.session_state["v2_text"] = st.session_state.get("v2ta","")

    c1, _, _ = st.columns([1,1,3])
    with c1: run_cmp = st.button("🔍 Compare Documents", type="primary", use_container_width=True)

    if run_cmp:
        t1c = st.session_state["v1_text"].strip()
        t2c = st.session_state["v2_text"].strip()
        if not t1c or not t2c:
            st.markdown('<div class="rc warn">Please provide both document versions.</div>', unsafe_allow_html=True)
        else:
            changes = compare_documents(t1c, t2c)
            sc = sum(1 for c in changes if c["Substantive"] == "Yes")
            c1,c2,c3,c4,c5 = st.columns(5)
            c1.metric("Total",len(changes)); c2.metric("Added",sum(1 for c in changes if c["Type"]=="ADDED"))
            c3.metric("Removed",sum(1 for c in changes if c["Type"]=="REMOVED"))
            c4.metric("Changed",sum(1 for c in changes if c["Type"]=="CHANGED")); c5.metric("Substantive",sc)
            risk_c = "High" if sc >= 3 else "Medium" if sc >= 1 else "Low"
            action = (f"{sc} substantive change(s) detected — formal review and possible amended submission to CDSCO required."
                      if sc > 0 else "No substantive changes. Administrative edits only — may proceed without re-review.")
            ai_recommendation_card(f"{len(changes)} changes · {sc} substantive · {len(changes)-sc} administrative",
                risk_c, action, "Substantive: changes affecting dosage, safety, outcomes, or patient information.")
            cc = "err" if sc > 0 else "ok"
            st.markdown(f'<div class="rc {cc}">{"⚠️ "+str(sc)+" substantive change(s) — regulatory review required." if sc > 0 else "✓ No substantive changes detected."}</div>', unsafe_allow_html=True)
            if changes:
                def sd(row):
                    if row["Type"]=="ADDED": return ["background-color:#dcfce7"]*len(row)
                    if row["Type"]=="REMOVED": return ["background-color:#fee2e2"]*len(row)
                    if row["Substantive"]=="Yes": return ["background-color:#fef9c3"]*len(row)
                    return [""]*len(row)
                df = pd.DataFrame(changes)
                with st.expander("Full Change Table", expanded=True):
                    st.markdown('<div class="tw">', unsafe_allow_html=True)
                    st.dataframe(df.style.apply(sd, axis=1), use_container_width=True, hide_index=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.caption("🟢 Added · 🔴 Removed · 🟡 Changed (Substantive)")
                st.download_button("⬇ Comparison Report (CSV)", df.to_csv(index=False),
                                   file_name="comparison_report.csv", mime="text/csv")
            add_audit_event("Comparison", f"{len(changes)} changes — {sc} substantive", 0.91,
                            "AI output generated", "Generated", "Document comparison", action)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 6 — INSPECTION REPORT
# ═══════════════════════════════════════════════════════════════════════════════
with t_insp:
    st.markdown("""
<div class="sec-hd">
  <div class="sec-ic ic-pink">📋</div>
  <div><h2>Inspection Report Generation</h2>
  <p>Raw site observations → Formal CDSCO GCP report · Critical / Major / Minor grading · CAPA timelines · NDCT Rules 2019</p></div>
</div>
""", unsafe_allow_html=True)

    ic1,ic2,ic3,ic4 = st.columns(4)
    with ic1: insp_name = st.text_input("Inspector Name", placeholder="Dr. A.K. Sharma")
    with ic2: insp_site = st.text_input("Site Name", placeholder="AIIMS Delhi")
    with ic3: insp_sno  = st.text_input("Site Number", placeholder="SITE-DEL-001")
    with ic4: insp_date = st.date_input("Inspection Date")

    obs = st.text_area("Raw inspection observations — one per line", height=180, key="obs_ta",
        placeholder="No record of drug accountability for subjects 3 and 7\nInformed consent missing local language version\nMinor labelling error on storage box")

    c1, _, _ = st.columns([1,1,3])
    with c1: run_insp = st.button("📋 Generate Report", type="primary", use_container_width=True)

    if run_insp and obs.strip():
        rpt = generate_inspection_report(obs, insp_site, insp_sno, insp_name, insp_date)
        risk_label = "Critical" if rpt["critical"] > 0 else "High" if rpt["major"] > 0 else "Low"
        action_insp = (f"{rpt['critical']} Critical GCP deviation(s). Immediate CAPA required. Report to DCGI within 15 days."
                       if rpt["critical"] > 0 else
                       f"{rpt['major']} Major deviation(s). CAPA plan within 30 days."
                       if rpt["major"] > 0 else
                       f"No Critical or Major findings. {rpt['minor']} Minor deviation(s) to be logged within 60 days.")
        ai_recommendation_card(
            f"Inspection: {rpt['critical']} Critical · {rpt['major']} Major · {rpt['minor']} Minor",
            risk_label, action_insp,
            f"Site: {insp_site or '[Site]'} · {insp_date.strftime('%d %B %Y')} · Inspector: {insp_name or '[Inspector]'}")
        cc = "err" if rpt["critical"] > 0 else "warn" if rpt["major"] > 0 else "ok"
        st.markdown(f'<div class="rc {cc}">{"⚠️ "+str(rpt["critical"])+" Critical findings — CAPA required." if rpt["critical"] > 0 else "⚠️ "+str(rpt["major"])+" Major findings — CAPA due in 30 days." if rpt["major"] > 0 else "✓ No Critical or Major findings."}</div>', unsafe_allow_html=True)
        ic1,ic2,ic3 = st.columns(3)
        ic1.metric("Critical",rpt["critical"]); ic2.metric("Major",rpt["major"]); ic3.metric("Minor",rpt["minor"])
        df = pd.DataFrame(rpt["rows"])
        def sr(v):
            if v=="Critical": return "background-color:#fee2e2;color:#991b1b;font-weight:700"
            if v=="Major":    return "background-color:#fef9c3;color:#92400e;font-weight:700"
            if v=="Minor":    return "background-color:#dcfce7;color:#166534"
            return ""
        with st.expander("Full Inspection Report Table", expanded=True):
            st.markdown('<div class="tw">', unsafe_allow_html=True)
            st.dataframe(df.style.map(sr, subset=["Risk"]), use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)
        st.download_button("⬇ Inspection Report (TXT)", rpt["full_text"],
                           file_name=f"inspection_report_{insp_date}.txt", mime="text/plain")
        add_audit_event("Inspection Report",
                        f"Report generated — {rpt['critical']} Critical, {rpt['major']} Major, {rpt['minor']} Minor",
                        0.92, "AI output generated", "Generated",
                        insp_site or "unknown site", action_insp)
    elif run_insp:
        st.markdown('<div class="rc warn">Please enter at least one observation.</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 7 — REVIEW WORKFLOW (formerly separate screens, now in a tab)
# ═══════════════════════════════════════════════════════════════════════════════
with t_workflow:
    render_banner("CDSCO Review Workflow", "Full reviewer pipeline: intake → protected view → SAE review → version compare → audit trail. Uses pre-loaded sample packets.")

    def command_dashboard() -> None:
        case["current_stage"] = "Command Dashboard"
        save_active_case(case)
        render_metrics()
        render_case_header(case)
        sc1,sc2,sc3 = st.columns(3)
        with sc1:
            st.metric("Selected document", case["documents"][case["selected_document_id"]]["type"])
            st.metric("Reviewer confirmations", len(case["reviewer_decisions"]))
        with sc2:
            st.metric("Protected-view status", "Validated" if case["protected_view"]["validated"] else "Pending")
            st.metric("SAE packet", "Ready" if case["sae_review"]["review_packet"] else "Pending")
        with sc3:
            st.metric("Compare packet", "Ready" if case["compare_review"]["review_packet"] else "Pending")
            st.metric("Audit packet", "Ready" if case["export_readiness"]["audit_packet"] else "Pending")
        st.caption("Dashboard → Document Intake → Protected View → SAE Review → Version Compare → Audit Trail")
        ac1,ac2,ac3 = st.columns(3)
        with ac1:
            if st.button("Open Document Intake", use_container_width=True):
                add_audit_event("Command Dashboard","Workflow routed",1.0,"Opened Document Intake","Completed",case["packet_id"],""); go_to("Document Intake")
        with ac2:
            if st.button("Jump to SAE Review", use_container_width=True):
                add_audit_event("Command Dashboard","Workflow routed",1.0,"Opened SAE Review","Completed",case["packet_id"],""); go_to("SAE Review")
        with ac3:
            if st.button("Open Audit Trail", use_container_width=True): go_to("Audit Trail")
        st.markdown("### Source packet overview")
        dc1,dc2,dc3 = st.columns(3)
        for idx, doc in enumerate(case["documents"].values()):
            with [dc1,dc2,dc3][idx % 3]:
                with st.container(border=True):
                    st.write(f"**{doc['name']}**"); st.write(f"Type: {doc['type']}")
                    st.write(f"Source: {doc['source']}"); st.write(f"Risk: {doc['risk_level']}")
                    st.caption(doc["preview"])

    def document_intake() -> None:
        case["current_stage"] = "Document Intake"; save_active_case(case)
        doc_ids  = list(case["documents"].keys())
        selected = st.selectbox("Case packet document", options=doc_ids,
                                index=doc_ids.index(case["selected_document_id"]),
                                format_func=lambda d: case["documents"][d]["name"])
        if selected != case["selected_document_id"]:
            case["selected_document_id"] = selected; save_active_case(case)
        sel_doc = case["documents"][case["selected_document_id"]]
        st.markdown("### Intake controls")
        ic1,ic2,ic3,ic4 = st.columns(4)
        with ic1:
            if st.button("Run classification", use_container_width=True): run_classification(); st.success("Classification recorded.")
        with ic2:
            if st.button("Confirm reviewer action", use_container_width=True):
                confirm_reviewer_action("Document Intake","Reviewer confirmed intake assessment","Classification accepted.",sel_doc["name"],confidence=sel_doc["confidence"]); st.success("Confirmation recorded.")
        with ic3:
            if st.button("Escalate low-confidence", use_container_width=True):
                confirm_reviewer_action("Document Intake","Escalated",sel_doc.get("classification",{}).get("escalation_recommendation","Escalation requested."),sel_doc["name"],confidence=sel_doc["confidence"],final_status="Escalated"); st.warning("Escalation recorded.")
        with ic4:
            if st.button("→ Protected View", use_container_width=True): go_to("Protected View")
        dt1, dt2, dt3 = st.tabs(["Classification","Synopsis","Source"])
        with dt1:
            clf = case["document_classification"] or sel_doc.get("classification",{})
            with st.container(border=True):
                st.write(f"**Probable type:** {clf.get('probable_type','Pending')}"); st.write(f"**Severity:** {clf.get('severity',sel_doc['risk_level'])}")
                st.write(f"**Duplicate warning:** {clf.get('duplicate_warning','Pending')}"); st.write(f"**Escalation:** {clf.get('escalation_recommendation','Pending')}"); st.write(f"**Confidence:** {int(sel_doc['confidence']*100)}%")
        with dt2:
            syn = case["structured_synopsis"] or sel_doc.get("synopsis",{})
            with st.container(border=True):
                st.write(f"**Headline:** {syn.get('headline','Pending')}"); st.write(syn.get("summary","Run classification to generate synopsis."))
                for sig in syn.get("key_signals",[]): st.write(f"- {sig}")
                if syn.get("reviewer_prompt"): st.info(syn["reviewer_prompt"])
        with dt3:
            with st.container(border=True): st.write(sel_doc["raw_text"])

    def protected_view_screen() -> None:
        case["current_stage"] = "Protected View"; save_active_case(case)
        protected = case["protected_view"]
        pv_doc    = case["documents"][protected["source_document_id"]]
        fc1,fc2,fc3,fc4 = st.columns(4)
        cats = protected["category_filters"]
        with fc1: cats["Patient"]      = st.checkbox("Patient identifiers",      value=cats["Patient"])
        with fc2: cats["Investigator"] = st.checkbox("Investigator identifiers", value=cats["Investigator"])
        with fc3: cats["Date"]         = st.checkbox("Dates",                    value=cats["Date"])
        with fc4: cats["Site"]         = st.checkbox("Site identifiers",         value=cats["Site"])
        save_active_case(case)
        ent_cols = st.columns(2)
        with ent_cols[0]:
            st.markdown("**Original document**")
            st.markdown(f'<div class="entity-box">{pv_doc["raw_text"]}</div>', unsafe_allow_html=True)
        with ent_cols[1]:
            st.markdown("**Protected view**")
            st.markdown(f'<div class="entity-box">{apply_redaction_filters(case)}</div>', unsafe_allow_html=True)
        st.markdown("### Entity review")
        for entity in protected["entities"]:
            with st.container(border=True):
                ec1,ec2,ec3 = st.columns([2,2,1])
                with ec1: st.write(f"**{entity['label']}** — `{entity['value']}`")
                with ec2: st.write(f"Replacement: `{entity['replacement']}` | Confidence: {int(entity['confidence']*100)}%")
                with ec3: entity["approved"] = st.checkbox("Approve",value=entity["approved"],key=f"ent_{entity['label']}")
        save_active_case(case)
        pa1,pa2,pa3 = st.columns(3)
        with pa1:
            if st.button("Validate protected view", use_container_width=True): validate_redaction(); st.success("Protected view validated.")
        with pa2:
            if st.button("Confirm reviewer action", use_container_width=True):
                confirm_reviewer_action("Protected View","Reviewer confirmed protected view","Redaction confirmed.",pv_doc["name"],confidence=0.93); st.success("Confirmed.")
        with pa3:
            if st.button("→ SAE Review", use_container_width=True): go_to("SAE Review")
        if protected["validated"]: st.success(f"✓ {protected['validation_summary']} — {protected['escalation_status']}")

    def sae_review_screen() -> None:
        case["current_stage"] = "SAE Review"; save_active_case(case)
        sae = case["sae_review"]
        with st.container(border=True):
            sc1,sc2,sc3 = st.columns(3)
            with sc1: st.write(f"**Patient:** {sae['patient_profile']}"); st.write(f"**Event:** {sae['event']}")
            with sc2: st.write(f"**Seriousness:** {sae['seriousness']}"); st.write(f"**Causality:** {sae['causality']}")
            with sc3: st.write(f"**Action:** {sae['action_taken']}"); st.write(f"**Outcome:** {sae['outcome']}")
        st.markdown("**Missing information**")
        for item in sae["missing_info"]:
            item["resolved"] = st.checkbox(item["item"], value=item["resolved"], key=f"mi_{item['item']}")
        sae["reviewer_notes"] = st.text_area("Reviewer notes", value=sae["reviewer_notes"], height=80)
        save_active_case(case)
        sa1,sa2,sa3,sa4 = st.columns(4)
        with sa1:
            if st.button("Confirm reviewer action", use_container_width=True):
                confirm_reviewer_action("SAE Review","Reviewer confirmed SAE output","SAE output accepted.",case["documents"]["sae"]["name"],confidence=0.94); st.success("Confirmed.")
        with sa2:
            if st.button("Escalate low-confidence", use_container_width=True):
                confirm_reviewer_action("SAE Review","Escalated","Escalated due to source gaps.",case["documents"]["sae"]["name"],confidence=0.9,final_status="Escalated"); st.warning("Escalated.")
        with sa3:
            if st.button("Create review packet", use_container_width=True):
                packet = create_sae_packet(); st.success("SAE packet created."); st.text_area("Generated packet", value=packet, height=200)
        with sa4:
            if st.button("→ Version Compare", use_container_width=True): go_to("Version Compare")
        if sae["review_packet"]:
            st.download_button("⬇ SAE Review Packet", sae["review_packet"].encode(),
                               file_name=f"{case['case_id']}_sae_packet.txt", mime="text/plain", use_container_width=True)

    def version_compare_screen() -> None:
        case["current_stage"] = "Version Compare"; save_active_case(case)
        amendment = case["documents"]["amendment"]
        compare   = case["compare_review"]
        filt = st.radio("Change filter",["All changes","Eligibility","Endpoint","Consent language"],horizontal=True,
                        index=["All changes","Eligibility","Endpoint","Consent language"].index(st.session_state.compare_filter))
        st.session_state.compare_filter = compare["selected_filter"] = filt; save_active_case(case)
        vc1,vc2 = st.columns(2)
        with vc1: st.text_area("Baseline version",value=amendment["base_text"],height=180,disabled=True)
        with vc2: st.text_area("Updated version",value=amendment["updated_text"],height=180,disabled=True)
        st.markdown("### Change analysis")
        visible = [c for c in amendment["changes"] if filt == "All changes" or c["area"] == filt]
        for c in visible:
            with st.expander(f"{c['area']} | {c['classification']} | {c['impact_level']} impact"):
                st.write(f"**Before:** {c['before']}"); st.write(f"**After:** {c['after']}"); st.write(f"**Regulatory impact:** {c['impact']}")
        vc1a,vc2a,vc3a,vc4a = st.columns(4)
        with vc1a:
            if st.button("Confirm reviewer action ", use_container_width=True):
                confirm_reviewer_action("Version Compare","Reviewer confirmed comparison","Material changes accepted.",amendment["name"],confidence=amendment["confidence"]); st.success("Confirmed.")
        with vc2a:
            if st.button("Escalate substantive change", use_container_width=True):
                confirm_reviewer_action("Version Compare","Escalated","Substantive change escalated.",amendment["name"],confidence=0.91,final_status="Escalated"); st.warning("Escalated.")
        with vc3a:
            if st.button("Create review packet ", use_container_width=True):
                packet = create_compare_packet(); st.success("Comparison packet created."); st.text_area("Generated packet", value=packet, height=220)
        with vc4a:
            if st.button("→ Audit Trail", use_container_width=True): go_to("Audit Trail")
        if compare["review_packet"]:
            st.download_button("⬇ Comparison Packet", compare["review_packet"].encode(),
                               file_name=f"{case['case_id']}_compare_packet.txt", mime="text/plain", use_container_width=True)

    def audit_trail_screen() -> None:
        case["current_stage"] = "Audit Trail"; save_active_case(case)
        df = audit_dataframe(case)
        search = st.text_input("Search audit events")
        if search:
            low = search.lower()
            df  = df[df.astype(str).apply(lambda col: col.str.lower().str.contains(low, na=False)).any(axis=1)]
        st.dataframe(df, use_container_width=True, hide_index=True)
        for evt in case["audit_events"][-5:][::-1]:
            with st.expander(f"{evt['timestamp']} | {evt['module']} | {evt['reviewer_action']}"):
                st.write(f"**Action:** {evt['action']}"); st.write(f"**Confidence:** {evt['confidence']}")
                st.write(f"**Status:** {evt['final_status']}"); st.write(f"**Source:** {evt['source_reference']}"); st.write(f"**Detail:** {evt['note']}")
        with st.container(border=True):
            st.write(f"**Protected view:** {case['protected_view']['escalation_status']}")
            st.write(f"**SAE packet ready:** {'Yes' if case['sae_review']['review_packet'] else 'No'}")
            st.write(f"**Compare packet ready:** {'Yes' if case['compare_review']['review_packet'] else 'No'}")
            st.write(f"**Reviewer confirmations:** {len(case['reviewer_decisions'])}")
        at1,at2,at3 = st.columns(3)
        with at1:
            if st.button("Confirm reviewer action  ", use_container_width=True):
                confirm_reviewer_action("Audit Trail","Reviewer confirmed audit record","Audit record accepted.",case["packet_id"]); st.success("Confirmed.")
        with at2:
            if st.button("Generate audit packet", use_container_width=True):
                pkt = generate_audit_packet(); st.success("Audit packet generated.")
                st.download_button("⬇ Audit Packet (JSON)", to_json_bytes(pkt),
                                   file_name=f"{case['case_id']}_audit_packet.json", mime="application/json", use_container_width=True)
        with at3:
            st.download_button("⬇ Audit Log (CSV)", to_csv_bytes(case["audit_events"]),
                               file_name=f"{case['case_id']}_audit_log.csv", mime="text/csv", use_container_width=True)
        st.info(APP_DISCLAIMER)

    # Route to the selected workflow screen
    WORKFLOW_ROUTES = {
        "Command Dashboard": command_dashboard,
        "Document Intake":   document_intake,
        "Protected View":    protected_view_screen,
        "SAE Review":        sae_review_screen,
        "Version Compare":   version_compare_screen,
        "Audit Trail":       audit_trail_screen,
    }
    WORKFLOW_ROUTES[screen]()


# ── Compliance ribbon ─────────────────────────────────────────────────────────
compliance_ribbon()
