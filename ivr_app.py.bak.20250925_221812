[PASTE THE ABOVE CONTENT]

# --- Admin test route for hours ---
from flask import request
from twilio.twiml.voice_response import VoiceResponse

@app.route("/admin/say-hours", methods=["GET"])
def admin_say_hours():
    called = request.args.get("called", "+18579579141")
    info = get_client_info(called)
    hours = (info or {}).get("business_hours")
    vr = VoiceResponse()
    if hours:
        speak(vr, f"Our business hours are {hours}.", info)
    else:
        speak(vr, "Sorry, I don’t have our business hours on file.", info)
    return str(vr)
