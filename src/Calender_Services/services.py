import os
import datetime as dt
from typing import List, Dict, Optional
import pytz
import logging
import yaml

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
from dotenv import load_dotenv
import os
import json

load_dotenv()  # Loads environment variables from .env

# -------------------------
# Logger setup
# -------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(ch)

# -------------------------
# Paths and scopes
# -------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
# SERVICE_ACCOUNT_FILE = os.path.join(HERE, "sakey.json")
CONFIG_FILE = os.path.join(HERE, "calender_config.yaml")
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# -------------------------
# Load config
# -------------------------
def load_calendar_config(path: Optional[str] = None) -> dict:
    p = path or CONFIG_FILE
    if not os.path.exists(p):
        raise FileNotFoundError(f"Calendar config not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    cfg.setdefault("working_days", [1, 2, 3, 4, 5])
    cfg.setdefault("working_hours", {"start": "09:00", "end": "17:00"})
    cfg.setdefault("slot_duration_minutes", 30)
    cfg.setdefault("timezone", "UTC")
    if "calendar_id" not in cfg:
        raise ValueError("calendar_id must be configured in calender_config.yaml")
    return cfg

# -------------------------
# Google Calendar service
# -------------------------
from google.oauth2 import service_account

def get_service_account_service(subject: Optional[str] = None):
    # Create service account info dict from environment variables
    service_account_info = {
        "type": os.getenv("TYPE"),
        "project_id": os.getenv("PROJECT_ID"),
        "private_key_id": os.getenv("PRIVATE_KEY_ID"),
        "private_key": os.getenv("PRIVATE_KEY").replace("\\n", "\n"),
        "client_email": os.getenv("CLIENT_EMAIL"),
        "client_id": os.getenv("CLIENT_ID"),
        "auth_uri": os.getenv("AUTH_URI"),
        "token_uri": os.getenv("TOKEN_URI"),
        "auth_provider_x509_cert_url": os.getenv("AUTH_PROVIDER_X509_CERT_URL"),
        "client_x509_cert_url": os.getenv("CLIENT_X509_CERT_URL"),
        "universe_domain": os.getenv("UNIVERSE_DOMAIN")
    }

    creds = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=SCOPES
    )
    if subject:
        creds = creds.with_subject(subject)
    service = build("calendar", "v3", credentials=creds)
    return service

# -------------------------
# Freebusy query
# -------------------------
def freebusy_query(service, calendar_id: str, time_min_iso: str, time_max_iso: str) -> List[Dict]:
    body = {"timeMin": time_min_iso, "timeMax": time_max_iso, "items": [{"id": calendar_id}]}
    try:
        resp = service.freebusy().query(body=body).execute()
        busy = resp["calendars"].get(calendar_id, {}).get("busy", [])
        return busy
    except HttpError as e:
        logger.error("Freebusy error: %s", e)
        return []

# -------------------------
# Compute free slots (formatted)
# -------------------------
def compute_free_slots_from_busy(
    busy_intervals: List[Dict],
    cfg: dict,
    days: int = 7,
    start_from: Optional[dt.datetime] = None
) -> List[Dict]:
    tz = pytz.timezone(cfg.get("timezone", "UTC"))
    slot_minutes = int(cfg.get("slot_duration_minutes", 30))
    working_days = cfg.get("working_days", [1, 2, 3, 4, 5])
    wh = cfg.get("working_hours", {"start": "09:00", "end": "17:00"})
    start_h, start_m = map(int, wh["start"].split(":"))
    end_h, end_m = map(int, wh["end"].split(":"))

    # Convert busy intervals to datetime tuples
    busy = []
    for b in busy_intervals:
        try:
            s = dt.datetime.fromisoformat(b["start"].replace("Z", "+00:00")).astimezone(tz)
            e = dt.datetime.fromisoformat(b["end"].replace("Z", "+00:00")).astimezone(tz)
            busy.append((s, e))
        except Exception:
            continue

    results = []

    # Use start_from as base reference
    base_day = (start_from or dt.datetime.now(tz)).replace(hour=0, minute=0, second=0, microsecond=0)
    reference_now = start_from or dt.datetime.now(tz)

    for d in range(days):
        day = base_day + dt.timedelta(days=d)
        if day.isoweekday() not in working_days:
            continue

        slot_start = day.replace(hour=start_h, minute=start_m)
        slot_end_day = day.replace(hour=end_h, minute=end_m)

        while slot_start + dt.timedelta(minutes=slot_minutes) <= slot_end_day:
            slot_finish = slot_start + dt.timedelta(minutes=slot_minutes)
            overlap = any(not (slot_finish <= bstart or slot_start >= bend) for bstart, bend in busy)
            if not overlap and slot_start > reference_now:
                results.append({
                    "start_iso": slot_start.isoformat(),
                    "end_iso": slot_finish.isoformat(),
                    "start_readable": slot_start.strftime("%a, %b %d %Y | %I:%M %p"),
                    "end_readable": slot_finish.strftime("%I:%M %p")
                })
            slot_start = slot_finish

    return results

