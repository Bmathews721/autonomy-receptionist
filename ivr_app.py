# Root shim: expose the real app & add admin test routes
from services.ivr.ivr_app import app, get_client_info, speak  # real app + helpers

from flask import request, jsonify
from twilio.twiml.voice_response import VoiceResponse

# Health/confirm route (works on Flask 1.x/2.x)
@app.route("/admin/shim-ok", methods=["GET"])
def shim_ok():
    try:
        rules = sorted([r.rule for r in app.url_map.iter_rules()])
    except Exception:
        rules = []
    return jsonify({"ok": True, "source": "root ivr_app.py shim", "routes": rules})

# Force TTS of business hours (bypasses NLU)
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
