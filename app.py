import json
import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="AI Testing Methodologies Utility", layout="wide")

# --------- Heuristic scaffolding (replace with LLM later) ----------
def parse_requirement(text: str) -> dict:
    text_l = text.lower()
    actors = ["User"] + (["Admin"] if "admin" in text_l else [])
    missing = []
    if "password" in text_l and "complex" not in text_l:
        missing.append("password complexity policy (inferred, confidence=0.84)")
    if "lock" in text_l and "attempt" not in text_l:
        missing.append("max failed attempts before lockout (inferred, confidence=0.81)")
    if "otp" in text_l and "mandatory" not in text_l:
        missing.append("otp mandatory policy (inferred, confidence=0.7)")
    clarifying = [
        "Should OTP be mandatory for all admins or per-tenant configurable?",
        "What is the lockout threshold and lockout duration?",
        "What password complexity rules apply (length, charset, reuse, history)?"
    ]
    acceptance = [
        "User can login with valid email and password",
        "Admin can enable OTP for login (inferred, confidence=0.78)",
        "Successful login redirects to dashboard"
    ]
    return {
        "title": "Secure Login",
        "actors": actors,
        "functional_tags": ["authentication","otp" if "otp" in text_l else "login","lockout" if "lock" in text_l else "session"],
        "nonfunctional_tags": ["security","usability"],
        "acceptance_criteria": acceptance,
        "impacted_modules": ["auth-service","user-profile (inferred, confidence=0.62)"],
        "missing_info": missing or ["session timeout seconds (inferred, confidence=0.73)"],
        "clarifying_questions": clarifying,
        "risk": "High",
        "risk_reason": "Auth and lockout flows are security-critical; ambiguity can cause bypass or lockout issues",
        "assumptions": ["Email is unique username (inferred, confidence=0.65)"]
    }

def generate_tests(requirement_json: dict) -> dict:
    tests = [
        {"id":"TC001","title":"Valid login without OTP","preconditions":["OTP disabled for tenant"],
         "steps":["1. Open login page","2. Enter valid email and password","3. Click Login"],
         "test_data":"TD01","expected":"User lands on dashboard","risk":"High",
         "automation_candidate":True,"automation_reason":"Stable UI flow; high reuse"},
        {"id":"TC002","title":"Valid login with OTP","preconditions":["OTP enabled for tenant","User enrolled in OTP"],
         "steps":["1. Open login page","2. Enter valid credentials","3. Provide valid OTP within time window"],
         "test_data":"TD02","expected":"Login succeeds and redirect to dashboard","risk":"High",
         "automation_candidate":True,"automation_reason":"API-based OTP stub possible"},
        {"id":"TC003","title":"Invalid password","preconditions":[],
         "steps":["1. Open login page","2. Enter valid email and invalid password","3. Click Login"],
         "test_data":"TD03","expected":"Error displayed; no login","risk":"Medium",
         "automation_candidate":True,"automation_reason":"Simple negative path"},
        {"id":"TC004","title":"OTP timeout","preconditions":["OTP enabled"],
         "steps":["1. Login with valid credentials","2. Do not enter OTP","3. Wait for timeout window to elapse"],
         "test_data":"TD04","expected":"OTP expires; user prompted to resend","risk":"High",
         "automation_candidate":True,"automation_reason":"Can simulate clock or mock OTP"},
        {"id":"TC005","title":"Account lockout after N failures","preconditions":["Lockout policy configured (inferred, confidence=0.8)"],
         "steps":["1. Attempt login with invalid password N times","2. Attempt login with valid password"],
         "test_data":"TD05","expected":"Account is locked; login blocked","risk":"High",
         "automation_candidate":False,"automation_reason":"Lockout reset/stateful; may be slow"},
        {"id":"TC006","title":"Boundary: password length min-1","preconditions":[],
         "steps":["1. Enter password at min length minus one","2. Submit"],
         "test_data":"TD06","expected":"Validation error","risk":"Low",
         "automation_candidate":True,"automation_reason":"Fast validation check"},
        {"id":"TC007","title":"Exploratory: rapid successive logins","preconditions":[],
         "steps":["1. Attempt multiple rapid logins with valid and invalid data","2. Observe responses and rate limits"],
         "test_data":"TD07","expected":"System handles without instability","risk":"Medium",
         "automation_candidate":False,"automation_reason":"Exploratory; less deterministic"},
        {"id":"TC008","title":"State transition: locked -> unlocked after duration","preconditions":["Account locked"],
         "steps":["1. Wait lockout duration","2. Attempt valid login"],
         "test_data":"TD08","expected":"Account unlocks; login succeeds","risk":"Medium",
         "automation_candidate":True,"automation_reason":"Can fast-forward time with mocks"},
    ]
    counts = {"High":0,"Medium":0,"Low":0}
    for t in tests:
        counts[t["risk"]] += 1
    return {"test_cases": tests, "summary": {"high":counts["High"], "medium":counts["Medium"], "low":counts["Low"]}, "assumptions": requirement_json.get("assumptions",[])}

