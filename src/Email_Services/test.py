from get_mails import get_last_mail_from_sender, get_last_sent_mail_to

# Example usage
sender_email = "maheshmukati1965@gmail.com"
recipient_email = "maheshmukati1965@gmail.com"

latest_inbox_mail = get_last_mail_from_sender(sender_email)
latest_sent_mail = get_last_sent_mail_to(recipient_email)

print("Latest Inbox Mail:\n", latest_inbox_mail)
print("Latest Sent Mail:\n", latest_sent_mail)
