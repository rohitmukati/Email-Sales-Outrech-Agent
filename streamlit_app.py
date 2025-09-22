import streamlit as st
import requests
import json
from typing import Optional

st.set_page_config(page_title="Draft Manager — Direct Send", layout="wide")

# ------ Sidebar / config ------
st.sidebar.title("Config")
BACKEND_URL = st.sidebar.text_input("Backend base URL", value="http://localhost:8000")
st.sidebar.markdown("""
**Notes**
- Start backend: `uvicorn main:app --reload --port 8000`
- Make sure backend /api/generate-draft and /api/act are reachable.
- Fix backend apply_feedback to return a dict (no trailing comma).
""")

# ------ helpers ------
def post_raw(path: str, payload: dict, timeout=30):
    url = BACKEND_URL.rstrip("/") + path
    try:
        r = requests.post(url, json=payload, timeout=timeout)
    except requests.exceptions.RequestException as e:
        return {"__network_error__": str(e)}
    out = {
        "status_code": r.status_code,
        "reason": r.reason,
        "text": r.text,
        "headers": dict(r.headers)
    }
    try:
        out["json"] = r.json()
    except Exception:
        out["json"] = None
    if not (200 <= r.status_code < 300):
        out["__error__"] = f"HTTP {r.status_code} {r.reason}"
    return out

def get_raw(path: str, timeout=20):
    url = BACKEND_URL.rstrip("/") + path
    try:
        r = requests.get(url, timeout=timeout)
    except requests.exceptions.RequestException as e:
        return {"__network_error__": str(e)}
    try:
        return {"status_code": r.status_code, "json": r.json(), "text": r.text}
    except Exception:
        return {"status_code": r.status_code, "json": None, "text": r.text}

# ------ UI layout ------
st.title("✉️ Draft Manager — Direct Send (single JSON box)")

left, right = st.columns([1, 2])

with left:
    st.subheader("Generate Draft")
    with st.form("gen"):
        email = st.text_input("Email", value="")
        name = st.text_input("Name", value="")
        role = st.text_input("Role", value="")
        industry = st.text_input("Industry", value="")
        gen_btn = st.form_submit_button("Generate")

    st.markdown("---")
    st.subheader("Actions")
    feedback = st.text_area("Feedback for update (U)", height=120, placeholder="e.g. shorten subject, add pricing note")
    update_btn = st.button("Update draft (decision U)")
    send_btn = st.button("Send immediately (decision A)  — NO PROMPT")

    st.markdown("---")
    if st.button("Fetch history"):
        hist = get_raw("/api/history")
        if hist.get("__network_error__"):
            st.error(f"Network error: {hist['__network_error__']}")
        else:
            if hist.get("json") is not None:
                st.success("History fetched")
                st.json(hist["json"])
            else:
                st.code(hist.get("text", "No response"))

with right:
    st.subheader("Draft JSON (single box)")
    if "draft_data" not in st.session_state:
        # initialize with backend draft.json if exists
        try:
            r = get_raw("/api/history")  # just to ensure backend reachable
        except Exception:
            r = {}
        st.session_state.draft_data = {}  # empty until generate

    # Display the draft JSON in a single read-only box (but also allow manual editing if user wants)
    # We'll show a pretty JSON via st.json and also provide a hidden editable textarea for manual edits if needed.
    st.markdown("**Current draft (readable)**")
    if st.session_state.get("draft_data"):
        st.json(st.session_state["draft_data"])
    else:
        st.info("No draft loaded. Generate a draft from left panel.")

    # Hidden editable JSON (toggle)
    edit_toggle = st.checkbox("Edit JSON manually", key="edit_toggle")
    if edit_toggle:
        raw = json.dumps(st.session_state.get("draft_data", {}), indent=2, ensure_ascii=False)
        edited = st.text_area("Edit raw draft JSON", value=raw, height=300, key="raw_edit")
        if st.button("Apply manual JSON edits"):
            try:
                parsed = json.loads(edited)
                st.session_state["draft_data"] = parsed
                st.success("Manual edits applied to UI-only draft preview.")
            except Exception as e:
                st.error(f"Invalid JSON: {e}")

# ------ Generate logic ------
if gen_btn:
    if not email.strip():
        st.error("Email required to generate draft.")
    else:
        payload = {"email": email.strip(), "name": name.strip(), "role": role.strip(), "industry": industry.strip()}
        with st.spinner("Calling /api/generate-draft ..."):
            out = post_raw("/api/generate-draft", payload)
        if out.get("__network_error__"):
            st.error("Network error: " + out["__network_error__"])
        elif out.get("__error__"):
            st.error(f"Generate failed: {out.get('__error__')} — see response text below")
            st.code(out.get("text", ""))
        else:
            # prefer JSON payload
            content = out.get("json") or out.get("text")
            if isinstance(content, dict):
                st.session_state["draft_data"] = content
                st.success("Draft generated and loaded into box.")
                st.json(st.session_state["draft_data"])
            else:
                # try parse text as JSON
                try:
                    parsed = json.loads(out.get("text", "{}"))
                    st.session_state["draft_data"] = parsed
                    st.success("Loaded JSON from text response.")
                    st.json(parsed)
                except Exception:
                    st.error("Backend returned non-JSON response.")
                    st.code(out.get("text", ""))

# ------ Update logic (U) ------
if update_btn:
    if not st.session_state.get("draft_data"):
        st.error("No draft in UI. Generate first.")
    elif not feedback.strip():
        st.error("Feedback text required for update.")
    else:
        payload = {"decision": "U", "feedback": feedback}
        with st.spinner("Calling /api/act (update)..."):
            out = post_raw("/api/act", payload)
        # handle response
        if out.get("__network_error__"):
            st.error("Network error: " + out["__network_error__"])
        elif out.get("__error__"):
            st.error(f"Update failed: {out.get('__error__')}")
            st.code(out.get("text", ""))
        else:
            # Many backends return dict; sometimes update returns {"message":..., "draft": {...}}
            js = out.get("json")
            if isinstance(js, dict):
                # if server returned updated draft inside "draft", prefer that
                new_draft = js.get("draft") or js
                st.session_state["draft_data"] = new_draft
                st.success("Draft updated and UI box refreshed.")
                st.json(st.session_state["draft_data"])
            else:
                # try parse text as JSON fallback
                try:
                    parsed = json.loads(out.get("text", "{}"))
                    st.session_state["draft_data"] = parsed
                    st.success("Draft updated (parsed text).")
                    st.json(parsed)
                except Exception:
                    st.error("Update response not JSON. See raw text:")
                    st.code(out.get("text", ""))

# ------ Send logic (A) immediate, no confirmation ------
if send_btn:
    if not st.session_state.get("draft_data"):
        st.error("No draft loaded. Generate first.")
    else:
        payload = {"decision": "A", "feedback": None}
        with st.spinner("Sending (approve) — calling /api/act ..."):
            out = post_raw("/api/act", payload, timeout=60)
        if out.get("__network_error__"):
            st.error("Network error: " + out["__network_error__"])
        elif out.get("__error__"):
            # show HTTP error + full body
            st.error(f"Send failed: {out.get('__error__')}")
            st.code(out.get("text", ""))
        else:
            js = out.get("json")
            if js:
                st.success("Send completed. Server response:")
                st.json(js)
            else:
                st.success("Send completed. Server returned non-JSON:")
                st.code(out.get("text", ""))

# ------ footer ------
st.markdown("---")
st.caption("Direct-send mode. Be sure your SMTP/calendar config is correct on backend; this UI sends approval immediately.")
