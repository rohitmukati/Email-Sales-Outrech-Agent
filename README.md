# ✉️ Email Sales Outreach Agent

**Short description:**  
A lightweight application that generates, updates, and sends personalized email drafts based on prospect conversations. It checks calendar availability for slot suggestions, handles follow-ups, and manages confirmed bookings. Includes frontend (`index.html`), FastAPI backend (`main.py`), and optional Streamlit UI.

---

## Features

- Generate personalized email drafts (fresh / follow-up / confirmed) based on:
  - Current received email
  - Past interaction history
  - Prospect details (email, name, role, industry)
  - Calendar availability and upcoming appointments
- Update draft with user feedback (U)
- Approve and send draft (A)
- Fetch interaction history
- Simple frontend served from `index.html` with optional Streamlit UI
- Calendar integration (check upcoming events and slot status)
- Modular utilities for draft generation and sending in `src/utils` and routes in `src`

---

##
Demo - https://www.loom.com/share/e17fe73948fe4f1e98d9f18b8ad2b597?sid=701e344d-0465-4f89-8480-a17593f8da49

## Project Structure

```
.
├─ src/
│  ├─ Calender_Services/
│  │  ├─ __init__.py
│  │  ├─ calender_config.yaml
│  │  └─ services.py
│  ├─ Email_Services/
│  │  ├─ get_mails.py
│  │  └─ test.py
│  ├─ utils/
│  │  ├─ helpers.py
│  │  ├─ draft_routes.py
│  │  ├─ generate_draft.py
│  │  ├─ send_routes.py
│  │  └─ update_approve.py
├─ data/
│  ├─ draft.json
│  └─ history.json
├─ index.html              # Main frontend UI
├─ main.py                 # FastAPI backend server
├─ streamlit_app.py        # Optional Streamlit UI
├─ requirements.txt
├─ runtime.txt
└─ README.md
```

---

## Quick Setup (Local)

1. **Clone the repository**

2. **Create virtual environment and install dependencies:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Set environment variables** (create a `.env` file in the root directory):
```properties
# Google Service Account Configuration
TYPE=service_account
PROJECT_ID=your-project-id
PRIVATE_KEY_ID=your-private-key-id
PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYour-Private-Key-Here\n-----END PRIVATE KEY-----"
CLIENT_EMAIL=your-service-account@your-project.iam.gserviceaccount.com
CLIENT_ID=your-client-id
AUTH_PROVIDER_X509_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
CLIENT_X509_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com
TOKEN_URI=https://oauth2.googleapis.com/token
UNIVERSE_DOMAIN=googleapis.com

# Email Configuration (IMAP - for receiving emails)
IMAP_HOST=imap.gmail.com
IMAP_USER=your-email@gmail.com
IMAP_PASS=your-app-password
IMAP_MAILBOX=INBOX

# Email Configuration (SMTP - for sending emails)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
SMTP_USE_TLS=true

# OpenAI API Key (if using AI features)
OPENAI_API_KEY2=your-openai-api-key

# Backend URL
BACKEND_URL=http://localhost:8000
```

**Important Notes:**
- Replace all placeholder values with your actual credentials
- For Gmail: Use App Password instead of regular password (Settings → Security → 2-Step Verification → App Passwords)
- Keep your `.env` file secure and add it to `.gitignore`
- For `PRIVATE_KEY`: Ensure proper formatting with `\n` for line breaks

4. **Run the backend server:**
```bash
uvicorn main:app --reload
```

5. **Optional: Run Streamlit UI in another terminal:**
```bash
streamlit run streamlit_app.py
```

6. **Access the application:**
   - Main frontend: `http://localhost:8000/`
   - Streamlit UI: URL displayed in terminal (typically `http://localhost:8501`)

---

## API Endpoints

**Base URL:** `http://localhost:8000/api`


## How It Works

1. **Backend** reads current email and history (from mail service or `data/history.json`)
2. **Calendar service** checks upcoming events and slot availability via `Calender_Services`
3. **Draft generator** (`generate_draft.py`) constructs contextual draft (fresh/follow-up/confirmed) using business rules or LLM integration
4. **Send service** (`send_routes.py`) handles email sending and updates interaction history
5. **Frontend** (`index.html`) calls API endpoints: `/api/generate-draft`, `/api/act`, and `/api/history`

---

## Testing

### Using Postman or curl

**Generate draft example:**
```bash
curl -X POST http://localhost:8000/api/generate-draft \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "name": "Rohit",
    "role": "Founder",
    "industry": "AI"
  }'
```

**Update draft example:**
```bash
curl -X POST http://localhost:8000/api/act \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "U",
    "feedback": "Add more details about pricing"
  }'
```

**Approve and send example:**
```bash
curl -X POST http://localhost:8000/api/act \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "A",
    "feedback": null
  }'
```

---

## Technologies Used

- **Backend:** FastAPI
- **Frontend:** HTML/CSS/JavaScript
- **Optional UI:** Streamlit
- **Email:** SMTP integration
- **Calendar:** Google Calendar API
- **Data Storage:** JSON files (`draft.json`, `history.json`)

---

## Contributing

Feel free to submit issues or pull requests to improve the application.

---

## License

[Specify your license here]

---

## Contact

For questions or support, please contact [your-email@example.com]
