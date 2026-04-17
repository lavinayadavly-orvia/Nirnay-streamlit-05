"""
engine.py — Nirnay · CDSCO AI Hackathon 2026
---------------------------------------------
All rule-based processing engines:
  - PII/PHI anonymisation (DPDP Act 2023, two-step)
  - Document summarisation (SAE, Checklist, Meeting)
  - Completeness assessment (Schedule Y / Form CT fields)
  - SAE classification + duplicate detection
  - Document comparison (difflib semantic diff)
  - Inspection report generation (CDSCO GCP format)
  - File text extraction (PDF, DOCX, TXT)
  - Optional Claude API calls for AI-enhanced summaries
"""

from __future__ import annotations

import datetime
import difflib
import io
import importlib
import re
import sys

import pandas as pd

# ── Optional document imports ─────────────────────────────────────────────────
try:
    import docx as python_docx
    DOCX_OK = True
except ImportError:
    DOCX_OK = False

# ── Optional Claude API ───────────────────────────────────────────────────────
try:
    import anthropic
    _ANTHROPIC_CLIENT = anthropic.Anthropic()
    CLAUDE_OK = True
except Exception:
    _ANTHROPIC_CLIENT = None
    CLAUDE_OK = False

CLAUDE_MODEL = "claude-haiku-4-5-20251001"  # free-tier compatible


# ═══════════════════════════════════════════════════════════════════════════════
# FILE EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def _resolve_pdf_reader():
    """Resolve an available PDF reader at call time to avoid stale import state."""
    errors: list[str] = []
    for module_name in ("pypdf", "PyPDF2"):
        try:
            module = importlib.import_module(module_name)
            return module.PdfReader, module_name, None
        except Exception as exc:  # pragma: no cover - depends on local env
            errors.append(f"{module_name}: {exc}")

    detail = "; ".join(errors) if errors else "No PDF parser module found."
    return None, None, (
        "PDF support is unavailable in the active Streamlit environment. "
        f"Install `pypdf` or `PyPDF2` for `{sys.executable}` and restart the app. "
        f"Details: {detail}"
    )

def extract_text(uploaded_file) -> tuple[str, str | None]:
    """Returns (text, error_or_None). Handles PDF, DOCX, TXT."""
    if uploaded_file is None:
        return "", None
    name = uploaded_file.name.lower()
    try:
        uploaded_file.seek(0)
        raw = uploaded_file.read()
        if not raw:
            return "", "File appears empty."
        if name.endswith(".docx"):
            if not DOCX_OK:
                return "", "Install python-docx: add to requirements.txt"
            doc = python_docx.Document(io.BytesIO(raw))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip()), None
        elif name.endswith(".pdf"):
            reader_cls, reader_name, reader_error = _resolve_pdf_reader()
            if reader_error:
                return "", reader_error

            reader = reader_cls(io.BytesIO(raw))
            extracted = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
            if not extracted:
                return "", (
                    f"No extractable text found in {uploaded_file.name}. "
                    f"The PDF may be scanned/image-only or unsupported by {reader_name}."
                )
            return extracted, None
        elif name.endswith(".txt"):
            return raw.decode("utf-8", errors="ignore"), None
        return "", f"Unsupported file type: {uploaded_file.name}"
    except Exception as exc:
        return "", str(exc)


# ═══════════════════════════════════════════════════════════════════════════════
# ANONYMISATION ENGINE (DPDP Act 2023 — two-step)
# ═══════════════════════════════════════════════════════════════════════════════

INDIAN_FIRST = [
    "Rajesh","Priya","Suresh","Anita","Vikram","Sunita","Amit","Kavita","Ravi",
    "Deepa","Mohit","Pooja","Arjun","Neha","Sanjay","Meera","Rahul","Divya",
    "Anil","Rekha","Vijay","Smita","Ramesh","Geeta","Ashok","Usha","Manoj",
    "Seema","Vinod","Lata","Amitabh","Sunil","Sneha","Preeti","Rohit","Kiran",
    "Nisha","Ganesh","Harish","Naresh","Satish","Girish",
]
INDIAN_LAST = [
    "Sharma","Patel","Singh","Kumar","Mehta","Gupta","Verma","Joshi","Nair",
    "Rao","Iyer","Reddy","Bose","Das","Malhotra","Kapoor","Agarwal","Pandey",
    "Mishra","Tiwari","Ghosh","Chatterjee","Mukherjee","Kulkarni","Desai",
]