# -------------------------
# Get top N available slots
# -------------------------
def get_top_available_slots(
    cfg_path: Optional[str] = None,
    days: int = 7,
    top_n: int = 5,
    offset_days: int = 0
) -> List[Dict]:
    cfg = load_calendar_config(cfg_path)
    svc = get_service_account_service()
    tz = pytz.timezone(cfg.get("timezone", "UTC"))

    # base day with offset
    start_from = dt.datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0) + dt.timedelta(days=offset_days)

    now_iso = start_from.astimezone(pytz.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    future_iso = (start_from + dt.timedelta(days=days)).astimezone(pytz.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    busy = freebusy_query(svc, cfg["calendar_id"], now_iso, future_iso)
    slots = compute_free_slots_from_busy(busy, cfg, days=days, start_from=start_from)
    
    return sorted(slots, key=lambda s: s["start_iso"])[:top_n]

# -------------------------
# Check if prospect has upcoming event (formatted)
# -------------------------
def check_prospect_upcoming_event(prospect_email: str, cfg_path: Optional[str] = None) -> List[Dict]:
    cfg = load_calendar_config(cfg_path)
    svc = get_service_account_service()
    
    tz = pytz.timezone(cfg.get("timezone", "UTC"))
    now_local = dt.datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    now_iso = now_local.astimezone(pytz.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    events_result = svc.events().list(
        calendarId=cfg["calendar_id"],
        timeMin=now_iso,
        maxResults=250,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    events = events_result.get("items", [])
    matched_events = []

    prospect_email_lower = prospect_email.lower()

    for ev in events:
        summary = ev.get("summary", "")
        description = ev.get("description", "")
        attendees = [a.get("email") for a in (ev.get("attendees") or []) if a.get("email")]

        combined_text = " ".join([summary, description] + attendees).lower()

        if prospect_email_lower in combined_text:
            start_dt = dt.datetime.fromisoformat(ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date")).astimezone(tz)
            end_dt = dt.datetime.fromisoformat(ev.get("end", {}).get("dateTime") or ev.get("end", {}).get("date")).astimezone(tz)
            matched_events.append({
                "summary": summary,
                "description": description,
                "start_iso": start_dt.isoformat(),
                "end_iso": end_dt.isoformat(),
                "start_readable": start_dt.strftime("%a, %b %d %Y | %I:%M %p"),
                "end_readable": end_dt.strftime("%I:%M %p"),
                "attendees": attendees,
                "confirmed": True
            })

    if not matched_events:
        matched_events.append({
            "summary": "",
            "description": "",
            "start_iso": "",
            "end_iso": "",
            "start_readable": "",
            "end_readable": "",
            "attendees": [],
            "confirmed": False
        })

    return matched_events


# -------------------------
# 1️⃣ Get readable available slots
# -------------------------
def get_readable_available_slots(cfg_path: Optional[str] = None, days: int = 7, top_n: int = 5, offset_days: int = 0) -> List[str]:
    slots = get_top_available_slots(cfg_path=cfg_path, days=days, top_n=top_n, offset_days=offset_days)
    readable_slots = [f"{s['start_readable']} - {s['end_readable']}" for s in slots]
    return readable_slots

# -------------------------
# 2️⃣ Get prospect upcoming event simplified
# -------------------------
def get_prospect_upcoming_event_simple(prospect_email: str, cfg_path: Optional[str] = None) -> List[Dict]:
    events = check_prospect_upcoming_event(prospect_email, cfg_path=cfg_path)
    simplified = [{"start_readable": e["start_readable"], "confirmed": e["confirmed"]} for e in events]
    return simplified


####################################################################

# -------------------------
# Check if a slot is free
# -------------------------
def is_slot_free(cfg: dict, start_iso: str, end_iso: str) -> bool:
    """
    Returns True if the given time slot is free in the calendar.
    """
    svc = get_service_account_service()
    busy = freebusy_query(svc, cfg["calendar_id"], start_iso, end_iso)
    return len(busy) == 0


# -------------------------
# Create a calendar event
# -------------------------
def create_event(
    cfg: dict,
    summary: str,
    start_iso: str,
    end_iso: str,
    email: str = "",
    mail_body: str = "",
    conference: bool = False,
    invite_attendees: bool = False
) -> dict:
    """
    Create an event in Google Calendar.
    - summary: Event title
    - start_iso, end_iso: ISO formatted start/end datetime
    - email: prospect email to add in description/attendees
    - mail_body: put email content in description
    - conference: add Google Meet link if True
    - invite_attendees: if True, add the prospect email as attendee
    Returns event dict.
    """
    svc = get_service_account_service()
    event_body = {
        "summary": summary,
        "description": f"Email: {email}\n\n{mail_body}",
        "start": {"dateTime": start_iso, "timeZone": cfg.get("timezone", "UTC")},
        "end": {"dateTime": end_iso, "timeZone": cfg.get("timezone", "UTC")},
    }

    if invite_attendees and email:
        event_body["attendees"] = [{"email": email}]

    if conference:
        event_body["conferenceData"] = {"createRequest": {"requestId": f"meet-{int(dt.datetime.now().timestamp())}"}}

    try:
        created_event = svc.events().insert(
            calendarId=cfg["calendar_id"],
            body=event_body,
            conferenceDataVersion=1 if conference else 0
        ).execute()
        return created_event
    except HttpError as e:
        logger.error("Failed to create event: %s", e)
        raise
##############################################################################################################



# -------------------------
# Example usage
# -------------------------
if __name__ == "__main__":
    cfg_path = os.path.join("src/calender_config.yaml")
    prospect_email = "gouravpanchaludemy@gmail.com"

    
    slots_today = get_readable_available_slots(cfg_path=cfg_path, days=7, top_n=5, offset_days=5)
    print(slots_today)  # prints the list of strings

    print("\nCheck if prospect has upcoming events:")
    upcoming = get_prospect_upcoming_event_simple(prospect_email, cfg_path=cfg_path)
    print(upcoming)
