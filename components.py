"""
components.py — Nirnay · CDSCO AI Hackathon 2026
-------------------------------------------------
UI components, session state management, sidebar, audit trail helpers.
Imports from demo_data.py (sample packets) and engine.py (processing).
"""

from __future__ import annotations

import csv
import io
import json
from copy import deepcopy
from datetime import datetime

import pandas as pd
import streamlit as st

from demo_data import (
    APP_DISCLAIMER,
    APP_SUBTITLE,
    APP_TITLE,
    DEMO_MODE_LABEL,
    LEADERSHIP_METRICS,
    SCREENS,
    get_case_library,
)

# ── Re-export engine availability flags so app.py can check ──────────────────
from engine import CLAUDE_OK, CLAUDE_MODEL  # noqa: F401


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG & STYLES
# ═══════════════════════════════════════════════════════════════════════════════

def configure_page() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="⚖️", layout="wide",
                       initial_sidebar_state="expanded")


def apply_styles() -> None:
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
#MainMenu,footer,header{visibility:hidden;}
.stApp{background-color:#f0f3f8;}

section[data-testid="stSidebar"]{background:linear-gradient(180deg,#001f5b 0%,#003087 60%,#004db3 100%);}
section[data-testid="stSidebar"] *{color:white!important;}
section[data-testid="stSidebar"] .stMarkdown p{color:rgba(255,255,255,0.8)!important;}
section[data-testid="stSidebar"] .stSelectbox>div>div{background:rgba(255,255,255,0.1)!important;border:1px solid rgba(255,255,255,0.25)!important;border-radius:8px!important;}

.hero{background:linear-gradient(135deg,#001f5b 0%,#003087 55%,#0052cc 100%);border-radius:16px;padding:28px 36px;margin-bottom:18px;box-shadow:0 4px 24px rgba(0,48,135,0.18);}
.hero h1{color:white;font-size:28px;font-weight:800;margin:0;}
.hero .sub{color:rgba(255,255,255,0.68);font-size:13px;margin:5px 0 0;}
.hero-badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px;}
.hbadge{background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.22);border-radius:20px;padding:4px 12px;font-size:11px;color:rgba(255,255,255,0.9);font-weight:500;}
.hbadge.g{border-color:#4ade80;color:#4ade80;}

.card{background:rgba(255,255,255,0.96);border:1px solid rgba(11,63,117,0.12);border-radius:16px;padding:1rem 1.1rem;box-shadow:0 10px 24px rgba(11,63,117,0.05);margin-bottom:1rem;}
.case-chip{display:inline-block;background:rgba(24,166,184,0.12);color:#0b3f75;border:1px solid rgba(24,166,184,0.24);border-radius:999px;padding:0.2rem 0.55rem;font-size:0.78rem;font-weight:600;}
.small-note{color:#5c6b7a;font-size:0.92rem;}

.sec-hd{display:flex;align-items:center;gap:12px;margin-bottom:20px;padding-bottom:14px;border-bottom:1px solid #e2e8f0;}
.sec-ic{width:42px;height:42px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;}
.ic-blue{background:#dbeafe;}.ic-teal{background:#ccfbf1;}.ic-purple{background:#ede9fe;}
.ic-amber{background:#fef3c7;}.ic-sky{background:#e0f2fe;}.ic-pink{background:#fce7f3;}
.sec-hd h2{font-size:17px;font-weight:600;color:#1e293b;margin:0;}
.sec-hd p{font-size:12px;color:#64748b;margin:2px 0 0;}

.upload-card{background:rgba(255,255,255,0.7);border-radius:14px;padding:20px 22px;box-shadow:0 2px 12px rgba(0,0,0,0.06);margin-bottom:14px;border:1px solid rgba(255,255,255,0.6);}
.upload-card h4{color:#1e293b;font-size:14px;font-weight:600;margin:0 0 10px;}
.or-line{display:flex;align-items:center;gap:10px;margin:12px 0;color:#94a3b8;font-size:12px;}
.or-line::before,.or-line::after{content:'';flex:1;height:1px;background:#e2e8f0;}

.pii-chips{display:flex;flex-wrap:wrap;gap:7px;margin:12px 0;}
.chip{display:inline-flex;align-items:center;gap:4px;border-radius:20px;padding:4px 11px;font-size:12px;font-weight:600;}
.cr{background:#fee2e2;color:#991b1b;}.ca{background:#fef3c7;color:#92400e;}
.cb{background:#dbeafe;color:#1e40af;}.cp{background:#ede9fe;color:#5b21b6;}
.ct{background:#ccfbf1;color:#065f46;}.cg{background:#f1f5f9;color:#475569;}

.rc{background:white;border-radius:10px;padding:14px 18px;box-shadow:0 1px 4px rgba(0,0,0,0.06);margin:8px 0;border-left:4px solid #003087;}
.rc.ok{border-left-color:#16a34a;background:#f0fdf4;}
.rc.warn{border-left-color:#d97706;background:#fffbeb;}
.rc.err{border-left-color:#dc2626;background:#fef2f2;}
.rc.info{border-left-color:#0284c7;background:#f0f9ff;}

.tw{background:white;border-radius:10px;padding:4px;box-shadow:0 1px 4px rgba(0,0,0,0.06);margin:8px 0;}
.dup-session{background:#f0f9ff;border:1px solid #bae6fd;border-radius:12px;padding:14px 18px;margin-bottom:12px;font-size:13px;color:#0369a1;}
.audio-note{background:#fef9c3;border:1px solid #fbbf24;border-radius:8px;padding:10px 14px;font-size:12px;color:#78350f;margin:8px 0;}

.stTabs [data-baseweb="tab-list"]{background:#0a2240;border-radius:10px;padding:4px;gap:2px;}
.stTabs [data-baseweb="tab"]{border-radius:7px;font-size:12px;font-weight:500;color:rgba(255,255,255,0.55);padding:8px 14px;}
.stTabs [aria-selected="true"]{background:#0077b6!important;color:white!important;}
.stTabs [data-baseweb="tab"]:hover{color:white!important;}
.stTabs [data-baseweb="tab-border"]{display:none;}
.stTabs [data-baseweb="tab-panel"]{background:white;border-radius:0 0 12px 12px;padding:20px !important;}

.stButton>button[kind="primary"]{background:#0a2240!important;color:white!important;border:none!important;border-radius:8px!important;font-weight:600!important;font-size:12px!important;padding:8px 16px!important;}
.stDownloadButton>button{border-radius:8px!important;border:1.5px solid #003087!important;color:#003087!important;font-weight:500!important;font-size:13px!important;}
.stTextArea textarea{border:1.5px solid #e2e8f0!important;border-radius:10px!important;font-size:13px!important;background:#fafbfc!important;}
[data-testid="stMetricValue"]{font-size:24px!important;font-weight:700!important;}
[data-testid="stMetricLabel"]{font-size:12px!important;color:#64748b!important;}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════

def init_state() -> None:
    # Workflow case state
    if "demo_cases" not in st.session_state:
        st.session_state.demo_cases = get_case_library()
    if "active_case_key" not in st.session_state:
        st.session_state.active_case_key = next(iter(st.session_state.demo_cases))
    if "active_case" not in st.session_state:
        st.session_state.active_case = deepcopy(
            st.session_state.demo_cases[st.session_state.active_case_key])
    if "screen" not in st.session_state:
        st.session_state.screen = SCREENS[0]
    if "compare_filter" not in st.session_state:
        st.session_state.compare_filter = "All changes"
    # Feature tab state
    for k in ["anon_text","sum_text","comp_text","class_text","v1_text","v2_text",
              "anon_textarea","sum_ta","comp_ta","class_ta","v1ta","v2ta"]:
        if k not in st.session_state:
            st.session_state[k] = ""
    if "dup_files" not in st.session_state:
        st.session_state["dup_files"] = {}
    if "active_tab" not in st.session_state:
        st.session_state["active_tab"] = 0


def get_active_case() -> dict:
    return st.session_state.active_case


def save_active_case(case: dict) -> None:
    st.session_state.active_case = case


def set_active_case(case_key: str) -> None:
    st.session_state.active_case_key = case_key
    st.session_state.active_case = deepcopy(st.session_state.demo_cases[case_key])


def set_screen(screen: str) -> None:
    st.session_state.screen = screen


def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT TRAIL HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def add_audit_event(module: str, action: str, confidence: float,
                    reviewer_action: str, final_status: str,
                    source_reference: str, note: str) -> None:
    case = get_active_case()
    case["audit_events"].append({
        "timestamp":        timestamp(),
        "module":           module,
        "action":           action,
        "confidence":       round(confidence, 2),
        "reviewer_action":  reviewer_action,
        "final_status":     final_status,
        "source_reference": source_reference,
        "note":             note,
    })
    save_active_case(case)


def confirm_reviewer_action(module: str, decision: str, note: str,
                             source_reference: str, confidence: float = 1.0,
                             final_status: str = "Confirmed") -> None:
    case = get_active_case()
    case["reviewer_decisions"].append({
        "timestamp": timestamp(), "module": module,
        "decision":  decision,   "note": note,
    })
    save_active_case(case)
    add_audit_event(module=module, action="Reviewer confirmation recorded",
                    confidence=confidence, reviewer_action=decision,
                    final_status=final_status, source_reference=source_reference, note=note)


def audit_dataframe(case: dict) -> pd.DataFrame:
    return pd.DataFrame(case["audit_events"])


# ═══════════════════════════════════════════════════════════════════════════════
# WORKFLOW ACTION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def run_classification() -> None:
    case     = get_active_case()
    document = case["documents"][case["selected_document_id"]]
    if "classification" not in document:
        st.warning("This document does not have a seeded classification. Upload a real document to generate AI output.")
        return
    case["document_classification"] = deepcopy(document["classification"])
    case["structured_synopsis"]     = deepcopy(document["synopsis"])
    case["export_readiness"]["classification"] = True
    case["current_stage"] = "Document Intake"
    save_active_case(case)
    add_audit_event("Document Intake", "Classification completed", document["confidence"],
                    "AI output generated", "Generated", document["name"],
                    "Probable document type and structured synopsis recorded on the active case packet.")


def apply_redaction_filters(case: dict) -> str:
    source_text = case["documents"][case["protected_view"]["source_document_id"]]["raw_text"]
    redacted    = source_text
    for entity in case["protected_view"]["entities"]:
        show = case["protected_view"]["category_filters"].get(entity["category"], True)
        if entity["approved"] and show:
            redacted = redacted.replace(entity["value"], entity["replacement"])
    return redacted


def validate_redaction() -> None:
    case          = get_active_case()
    low_conf      = [e["label"] for e in case["protected_view"]["entities"] if e["confidence"] < 0.9]
    approved_count = sum(1 for e in case["protected_view"]["entities"] if e["approved"])
    summary       = (f"{approved_count} identifiers approved for protected review. "
                     f"{len(low_conf)} low-confidence entities remain subject to reviewer confirmation.")
    case["protected_view"]["validated"]         = True
    case["protected_view"]["validation_summary"]= summary
    case["protected_view"]["escalation_status"] = "Escalation required" if low_conf else "No escalation required"
    case["export_readiness"]["protected_view"]  = True
    case["current_stage"] = "Protected View"
    save_active_case(case)
    add_audit_event("Protected View", "Protected view validated", 0.93,
                    "Reviewer confirmation pending", "Validated",
                    case["documents"][case["protected_view"]["source_document_id"]]["name"], summary)


def create_sae_packet() -> str:
    case = get_active_case()
    sae  = case["sae_review"]
    missing = ", ".join(i["item"] for i in sae["missing_info"] if not i["resolved"]) or "None"
    packet  = (f"Nirnay SAE Review Packet\nCase ID: {case['case_id']}\n"
               f"Source: {case['documents']['sae']['name']}\n"
               f"Patient profile: {sae['patient_profile']}\n"
               f"Event: {sae['event']}\nSeriousness: {sae['seriousness']}\n"
               f"Reviewer severity: {sae['severity']}\nCausality: {sae['causality']}\n"
               f"Action taken: {sae['action_taken']}\nOutcome: {sae['outcome']}\n"
               f"Missing information: {missing}\nReviewer notes: {sae['reviewer_notes']}\n"
               f"{APP_DISCLAIMER}")
    case["sae_review"]["review_packet"]    = packet
    case["export_readiness"]["sae_packet"] = True
    case["current_stage"] = "SAE Review"
    save_active_case(case)
    add_audit_event("SAE Review", "SAE review packet created", 0.94, "Packet ready", "Generated",
                    case["documents"]["sae"]["name"],
                    "Structured safety review packet generated from deterministic seeded outputs.")
    return packet


def create_compare_packet() -> str:
    case      = get_active_case()
    amendment = case["documents"]["amendment"]
    lines     = ["Nirnay Version Review Packet", f"Case ID: {case['case_id']}",
                 f"Source: {amendment['name']}", ""]
    for c in amendment["changes"]:
        lines += [f"- {c['area']} | {c['classification']} | {c['impact_level']}",
                  f"  Before: {c['before']}", f"  After: {c['after']}",
                  f"  Regulatory impact: {c['impact']}"]
    lines += ["", APP_DISCLAIMER]
    packet = "\n".join(lines)
    case["compare_review"]["review_packet"]    = packet
    case["export_readiness"]["compare_packet"] = True
    case["current_stage"] = "Version Compare"
    save_active_case(case)
    add_audit_event("Version Compare", "Comparison review packet created",
                    amendment["confidence"], "Packet ready", "Generated", amendment["name"],
                    "Substantive and administrative changes summarised for reviewer use.")
    return packet


def generate_audit_packet() -> dict:
    case   = get_active_case()
    packet = {
        "case_id":              case["case_id"],
        "packet_id":            case["packet_id"],
        "reviewer":             case["reviewer"],
        "status":               case["status"],
        "document_classification": case["document_classification"],
        "structured_synopsis":     case["structured_synopsis"],
        "protected_view": {
            "validated":         case["protected_view"]["validated"],
            "escalation_status": case["protected_view"]["escalation_status"],
            "validation_summary":case["protected_view"]["validation_summary"],
        },
        "sae_review_packet_ready":    bool(case["sae_review"]["review_packet"]),
        "compare_review_packet_ready":bool(case["compare_review"]["review_packet"]),
        "reviewer_decisions": case["reviewer_decisions"],
        "audit_events":       case["audit_events"],
    }
    case["export_readiness"]["audit_packet"] = True
    case["current_stage"] = "Audit Trail"
    save_active_case(case)
    add_audit_event("Audit Trail", "Audit packet generated", 1.0, "Audit packet ready", "Generated",
                    case["packet_id"], "Consolidated audit packet prepared from the active case state.")
    return packet


# ═══════════════════════════════════════════════════════════════════════════════
# RENDER HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def render_banner(title: str, subtitle: str) -> None:
    st.markdown(f"""
<div class="hero">
  <p style="font-size:0.8rem;text-transform:uppercase;letter-spacing:0.04em;color:rgba(255,255,255,0.82);">{DEMO_MODE_LABEL}</p>
  <h1>{title}</h1>
  <p class="sub">{subtitle}</p>
  <div class="hero-badges">
    <span class="hbadge g">✓ DPDP Act 2023</span>
    <span class="hbadge g">✓ NDCT Rules 2019</span>
    <span class="hbadge g">✓ ICMR GCP</span>
    <span class="hbadge g">✓ MeitY AI Ethics</span>
  </div>
  <p style="margin-top:0.8rem;font-size:0.85rem;color:rgba(255,255,255,0.88);">{APP_DISCLAIMER}</p>
</div>
""", unsafe_allow_html=True)


def render_top_nav() -> str:
    """Returns the active workflow screen from session state. No ribbon rendered."""
    return st.session_state.get("screen", SCREENS[0])


def render_sidebar() -> str:
    case = get_active_case()
    with st.sidebar:
        st.markdown(f"## {APP_TITLE}")
        st.caption(APP_SUBTITLE)

        # Judge notice
        st.markdown("""
<div style="background:rgba(255,153,51,0.15);border:1px solid rgba(255,153,51,0.4);border-radius:8px;padding:10px 12px;margin:8px 0;">
  <p style="font-size:10px;font-weight:700;color:#FF9933;margin:0 0 4px;">📋 FOR JUDGES — EVALUATION GUIDE</p>
  <p style="font-size:10px;color:rgba(255,255,255,0.85);margin:0;line-height:1.5;">
  Sample packets are pre-loaded for quick review.<br>
  Upload <b>your own documents</b> in any feature tab — the AI engines process your files live.<br>
  Use <b>Review workflow</b> below to walk through the full CDSCO case review pipeline.
  </p>
</div>
""", unsafe_allow_html=True)

        case_key = st.selectbox(
            "Active sample packet",
            options=list(st.session_state.demo_cases.keys()),
            index=list(st.session_state.demo_cases.keys()).index(st.session_state.active_case_key),
            format_func=lambda k: st.session_state.demo_cases[k]["title"],
        )
        if case_key != st.session_state.active_case_key:
            set_active_case(case_key)
            case = get_active_case()

        screen = st.radio("Review workflow", options=SCREENS,
                          index=SCREENS.index(st.session_state.screen))
        st.session_state.screen = screen

        with st.expander("Current case packet", expanded=True):
            st.write(f"**Case ID:** {case['case_id']}")
            st.write(f"**Packet ID:** {case['packet_id']}")
            st.write(f"**Reviewer:** {case['reviewer']}")
            st.write(f"**Status:** {case['status']}")
            st.write(f"**Stage:** {case['current_stage']}")

        st.info(APP_DISCLAIMER)
    return screen


def render_metrics() -> None:
    cols = st.columns(3)
    for i, m in enumerate(LEADERSHIP_METRICS):
        with cols[i % 3]:
            st.metric(m["label"], m["value"], help=m["detail"])


def render_case_header(case: dict) -> None:
    st.markdown(f"""
<div class="card">
  <span class="case-chip">{case['packet_id']}</span>
  <h3 style="margin-top:0.75rem;">{case['title']}</h3>
  <p class="small-note">Reviewer: {case['reviewer']} | Status: {case['status']} | Stage: {case['current_stage']}</p>
</div>
""", unsafe_allow_html=True)


def ai_recommendation_card(finding: str, risk_level: str, action: str, detail: str = "") -> None:
    colours = {
        "Critical": ("background:#fee2e2;border-color:#fca5a5;", "color:#991b1b;background:#fecaca;"),
        "High":     ("background:#fff7ed;border-color:#fed7aa;", "color:#9a3412;background:#ffedd5;"),
        "Medium":   ("background:#fefce8;border-color:#fef08a;", "color:#854d0e;background:#fef9c3;"),
        "Low":      ("background:#f0fdf4;border-color:#bbf7d0;", "color:#166534;background:#dcfce7;"),
    }
    cs, bs = colours.get(risk_level, colours["Medium"])
    st.markdown(f"""
<div style="border-radius:12px;padding:18px 22px;margin:14px 0;border:1px solid;{cs}border-left:5px solid #0a2240;">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap;">
    <div style="flex:1;">
      <div style="font-size:10px;font-weight:700;color:#0a2240;letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px;">AI Recommendation</div>
      <div style="font-size:15px;font-weight:700;color:#0a2240;margin-bottom:4px;">{finding}</div>
      <div style="font-size:13px;color:#475569;line-height:1.5;">{action}</div>
      {f'<div style="font-size:11px;color:#64748b;margin-top:5px;">{detail}</div>' if detail else ""}
    </div>
    <div style="text-align:center;flex-shrink:0;">
      <div style="font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;padding:6px 16px;border-radius:6px;{bs}">{risk_level} Risk</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


def compliance_ribbon() -> None:
    st.markdown("""
<div style="margin-top:32px;border-top:1px solid #e2e8f0;padding:10px 0;display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
  <span style="font-size:9px;font-weight:600;color:#94a3b8;">✓ DPDP Act 2023</span>
  <span style="color:#e2e8f0;">·</span>
  <span style="font-size:9px;font-weight:600;color:#94a3b8;">✓ NDCT Rules 2019</span>
  <span style="color:#e2e8f0;">·</span>
  <span style="font-size:9px;font-weight:600;color:#94a3b8;">✓ ICMR Guidelines</span>
  <span style="color:#e2e8f0;">·</span>
  <span style="font-size:9px;font-weight:600;color:#94a3b8;">✓ MeitY AI Ethics</span>
  <span style="margin-left:auto;font-size:9px;color:#cbd5e1;">© 2026 Nirnay — Built for IndiaAI/CDSCO Hackathon</span>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

def to_json_bytes(payload: object) -> bytes:
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def to_csv_bytes(rows: list[dict]) -> bytes:
    if not rows:
        return b""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")