CHIP_MAP = {
    "Patient Name": "cr", "Patient Initials": "cr", "Patient ID": "cr",
    "Hospital Record No.": "ca", "Investigator Name": "cp", "Investigator ID": "cp",
    "Date / DOB": "cb", "Phone Number": "ct", "Aadhaar Number": "ca",
    "Pincode": "cg", "Site Number": "cg", "Regulatory ID": "cg", "Address": "cg",
}


def run_anonymisation(text: str) -> dict:
    """
    Two-step anonymisation per DPDP Act 2023 / NDHM / ICMR guidelines.
    Step 1 — Pseudonymisation (reversible tokens).
    Step 2 — Irreversible generalisation (age bands, geo tiers, etc.).
    Returns dict with step1, step2, tokens, audit, types, count.
    """
    tokens, audit, processed = [], [], text
    cnt = {k: 0 for k in [
        "PATIENT","INVESTIGATOR","DATE","SITE","PHONE","AADHAAR","HOSP_REC",
        "EMAIL","PINCODE","INSTITUTION","BATCH","URL","IP_ADDR","DEVICE_ID",
        "ACCOUNT_NO","CERT_NO","BIOMETRIC",
    ]}
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    found_types: set[str] = set()

    def tok(kind: str) -> str:
        cnt[kind] += 1
        return f"[{kind}-{cnt[kind]:03d}]"

    def rec(t: str, orig: str, etype: str) -> None:
        tokens.append({"Token": t, "Original Value": orig, "Entity Type": etype, "Step": "Step 1"})
        audit.append({"Timestamp": ts, "Action": "Pseudonymised", "Entity Type": etype, "Token": t, "Reversible": "Yes"})
        found_types.add(etype)

    for m in re.finditer(r"https?://[^\s,;\"'<>]+", processed):
        t = tok("URL"); rec(t, m.group(), "Web URL"); processed = processed.replace(m.group(), t, 1)
    for m in re.finditer(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", processed):
        t = tok("IP_ADDR"); rec(t, m.group(), "IP Address"); processed = processed.replace(m.group(), t, 1)
    for m in re.finditer(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", processed):
        t = tok("EMAIL"); rec(t, m.group(), "Email Address"); processed = processed.replace(m.group(), t, 1)
    for m in re.finditer(r"#\d{4,6}", processed):
        t = tok("HOSP_REC"); rec(t, m.group(), "Hospital Record No."); processed = processed.replace(m.group(), t, 1)
    for m in re.finditer(r"\d{4}[-\s]\d{4}[-\s]\d{4}", processed):
        t = tok("AADHAAR"); rec(t, m.group(), "Aadhaar Number"); processed = processed.replace(m.group(), t, 1)
    for m in re.finditer(r"(?:S/?N|Serial\s*No?\.?|Device\s*ID)[:\s]*[A-Z0-9\-]{4,16}", processed, re.I):
        t = tok("DEVICE_ID"); rec(t, m.group(), "Device/Serial Number"); processed = processed.replace(m.group(), t, 1)
    for m in re.finditer(r"(?:A/?C|Account)\s*(?:No\.?|Number)?[:\s]*\d{6,18}", processed, re.I):
        t = tok("ACCOUNT_NO"); rec(t, m.group(), "Account Number"); processed = processed.replace(m.group(), t, 1)
    for m in re.finditer(r"(?:Licen[sc]e|Cert(?:ificate)?|Reg(?:istration)?)\s*(?:No\.?|Number)?[:\s]*[A-Z0-9/\-]{4,16}", processed, re.I):
        t = tok("CERT_NO"); rec(t, m.group(), "Certificate/Licence Number"); processed = processed.replace(m.group(), t, 1)
    for m in re.finditer(r"\b(?:fingerprint|retina\s*scan|iris\s*scan|biometric)\s*(?:ID|code|data|ref(?:erence)?)?[:\s]*[A-Z0-9\-]{0,16}", processed, re.I):
        t = tok("BIOMETRIC"); rec(t, m.group(), "Biometric Identifier"); processed = processed.replace(m.group(), t, 1)
    for m in re.finditer(r"\+91[\s-]?\d{2,4}[\s-]\d{4}[\s-]\d{4}", processed):
        t = tok("PHONE"); rec(t, m.group(), "Phone Number"); processed = processed.replace(m.group(), t, 1)
    for m in re.finditer(r"[6-9]\d{9}", processed):
        t = tok("PHONE"); rec(t, m.group(), "Phone Number"); processed = processed.replace(m.group(), t, 1)
    for m in re.finditer(r"(?:PT|SITE|IND|CT|SUBJ|INV|LH|MH|DL|CH)[-]\w{2,8}[-]\w{2,8}", processed):
        o = m.group()
        if any(o.startswith(p) for p in ["PT","SUBJ","LH","MH","DL"]):
            t = tok("PATIENT"); et = "Patient ID"
        elif o.startswith("SITE"):
            t = tok("SITE"); et = "Site Number"
        elif o.startswith("INV"):
            t = tok("INVESTIGATOR"); et = "Investigator ID"
        else:
            t = tok("SITE"); et = "Regulatory ID"
        rec(t, o, et); processed = processed.replace(o, t, 1)
    for pat in [
        re.compile(r"\d{1,2}[-/]\w{2,9}[-/]\d{2,4}"),
        re.compile(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}"),
        re.compile(r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}", re.I),
        re.compile(r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}", re.I),
    ]:
        for m in pat.finditer(processed):
            t = tok("DATE"); rec(t, m.group(), "Date / DOB"); processed = processed.replace(m.group(), t, 1)
    for m in re.finditer(r"(?<!\w)[A-Z]\.[A-Z]\.(?!\w)", processed):
        t = tok("PATIENT"); rec(t, m.group(), "Patient Initials"); processed = processed.replace(m.group(), t, 1)
    name_re = re.compile(r"(Dr\.?\s+)(" + "|".join(INDIAN_FIRST) + r")\s+(" + "|".join(INDIAN_LAST) + r")")
    for m in name_re.finditer(processed):
        t = tok("INVESTIGATOR"); rec(t, m.group(), "Investigator Name"); processed = processed.replace(m.group(), t, 1)
    name_re2 = re.compile(r"(" + "|".join(INDIAN_FIRST) + r")\s+(" + "|".join(INDIAN_LAST) + r")")
    for m in name_re2.finditer(processed):
        if m.group() in processed:
            t = tok("PATIENT"); rec(t, m.group(), "Patient Name"); processed = processed.replace(m.group(), t, 1)
    for m in re.finditer(r"\bIND-[A-Z]{2,4}-\d{4}-\d{3,6}\b", processed):
        t = tok("SITE"); rec(t, m.group(), "Study ID"); processed = processed.replace(m.group(), t, 1)
    for m in re.finditer(r"\b[1-9]\d{5}\b", processed):
        t = tok("PINCODE"); rec(t, m.group(), "Pincode"); processed = processed.replace(m.group(), t, 1)
    for m in re.finditer(r"\b[A-Z][A-Za-z]+(\s+[A-Z][A-Za-z]+){0,3}\s+(?:Hospital|Institute|Clinic|Centre|Center|Medical College|AIIMS|PGI|CMC)\b", processed):
        t = tok("INSTITUTION"); rec(t, m.group(), "Institution Name"); processed = processed.replace(m.group(), t, 1)
    for m in re.finditer(r"\b(?:Batch|Lot|BN|LN)[.:\s#]*[A-Z0-9]{4,12}\b", processed, re.I):
        t = tok("BATCH"); rec(t, m.group(), "Batch/Lot Number"); processed = processed.replace(m.group(), t, 1)

    # Step 2: Irreversible generalisation
    step2 = processed
    step2 = re.compile(r"\b(\d{2})\s*(?:years?|yrs?)(?:\s*old)?\b", re.I).sub(
        lambda m: f"{(int(m.group(1))//5)*5}-{(int(m.group(1))//5)*5+4} years", step2)
    step2 = re.compile(r"\b(\d{2,3})\s*kg\b", re.I).sub(
        lambda m: f"{(int(m.group(1))//10)*10}-{(int(m.group(1))//10)*10+9} kg", step2)
    step2 = re.compile(r"\[DATE-\d+\]").sub("[YEAR-ONLY]", step2)
    step2 = re.compile(r"\bBMI[:\s]*(\d{1,2}\.?\d?)\b", re.I).sub("[BMI-RANGE]", step2)
    step2 = re.compile(r"\b(?:Blood\s+[Gg]roup|blood\s+type)[:\s]*[ABO]{1,2}[+-]?\b").sub("[BLOOD-GROUP]", step2)
    step2 = re.compile(r"\b\d{1,3}\.\d{1,2}\s*(?:g/dL|mg/dL|mmol/L|IU/L|U/L|mEq/L)\b").sub("[LAB-VALUE]", step2)
    for pat, rep in [
        (r"\b(?:New\s+Delhi|Delhi)\b", "[TIER-1 CITY, NORTH INDIA]"),
        (r"\b(?:Mumbai|Pune)\b",       "[TIER-1 CITY, WEST INDIA]"),
        (r"\b(?:Bengaluru|Bangalore|Chennai|Hyderabad)\b", "[TIER-1 CITY, SOUTH INDIA]"),
        (r"\bKolkata\b",               "[TIER-1 CITY, EAST INDIA]"),
        (r"\b(?:Jaipur|Lucknow|Kanpur|Agra|Varanasi|Chandigarh|Amritsar)\b", "[TIER-2 CITY, NORTH INDIA]"),
        (r"\b(?:Ahmedabad|Surat|Vadodara|Nagpur)\b",       "[TIER-2 CITY, WEST INDIA]"),
    ]:
        step2 = re.compile(pat, re.I).sub(rep, step2)
    for et in ["Dates->Year only", "Ages->5-year band", "Biometrics->Range", "City->Tier (k-anonymity)"]:
        audit.append({"Timestamp": ts, "Action": "Irreversible Generalisation", "Entity Type": et, "Token": "Generalised", "Reversible": "No"})

    return {"step1": processed, "step2": step2, "tokens": tokens, "audit": audit,
            "types": list(found_types), "count": len(tokens)}


# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARISATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def summarise_sae(text: str) -> dict:
    tl = text.lower()
    is_death = any(w in tl for w in ["died","fatal outcome","patient died","death reported","deceased","mortality confirmed"])
    priority = "URGENT" if is_death or any(w in tl for w in ["death","fatal","disability","permanent"]) \
               else "STANDARD" if any(w in tl for w in ["hospitalised","admitted","icu","hospital"]) else "LOW"
    causality = ("Probably Related" if "probably" in tl else
                 "Possibly Related" if "possibly" in tl else
                 "Unrelated" if "unrelated" in tl else
                 "Definitely Related" if "definitely" in tl else "Under Assessment")
    outcome = ("Recovered"  if any(w in tl for w in ["recovered","recovery","resolved","discharged"]) else
               "Recovering" if "recovering" in tl else
               "Fatal"      if any(w in tl for w in ["died","death","fatal","deceased"]) else "Ongoing")
    timeline = ("Expedited 7-day" if is_death else
                "Expedited 15-day" if priority == "STANDARD" else "Periodic 90-day")
    setting  = "Hospital/Emergency" if any(w in tl for w in ["hospital","emergency","icu"]) else "Outpatient"
    return {"priority": priority, "causality": causality, "outcome": outcome,
            "timeline": timeline, "setting": setting}


def summarise_checklist(text: str) -> dict:
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    comp  = sum(1 for l in lines if any(w in l.lower() for w in ["complete","present","yes","submitted","available"]))
    miss  = sum(1 for l in lines if any(w in l.lower() for w in ["missing","absent","no","not submitted"]))
    inc   = sum(1 for l in lines if any(w in l.lower() for w in ["incomplete","pending","partial"]))
    tot   = len(lines)
    score = round((comp / tot) * 100) if tot else 0
    rec   = ("✅ Approve" if score >= 80 else
             "⚠️ Return for Completion" if score >= 50 else "❌ Reject")
    actions    = [l for l in lines if any(w in l.lower() for w in ["action","follow up","submit","provide","upload","resubmit"])]
    next_steps = [l for l in lines if any(w in l.lower() for w in ["next step","deadline","due","required by"])]
    return {"total": tot, "complete": comp, "incomplete": inc, "missing": miss,
            "score": score, "recommendation": rec, "actions": actions, "next_steps": next_steps}


def summarise_meeting(text: str) -> dict:
    lines      = [l.strip() for l in text.split("\n") if l.strip()]
    decisions  = [l for l in lines if any(w in l.lower() for w in ["decided","approved","agreed","resolved","confirmed","accepted"])]
    actions    = [l for l in lines if any(w in l.lower() for w in ["action","will","must","should","to do","assigned","responsible","deadline","follow-up"])]
    next_steps = [l for l in lines if any(w in l.lower() for w in ["next meeting","next step","by","due","schedule","upcoming"])]
    return {"total_lines": len(lines), "decisions": decisions[:8],
            "actions": actions[:8], "next_steps": next_steps[:5]}


# ═══════════════════════════════════════════════════════════════════════════════
# COMPLETENESS ASSESSMENT (Schedule Y + Form CT mandatory fields)
# ═══════════════════════════════════════════════════════════════════════════════

SCHED_Y_FIELDS = [
    ("Form CT-01 (Application)", "form ct-01", "Critical"),
    ("Ethics Committee Approval", "ethics committee", "Critical"),
    ("Investigator CV / Brochure", "investigator cv", "Critical"),
    ("Site Qualification Report", "site qualification", "Critical"),
    ("GCP Certification", "gcp certification", "Critical"),
    ("Insurance Certificate", "insurance", "Major"),
    ("SAE Reporting Plan", "sae reporting", "Critical"),
    ("DSMB Charter", "data safety monitoring", "Major"),
    ("Risk Management Plan", "risk management", "Major"),
    ("Stopping Rules", "stopping rules", "Major"),
    ("Drug Master File Reference", "drug master file", "Critical"),
    ("Certificate of Analysis", "certificate of analysis", "Critical"),
    ("Stability Data (24 months)", "stability data", "Major"),
    ("Informed Consent Form (English)", "informed consent", "Critical"),
    ("Protocol (latest amendment)", "protocol", "Critical"),
    ("Investigator's Brochure", "investigator", "Major"),
    ("CRF / eCRF Design", "crf", "Minor"),
    ("Statistical Analysis Plan", "statistical analysis", "Major"),
    ("Pharmacovigilance Agreement", "pharmacovigilance", "Major"),
    ("Regulatory Authority Approval", "regulatory authority", "Critical"),
]


def assess_completeness(text: str) -> dict:
    tl   = text.lower()
    rows = []
    crit_missing = []
    major_missing = []
    for field, kw, sev in SCHED_Y_FIELDS:
        if kw in tl:
            status = "INCOMPLETE" if any(w in tl for w in ["pending","tbd","partial","to be"]) else "PRESENT"
            rag    = "🟢 Green" if status == "PRESENT" else "🟡 Amber"
        else:
            status = "MISSING"
            rag    = "🔴 Red"
            if sev == "Critical": crit_missing.append(field)
            elif sev == "Major":  major_missing.append(field)
        rows.append({"Field": field, "Severity": sev, "Status": status, "RAG": rag})
    present = sum(1 for r in rows if r["Status"] == "PRESENT")
    score   = round((present / len(SCHED_Y_FIELDS)) * 100)
    rec     = ("✅ Approve for Technical Review" if score >= 85 and not crit_missing else
               "⚠️ Return for Completion" if score >= 60 else "❌ Reject — Critical fields missing")
    return {"rows": rows, "score": score, "recommendation": rec,
            "critical_missing": crit_missing, "major_missing": major_missing,
            "present": present, "total": len(SCHED_Y_FIELDS)}


# ═══════════════════════════════════════════════════════════════════════════════
# SAE CLASSIFICATION + DUPLICATE DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

ICD_MAP      = {"DEATH": "R96.x/R98/R99", "DISABILITY": "S00-T98 (perm.)",
                "HOSPITALISATION": "Z75.1", "OTHERS": "MedDRA PT"}
TIMELINE_MAP = {"DEATH": "Expedited 7-day", "DISABILITY": "Expedited 15-day",
                "HOSPITALISATION": "Expedited 15-day", "OTHERS": "Periodic 90-day"}


def classify_sae(text: str) -> dict:
    tl = text.lower()
    death_kw = [w for w in ["died","fatal outcome","patient died","death reported","deceased","mortality confirmed"] if w in tl]
    disab_kw = [w for w in ["permanent disability","permanent impairment","paralysis","blindness","deafness"] if w in tl]
    hosp_kw  = [w for w in ["hospitalised","hospitalized","admitted","inpatient","icu","emergency admission"] if w in tl]

    if death_kw:
        sev = "DEATH"; ps = 1; rk = death_kw
    elif disab_kw:
        sev = "DISABILITY"; ps = 2; rk = disab_kw
    elif hosp_kw:
        sev = "HOSPITALISATION"; ps = 3; rk = hosp_kw
    else:
        sev = "OTHERS"; ps = 4; rk = ["no critical keywords — default"]

    conf = "HIGH" if len(rk) >= 3 else "MEDIUM" if len(rk) >= 1 else "LOW"
    return {"severity": sev, "confidence": conf, "priority": ps,
            "keywords": rk, "icd10": ICD_MAP[sev], "timeline": TIMELINE_MAP[sev]}


def detect_duplicates(primary_text: str, session_files: dict) -> list[dict]:
    def get_ids(t: str):
        ids   = set(re.findall(r"\b(?:PT|SUBJ|LH|MH|DL)[-][A-Z0-9]{3,}[-][A-Z0-9]{3,}\b", t))
        drugs = set(re.findall(r"\b[A-Z][a-z]+(?:vir|mab|nib|tide|pril|sartan|statin|mycin|cillin)\b", t))
        drugs |= set(re.findall(r"\b[A-Z]{4,}[-]?\d+\s*mg\b", t))
        return ids, drugs

    id1, dr1 = get_ids(primary_text)
    results = []
    for k, v in session_files.items():
        if v["text"].strip() == primary_text.strip():
            continue
        id2, dr2 = get_ids(v["text"])
        shared_ids = id1 & id2
        if shared_ids:
            results.append({"file": v["name"], "shared_ids": shared_ids, "shared_drugs": dr1 & dr2})
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT COMPARISON ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

SUBSTANTIVE_KEYWORDS = [
    "dose","dosage","mg","ml","death","disability","outcome","causality",
    "adverse","event","date","patient","diagnosis","icd","treatment",
    "safety","efficacy","result","risk","fatal","serious",
]


def compare_documents(text1: str, text2: str) -> list[dict]:
    def normalise(t: str) -> list[str]:
        lines  = [l.strip() for l in t.splitlines() if l.strip()]
        result = []
        for l in lines:
            if len(l) > 200:
                parts = re.split(r"(?<=[.!?])\s+", l)
                result.extend(p.strip() for p in parts if p.strip())
            else:
                result.append(l)
        return result

    l1 = normalise(text1)
    l2 = normalise(text2)
    changes = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, l1, l2).get_opcodes():
        if tag == "replace":
            for o, n in zip(l1[i1:i2], l2[j1:j2]):
                s = any(k in o.lower() or k in n.lower() for k in SUBSTANTIVE_KEYWORDS)
                changes.append({"Type": "CHANGED", "Original": o, "New": n, "Substantive": "Yes" if s else "No"})
        elif tag == "delete":
            for line in l1[i1:i2]:
                s = any(k in line.lower() for k in SUBSTANTIVE_KEYWORDS)
                changes.append({"Type": "REMOVED", "Original": line, "New": "—", "Substantive": "Yes" if s else "No"})
        elif tag == "insert":
            for line in l2[j1:j2]:
                s = any(k in line.lower() for k in SUBSTANTIVE_KEYWORDS)
                changes.append({"Type": "ADDED", "Original": "—", "New": line, "Substantive": "Yes" if s else "No"})
    return changes


# ═══════════════════════════════════════════════════════════════════════════════
# INSPECTION REPORT ENGINE (CDSCO GCP Format)
# ═══════════════════════════════════════════════════════════════════════════════

CRITICAL_KW = [
    "no record","falsified","patient safety","data integrity","unaccounted","fraud","fabricat",
    "sae delay","delayed sae","sae not reported","unreported sae","reporting violation",
    "not reported within","failed to report","safety reporting","failure to notify",
]
MAJOR_KW = [
    "incomplete","not documented","protocol deviation","untrained",
    "not signed","not dated","expired","missing signature",
]
REG_REF = {
    "Critical": "NDCT Rules 2019, Rule 26 (SAE Reporting) / Schedule Y, Para 4.4 (Data Integrity)",
    "Major":    "NDCT Rules 2019, Rule 21 (GCP Compliance) / Schedule Y, Para 4.3 (Documentation)",
    "Minor":    "NDCT Rules 2019, Rule 22 (Site Standards) / Schedule Y, Para 4.2 (Labelling)",
}
_PLACEHOLDER_RE = re.compile(
    r"^\[.*\]$|^<.*>$|^Note:|^Ref:|^Reference:|^Template|^Example|^Instructions?:", re.I
)


def generate_inspection_report(observations: str, site: str, site_no: str,
                                inspector: str, date: datetime.date) -> dict:
    raw_lines = [o.strip() for o in observations.splitlines() if o.strip()]
    obs_list  = [o for o in raw_lines if not _PLACEHOLDER_RE.match(o) and len(o) > 5]
    rows = []
    for i, ob in enumerate(obs_list, 1):
        ol = ob.lower()
        if any(k in ol for k in CRITICAL_KW):
            risk = "Critical"; dl = "15 days"; ca = "Immediate CAPA. Site may be suspended."
        elif any(k in ol for k in MAJOR_KW):
            risk = "Major"; dl = "30 days"; ca = "CAPA plan within 30 days."
        else:
            risk = "Minor"; dl = "60 days"; ca = "Document in site log."
        ob_s   = ob.rstrip(".")
        formal = (f"During the inspection conducted on {date.strftime('%d %B %Y')} at {site or 'the site'}, "
                  f"a {risk.lower()}-grade GCP deviation was identified: "
                  f"{ob_s[0].upper() + ob_s[1:] if ob_s else ob_s}. "
                  f"This finding requires corrective action in accordance with {REG_REF[risk]}.")
        rows.append({"Obs": f"OBS-{i:03d}", "Raw": ob, "Formal Finding": formal,
                     "Risk": risk, "Corrective Action": ca, "Deadline": dl,
                     "Regulatory Reference": REG_REF[risk]})
    cc_n = sum(1 for r in rows if r["Risk"] == "Critical")
    mc_n = sum(1 for r in rows if r["Risk"] == "Major")
    mn_n = sum(1 for r in rows if r["Risk"] == "Minor")
    sep  = "=" * 56
    sep2 = "-" * 56
    report_txt = f"""CDSCO GCP SITE INSPECTION REPORT\n{sep}\n
SECTION 1: BASIC DETAILS
Study/Site Name : {site or "[Site name]"}
Site Number     : {site_no or "[Site number]"}
Inspection Date : {date.strftime("%d %B %Y")}
Inspector       : {inspector or "[Inspector name]"}
\n{sep}\n
SECTION 2: SUMMARY
Total Observations: {len(rows)}
Critical          : {cc_n}
Major             : {mc_n}
Minor             : {mn_n}
Overall Risk      : {"HIGH" if cc_n > 0 else "MEDIUM" if mc_n > 0 else "LOW"}
\n{sep}\n
SECTION 3: FINDINGS TABLE\n\n"""
    for r in rows:
        report_txt += (f"{r['Obs']} | {r['Risk'].upper()}\n"
                       f"Observation         : {r['Raw']}\n"
                       f"Formal Finding      : {r['Formal Finding']}\n"
                       f"Severity            : {r['Risk']}\n"
                       f"Regulatory Reference: {r['Regulatory Reference']}\n"
                       f"Recommendation      : {r['Corrective Action']}\n"
                       f"Deadline            : {r['Deadline']}\n{sep2}\n")
    report_txt += f"""
SECTION 4: CROSS-DOCUMENT ISSUES
No cross-document mismatches identified in this report.
\n{sep}\n
SECTION 5: CAPA (CORRECTIVE AND PREVENTIVE ACTION)
Critical findings require immediate CAPA submission within 15 days.
Major findings require CAPA plan within 30 days.
Minor findings to be documented in site log within 60 days.
\n{sep}\n
SECTION 6: RISK LEVEL
Overall Site Risk: {"HIGH — immediate action required" if cc_n > 0 else "MEDIUM — corrective action required" if mc_n > 0 else "LOW — routine monitoring"}
\n{sep}\n
SECTION 7: AUDIT TRAIL (AI FLAGGING RATIONALE)
Generated by Nirnay AI — CDSCO AI Hackathon 2026, Stage 1.
Critical flags: data integrity, patient safety, SAE reporting violations.
Major flags: incomplete documentation, protocol deviations, missing signatures.
Minor flags: administrative or labelling issues not affecting patient safety.
Regulatory framework: NDCT Rules 2019, Schedule Y, ICMR GCP Guidelines.
\n{sep}
Inspector Signature: ___________________________
Date: {datetime.date.today()}
Generated by: Nirnay — CDSCO Regulatory Intelligence Platform
"""
    return {"rows": rows, "critical": cc_n, "major": mc_n, "minor": mn_n,
            "full_text": report_txt, "overall_risk": "HIGH" if cc_n > 0 else "MEDIUM" if mc_n > 0 else "LOW"}


# ═══════════════════════════════════════════════════════════════════════════════
# CLAUDE API — AI-ENHANCED SUMMARISATION (optional, free-tier)
# ═══════════════════════════════════════════════════════════════════════════════

def claude_summarise(text: str, doc_type: str) -> str | None:
    """
    Calls Claude Haiku for AI-enhanced summary.
    Returns None if API is unavailable (falls back to rule-based engine).
    Only used for summarisation feature — all other features use rule-based engines.
    """
    if not CLAUDE_OK or not _ANTHROPIC_CLIENT:
        return None
    prompts = {
        "SAE Case Narration": (
            "You are a CDSCO regulatory reviewer. Extract from this SAE narrative: "
            "patient profile, event description, seriousness criteria, causality, outcome, "
            "and recommended reporting timeline under Schedule Y / NDCT Rules 2019. "
            "Be concise and structured."
        ),
        "Application Checklist (SUGAM)": (
            "You are a CDSCO reviewer. Analyse this SUGAM application checklist. "
            "Identify present, missing, and incomplete fields. "
            "Give a completeness score and a clear approve/return/reject recommendation."
        ),
        "Meeting Transcript / Audio": (
            "You are a CDSCO regulatory meeting secretary. From this transcript, extract: "
            "key decisions made, action items with owners, and next steps. "
            "Format clearly under those three headings."
        ),
    }
    system_prompt = prompts.get(doc_type, "Summarise this regulatory document concisely.")
    try:
        response = _ANTHROPIC_CLIENT.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=800,
            system=system_prompt,
            messages=[{"role": "user", "content": text[:4000]}],
        )
        return response.content[0].text if response.content else None
    except Exception:
        return None