def df_from_tests(tests_json: dict) -> pd.DataFrame:
    rows = []
    for t in tests_json["test_cases"]:
        rows.append({
            "id": t["id"],
            "title": t["title"],
            "preconditions": "; ".join(t["preconditions"]),
            "steps": " | ".join(t["steps"]),
            "test_data": t["test_data"],
            "expected": t["expected"],
            "risk": t["risk"],
            "automation_candidate": t["automation_candidate"],
            "automation_reason": t["automation_reason"]
        })
    return pd.DataFrame(rows)

def download_bytes(obj, filename="data.json"):
    b = io.BytesIO()
    if filename.endswith(".json"):
        b.write(json.dumps(obj, indent=2).encode("utf-8"))
    else:
        b.write(obj.encode("utf-8"))
    b.seek(0)
    return b

# ------------------------- UI -------------------------
st.title("AI Testing Methodologies Utility (Demo)")
st.caption("Requirement Analysis → Test Design | JSON + Tables | CSV export | Clarifications")

mode = st.selectbox("Mode", ["Requirement Analysis","Test Design"])
default_text = "Users must login using email and password; admins can require OTP. Lock account after too many failures. Redirect to dashboard on success."
input_text = st.text_area("Input (paste requirement text here)", value=default_text, height=150)
run = st.button("Run")

clarify_answers = {}

if run:
    if mode == "Requirement Analysis":
        ra = parse_requirement(input_text)
        left, right = st.columns([1,1])
        with left:
            st.subheader("JSON")
            st.code(json.dumps(ra, indent=2), language="json")
            st.download_button("Download JSON", data=download_bytes(ra, "requirement_analysis.json"), file_name="requirement_analysis.json")
        with right:
            st.subheader("Tables")
            st.markdown("Actors")
            st.table(pd.DataFrame({"actors": ra["actors"]}))
            st.markdown("Acceptance criteria")
            st.table(pd.DataFrame({"acceptance_criteria": ra["acceptance_criteria"]}))
            st.markdown("Missing info (clarify)")
            st.table(pd.DataFrame({"missing_info": ra["missing_info"]}))
            st.markdown("Clarifying questions (prioritized)")
            st.table(pd.DataFrame({"clarifying_questions": ra["clarifying_questions"]}))
            csv_rows = [{"type":"actor","value":a} for a in ra["actors"]] + [{"type":"missing_info","value":m} for m in ra["missing_info"]]
            csv_df = pd.DataFrame(csv_rows)
            st.download_button("Export CSV (actors/missing)", data=csv_df.to_csv(index=False), file_name="requirement_summary.csv", mime="text/csv")
        st.divider()
        st.subheader("Answer clarifying questions inline")
        for q in ra["clarifying_questions"]:
            clarify_answers[q] = st.text_input(f"Answer: {q}", "")
        if st.button("Apply answers and regenerate tests"):
            ra["assumptions"] = ra.get("assumptions", []) + [f"Answered clarifications: {sum(1 for a in clarify_answers.values() if a)}"]
            td = generate_tests(ra)
            st.subheader("Generated Tests (after clarification)")
            st.code(json.dumps(td, indent=2), language="json")
            tdf = df_from_tests(td)
            st.dataframe(tdf, use_container_width=True)
            st.download_button("Export tests CSV", data=tdf.to_csv(index=False), file_name="tests.csv", mime="text/csv")

    elif mode == "Test Design":
        ra = parse_requirement(input_text)
        td = generate_tests(ra)
        left, right = st.columns([1,1])
        with left:
            st.subheader("Requirement (parsed)")
            st.code(json.dumps(ra, indent=2), language="json")
        with right:
            st.subheader("Test Design JSON")
            st.code(json.dumps(td, indent=2), language="json")
        st.subheader("Test Cases Table")
        tdf = df_from_tests(td)
        st.dataframe(tdf, use_container_width=True)
        st.download_button("Export tests CSV", data=tdf.to_csv(index=False), file_name="tests.csv", mime="text/csv")
        st.download_button("Download JSON", data=download_bytes(td, "test_design.json"), file_name="test_design.json")
