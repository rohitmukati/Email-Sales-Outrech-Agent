# src/routes.py
import os
import smtplib
import traceback
from email.message import EmailMessage
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pytz  # ✅ Added for timezone handling

from src.utils.helpers import load_json, save_json
from src.update_approve import apply_feedback
from src.Calender_Services.services import load_calendar_config, is_slot_free, create_event


router = APIRouter()

# env
load_dotenv()

DRAFT_FILE = os.path.join(os.path.dirname(__file__), "data", "draft.json")
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "data", "history.json")
print("Draft file path:", DRAFT_FILE)

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER") or os.getenv("FROM_EMAIL")
SMTP_PASS = (os.getenv("SMTP_PASS") or "").replace(" ", "")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
FROM_EMAIL = os.getenv("FROM_EMAIL") or SMTP_USER


# ------------------- Email Sender -------------------
def send_email(to_email: str, subject: str, body: str):
    if not (SMTP_HOST and SMTP_PORT and SMTP_USER and SMTP_PASS and FROM_EMAIL):
        raise RuntimeError("SMTP configuration missing.")
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        server.ehlo()
        if SMTP_USE_TLS:
            server.starttls()
            server.ehlo()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


# ------------------- Models -------------------
class ActionRequest(BaseModel):
    decision: str  # "U" or "A"
    feedback: str | None = None


# ------------------- Helper: Save to history -------------------
def save_to_history(full_data: dict):
    history = load_json(HISTORY_FILE, [])
    if isinstance(history, dict):
        history = [history]

    full_data["sent_at"] = datetime.now().isoformat()
    history.append(full_data)
    save_json(HISTORY_FILE, history)


# GET /api/history
@router.get("/history")
def get_history():
    try:
        history = load_json(HISTORY_FILE, [])
        if isinstance(history, dict):
            history = [history]
        return {"history": history}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to load history: {e}")


# ------------------- Routes -------------------
@router.post("/act")
def act_on_draft(req: ActionRequest):
    decision = (req.decision or "").upper()
    data = load_json(DRAFT_FILE, {})

    if not data or "draft" not in data:
        raise HTTPException(status_code=404, detail="No draft found.")

    draft = data["draft"]
    email = draft.get("email")

    if decision == "U":
        if not req.feedback:
            raise HTTPException(status_code=400, detail="Feedback required for update.")
        result = apply_feedback(req.feedback)
        return result

    elif decision == "A":
        event_info = None

        # Create calendar event if slot confirmed
        if draft.get("slot_status") == "confirmed" and draft.get("final_slot"):
            try:
                cal_cfg = load_calendar_config()
                slot_minutes = int(cal_cfg.get("slot_duration_minutes", 30))

                # Convert final_slot string to datetime
                start_str = draft.get("final_slot")

                # If slot includes a range, split and take only the start time
                if " - " in start_str:
                    start_str = start_str.split(" - ")[0].strip()

                try:
                    start_dt = datetime.strptime(start_str, "%a, %b %d %Y | %I:%M %p")
                    end_dt = start_dt + timedelta(minutes=slot_minutes)

                    # ✅ Convert to RFC3339 UTC format
                    start_iso = start_dt.astimezone(pytz.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                    end_iso = end_dt.astimezone(pytz.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

                except Exception:
                    raise HTTPException(status_code=400, detail="Invalid final_slot format.")

                # Check if slot is free
                free = is_slot_free(cal_cfg, start_iso, end_iso)
                if not free:
                    raise HTTPException(status_code=409, detail="Selected slot not free.")

                # Create event
                ev = create_event(
                    cal_cfg,
                    f"{draft.get('subject')} ({email})",
                    start_iso,
                    end_iso,
                    email=email,
                    mail_body=draft.get("body", ""),
                    conference=True,
                    invite_attendees=False
                )

                event_info = {
                    "id": ev.get("id"),
                    "htmlLink": ev.get("htmlLink"),
                    "start": ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date"),
                    "end": ev.get("end", {}).get("dateTime") or ev.get("end", {}).get("date")
                }

                # Append meeting link to body
                if event_info.get("htmlLink"):
                    draft["body"] += f"\n\nMeeting details: {event_info['htmlLink']}"

            except Exception as e:
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=f"Failed to create event: {e}")

        # Send email
        try:
            send_email(email, draft.get("subject", ""), draft.get("body", ""))
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Failed to send email: {e}")

        # Save full draft to history and clear draft.json
        try:
            save_to_history(data)
            save_json(DRAFT_FILE, {})
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Failed to save history or clear draft: {e}")

        return {
            "message": "📨 Email sent, draft archived to history and removed.",
            "email": email,
            "subject": draft.get("subject"),
            "body": draft.get("body"),
            "event_info": event_info or {}
        }

    else:
        raise HTTPException(status_code=400, detail="decision must be 'U' or 'A'")
