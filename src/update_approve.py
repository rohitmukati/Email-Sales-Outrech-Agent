# src/update_logic.py
import os
import json
import traceback
from dotenv import load_dotenv
from openai import OpenAI
from src.utils.helpers import load_json, save_json, setup_logging

# env load
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY2")
client = OpenAI(api_key=OPENAI_API_KEY)
MODEL = "gpt-4o-mini"

import os

DRAFT_FILE = os.path.join(os.path.dirname(__file__), "data", "draft.json")

setup_logging()


# ------------------- LLM refine -------------------
def refine_draft_with_feedback(existing_subject, existing_body, feedback):
    prompt = f"""
You are a professional sales email writer.

Here is the current draft:
Subject: {existing_subject}
Body: {existing_body}

User Feedback: "{feedback}"

👉 Task:
- Update subject and body according to feedback
- Keep professional tone
- Return valid JSON:
{{
  "subject": "<string>",
  "body": "<string>"
}}
"""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            temperature=0.7,
            messages=[
                {"role": "system", "content": "You refine sales email drafts strictly based on feedback. JSON only output."},
                {"role": "user", "content": prompt}
            ]
        )
        text = response.choices[0].message.content.strip()
        return json.loads(text)
    except Exception as e:
        print("⚠️ Error parsing LLM output:", e)
        traceback.print_exc()
        return {"subject": existing_subject, "body": existing_body}


# ------------------- Update draft.json -------------------
def apply_feedback(feedback: str):
    data = load_json(DRAFT_FILE, {})

    if not data or "draft" not in data:
        return {"error": "No draft available to update."}

    draft = data["draft"]

    refined = refine_draft_with_feedback(
        existing_subject=draft.get("subject", ""),
        existing_body=draft.get("body", ""),
        feedback=feedback
    )

    # update draft
    if isinstance(refined, dict):
        draft["subject"] = refined.get("subject", draft.get("subject"))
        draft["body"] = refined.get("body", draft.get("body"))

    data["draft"] = draft
    save_json(DRAFT_FILE, data)

    return {
        "message": "✅ Draft updated with feedback",
        "draft": draft
    }
