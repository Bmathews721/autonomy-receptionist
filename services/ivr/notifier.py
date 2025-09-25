
import os
from twilio.rest import Client as TwilioClient

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM = os.getenv("TWILIO_FROM", "")

def send_summary_sms(to_number: str, body: str):
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_FROM):
        raise RuntimeError("Twilio SMS env vars missing.")
    client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    client.messages.create(to=to_number, from_=TWILIO_FROM, body=body[:1500])

def send_sms_raw(to_number: str, body: str):
    send_summary_sms(to_number, body)
