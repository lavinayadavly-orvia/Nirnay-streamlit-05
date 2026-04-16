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
    03 Completeness      — NDCT Rules 2019 / Form CT mandatory field assessment
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
    render_top_nav,
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
# LOGIN PAGE — native Streamlit inputs, full CSS dark styling
# ═══════════════════════════════════════════════════════════════════════════════
if not st.session_state["logged_in"]:
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
*{font-family:'Inter',system-ui,sans-serif;}
section[data-testid="stSidebar"]{display:none!important;}
header{display:none!important;}
footer{display:none!important;}
.stApp{background-color:#060f1e!important;}
.block-container{padding:0!important;max-width:100%!important;}
[data-testid="column"]{padding:0!important;}
[data-testid="column"]:first-child{background-color:#071428!important;padding:52px 48px!important;border-right:1px solid rgba(255,255,255,0.05)!important;}
[data-testid="column"]:last-child{background-color:#0d1f3c!important;padding:52px 48px!important;}
[data-testid="stTextInput"] input{background-color:#071224!important;border:1.5px solid rgba(255,255,255,0.18)!important;border-radius:9px!important;color:#f1f5f9!important;font-size:14px!important;}
[data-testid="stTextInput"] input:focus{border-color:#FF9933!important;outline:none!important;}
[data-testid="stTextInput"] input::placeholder{color:rgba(255,255,255,0.3)!important;}
[data-testid="stTextInput"] label,[data-testid="stTextInput"] p{color:rgba(255,255,255,0.7)!important;font-size:11px!important;font-weight:700!important;letter-spacing:.1em!important;text-transform:uppercase!important;}
[data-testid="stFormSubmitButton"] button{background-color:#FF9933!important;border:none!important;border-radius:9px!important;color:white!important;font-size:14px!important;font-weight:700!important;width:100%!important;padding:13px!important;}
[data-testid="stFormSubmitButton"] button:hover{background-color:#e8821a!important;}
[data-testid="stForm"]{border:none!important;padding:0!important;background-color:transparent!important;}
</style>
""", unsafe_allow_html=True)

    _lcol, _rcol = st.columns([13, 10], gap="small")

    # ── LEFT COLUMN — pure HTML, zero Streamlit widgets ──────────────────────
    with _lcol:
        st.markdown(
            '<div style="font-family:Inter,system-ui,sans-serif;min-height:640px;display:flex;flex-direction:column;">'

            '<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">'
            '<div style="width:36px;height:36px;border-radius:9px;background-color:#FF9933;display:flex;align-items:center;justify-content:center;flex-shrink:0;">'
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" stroke="white" stroke-width="2.2" stroke-linejoin="round"/></svg>'
            '</div>'
            '<span style="font-size:20px;font-weight:800;color:white;letter-spacing:-0.5px;">Nirnay</span>'
            '<span style="font-size:11px;font-weight:500;color:rgba(255,255,255,0.35);border:1px solid rgba(255,255,255,0.12);border-radius:20px;padding:2px 10px;">AI Review System</span>'
            '</div>'

            '<div style="width:32px;height:2px;background-color:#FF9933;border-radius:2px;margin-bottom:20px;"></div>'

            '<div style="font-size:20px;font-weight:700;color:white;line-height:1.35;margin-bottom:8px;">'
            'Regulatory review,<br><span style="color:#FF9933;">reimagined for India.</span>'
            '</div>'

            '<div style="font-size:13px;font-weight:400;color:rgba(255,255,255,0.45);line-height:1.7;margin-bottom:24px;">'
            'All 6 CDSCO-mandated AI features in one platform.<br>Upload real documents — structured outputs in seconds.'
            '</div>'

            '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:20px;flex:1;">'

            '<div style="background-color:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-top:2px solid #3b82f6;border-radius:10px;padding:14px;">'
            '<div style="font-size:11px;font-weight:700;color:#60a5fa;letter-spacing:.1em;text-transform:uppercase;margin-bottom:4px;">01 &middot; Privacy</div>'
            '<div style="font-size:13px;font-weight:700;color:white;margin-bottom:4px;">Anonymisation</div>'
            '<div style="font-size:11px;font-weight:400;color:rgba(255,255,255,0.4);line-height:1.5;">DPDP Act 2023 &middot; two-step PII removal</div>'
            '</div>'

            '<div style="background-color:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-top:2px solid #10b981;border-radius:10px;padding:14px;">'
            '<div style="font-size:11px;font-weight:700;color:#34d399;letter-spacing:.1em;text-transform:uppercase;margin-bottom:4px;">02 &middot; Intelligence</div>'
            '<div style="font-size:13px;font-weight:700;color:white;margin-bottom:4px;">Summarisation</div>'
            '<div style="font-size:11px;font-weight:400;color:rgba(255,255,255,0.4);line-height:1.5;">SAE &middot; checklists &middot; meeting audio</div>'
            '</div>'

            '<div style="background-color:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-top:2px solid #8b5cf6;border-radius:10px;padding:14px;">'
            '<div style="font-size:11px;font-weight:700;color:#a78bfa;letter-spacing:.1em;text-transform:uppercase;margin-bottom:4px;">03 &middot; Validation</div>'
            '<div style="font-size:13px;font-weight:700;color:white;margin-bottom:4px;">Completeness Check</div>'
            '<div style="font-size:11px;font-weight:400;color:rgba(255,255,255,0.4);line-height:1.5;">20 mandatory fields &middot; RAG flagging</div>'
            '</div>'

            '<div style="background-color:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-top:2px solid #f59e0b;border-radius:10px;padding:14px;">'
            '<div style="font-size:11px;font-weight:700;color:#fbbf24;letter-spacing:.1em;text-transform:uppercase;margin-bottom:4px;">04 &middot; Triage</div>'
            '<div style="font-size:13px;font-weight:700;color:white;margin-bottom:4px;">Classification</div>'
            '<div style="font-size:11px;font-weight:400;color:rgba(255,255,255,0.4);line-height:1.5;">SAE severity &middot; duplicate detection</div>'
            '</div>'

            '<div style="background-color:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-top:2px solid #0ea5e9;border-radius:10px;padding:14px;">'
            '<div style="font-size:11px;font-weight:700;color:#38bdf8;letter-spacing:.1em;text-transform:uppercase;margin-bottom:4px;">05 &middot; Diff Engine</div>'
            '<div style="font-size:13px;font-weight:700;color:white;margin-bottom:4px;">Version Compare</div>'
            '<div style="font-size:11px;font-weight:400;color:rgba(255,255,255,0.4);line-height:1.5;">Semantic + structural dossier diff</div>'
            '</div>'

            '<div style="background-color:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-top:2px solid #ec4899;border-radius:10px;padding:14px;">'
            '<div style="font-size:11px;font-weight:700;color:#f472b6;letter-spacing:.1em;text-transform:uppercase;margin-bottom:4px;">06 &middot; Generation</div>'
            '<div style="font-size:13px;font-weight:700;color:white;margin-bottom:4px;">Inspection Report</div>'
            '<div style="font-size:11px;font-weight:400;color:rgba(255,255,255,0.4);line-height:1.5;">Typed / audio &#8594; CDSCO GCP report</div>'
            '</div>'

            '</div>'

            '<div style="display:flex;gap:6px;flex-wrap:wrap;padding-top:14px;border-top:1px solid rgba(255,255,255,0.07);">'
            '<span style="font-size:11px;font-weight:600;color:#4ade80;background-color:rgba(74,222,128,0.08);border:1px solid rgba(74,222,128,0.2);border-radius:20px;padding:3px 10px;">&#10003; DPDP Act 2023</span>'
            '<span style="font-size:11px;font-weight:600;color:#4ade80;background-color:rgba(74,222,128,0.08);border:1px solid rgba(74,222,128,0.2);border-radius:20px;padding:3px 10px;">&#10003; NDCT Rules 2019</span>'
            '<span style="font-size:11px;font-weight:600;color:#4ade80;background-color:rgba(74,222,128,0.08);border:1px solid rgba(74,222,128,0.2);border-radius:20px;padding:3px 10px;">&#10003; ICMR GCP</span>'
            '<span style="font-size:11px;font-weight:600;color:#4ade80;background-color:rgba(74,222,128,0.08);border:1px solid rgba(74,222,128,0.2);border-radius:20px;padding:3px 10px;">&#10003; MeitY AI Ethics</span>'
            '</div>'

            '</div>',
            unsafe_allow_html=True,
        )

    # ── RIGHT COLUMN — st.form only, zero unclosed HTML ───────────────────────
    with _rcol:
        # IndiaAI + CDSCO badge — single line
        st.markdown("""
<div style="font-family:'Inter',sans-serif;">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:36px;flex-wrap:nowrap;">
    <div style="background:rgba(255,255,255,0.07);border:1px solid rgba(255,255,255,0.12);border-radius:8px;padding:5px 10px;font-size:9px;font-weight:800;color:rgba(255,255,255,0.6);letter-spacing:.06em;text-align:center;line-height:1.4;flex-shrink:0;">India<br>AI</div>
    <div style="width:1px;height:20px;background:rgba(255,255,255,0.1);flex-shrink:0;"></div>
    <div style="background:rgba(255,255,255,0.07);border:1px solid rgba(255,255,255,0.12);border-radius:8px;padding:5px 10px;font-size:9px;font-weight:800;color:rgba(255,255,255,0.6);letter-spacing:.06em;text-align:center;line-height:1.4;flex-shrink:0;">CD<br>SCO</div>
    <div style="flex:1;">
      <div style="font-size:10px;font-weight:700;color:rgba(255,153,51,0.9);letter-spacing:.04em;">Health Innovation Acceleration</div>
      <div style="font-size:10px;color:rgba(255,255,255,0.3);">Hackathon 2026 · Stage 1</div>
    </div>
  </div>
  <div style="width:32px;height:3px;background:linear-gradient(90deg,#FF9933,rgba(255,153,51,0.2));border-radius:2px;margin-bottom:16px;"></div>
  <div style="font-size:11px;font-weight:700;color:rgba(255,255,255,0.35);letter-spacing:.14em;text-transform:uppercase;margin-bottom:8px;">Authorised access only</div>
  <div style="font-size:26px;font-weight:800;color:white;margin-bottom:28px;letter-spacing:-0.5px;">Welcome back</div>
</div>
""", unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            _uname = st.text_input("Username", placeholder="Username", key="login_uname")
            _pwd   = st.text_input("Password", placeholder="Password",
                                   type="password", key="login_pwd")
            if st.session_state["_login_failed"]:
                st.markdown('<p style="color:#f87171;font-size:11px;margin:2px 0 6px;">⚠ Invalid credentials. Please try again.</p>',
                            unsafe_allow_html=True)
            _submitted = st.form_submit_button("Sign in →", use_container_width=True)

        st.markdown("""
<div style="margin-top:24px;padding-top:20px;border-top:1px solid rgba(255,255,255,0.06);">
  <div style="font-size:10px;color:rgba(255,255,255,0.22);line-height:1.8;text-align:center;">
    Authorised CDSCO personnel only · All sessions are logged for compliance<br>
    <span style="color:rgba(255,153,51,0.45);font-weight:600;">Nirnay © 2026 · IndiaAI / CDSCO Hackathon</span>
  </div>
</div>
""", unsafe_allow_html=True)

        if _submitted:
            if _uname.strip() == VALID_USER and _pwd == VALID_PASS:
                st.session_state["logged_in"]     = True
                st.session_state["_login_failed"] = False
                st.rerun()
            else:
                st.session_state["_login_failed"] = True
                st.rerun()

    st.stop()

# ── Past login gate ───────────────────────────────────────────────────────────
render_sidebar()
case = get_active_case()


def go_to(screen_name: str) -> None:
    set_screen(screen_name)
    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TOP BAR
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="background-color:white;border-radius:12px;padding:14px 22px;margin-bottom:12px;box-shadow:0 1px 4px rgba(0,0,0,0.08);border:1px solid #e2e8f0;display:flex;align-items:center;gap:14px;">
  <div style="width:34px;height:34px;border-radius:9px;background-color:#003087;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" stroke="white" stroke-width="2.2" stroke-linejoin="round"/></svg>
  </div>
  <span style="font-size:20px;font-weight:800;color:#0a2240;letter-spacing:-0.5px;">Nirnay</span>
  <span style="font-size:12px;color:#9ca3af;border-left:1px solid #e5e7eb;padding-left:14px;margin-left:2px;">CDSCO AI Review Platform</span>
  <span style="font-size:10px;font-weight:700;color:#f97316;background-color:#fff7ed;border:1px solid #fed7aa;border-radius:20px;padding:3px 11px;margin-left:4px;">IndiaAI Hackathon 2026</span>
</div>
""", unsafe_allow_html=True)


# ── Always-visible nav bar: case selector + workflow breadcrumb ───────────────
screen = render_top_nav()

# Sign-out (tucked right, below nav bar)
_so_col1, _so_col2 = st.columns([11, 1])
with _so_col2:
    if st.button("Sign out", key="signout"):
        st.session_state["logged_in"] = False
        st.query_params.clear()
        st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN TABS — Features + Workflow
# ═══════════════════════════════════════════════════════════════════════════════
(t_cmd_dash, t_doc_intake, t_anon, t_sum, t_comp, t_cls, t_cmp, t_sae_review,
 t_audit_trail) = st.tabs([
    "🖥️ Command Dashboard",
    "📥 Document Intake",
    "🔒 Protected View",
    "📄 Summarisation",
    "✅ Completeness Check",
    "🏷️ Classification",
    "🔍 Version Compare",
    "🚨 SAE Review",
    "📑 Audit Trail",
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
# TAB 1 — ANONYMISATION (Protected View)
# ═══════════════════════════════════════════════════════════════════════════════
with t_anon:
    render_banner("Protected View", "PII/PHI detection and anonymisation · Two-step DPDP Act 2023 process · Full audit log")
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
    st.markdown('</div>', unsafe_allow_html=True)

    c1, c2, _ = st.columns([1,1,3])
    with c1: run_anon = st.button("Analyse & protect document", type="primary", use_container_width=True)
    with c2:
        if st.button("🗑 Clear", use_container_width=True, key="anon_clear"):
            st.session_state["anon_text"] = st.session_state["anon_textarea"] = ""
            st.rerun()

    if run_anon:
        content = (st.session_state.get("anon_text") or st.session_state.get("anon_textarea","")).strip()
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
    render_banner("Summarisation", "Structured summaries for SAE narratives · SUGAM checklists · Meeting transcripts")
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
    st.markdown('</div>', unsafe_allow_html=True)

    c1, c2, _ = st.columns([1,1,3])
    with c1: run_sum = st.button("Summarise document", type="primary", use_container_width=True)
    with c2:
        if st.button("🗑 Clear ", use_container_width=True, key="sum_clear"):
            st.session_state["sum_text"] = st.session_state["sum_ta"] = ""
            st.rerun()

    if run_sum:
        content = (st.session_state.get("sum_text") or st.session_state.get("sum_ta","")).strip()
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
                    "URGENT": f"Immediate escalation to DCGI required. {r['timeline']} report applicable under NDCT Rules 2019.",
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
    render_banner("Completeness Check", "NDCT Rules 2019 / Form CT mandatory field assessment · RAG status · Approve / Return / Reject")
    st.markdown("""
<div class="sec-hd">
  <div class="sec-ic ic-purple">✅</div>
  <div><h2>Completeness Assessment — NDCT Rules 2019 / Form CT</h2>
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
        st.markdown('</div>', unsafe_allow_html=True)
    with col_b:
        app_id = st.text_input("Application ID", placeholder="SUGAM-CT-2024-0892")
        st.markdown("<br>", unsafe_allow_html=True)
        run_comp = st.button("✅ Check Completeness", type="primary", use_container_width=True)

    if run_comp:
        content = (st.session_state.get("comp_text") or st.session_state.get("comp_ta","")).strip()
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

    st.markdown("---")
    st.markdown("**Reviewer Actions**")
    cc1, cc2, cc3, cc4 = st.columns(4)
    with cc1:
        if st.button("Confirm Reviewer Action", use_container_width=True, key="comp_confirm"):
            confirm_reviewer_action("Completeness Check", "Reviewer confirmed completeness assessment", "Completeness accepted.", app_id or "unknown", confidence=0.91)
            st.success("Confirmed.")
    with cc2:
        if st.button("Escalate Low-Confidence", use_container_width=True, key="comp_escalate"):
            confirm_reviewer_action("Completeness Check", "Escalated", "Escalated due to critical missing fields.", app_id or "unknown", confidence=0.91, final_status="Escalated")
            st.warning("Escalated.")
    with cc3:
        if st.button("Create Review Packet", use_container_width=True, key="comp_packet"):
            pkt_comp = generate_audit_packet()
            st.success("Review packet generated.")
    with cc4:
        if st.button("Open Audit Trail", use_container_width=True, key="comp_audit"):
            go_to("Audit Trail")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════════
with t_cls:
    render_banner("Classification", "SAE severity grading · ICD-10 mapping · Session-based duplicate detection")
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
        content = (st.session_state.get("class_text") or st.session_state.get("class_ta","")).strip()
        if not content:
            st.markdown('<div class="rc warn">Please upload or paste an SAE report first.</div>', unsafe_allow_html=True)
        else:
            r = classify_sae(content)
            risk_map = {"DEATH":"Critical","DISABILITY":"High","HOSPITALISATION":"Medium","OTHERS":"Low"}
            action_map = {
                "DEATH":          "Expedited 7-day report mandatory. Immediate notification to DCGI and Ethics Committee required under NDCT Rules 2019.",
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
    render_banner("Version Compare", "Semantic document diff · Substantive vs administrative change flagging · Downloadable report")
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
    with cv2:
        st.markdown("**Version 2 — Updated**")
        v2f = st.file_uploader("Upload V2", type=["docx","pdf","txt"], key="v2f")
        if v2f:
            t, e = extract_text(v2f)
            if not e and t.strip():
                st.session_state["v2_text"] = st.session_state["v2ta"] = t
                st.success(f"✓ {v2f.name}")
        st.text_area("or paste V2", height=200, key="v2ta", placeholder="Updated document...")

    c1, _, _ = st.columns([1,1,3])
    with c1: run_cmp = st.button("🔍 Compare Documents", type="primary", use_container_width=True)

    if run_cmp:
        t1c = (st.session_state.get("v1_text") or st.session_state.get("v1ta","")).strip()
        t2c = (st.session_state.get("v2_text") or st.session_state.get("v2ta","")).strip()
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
# INSPECTION REPORT — removed from ribbon per spec; logic preserved for audit
# ═══════════════════════════════════════════════════════════════════════════════
# (Content retained below for reference; no longer rendered in a tab)
if False:  # Inspection Report tab removed from ribbon
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
# REVIEW WORKFLOW — routing logic; functions defined here, called from ribbon tabs
# ═══════════════════════════════════════════════════════════════════════════════
if True:  # scope block — functions promoted to module level via exec pattern

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

    # ── Global action button group — pinned bottom of each reviewer screen ─────
    def _global_action_buttons(module_label: str, doc_name: str, confidence: float = 0.92) -> None:
        """Consistent 4-button action group rendered at the bottom of each reviewer screen."""
        st.markdown("---")
        st.markdown("**Reviewer Actions**")
        ga1, ga2, ga3, ga4 = st.columns(4)
        with ga1:
            if st.button("Confirm Reviewer Action", use_container_width=True, key=f"gab_confirm_{module_label}"):
                confirm_reviewer_action(module_label, f"Reviewer confirmed {module_label}", "Action confirmed.", doc_name, confidence=confidence)
                st.success("Confirmed.")
        with ga2:
            if st.button("Escalate Low-Confidence", use_container_width=True, key=f"gab_escalate_{module_label}"):
                confirm_reviewer_action(module_label, "Escalated", "Escalated due to low confidence.", doc_name, confidence=confidence, final_status="Escalated")
                st.warning("Escalated.")
        with ga3:
            if st.button("Create Review Packet", use_container_width=True, key=f"gab_packet_{module_label}"):
                if module_label == "SAE Review":
                    pkt = create_sae_packet(); st.success("SAE packet created.")
                elif module_label == "Version Compare":
                    pkt = create_compare_packet(); st.success("Comparison packet created.")
                else:
                    pkt = generate_audit_packet(); st.success("Review packet generated.")
        with ga4:
            if st.button("Open Audit Trail", use_container_width=True, key=f"gab_audit_{module_label}"):
                go_to("Audit Trail")

    # Route map — defined at module level (if True: doesn't create a new scope)
    WORKFLOW_ROUTES = {
        "Command Dashboard": command_dashboard,
        "Document Intake":   document_intake,
        "Protected View":    protected_view_screen,
        "SAE Review":        sae_review_screen,
        "Version Compare":   version_compare_screen,
        "Audit Trail":       audit_trail_screen,
    }

# Render the selected workflow screen inside the Command Dashboard ribbon tab
with t_cmd_dash:
    render_banner("CDSCO Review Workflow", "Full reviewer pipeline: intake → protected view → SAE review → version compare → audit trail.")
    WORKFLOW_ROUTES[screen]()
    if screen in ("Protected View", "SAE Review", "Version Compare"):
        _doc_ref = case["documents"].get(case.get("selected_document_id", ""), {}).get("name", case["packet_id"])
        _global_action_buttons(screen, _doc_ref)

# ── New ribbon tabs: Document Intake, SAE Review, Audit Trail ─────────────

with t_doc_intake:
    render_banner("Document Intake", "Select and classify the incoming case packet document before routing to review.")
    case2 = get_active_case()
    doc_ids2  = list(case2["documents"].keys())
    selected2 = st.selectbox("Case packet document", options=doc_ids2,
                             index=doc_ids2.index(case2["selected_document_id"]),
                             format_func=lambda d: case2["documents"][d]["name"],
                             key="di_tab_selectbox")
    if selected2 != case2["selected_document_id"]:
        case2["selected_document_id"] = selected2; save_active_case(case2)
    sel_doc2 = case2["documents"][case2["selected_document_id"]]
    st.markdown("### Intake controls")
    dti1, dti2, dti3, dti4 = st.columns(4)
    with dti1:
        if st.button("Run classification", use_container_width=True, key="di_tab_cls"): run_classification(); st.success("Classification recorded.")
    with dti2:
        if st.button("Confirm reviewer action", use_container_width=True, key="di_tab_confirm"):
            confirm_reviewer_action("Document Intake","Reviewer confirmed intake assessment","Classification accepted.",sel_doc2["name"],confidence=sel_doc2["confidence"]); st.success("Confirmation recorded.")
    with dti3:
        if st.button("Escalate low-confidence", use_container_width=True, key="di_tab_esc"):
            confirm_reviewer_action("Document Intake","Escalated",sel_doc2.get("classification",{}).get("escalation_recommendation","Escalation requested."),sel_doc2["name"],confidence=sel_doc2["confidence"],final_status="Escalated"); st.warning("Escalation recorded.")
    with dti4:
        if st.button("→ Protected View", use_container_width=True, key="di_tab_pv"): go_to("Protected View")
    dt1b, dt2b, dt3b = st.tabs(["Classification","Synopsis","Source"])
    with dt1b:
        clf2 = case2["document_classification"] or sel_doc2.get("classification",{})
        with st.container(border=True):
            st.write(f"**Probable type:** {clf2.get('probable_type','Pending')}"); st.write(f"**Severity:** {clf2.get('severity',sel_doc2['risk_level'])}")
            st.write(f"**Duplicate warning:** {clf2.get('duplicate_warning','Pending')}"); st.write(f"**Escalation:** {clf2.get('escalation_recommendation','Pending')}"); st.write(f"**Confidence:** {int(sel_doc2['confidence']*100)}%")
    with dt2b:
        syn2 = case2["structured_synopsis"] or sel_doc2.get("synopsis",{})
        with st.container(border=True):
            st.write(f"**Headline:** {syn2.get('headline','Pending')}"); st.write(syn2.get("summary","Run classification to generate synopsis."))
            for sig2 in syn2.get("key_signals",[]): st.write(f"- {sig2}")
            if syn2.get("reviewer_prompt"): st.info(syn2["reviewer_prompt"])
    with dt3b:
        with st.container(border=True): st.write(sel_doc2["raw_text"])

with t_sae_review:
    render_banner("SAE Review", "Review SAE classification output, resolve missing information, and confirm or escalate.")
    case3 = get_active_case()
    sae3 = case3["sae_review"]
    with st.container(border=True):
        sr1,sr2,sr3 = st.columns(3)
        with sr1: st.write(f"**Patient:** {sae3['patient_profile']}"); st.write(f"**Event:** {sae3['event']}")
        with sr2: st.write(f"**Seriousness:** {sae3['seriousness']}"); st.write(f"**Causality:** {sae3['causality']}")
        with sr3: st.write(f"**Action:** {sae3['action_taken']}"); st.write(f"**Outcome:** {sae3['outcome']}")
    st.markdown("**Missing information**")
    for item3 in sae3["missing_info"]:
        item3["resolved"] = st.checkbox(item3["item"], value=item3["resolved"], key=f"srt_mi_{item3['item']}")
    sae3["reviewer_notes"] = st.text_area("Reviewer notes", value=sae3["reviewer_notes"], height=80, key="srt_notes")
    save_active_case(case3)
    st.markdown("---"); st.markdown("**Reviewer Actions**")
    srt1,srt2,srt3,srt4 = st.columns(4)
    with srt1:
        if st.button("Confirm Reviewer Action", use_container_width=True, key="srt_confirm"):
            confirm_reviewer_action("SAE Review","Reviewer confirmed SAE output","SAE output accepted.",case3["documents"]["sae"]["name"],confidence=0.94); st.success("Confirmed.")
    with srt2:
        if st.button("Escalate Low-Confidence", use_container_width=True, key="srt_esc"):
            confirm_reviewer_action("SAE Review","Escalated","Escalated due to source gaps.",case3["documents"]["sae"]["name"],confidence=0.9,final_status="Escalated"); st.warning("Escalated.")
    with srt3:
        if st.button("Create Review Packet", use_container_width=True, key="srt_pkt"):
            pkt3 = create_sae_packet(); st.success("SAE packet created."); st.text_area("Generated packet", value=pkt3, height=200, key="srt_pkt_out")
    with srt4:
        if st.button("Open Audit Trail", use_container_width=True, key="srt_audit"): go_to("Audit Trail")

with t_audit_trail:
    render_banner("Audit Trail", "Full audit log of all AI outputs and reviewer decisions for the active case packet.")
    case4 = get_active_case()
    df4 = audit_dataframe(case4)
    search4 = st.text_input("Search audit events", key="at_tab_search")
    if search4:
        low4 = search4.lower()
        df4  = df4[df4.astype(str).apply(lambda col: col.str.lower().str.contains(low4, na=False)).any(axis=1)]
    st.dataframe(df4, use_container_width=True, hide_index=True)
    for evt4 in case4["audit_events"][-5:][::-1]:
        with st.expander(f"{evt4['timestamp']} | {evt4['module']} | {evt4['reviewer_action']}"):
            st.write(f"**Action:** {evt4['action']}"); st.write(f"**Confidence:** {evt4['confidence']}")
            st.write(f"**Status:** {evt4['final_status']}"); st.write(f"**Source:** {evt4['source_reference']}"); st.write(f"**Detail:** {evt4['note']}")
    with st.container(border=True):
        st.write(f"**Protected view:** {case4['protected_view']['escalation_status']}")
        st.write(f"**SAE packet ready:** {'Yes' if case4['sae_review']['review_packet'] else 'No'}")
        st.write(f"**Compare packet ready:** {'Yes' if case4['compare_review']['review_packet'] else 'No'}")
        st.write(f"**Reviewer confirmations:** {len(case4['reviewer_decisions'])}")
    st.markdown("---"); st.markdown("**Reviewer Actions**")
    att1,att2,att3,att4 = st.columns(4)
    with att1:
        if st.button("Confirm Reviewer Action", use_container_width=True, key="att_confirm"):
            confirm_reviewer_action("Audit Trail","Reviewer confirmed audit record","Audit record accepted.",case4["packet_id"]); st.success("Confirmed.")
    with att2:
        if st.button("Escalate Low-Confidence", use_container_width=True, key="att_esc"):
            confirm_reviewer_action("Audit Trail","Escalated","Escalated from audit review.",case4["packet_id"],final_status="Escalated"); st.warning("Escalated.")
    with att3:
        if st.button("Create Review Packet", use_container_width=True, key="att_pkt"):
            pkt4 = generate_audit_packet(); st.success("Audit packet generated.")
            st.download_button("⬇ Audit Packet (JSON)", to_json_bytes(pkt4),
                               file_name=f"{case4['case_id']}_audit_packet.json", mime="application/json", use_container_width=True)
    with att4:
        st.download_button("⬇ Audit Log (CSV)", to_csv_bytes(case4["audit_events"]),
                           file_name=f"{case4['case_id']}_audit_log.csv", mime="text/csv", use_container_width=True)
    st.info(APP_DISCLAIMER)


# ── Compliance ribbon ─────────────────────────────────────────────────────────
compliance_ribbon()
