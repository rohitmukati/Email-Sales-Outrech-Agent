# draft_routes.py
import os
import json
import traceback
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

# Calendar & Email imports
from Calender_Services.services import (
    get_readable_available_slots,
    get_prospect_upcoming_event_simple
)
from Email_Services.get_mails import get_last_mail_from_sender, get_last_sent_mail_to

# Draft generator
from generate_draft import generate_draft

# Load env
load_dotenv()

cfg_path = os.path.join(os.path.dirname(__file__), "Calender_Services", "calender_config.yaml")
print("Using config path:", cfg_path)


# JSON file to persist draft
DRAFT_JSON_FILE = os.path.join(os.path.dirname(__file__), "data", "draft.json")

router = APIRouter()


# -------- Prospect Model --------
class Prospect(BaseModel):
    email: str
    name: str = ""
    role: str = ""
    industry: str = ""


def save_draft_to_json(data: dict):
    """
    Save the latest draft to JSON, replacing any previous entry.
    """
    folder = os.path.dirname(DRAFT_JSON_FILE)
    os.makedirs(folder, exist_ok=True)
    try:
        with open(DRAFT_JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("Draft saved to", DRAFT_JSON_FILE)
    except Exception as e:
        print("⚠️ Failed to save draft:", e)


# -------- Draft Route --------
@router.post("/generate-draft")
def generate_draft_route(prospect: Prospect):
    try:
        # -------- Fetch mails --------
        try:
            current_mail = get_last_mail_from_sender(prospect.email) or ""
        except Exception as e:
            print("Warning: get_last_mail_from_sender failed:", e)
            current_mail = ""

        try:
            past_interaction = get_last_sent_mail_to(prospect.email) or ""
        except Exception as e:
            print("Warning: get_last_sent_mail_to failed:", e)
            past_interaction = ""

        # -------- Calendar --------
        try:
            upcoming_events = get_prospect_upcoming_event_simple(prospect.email, cfg_path=cfg_path) or []
            print("Upcoming events for", prospect.email, ":", upcoming_events)
        except Exception as e:
            print("Warning: get_prospect_upcoming_event_simple failed:", e)
            upcoming_events = []

        # Determine first confirmed slot
        confirmed_slot = ""
        for ev in upcoming_events:
            if ev.get("confirmed"):
                confirmed_slot = ev.get("start_readable", "")
                break

        try:
            available_slots = get_readable_available_slots(cfg_path=cfg_path, days=7, top_n=5, offset_days=1) or []
        except Exception as e:
            print("Warning: get_readable_available_slots failed:", e)
            available_slots = []

        # -------- Company config --------
        company_config = {
            "sender_company": os.getenv("SENDER_COMPANY", "Talita Alves Clinic"),
            "signature": os.getenv("EMAIL_SIGNATURE", "Best regards,\nTalita Alves Clinic Team"),
            "cta": os.getenv("EMAIL_CTA", "📅 Book Your Evaluation Today"),
            "services": ["Aesthetic Treatments", "Skin Care", "Wellness"],
            "usp": ["Personalized care", "Expert doctors", "Advanced technology"]
        }

        # -------- Generate draft --------
        draft = generate_draft(
            prospect=prospect.dict(),
            past_interaction=past_interaction,
            current_mail=current_mail,
            available_slots=available_slots,
            upcoming_events=upcoming_events,  # ✅ pass list of events
            company_config=company_config
        )

        # -------- Persist draft in JSON (replace old entry) --------
        save_draft_to_json({
            "prospect": prospect.dict(),
            "draft": draft,
            "upcoming_events": upcoming_events,
            "available_slots": available_slots,
            "current_mail": current_mail,
            "past_interaction": past_interaction
        })

        # -------- Return response --------
        return {
            "status": "success",
            "draft": draft,
            "upcoming_events": upcoming_events,
            "available_slots": available_slots,
            "current_mail": current_mail,
            "past_interaction": past_interaction
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
