import imaplib
import email
import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
IMAP_USER = os.getenv("IMAP_USER")
IMAP_PASS = os.getenv("IMAP_PASS")


def get_last_mail_from_sender(sender_email):
    """
    Get the latest mail from a specific sender in your inbox.
    """
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST)
        mail.login(IMAP_USER, IMAP_PASS)
        mail.select("inbox")

        status, data = mail.search(None, f'(FROM "{sender_email}")')
        if status != "OK" or not data[0]:
            return ""

        latest_id = data[0].split()[-1]
        status, msg_data = mail.fetch(latest_id, "(RFC822)")
        if status != "OK":
            return ""

        msg = email.message_from_bytes(msg_data[0][1])
        subject = msg["subject"] or ""

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition")):
                    body = part.get_payload(decode=True).decode(errors="ignore")
                    break
        else:
            body = msg.get_payload(decode=True).decode(errors="ignore")

        mail_text = f"{subject}\n{body.strip()}".strip()
        return mail_text if len(mail_text.split()) >= 3 else ""

    except Exception as e:
        print(f"Error fetching email: {e}")
        return ""


def get_last_sent_mail_to(recipient_email):
    """
    Get the latest sent mail to a specific recipient.
    """
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST)
        mail.login(IMAP_USER, IMAP_PASS)
        mail.select('"[Gmail]/Sent Mail"')

        status, data = mail.search(None, f'(TO "{recipient_email}")')
        if status != "OK" or not data[0]:
            return ""

        latest_id = data[0].split()[-1]
        status, msg_data = mail.fetch(latest_id, "(RFC822)")
        if status != "OK":
            return ""

        msg = email.message_from_bytes(msg_data[0][1])
        subject = msg["subject"] or ""

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition")):
                    body = part.get_payload(decode=True).decode(errors="ignore")
                    break
        else:
            body = msg.get_payload(decode=True).decode(errors="ignore")

        mail_text = f"{subject}\n{body.strip()}".strip()
        return mail_text if len(mail_text.split()) >= 3 else ""

    except Exception as e:
        print(f"Error fetching sent email: {e}")
        return ""
