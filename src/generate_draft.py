# generate_draft.py
from openai import OpenAI
import os, json, re
from dotenv import load_dotenv

load_dotenv()

# support either env var name
_api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY2")
client = OpenAI(api_key=_api_key)
MODEL = "gpt-4o-mini"


def generate_draft(prospect, past_interaction, current_mail, available_slots, upcoming_events, company_config):
    """
    Generate a sales email draft based on prospect interaction state.
    upcoming_events -> list of dicts: [{'start_readable': ..., 'confirmed': True/False}]
    """
    person_email = prospect.get("email", "")
    person_name = prospect.get("name", "")
    person_role = prospect.get("role", "")
    person_industry = prospect.get("industry", "")

    # Prepare slots text for LLM
    slots_text = "\n".join([f"- {s}" for s in (available_slots or [])[:3]]) or "No available slots."

    company_text = f"""
Company: {company_config.get("sender_company", "")}
Signature: {company_config.get("signature", "")}
CTA: {company_config.get("cta", "")}
Services: {company_config.get("services", [])}
USP: {', '.join(company_config.get("usp", []))}
"""

    # ----------------- Determine existing confirmed slot -----------------
    existing_slot = ""
    for ev in (upcoming_events or []):
        if ev.get("confirmed"):
            existing_slot = ev.get("start_readable", "")
            break  # use first confirmed slot

    # ----------------- CASE HANDLING -----------------
    if existing_slot:
        # Prospect already has a scheduled meeting
        user_prompt = f"""
Prospect reply:\n{current_mail}\n
Note: Prospect already has a scheduled meeting at {existing_slot}.

Task:
- Reply politely informing them that the meeting is already scheduled.
- confirmed_slot should contain the scheduled slot info (string).
- suggested_slots should be an empty list.
- slot_action should be "existing".
"""
        slot_status = "existing"

    elif not past_interaction and not current_mail:
        # New prospect → cold outreach
        user_prompt = f"""
Prospect: {person_name} ({person_role}, {person_industry})
Task: Write a cold outreach email introducing {company_text}
and how it can help in {person_industry}. Keep it short, personalized, professional.
"""
        slot_status = "none"

    elif past_interaction and not current_mail:
        # Follow-up
        user_prompt = f"""
Write a polite follow-up email based on Past Interaction:\n{past_interaction}\n
Suggest these available slots:\n{slots_text}
Always include suggested_slots as a list of strings.
"""
        slot_status = "suggested"

    else:
        # Prospect replied without any confirmed events
        user_prompt = f"""
Prospect reply:\n{current_mail}\n
Available slots:\n{slots_text}\n
Task:
- If prospect asks for available time, suggest available slots. and confirm 
- If they confirm a time or are flexible, include confirmation and set confirmed_slot based on available slots only.
- Otherwise, reply naturally.
"""
        slot_status = "confirmed"

    # ----------------- LLM CALL -----------------
    system_prompt = """
You are a professional B2B sales email writer.
Follow User instructions exactly.
IF you found suggested lots in past interaction or current mail, and they are not matched with  {available_slots} then use available slots dont prefer old ones.
Strictly return ONLY one JSON object with fields:
- subject (string)
- body (string)
- confirmed_slot (string)  ## if slot is confirmed include it here, otherwise ""
- suggested_slots (list of strings) ## up to 3 suggested slots
- slot_action (string) ## one of "existing", "none", "suggested", "confirmed"
"""

    # Call LLM
    try:
        response = client.chat.completions.create(
            model=MODEL,
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": user_prompt.strip()}
            ],
            max_tokens=600
        )

        # robust extraction of text from different response shapes
        choice = response.choices[0]
        text = ""
        # try attribute .message.content
        try:
            text = choice.message.content.strip()
        except Exception:
            try:
                text = choice['message']['content'].strip()
            except Exception:
                # fallback to string representation
                text = str(choice)

        parsed = None
        try:
            parsed = json.loads(text)
        except Exception:
            # fallback: extract first {...} block (non-greedy, DOTALL)
            m = re.search(r"(\{(?:.|\n)*?\})", text, flags=re.S)
            if m:
                try:
                    parsed = json.loads(m.group(1))
                except Exception:
                    parsed = None

        if not isinstance(parsed, dict):
            raise ValueError(f"Invalid LLM response (not a JSON object). Raw: {text[:400]}")

        # ensure defaults / types
        subject = parsed.get("subject", "") or ""
        body = parsed.get("body", "") or ""
        confirmed_slot = parsed.get("confirmed_slot", "") or existing_slot or ""
        suggested_slots = parsed.get("suggested_slots", []) or []
        slot_action = parsed.get("slot_action", slot_status) or slot_status

        return {
            "email": person_email,
            "subject": subject,
            "body": body,
            "slot_status": slot_action,
            "slots": suggested_slots[:3],
            "final_slot": confirmed_slot
        }

    except Exception as e:
        print("⚠️ Draft generation failed:", e)
        # Return consistent dict (no tuple)
        return {
            "email": person_email,
            "subject": "",
            "body": "",
            "slot_status": slot_status,
            "slots": (available_slots or [])[:3] if slot_status == "suggested" else [],
            "final_slot": existing_slot
        }
